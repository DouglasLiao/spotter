# HaulCast

Compare truck routes using weather forecasts, load weight, and travel time.
Built with Django REST Framework, React, TypeScript, and Leaflet.

Live app: https://haulcast-douglasliao.vercel.app

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

1. Choose origin and destination cities from autocomplete suggestions, or enter
   addresses or coordinates.
2. Set departure time, load weight in pounds, and checkpoint interval (10, 25, or 50 miles).
3. Compare up to three routes and inspect weather risks at each checkpoint's ETA.
4. Explore the corridor heatmap and simulate the selected route through arrival.
   Playback stops at arrival; select Simulate to replay.

The timeline covers at least 48 hours and extends for longer routes. Map forecasts
extend up to 384 hours, with unavailable hours shown as **Unknown**. Simulation can
continue through arrival even when forecasts are unavailable.

Routes are ranked by Severe miles, High miles, average risk, then travel time.
Missing forecasts appear as **Unknown**; routes with incomplete ETA weather are
excluded from recommendations. Routing and weather require internet access.

## Development and deployment

- [Local setup, configuration, and tests](docs/DEVELOPMENT.md)
- [Deploy to Vercel](docs/DEPLOY_VERCEL.md)

Vercel serves the frontend and stateless API under one URL. The `robots.txt` file
asks all crawlers not to crawl the site. The Loom recording is pending.
