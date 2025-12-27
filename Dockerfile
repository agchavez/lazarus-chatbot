# Dockerfile para API RAG CONCESA
# Python 3.11 slim para reducir tamaño de imagen
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema necesarias para PDF processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivo de requirements
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY api_rag.py .

# Copiar el PDF del catálogo
COPY Catalogo_Equipos_Construccion.pdf .

# Copiar el frontend HTML
COPY index.html .

# Crear directorios para persistencia
RUN mkdir -p /app/vectorstore_db /app/data

# Exponer puerto 8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Comando para ejecutar la aplicación
CMD ["uvicorn", "api_rag:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
