"""
================================================================================
  FILE: dr_project/settings.py
  PURPOSE: Central configuration for the entire Django project.
  All database settings, installed apps, middleware, file paths live here.
================================================================================
"""

import os
from pathlib import Path

# ------------------------------------------------------------------------------
# BASE_DIR: The root folder of our project (where manage.py lives).
# Path(__file__) = this file's location
# .resolve().parent.parent = go up two levels → project root
# ------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------------------
# SECRET_KEY: A long random string Django uses for cryptographic signing
# (sessions, CSRF tokens, etc.). NEVER share this in production.
# ------------------------------------------------------------------------------
SECRET_KEY = 'django-insecure-dr-retinopathy-detection-secret-key-2024-change-in-prod'

# ------------------------------------------------------------------------------
# DEBUG: When True, Django shows detailed error pages. Set False in production.
# ------------------------------------------------------------------------------
DEBUG = True

# ------------------------------------------------------------------------------
# ALLOWED_HOSTS: List of hostnames that can serve this Django app.
# '*' means any host (fine for development, restrict in production).
# ------------------------------------------------------------------------------
ALLOWED_HOSTS = ['*']

# ------------------------------------------------------------------------------
# INSTALLED_APPS: All Django apps (built-in + third-party + our own) that
# Django should load. Order matters for template loading.
# ------------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',        # Admin panel at /admin/
    'django.contrib.auth',         # User authentication system (login/logout)
    'django.contrib.contenttypes', # Framework for generic relations
    'django.contrib.sessions',     # Session management (remembers logged-in user)
    'django.contrib.messages',     # Flash messages (success/error alerts)
    'django.contrib.staticfiles',  # Manages CSS/JS/image files
    'detection',                   # OUR custom app (the main DR detection logic)
]

# ------------------------------------------------------------------------------
# MIDDLEWARE: Functions that process every request/response.
# They run in order for requests, and in reverse for responses.
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',    # Enables sessions
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',               # CSRF protection
    'django.contrib.auth.middleware.AuthenticationMiddleware', # Attaches user to request
    'django.contrib.messages.middleware.MessageMiddleware',    # Enables flash messages
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ------------------------------------------------------------------------------
# ROOT_URLCONF: Tells Django which file contains the main URL routing table.
# ------------------------------------------------------------------------------
ROOT_URLCONF = 'dr_project.urls'

# ------------------------------------------------------------------------------
# TEMPLATES: Configuration for Django's HTML template engine.
# DIRS: Extra folders to search for templates.
# APP_DIRS: Also look in each app's /templates/ subfolder.
# ------------------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Our global templates folder
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',     # Injects 'user' into all templates
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ------------------------------------------------------------------------------
# WSGI_APPLICATION: Entry point for WSGI-compatible web servers (like Gunicorn).
# ------------------------------------------------------------------------------
WSGI_APPLICATION = 'dr_project.wsgi.application'

# ------------------------------------------------------------------------------
# DATABASES: We use SQLite (a file-based database) — perfect for development.
# The database file will be created at BASE_DIR/db.sqlite3
# ------------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ------------------------------------------------------------------------------
# AUTH_PASSWORD_VALIDATORS: Rules for password strength validation.
# ------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ------------------------------------------------------------------------------
# LANGUAGE_CODE / TIME_ZONE: Localization settings.
# ------------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'   # IST timezone (Hyderabad)
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------------------------
# STATIC FILES: CSS, JavaScript, images that don't change per-user.
# STATIC_URL: The URL prefix for static files (e.g., /static/css/style.css)
# STATICFILES_DIRS: Where Django looks for static files during development.
# ------------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Where collectstatic puts files for production

# ------------------------------------------------------------------------------
# MEDIA FILES: User-uploaded files (retinal images in our case).
# MEDIA_URL: URL prefix for uploaded files (e.g., /media/uploads/image.jpg)
# MEDIA_ROOT: Actual folder on disk where uploads are stored.
# ------------------------------------------------------------------------------
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ------------------------------------------------------------------------------
# DEFAULT_AUTO_FIELD: The default type for auto-generated primary key fields.
# BigAutoField = 64-bit integer (handles billions of records).
# ------------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ------------------------------------------------------------------------------
# LOGIN / LOGOUT REDIRECTS:
# After login → go to dashboard. After logout → go to login page.
# ------------------------------------------------------------------------------
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# ------------------------------------------------------------------------------
# MODEL SETTINGS: Path to our saved deep learning model file.
# We define it here so we can easily change it without hunting through code.
# ------------------------------------------------------------------------------
MODEL_PATH = BASE_DIR / 'detection' / 'ml_model' / 'dr_model.pth'
