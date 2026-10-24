# Local development

The repository contains a Django API in `backend/` and a React/Vite application in
`frontend/`. Use Docker for a complete local setup, or run both services directly
for hot reload.

## Docker

From the repository root:

```bash
docker compose up --build -d --wait
```

Open http://localhost:8080. Nginx serves React and forwards `/api/` to
Django/Gunicorn. Migrations and static file collection run at backend startup.
SQLite data and admin static files use named Docker volumes. The Docker database
is separate from `backend/db.sqlite3`.

Optional configuration:

```bash
cp .env.docker.example .env
```

The root `.env` controls `FRONTEND_PORT`, `SECRET_KEY`, and `ALLOWED_HOSTS`.
`backend/.env`, when present, supplies external provider settings. Compose overrides
debug, CORS, database path, secret key, and allowed hosts. The frontend image builds
with `VITE_API_BASE_URL=/api`. Local environment files are excluded from build contexts.

```bash
docker compose logs -f
docker compose exec backend python manage.py test
docker compose exec backend python manage.py createsuperuser
docker compose down
```

Containers require a rebuild after source changes. `docker compose down` keeps the
database; `docker compose down -v` deletes it. The default port binds to localhost.

The root `Dockerfile` provides an optional image containing both frontend and
backend. Vercel uses the native services in `vercel.json` instead.

## Backend without Docker

Use Python 3.12. From the repository root:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver 8000
```

The API runs at http://localhost:8000/api. Provider settings are documented in
`backend/.env.example`; the default providers do not require API keys.

## Frontend without Docker

Use Node.js 24. In a separate terminal:

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

Open http://localhost:5173. `VITE_API_BASE_URL` defaults to the value copied from
`.env.example`: `http://localhost:8000/api`.

## Checks

Run backend tests from `backend/` with the virtual environment activated:

```bash
python manage.py test
```

Run frontend checks from `frontend/`:

```bash
npm run build
npm run lint
npx playwright install chromium
npm run test:e2e
```

If Chrome is already installed, an alternative is:

```bash
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/google-chrome npm run test:e2e
```

Browser tests cover desktop and mobile layouts with mocked API responses and map
tiles. Backend integration tests mock external HTTP while exercising the routing,
weather, risk, and recommendation services. These tests do not guarantee provider
availability or a particular frame rate on every device.

See the [Vercel guide](DEPLOY_VERCEL.md) for native service validation and deployment.
