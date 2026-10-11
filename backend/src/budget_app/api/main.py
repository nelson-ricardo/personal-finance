import os

from fastapi import FastAPI
from budget_app.db import get_session

from budget_app.api.routes import accounts, categories, envelopes, transactions

app = FastAPI(title="Personal Finance API")

app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(envelopes.router)
app.include_router(transactions.router)

@app.get("/health")
async def health():
    return {
        "message": "Up and Running!"
    }


# Development-only wiring. Enabled by backend/dev_server.py (APP_ENV=dev); the
# production app and the test suite never mount these.
if os.getenv("APP_ENV") == "dev":
    from fastapi.middleware.cors import CORSMiddleware

    from budget_app.api.routes import dev

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(dev.router)