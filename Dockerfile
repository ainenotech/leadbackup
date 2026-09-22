FROM python:3.12-slim

# Prevent Python from writing .pyc files & enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required for compilation and reportlab/matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose default ports (8000 for FastAPI, 8501 for Streamlit)
EXPOSE 8000 8501

# Default command (can be overridden in docker-compose.yml)
CMD ["python", "main_api.py"]
