# Personal Budgeting App

A full-stack personal budgeting application featuring envelope budgeting, accounts, categories, and transactions with double-entry mechanics.

- **Backend**: FastAPI, SQLModel / SQLAlchemy, Alembic, PostgreSQL, `uv`
- **Frontend**: SvelteKit 5 (Runes), Tailwind CSS, Vite

---

## Quick Start (Full-Stack Dev Mode)

To spin up both the backend API and the frontend in development mode simultaneously:

```bash
cd frontend
npm run dev
```

### What happens behind the scenes:
1. **Isolated Frontend Database**: Spawns an isolated Postgres database (`budget_db_frontend`) exclusively for frontend testing/development. Your testing database (`budget_db_test`) is never touched.
2. **Schema & Bootstrap Migration**: Automatically runs all Alembic migrations (`alembic upgrade head`) and executes `init_db` to register default system categories and envelopes.
3. **Realistic Service-Seeded Data**:
   - Accounts: `Cash`, `Chase Sapphire` (Credit Card), `Amex Blue` (Credit Card), `Honda Civic Loan` (Loan with initial balance).
   - Envelopes: Rent, Utilities, Phone Bill, Groceries, Gas, Household, Skincare, Dining Out, Entertainment, Emergency Fund, Vacation, plus financing & loan envelopes.
   - Dynamic Timeline: Transactions backdated starting 2 months prior to the current date across ~10 weeks of realistic financial activity (paychecks, multi-envelope transactions like Target/Costco, transfers, interest charges, debt payoff, financed laptop).
   - Includes one deliberate overspend on `Dining Out` for testing negative envelope balance UI styling.
4. **Pristine Snapshot & Reset**: A template database (`budget_db_frontend_seed`) is created right after seeding.
5. **Clean Exit**: Pressing `Ctrl + C` sends a termination signal which intercepts shutdown, tears down both `budget_db_frontend` and `budget_db_frontend_seed`, leaving your Postgres instance clean.

---

## Development Endpoints

When running in dev mode (`APP_ENV=dev`):

- **Backend API**: `http://localhost:8000` (Docs: `http://localhost:8000/docs`)
- **Frontend**: `http://localhost:5173`
- **Reset Database**:
  ```bash
  curl -X POST http://localhost:8000/dev/reset
  ```
  Calling `POST /dev/reset` instantly reverts all mutations (creations, deletions, balance changes) made by the frontend back to the initial seeded state. Note: this endpoint is strictly disabled outside of dev mode.

---

## Running Backend Independently

If you want to run backend tests or standalone API:

```bash
cd backend

# Run the test suite (uses budget_db_test)
uv run pytest

# Run dev backend server directly
uv run python main.py --dev

# Run standard/production backend server
uv run python main.py
```
