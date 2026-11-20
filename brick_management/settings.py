"""
Django settings for brick_management project.
Brick Manufacturing Management System
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-4y1-#9dkgx6s9iq#zh7ak1wm4)zpgmk&0vx7@7susr5ow0ma$f'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# Host Header attack prevention
allowed_hosts_env = os.environ.get('DJANGO_ALLOWED_HOSTS')
if allowed_hosts_env:
    ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(',') if h.strip()]
else:
    ALLOWED_HOSTS = [
        '127.0.0.1',
        'localhost',
        'thamarayyathproduction.pythonanywhere.com',
        '.pythonanywhere.com',
        '*',  # Permissive fallback for local dev & testing
    ]

CSRF_TRUSTED_ORIGINS = [
    'https://thamarayyathproduction.pythonanywhere.com',
    'https://*.pythonanywhere.com',
    'http://127.0.0.1',
    'http://localhost',
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Modular Business Apps
    'accounts.apps.AccountsConfig',
    'products.apps.ProductsConfig',
    'inventory.apps.InventoryConfig',
    'production.apps.ProductionConfig',
    'clients.apps.ClientsConfig',
    'dispatch.apps.DispatchConfig',
    'construction.apps.ConstructionConfig',
    'finance.apps.FinanceConfig',
    'workers.apps.WorkersConfig',
    'reports.apps.ReportsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'brick_management.urls'

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
                'accounts.context_processors.user_role_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'brick_management.wsgi.application'

# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators
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
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Authentication URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================================================================
# SECURITY & SESSION HARDENING
# ==============================================================================
# 1-Hour Session Timeout: Exactly 3600 seconds (1 hour of inactivity)
SESSION_COOKIE_AGE = 3600
# Rolling session: resets timer on every user interaction
SESSION_SAVE_EVERY_REQUEST = True
# Ensure user stays logged in for the 1-hour window even across mobile tab minimizes/reopens
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Session cookie protection against XSS (JavaScript cannot access session id)
SESSION_COOKIE_HTTPONLY = True
# Prevent CSRF attacks via cross-site requests
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# CSRF Security Settings
CSRF_COOKIE_SAMESITE = 'Lax'

# Defense-in-Depth Attack Protection Headers:
# Prohibit embedding in external iframes (Clickjacking protection)
X_FRAME_OPTIONS = 'DENY'
# Prevent browsers from MIME-sniffing response away from declared content-type
SECURE_CONTENT_TYPE_NOSNIFF = True
# Enable browser XSS filter
SECURE_BROWSER_XSS_FILTER = True
# Protect referrer privacy and URL leaks
SECURE_REFERRER_POLICY = 'same-origin'

# PythonAnywhere Reverse Proxy SSL Header
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HTTPS Cookies when running in production (not in DEBUG mode)
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

