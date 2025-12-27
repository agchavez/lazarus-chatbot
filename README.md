# 🚀 API RAG CONCESA - Despliegue con Docker

Sistema completo de agente RAG (Retrieval-Augmented Generation) para CONCESA con ingesta automática de documentos, listo para desplegar con Docker.

## 📋 Contenido del Proyecto

```
Clase Final/
├── api_rag.py                           # API FastAPI con ingesta integrada
├── Dockerfile                           # Imagen Docker optimizada
├── docker-compose.yml                   # Orquestación con Docker Compose
├── requirements.txt                     # Dependencias Python
├── .env.example                         # Plantilla de variables de entorno
├── Catalogo_Equipos_Construccion.pdf   # Catálogo de productos
└── README.md                            # Este archivo
```

## ✨ Características

- ✅ **Ingesta Automática**: Los documentos PDF se procesan automáticamente al iniciar
- ✅ **API REST Completa**: FastAPI con documentación interactiva (Swagger/ReDoc)
- ✅ **Sistema CRM**: Base de datos SQLite para tracking de clientes
- ✅ **Herramientas Inteligentes**: Búsqueda RAG, cálculos, disponibilidad, etc.
- ✅ **Persistencia de Datos**: Volúmenes Docker para BD y vectorstore
- ✅ **Health Checks**: Monitoreo automático del estado del servicio
- ✅ **Variables Configurables**: Todo configurable vía archivo .env

## 🔧 Requisitos Previos

- Docker (versión 20.10 o superior)
- Docker Compose (versión 2.0 o superior)
- API Key de OpenAI

## 🚀 Inicio Rápido

### 1. Configurar Variables de Entorno

Copia el archivo de ejemplo y configura tu API key:

```bash
cp .env.example .env
```

Edita el archivo `.env` y agrega tu API key de OpenAI:

```env
OPENAI_API_KEY=sk-tu-api-key-aqui
```

### 2. Construir y Ejecutar con Docker Compose

```bash
docker-compose up --build
```

Esto hará:
- ✅ Construir la imagen Docker
- ✅ Ingerir el PDF automáticamente
- ✅ Crear el vectorstore FAISS
- ✅ Inicializar la base de datos CRM
- ✅ Iniciar la API en el puerto 8000

### 3. Verificar que Funciona

Abre tu navegador en:

- **🎨 Frontend (Interfaz de Chat)**: http://localhost:8000
- **📡 Info de la API**: http://localhost:8000/api
- **📖 Documentación Interactiva (Swagger)**: http://localhost:8000/docs
- **📚 Documentación ReDoc**: http://localhost:8000/redoc
- **❤️ Health Check**: http://localhost:8000/health

**¡Listo para usar!** El frontend se abrirá directamente en la raíz y podrás comenzar a chatear con el agente inmediatamente.

## 📡 Endpoints Disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Frontend HTML (interfaz de chat) |
| GET | `/api` | Información de la API |
| GET | `/health` | Health check del servicio |
| POST | `/chat` | Enviar mensaje al agente |
| POST | `/chat/new` | Iniciar nueva sesión |
| DELETE | `/chat/{session_id}` | Borrar historial de sesión |
| GET | `/sessions/{session_id}/stats` | Estadísticas de sesión |
| GET | `/crm/dashboard` | Dashboard del CRM |
| GET | `/docs` | Documentación Swagger |
| GET | `/redoc` | Documentación ReDoc |

## 💬 Ejemplo de Uso

### Usando el Frontend Web

1. Abre tu navegador en http://localhost:8000
2. Escribe tu mensaje en el campo de texto
3. Presiona Enter o haz clic en "Enviar"
4. El agente responderá automáticamente

**Funcionalidades del Frontend:**
- ✅ Chat interactivo en tiempo real
- ✅ Indicador de escritura mientras el agente piensa
- ✅ Historial de conversación
- ✅ Botón para limpiar historial (mantiene cliente)
- ✅ Botón para nueva sesión (resetea todo)
- ✅ Estadísticas en tiempo real (tokens, costo)
- ✅ Renderizado de Markdown en respuestas
- ✅ Diseño responsive

### Usando la API directamente (curl)

Si prefieres interactuar con la API mediante comandos curl:

#### Enviar un mensaje al agente

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "mensaje": "Hola, mi nombre es Juan",
    "session_id": "session-123",
    "verbose": false
  }'
```

#### Ver estadísticas de sesión

```bash
curl -X GET "http://localhost:8000/sessions/session-123/stats"
```

#### Ver dashboard CRM

```bash
curl -X GET "http://localhost:8000/crm/dashboard"
```

### Flujo Típico de Conversación

1. **Usuario**: "Hola, mi nombre es Juan"
   - El agente pedirá tu nombre y lo guardará en el CRM

2. **Usuario**: "¿Cuánto cuesta rentar un rotomartillo?"
   - El agente buscará en el catálogo PDF usando RAG
   - Registrará tu interés en el producto

3. **Usuario**: "Lo quiero por 10 días"
   - El agente calculará el precio con descuentos
   - Mostrará las fechas de entrega
   - Todo queda registrado en el CRM

## ⚙️ Configuración Avanzada

### Perfiles de Configuración

Puedes cambiar el perfil del LLM en el archivo `.env`:

```env
PERFIL_ACTIVO=balanceado  # Opciones: economico, balanceado, premium
```

**Perfiles disponibles:**

- **economico**: Menor costo, respuestas cortas (200 tokens)
- **balanceado**: Balance costo-calidad (350 tokens) - **Por defecto**
- **premium**: Máxima calidad, respuestas detalladas (500 tokens)

### Personalizar Parámetros de Embeddings

```env
EMBEDDING_MODEL=text-embedding-3-small  # Modelo de embeddings
CHUNK_SIZE=500                          # Tamaño de chunks
CHUNK_OVERLAP=100                       # Overlap entre chunks
TOP_K_DOCUMENTS=3                       # Documentos a recuperar
```

### Cambiar Base de Datos o Vectorstore

```env
CRM_DB_PATH=crm_concesa_api.db         # Path de la BD SQLite
VECTORSTORE_DIR=vectorstore_db          # Directorio del vectorstore
```

## 🔄 Comandos Docker Útiles

### Detener los servicios

```bash
docker-compose down
```

### Ver logs en tiempo real

```bash
docker-compose logs -f
```

### Reiniciar solo el servicio (sin rebuild)

```bash
docker-compose restart
```

### Eliminar volúmenes (resetear datos)

```bash
docker-compose down -v
```

### Reconstruir desde cero

```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

## 📂 Persistencia de Datos

Los datos se persisten en volúmenes Docker:

- **Base de datos CRM**: `./data/crm_concesa_api.db`
- **Vectorstore**: `./vectorstore_db/` (se puede regenerar)

Para hacer backup:

```bash
# Backup de la base de datos
docker cp concesa-api-rag:/app/crm_concesa_api.db ./backup_crm.db

# Backup del vectorstore (opcional)
docker cp concesa-api-rag:/app/vectorstore_db ./backup_vectorstore
```

## 🐛 Troubleshooting

### Error: "No se encontró OPENAI_API_KEY"

**Solución**: Verifica que el archivo `.env` existe y contiene tu API key:

```bash
cat .env | grep OPENAI_API_KEY
```

### Error: "No se encontró el archivo PDF"

**Solución**: Verifica que el PDF está en el directorio:

```bash
ls -la Catalogo_Equipos_Construccion.pdf
```

### El servicio no inicia

**Solución**: Verifica los logs:

```bash
docker-compose logs api-rag
```

### Resetear todo el sistema

```bash
docker-compose down -v
rm -rf vectorstore_db data
docker-compose up --build
```

## 📊 Monitoreo

### Ver estado del contenedor

```bash
docker ps
```

### Ver salud del servicio

```bash
docker inspect --format='{{json .State.Health}}' concesa-api-rag
```

### Ver uso de recursos

```bash
docker stats concesa-api-rag
```

## 🔒 Seguridad

- ⚠️ **NO** commitees el archivo `.env` con tu API key
- ✅ Usa `.env.example` como plantilla
- ✅ El archivo `.env` debe estar en `.gitignore`
- ✅ En producción, usa secretos de Docker o variables de entorno del host

## 🌐 Despliegue en Producción

### Consideraciones

1. **Remover `--reload`** del comando en Dockerfile (línea CMD)
2. **Usar HTTPS** con un proxy reverso (nginx, Traefik)
3. **Configurar CORS** apropiadamente para tu dominio
4. **Usar secretos** para la API key (Docker Secrets, AWS Secrets Manager)
5. **Configurar logs** con volúmenes persistentes
6. **Establecer límites de recursos** en docker-compose.yml

### Ejemplo de configuración de producción

```yaml
services:
  api-rag:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    restart: always
```

## 📝 Notas Importantes

1. **Primera ejecución**: La ingesta de documentos puede tardar 1-2 minutos
2. **Vectorstore**: Se crea automáticamente si no existe
3. **Base de datos**: Se crea automáticamente en la primera ejecución
4. **Sesiones**: Se mantienen en memoria, se pierden al reiniciar el contenedor

## 🤝 Soporte

Si encuentras problemas:

1. Revisa los logs: `docker-compose logs -f`
2. Verifica el health check: `curl http://localhost:8000/health`
3. Consulta la documentación interactiva: `http://localhost:8000/docs`

## 📄 Licencia

Este proyecto es parte del curso de Lazarus AI Assistant.

---

**¡Listo para usar!** Solo ejecuta `docker-compose up` y tu API RAG estará funcionando. 🚀
