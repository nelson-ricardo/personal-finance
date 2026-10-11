# Budget App Backend

FastAPI backend application for personal budgeting.

## Development Mode

To start the backend in dev mode with an isolated frontend testing database:

```bash
uv run python main.py --dev
```

To run standard/production mode:

```bash
uv run python main.py
```

Features:
- Spawns and migrates `budget_db_frontend` and `budget_db_frontend_seed`.
- Seeds realistic financial data via application service layers.
- Enables CORS for `http://localhost:5173`.
- Enables `POST /dev/reset` to restore seeded state.
- Automatically cleans up both databases upon `Ctrl + C` (SIGINT/SIGTERM).

## Running Tests

Tests run strictly against the test database defined in `.env.test`:

```bash
uv run pytest
```
