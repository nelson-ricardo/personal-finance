from decimal import Decimal
import pytest

from budget_app.models import Account, Envelope, Transaction
from budget_app.repositories.account_repo import get_account_by_name
from budget_app.repositories.envelope_repo import (
    get_balance_for_envelope,
    get_envelope_by_name,
)
from budget_app.repositories.transaction_repo import create_transaction
from budget_app.schemas import (
    EnvelopeBase,
    LedgerRequest,
    TransactionRequest,
    TransactionType,
)
from budget_app.services import envelope_service as env_service


class TestCreateEnvelope:
    def test_create_envelope_success(self, session):
        env_info = EnvelopeBase(name="Vacation", note="Savings for trip")
        envelope = env_service.create_envelope(session, env_info)

        assert envelope is not None
        assert envelope.id is not None
        assert envelope.name == "Vacation"
        assert envelope.note == "Savings for trip"
        assert envelope.is_active is True

    def test_create_envelope_empty_name_raises_error(self, session):
        env_info = EnvelopeBase(name="   ")
        with pytest.raises(ValueError, match="Envelope name cannot be empty"):
            env_service.create_envelope(session, env_info)

    def test_create_envelope_duplicate_name_raises_error(self, session):
        env_info = EnvelopeBase(name="Shopping")
        env_service.create_envelope(session, env_info)

        duplicate_info = EnvelopeBase(name="Shopping")
        with pytest.raises(ValueError, match="Envelope already exists"):
            env_service.create_envelope(session, duplicate_info)

    def test_create_envelope_preserves_is_active(self, session):
        env_info = EnvelopeBase(name="InactiveEnv", is_active=False)
        envelope = env_service.create_envelope(session, env_info)

        assert envelope is not None
        assert envelope.is_active is False


class TestAddToCash:
    @pytest.mark.parametrize(
        "amount, source, note",
        [
            (Decimal("500"), "paycheck", "weekly paycheck"),
            (Decimal("1000"), "gift", "gift from a friend"),
        ],
    )
    def test_adding_money(self, session, amount, source, note):
        test_transaction: Transaction = env_service.add_to_cash(
            session, amount=amount, source=source, note=note
        )
        cash_account: Account | None = get_account_by_name(session, "Cash")
        unassigned_envelope: Envelope | None = get_envelope_by_name(session, "Unassigned")

        if cash_account is None:
            raise RuntimeError(
                "System error: default cash account or unassigned envelope does not exist"
            )

        if unassigned_envelope is None:
            raise RuntimeError("System error: default unassigned envelope does not exist")

        assert test_transaction.id is not None
        assert cash_account.current_balance == amount
        assert len(test_transaction.entries) == 1
        assert get_balance_for_envelope(session, unassigned_envelope) == amount

    @pytest.mark.parametrize(
        "amount, source, note",
        [(Decimal("-500"), "payout", "give money to someone")],
    )
    def test_adding_money_negative(self, session, amount, source, note):
        with pytest.raises(ValueError):
            env_service.add_to_cash(session, amount=amount, source=source, note=note)


@pytest.fixture
def transfer_setup(session):
    source: Envelope = env_service.create_envelope(
        session, EnvelopeBase(name="Groceries")
    )
    dest: Envelope = env_service.create_envelope(session, EnvelopeBase(name="Fun"))
    session.flush()

    source_addition: LedgerRequest = LedgerRequest(
        amount=Decimal("500"), envelope_name="Groceries"
    )
    dest_addition: LedgerRequest = LedgerRequest(
        amount=Decimal("100"), envelope_name="Fun"
    )

    tx: TransactionRequest = TransactionRequest(
        merchant="Testing",
        note="For testing purposes only",
        payment_method_name="Cash",
        transaction_type=TransactionType.INCOME,
        ledger_entries=[source_addition, dest_addition],
    )

    master_transaction: Transaction = create_transaction(session, tx)
    session.flush()
    session.refresh(source)
    session.refresh(dest)
    session.refresh(master_transaction)

    return (source, dest, master_transaction)


class TestTransferBetweenEnvelopes:
    def test_transfer_between_envelopes_success(self, session, transfer_setup):
        src, dest, master_tx = transfer_setup

        result = env_service.transfer_between_envelopes(
            session, src.name, dest.name, Decimal("50")
        )

        assert result is not None
        assert len(result.transfer_transaction.entries) == 2
        assert result.new_balance_src == Decimal("450")
        assert result.new_balance_dest == Decimal("150")

    @pytest.mark.parametrize(
        "src_key, dest_key, amount",
        [
            ("src", "src", Decimal("50")),  # Transfer to same envelope
            ("src", "dest", Decimal("-50")),  # Negative transfer amount
            ("src", "dest", Decimal("5000")),  # Amount exceeds available balance
            ("DNE", "src", Decimal("50")),  # Source envelope does not exist
        ],
        ids=["same_envelope", "negative_amount", "over_balance", "envelope_dne"],
    )
    def test_transfer_between_envelopes_validation_failures(
        self, session, transfer_setup, src_key, dest_key, amount
    ):
        src, dest, _ = transfer_setup

        env_map = {
            "src": src.name,
            "dest": dest.name,
            "DNE": "Jibberish",
        }

        with pytest.raises(ValueError):
            env_service.transfer_between_envelopes(
                session, env_map[src_key], env_map[dest_key], amount
            )