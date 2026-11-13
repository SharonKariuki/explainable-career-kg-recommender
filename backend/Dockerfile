# The AjiraGuide API as one container. Build from the repository root, since
# the engine reads data/processed/ beside backend/:
#   docker build -f backend/Dockerfile -t ajiraguide-api .
# PYTHON_IMAGE lets the upstream-drift check build from an exact base-image digest;
# without the build argument the image is built exactly as before.
ARG PYTHON_IMAGE=python:3.11-slim
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.hf

WORKDIR /app/backend

# Every package, transitive ones included, comes from the approved lock (the same file and
# command the ranking-invariance gate uses), so a rebuild cannot pick up newer versions that
# change rankings. torch is the CPU-only wheel: the default one bundles unused GPU libraries.
COPY backend/tests/snapshots/requirements_lock_v1.txt requirements.lock
RUN pip install --no-cache-dir --no-deps -r requirements.lock \
        --extra-index-url https://download.pytorch.org/whl/cpu
# The base image also ships `wheel`, which the lock does not list (upstream-drift run
# 43417955162, #173). Nothing installed needs it outside optional extras, so it is removed,
# and the build stops if the installed packages are not exactly the approved lock.
RUN pip uninstall --yes wheel \
    && python -c "import sys; from importlib import metadata; \
installed = sorted(f'{d.metadata[\"Name\"].lower()}=={d.version}' for d in metadata.distributions() if d.metadata['Name']); \
locked = sorted(l.strip().lower() for l in open('requirements.lock') if l.strip()); \
extra, missing = sorted(set(installed) - set(locked)), sorted(set(locked) - set(installed)); \
sys.exit(f'installed packages differ from the approved lock: extra {extra}, missing {missing}' if extra or missing else 0)"

COPY data/processed /app/data/processed
COPY backend/ .

# Download the SBERT model and encode every skill label now, so a cold start
# only loads files instead of fetching and encoding them. The labels are encoded with the
# ranking-invariance gate's portable arithmetic (one thread, generic torch kernels, MKL in
# compatible mode, OpenBLAS on Haswell, oneDNN off via pin_threads), so the cached vectors are
# the gate's to the last bit whatever CPU builds the image (#173). These variables apply to
# this build step only; the running server's settings are unchanged.
RUN DJANGO_SECRET_KEY=build DB_NAME=x DB_USER=x DB_PASSWORD=x DB_HOST=x DB_PORT=5432 \
    OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
    ATEN_CPU_CAPABILITY=default MKL_CBWR=COMPATIBLE OPENBLAS_CORETYPE=Haswell \
    python -c "import django; import os; os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'; django.setup(); from recommender.invariance import pin_threads; pin_threads(); from core.services import warm_up; warm_up()"

# The admin site's CSS and JS, served by WhiteNoise.
RUN DJANGO_SECRET_KEY=build DB_NAME=x DB_USER=x DB_PASSWORD=x DB_HOST=x DB_PORT=5432     python manage.py collectstatic --noinput

RUN useradd --create-home app && chown -R app /app
USER app

EXPOSE 8000

# One worker keeps a single copy of the model in memory; threads serve requests
# concurrently. --preload loads the model before the port opens.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi --preload --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:8000"]
