import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

# Application definition
AUTH_USER_MODEL = 'users.User'

# Auth URL overrides
LOGIN_URL = 'rest_framework:login'
LOGOUT_URL = 'rest_framework:logout'

INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',  # For PostGIS
    
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'channels',
    'corsheaders',
    'django_filters',
    'drf_yasg',  # Swagger
    'django_celery_beat',
    
    # Apps
    'apps.core',
    'apps.users',
    'apps.drones',
    'apps.stream_ingestion',
    'apps.detections',
    'apps.violations',
    'apps.analytics',
    'apps.notifications',
    'apps.vehicle_lookup',
    'apps.compliance',
    'apps.patrols',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'api.wsgi.application'
ASGI_APPLICATION = 'api.asgi.application'

# Database (PostgreSQL + PostGIS)
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': config('DB_NAME', default='skymarshal'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='db'),
        'PORT': config('DB_PORT', default='5432'),
    }
}



# GDAL Fix for Linux/Docker
if os.name == 'posix':
    gdal_lib_paths = [
        '/usr/lib/libgdal.so',
        '/usr/local/lib/libgdal.so',
        '/usr/lib/x86_64-linux-gnu/libgdal.so',
        '/usr/lib/aarch64-linux-gnu/libgdal.so',
    ]
    for path in gdal_lib_paths:
        if os.path.exists(path):
            GDAL_LIBRARY_PATH = path
            break

# Redis
REDIS_URL = config('REDIS_URL', default='redis://redis:6379/0')
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
    }
}

# Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
        },
    },
}

# Celery
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='amqp://guest:guest@rabbitmq:5672//')
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_ROUTES = {
    'stream_ingestion.tasks.*': {'queue': 'default'},
    'computer_vision.tasks.*': {'queue': 'cv_processing'},
    'violations.tasks.*': {'queue': 'citations'},
    'analytics.tasks.*': {'queue': 'analytics'},
}

# JWT Authentication
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'apps.core.drone_authentication.DroneAPIKeyAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'LOGIN_URL': 'rest_framework:login',
    'LOGOUT_URL': 'rest_framework:logout',
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day',
    }
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# CORS
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000').split(',')
CORS_ALLOW_CREDENTIALS = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Storages (Django 5.0+)
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Object Storage (AWS S3) configuration
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'

# SES
AWS_SES_REGION_NAME = config('AWS_SES_REGION_NAME', default='us-east-1')
AWS_SNS_REGION_NAME = config('AWS_SNS_REGION_NAME', default='us-east-1')
EMAIL_BACKEND = 'django_ses.SESBackend'
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@devmetric.dev')

# Kafka
KAFKA_BOOTSTRAP_SERVERS = config('KAFKA_BOOTSTRAP_SERVERS', default='kafka:9092').split(',')
KAFKA_TOPICS = {
    'RAW_FRAMES': 'raw_video_frames',
    'DETECTIONS': 'detection_events',
    'VIOLATIONS': 'violation_events',
    'CITATIONS': 'citation_events',
    'ANALYTICS': 'analytics_events',
}

# Computer Vision
CV_MODELS = {
    'VEHICLE_DETECTION': BASE_DIR / 'models' / 'yolov8n.pt',
    'PLATE_DETECTION': BASE_DIR / 'models' / 'plate_yolov8.pt',
}
CV_CONFIDENCE_THRESHOLD = config('CV_CONFIDENCE_THRESHOLD', default=0.5, cast=float)
CV_SPEED_LIMIT_DEFAULT = config('CV_SPEED_LIMIT_DEFAULT', default=60.0, cast=float)

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}