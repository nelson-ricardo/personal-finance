"""Account repository for database operations on the Account entity."""

from sqlmodel import Session, select

from budget_app.models import Account
from budget_app.schemas import AccountBase


def get_account_by_name(session: Session, account_name: str) -> Account | None:
    """Fetches an account by its unique name.

    Args:
        session: Active SQLModel database session.
        account_name: Name of the account to look up.

    Returns:
        The matching Account instance if found, otherwise None.
    """
    stmt = select(Account).where(Account.name == account_name)
    ret_account = session.exec(stmt).one_or_none()
    return ret_account


def get_account_by_id(session: Session, account_id: int) -> Account | None:
    """Fetches an account by its primary key ID.

    Args:
        session: Active SQLModel database session.
        account_id: Integer ID of the account.

    Returns:
        The matching Account instance if found, otherwise None.
    """
    stmt = select(Account).where(Account.id == account_id)
    ret_account = session.exec(stmt).one_or_none()
    return ret_account


def create_account(session: Session, new_account: AccountBase) -> Account:
    """Instantiates and stages a new Account entity in the session.

    Args:
        session: Active SQLModel database session.
        new_account: AccountBase schema containing account attributes.

    Returns:
        The staged Account instance (uncommitted).
    """
    account_entry = Account.model_validate(new_account)
    session.add(account_entry)
    return account_entry


