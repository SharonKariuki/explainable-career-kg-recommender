# 02. Architecture

## 1. Layers

```
+-----------------------------------------------------------+
|  Presentation: React (Vite) single-page app  [frontend/]   |
+-----------------------------+-----------------------------+
                              | JSON over HTTP (/api/v1/...)
+-----------------------------v-----------------------------+
|  Application: Django 5.2 + Django REST Framework           |
|    apps/accounts         custom user, authentication       |
|    apps/profiles         declared skills, education        |
|    apps/recommendations  stored rankings and explanations  |
|                                                            |
|    engine/  (same process, imported by the views)          |
|      matching -> graph -> scoring -> explanation, skills_gap|
+--------------+------------------------------+--------------+
               |                              |
+--------------v-------------+  +-------------v---------------+
|  PostgreSQL 17             |  |  In-process knowledge data  |
|  users, profiles,          |  |  NetworkX graph (data/graph)|
|  recommendations,          |  |  NumPy skill embeddings     |
|  explanations              |  |  loaded once per process    |
+----------------------------+  +-----------------------------+
               ^
               | offline, before the server starts
+--------------+---------------------------------------------+
|  Data pipeline [scripts/]                                   |
|  download_data -> prepare_data -> build_graph               |
|                                -> build_embeddings          |
+-------------------------------------------------------------+
```

**Presentation.** A React app built with Vite. It calls the Django API and
contains no recommendation logic. Sprint 1 ships only the default scaffold.

**Application.** Django handles accounts, profiles, persistence and the REST
API. The `engine` package holds the research logic and is called directly by
the recommendation views.

**Data.** PostgreSQL stores what belongs to users: accounts, profiles, and the
recommendations and explanations produced for them. Occupational knowledge
(occupations, skills, technologies and their relationships) lives only in the
NetworkX graph. PostgreSQL references an occupation by its O*NET-SOC code and
has no occupation or skill tables. A test enforces this.

**Pipeline.** Offline scripts turn the raw O*NET and ESCO files into the graph
and embeddings before the server starts. The server never downloads or
rebuilds data.

## 2. Request flow (planned)

1. The user submits a profile (`/api/v1/profiles/me/`).
2. The user requests recommendations (`POST /api/v1/recommendations/`).
3. `engine.matching` encodes each declared skill with SBERT and finds graph
   Skill nodes above `SIMILARITY_THRESHOLD`.
4. `engine.graph` runs a breadth-first search from those nodes, up to
   `MAX_TRAVERSAL_DEPTH`, and returns candidate occupations with their depth
   and path.
5. `engine.scoring` computes SkillCoverage, GraphProximity and MissingPenalty
   for each candidate and combines them with the configured weights.
6. `engine.skills_gap` lists the required skills that were not matched, using
   the same set that fed MissingPenalty.
7. `engine.explanation` fills text templates from the stored evidence.
8. The view saves one `Recommendation` row per ranked occupation (every score
   term in its own column, plus the configuration used) and one `Explanation`
   row each, then returns them.

## 3. API surface (Sprint 1: stubs returning HTTP 501)

| Route | Methods | Purpose | Sprint |
|---|---|---|---|
| `/api/v1/auth/register/` | POST | Create an account | 5 |
| `/api/v1/auth/login/` | POST | Start a session | 5 |
| `/api/v1/auth/logout/` | POST | End a session | 5 |
| `/api/v1/profiles/me/` | GET, PUT, PATCH | Read or update the current profile | 5 |
| `/api/v1/recommendations/` | GET, POST | List or generate recommendations | 3 |
| `/api/v1/recommendations/<id>/` | GET | One recommendation with score terms | 3 |
| `/api/v1/recommendations/<id>/explanation/` | GET | Explanation and evidence | 4 |
| `/api/v1/recommendations/<id>/skills-gap/` | GET | Skills gap | 4 |
| `/admin/` | | Django admin | available |

Each stub answers `{"detail": "Not implemented.", "endpoint": ..., "planned_sprint": N}`.

## 4. Data model (PostgreSQL)

* `accounts.User`: extends Django's `AbstractUser`; email is required and
  unique. It was defined before the first migration because swapping the user
  model later is disruptive.
* `profiles.Profile`: one per user (`OneToOneField`, a unique foreign key).
  `declared_skills` and `interests` are JSON lists of strings, kept exactly as
  typed so explanations can quote the user's own words. Also
  `education_level`, `field_of_study` and `institution`.
* `recommendations.Recommendation`: `run_id` (groups one ranked list),
  `profile`, `occupation_code`, `rank`, `final_score`, `skill_coverage`,
  `graph_proximity`, `missing_penalty`, `traversal_depth`, `scoring_config`
  (weights, threshold, depth and model in force) and `created_at`. Unique
  constraints on (run_id, rank) and (run_id, occupation_code).
* `recommendations.Explanation`: one per recommendation, holding `text`,
  `matched_skills`, `missing_skills` and `evidence_paths` as structured JSON.

The score terms are separate columns so that any stored ranking can be
recomputed and audited from its parts. That is what makes the explanations
checkable rather than decorative.

## 5. Why the engine runs inside Django

The recommendation pipeline is a Python package imported by the Django views,
not a separate service. Reasons:

* **Scale.** The graph covers 24 occupations and about 2,200 nodes. It and the
  embedding matrix fit comfortably in memory, and one process can serve a
  prototype.
* **One language, one deployment.** Django and the engine are both Python. A
  separate service would add a second deployable, an internal API contract,
  network latency and more failure modes, with no research benefit.
* **Traceability.** The view that computes a score is the view that saves it,
  in the same transaction, so the stored evidence always matches what was
  shown to the user.
* **Testability.** Pytest can exercise the engine directly with the same
  configuration Django uses.
* **Separation is still kept.** `engine/` does not import Django models. It
  takes plain inputs and returns plain results, so it could be moved into a
  separate service later without rewriting it.

The model and graph must be loaded once per process, not per request. This is
handled in Sprint 3 with a lazily initialised module-level cache.

## 6. Why NetworkX instead of Neo4j

* The graph is small (thousands of nodes, tens of thousands of edges) and is
  rebuilt offline from files. It is never edited by users.
* Traversal happens in the same process as scoring, with no query language or
  network round trip.
* Neo4j would add a second database server to install, secure, back up and
  keep in sync with PostgreSQL, without improving the research results.
* NetworkX graphs are ordinary Python objects, which makes unit testing,
  inspection and serialisation simple.
* Trade-off accepted: no graph query language and no concurrent writes. If
  the graph later grows to the full O*NET set (about 1,000 occupations), the
  in-memory approach still fits; a graph database would only be reconsidered
  if the graph had to be edited online.

## 7. Configuration

All credentials and tunable parameters come from environment variables loaded
from `.env` (see `.env.example`). `config/settings.py` raises
`ImproperlyConfigured` naming the variable if a required one is missing or
malformed, and validates ranges (threshold between 0 and 1, depth at least 1,
weights non-negative). The engine reads parameters from
`settings.RECOMMENDER`, never from constants. The missing-skill weight is
stored as a positive number and subtracted by the scoring function.

## 8. Technology stack

| Concern | Choice | Version |
|---|---|---|
| Language | Python | 3.11.9 |
| Web framework | Django, Django REST Framework | 5.2.17 (LTS), 3.18.1 |
| Database | PostgreSQL, psycopg2-binary | 17.10, 2.9.13 |
| Graph | NetworkX | 3.6.1 |
| Embeddings | sentence-transformers, PyTorch (CPU), transformers | 6.0.1, 2.14.0, 5.17.0 |
| Data | pandas, NumPy | 3.0.5, 2.4.6 |
| Config | python-dotenv | 1.2.3 |
| Tests and quality | pytest, pytest-django, black, flake8 | 9.1.1, 4.14.0, 26.5.1, 7.3.0 |
| Frontend | React, Vite | 19.2, 8.3 |
