# Deployment

The live app is two parts:

| Part | Host | Address |
|---|---|---|
| Frontend (React) | Vercel, project root `frontend/` | https://explainable-career-kg-recommender.vercel.app |
| API (Django + recommender) | Azure Container Apps, image from GitHub Container Registry | `https://<app>.<region>.azurecontainerapps.io` |
| Database | Neon Postgres (free plan) | |

The browser only talks to Vercel. `frontend/vercel.json` forwards every
`/api/...` request to the API, so the frontend keeps calling `/api` exactly as
it does in development and no cross-origin setup is needed.

The API scales to zero when idle. The first request after a quiet spell waits
while the container starts and loads the model (about 30-45 seconds); open the
app a minute before a demo.

## 1. Database (Neon)

1. Create a project at https://neon.tech (free plan, no card). Pick the region
   closest to the Azure region chosen below.
2. From **Connection details**, note the host, database, user and password.

## 2. API image

`.github/workflows/backend-image.yml` builds `backend/Dockerfile` on pull
requests and publishes `ghcr.io/sharonkariuki/ajiraguide-api` when `main`
changes (or when run by hand from the Actions tab).

After the first publish, make the image public so Azure can pull it without a
password: GitHub profile > **Packages** > `ajiraguide-api` > **Package
settings** > **Change visibility** > Public.

## 3. Azure Container Apps

Run these in **Azure Cloud Shell** (the `>_` icon in the Azure portal, Bash),
signed in to the Azure for Students subscription. Fill in the Neon values and a
new secret key (`python -c "import secrets; print(secrets.token_urlsafe(50))"`).

```bash
RG=ajiraguide
LOCATION=southafricanorth   # if the student policy refuses it, try westeurope or northeurope

az provider register --namespace Microsoft.App --wait
az group create -n $RG -l $LOCATION
az containerapp env create -n ajiraguide-env -g $RG -l $LOCATION --logs-destination none

az containerapp create -n ajiraguide-api -g $RG --environment ajiraguide-env \
  --image ghcr.io/sharonkariuki/ajiraguide-api:latest \
  --ingress external --target-port 8000 \
  --cpu 1 --memory 2Gi --min-replicas 0 --max-replicas 1 \
  --secrets django-secret='<secret key>' db-password='<neon password>' \
  --env-vars DJANGO_SECRET_KEY=secretref:django-secret DJANGO_DEBUG=false \
    DJANGO_ALLOWED_HOSTS=.azurecontainerapps.io \
    DB_NAME='<neon database>' DB_USER='<neon user>' DB_PASSWORD=secretref:db-password \
    DB_HOST='<neon host>' DB_PORT=5432 DB_SSLMODE=require \
    GOOGLE_CLIENT_ID='<same client id as frontend/.env>'

az containerapp show -n ajiraguide-api -g $RG --query properties.configuration.ingress.fqdn -o tsv
```

The last command prints the API host. The container applies database
migrations each time it starts.

Check it (expects a 400 with "Google could not confirm that sign-in"):

```bash
curl -X POST -H 'Content-Type: application/json' -d '{"credential":"x"}' https://<api host>/api/auth/google/
```

**Updating the API** after a new image is published:

```bash
az containerapp update -n ajiraguide-api -g ajiraguide --image ghcr.io/sharonkariuki/ajiraguide-api:<commit sha>
```

**Cost.** With `--min-replicas 0` the app only uses compute while serving
requests, which a capstone's traffic keeps inside the monthly free allowance.
Track spending under **Cost Management** on the subscription. To keep it warm
for a grading week, set `--min-replicas 1` with `az containerapp update` and
set it back to 0 afterwards. Deleting the resource group (`az group delete -n
ajiraguide`) removes everything.

## 4. Vercel

1. In `frontend/vercel.json`, replace `BACKEND_HOST` with the API host and merge
   the change to `main`.
2. In the Vercel project, **Settings > Environment Variables**: add
   `VITE_GOOGLE_CLIENT_ID` (the same client id), then redeploy. Vite builds the
   value into the page, so it only takes effect on a new deployment.

## 5. Google sign-in

In Google Cloud Console > **APIs & Services**:

1. **Credentials** > the OAuth web client > **Authorized JavaScript origins**:
   add `https://explainable-career-kg-recommender.vercel.app`, plus
   `http://localhost` and `http://localhost:5173` for local development.
2. **OAuth consent screen**: set the publishing status to **In production**.
   While it is **Testing**, only listed test users can sign in. Sign-in asks
   only for name and email, which needs no Google review.

## 6. Final check

Open the Vercel address in a private window, create an account with a
password, add skills and open a recommendation; then sign out and sign in with
Google.
