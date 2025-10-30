import os, json
from pathlib import Path
from dotenv import load_dotenv
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

USE_EXT_SCHEMA = os.environ.get("USE_EXT_SCHEMA", "0")

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'LKYpe5/J$=h~xD[sfvnLL;gGID9`7,+4(-DKV]AHST:DkooY=*')
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'

# 🌍 Acepta cualquier host (útil si despliegas en Render, Vercel, etc.)
ALLOWED_HOSTS = ["*"]

# =========================================================
# 🔓 CONFIGURACIÓN GLOBAL DE CORS (PERMITIR TODO)
# =========================================================
CORS_ALLOW_ALL_ORIGINS = True  # <- Esto habilita CORS universalmente
CORS_ALLOW_CREDENTIALS = True

# Permite encabezados personalizados
CORS_ALLOW_HEADERS = list(default_headers) + [
    "authorization",
    "content-type",
]

# Confianza CSRF opcional (para cookies/sesiones en frontends)
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://*",  # <- Acepta cualquier dominio HTTPS
]

# =========================================================
# 🧩 APLICACIONES Y MIDDLEWARE
# =========================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'corsheaders',        # <- Debe ir antes de rest_framework
    'rest_framework',

    'seguridad.apps.SeguridadConfig',
    'quality',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # <- Debe ir arriba
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# =========================================================
# ⚙️ CONFIGURACIÓN DE DJANGO / DRF
# =========================================================
ROOT_URLCONF = 'sixsigma_backend.urls'
WSGI_APPLICATION = 'sixsigma_backend.wsgi.application'
ASGI_APPLICATION = 'sixsigma_backend.asgi.application'

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

# =========================================================
# 🗄️ BASE DE DATOS (SQL Server)
# =========================================================
DB_OPTIONS = os.environ.get(
    'DB_OPTIONS',
    '{"driver":"ODBC Driver 18 for SQL Server","extra_params":"Encrypt=yes;TrustServerCertificate=yes;"}'
)

DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': os.environ.get('DB_NAME', 'sixsigma'),
        'USER': os.environ.get('DB_USER', 'sa'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '1433'),
        'OPTIONS': json.loads(DB_OPTIONS),
    }
}

# =========================================================
# 🌎 LOCALIZACIÓN Y CONFIGURACIÓN GENERAL
# =========================================================
LANGUAGE_CODE = 'es'
TIME_ZONE = os.environ.get('TZ', 'America/Guatemala')
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =========================================================
# 🔐 CONFIGURACIÓN DRF + JWT
# =========================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PARSER_CLASSES': ['rest_framework.parsers.JSONParser'],
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
}
