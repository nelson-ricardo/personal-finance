from fastapi import FastAPI
from budget_app.db import get_session

from budget_app.api.routes import accounts, transactions

app = FastAPI(title="Personal Finance API")

app.include_router(accounts.router)
app.include_router(transactions.router)

@app.get("/health")
async def health():
    return {
        "message": "Up and Running!"
    }