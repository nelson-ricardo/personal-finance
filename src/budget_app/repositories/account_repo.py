from budget_app.models.account import Account

from sqlmodel import Session, select

def get_account_by_name(session: Session, account_name: str) -> Account | None:
    stmt = select(Account).where(Account.name == account_name)
    ret_account = session.exec(stmt).one_or_none()
    return ret_account