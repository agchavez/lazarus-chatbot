# 🚀 INSTRUCCIONES RÁPIDAS - API RAG CONCESA

## ✅ ESTADO: FUNCIONANDO CORRECTAMENTE

La API RAG está completamente configurada y funcionando con Docker.

## 🔥 Inicio Rápido (3 pasos)

### 1. Asegúrate de tener Docker instalado
```bash
docker --version
docker-compose --version
```

### 2. Inicia la aplicación
```bash
cd "Clases/Clase Final"
docker-compose up -d
```

### 3. Abre el navegador
```
http://localhost:8001
```

¡Listo! La interfaz de chat estará disponible inmediatamente.

## 📡 URLs Importantes

| URL | Descripción |
|-----|-------------|
| http://localhost:8001 | 🎨 **Frontend** (Interfaz de chat) |
| http://localhost:8001/api | 📊 Info de la API |
| http://localhost:8001/health | ❤️ Health check |
| http://localhost:8001/docs | 📖 Documentación Swagger |
| http://localhost:8001/redoc | 📚 Documentación ReDoc |
| http://localhost:8001/crm/dashboard | 📈 Dashboard CRM |

## 🎯 ¿Qué incluye esta instalación?

✅ **Ingesta Automática de Documentos**
- El PDF se procesa automáticamente al iniciar
- Se crean embeddings con OpenAI
- Se guarda en vectorstore FAISS

✅ **API REST Completa**
- FastAPI con documentación interactiva
- Endpoints para chat, sesiones y CRM

✅ **Frontend Moderno**
- Interfaz de chat elegante
- Indicador de escritura en tiempo real
- Estadísticas de tokens y costo

✅ **Sistema CRM**
- Base de datos SQLite
- Tracking de clientes y productos
- Dashboard con métricas

✅ **Herramientas Inteligentes**
- Búsqueda RAG en catálogo
- Cálculo de descuentos
- Verificación de disponibilidad
- Cálculo de fechas de entrega

## 📝 Logs en Tiempo Real

Ver los logs de la aplicación:
```bash
docker-compose logs -f
```

Ver solo las últimas 50 líneas:
```bash
docker-compose logs --tail=50
```

## 🔄 Comandos Útiles

### Detener la aplicación
```bash
docker-compose down
```

### Reiniciar la aplicación
```bash
docker-compose restart
```

### Reconstruir desde cero
```bash
docker-compose down -v
docker-compose up --build -d
```

### Ver estado de los contenedores
```bash
docker-compose ps
```

## 💬 Probar el Chat

1. Abre http://localhost:8001
2. Escribe: "Hola, mi nombre es Juan"
3. Pregunta: "¿Cuánto cuesta el rotomartillo?"
4. Pregunta: "Lo quiero por 10 días"

El agente:
- Te pedirá tu nombre (si no lo has dado)
- Buscará información en el PDF
- Calculará precios con descuentos
- Registrará todo en el CRM

## 🐛 Solución de Problemas

### El puerto 8001 está ocupado

Edita `docker-compose.yml` y cambia el puerto:
```yaml
ports:
  - "8002:8000"  # Cambiar 8001 por 8002
```

Luego reinicia:
```bash
docker-compose down
docker-compose up -d
```

### Ver errores detallados
```bash
docker-compose logs api-rag
```

### Resetear completamente
```bash
docker-compose down -v
rm -rf vectorstore_db data
docker-compose up --build -d
```

## 📊 Arquitectura

```
┌─────────────────────────────────────────────┐
│           DOCKER CONTAINER                   │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │   FastAPI + Uvicorn (Puerto 8000)     │ │
│  │                                        │ │
│  │   Endpoints:                          │ │
│  │   - GET / (Frontend HTML)             │ │
│  │   - POST /chat (Agente RAG)           │ │
│  │   - GET /crm/dashboard                │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │   Sistema RAG                          │ │
│  │                                        │ │
│  │   - LangChain                         │ │
│  │   - OpenAI Embeddings                 │ │
│  │   - FAISS Vectorstore                 │ │
│  │   - PDF Loader                        │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │   Base de Datos                        │ │
│  │                                        │ │
│  │   - SQLite CRM                        │ │
│  │   - Persistencia en volumen           │ │
│  └────────────────────────────────────────┘ │
│                                              │
└─────────────────────────────────────────────┘
         │
         │ Puerto 8001 → 8000
         ▼
    localhost:8001
```

## 🎓 Archivos del Proyecto

```
Clase Final/
├── api_rag.py                    # API principal con ingesta integrada
├── Dockerfile                    # Imagen Docker
├── docker-compose.yml            # Orquestación
├── requirements.txt              # Dependencias Python
├── .env                         # Variables de entorno (con API key)
├── .env.example                 # Plantilla de configuración
├── index.html                   # Frontend de chat
├── Catalogo_Equipos_Construccion.pdf  # Catálogo de productos
├── README.md                    # Documentación completa
└── INSTRUCCIONES_RAPIDAS.md     # Este archivo
```

## 🔐 Seguridad

⚠️ **IMPORTANTE:**
- El archivo `.env` contiene tu API key de OpenAI
- NO lo subas a repositorios públicos
- Está en `.gitignore` por seguridad
- Usa `.env.example` como plantilla

## ✨ Características Destacadas

🚀 **Despliegue con 1 comando**
```bash
docker-compose up -d
```

🔄 **Ingesta automática** al iniciar

💾 **Persistencia** de datos con volúmenes Docker

📊 **Monitoring** con health checks

🎨 **Frontend** incluido y listo para usar

📈 **CRM** con tracking de clientes

🤖 **Agente inteligente** con 6 herramientas

## 📞 Soporte

Si tienes problemas:
1. Revisa los logs: `docker-compose logs -f`
2. Verifica el health check: `curl http://localhost:8001/health`
3. Consulta el README.md para más detalles

---

**¡Todo listo para usar!** 🎉

Solo ejecuta `docker-compose up -d` y abre http://localhost:8001 en tu navegador.
