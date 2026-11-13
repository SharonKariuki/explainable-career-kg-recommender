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

# CPU-only PyTorch first: the default wheel bundles GPU libraries the server
# never uses and adds several GB to the image.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY data/processed /app/data/processed
COPY backend/ .

# Download the SBERT model and encode every skill label now, so a cold start
# only loads files instead of fetching and encoding them.
RUN DJANGO_SECRET_KEY=build DB_NAME=x DB_USER=x DB_PASSWORD=x DB_HOST=x DB_PORT=5432 \
    python -c "import django; import os; os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'; django.setup(); from core.services import warm_up; warm_up()"

# The admin site's CSS and JS, served by WhiteNoise.
RUN DJANGO_SECRET_KEY=build DB_NAME=x DB_USER=x DB_PASSWORD=x DB_HOST=x DB_PORT=5432     python manage.py collectstatic --noinput

RUN useradd --create-home app && chown -R app /app
USER app

EXPOSE 8000

# One worker keeps a single copy of the model in memory; threads serve requests
# concurrently. --preload loads the model before the port opens.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi --preload --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:8000"]
