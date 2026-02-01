FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libpq-dev \
    gcc \
    g++ \
    libgl1 \
    libglvnd0 \
    libglib2.0-0 \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first to leverage standard layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create media directory and setup user in one layer
RUN mkdir -p /app/media && \
    useradd -m -u 1000 skyuser && \
    chown -R skyuser:skyuser /app && \
    chmod +x ./scripts/entrypoint.sh

USER skyuser

EXPOSE 8000

CMD ["sh", "scripts/entrypoint.sh"]