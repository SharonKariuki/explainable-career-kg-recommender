"""
Django settings for the career recommender project.

Every credential and every tunable research parameter is read from the
environment. Values are loaded from a `.env` file at the project root by
python-dotenv (variables already present in the process environment take
precedence). Set DJANGO_ENV_FILE to load a different file.

A missing required variable stops start-up with ImproperlyConfigured and a
message naming the variable, rather than failing later with a vague error.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

ENV_FILE = Path(os.environ.get("DJANGO_ENV_FILE", BASE_DIR / ".env"))
load_dotenv(ENV_FILE)


def require_env(name):
    """Return a required environment variable or raise a clear error."""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        raise ImproperlyConfigured(
            f"Required environment variable '{name}' is not set. "
            f"Copy .env.example to .env and fill in a value for {name} "
            f"(looked for an env file at: {ENV_FILE})."
        )
    return value.strip()


def require_float(name):
    raw = require_env(name)
    try:
        return float(raw)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"Environment variable '{name}' must be a number, got '{raw}'."
        ) from exc


def require_int(name):
    raw = require_env(name)
    try:
        return int(raw)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"Environment variable '{name}' must be an integer, got '{raw}'."
        ) from exc


def env_bool(name, default=False):
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# Core

SECRET_KEY = require_env("DJANGO_SECRET_KEY")
DEBUG = env_bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.accounts",
    "apps.profiles",
    "apps.recommendations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database (PostgreSQL only; no SQLite fallback so that development and
# evaluation run against the same engine)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": require_env("DB_NAME"),
        "USER": require_env("DB_USER"),
        "PASSWORD": require_env("DB_PASSWORD"),
        "HOST": require_env("DB_HOST"),
        "PORT": require_env("DB_PORT"),
        "CONN_MAX_AGE": 60,
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Data locations used by the data pipeline and, from Sprint 2, the engine

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
GRAPH_DATA_DIR = DATA_DIR / "graph"

# Recommender parameters. These are tuned during evaluation, so they are
# configuration, never constants in engine code. The missing-skill penalty
# weight is stored as a positive number and subtracted by the scoring
# function: FinalScore = wc*Coverage + wp*Proximity - wm*MissingPenalty.

RECOMMENDER = {
    "SBERT_MODEL_NAME": require_env("SBERT_MODEL_NAME"),
    "SIMILARITY_THRESHOLD": require_float("SIMILARITY_THRESHOLD"),
    "MAX_TRAVERSAL_DEPTH": require_int("MAX_TRAVERSAL_DEPTH"),
    "WEIGHT_SKILL_COVERAGE": require_float("WEIGHT_SKILL_COVERAGE"),
    "WEIGHT_GRAPH_PROXIMITY": require_float("WEIGHT_GRAPH_PROXIMITY"),
    "WEIGHT_MISSING_PENALTY": require_float("WEIGHT_MISSING_PENALTY"),
}

if not 0.0 <= RECOMMENDER["SIMILARITY_THRESHOLD"] <= 1.0:
    raise ImproperlyConfigured("SIMILARITY_THRESHOLD must be between 0 and 1.")
if RECOMMENDER["MAX_TRAVERSAL_DEPTH"] < 1:
    raise ImproperlyConfigured("MAX_TRAVERSAL_DEPTH must be at least 1.")
for _weight in ("WEIGHT_SKILL_COVERAGE", "WEIGHT_GRAPH_PROXIMITY", "WEIGHT_MISSING_PENALTY"):
    if RECOMMENDER[_weight] < 0:
        raise ImproperlyConfigured(f"{_weight} must be non-negative.")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
