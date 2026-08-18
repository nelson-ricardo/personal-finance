from sqlmodel import Session

from budget_app.models import Account
from budget_app.repositories import account_repo
from budget_app.schemas import AccountBase


def create_account(
    session: Session, acc_info: AccountBase
) -> Account:
    new_account = account_repo.create_account(session, acc_info)
    session.commit()
    session.refresh(new_account)
    return new_account
