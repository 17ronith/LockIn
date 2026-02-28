FROM python:3.11-slim

WORKDIR /app

# Install CPU-only PyTorch first (much smaller than full CUDA version)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy and install remaining requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway sets PORT env var
CMD uvicorn api_backend:app --host 0.0.0.0 --port ${PORT:-8000}
