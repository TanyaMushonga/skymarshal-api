# SkyMarshal API

A comprehensive Django REST API for intelligent aerial traffic monitoring, featuring real-time drone fleet management, computer vision-powered vehicle detection, speed monitoring, automated violation processing, and compliance tracking.

## Features

### 🚁 Drone Fleet Management

- **Drone Registration & Tracking** - Register drones with unique IDs, models, and serial numbers
- **Real-time GPS Tracking** - Track drone locations with PostGIS geographic data support
- **Battery & Signal Monitoring** - Live status updates including battery level and signal strength
- **API Key Authentication** - Secure ESP32-CAM drone authentication with auto-generated keys

### 👮 User Management & Authentication

- **Role-Based Access Control** - Admin, Officer, and Dispatcher roles
- **Two-Factor Authentication** - SMS-based 2FA for enhanced security
- **JWT Authentication** - Secure API access with token-based auth
- **Officer Certification Tracking** - Pilot license and certification management

### 🎥 Video Stream Ingestion

- **RTSP Stream Support** - Ingest live video feeds from surveillance drones
- **Kafka Integration** - Real-time frame processing via message queues
- **Session Management** - Track active streaming sessions per patrol

### 🔍 Computer Vision Processing

- **YOLOv8 Vehicle Detection** - Real-time detection of cars, trucks, motorcycles, and buses
- **License Plate Recognition (ALPR)** - Automatic plate detection with EasyOCR
- **Speed Estimation** - Perspective-transformed speed calculations
- **Detection Storage** - Persist all detections with location and confidence data

### ⚠️ Violation Management

- **Automatic Violation Creation** - Generated from speed/detection events
- **Evidence Pack Storage** - Video clips and image snapshots for each violation
- **Citation Workflow** - NEW → PROCESSED → CITATION_SENT → DISMISSED status flow
- **Fine Calculation** - Configurable fine amounts per violation type

### 🏅 Compliance & Incentive System

- **Safe Driving Points** - Reward compliant drivers with points
- **Lottery Events** - Periodic drawings for drivers meeting minimum point thresholds
- **Vehicle Registration Database** - Track vehicle status (Active, Expired, Stolen, Suspended)

### 📧 Multi-Channel Notifications

- **Real-time WebSocket** - Django Channels for instant push notifications
- **Email via AWS SES** - Automated email alerts
- **SMS via AWS SNS** - Text message notifications
- **Notification Types** - Stream health, mission updates, system alerts

### 📊 Analytics & Reporting

- **Admin Analytics** - System-wide statistics and insights
- **Officer Analytics** - Individual performance metrics
- **Period Filtering** - Daily, weekly, monthly, and custom date ranges

## Tech Stack

| Component            | Technology                                     |
| -------------------- | ---------------------------------------------- |
| **Framework**        | Django 5.0, Django REST Framework 3.14         |
| **Database**         | PostgreSQL 15 with PostGIS                     |
| **Caching**          | Redis 7                                        |
| **Message Queue**    | RabbitMQ 3.12 (Celery), Kafka 7.5 (CV streams) |
| **WebSockets**       | Django Channels with Redis backend             |
| **Computer Vision**  | YOLOv8 (Ultralytics), OpenCV, EasyOCR          |
| **Cloud Services**   | AWS S3, SES, SNS via boto3                     |
| **Monitoring**       | Sentry, Flower (Celery monitoring)             |
| **Web Server**       | Nginx, Gunicorn, Daphne (ASGI)                 |
| **Containerization** | Docker, Docker Compose                         |

## Project Structure

```
skymarshal-api/
├── api/                     # Django project settings & WSGI/ASGI config
│   ├── settings.py
│   ├── urls.py              # Main URL router
│   ├── celery.py            # Celery configuration
│   └── asgi.py              # ASGI config for WebSockets
├── apps/
│   ├── core/                # Shared utilities, pagination, Kafka config
│   ├── users/               # User management & authentication
│   ├── drones/              # Drone fleet management
│   ├── patrols/             # Patrol mission management
│   ├── stream_ingestion/    # RTSP video stream handling
│   ├── detections/          # CV detection records
│   ├── violations/          # Traffic violation processing
│   ├── vehicle_lookup/      # Vehicle registration database
│   ├── compliance/          # Compliance scores & lottery
│   ├── notifications/       # Multi-channel notifications
│   └── analytics/           # Dashboard analytics
├── computer_vision/         # YOLOv8 detection pipeline
├── docker-compose.yml       # Multi-service orchestration
├── Dockerfile
├── requirements.txt
└── nginx.conf
```

## API Endpoints

### Authentication

| Method | Endpoint                               | Description            |
| ------ | -------------------------------------- | ---------------------- |
| POST   | `/api/v1/auth/login/admin/`            | Admin login            |
| POST   | `/api/v1/auth/login/officer/`          | Officer login          |
| POST   | `/api/v1/auth/verify-2fa/`             | Verify 2FA code        |
| POST   | `/api/v1/auth/password-reset/confirm/` | Confirm password reset |

### Drones

| Method | Endpoint                             | Description         |
| ------ | ------------------------------------ | ------------------- |
| GET    | `/api/v1/drones/`                    | List all drones     |
| POST   | `/api/v1/drones/`                    | Register new drone  |
| GET    | `/api/v1/drones/{id}/`               | Get drone details   |
| PUT    | `/api/v1/drones/{id}/`               | Update drone        |
| POST   | `/api/v1/drones/{id}/update-status/` | Update drone status |
| POST   | `/api/v1/drones/{id}/update-gps/`    | Update GPS location |

### Patrols

| Method | Endpoint                | Description       |
| ------ | ----------------------- | ----------------- |
| GET    | `/api/v1/patrols/`      | List patrols      |
| POST   | `/api/v1/patrols/`      | Start new patrol  |
| PUT    | `/api/v1/patrols/{id}/` | End/update patrol |

### Detections & Violations

| Method | Endpoint                   | Description             |
| ------ | -------------------------- | ----------------------- |
| GET    | `/api/v1/detections/`      | List all detections     |
| GET    | `/api/v1/violations/`      | List all violations     |
| PUT    | `/api/v1/violations/{id}/` | Update violation status |

### Streams

| Method | Endpoint                      | Description             |
| ------ | ----------------------------- | ----------------------- |
| GET    | `/api/v1/streams/`            | List video streams      |
| POST   | `/api/v1/streams/`            | Register new stream     |
| POST   | `/api/v1/streams/{id}/start/` | Start streaming session |
| POST   | `/api/v1/streams/{id}/stop/`  | Stop streaming session  |

### Compliance & Lottery

| Method | Endpoint                                | Description            |
| ------ | --------------------------------------- | ---------------------- |
| GET    | `/api/v1/compliance/scores/`            | List compliance scores |
| GET    | `/api/v1/compliance/lottery/`           | List lottery events    |
| POST   | `/api/v1/compliance/lottery/{id}/draw/` | Execute lottery draw   |

### Vehicles

| Method | Endpoint                           | Description              |
| ------ | ---------------------------------- | ------------------------ |
| GET    | `/api/v1/vehicles/`                | List registered vehicles |
| GET    | `/api/v1/vehicles/{plate}/lookup/` | Lookup vehicle by plate  |

### Notifications

| Method    | Endpoint                           | Description             |
| --------- | ---------------------------------- | ----------------------- |
| GET       | `/api/v1/notifications/`           | List user notifications |
| POST      | `/api/v1/notifications/{id}/read/` | Mark as read            |
| WebSocket | `/ws/notifications/`               | Real-time notifications |

### Analytics

| Method | Endpoint                     | Description           |
| ------ | ---------------------------- | --------------------- |
| GET    | `/api/v1/analytics/admin/`   | Admin dashboard stats |
| GET    | `/api/v1/analytics/officer/` | Officer metrics       |

### Documentation

| Endpoint    | Description         |
| ----------- | ------------------- |
| `/swagger/` | Swagger UI          |
| `/redoc/`   | ReDoc documentation |

## Getting Started

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- PostgreSQL 15 with PostGIS extension
- Redis 7
- RabbitMQ 3.12
- Kafka (optional, for CV streams)

### Local Development

1. **Clone the repository**

   ```bash
   git clone https://github.com/TanyaMushonga/skymarshal-api.git
   cd skymarshal-api
   ```

2. **Create environment file**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Create and activate virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

5. **Run database migrations**

   ```bash
   python manage.py migrate
   ```

6. **Create superuser**

   ```bash
   python manage.py createsuperuser
   ```

7. **Start development server**
   ```bash
   python manage.py runserver
   ```

### Docker Deployment

Start the full stack with Docker Compose:

```bash
docker-compose up -d
```

This starts the following services:

- **web** - Django application (port 8000)
- **db** - PostgreSQL database (port 5432)
- **redis** - Redis cache (port 6379)
- **rabbitmq** - Message broker (ports 5672, 15672)
- **kafka** - Stream processing (port 9092)
- **zookeeper** - Kafka coordinator (port 2181)
- **celery** - Background task workers
- **celery-beat** - Scheduled tasks
- **computer_vision** - CV processing service
- **detection_consumer** - Kafka detection consumer
- **flower** - Celery monitoring (port 5555)
- **nginx** - Reverse proxy (ports 80, 443)

### Environment Variables

Key environment variables (see `.env.example`):

```bash
# Database
DB_NAME=skymarshal
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# AWS (for notifications)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
```

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for further details.

## Contributing

Contributions are welcome. Please refer to [CONTRIBUTING.md](CONTRIBUTING.md) for submission guidelines.
