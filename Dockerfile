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
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first to leverage caching
COPY requirements.txt .

# Install Python dependencies using BuildKit cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

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