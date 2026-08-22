from sqlmodel import Session, select

from budget_app.models import Account
from budget_app.schemas import AccountBase


def get_account_by_name(session: Session, account_name: str) -> Account | None:
    stmt = select(Account).where(Account.name == account_name)
    ret_account = session.exec(stmt).one_or_none()
    return ret_account


def get_account_by_id(session: Session, account_id: int) -> Account | None:
    stmt = select(Account).where(Account.id == account_id)
    ret_account = session.exec(stmt).one_or_none()
    return ret_account


def create_account(session: Session, new_account: AccountBase) -> Account:
    account_entry = Account.model_validate(new_account)
    session.add(account_entry)
    return account_entry

