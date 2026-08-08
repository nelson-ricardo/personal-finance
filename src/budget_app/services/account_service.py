from sqlmodel import Session

from budget_app.schemas import account as account_schema
from budget_app.models import account as account_db
from budget_app.repositories.account_repo import create_account as create_acc_db

def create_account(session: Session, acc_info: account_schema.AccountBase) -> account_db.Account:
    new_account = create_acc_db(session, acc_info)
    session.commit()
    session.refresh(new_account)
    return new_account