# Weather-Aware Truck Routing

A web application built with **Django REST Framework** and **React (Vite + TypeScript)** to help truck drivers choose the safest route based on real-time weather forecasts, load weight, and travel time.

---

## Project Structure

```
spotter/
├── backend/                  # Django REST API
│   ├── core/                 # Django settings & root configuration
│   ├── routing/              # Truck routing & weather risk domain
│   │   ├── services/         # Modular domain services (weather, routing, risk engine)
│   │   └── tests/            # Automated unit and integration tests
│   ├── manage.py
│   └── requirements.txt
├── frontend/                 # React + TypeScript + Vite
│   ├── src/                  # Components, map layers, hooks, styles
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

---

## Getting Started

### 1. Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

To run tests:
```bash
python manage.py test
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will run at `http://localhost:5173` and communicate with the backend at `http://localhost:8000`.
