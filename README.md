# HaulCast

Compare truck routes using weather forecasts, load weight, and travel time.
Built with Django REST Framework, React, TypeScript, and Leaflet.

## Run with Docker

Requires Docker and Docker Compose v2.24 or newer.

```bash
docker compose up --build -d --wait
```

Open http://localhost:8080. Check the API at http://localhost:8080/api/health/.

```bash
docker compose exec backend python manage.py test
docker compose logs -f
docker compose down
```

Rebuild after source changes. Database data persists until you run
`docker compose down -v`.

## How it works

1. Enter the origin, destination, departure time, load weight in pounds, and a
   checkpoint interval of 10, 25, or 50 miles.
2. Compare up to three routes, with weather evaluated at each checkpoint's ETA.
3. Inspect the recommended route, risk summaries, and checkpoints on the map.
4. Explore the corridor heatmap from departure through the next 48 hours.

Routes are ranked by Severe miles, High miles, average risk, then travel time.
Missing forecasts appear as **Unknown**; routes with incomplete ETA weather are
excluded from recommendations. Routing and weather require internet access.

## Development and deployment

- [Local setup, configuration, and tests](docs/DEVELOPMENT.md)
- [Deploy to Vercel](docs/DEPLOY_VERCEL.md)

Vercel serves the frontend and stateless API under one URL. Public deployment and
the Loom recording are pending.
