FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libpq-dev \
    gcc \
    g++ \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create media directory
RUN mkdir -p /app/media

COPY . .

RUN useradd -m -u 1000 skyuser && chown -R skyuser:skyuser /app
USER skyuser

RUN chmod +x ./scripts/entrypoint.sh

EXPOSE 8000

CMD ["sh", "scripts/entrypoint.sh"]