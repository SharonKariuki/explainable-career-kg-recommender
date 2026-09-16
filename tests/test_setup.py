"""
Environment and configuration sanity tests.

These confirm that the Sprint 1 foundation is in place: settings load from the
environment, PostgreSQL is reachable, migrations produce the expected schema,
critical packages import, and the engine contains no implemented logic yet.
"""

import importlib
import inspect
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings
from django.db import connection

PROJECT_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_ENV_VARS = [
    "DJANGO_SECRET_KEY",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "DB_HOST",
    "DB_PORT",
    "SBERT_MODEL_NAME",
    "SIMILARITY_THRESHOLD",
    "MAX_TRAVERSAL_DEPTH",
    "WEIGHT_SKILL_COVERAGE",
    "WEIGHT_GRAPH_PROXIMITY",
    "WEIGHT_MISSING_PENALTY",
]

CRITICAL_IMPORTS = [
    "django",
    "rest_framework",
    "psycopg2",
    "dotenv",
    "networkx",
    "numpy",
    "pandas",
    "torch",
    "sentence_transformers",
]

ENGINE_MODULES = [
    "engine.matching",
    "engine.graph",
    "engine.scoring",
    "engine.explanation",
    "engine.skills_gap",
]


# Settings


def test_settings_load():
    assert settings.SECRET_KEY
    assert settings.ROOT_URLCONF == "config.urls"
    assert settings.AUTH_USER_MODEL == "accounts.User"
    for app in ("rest_framework", "apps.accounts", "apps.profiles", "apps.recommendations"):
        assert app in settings.INSTALLED_APPS


def test_database_engine_is_postgresql():
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"


@pytest.mark.parametrize("name", REQUIRED_ENV_VARS)
def test_required_environment_variable_present(name):
    assert os.environ.get(name, "").strip(), f"{name} is not set; see .env.example"


def test_recommender_parameters_are_typed_configuration():
    config = settings.RECOMMENDER
    assert config["SBERT_MODEL_NAME"] == os.environ["SBERT_MODEL_NAME"]
    assert isinstance(config["SIMILARITY_THRESHOLD"], float)
    assert 0.0 <= config["SIMILARITY_THRESHOLD"] <= 1.0
    assert isinstance(config["MAX_TRAVERSAL_DEPTH"], int)
    assert config["MAX_TRAVERSAL_DEPTH"] >= 1
    for key in ("WEIGHT_SKILL_COVERAGE", "WEIGHT_GRAPH_PROXIMITY", "WEIGHT_MISSING_PENALTY"):
        assert isinstance(config[key], float)
        assert config[key] >= 0.0


def test_missing_variable_gives_clear_error(tmp_path):
    """Start Django in a clean process without DB_PASSWORD and read the error."""
    env = {k: v for k, v in os.environ.items() if k not in REQUIRED_ENV_VARS}
    for name in REQUIRED_ENV_VARS:
        if name != "DB_PASSWORD":
            env[name] = os.environ[name]
    env["DJANGO_ENV_FILE"] = str(tmp_path / "does-not-exist.env")
    env["DJANGO_SETTINGS_MODULE"] = "config.settings"

    result = subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert "DB_PASSWORD" in result.stderr


def test_env_file_is_gitignored():
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in [line.strip() for line in gitignore]


def test_env_example_lists_every_required_variable():
    text = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    for name in REQUIRED_ENV_VARS:
        assert f"{name}=" in text, f"{name} missing from .env.example"


# Database


@pytest.mark.django_db
def test_database_connection():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        assert cursor.fetchone() == (1,)
    assert connection.vendor == "postgresql"
    assert connection.pg_version >= 140000


@pytest.mark.django_db
def test_schema_tables_exist():
    tables = set(connection.introspection.table_names())
    for table in (
        "accounts_user",
        "profiles_profile",
        "recommendations_recommendation",
        "recommendations_explanation",
    ):
        assert table in tables


@pytest.mark.django_db
def test_no_occupation_or_skill_tables():
    """Occupational knowledge lives in the graph, not in PostgreSQL."""
    tables = set(connection.introspection.table_names())
    assert not any("occupation" in t or "skill" in t for t in tables)


def test_score_components_are_separate_fields():
    from apps.recommendations.models import Explanation, Recommendation

    fields = {f.name for f in Recommendation._meta.get_fields()}
    for name in (
        "occupation_code",
        "final_score",
        "skill_coverage",
        "graph_proximity",
        "missing_penalty",
        "traversal_depth",
        "scoring_config",
    ):
        assert name in fields

    explanation_fields = {f.name for f in Explanation._meta.get_fields()}
    for name in ("text", "matched_skills", "missing_skills", "evidence_paths"):
        assert name in explanation_fields


def test_custom_user_model_in_use():
    from django.contrib.auth import get_user_model

    assert get_user_model()._meta.label == "accounts.User"


# Imports and scaffolding


@pytest.mark.parametrize("module", CRITICAL_IMPORTS)
def test_critical_import(module):
    importlib.import_module(module)


@pytest.mark.parametrize("module", ENGINE_MODULES)
def test_engine_modules_are_placeholders(module):
    """Sprint 1 must not implement engine logic: modules hold docstrings only."""
    imported = importlib.import_module(module)
    assert imported.__doc__ and "Not implemented in Sprint 1" in imported.__doc__
    assert not inspect.getmembers(imported, inspect.isfunction)
    assert not inspect.getmembers(imported, inspect.isclass)


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/auth/register/",
        "/api/v1/profiles/me/",
        "/api/v1/recommendations/",
        "/api/v1/recommendations/1/",
        "/api/v1/recommendations/1/explanation/",
        "/api/v1/recommendations/1/skills-gap/",
    ],
)
def test_api_stubs_return_not_implemented(client, url):
    response = client.get(url)
    assert response.status_code == 501
    assert response.json()["detail"] == "Not implemented."
