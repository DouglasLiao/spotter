# Deploy to Vercel

The root `vercel.json` uses Vercel Services (currently beta) to deploy two native
services in one project. Public routing sends `/api` to Django and other application
paths to React/Vite. API paths remain unchanged, so `/api/routes/plan/` works on the
same origin as the interface. No external backend URL or CORS setup is required.
See [Services](https://vercel.com/docs/services),
[service routing](https://vercel.com/docs/services/routing) and
[Django support](https://vercel.com/docs/frameworks/full-stack/django).

## Publish

1. Commit and push the implementation to `https://github.com/DouglasLiao/spotter`.
2. Import that Git repository in the Vercel dashboard. Keep **Root Directory at the
   repository root**, not `frontend` or `backend`. Use the root `vercel.json` for
   service configuration; leave project-level install/build/output overrides empty.
3. Add `SECRET_KEY` as a sensitive environment variable for both **Preview** and
   **Production**. Generate a unique value, for example with
   `python -c 'import secrets; print(secrets.token_urlsafe(48))'`, and keep it out of Git.
   The app fails startup if the hosted secret is missing.
4. Deploy. React builds with `VITE_API_BASE_URL=/api`. Django uses Python 3.12 and
   `core.wsgi:application`. The API function is configured for a 180-second maximum
   to accommodate external routing and weather calls. Set Node.js 24.x in the
   project settings for the frontend build.
5. Verify the assigned deployment URL: `/` shows the app, `/api/health/` returns
   `{"status":"ok"}`, an invalid POST to `/api/routes/plan/` returns JSON validation
   errors, and `/api/missing/` returns 404 rather than the frontend HTML.
6. Plan a trip, inspect ETA weather, choose another route, and test the forecast
   slider. Add the verified public URL to README.md.

The Vercel integration can publish after it is installed and connected to the user's
account. Alternatively, run the latest Vercel CLI from the repository root, log in,
and deploy a Preview first. Promote to Production after checking it. Local source
changes are not included in Git-based deploys until committed and pushed.

## Environment and stateless runtime

`VERCEL=1` is provided by the platform. In that environment, Django defaults to
`DEBUG=False`, same-origin API access, secure cookies and trusted HTTPS proxy
headers. `VERCEL_URL`, `VERCEL_PROJECT_PRODUCTION_URL` and `VERCEL_BRANCH_URL` populate
allowed hosts and trusted origins. Enable automatic system environment variables
in the Vercel project settings if they were disabled.

For custom domains, set `ALLOWED_HOSTS` to a comma-separated list of additional
hostnames and `CSRF_TRUSTED_ORIGINS` to their full `https://` origins. Do not include
a scheme in `ALLOWED_HOSTS`. External provider overrides (`OSRM_BASE_URL`,
`OPEN_METEO_BASE_URL`, `PHOTON_GEOCODE_URL`, `EXTERNAL_API_TIMEOUT`) remain optional.
Local `.env` files and development artifacts are excluded by `.vercelignore`.

Route planning is stateless and needs no database. In Vercel, the API ignores
session authentication, uses no persistent SQLite file, and does not expose Django
admin. Do not run migrations as a function startup step. Use Docker locally for
admin access. Adding persisted user accounts or saved trips requires an external
database and a corresponding application change.

Checkpoint responses carry ETA weather; only corridor points carry the hourly
forecast series (49 entries by default, extended for longer routes up to 385 entries). Dynamic JSON supports gzip to reduce large responses. Actual
[function duration and payload limits](https://vercel.com/docs/functions/limitations)
still apply; provider failures remain explicit Unknown states.

## Validate locally

```bash
cd backend
venv/bin/python manage.py test
cd ../frontend
npm ci
npm run build
npm run lint
```

With a current Vercel CLI that supports Services, run from the repository root:

```bash
VERCEL=1 SECRET_KEY=local-vercel-validation vercel dev --local
```

`--local` requests local-only development without linking a cloud project. Set the local
`SECRET_KEY` explicitly; do not copy a production secret into shell history. For
the established Docker workflow, use `docker compose up --build -d --wait` and open
http://localhost:8080. Vercel deployments use native runtimes, not the Dockerfiles.

Validation performed locally with Vercel CLI 65.2.0: both services started,
health/validation/404 routing passed, and Chrome completed a real three-route plan
and advanced the slider to +48h without browser errors. The 49 backend tests, frontend
build and lint passed. Cloud build and public URL verification remain pending.
