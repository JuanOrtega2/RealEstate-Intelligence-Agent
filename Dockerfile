# 1. Usamos una imagen de Python oficial y ligera
FROM python:3.11-slim

# 2. Copiamos el ejecutable de 'uv' desde su imagen oficial
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/uv

# 3. Configuramos el entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
WORKDIR /app

# 4. Instalamos las dependencias usando uv
# Copiamos los archivos de configuración
COPY pyproject.toml uv.lock ./

# Sincronizamos las dependencias (uv creará el entorno virtual internamente)
RUN /uv/bin/uv sync --frozen --no-dev

# 5. Copiamos el resto del código
COPY . .

# 6. Exponemos el puerto
EXPOSE 8080

# 7. Ejecutamos la aplicación
# Usamos la ruta completa a uv para evitar problemas de PATH
CMD ["/uv/bin/uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
