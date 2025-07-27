# ASTROFLORA BACKEND - DOCKERFILE MULTI-STAGE
FROM python:3.11-slim as base

# Instala dependencias del sistema necesarias para bioinformática
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Stage de desarrollo
FROM base as development

# Copia requirements y los instala
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia el código fuente
COPY . .

# Expone puerto
EXPOSE 8001

# Comando por defecto para desarrollo
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]

# Stage de producción
FROM base as production

# Instala solo dependencias de producción
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia solo el código fuente (sin archivos de desarrollo)
COPY src/ src/
COPY alembic.ini .
COPY alembic/ alembic/

# Crea usuario no-root para seguridad
RUN useradd --create-home --shell /bin/bash astroflora
USER astroflora

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Expone puerto
EXPOSE 8001

# Comando optimizado para producción
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]