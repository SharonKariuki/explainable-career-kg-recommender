# Explainable Knowledge Graph-Driven Career Guidance Recommender

**An Explainable Knowledge Graph-Driven Career Guidance Recommender for the
Cold-Start Recommendation Problem Using Semantic Similarity**

BSc Informatics and Computer Science capstone project, Strathmore University.
Author: Sharon Mugure Kariuki. Supervisor: Mr. Kevin Ochieng Omondi.

## The two research problems

1. **Cold start.** Students and early-career professionals have little or no
   interaction history and often declare only one or two skills. The system
   must still return useful, ranked career recommendations for them.
2. **Explainability.** Every recommendation must be traceable to the evidence
   that produced it. Explanations are generated from that evidence, not
   written separately to sound plausible.

## Approach

* An occupational **knowledge graph** built from O*NET 31.0, with ESCO v1.1.0
  skill vocabulary attached through the official ESCO-O*NET crosswalk.
* **Sentence-BERT** (`sentence-transformers/all-mpnet-base-v2`) matches a
  user's own skill wording to skill nodes in the graph.
* **Breadth-first traversal** moves from matched skills to candidate
  occupations.
* A **transparent additive score** whose separate terms are stored and reused
  to generate the explanation and the skills gap:

  `FinalScore(o) = 0.5 * SkillCoverage(o) + 0.2 * GraphProximity(o) - 0.3 * MissingPenalty(o)`

Scope: 24 technology occupations across software engineering, data science,
cybersecurity, cloud computing and artificial intelligence.

## Tech stack

Python 3.11, Django 5.2 LTS with Django REST Framework, PostgreSQL 17,
NetworkX (in-process graph), sentence-transformers with PyTorch (CPU), NumPy
and pandas, React with Vite, pytest with pytest-django, black and flake8.
Pinned versions are in `requirements.txt`. The reasons for each choice are in
`docs/02-architecture.md`.

## Repository layout

```
career-recommender/
├── README.md, requirements.txt, pytest.ini, manage.py, .env.example
├── docs/            project overview, architecture, data sources,
│                    graph schema, setup guide, sprint log
├── config/          Django settings (all values from environment), URLs, WSGI
├── apps/
│   ├── accounts/          custom user model
│   ├── profiles/          declared skills, education, interests
│   └── recommendations/   stored rankings (one column per score term) and explanations
├── engine/          research core: matching, graph, scoring, explanation,
│                    skills_gap (placeholders in Sprint 1)
├── data/
│   ├── tech_occupations.csv   the 24 occupations in scope
│   ├── raw/                   O*NET and ESCO downloads (gitignored)
│   ├── processed/             cleaned CSVs (gitignored)
│   └── graph/                 graph and embeddings (gitignored)
├── scripts/         download_data, prepare_data, build_graph, build_embeddings
├── tests/           environment and data integrity tests
└── frontend/        React (Vite) scaffold
```

## Setup

Full instructions for Windows and Unix are in `docs/05-setup-guide.md`. In
short:

```bash
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1    Unix: source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env                      # then fill in the values
# create the PostgreSQL role and database (see the setup guide)
python manage.py migrate

python scripts/download_data.py           # O*NET, ESCO and crosswalk
python scripts/prepare_data.py            # data/processed/

cd frontend && npm install && npm run dev
```

## Running tests

```bash
pytest                   # 96 tests: environment, database, config, data integrity
pytest -m "not data"     # skip the checks that need downloaded data
black --check . && flake8
```

## Project status

**Sprint 1 (data preparation and environment setup) is complete.**

* Environment, PostgreSQL schema, configuration and test suite are in place;
  all 96 tests pass.
* O*NET 31.0, ESCO v1.1.0 and the crosswalk are downloaded, verified and
  cleaned into scope-filtered CSVs (see `docs/03-data-sources.md`).
* API routes exist as stubs returning HTTP 501.
* No recommendation, matching, traversal, scoring, explanation or skills-gap
  logic has been written yet.

Next: Sprint 2 builds the knowledge graph and the skill embeddings. See
`docs/06-sprint-log.md`.

## Data attribution

This project includes information from the O*NET 31.0 Database by the U.S.
Department of Labor, Employment and Training Administration (USDOL/ETA), used
under the CC BY 4.0 license. The information has been modified, and USDOL/ETA
has not approved, endorsed, or tested these modifications. O*NET® is a
trademark of USDOL/ETA.

This project uses the ESCO classification of the European Commission.
