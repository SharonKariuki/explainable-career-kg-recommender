# 06. Sprint Log

## Sprint 1: Data Preparation and Development Environment Setup

**Date completed:** 16 September 2026
**Goal:** establish the project foundation (repository, environment, database,
configuration, tests, frontend scaffold, documentation) and genuinely prepare
the O*NET and ESCO data. No recommendation, matching, traversal, scoring,
explanation or skills-gap logic was to be written.

### Completed

| Item | Result |
|---|---|
| Repository structure | Created as specified. Git history on `main`; working branch `develop`. |
| Python environment | `venv/` on Python 3.11.9; 15 pinned direct dependencies install cleanly; `pip check` reports no broken requirements; `import sentence_transformers, networkx, django` succeeds. |
| PostgreSQL | PostgreSQL 17.10 running on 127.0.0.1:5432; role `career_app` (with CREATEDB) owns database `career_recommender`; all migrations applied. |
| Models | Custom `accounts.User`; `profiles.Profile`; `recommendations.Recommendation` with every score term in its own column; `recommendations.Explanation` with structured matched, missing and evidence fields. No occupation or skill tables. |
| API | URL structure under `/api/v1/` with stub views returning HTTP 501 and the sprint in which each is planned. |
| Configuration | `.env.example` lists every variable; `.env` is gitignored; a missing variable stops start-up with a message naming it (tested). Threshold, depth and the three weights are settings, validated for range. |
| Data | O*NET 31.0 text, ESCO v1.1.0 English CSV and the ESCO-O*NET crosswalk downloaded, checksummed and verified. A clean re-download produced identical files. Processed, scope-filtered CSVs written for 24 technology occupations. |
| Scripts | `download_data.py` and `prepare_data.py` working. `build_graph.py` and `build_embeddings.py` have working CLIs, input checks, logging and a documented stage plan, and exit with status 2 ("not implemented"). |
| Tests | `pytest`: 96 passed (43 setup tests, 53 data tests). `black --check` and `flake8` clean. |
| Frontend | Vite React scaffold; `npm run build` succeeds; dev server answers HTTP 200. |
| Documentation | README, `data/README.md` and docs 01 to 06 written. |
| Engine | Five modules containing docstrings only. A test fails if any of them defines a function or class. |

### Observed data

| Raw file | Rows |
|---|---|
| O*NET Occupation Data | 1,016 |
| O*NET Essential Skills | 18,200 |
| O*NET Transferable Skills | 45,500 |
| O*NET Knowledge | 60,060 |
| O*NET Software Skills | 31,821 |
| O*NET Related Occupations | 18,460 |
| O*NET Job Titles | 54,269 |
| O*NET Content Model Reference | 3,006 |
| O*NET Scales Reference | 33 |
| ESCO skills | 13,891 |
| ESCO occupations | 3,008 |
| ESCO occupation-skill relations | 123,852 |
| ESCO skill-skill relations | 5,899 |
| ESCO ICT skills collection | 21 |
| ESCO-O*NET crosswalk (mapping rows) | 4,253 |

Processed (technology scope): 24 occupations, 1,632 rating rows (24 x 68
elements), 5,299 software-skill rows, 299 related-occupation pairs, 1,152 job
titles, 103 crosswalk rows, 7,158 ESCO occupation-skill rows, 856 ESCO skills,
330 ESCO skill relations. Full breakdown in `03-data-sources.md`.

### Decisions and reasons

1. **O*NET 31.0 file names differ from older guides.** There is no
   `Skills.txt` or `Technology Skills.txt`. Skills are split into
   `Essential Skills.txt` (10 elements, `2.A.*`) and `Transferable Skills.txt`
   (25 elements, `2.B.*`), and technology data is in `Software Skills.txt`.
   The data dictionary confirms the rename. The manifest and tests use the
   real names.
2. **ESCO v1.1.0 rather than v1.2.1.** The crosswalk targets v1.1.0, so using
   that release guarantees every crosswalk URI resolves (verified: 0
   unresolved).
3. **The crosswalk links occupations only.** ESCO skills are therefore
   attached through ESCO's own occupation-skill relations. No similarity
   mapping joins the two vocabularies.
4. **Technology scope is an explicit file** (`data/tech_occupations.csv`, 24
   codes) with the evidence for each inclusion, rather than a SOC-prefix
   filter. The 15-* prefix would have pulled in actuaries and mathematicians.
   O*NET has no cloud or machine-learning engineer codes, so O*NET's own
   alternate job titles were used to place those roles.
5. **Crosswalk match types.** Software Developers has only broadMatch (and
   exactISCO) rows, so `build_graph.py` admits all four occupation match types
   by default and keeps the match type on each edge. Weighting by match type is
   a Sprint 2 decision.
6. **Added files beyond the specified tree**, each small and needed:
   `scripts/prepare_data.py` (the download script should not also clean data),
   `scripts/data_manifest.py` (one definition of expected files, shared by the
   script and the tests), `scripts/__init__.py`, `data/tech_occupations.csv`,
   `apps/common_stub.py` (the shared 501 view), `pyproject.toml` and `.flake8`
   (100-character lines for black and flake8), `frontend/README.md`.
7. **Frontend tool: Vite, not Create React App.** Create React App is
   deprecated. The Vite React template is the current standard. It builds into
   `frontend/dist/`, so both `dist/` and `build/` are gitignored.
8. **`Profile` uses `OneToOneField`**, which is a unique foreign key to the
   user, because a user has exactly one profile.
9. **Declared skills and interests are JSON lists of raw strings.** The
   matcher needs the user's own wording, and explanations quote it back.
10. **`Recommendation` also stores `run_id`, `rank` and `scoring_config`.**
    These are needed to reconstruct a ranked list and recompute a score from
    its terms.
11. **`Explanation` also stores `evidence_paths`.** The graph path is the core
    evidence for an explanation.
12. **The missing-penalty weight is a positive number (0.3) that is
    subtracted**, so all three weights can be validated as non-negative.
13. **Starting values** `SIMILARITY_THRESHOLD=0.60` and `MAX_TRAVERSAL_DEPTH=2`
    are placeholders to be tuned in evaluation.
14. **Django 5.2 LTS** is the newest Django release that supports Python 3.11,
    and has long-term support through the project timeline.
15. **PostgreSQL 17 from portable binaries.** No PostgreSQL or Docker was
    installed, and the standard installer needs administrator rights. The EDB
    binaries zip runs as the normal user. The cluster lives in
    `C:\Users\sharo\pgdata17`, outside the repository.
16. **Normalised importance and level** (0 to 1) are computed during
    preparation using bounds read from `Scales Reference.txt`. This is data
    cleaning, not scoring.
17. **`.gitignore` uses `data/raw/**` instead of `data/raw/`.** Git cannot
    re-include a `.gitkeep` inside a directory that is ignored as a whole.
    Verified with `git check-ignore`.

### Problems encountered and resolutions

| Problem | Resolution |
|---|---|
| The O*NET download page does not link the text zip. | The conventional URL `db_31_0_text.zip` was tested and returned the file. |
| Expected O*NET files `Skills.txt` and `Technology Skills.txt` do not exist in 31.0. | Checked the release's data dictionary and used the renamed files (decision 1). |
| The ESCO download page is a JavaScript form. | Found the stable package URL pattern on the form's confirmation page; manual steps documented as a fallback. |
| The crosswalk CSV has 16 metadata lines and a byte-order mark before the header. | `header_offset=16` and `utf-8-sig` encoding in the manifest; a test checks the metadata. |
| No database server on the machine; installer needs admin rights. | Portable PostgreSQL 17.10 binaries (decision 15). |
| `pg_ctl start` kept the shell pipe open and the command appeared to hang. | The server had started; checked with `pg_ctl status`. Documented start and stop commands. |
| No version conflicts during `pip install`. | None needed; `pip check` clean. `transformers` is pinned explicitly (5.17.0) because sentence-transformers depends on it and an unpinned upgrade could change model loading. |
| **An `npm install` ran in the wrong folder** (`C:\Users\sharo`, which already holds an unrelated Node project from 14 September). It re-synced that project's `node_modules` and rewrote its `package-lock.json`. | Not reverted, to avoid damaging that project further. Flagged for the owner to review. The frontend install was then run from inside `frontend/`. |
| `npm --prefix` did not change the install folder under npm 10 on Windows. | Run npm from inside `frontend/`; documented in the setup guide. |
| flake8 flagged long lines in the manifest. | Strings wrapped; `black` and `flake8` both clean. |

### Not done in Sprint 1 (by design)

Recommendation engine, SBERT inference, graph construction and traversal,
scoring, explanation, skills gap, API business logic, frontend screens,
evaluation harness and baselines.

### Sprint 2 starts with

1. **Implement `scripts/build_graph.py`** following its nine documented stages
   and the schema in `04-knowledge-graph-schema.md`. Decide and record how
   `recommend_suppress` rows and ESCO match types are weighted. Add tests for
   node and edge counts and for provenance on every edge.
2. **Implement `scripts/build_embeddings.py`**: first download of
   `all-mpnet-base-v2`, label and alternative-label embeddings, L2
   normalisation, and metadata tying the embeddings to the graph build.
3. **Build the graph and embedding loaders in `engine/graph.py` and
   `engine/matching.py`** with a once-per-process cache. Then run a first
   qualitative check: do "coding" and "programming" land on the same skill
   nodes, and do one- and two-skill profiles reach sensible occupations?
   Also start the synthetic profile set needed for evaluation.

### Handover notes

* Start PostgreSQL after a reboot:
  `C:\Users\sharo\pgsql17\bin\pg_ctl.exe -D C:\Users\sharo\pgdata17 -l C:\Users\sharo\pgdata17\server.log start`
* The superuser (`postgres`) password is in
  `C:\Users\sharo\pgsql17_superuser_password.txt`, outside the repository.
* The application database password is in `.env`.
* The attribution statements for O*NET and ESCO in `03-data-sources.md` must
  appear in the user interface and the final report.
