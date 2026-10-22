import os

from fastapi import FastAPI

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


# Development and UAT wiring. Enabled in dev or prod (APP_ENV in ("dev", "prod")).
# Hidden routes /dev/checkpoints allow database snapshots and safe rollback.
if os.getenv("APP_ENV") in ("dev", "prod"):
    from fastapi.middleware.cors import CORSMiddleware

    from budget_app.api.routes import dev

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(dev.router)