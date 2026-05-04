# 1. Use official lightweight Python image
FROM python:3.11-slim

# 2. Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/uv

# 3. Environment configuration
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
WORKDIR /app

# 4. Install dependencies using uv
# Copy configuration files first to leverage caching
COPY pyproject.toml uv.lock ./

# Sync dependencies (uv creates the internal virtual environment)
RUN /uv/bin/uv sync --frozen --no-dev

# 5. Copy application source code
COPY . .

# 6. Expose the application port
EXPOSE 8080

# 7. Execute the application
# Use absolute path for uv to ensure compatibility
CMD ["/uv/bin/uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
