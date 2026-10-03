# Spotter Fuel Route Planner

A Django backend assessment project that calculates a driving route between two locations in the United States and returns cost-effective fuel stops along that route.

The project also includes an interactive Leaflet map showing the route, start and finish locations, and recommended fuel stops.

## Vehicle assumptions

- Maximum range: **500 miles**
- Fuel efficiency: **10 MPG**
- Tank capacity: **50 gallons**
- Vehicle starts with a **full tank**
- Trip cost includes only fuel purchased during the trip

---

## Features

- Django REST Framework API
- PostgreSQL persistence
- Docker Compose development environment
- Supplied fuel-price CSV import
- Fuel-station coordinate enrichment
- HeiGIT / openrouteservice geocoding and routing
- USA-only start and finish validation
- Cost-effective fuel-stop optimization
- Multiple fuel stops when required
- Full route GeoJSON response
- Compact trip-summary endpoint
- Interactive Leaflet route map
- Swagger / OpenAPI / ReDoc documentation
- Strict request validation
- Bounded retry handling for transient mapping-provider failures
- Automated unit and API tests
- Ruff linting

---

## Technology

- Python 3.13
- Django 6.1.1
- Django REST Framework
- PostgreSQL 18
- psycopg
- httpx
- drf-spectacular
- pytest / pytest-django
- Ruff
- Docker / Docker Compose
- Leaflet 1.9.4

---

## Project structure

```text
config/

trip_planner/
    api/
    domain/
    integrations/
    management/
        commands/
    migrations/
    repositories/
    services/
    templates/
    tests/

docker/
    postgres/

data/
    2026_Gaz_place_national.zip
    fuel-prices-for-be-assessment.csv
```

The implementation separates API concerns, domain logic, external integrations, repository access, orchestration, and presentation.

The fuel optimizer is independent of Django views and external HTTP calls so its core behavior can be tested deterministically.

---

# Quick Start with Docker

## 1. Clone the repository

```bash
git clone https://github.com/isteeakCodeFoundry/spotter-fuel-route.git
cd spotter-fuel-route
```

---

## 2. Create `.env`

Copy:

```text
.env.example
```

to:

```text
.env
```

Example:

```env
DJANGO_SECRET_KEY=replace-with-django-secret-key

DB_NAME=spotter_fuel_route
DB_USER=spotter_app
DB_PASSWORD=replace-with-app-database-password

DB_HOST=localhost
DB_PORT=5433
DB_HOST_PORT=5433

DB_ADMIN_PASSWORD=replace-with-postgres-admin-password

HEIGIT_API_KEY=replace-with-heigit-api-key
```

Use your own local secrets.

Never commit `.env`.

---

## 3. Database credentials

Two separate PostgreSQL credential sets are used.

### PostgreSQL bootstrap administrator

Docker initializes PostgreSQL using the built-in administrator:

```text
postgres
```

Its password comes from:

```env
DB_ADMIN_PASSWORD=replace-with-postgres-admin-password
```

This account is used for PostgreSQL bootstrap only.

Django does not use it for normal application database access.

### Django application role

Django connects using:

```env
DB_USER=spotter_app
DB_PASSWORD=replace-with-app-database-password
```

On the first initialization of a fresh PostgreSQL Docker volume, this script runs automatically:

```text
docker/postgres/init-app-user.sh
```

It creates the application role with:

```text
LOGIN
NOSUPERUSER
NOCREATEDB
NOCREATEROLE
NOREPLICATION
```

and grants it access to the configured database and `public` schema.

The application therefore does not run as the PostgreSQL superuser.

### Database name

The database is configured with:

```env
DB_NAME=spotter_fuel_route
```

PostgreSQL creates this database during initial container bootstrap.

### Important: initialization scripts run only once

PostgreSQL runs files under:

```text
/docker-entrypoint-initdb.d/
```

only when a new database volume is initialized.

Changing any of these values later:

```text
DB_NAME
DB_USER
DB_PASSWORD
DB_ADMIN_PASSWORD
```

does not automatically recreate an existing database or change credentials stored inside an existing PostgreSQL volume.

To intentionally start again with a completely fresh local database:

```bash
docker compose down -v
docker compose up -d db
```

**Warning:** `docker compose down -v` deletes the local PostgreSQL data volume.

---

## 4. Host and Docker database ports

When Django runs directly on the host:

```text
localhost:5433
```

is used.

The `.env` values are:

```env
DB_HOST=localhost
DB_PORT=5433
```

Inside Docker Compose, the `web` service overrides these with:

```text
DB_HOST=db
DB_PORT=5432
```

so Django communicates directly with the PostgreSQL container over the Compose network.

---

## 5. Configure the mapping API

A HeiGIT / openrouteservice API key is required for live geocoding and routing.

Set:

```env
HEIGIT_API_KEY=replace-with-your-heigit-api-key
```

A normal successful request without retries performs approximately three external mapping calls:

1. geocode the start
2. geocode the finish
3. calculate the driving route

Fuel-station selection and fuel optimization run locally.

---

## 6. Build the Django image

```bash
docker compose build web
```

Run this again whenever Python dependencies or Docker build instructions change.

---

## 7. Start PostgreSQL

```bash
docker compose up -d db
```

Check the service:

```bash
docker compose ps
```

Wait until PostgreSQL is healthy before continuing.

---

## 8. Run migrations

```bash
docker compose run --rm web python manage.py migrate
```

The migrations run using the dedicated application database role.

---

## 9. Import the supplied fuel-price dataset

The assessment CSV is included at:

```text
data/fuel-prices-for-be-assessment.csv
```

The Docker image copies the repository to:

```text
/app
```

so the CSV is available in the container at:

```text
/app/data/fuel-prices-for-be-assessment.csv
```

Import it with:

```bash
docker compose run --rm web \
  python manage.py import_fuel_prices \
  /app/data/fuel-prices-for-be-assessment.csv
```

Verified result:

```text
Rows read:          8151
Unique stations:    6738
Price observations: 8151
```

The import is transactional.

All 8,151 price observations from the supplied CSV are persisted.

Where a station has multiple price observations, the runtime repository uses the minimum available retail price for that station when preparing optimizer candidates.

---

## 10. Enrich fuel-station coordinates

The supplied fuel-price CSV does not contain latitude or longitude.

Run:

```bash
docker compose run --rm web \
  python manage.py enrich_fuel_locations
```

The project contains the US Census Gazetteer source at:

```text
data/2026_Gaz_place_national.zip
```

Coordinate enrichment uses:

1. US Census batch address geocoding
2. Census Gazetteer place-centroid fallback

Verified clean-database result:

```text
Total stations:       6738
Geocoded:             6222
Unresolved:            516
```

Breakdown:

```text
Census address matches:       527
Gazetteer city centroids:    5695
Unresolved:                   516
```

Unresolved stations are excluded from route candidate selection.

---

## 11. Start the application

Start Django:

```bash
docker compose up -d web
```

or start the complete stack:

```bash
docker compose up -d
```

---

# Application URLs

Interactive route map:

```text
http://localhost:8000/map/
```

Swagger:

```text
http://localhost:8000/api/docs/
```

ReDoc:

```text
http://localhost:8000/api/redoc/
```

OpenAPI schema:

```text
http://localhost:8000/api/schema/
```

The Docker configuration intentionally uses Django's development server because this repository is a coding-assessment environment, not a production deployment.

---

# API

## Full trip plan

```http
POST /api/v1/trips/plan/
```

Request:

```json
{
  "start": "Chicago, IL",
  "finish": "Dallas, TX"
}
```

The response includes:

- resolved start and finish
- route distance
- route duration
- GeoJSON route geometry
- vehicle assumptions
- selected fuel stops
- station details
- approximate route mile
- approximate distance from route
- gallons to purchase
- fuel price
- cost at each stop
- total gallons purchased
- total fuel-purchase cost
- number of route candidate stations

---

## Compact trip summary

```http
POST /api/v1/trips/plan/summary/
```

Request:

```json
{
  "start": "Chicago, IL",
  "finish": "Dallas, TX"
}
```

The compact endpoint runs the same planner and optimizer as the full endpoint but omits route geometry and other larger response fields.

---

# Verified Example

A clean-database Chicago-to-Dallas request produced:

```text
Route distance:   971.19 miles
Fuel purchased:   47.119 gallons
Fuel stops:       4
Total fuel cost:  $136.03
```

Recommended purchases were:

| Route mile | Station | Location | Gallons | Price/gal | Cost |
|---:|---|---|---:|---:|---:|
| 320 | HUCKS FOOD & FUEL #379 | Marion, IL | 29.500 | $2.92900000 | $86.41 |
| 795 | Quiktrip #7900 | Texarkana, TX | 1.000 | $2.85733333 | $2.86 |
| 805 | EXTRA MILE TRUCK STOP | Hooks, TX | 12.500 | $2.81733333 | $35.22 |
| 930 | CADOO MILLS | Caddo Mills, TX | 4.119 | $2.80066666 | $11.54 |

Exact route geometry and distance can change if the external routing provider changes its routing data or calculation.

---

# Interactive Map

The interactive map is available at:

```text
/map/
```

It:

- accepts start and finish locations
- calls the existing full planning API
- renders the returned GeoJSON route
- marks the start and finish
- marks recommended fuel stops
- displays route distance
- displays gallons purchased
- displays total fuel cost
- lists each recommended purchase

The map contains no separate route-planning or fuel-optimization implementation.

It is a presentation layer over:

```text
POST /api/v1/trips/plan/
```

Leaflet renders the route and markers.

API-returned text such as station names and locations is inserted using DOM `textContent` rather than raw HTML concatenation.

The assessment map uses an OpenStreetMap-compatible tile service for low-volume demonstration use. A production system should use an appropriate production tile provider.

---

# USA-Only Location Validation

Both start and finish locations must resolve within the United States.

Geocoding requests include:

```text
boundary.country=US
```

The returned provider country code is also independently validated.

A non-US provider result is rejected even if the provider unexpectedly returns one.

For example:

```text
Toronto, Canada
```

is rejected.

This behavior has an automated test.

The assessment requirement applies to the start and finish locations. The application does not perform GIS polygon validation against every coordinate in the provider's returned driving route.

---

# Fuel Optimization

The model uses:

```text
Maximum range: 500 miles
Fuel economy:  10 MPG
Tank capacity: 50 gallons
```

The vehicle starts with a full tank.

At each usable station:

- if a cheaper station is reachable ahead, buy only enough fuel to reach the first cheaper station
- otherwise, buy enough to extend useful range toward the destination, subject to tank capacity
- if the current fuel can already reach the destination, buy nothing

Before optimization, the planner verifies that no required gap between the origin, usable stations, and destination exceeds the 500-mile vehicle range.

---

## Stations at the same route mile

Multiple fuel stations can map to approximately the same sampled route position.

They are reduced deterministically using:

1. lowest fuel price
2. shortest approximate distance from route
3. lowest OPIS station ID

---

## Fuel reserve assumption

The assessment specifies a 500-mile maximum range but does not specify a safety reserve.

The optimizer therefore permits arrival with:

```text
0 gallons
```

remaining.

A production implementation would normally use a configurable reserve.

---

# Route Candidate Selection

Fuel stations are matched approximately to the route using:

```text
Route sampling interval: 5 miles
Candidate corridor:      10 miles
```

The returned route geometry is sampled and each geocoded station is compared with the samples using haversine distance.

This avoids requiring PostGIS or another GIS service for the assessment.

---

# Fuel Station Coordinate Accuracy

The supplied price dataset does not provide exact station coordinates.

Verified enrichment produced:

```text
Census address matches:      527
Gazetteer city centroids:   5695
Unresolved:                  516
```

Coordinates marked:

```text
City_Centroid
```

represent the station's city/place centroid, not necessarily its exact pump location.

Therefore:

- route proximity for centroid-based stations is approximate
- candidate inclusion near the corridor boundary is approximate
- map markers may identify a city rather than the exact station
- exact station detour distance cannot be guaranteed
- unresolved stations are excluded

A production implementation should use precise station coordinates when available.

---

# External Provider Resilience

Transient provider transport failures are retried once for:

- connection errors
- read timeouts
- remote protocol errors

The retry is deliberately bounded.

If the second attempt fails, the application returns a provider-unavailable error instead of retrying indefinitely.

---

# Validation and Security

Request input is validated at the DRF serializer boundary.

The API rejects:

- missing required fields
- blank values
- unexpected fields
- oversized location strings
- NUL characters
- control characters
- locations that cannot resolve inside the USA

Whitespace and Unicode are normalized without aggressively stripping legitimate place-name characters.

## Database safety

Normal database access uses the Django ORM.

User-controlled values are not concatenated into SQL.

SQL-like text such as:

```text
' OR 1=1 --
```

is treated as ordinary input rather than executable SQL and is rejected as an invalid location.

## External request safety

Geocoding and routing requests use fixed provider URLs.

User input is supplied through HTTP query parameters and JSON request bodies.

Request data is not turned into shell commands.

The application does not use `eval` or `exec` for request handling.

## Browser output safety

API-returned text is inserted into the map UI through safe DOM text APIs instead of HTML string interpolation.

---

# Secrets

Runtime secrets are loaded from environment variables.

The local:

```text
.env
```

file must never be committed.

Only placeholders should exist in:

```text
.env.example
```

Before making the repository public, verify that no real:

- HeiGIT API key
- Django secret key
- PostgreSQL application password
- PostgreSQL administrator password

exists in tracked files or Git history.

Also ensure secrets do not appear in screenshots or the Loom submission video.

---

# Tests

Run:

```bash
pytest
```

Current verified result:

```text
38 passed
```

Coverage includes:

- request validation
- valid trip requests
- blank and missing input
- unexpected fields
- oversized input
- control characters
- SQL-like input
- USA-only geocoding
- Census address geocoding
- Census Gazetteer lookup
- route geometry
- route sampling
- route candidate selection
- fuel optimization
- range feasibility
- same-route-mile station handling
- external geocoding
- external routing
- transient provider retries
- trip-planner orchestration

External HTTP tests use:

```text
httpx.MockTransport
```

so unit tests do not depend on live third-party APIs.

---

# Ruff

Run:

```bash
ruff check .
```

Expected:

```text
All checks passed!
```

Configuration is stored in:

```text
ruff.toml
```

---

# Local Development with Docker PostgreSQL

Create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Start PostgreSQL:

```powershell
docker compose up -d db
```

PostgreSQL is available from the host at:

```text
localhost:5433
```

Run migrations:

```powershell
python manage.py migrate
```

Run Django:

```powershell
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/map/
```

---

# Useful Commands

Validate Django:

```bash
python manage.py check
```

Run tests:

```bash
pytest
```

Run Ruff:

```bash
ruff check .
```

Validate Compose without printing resolved environment values:

```bash
docker compose config --quiet
```

Build Django:

```bash
docker compose build web
```

Start the stack:

```bash
docker compose up -d
```

Show service status:

```bash
docker compose ps
```

Stop containers:

```bash
docker compose down
```

Recreate PostgreSQL from scratch:

```bash
docker compose down -v
docker compose up -d db
```

---

# Verified Fresh-Bootstrap Flow

The project has been verified through a fresh PostgreSQL volume:

```text
PostgreSQL bootstrap
        ↓
application role creation
        ↓
Django migrations
        ↓
8151 price observations imported
        ↓
6738 unique stations
        ↓
6222 station coordinates resolved
        ↓
route candidate selection
        ↓
fuel optimization
        ↓
live API request
        ↓
interactive Leaflet map
```

The clean-database Chicago-to-Dallas run reproduced:

```text
971.19 miles
4 fuel stops
47.119 gallons purchased
$136.03 total fuel cost
```

---

# Docker Security

The Django image runs as a non-root application user.

The local `.env` is excluded from the image build context.

The build context also excludes development artifacts such as:

```text
.git
.venv
.idea
Python bytecode
pytest cache
Ruff cache
```

The Django database role is separate from the PostgreSQL administrator.

---

# Scope

The solution intentionally avoids unnecessary infrastructure.

Not used:

- Redis
- Celery
- Kafka
- PostGIS
- Kubernetes
- microservices
- React
- separate frontend application

The goal is a focused Django implementation with clear domain logic, reproducible PostgreSQL setup, transparent data limitations, limited external calls, and automated verification.

---

# Production Considerations

A production implementation could add:

- exact fuel-station coordinates
- configurable fuel reserve
- production WSGI/ASGI server
- managed PostgreSQL
- authentication/authorization where required
- rate limiting
- structured logging and observability
- provider fallback
- route caching
- production-grade map tile hosting
- deployment automation

These are deliberately outside the assessment scope.

---

# Author

**By Isteeak Rasul for Spotter**