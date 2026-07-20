# LNG Fleet Performance Management System

A comprehensive fleet performance monitoring, optimization, and compliance platform for LNG carriers. Built with real-time edge analytics, physics-informed digital twins, and regulatory compliance automation.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   EDGE TIER     │────▶│   CLOUD TIER    │────▶│  FRONTEND TIER  │
│  (Rust/ARM64)   │     │  (Go/Python)    │     │  (React/TS)     │
│                 │     │                 │     │                 │
│ • Modbus/OPC-UA │     │ • API Gateway   │     │ • Fleet Map     │
│ • 1Hz telemetry │     │ • CII Engine    │     │ • CII Dashboard │
│ • Edge analtycs │     │ • EU ETS        │     │ • Voyage View   │
│ • Zstd compress │     │ • ML Inference  │     │ • Alert Center  │
│ • Satellite TX  │     │ • Digital Twin  │     │ • ECA Monitor   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Modules

| Module | Description | Edge | Cloud |
|---|---|---|---|
| **M1** Voyage Optimization | Weather routing, speed/power, JIT arrival | Route validation | Full optimization |
| **M2** Cargo & BOR | Boil-off rate, tank stratification, reliquefaction | BOR calculation | Trend analysis |
| **M3** Hull & Machinery | Engine perf, methane slip, hull fouling | Anomaly detection | Degradation models |
| **M4** CII & Compliance | CII, EU ETS, FuelEU, MRV, SEEMP | Daily CII calc | Full compliance |
| **M5** Digital Twin | Physics-based models, RUL prediction | State estimation | Fleet-wide learning |
| **M6** Charter Party | Speed/consumption verification, claims | Data logging | ISO 15016 correction |
| **M7** ECA Optimization | Fuel switch, scrubber, NOx control | Geofencing | MILP optimization |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Go 1.22+
- Node.js 20+
- Rust 1.77+ (for edge gateway)
- Python 3.12+

### 1. Start Infrastructure

```bash
docker compose up -d postgres redis kafka
```

### 2. Run Database Migrations

```bash
# Applied automatically on postgres first start via migrations/
# Or manually:
PGPASSWORD=lngfleet_dev psql -h localhost -U lngfleet -d lngfleet -f migrations/001_schema.sql
PGPASSWORD=lngfleet_dev psql -h localhost -U lngfleet -d lngfleet -f migrations/002_seed_vessels.sql
```

### 3. Generate Realistic Synthetic Data

```bash
cd synthetic-data-generator
pip install -r requirements.txt
python run.py --csv --db
```

This generates 30 days of realistic data for 10 LNG carriers:
- 20+ real-world voyages (Ras Laffan → Zeebrugge, Sabine Pass → Tokyo, etc.)
- 63,000+ telemetry records (engine, cargo, weather, emissions)
- ECA zone crossings with fuel switch events
- Monthly CII records with A–E ratings
- Charter party speed/consumption verifications

### 4. Start Backend

```bash
go run ./cmd/server
# API available at http://localhost:8080
```

### 5. Start Frontend

```bash
cd frontend
npm run dev
# Dashboard at http://localhost:5173
```

### 6. Train ML Models (Optional)

```bash
cd ml && pip install -r requirements.txt
python -m pipeline.train
python -m pipeline.inference  # Flask API at :5000
```

### 7. Build Edge Gateway (Optional)

```bash
cd edge && cargo build --release
```

## Makefile Targets

| Target | Description |
|---|---|
| `make dev` | Full stack development mode |
| `make up/down` | Start/stop all services |
| `make data-gen` | Generate synthetic data in Docker |
| `make data-gen-local` | Generate synthetic data locally |
| `make ml-train` | Train ML models |
| `make backend` | Run Go backend locally |
| `make frontend` | Run frontend dev server |
| `make edge-build` | Build Rust edge gateway |
| `make test` | Run all tests |
| `make lint` | Lint all code |
| `make clean` | Clean all build artifacts |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/healthz` | Health check |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/api/v1/vessels` | List all vessels |
| `GET` | `/api/v1/vessels/:id` | Vessel details |
| `GET` | `/api/v1/vessels/:id/telemetry` | Telemetry data |
| `GET` | `/api/v1/vessels/:id/cii` | CII records |
| `GET` | `/api/v1/vessels/:id/ets` | EU ETS records |
| `GET` | `/api/v1/vessels/:id/alerts` | Vessel alerts |
| `GET` | `/api/v1/voyages` | List voyages |
| `GET` | `/api/v1/voyages/:id` | Voyage details |
| `GET` | `/api/v1/alerts` | Fleet alerts |
| `POST` | `/api/v1/alerts/:id/acknowledge` | Acknowledge alert |
| `GET` | `/api/v1/dashboard/summary` | Fleet overview |
| `GET` | `/api/v1/dashboard/cii-fleet` | Fleet CII summary |
| `POST` | `/api/v1/telemetry` | Ingest telemetry |
| `POST` | `/api/v1/auth/login` | Get JWT token |

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Edge** | Rust (Tokio, rumqttc, tokio-modbus) | Real-time sensor acquisition & analytics |
| **Backend** | Go (Gin, pgx, Kafka) | REST API, data ingestion, compliance engine |
| **ML** | Python (PyTorch, XGBoost, scikit-learn) | CII forecasting, anomaly detection, RUL |
| **Frontend** | React + TypeScript (deck.gl, MUI, Recharts) | Fleet dashboard & monitoring |
| **Database** | TimescaleDB + PostgreSQL + PostGIS | Time-series sensor data & geospatial |
| **Cache** | Redis | Real-time telemetry cache |
| **Stream** | Apache Kafka | Telemetry ingestion pipeline |
| **Infra** | Docker Compose / Kubernetes | Deployment |

## Regulatory Coverage

- **IMO**: CII (MEPC.352(78)), EEXI, DCS, SEEMP Part III, MARPOL Annex VI
- **EU**: EU ETS (Dir. 2023/959), FuelEU Maritime (Reg. 2023/1805), MRV (Reg. 2015/757)
- **ECA**: Baltic SECA, North Sea SECA, North American ECA, US Caribbean ECA, Mediterranean SOx (2025), California CARB
- **Future**: Mediterranean NOx (2028), Red Sea SOx (2027), IMO Mid-Term Measures

## Project Structure

```
lng-fleet-system/
├── cmd/server/              # Go entry point
├── internal/                # Go internal packages
│   ├── api/                 # HTTP handlers & middleware
│   ├── services/            # Business logic
│   ├── models/              # Data models
│   ├── database/            # DB connections
│   └── config/              # Configuration
├── pkg/                     # Shared Go packages
│   ├── geofencing/          # ECA zone detection
│   ├── weather/             # Open-Meteo client
│   ├── emissions/           # CO₂/NOx/SOx calculator
│   ├── cii/                 # CII calculator
│   ├── bog/                 # BOR estimator
│   └── charterparty/        # Charter verification
├── edge/                    # Rust edge gateway
│   ├── src/                 # Source code
│   └── config/              # Edge config
├── frontend/                # React dashboard
│   └── src/
│       ├── components/      # UI components
│       ├── pages/           # Route pages
│       ├── services/        # API client
│       ├── hooks/           # Custom hooks
│       └── store/           # State management
├── ml/                      # Python ML pipeline
│   ├── pipeline/            # ML models & training
│   ├── data/                # Dataset utilities
│   └── notebooks/           # EDA scripts
├── synthetic-data-generator/ # Realistic data generator
│   └── src/                 # Generator source
├── migrations/              # SQL migrations
├── deploy/                  # Deployment configs
│   ├── docker/              # Dockerfiles
│   └── kubernetes/          # K8s manifests
└── docker-compose.yml       # Local development
```

## License

Proprietary — All rights reserved.
