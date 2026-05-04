# Use an official lightweight Python image with uv installed
FROM ghcr.io/astral-sh/uv:python3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Set work directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Install dependencies using uv
# We copy pyproject.toml and uv.lock first to leverage cache
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy the rest of the application
COPY . .

# Expose the port
EXPOSE 8080

# Use uv to run the application efficiently
# 'uv run' handles the virtual environment automatically inside the container
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
