# AjiraGuide

An explainable, knowledge-graph-based career guidance recommender.

The repository holds two apps side by side:

- `backend/`: Django REST API (`config` project, `core` app for accounts, skill
  profiles and recommendations), the data pipeline (`pipeline/`) and the
  recommender (`recommender/`)
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
   python manage.py runserver --noreload
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

## Recommender

`backend/recommender/` loads the dataset into an in-memory knowledge graph of
careers and the skills they require, matches a user's skills to graph skills
with SBERT, and ranks careers. From `backend/`:

```bash
python -m recommender.engine Python "machine learning" statistics --top 5
```

Each career is scored as a weighted sum of Coverage (how much of the profile it
requires), ProfileSimilarity (SBERT similarity to its O*NET description) and
GraphProximity (personalised PageRank from the matched skills); the formula is
documented in `recommender/engine.py`. The output shows how each skill was
matched, each career's three components, and the skills behind them. The first
run downloads the SBERT model; after that, loading takes about 20 seconds and a
ranking takes well under a second.

Each recommendation can be explained in plain language and comes with a skills
gap (the career's requirements you did not list, most important first):

```bash
python -m recommender.explanation Python "machine learning" statistics --top 3
python -m recommender.skills_gap Python "machine learning" statistics --top 3
```

Explanations are checked for fidelity (they may only state what the score used)
with `python -m recommender.fidelity`, and scored for completeness and
readability with `python -m recommender.explanation_quality`; the rubric and
results are in `docs/explainability_rubric.md`.

The keyword-matching baseline (no embeddings, no graph) takes the same input:

```bash
python -m recommender.baseline Python "machine learning" statistics --top 5
```

The engine's parameters were chosen by a grid search on synthetic validation
profiles; re-run it (about 3 minutes) with `python -m recommender.tuning`, which
writes every configuration's scores to `data/results/tuning.csv`.

Run the tests from `backend/`:

```bash
python -m pytest
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at http://localhost:5173/.

## Running the web app

Start both apps, each in its own terminal, after the setup steps above:

```bash
# terminal 1, in backend/ with the virtual environment active
python manage.py runserver --noreload

# terminal 2, in frontend/
npm run dev
```

Django loads the knowledge graph and the SBERT model when it starts, so wait
for "Starting development server" (about 20 seconds) before using the app. Use
`--noreload`: Django's auto-reloader checks every loaded module for changes each
second, and once the model libraries are loaded that slows startup to several
minutes. Restart the server yourself after changing backend code. Then
open http://localhost:5173/, create an account, list your skills and choose
**Save and see my careers**. Each career links to its explanation and the
skills you would need to build.

In development Vite forwards `/api` requests to Django on port 8000. If that
port is taken, run Django on another one and tell Vite where it is:

```bash
python manage.py runserver 8010 --noreload           # backend
API_PROXY_TARGET=http://127.0.0.1:8010 npm run dev   # frontend (PowerShell: $env:API_PROXY_TARGET="http://127.0.0.1:8010"; npm run dev)
```

The API, under `/api/`, needs a token from register or login on every other
endpoint:

| Endpoint | Purpose |
|---|---|
| `POST auth/register/`, `POST auth/login/`, `POST auth/logout/`, `GET auth/me/` | Accounts and tokens |
| `GET`, `PUT profile/` | The signed-in user's skills |
| `GET recommendations/?top=N` | Ranked careers with score components |
| `GET recommendations/<career code>/` | One career's explanation, contributing skills and skills gap |
