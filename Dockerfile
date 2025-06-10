FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/

# Install dependencies
RUN uv pip install --system -e .

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "src.webhook_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
