# 05. Setup Guide

Follow these steps in order on a clean machine. Commands are shown for Windows
(PowerShell) and Unix (macOS or Linux, bash or zsh). Run everything from the
project root, `career-recommender/`, unless a step says otherwise.

## 1. Prerequisites

| Tool | Version used | Check with |
|---|---|---|
| Python | 3.11 (3.11.9 used) | `python --version` |
| Git | any recent | `git --version` |
| PostgreSQL | 14 or newer (17.10 used) | `psql --version` |
| Node.js and npm | Node 20+ (22.14 and npm 10.8 used) | `node --version` |
| Disk space | about 3 GB (PyTorch and data) | |
| Internet | needed for pip, npm and data downloads | |

## 2. Get the code

```bash
git clone <repository-url> career-recommender
cd career-recommender
git checkout develop
```

## 3. Python virtual environment

Windows (PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell refuses to run the activation script, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once. From Git Bash, use
`source venv/Scripts/activate`. From cmd.exe, use `venv\Scripts\activate.bat`.

macOS or Linux:

```bash
python3.11 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On Linux, pip installs the default PyTorch wheel, which includes CUDA
libraries and is large. For a CPU-only install, run this first:
`pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu`.

Check the install:

```bash
pip check
python -c "import sentence_transformers, networkx, django; print('ok')"
```

The first import takes 10 to 20 seconds because PyTorch loads.

**Model weights are not downloaded during setup.** The project uses
`sentence-transformers/all-mpnet-base-v2`. Its weights (about 420 MB) download
automatically from Hugging Face the first time Sprint 2 code loads the model,
and are cached in `~/.cache/huggingface/`.

Deactivate the environment with `deactivate`.

## 4. PostgreSQL

### 4a. Install

* **Windows, with admin rights:** use the EDB installer from
  https://www.postgresql.org/download/windows/ and remember the `postgres`
  password you set.
* **Windows, without admin rights (the method used for this project):**
  download the portable binaries zip, for example
  `https://get.enterprisedb.com/postgresql/postgresql-17.10-1-windows-x64-binaries.zip`,
  and extract it so that `C:\Users\<you>\pgsql17\bin\psql.exe` exists. Then:

  ```powershell
  $pg = "$env:USERPROFILE\pgsql17\bin"
  # Put a strong password in a file first, e.g. $env:USERPROFILE\pgsql17_superuser_password.txt
  & "$pg\initdb.exe" -D "$env:USERPROFILE\pgdata17" -U postgres `
      --pwfile="$env:USERPROFILE\pgsql17_superuser_password.txt" `
      --auth=scram-sha-256 --encoding=UTF8 --locale=C
  & "$pg\pg_ctl.exe" -D "$env:USERPROFILE\pgdata17" -l "$env:USERPROFILE\pgdata17\server.log" start
  ```

  The server listens on 127.0.0.1:5432 only. It does not start automatically
  after a reboot: run the `pg_ctl ... start` line again. Stop it with
  `& "$pg\pg_ctl.exe" -D "$env:USERPROFILE\pgdata17" stop`.
* **macOS:** `brew install postgresql@17 && brew services start postgresql@17`
* **Ubuntu/Debian:** `sudo apt install postgresql && sudo systemctl start postgresql`

### 4b. Create the application role and database

Connect as the superuser (`psql -h 127.0.0.1 -U postgres`; on Linux you may
need `sudo -u postgres psql`) and run:

```sql
CREATE ROLE career_app LOGIN CREATEDB PASSWORD 'choose-a-strong-password';
CREATE DATABASE career_recommender OWNER career_app ENCODING 'UTF8';
```

`CREATEDB` is required because pytest creates and drops a temporary
`test_career_recommender` database on every run.

## 5. Environment variables

```bash
cp .env.example .env        # Windows: Copy-Item .env.example .env
```

Edit `.env`:

* `DJANGO_SECRET_KEY`: generate one with
  `python -c "import secrets; print(secrets.token_urlsafe(50))"`
* `DB_PASSWORD`: the password you gave `career_app`.
* Leave the recommender parameters at their defaults for now.

`.env` is gitignored. If a required variable is missing, any Django command
stops with a message such as:

```
django.core.exceptions.ImproperlyConfigured: Required environment variable
'DB_PASSWORD' is not set. Copy .env.example to .env and fill in a value for
DB_PASSWORD ...
```

## 6. Database schema

```bash
python manage.py check
python manage.py migrate
python manage.py createsuperuser     # optional, for /admin/
```

Confirm the tables exist:

```bash
psql -h 127.0.0.1 -U career_app -d career_recommender -c "\dt"
```

You should see `accounts_user`, `profiles_profile`,
`recommendations_recommendation` and `recommendations_explanation` among the
Django tables.

## 7. Data

```bash
python scripts/download_data.py      # about 24 MB; fetches, extracts and verifies
python scripts/prepare_data.py       # writes data/processed/ and prep_report.json
```

`download_data.py --verify-only` checks files without downloading. If an
automatic download fails, the script prints manual download steps and exits
with status 1; see `docs/03-data-sources.md`. The Sprint 2 scripts can be run
now to check their inputs, but they stop with exit status 2 because they are
not implemented yet:

```bash
python scripts/build_graph.py
python scripts/build_embeddings.py
```

## 8. Tests and code quality

```bash
pytest                    # all tests (about 25 seconds)
pytest -m "not data"      # skip checks that need downloaded data
pytest tests/test_setup.py -v
black --check .
flake8
```

A successful run ends with `96 passed`.

## 9. Run the backend

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/admin/. API routes under `/api/v1/` currently
return HTTP 501 by design.

## 10. Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
npm run build        # output in frontend/dist/
```

Run npm commands from inside `frontend/`. Running `npm install` anywhere else
installs into whichever folder you are in.

## 11. Troubleshooting

| Symptom | Fix |
|---|---|
| `ImproperlyConfigured: Required environment variable ...` | Add the variable to `.env`. |
| `connection refused` on port 5432 | Start PostgreSQL (section 4a). |
| `permission denied to create database` during pytest | `ALTER ROLE career_app CREATEDB;` |
| `password authentication failed` | Check `DB_USER` and `DB_PASSWORD` in `.env`. |
| Data tests fail with "Missing ..." | Run `python scripts/download_data.py` then `python scripts/prepare_data.py`. |
| `'vite' is not recognized` | Run `npm install` inside `frontend/` first. |
