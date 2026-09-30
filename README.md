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

## Dataset

The processed dataset in `data/processed/` is committed, so nothing needs to be
downloaded to use it. To inspect one occupation (from `backend/`, with the
virtual environment active):

```bash
python -m pipeline.summary "Data Scientists"
```

To rebuild it from the original sources, run the pipeline steps in order:

```bash
python -m pipeline.download     # O*NET 31.0, ESCO v1.1.0, crosswalk -> data/raw/ (checksums verified)
python -m pipeline.onet         # occupations, rated skills and tools
python -m pipeline.esco         # ESCO skills linked through the crosswalk
python -m pipeline.embeddings   # skill label embeddings -> data/cache/ (first run downloads the model)
python -m pipeline.mapping      # which ESCO skills are the same as an O*NET skill
```

| File | Contents |
|---|---|
| `occupations.csv` | The 24 in-scope tech occupations and their domain |
| `onet_skills.csv` | Essential, Transferable and Knowledge ratings; importance and level on 0-1 |
| `onet_tools.csv` | Software tools, weighted 1.0 In Demand / 0.75 Hot Technology / 0.5 other |
| `esco_occupations.csv` | ESCO occupations linked through the ESCO-O*NET crosswalk |
| `esco_occupation_skills.csv` | ESCO skills per occupation, weighted by how consistently they are required |
| `esco_skills.csv` | ESCO skill labels, types and alternative labels |
| `esco_onet_map.csv` | Each ESCO skill's closest O*NET skill; `merged` when similarity is at least 0.90 or the pair is in the hand-checked list in `mapping.py` |

O*NET is licensed under CC BY 4.0 by the U.S. Department of Labor, Employment and
Training Administration. ESCO is published by the European Commission.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at http://localhost:5173/.
