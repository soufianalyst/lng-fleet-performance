# AGENTS.md — LNG Fleet Performance Management System

## CRITICAL RULES
1. **SURGICAL CHANGES ONLY** — Never rewrite entire files. Use targeted edits (oldString/newString). If a file needs >30% changes, discuss with user first.
2. **PRESERVE EXISTING FEATURES** — Before any change, read the affected file(s), understand the context, and ensure nothing breaks. Run the server and test after changes.
3. **ALWAYS VERIFY** — After changes, curl-test affected API endpoints and confirm the server starts without errors.
4. **CHARTERER-FOCUSED** — The user is a charterer, not an owner. Features should prioritize charterer needs: P&L, CP compliance, bunker costs, BOG losses, off-hire risk, carbon costs, utilization, benchmarking, laytime.
5. **USE LNG EXPERT** — Invoke `@lng-expert` subagent or load `lng-technical-audit` skill when reviewing physics models, sensor data realism, navigation logic, charter party compliance, or any maritime-domain code for technical accuracy.

---

## Available Agents & Skills

### `@lng-expert` Subagent
- **Role:** LNG Shipping Technical Expert (Chief Engineer + Vessel Master)
- **Purpose:** Audits code, data models, physics calculations, and business rules for maritime technical accuracy
- **Access:** Read-only (no edits, no bash) — pure audit and review
- **Use when:** Reviewing sensor data realism, engine performance models, emission factors, navigation logic, charter party compliance, or any maritime-domain accuracy question
- **Config:** `.opencode/agents/lng-expert.md`

### `lng-technical-audit` Skill
- **Role:** Comprehensive LNG carrier technical knowledge base
- **Purpose:** Reference for Chief Engineer systems (ME-GI, X-DF, FGSS, BOG, SFOC, emissions) and Vessel Master operations (navigation, cargo, charter party, stability, safety, environmental compliance)
- **Use when:** Auditing maritime simulation code, sensor data, physics models, or business logic
- **Config:** `.opencode/skills/lng-technical-audit/SKILL.md`

---

## Architecture

- **Backend:** Python 3, FastAPI, SQLite (WAL mode), uvicorn
- **Frontend:** Single-file React 18 SPA (`frontend/build/index.html`), Babel standalone in-browser transpilation, Chart.js 4, Leaflet 1.9.4 (CARTO dark tiles)
- **Entry:** `python -m lng_fleet_performance` → `web.py` → `api/app.py`
- **Server:** `python -m lng_fleet_performance.web --port 8000` (auto-opens browser)

## Project Layout

```
lng_fleet_performance/
├── __init__.py              # Exports DatabaseManager, create_all_tables
├── __main__.py              # Calls web.main()
├── main.py                  # CLI interface (standalone, not used by web)
├── web.py                   # Uvicorn launcher, serves frontend from frontend/build/
├── lng_fleet.db             # SQLite database (auto-created)
├── AGENTS.md                # This file — project memory
├── database/
│   ├── connection.py        # DatabaseManager: execute, fetchone, fetchall, executemany, insert_returning_id, audit_hash, log_audit
│   └── schema.py            # create_all_tables() — 39 tables, 3 indexes
├── models/                  # Dataclass CRUD models (12 classes)
│   ├── vessel.py            # Vessel (29 fields), VesselTank (9 fields)
│   ├── voyage.py            # Voyage (27 fields), VoyageWaypoint (19 fields)
│   ├── cargo.py             # CargoRecord (18 fields), BORDailySummary (12 fields)
│   ├── engine.py            # EnginePerformance (20 fields), AuxiliaryEngine (10 fields)
│   └── compliance.py        # CIIAssessment (22 fields), EUETSRecord (12 fields), FuelEURecord (10 fields)
├── modules/                 # Business logic (10 classes)
│   ├── voyage_optimization.py   # VoyageOptimization: route opt, speed-power, JIT
│   ├── cargo_monitoring.py      # CargoMonitoring: BOR, stratification, rollover
│   ├── hull_machinery.py        # HullMachinery: engine index, fouling, shaft power
│   ├── cii_compliance.py        # CIICompliance: CII calc, EU ETS, FuelEU (454 lines — largest module)
│   ├── digital_twin.py          # DigitalTwin: health, anomalies, simulation
│   ├── charter_party.py         # CharterPartyVerification: ISO 15016 corrections
│   ├── eca_optimization.py      # ECAOptimization: zone compliance, fuel switch, scrubber
│   ├── eexi_compliance.py       # EEXICompliance: EEXI calc, EPL config
│   ├── seemp_compliance.py      # SEEMPCompliance: measures, improvement, DCS
│   └── certificate_manager.py   # CertificateManager: lifecycle, alerts, voyage clearance
├── utils/
│   ├── weather.py           # WeatherEngine: haversine, Holtrop-Mennen, SFOC, isochrone, emissions
│   ├── geofencing.py        # ECAFencing: point-in-polygon, 11 predefined ECA zones (UNIQUE zone_name)
│   └── reporting.py         # ReportGenerator: voyage, CII, ECA, fleet, emissions reports
├── api/                     # FastAPI routers (57 endpoints)
│   ├── app.py               # FastAPI app, CORS, router mounts, /api/health, /api/dashboard
│   ├── deps.py              # Dependency injection: get_db(), init_modules(), get_*() for each module
│   ├── vessels.py           # GET /api/vessels/, GET /api/vessels/{id}
│   ├── voyages.py           # GET /api/voyages/, GET /api/voyages/{id}
│   ├── voyage_opt.py        # 5 endpoints: optimize, speed-power, JIT, fuel, weather
│   ├── cargo.py             # 7 endpoints: BOR, energy, stratification, rollover, reliq, forecast, summary
│   ├── machinery.py         # 5 endpoints: engine, cylinder, fouling, shaft, aux
│   ├── compliance.py        # 14 endpoints: CII, EEXI, EPL, EU ETS, FuelEU (order matters!)
│   ├── eca.py               # 10 endpoints: check, fuel-switch, scrubber, SCR, EGR, IGC, emissions
│   ├── certificates.py      # 4 endpoints: list, alerts, validate, add
│   ├── seemp.py             # 4 endpoints: measures, add, improvement, DCS
│   ├── digital_twin.py      # 6 endpoints: health, hull, BOG, fleet, alerts, scenario
│   ├── charter.py           # 6 endpoints: verify, BOR, weather speed/consumption, audit, record
│   ├── reports.py           # 6 endpoints: voyage, CII, ECA, fleet, emissions, charter
│   ├── map_data.py          # 1 endpoint: GET /api/map/fleet-positions (?vessel_id)
│   ├── fleet_analytics.py   # 6 endpoints: fleet-kpi, fleet-ranking, vessel/fleet timeseries, vessel-comparison, route-stats
│   ├── charterer.py         # 13 endpoints: voyage-pnl, cp-compliance, bunker-costs, bog-impact, offhire-risk, carbon-cost, utilization, voyage-compare, benchmark, laytime
│   └── demo.py              # 2 endpoints: POST generate, POST reset
├── demo/
│   └── generate_data.py     # DemoDataGenerator: 5 vessels, 4 tanks each, 4 voyages each, certs, SEEMP
└── frontend/build/
    └── index.html           # Single-file React SPA (1298 lines)
```

## Database: 39 Tables

vessels, vessel_tanks, voyages, voyage_waypoints, cargo_records, bor_daily_summary, engine_performance, engine_cylinder_data, auxiliary_engines, hull_performance, cii_assessment, eu_ets_records, fueleu_records, emissions_log, eca_events, fuel_switch_log, charter_party, charter_performance, off_hire_events, digital_twin_state, maintenance_events, predictive_alerts, scrubber_data, scr_data, weather_data, sensor_readings, audit_log, certificates, bunkering_records, eca_zones (UNIQUE zone_name), cii_rating_boundaries, eexi_assessment, epl_config, seemp_measures, seemp_reports, egr_data, igc_compliance_log, certificate_expiry_log, eu_ets_surrender

Indexes: idx_sensor_vessel_time, idx_sensor_type_time, idx_audit_table_record

## API Route Ordering (CRITICAL)

In `api/compliance.py`, static routes MUST come before parameterized routes:
1. `/cii/boundaries` (static path) BEFORE `/cii/{vessel_id}`
2. `/eu-ets/summary/{vessel_id}` BEFORE `/eu-ets/{voyage_id}`
3. `/fueleu/trajectory` (static path) BEFORE `/fueleu/{voyage_id}`
4. `/fueleu/annual/{vessel_id}` BEFORE `/fueleu/{voyage_id}`
5. `/epl/verify/{vessel_id}` BEFORE `/epl/{vessel_id}`

In `api/eca.py`, `/check/{lat}/{lon}` must not conflict with other parameterized routes.

## Key Constants

- `FUEL_ENERGY_CONTENT` (in `cii_compliance.py`): HFO/VLSFO: 40200, ULSFO/MGO: 42700, LNG: 50000, B30: 39000 — all in **MJ/tonne** (NOT MJ/kg)
- `PREDEFINED_ECA_ZONES` (in `geofencing.py`): 11 zones, saved with `INSERT OR REPLACE` using UNIQUE(zone_name)
- `CERT_TYPES` (in `certificate_manager.py`): 10 types — IAPP, EIAPP, IEE, ISGOTT, IGC, ISM, ISPS, MLC, CLASS, P&I
- Demo vessels: LNG Atlantic Eagle (ME-GI), LNG Pacific Titan (X-DF), LNG Nordic Voyager (ME-GI), LNG Silk Route (X-DF), LNG Desert Star (ME-GI)

## Known Bugs Fixed (DO NOT REGRESS)

1. **FUEL_ENERGY_CONTENT units**: Must be MJ/tonne (multiplied by 1000 from original MJ/kg values)
2. **eca_zones UNIQUE**: `zone_name` has UNIQUE constraint; `ECAZone.save()` uses INSERT OR REPLACE
3. **CertificateManager.add_certificate**: Uses `insert_returning_id()` not `last_insert_rowid()` because `DatabaseManager.execute()` opens/closes connections per call
4. **Route ordering in compliance.py**: Static paths before parameterized paths
5. **Map initialization**: Uses `createFleetMap()`/`destroyFleetMap()`/`renderFleetPositions()` with proper cleanup on React component unmount
6. **SQLite strftime**: `strftime('%Y-%m-%d', ...)` returns None in SQLite 3.45.3 for large integer timestamps. Use `datetime(ts, 'unixepoch')` + `substr()` instead.
7. **Analytics DB schema**: Raw telemetry tables are per-vessel (`telemetry_lng_001`...`050`). Aggregated tables: `telemetry_daily` uses columns `fuel_consumption_total_kg`, `co2_total_mt`, `sfoc_avg`, `eeoi_avg`, `bog_rate_avg`, `cargo_qty_avg`, `distance_total_nm`. NOT `total_fuel_kg`, `total_co2_mt`, `avg_sfoc` etc.

## Frontend Architecture

- Single HTML file, no build step — Babel standalone transpiles JSX in-browser
- Leaflet CSS loaded in `<head>`, Leaflet JS + Chart.js loaded as plain `<script>` BEFORE React/Babel
- Map functions (`createFleetMap`, `destroyFleetMap`, `renderFleetPositions`) are plain JS globals, called from React effects
- Dashboard uses `key={page}` on `<Page/>` to force remount on navigation
- Map cleanup in `useEffect` return destroys Leaflet instance on unmount
- `useAPI(path, deps)` custom hook for data fetching with loading/error states

## Testing Commands

```bash
# Start server
cd /Users/soufianerahal/Desktop/ERP\ OpenCode/lng_fleet_performance
python -m lng_fleet_performance.web --port 8000

# Test APIs
curl http://localhost:8000/api/health
curl http://localhost:8000/api/dashboard
curl http://localhost:8000/api/vessels/
curl http://localhost:8000/api/map/fleet-positions
curl http://localhost:8000/api/compliance/cii/1
curl http://localhost:8000/api/certificates/1

# Regenerate demo data
curl -X POST http://localhost:8000/api/demo/generate

# Reset database
curl -X POST http://localhost:8000/api/demo/reset
```

## Change Log

- 2025-07-19: Initial CLI system built
- 2025-07-19: FastAPI + React SPA web layer added (57 endpoints, 11 frontend views)
- 2025-07-19: Fleet tracking map with Leaflet (vessel markers, route polylines, popups)
- 2025-07-19: Bug fixes — FUEL_ENERGY_CONTENT units, eca_zones UNIQUE, compliance route ordering, certificate_manager insert_returning_id
- 2025-07-19: Map re-initialization fix — proper Leaflet cleanup on React component unmount, script load order fix
- 2025-07-19: Fleet Analytics API (6 endpoints) + dashboard with fleet KPI, ranking, charts
- 2025-07-19: Data Generator built — 12 generators, 90 fields, 50 vessels × 365 days × 30s = 52.5M records
- 2025-07-19: Aggregation script — hourly/daily rollups to analytics DB
- 2025-07-19: Charterer Analytics — 13 API endpoints + 10 frontend components (Voyage P&L, CP Compliance, Bunker Costs, BOG Impact, Off-Hire Risk, Carbon Cost, Fleet Utilization, Voyage Compare, Market Benchmark, Laytime)
- 2025-07-19: `@lng-expert` subagent created — Chief Engineer + Vessel Master audit expert (read-only, `.opencode/agents/lng-expert.md`)
- 2025-07-19: `lng-technical-audit` skill created — comprehensive LNG carrier technical knowledge base (`.opencode/skills/lng-technical-audit/SKILL.md`)
- 2025-07-19: AGENTS.md comprehensive rewrite — full system documentation, agent/skill references, charterer rules
- 2025-07-19: Data generation killed at ~29% (17.4M rows across 50 vessels, ~122 days each) — used as-is
- 2025-07-19: `aggregate.py` fixed — column mismatches (fuel_consumption_kg_h→cumulative delta, cargo_level_avg→cargo_qty_avg, nox/sox/ch4 units kg→mt×1000, distance_nm→distance_sailed_nm, strftime→datetime for SQLite 3.45 compat), ATTACH-based cross-DB queries, per-table alarm column detection, timestamp offset to realistic dates (2025-07-01+), INSERT placeholder count fix
- 2025-07-19: Analytics API fixes — `fleet_kpi` column names aligned (total_co2_mt→co2_total_mt, total_fuel_kg→fuel_consumption_total_kg, avg_sfoc→sfoc_avg), charterer.py cargo_level_avg→cargo_qty_avg
- 2025-07-19: Analytics DB created — 145K hourly rows, 6K daily rows, 122 fleet daily summaries, 46 MB, date range 2025-07-01 to 2025-10-30
- 2025-07-20: 45 analytics vessels imported into main DB (total 50; name/IMO dedup; tuple-safe access)
- 2025-07-20: Frontend hardcoded `[1,2,3,4,5]` dropdowns removed — HullOverview, SpeedPower, TrimAnalysis now use `/api/vessels/` dynamic dropdowns
- 2025-07-20: `/api/map/fleet-positions` returns all 50 vessels — in-progress voyages use waypoint interpolation; others get static positions from 20-port hash list
- 2025-07-20: vessels.py dedup by composite key (vessel_name, imo_number, propulsion_type) — no duplicates across main+analytics merge
- 2025-07-20: hull_machinery.py analytics fallback — `_get_analytics_hull_data()` converts telemetry_daily→hull_performance format (self-referencing k=shaft_power/speed³ baseline, clamped ±10..25%); wired into fouling, trend, HPI, cleaning, speed-power, trim; vessel ID map `LNG-%03d`
- 2025-07-20: voyage-compare normalizes integer IDs (1→LNG-001); verified 32/32 endpoint sweep passes
- 2025-07-20: **Known schema note**: analytics telemetry_daily speed column is `sog_avg` (NOT `speed_avg`)
- 2025-07-20: **Fleet-level endpoints**: `/api/digital-twin/fleet` (fleet_wide_health for all 50 vessels) and `/api/compliance/cii/fleet` (fleet CII ratings, distribution, best/worst)
- 2025-07-20: **Analytics fallback CII dict normalized**: `_calculate_cii_from_analytics()` now returns `drift_alert`, `projected_cii`, `cii_required_c`, `days_elapsed_in_year`, `fuel_breakdown`, `compliant` keys matching main-DB format (fixed KeyError in drift-alert endpoint)
- 2025-07-20: **Frontend "Fleet (All Vessels)" option** added to DigitalTwin, CIICompliance, HullOverview, SpeedPower, TrimAnalysis — select 0 for fleet aggregate view
- 2025-07-20: **24/24 endpoint sweep passing** (was 21/23; drift-alert 500 fixed, hull/fouling 404 expected — it's part of overview)
- 2025-07-20: **@lng-expert physics audit** — 3 critical, 3 high, 4 medium findings; all critical/high fixed:
  - CII AER denominator: `cargo × distance` → `DWT × distance` (IMO MEPC.338(76))
  - EEXI calculation: GT → DWT, corrected formula `MCR × SFOC × FEC / (DWT × V)`
  - Demo vessel EEXI: 0.76-0.88 → 4.78-4.88 (realistic for LNG carriers)
  - EEXI required table: GT buckets → DWT buckets
  - QPC: 0.85-0.93 → 0.65-0.75 (realistic propulsive efficiency)
  - Baseline roughness: 0.30 → 0.20 mm (post-cleaning baseline)
- 2025-07-20: **Hull fleet comparison** extended — now returns 50 vessels (was 5); includes analytics vessels via `_get_analytics_hull_data()` fallback
- 2025-07-20: **Data generator rewrite + physics audit** — 50 vessels, 110 days, 15.84M raw records, 25 sea-lane routes, voyage lifecycle (laden→discharge→ballast→loading→return), demand-driven fuel (natural BOG + forced boil-off + GCU + MGO changeover), cube-law power-speed, propeller-law RPM, hull fouling growth, storms per region probability
- 2025-07-20: **Physics audit fixes** — CII AER uses DWT (not cargo×1.5), CII boundaries realistic (A:5.05–E:>7.15), EEXI DWT-based, NOx g/kWh units, CO2 no ×0.68 factor, QPC 0.65–0.75, GM 1.7–2.8m, displacement via mass balance, CH4 ME-GI ~135 kg/d vs X-DF ~1,392 kg/d
- 2025-07-20: **`cargo_qty_avg` unit mismatch fix** — aggregate now stores fill percentage (0-100%) instead of metric tons; fixed consumers: cargo.py (direct use), cii_compliance.py (fill%→mt conversion), digital_twin.py (fill%→mt conversion + added `_analytics_fetchone`); charterer.py already expected fill% (thresholds `>30` now correct)
- 2025-07-20: **Post-fix data quality** — laden fill 92-95%, BOR 0.044%/day, EEOI 10.6 g/(t·nm), SFOC 163.9 g/kWh, sea-day fuel 88.8 mt/d, 38/40 endpoints passing (2 are 404 path mismatches, not bugs)
- 2025-07-20: **CII fleet now realistic** — ratings C/D/E instead of all-A; fleet avg CII 7.1, distribution A:2 B:4 C:18 D:20 E:6
- 2025-07-20: **Render deployment prep** — centralized `utils/analytics_db.py` (SQLite/PostgreSQL dual support via DATABASE_URL), `requirements.txt`, `render.yaml`, `scripts/migrate_to_postgres.py`, gunicorn+uvicorn production server verified

## Deployment (Render)

### Setup Steps
1. Push code to GitHub
2. Go to render.com → New → Blueprint
3. Connect GitHub repo → Render detects `render.yaml`
4. Render creates: web service + PostgreSQL database
5. First deploy runs automatically
6. **After first deploy**: run migration to load analytics data:
   ```bash
   # Get DATABASE_URL from Render dashboard → Environment tab
   DATABASE_URL="postgresql://..." python scripts/migrate_to_postgres.py
   ```

### Local Development
```bash
# Start server (with browser auto-open)
cd /Users/soufianerahal/Desktop/ERP\ OpenCode
python -m lng_fleet_performance.web --port 8000

# Production mode (gunicorn)
gunicorn lng_fleet_performance.api.app:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Files for Deployment
- `requirements.txt` — Python dependencies
- `render.yaml` — Render Blueprint config (web service + PostgreSQL)
- `utils/analytics_db.py` — Dual SQLite/PostgreSQL connection (uses DATABASE_URL env var)
- `scripts/migrate_to_postgres.py` — One-time SQLite → PostgreSQL data migration
- `api/app.py` — FastAPI app with frontend serving (catch-all route for SPA)
