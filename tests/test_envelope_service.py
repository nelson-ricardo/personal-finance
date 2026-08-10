import pytest

from decimal import Decimal

from budget_app.repositories.account_repo import get_account_by_name
from budget_app.repositories.envelope_repo import get_envelope_by_name, get_balance_for_envelope

from budget_app.services import envelope_service as env_service
from budget_app.models.transaction import Transaction
from budget_app.models.account import Account
from budget_app.models.envelope import Envelope

@pytest.mark.parametrize(
        "amount, source, note",
        [
            (Decimal("500"), "paycheck", "weekly paycheck"),
            (Decimal("1000"), "gift", "gift from a friend")
        ]
)
def test_adding_money(session, amount, source, note):
    test_transaction: Transaction = env_service.add_to_cash(
        session, 
        amount=amount, 
        source=source, 
        note=note
    )
    cash_account: Account | None = get_account_by_name(session, "Cash")
    unasiggned_envelope: Envelope | None = get_envelope_by_name(session, "Unassigned")

    if cash_account is None:
        raise RuntimeError("System error: default cash account or unassigned envelope does not exist")

    if unasiggned_envelope is None:
        raise RuntimeError("System error: default unassigned envelope does not exist")
    
    assert test_transaction.id is not None
    print("transaction exists in the database")
    assert cash_account.current_balance == amount
    print("transaction added money to the cash account balance")
    assert len(test_transaction.entries) == 1
    print("transaction has a single entry")
    assert get_balance_for_envelope(session, unasiggned_envelope) == amount
    print("unassigned envelope balance is equal to the amount")

@pytest.mark.parametrize(
        "amount, source, note",
        [
            (Decimal("-500"), "payout", "give money to someone")
        ]
)
def test_adding_money_negative(session, amount, source, note):
    with pytest.raises(ValueError):
        env_service.add_to_cash(session, amount=amount, source=source, note=note)