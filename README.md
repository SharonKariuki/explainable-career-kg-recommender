# AjiraGuide

An explainable, knowledge-graph-based career guidance recommender.

The repository holds two apps side by side:

- `backend/`: Django project (`config`) with a placeholder `core` app
- `frontend/`: React app built with Vite

## Prerequisites

- Python 3.11
- Node.js 22.12 or newer
- PostgreSQL 18 (any recent version works)

## Backend

1. Create the database (you will be asked for the `postgres` user's password):

   ```bash
   psql -U postgres -h localhost -c "CREATE DATABASE ajiraguide"
   ```

2. Create a virtual environment and install the pinned dependencies:

   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in real values. Generate a secret key with:

   ```bash
   python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
   ```

   If PostgreSQL is not on the default port 5432, set `DB_PORT` to match.

4. Apply migrations and start the server:

   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

   The server runs at http://127.0.0.1:8000/.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at http://localhost:5173/.
