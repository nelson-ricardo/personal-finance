# Personal Budgeting App

A full-stack personal budgeting application featuring envelope budgeting, accounts, categories, and transactions with double-entry mechanics.

- **Backend**: FastAPI, SQLModel / SQLAlchemy, Alembic, PostgreSQL, `uv`
- **Frontend**: SvelteKit 5 (Runes), Tailwind CSS, Vite, `@sveltejs/adapter-node`
- **Infrastructure**: Docker & Docker Compose with multi-stage builds (`dev` and `prod` targets)

---

## 🐳 Docker Deployment (Recommended)

The entire stack (PostgreSQL database, FastAPI backend, and SvelteKit frontend) is containerized and orchestrated via Docker Compose.

You can toggle between **development mode** (with live hot reload and rich seed data) and **production mode** (optimized standalone builds with a clean slate) using the `APP_ENV` environment variable in `.env`.

### 1. Configuration Setup

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

The primary settings in `.env`:
- `APP_ENV=dev` (default): Runs Vite dev server (`:5173`) and FastAPI reload (`:8000`), connected to `budget_app_dev` pre-loaded with the "Alex" demo dataset.
- `APP_ENV=prod`: Runs production Node server (`:3000`) and optimized Uvicorn (`:8000`), connected to `budget_app_prod` initialized with only migrations and system envelopes.

---

### 2. Running in Development Mode (`dev`)

Ensure `.env` has `APP_ENV=dev`:

```bash
docker compose up -d --build
```

- **Frontend**: `http://localhost:5173` (Vite with hot module replacement, live source bind-mounts)
- **Backend API**: `http://localhost:8000` (FastAPI with live code reloading)
- **API Docs**: `http://localhost:8000/docs`
- **Database**: PostgreSQL on port `5432` (`budget_app_dev`)

---

### 3. Running in Production Mode (`prod`)

Set `APP_ENV=prod` in `.env`:

```bash
# In .env:
APP_ENV=prod
DB_NAME=budget_app_prod
BACKEND_TARGET=prod
FRONTEND_TARGET=prod
FRONTEND_PORT=3000
```

Start the containers:

```bash
docker compose up -d --build
```

- **Frontend**: `http://localhost:3000` (Production Node server via `@sveltejs/adapter-node`)
- **Backend API**: `http://localhost:8000` (Production Uvicorn server)
- **Database**: PostgreSQL on port `5432` (`budget_app_prod`)

---

### 4. Checkpoints & UAT Testing

To facilitate User Acceptance Testing (UAT) and experimentation in both `dev` and `prod`, database snapshot and restore tools are accessible at:

👉 `http://localhost:5173/dev/checkpoint` (in dev) or `http://localhost:3000/dev/checkpoint` (in prod)

*(Note: This route is unlinked in the primary navigation for safety).*

#### Available Features:
- **Instant Snapshots**: Click "Create New Checkpoint" to dump the full database state to `./checkpoints/`.
- **Restore & Rollback**: Restore any past checkpoint or built-in template at any time with a single click.
- **Built-in Snapshots**:
  - `alex_seed.json`: Full demo dataset with accounts, envelopes, and 10 weeks of realistic transactions.
  - `clean_slate.json`: Clean baseline with 3 system envelopes (`Unassigned`, `Credit Card Payment`, `Account Adjustment`) and 1 `Cash` account.
  - `blank_slate.json`: Empty schema for isolated unit testing.

Snapshots saved to `./checkpoints/` on the host machine persist across container restarts.

---

## Local Development (Without Docker)

If you prefer to run services natively on the host:

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Backend
```bash
cd backend

# Run the test suite (345 tests)
uv run pytest

# Run dev backend server directly
uv run python main.py --dev

# Run standard/production backend server
uv run python main.py
```
