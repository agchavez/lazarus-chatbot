"""
🚀 API FastAPI para RAG OpenAI V4 - Despliegue con Docker
Integración completa del agente RAG con ingesta automática de documentos

Endpoints:
- GET /: Info de la API
- POST /chat: Enviar mensaje al agente
- DELETE /chat/{session_id}: Borrar historial de sesión
- POST /chat/new: Iniciar nueva sesión
- GET /health: Health check
- GET /sessions/{session_id}/stats: Estadísticas de sesión
- GET /crm/dashboard: Dashboard CRM

Autor: Lazarus AI Assistant
Fecha: 2025-12-26
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
import os
from dotenv import load_dotenv

# Imports del agente RAG V3
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_community.callbacks import get_openai_callback
from langchain_core.tools import tool

import sqlite3
from time import time
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN INICIAL
# ============================================================================

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    raise ValueError("⚠️ No se encontró OPENAI_API_KEY en el archivo .env")

# Configuración global
PDF_PATH = os.getenv('PDF_PATH', 'Catalogo_Equipos_Construccion.pdf')
VECTORSTORE_DIR = os.getenv('VECTORSTORE_DIR', 'vectorstore_db')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '500'))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '100'))
TOP_K_DOCUMENTS = int(os.getenv('TOP_K_DOCUMENTS', '3'))
CRM_DB_PATH = os.getenv('CRM_DB_PATH', 'crm_concesa_api.db')

# Perfil de configuración
PERFIL_ACTIVO = os.getenv('PERFIL_ACTIVO', 'balanceado')
PERFILES = {
    "economico": {
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 200,
        "prompt_type": "minimal",
    },
    "balanceado": {
        "model": "gpt-4o-mini",
        "temperature": 0.5,
        "max_tokens": 350,
        "prompt_type": "estandar",
    },
    "premium": {
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 500,
        "prompt_type": "profesional",
    }
}

CONFIG = PERFILES[PERFIL_ACTIVO]

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class MensajeRequest(BaseModel):
    """Request para enviar un mensaje al chat"""
    mensaje: str = Field(..., min_length=1, description="Mensaje del usuario")
    session_id: str = Field(..., min_length=1, description="ID de la sesión")
    verbose: bool = Field(default=False, description="Mostrar logs detallados")

class MensajeResponse(BaseModel):
    """Response del chat"""
    respuesta: str
    timestamp: str
    session_id: str
    tokens_usados: int
    costo_usd: float
    cliente_nombre: Optional[str] = None

class NuevaSesionRequest(BaseModel):
    """Request para crear nueva sesión"""
    session_id: str = Field(..., min_length=1, description="ID para la nueva sesión")

class EstadisticasResponse(BaseModel):
    """Estadísticas de una sesión"""
    session_id: str
    total_mensajes: int
    total_tokens: int
    total_costo_usd: float
    tools_usadas: int
    tiempo_total_segundos: float
    cliente_nombre: Optional[str] = None

class CRMDashboardResponse(BaseModel):
    """Dashboard CRM"""
    total_clientes: int
    clientes_nuevos_24h: int
    total_productos_consultados: int
    top_productos: List[Dict]
    clientes_recientes: List[Dict]
    hot_leads: List[Dict]

# ============================================================================
# SISTEMA CRM
# ============================================================================

class CRMManager:
    """Gestor de CRM con SQLite"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.current_client_id = None
        self.current_client_name = None
        self.init_database()

    def init_database(self):
        """Inicializa la base de datos"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = self.conn.cursor()

        # Tabla de clientes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                primer_contacto TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ultimo_contacto TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_consultas INTEGER DEFAULT 0,
                estado TEXT DEFAULT 'nuevo'
            )
        """)

        # Tabla de productos de interés
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos_interes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                producto TEXT NOT NULL,
                fecha_interes TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                precio_consultado REAL,
                dias_consultados INTEGER,
                estado TEXT DEFAULT 'interesado',
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            )
        """)

        # Tabla de conversaciones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                mensaje_usuario TEXT,
                respuesta_asistente TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tokens_usados INTEGER,
                costo_usd REAL,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            )
        """)

        self.conn.commit()

    def crear_o_obtener_cliente(self, nombre: str) -> int:
        """Crea un nuevo cliente o obtiene el ID si ya existe"""
        cursor = self.conn.cursor()

        cursor.execute(
            "SELECT id FROM clientes WHERE nombre = ? COLLATE NOCASE",
            (nombre,)
        )
        result = cursor.fetchone()

        if result:
            cliente_id = result[0]
            cursor.execute(
                "UPDATE clientes SET ultimo_contacto = CURRENT_TIMESTAMP, total_consultas = total_consultas + 1 WHERE id = ?",
                (cliente_id,)
            )
            self.conn.commit()
            return cliente_id
        else:
            cursor.execute(
                "INSERT INTO clientes (nombre, total_consultas) VALUES (?, 1)",
                (nombre,)
            )
            self.conn.commit()
            return cursor.lastrowid

    def registrar_interes_producto(self, cliente_id: int, producto: str,
                                   precio: Optional[float] = None,
                                   dias: Optional[int] = None):
        """Registra el interés de un cliente en un producto"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO productos_interes
            (cliente_id, producto, precio_consultado, dias_consultados)
            VALUES (?, ?, ?, ?)
        """, (cliente_id, producto, precio, dias))
        self.conn.commit()

    def registrar_conversacion(self, cliente_id: int, mensaje: str,
                              respuesta: str, tokens: int = 0, costo: float = 0.0):
        """Registra una conversación en la BD"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO conversaciones
            (cliente_id, mensaje_usuario, respuesta_asistente, tokens_usados, costo_usd)
            VALUES (?, ?, ?, ?, ?)
        """, (cliente_id, mensaje, respuesta, tokens, costo))
        self.conn.commit()

    def obtener_dashboard(self) -> Dict:
        """Obtiene métricas del CRM"""
        cursor = self.conn.cursor()

        # Total de clientes
        cursor.execute("SELECT COUNT(*) FROM clientes")
        total_clientes = cursor.fetchone()[0]

        # Clientes nuevos (últimas 24 horas)
        cursor.execute("""
            SELECT COUNT(*) FROM clientes
            WHERE primer_contacto >= datetime('now', '-1 day')
        """)
        clientes_nuevos = cursor.fetchone()[0]

        # Total de productos consultados
        cursor.execute("SELECT COUNT(*) FROM productos_interes")
        total_productos = cursor.fetchone()[0]

        # Top productos
        cursor.execute("""
            SELECT producto, COUNT(*) as consultas
            FROM productos_interes
            GROUP BY producto
            ORDER BY consultas DESC
            LIMIT 5
        """)
        top_productos = [{"producto": p, "consultas": c} for p, c in cursor.fetchall()]

        # Clientes activos recientes
        cursor.execute("""
            SELECT nombre, total_consultas, ultimo_contacto
            FROM clientes
            ORDER BY ultimo_contacto DESC
            LIMIT 5
        """)
        clientes_recientes = [
            {"nombre": n, "consultas": c, "ultimo_contacto": u}
            for n, c, u in cursor.fetchall()
        ]

        # Hot leads
        cursor.execute("""
            SELECT nombre, total_consultas
            FROM clientes
            WHERE total_consultas >= 3
            ORDER BY total_consultas DESC
        """)
        hot_leads = [{"nombre": n, "consultas": c} for n, c in cursor.fetchall()]

        return {
            "total_clientes": total_clientes,
            "clientes_nuevos_24h": clientes_nuevos,
            "total_productos_consultados": total_productos,
            "top_productos": top_productos,
            "clientes_recientes": clientes_recientes,
            "hot_leads": hot_leads
        }

# Instancia global del CRM
crm = CRMManager(CRM_DB_PATH)

# ============================================================================
# TOOLS
# ============================================================================

# Variable global para tracking
tool_usage_stats = {}

def init_tools(retriever, crm_instance):
    """Inicializa las herramientas del agente"""

    global tool_usage_stats
    tool_usage_stats = {
        "buscar_info_producto": 0,
        "calcular_descuento": 0,
        "verificar_disponibilidad": 0,
        "calcular_fecha_entrega": 0,
        "guardar_nombre_cliente": 0,
        "registrar_interes": 0
    }

    @tool
    def buscar_info_producto(producto: str) -> str:
        """Busca información de productos en el catálogo"""
        tool_usage_stats["buscar_info_producto"] += 1
        docs = retriever.invoke(producto)
        if docs:
            return docs[0].page_content[:500]
        return "No se encontró información del producto"

    @tool
    def calcular_descuento(precio: float, dias: int) -> dict:
        """Calcula el precio total de renta con descuentos"""
        tool_usage_stats["calcular_descuento"] += 1
        total = precio * dias

        if dias >= 30:
            descuento = 0.20
        elif dias >= 14:
            descuento = 0.15
        elif dias >= 7:
            descuento = 0.10
        else:
            descuento = 0

        total_con_descuento = total * (1 - descuento)
        ahorro = total - total_con_descuento

        return {
            "total_sin_descuento": f"L{total:,.2f}",
            "descuento_porcentaje": f"{descuento*100:.0f}%",
            "total_con_descuento": f"L{total_con_descuento:,.2f}",
            "ahorro": f"L{ahorro:,.2f}"
        }

    @tool
    def verificar_disponibilidad(equipo: str) -> str:
        """Verifica si un equipo está disponible"""
        tool_usage_stats["verificar_disponibilidad"] += 1
        inventario = {
            "demoledor": {"disponible": True, "unidades": 3},
            "rotomartillo": {"disponible": True, "unidades": 5},
            "compactador": {"disponible": False, "unidades": 0},
            "bailarina": {"disponible": True, "unidades": 2}
        }

        for key, info in inventario.items():
            if key in equipo.lower():
                if info["disponible"]:
                    return f"✅ {equipo.upper()} disponible. Stock: {info['unidades']} unidades"
                else:
                    return f"❌ {equipo.upper()} agotado temporalmente"

        return f"⚠️ Equipo no encontrado: {equipo}"

    @tool
    def calcular_fecha_entrega(dias: int) -> str:
        """Calcula la fecha de devolución del equipo"""
        tool_usage_stats["calcular_fecha_entrega"] += 1
        from datetime import datetime, timedelta
        fecha_hoy = datetime.now()
        fecha_devolucion = fecha_hoy + timedelta(days=dias)

        return f"""📅 Fechas de renta:
- Inicio: {fecha_hoy.strftime('%d/%m/%Y')}
- Devolución: {fecha_devolucion.strftime('%d/%m/%Y')}
- Total días: {dias}"""

    @tool
    def guardar_nombre_cliente(nombre: str) -> str:
        """Registra el nombre del cliente en el CRM"""
        tool_usage_stats["guardar_nombre_cliente"] += 1
        cliente_id = crm_instance.crear_o_obtener_cliente(nombre)
        crm_instance.current_client_id = cliente_id
        crm_instance.current_client_name = nombre
        return f"✅ Perfecto {nombre}, te damos la bienvenida a CONCESA. ¿En qué te puedo ayudar hoy?"

    @tool
    def registrar_interes(producto: str, precio: float = None, dias: int = None) -> str:
        """Registra el interés de un cliente en un producto"""
        tool_usage_stats["registrar_interes"] += 1

        if not crm_instance.current_client_id:
            return "⚠️ Necesito tu nombre primero para registrar tu interés"

        crm_instance.registrar_interes_producto(
            crm_instance.current_client_id,
            producto,
            precio,
            dias
        )
        return f"📝 Interés registrado en {producto}. Nos pondremos en contacto contigo pronto."

    return [
        buscar_info_producto,
        calcular_descuento,
        verificar_disponibilidad,
        calcular_fecha_entrega,
        guardar_nombre_cliente,
        registrar_interes
    ]

# ============================================================================
# CLASE CHAT RAG V4
# ============================================================================

class ChatRAGV4:
    """Sistema de chat V4 para FastAPI"""

    def __init__(self, llm, tools, retriever, crm_instance):
        self.llm = llm.bind_tools(tools)
        self.tools = tools
        self.retriever = retriever
        self.crm = crm_instance
        self.historial = []
        self.max_iterations = 5
        self.primer_mensaje = True

        self.session_stats = {
            "total_mensajes": 0,
            "total_tokens": 0,
            "total_costo_usd": 0.0,
            "tokens_prompt": 0,
            "tokens_completion": 0,
            "tiempo_total_segundos": 0.0,
            "tools_usadas": 0
        }

    def chat(self, mensaje_usuario: str) -> tuple[str, int, float]:
        """Procesa un mensaje y retorna (respuesta, tokens, costo)"""

        inicio = time()

        # Si es el primer mensaje y no hay cliente, pedir nombre
        if self.primer_mensaje and not self.crm.current_client_id:
            self.historial.append(SystemMessage(
                content="INSTRUCCIÓN IMPORTANTE: Antes de ayudar al cliente, debes preguntarle su nombre de forma amable y natural."
            ))
            self.primer_mensaje = False

        # Agregar mensaje del usuario
        self.historial.append(HumanMessage(content=mensaje_usuario))
        self.session_stats["total_mensajes"] += 1

        ultimo_costo = 0.0
        ultimo_tokens = 0

        # Loop de iteraciones
        for iteracion in range(self.max_iterations):

            with get_openai_callback() as cb:
                response = self.llm.invoke(self.historial)

                self.session_stats["total_tokens"] += cb.total_tokens
                self.session_stats["tokens_prompt"] += cb.prompt_tokens
                self.session_stats["tokens_completion"] += cb.completion_tokens
                self.session_stats["total_costo_usd"] += cb.total_cost

                ultimo_costo = cb.total_cost
                ultimo_tokens = cb.total_tokens

            self.historial.append(response)

            # Si no hay tool calls, es la respuesta final
            if not response.tool_calls:
                tiempo_respuesta = time() - inicio
                self.session_stats["tiempo_total_segundos"] += tiempo_respuesta

                # Registrar conversación en CRM
                if self.crm.current_client_id:
                    self.crm.registrar_conversacion(
                        self.crm.current_client_id,
                        mensaje_usuario,
                        response.content,
                        ultimo_tokens,
                        ultimo_costo
                    )

                    # Detectar productos mencionados
                    productos_comunes = ['rotomartillo', 'demoledor', 'compactador', 'bailarina',
                                       'allanadora', 'mezcladora', 'te-500', 'te-2000', 'te-800']
                    mensaje_lower = mensaje_usuario.lower()

                    for producto in productos_comunes:
                        if producto in mensaje_lower:
                            self.crm.registrar_interes_producto(self.crm.current_client_id, producto)
                            break

                return response.content, ultimo_tokens, ultimo_costo

            # Ejecutar tools
            for tool_call in response.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']

                self.session_stats["tools_usadas"] += 1

                for tool in self.tools:
                    if tool.name == tool_name:
                        result = tool.invoke(tool_args)
                        self.historial.append(
                            ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call['id']
                            )
                        )

        return "⚠️ Límite de iteraciones alcanzado", 0, 0.0

    def limpiar_historial(self):
        """Limpia el historial manteniendo el cliente"""
        self.historial = []
        self.primer_mensaje = True
        self.session_stats = {
            "total_mensajes": 0,
            "total_tokens": 0,
            "total_costo_usd": 0.0,
            "tokens_prompt": 0,
            "tokens_completion": 0,
            "tiempo_total_segundos": 0.0,
            "tools_usadas": 0
        }
        for key in tool_usage_stats:
            tool_usage_stats[key] = 0

    def nueva_sesion(self):
        """Inicia una nueva sesión completa"""
        self.limpiar_historial()
        self.crm.current_client_id = None
        self.crm.current_client_name = None

# ============================================================================
# FUNCIÓN DE INGESTA DE DOCUMENTOS
# ============================================================================

def ingerir_documentos():
    """
    Ingesta los documentos PDF y crea el vectorstore.
    Se ejecuta al inicio de la aplicación.
    """
    logger.info("🚀 Iniciando ingesta de documentos...")

    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"⚠️ No se encontró el archivo PDF: {PDF_PATH}")

    logger.info(f"📄 Cargando documento: {PDF_PATH}")

    # Cargar documento
    loader = PyPDFLoader(PDF_PATH)
    documents = loader.load()
    logger.info(f"✅ Documento cargado: {len(documents)} páginas")

    # Dividir en chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    docs = text_splitter.split_documents(documents)
    logger.info(f"✅ Documento dividido en {len(docs)} chunks")

    # Crear embeddings
    logger.info("🔄 Creando embeddings...")
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

    # Cargar o crear vectorstore
    index_path = os.path.join(VECTORSTORE_DIR, "index.faiss")
    if os.path.exists(index_path):
        logger.info(f"📦 Cargando vectorstore existente desde {VECTORSTORE_DIR}")
        vectorstore = FAISS.load_local(VECTORSTORE_DIR, embeddings, allow_dangerous_deserialization=True)
    else:
        logger.info("🆕 Creando nuevo vectorstore...")
        vectorstore = FAISS.from_documents(docs, embeddings)
        vectorstore.save_local(VECTORSTORE_DIR)
        logger.info(f"💾 Vectorstore guardado en {VECTORSTORE_DIR}")

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": TOP_K_DOCUMENTS}
    )

    logger.info("✅ Ingesta de documentos completada")
    return retriever, embeddings

# ============================================================================
# INICIALIZACIÓN DEL SISTEMA RAG
# ============================================================================

logger.info("🚀 Inicializando sistema RAG...")

# Ingerir documentos
retriever, embeddings = ingerir_documentos()

# Configurar LLM
llm = ChatOpenAI(
    model=CONFIG["model"],
    temperature=CONFIG["temperature"],
    max_tokens=CONFIG["max_tokens"]
)

# Crear tools
tools = init_tools(retriever, crm)

logger.info("✅ Sistema RAG inicializado correctamente")

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="API RAG CONCESA",
    description="API REST para agente inteligente de equipos de construcción",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estado de la aplicación (sesiones activas)
sessions: Dict[str, ChatRAGV4] = {}

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
def home():
    """Servir el frontend HTML"""
    return FileResponse("index.html")

@app.get("/api")
def api_info():
    """Información de la API"""
    return {
        "nombre": "API RAG CONCESA V4",
        "version": "1.0.0",
        "descripcion": "API REST para agente inteligente de equipos de construcción con FastAPI",
        "endpoints": {
            "GET /": "Frontend de la aplicación",
            "GET /api": "Información de la API",
            "POST /chat": "Enviar mensaje al agente",
            "DELETE /chat/{session_id}": "Borrar historial de sesión",
            "POST /chat/new": "Iniciar nueva sesión",
            "GET /sessions/{session_id}/stats": "Estadísticas de sesión",
            "GET /crm/dashboard": "Dashboard CRM",
            "GET /health": "Health check"
        },
        "perfil_activo": PERFIL_ACTIVO,
        "modelo": CONFIG["model"]
    }

@app.get("/health")
def health_check():
    """Health check"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "sesiones_activas": len(sessions)
    }

@app.post("/chat", response_model=MensajeResponse)
async def chat(request: MensajeRequest):
    """Enviar mensaje al agente"""

    # Crear sesión si no existe
    if request.session_id not in sessions:
        sessions[request.session_id] = ChatRAGV4(llm, tools, retriever, crm)

    session = sessions[request.session_id]

    try:
        # Procesar mensaje
        respuesta, tokens, costo = session.chat(request.mensaje)

        return MensajeResponse(
            respuesta=respuesta,
            timestamp=datetime.now().isoformat(),
            session_id=request.session_id,
            tokens_usados=tokens,
            costo_usd=costo,
            cliente_nombre=crm.current_client_name
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar mensaje: {str(e)}")

@app.delete("/chat/{session_id}")
def borrar_historial(session_id: str):
    """Borrar historial de una sesión (mantiene cliente)"""

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    sessions[session_id].limpiar_historial()

    return {
        "mensaje": "Historial borrado exitosamente",
        "session_id": session_id,
        "cliente_activo": crm.current_client_name
    }

@app.post("/chat/new")
def nueva_sesion(request: NuevaSesionRequest):
    """Iniciar una nueva sesión completa (resetea cliente)"""

    # Si existe, resetear completamente
    if request.session_id in sessions:
        sessions[request.session_id].nueva_sesion()
    else:
        sessions[request.session_id] = ChatRAGV4(llm, tools, retriever, crm)

    return {
        "mensaje": "Nueva sesión iniciada",
        "session_id": request.session_id
    }

@app.get("/sessions/{session_id}/stats", response_model=EstadisticasResponse)
def obtener_estadisticas(session_id: str):
    """Obtener estadísticas de una sesión"""

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    session = sessions[session_id]
    stats = session.session_stats

    return EstadisticasResponse(
        session_id=session_id,
        total_mensajes=stats["total_mensajes"],
        total_tokens=stats["total_tokens"],
        total_costo_usd=stats["total_costo_usd"],
        tools_usadas=stats["tools_usadas"],
        tiempo_total_segundos=stats["tiempo_total_segundos"],
        cliente_nombre=crm.current_client_name
    )

@app.get("/crm/dashboard", response_model=CRMDashboardResponse)
def crm_dashboard():
    """Obtener dashboard del CRM"""

    try:
        dashboard = crm.obtener_dashboard()
        return CRMDashboardResponse(**dashboard)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener dashboard: {str(e)}")

# ============================================================================
# EJECUCIÓN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    logger.info("\n🚀 Iniciando API FastAPI...")
    logger.info("📖 Documentación: http://localhost:8000/docs")
    logger.info("🔄 ReDoc: http://localhost:8000/redoc")
    uvicorn.run(app, host="0.0.0.0", port=8000)
