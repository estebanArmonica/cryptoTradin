# Parte 1: Build stage
FROM python:3.12-slim AS build

# Parte 2: creamos el directorio de trabajo
WORKDIR /app

# Instalar dependencias de compilación solo si son necesarias
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Crear y activar entorno virtual
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instalar dependencias primero para aprovechar caché de Docker
COPY pyproject.toml poetry.lock* ./
RUN pip install --upgrade pip && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi

# Stage 2: Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Copiar solo el entorno virtual desde el builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Crear usuario no root
RUN useradd -m myuser && chown -R myuser:myuser /app
USER myuser

# Copiar solo lo necesario
COPY --chown=myuser:myuser ./src /app

# Variables de entorno
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Puerto expuesto (el mismo que usa Uvicorn)
EXPOSE 8400

# Comando de inicio (sin --reload en producción)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8400"]