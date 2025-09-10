# Python base
FROM python:3.11-slim

# Prevent .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps commonly needed for scientific Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc gfortran \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user early to own files
RUN useradd -m appuser
WORKDIR /app

# Copy dependency file first to maximize layer caching
COPY requirements.txt /app/requirements.txt

# Install Python deps
# Include your web stack and (optionally) a scientific stack for code execution
# Adjust versions as needed in requirements.txt
RUN pip install --upgrade --no-cache-dir pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY . /app

# Drop privileges
USER appuser

# Cloud Run sends traffic to $PORT; default to 8080 locally
EXPOSE 8080
ENV PORT=8080

# Start FastAPI with Uvicorn, binding to 0.0.0.0 and Cloud Run's $PORT
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
