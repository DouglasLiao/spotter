# Spotter frontend

React, TypeScript, Vite, and Leaflet interface for weather-aware truck routing.

## Run locally

Start the Django API first, then run:

```bash
npm ci
cp .env.example .env
npm run dev
```

Open http://localhost:5173. Set `VITE_API_BASE_URL` in `.env` to change the API URL.
The example points to `http://localhost:8000/api`.

## Checks

```bash
npm run build
npm run lint
npx playwright install chromium
npm run test:e2e
```

The browser tests cover desktop and mobile layouts. API responses and map tiles
are mocked for repeatable checks.

See the [project README](../README.md), [development guide](../docs/DEVELOPMENT.md),
and [Vercel guide](../docs/DEPLOY_VERCEL.md) for the complete setup.
