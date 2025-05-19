# ---------- Stage 1: Builder ----------
    FROM python:3.12-slim AS builder

    # Install build dependencies if needed
    RUN apt-get update && apt-get install -y gcc build-essential && rm -rf /var/lib/apt/lists/*
    
    # Set working directory
    WORKDIR /app
    
    # Copy requirements and install dependencies into a temporary directory
    COPY requirements.txt .
    RUN pip install --upgrade pip && \
        pip install --prefix=/install -r requirements.txt
    
    # Copy application code
    COPY app/ ./app/
    
    # ---------- Stage 2: Final Image ----------
    FROM python:3.12-slim
    
    # Set working directory
    WORKDIR /app
    
    # Copy installed Python packages from builder
    COPY --from=builder /install /usr/local
    
    # Copy application code from builder
    COPY --from=builder /app /app
    
    # Expose the port
    EXPOSE 8000
    
    # Run the FastAPI app using Uvicorn
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    