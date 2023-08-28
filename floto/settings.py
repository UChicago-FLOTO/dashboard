"""
Django settings for floto project.

Generated by 'django-admin startproject' using Django 4.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

from pathlib import Path
import os
import logging

import rest_framework.authentication

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DJANGO_ENV", "DEBUG") == "DEBUG"
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)

if DEBUG:
    ALLOWED_HOSTS = []
else:
    ALLOWED_HOSTS = ["portal.floto.science"]
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'bootstrap5',
    'mozilla_django_oidc',
    'rest_framework',
    'rest_framework.authtoken',
    'floto',
    'floto.api',
    'floto.auth',
    'floto.dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'floto.auth.middleware.UserTokenMiddleware',
]

ROOT_URLCONF = 'floto.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, "floto", "templates"),
        ],
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

WSGI_APPLICATION = 'floto.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

if os.getenv("DB_ENGINE"):
    DATABASES = {
        "default": {
            "ENGINE": os.getenv("DB_ENGINE"),
            "NAME": os.getenv("DB_NAME"),
            "HOST": os.getenv("DB_HOST"),
            "PORT": os.getenv("DB_PORT"),
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_ROOT = "/static"
STATIC_URL = "/static/"


STATICFILES_DIRS = (os.path.join(BASE_DIR, "floto", "static"),)
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO")
LOG_VERBOSITY = os.getenv("DJANGO_LOG_VERBOSITY", "SHORT")
logging.captureWarnings(True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "formatters": {
        "default_short": {
            "format": "[DJANGO] %(levelname)s %(name)s.%(funcName)s: %(message)s"
        },
        "default_verbose": {
            "format": "[DJANGO] %(levelname)s %(asctime)s %(module)s %(name)s.%(funcName)s: %(message)s"
        },
    },
    "handlers": {
        "console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": f"default_{LOG_VERBOSITY.lower()}",
        },
    },
    "loggers": {
        "default": {"handlers": ["console"], "level": "DEBUG"},
        "console": {"handlers": ["console"], "level": "DEBUG"},
        "django": {"handlers": ["console"], "level": "INFO"},
        "py.warnings": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": True,
        },
        "pipeline": {"handlers": ["console"], "level": "INFO"},
    },
}

# Auth
AUTH_USER_MODEL = "floto_auth.KeycloakUser"

AUTHENTICATION_BACKENDS = [
    "mozilla_django_oidc.auth.OIDCAuthenticationBackend",
]

OIDC_RP_SIGN_ALGO = "RS256"
OIDC_OP_JWKS_ENDPOINT="https://auth.floto.science/realms/floto/protocol/openid-connect/certs"
#OIDC_RP_SCOPES = "openid email group role"

OIDC_RP_CLIENT_ID = os.environ['OIDC_RP_CLIENT_ID']
OIDC_RP_CLIENT_SECRET = os.environ['OIDC_RP_CLIENT_SECRET']
OIDC_RP_ADMIN_CLIENT_ID = os.environ['OIDC_RP_ADMIN_CLIENT_ID']
OIDC_RP_ADMIN_CLIENT_SECRET = os.environ['OIDC_RP_ADMIN_CLIENT_SECRET']

OIDC_OP_AUTHORIZATION_ENDPOINT = "https://auth.floto.science/realms/floto/protocol/openid-connect/auth"
OIDC_OP_TOKEN_ENDPOINT = "https://auth.floto.science/realms/floto/protocol/openid-connect/token"
OIDC_OP_USER_ENDPOINT = "https://auth.floto.science/realms/floto/protocol/openid-connect/userinfo"

LOGIN_URL = "oidc_authentication_init"
LOGIN_REDIRECT_URL = "/dashboard"
LOGOUT_REDIRECT_URL = "/"

# Balena variables
BALENA_API_ENDPOINT = os.environ.get("BALENA_API_ENDPOINT")
BALENA_PINE_ENDPOINT = os.environ.get("BALENA_PINE_ENDPOINT")
BALENA_USERNAME = os.environ.get("BALENA_USERNAME")
BALENA_PASSWORD = os.environ.get("BALENA_PASSWORD")
BALENA_TUNNEL_PORT = os.environ.get("BALENA_TUNNEL_PORT")
BALENA_TUNNEL_HOST = os.environ.get("BALENA_TUNNEL_HOST")

# DRF

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        "rest_framework.permissions.IsAuthenticated",
        "floto.api.permissions.IsAdmin",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        'rest_framework.authentication.SessionAuthentication',
    ],
}
