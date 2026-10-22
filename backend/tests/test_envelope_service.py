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
    AccountBase,
    AccountType,
    EnvelopeBase,
    EnvelopeSplitRequest,
    EnvelopeUpdate,
    EnvelopeWithBalance,
    SystemEnvelopeType,
    TransactionRequest,
    TransactionType,
)
from budget_app.services import account_service
from budget_app.services import envelope_service as env_service
from budget_app.services import transaction_service as tx_service


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

    def test_create_envelope_starting_balance_is_zero(self, session):
        env_info = EnvelopeBase(name="ZeroBalEnv")
        envelope = env_service.create_envelope(session, env_info)
        assert get_balance_for_envelope(session, envelope) == Decimal("0")


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

    source_addition: EnvelopeSplitRequest = EnvelopeSplitRequest(
        amount=Decimal("500"), envelope_name="Groceries"
    )
    dest_addition: EnvelopeSplitRequest = EnvelopeSplitRequest(
        amount=Decimal("100"), envelope_name="Fun"
    )

    tx: TransactionRequest = TransactionRequest(
        merchant="Testing",
        note="For testing purposes only",
        payment_method_name="Cash",
        transaction_type=TransactionType.INCOME,
        splits=[source_addition, dest_addition],
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

    def test_assign_to_envelope_success(self, session):
        env_service.add_to_cash(session, Decimal("1000"), "Paycheck")
        env_service.create_envelope(
            session, EnvelopeBase(name="Dining Out")
        )

        result = env_service.assign_to_envelope(
            session, destination="Dining Out", amount=Decimal("250")
        )

        assert result is not None
        assert result.source.name == "Unassigned"
        assert result.destination.name == "Dining Out"
        assert result.new_balance_src == Decimal("750")
        assert result.new_balance_dest == Decimal("250")
        assert len(result.transfer_transaction.entries) == 2

    def test_assign_to_unassigned_raises_error(self, session):
        env_service.add_to_cash(session, Decimal("500"), "Income")
        with pytest.raises(
            ValueError, match="source cannot equal destination"
        ):
            env_service.assign_to_envelope(
                session, destination="Unassigned", amount=Decimal("100")
            )

    def test_assign_empty_destination_raises_error(self, session):
        env_service.add_to_cash(session, Decimal("500"), "Income")
        with pytest.raises(
            ValueError, match="destination envelope cannot be empty"
        ):
            env_service.assign_to_envelope(
                session, destination="   ", amount=Decimal("100")
            )

    def test_assign_zero_or_negative_amount_raises_error(self, session):
        env_service.add_to_cash(session, Decimal("500"), "Income")
        env_service.create_envelope(session, EnvelopeBase(name="Rent"))

        with pytest.raises(
            ValueError, match="amount cannot be 0 or negative"
        ):
            env_service.assign_to_envelope(
                session, destination="Rent", amount=Decimal("0")
            )

        with pytest.raises(
            ValueError, match="amount cannot be 0 or negative"
        ):
            env_service.assign_to_envelope(
                session, destination="Rent", amount=Decimal("-50")
            )

    def test_assign_nonexistent_destination_raises_error(self, session):
        env_service.add_to_cash(session, Decimal("500"), "Income")
        with pytest.raises(
            ValueError, match="destination envelope 'NonExistent' does not exist"
        ):
            env_service.assign_to_envelope(
                session, destination="NonExistent", amount=Decimal("100")
            )

    def test_assign_insufficient_unassigned_balance_raises_error(self, session):
        env_service.add_to_cash(session, Decimal("100"), "Small Paycheck")
        env_service.create_envelope(session, EnvelopeBase(name="Bills"))

        with pytest.raises(
            ValueError, match="amount too high, can transfer up to .* from Unassigned"
        ):
            env_service.assign_to_envelope(
                session, destination="Bills", amount=Decimal("500")
            )

    def test_alias_transfer_from_unassigned(self, session):
        env_service.add_to_cash(session, Decimal("500"), "Income")
        env_service.create_envelope(session, EnvelopeBase(name="Gym"))

        result = env_service.transfer_from_unassigned(
            session, destination="Gym", amount=Decimal("75")
        )
        assert result.new_balance_src == Decimal("425")
        assert result.new_balance_dest == Decimal("75")


class TestDeactivateEnvelope:
    def test_deactivate_envelope_zero_balance_success(self, session):
        env = env_service.create_envelope(session, EnvelopeBase(name="Subscriptions"))
        assert env.is_active is True

        deactivated = env_service.deactivate_envelope(session, "Subscriptions")
        assert deactivated.is_active is False

    def test_deactivate_envelope_strips_whitespace(self, session):
        env_service.create_envelope(session, EnvelopeBase(name="Online Courses"))
        deactivated = env_service.deactivate_envelope(session, "  Online Courses  ")
        assert deactivated.is_active is False

    def test_deactivate_already_inactive_returns_envelope(self, session):
        env = env_service.create_envelope(
            session, EnvelopeBase(name="OldProject", is_active=False)
        )
        assert env.is_active is False

        result = env_service.deactivate_envelope(session, "OldProject")
        assert result.id == env.id
        assert result.is_active is False

    def test_deactivate_envelope_with_positive_balance_raises_error(self, session):
        env_service.add_to_cash(session, Decimal("500"), "Income")
        env_service.create_envelope(session, EnvelopeBase(name="Dining"))
        env_service.assign_to_envelope(
            session, destination="Dining", amount=Decimal("100")
        )

        with pytest.raises(
            ValueError, match="has a balance .* needs to be zero before deactivating"
        ):
            env_service.deactivate_envelope(session, "Dining")

    def test_deactivate_unassigned_raises_error(self, session):
        with pytest.raises(
            ValueError, match="Cannot deactivate system envelope 'Unassigned'"
        ):
            env_service.deactivate_envelope(session, "Unassigned")

    def test_deactivate_credit_card_payment_raises_error(self, session):
        with pytest.raises(
            ValueError,
            match="Cannot deactivate system envelope 'Credit Card Payment'",
        ):
            env_service.deactivate_envelope(session, "Credit Card Payment")

    def test_deactivate_account_adjustment_raises_error(self, session):
        with pytest.raises(
            ValueError,
            match="Cannot deactivate system envelope 'Account Adjustment'",
        ):
            env_service.deactivate_envelope(session, "Account Adjustment")

    def test_deactivate_envelope_linked_to_account_raises_error(self, session):
        custom_env = env_service.create_envelope(
            session, EnvelopeBase(name="Store Card Payment")
        )
        acc = Account(
            name="Store Card",
            account_type=AccountType.CREDIT_CARD,
            envelope_id=custom_env.id,
        )
        session.add(acc)
        session.commit()
        session.refresh(acc)

        with pytest.raises(
            ValueError,
            match="Cannot deactivate envelope .* linked to account 'Store Card'",
        ):
            env_service.deactivate_envelope(session, "Store Card Payment")

    def test_deactivate_empty_name_raises_error(self, session):
        with pytest.raises(ValueError, match="envelope name cannot be empty"):
            env_service.deactivate_envelope(session, "   ")

    def test_deactivate_nonexistent_envelope_raises_error(self, session):
        with pytest.raises(ValueError, match="envelope 'GhostEnvelope' does not exist"):
            env_service.deactivate_envelope(session, "GhostEnvelope")


class TestActivateEnvelope:
    def test_activate_envelope_success(self, session):
        env = env_service.create_envelope(
            session, EnvelopeBase(name="DormantEnv", is_active=False)
        )
        assert env.is_active is False

        activated = env_service.activate_envelope(session, "DormantEnv")
        assert activated.is_active is True

    def test_activate_envelope_strips_whitespace(self, session):
        env_service.create_envelope(
            session, EnvelopeBase(name="TrimActivation", is_active=False)
        )
        activated = env_service.activate_envelope(session, "  TrimActivation  ")
        assert activated.is_active is True

    def test_activate_already_active_returns_envelope(self, session):
        env = env_service.create_envelope(session, EnvelopeBase(name="ActiveEnv"))
        assert env.is_active is True

        result = env_service.activate_envelope(session, "ActiveEnv")
        assert result.id == env.id
        assert result.is_active is True

    def test_activate_empty_name_raises_error(self, session):
        with pytest.raises(ValueError, match="envelope name cannot be empty"):
            env_service.activate_envelope(session, "")

    def test_activate_nonexistent_envelope_raises_error(self, session):
        with pytest.raises(ValueError, match="envelope 'NoSuchEnv' does not exist"):
            env_service.activate_envelope(session, "NoSuchEnv")


class TestGetEnvelopesAndBalances:
    def test_get_envelopes_and_balances_returns_all(self, session):
        env_service.create_envelope(session, EnvelopeBase(name="AlphaEnv"))
        env_service.create_envelope(
            session, EnvelopeBase(name="BetaEnv", is_active=False)
        )

        all_envelopes = env_service.get_envelopes_and_balances(session)
        names = [e.name for e in all_envelopes]
        assert "AlphaEnv" in names
        assert "BetaEnv" in names

        for e in all_envelopes:
            assert isinstance(e, EnvelopeWithBalance)
            assert e.id is not None
            assert isinstance(e.balance, Decimal)

    def test_get_active_envelopes_w_balance(self, session):
        env_service.create_envelope(session, EnvelopeBase(name="Active1"))
        env_service.create_envelope(
            session, EnvelopeBase(name="Inactive1", is_active=False)
        )

        active = env_service.get_active_envelopes_w_balance(session)
        active_names = [e.name for e in active]
        assert "Active1" in active_names
        assert "Inactive1" not in active_names

    def test_get_inactive_envelopes_w_balance(self, session):
        env_service.create_envelope(session, EnvelopeBase(name="Active2"))
        env_service.create_envelope(
            session, EnvelopeBase(name="Inactive2", is_active=False)
        )

        inactive = env_service.get_inactive_envelopes_w_balance(session)
        inactive_names = [e.name for e in inactive]
        assert "Inactive2" in inactive_names
        assert "Active2" not in inactive_names

    def test_envelope_with_balance_reflects_transactions(self, session):
        env_service.add_to_cash(session, Decimal("500"), "Income")
        env_service.create_envelope(session, EnvelopeBase(name="FundedEnv"))
        env_service.assign_to_envelope(
            session, destination="FundedEnv", amount=Decimal("150")
        )

        results = env_service.get_envelopes_and_balances(session)
        funded = next(e for e in results if e.name == "FundedEnv")
        assert funded.balance == Decimal("150")


class TestGetSingleEnvelopeWithBalance:
    def test_get_single_envelope_success(self, session):
        env_service.create_envelope(
            session, EnvelopeBase(name="Coffee", note="Daily brew")
        )
        result = env_service.get_single_envelope_w_balance(session, "Coffee")

        assert result.name == "Coffee"
        assert result.note == "Daily brew"
        assert result.is_active is True
        assert result.balance == Decimal("0")
        assert result.id is not None

    def test_get_single_envelope_strips_whitespace(self, session):
        env_service.create_envelope(session, EnvelopeBase(name="Tea"))
        result = env_service.get_single_envelope_w_balance(session, "  Tea  ")
        assert result.name == "Tea"

    def test_get_single_envelope_empty_name_raises_error(self, session):
        with pytest.raises(ValueError, match="envelope name cannot be empty"):
            env_service.get_single_envelope_w_balance(session, "   ")

    def test_get_single_envelope_nonexistent_raises_error(self, session):
        with pytest.raises(ValueError, match="envelope 'Nonexistent' does not exist"):
            env_service.get_single_envelope_w_balance(session, "Nonexistent")


class TestPermaDeleteEnvelope:
    def test_perma_delete_empty_envelope_success(self, session):
        env_service.create_envelope(session, EnvelopeBase(name="Disposable"))
        success = env_service.perma_delete_envelope(session, "Disposable")

        assert success is True
        assert get_envelope_by_name(session, "Disposable") is None

    def test_perma_delete_strips_whitespace(self, session):
        env_service.create_envelope(session, EnvelopeBase(name="TrimDelete"))
        success = env_service.perma_delete_envelope(session, "  TrimDelete  ")

        assert success is True
        assert get_envelope_by_name(session, "TrimDelete") is None

    def test_perma_delete_envelope_with_transactions_raises_error(self, session):
        env_service.add_to_cash(session, Decimal("500"), "Income")
        env_service.create_envelope(session, EnvelopeBase(name="HasTransactions"))
        env_service.assign_to_envelope(
            session, destination="HasTransactions", amount=Decimal("50")
        )

        with pytest.raises(
            ValueError,
            match="has transactions associated with it, deactivate it instead",
        ):
            env_service.perma_delete_envelope(session, "HasTransactions")

    def test_perma_delete_unassigned_raises_error(self, session):
        with pytest.raises(
            ValueError, match="Cannot delete system envelope 'Unassigned'"
        ):
            env_service.perma_delete_envelope(session, "Unassigned")

    def test_perma_delete_credit_card_payment_raises_error(self, session):
        with pytest.raises(
            ValueError, match="Cannot delete system envelope 'Credit Card Payment'"
        ):
            env_service.perma_delete_envelope(session, "Credit Card Payment")

    def test_perma_delete_account_adjustment_raises_error(self, session):
        with pytest.raises(
            ValueError, match="Cannot delete system envelope 'Account Adjustment'"
        ):
            env_service.perma_delete_envelope(session, "Account Adjustment")

    def test_perma_delete_linked_envelope_raises_error(self, session):
        custom_env = env_service.create_envelope(
            session, EnvelopeBase(name="TargetCard Payment")
        )
        acc = Account(
            name="Target Card",
            account_type=AccountType.CREDIT_CARD,
            envelope_id=custom_env.id,
        )
        session.add(acc)
        session.commit()

        with pytest.raises(
            ValueError, match="Cannot delete envelope .* linked to account 'Target Card'"
        ):
            env_service.perma_delete_envelope(session, "TargetCard Payment")

    def test_perma_delete_empty_name_raises_error(self, session):
        with pytest.raises(ValueError, match="envelope name cannot be empty"):
            env_service.perma_delete_envelope(session, "   ")

    def test_perma_delete_nonexistent_envelope_raises_error(self, session):
        with pytest.raises(ValueError, match="envelope 'Ghost' does not exist"):
            env_service.perma_delete_envelope(session, "Ghost")


class TestUpdateEnvelopeInfo:
    def test_update_envelope_name_success(self, session):
        env_service.create_envelope(
            session, EnvelopeBase(name="OldName", note="Old note")
        )
        updated = env_service.update_envelope_info(
            session,
            target_name="OldName",
            envelope_info=EnvelopeUpdate(name="NewName"),
        )

        assert updated.name == "NewName"
        assert updated.note == "Old note"
        assert get_envelope_by_name(session, "OldName") is None
        assert get_envelope_by_name(session, "NewName") is not None

    def test_update_envelope_note_success(self, session):
        env_service.create_envelope(
            session, EnvelopeBase(name="Travel", note="Trip to Japan")
        )
        updated = env_service.update_envelope_info(
            session,
            target_name="Travel",
            envelope_info=EnvelopeUpdate(note="Trip to Italy"),
        )

        assert updated.name == "Travel"
        assert updated.note == "Trip to Italy"

    def test_update_envelope_keep_same_name_and_change_note(self, session):
        env_service.create_envelope(
            session, EnvelopeBase(name="Hobbies", note="Guitars")
        )
        updated = env_service.update_envelope_info(
            session,
            target_name="Hobbies",
            envelope_info=EnvelopeUpdate(name="Hobbies", note="Bicycles"),
        )

        assert updated.name == "Hobbies"
        assert updated.note == "Bicycles"

    def test_update_envelope_clear_note(self, session):
        env_service.create_envelope(
            session, EnvelopeBase(name="Subscriptions", note="Netflix")
        )
        updated = env_service.update_envelope_info(
            session,
            target_name="Subscriptions",
            envelope_info=EnvelopeUpdate(note=""),
        )

        assert updated.note is None

    def test_update_envelope_strips_whitespace(self, session):
        env_service.create_envelope(session, EnvelopeBase(name="Books"))
        updated = env_service.update_envelope_info(
            session,
            target_name="  Books  ",
            envelope_info=EnvelopeUpdate(name="  Reading  "),
        )

        assert updated.name == "Reading"

    def test_update_envelope_duplicate_name_raises_error(self, session):
        env_service.create_envelope(session, EnvelopeBase(name="EnvA"))
        env_service.create_envelope(session, EnvelopeBase(name="EnvB"))

        with pytest.raises(
            ValueError, match="envelope 'EnvB' already exists, try a different name"
        ):
            env_service.update_envelope_info(
                session,
                target_name="EnvA",
                envelope_info=EnvelopeUpdate(name="EnvB"),
            )

    def test_update_envelope_rename_unassigned_succeeds_and_preserves_role(self, session):
        updated = env_service.update_envelope_info(
            session,
            target_name="Unassigned",
            envelope_info=EnvelopeUpdate(name="Ready to Assign"),
        )
        assert updated.name == "Ready to Assign"
        assert updated.system_role == SystemEnvelopeType.UNASSIGNED

        # Old name no longer exists
        assert get_envelope_by_name(session, "Unassigned") is None
        assert get_envelope_by_name(session, "Ready to Assign") is not None

        # add_to_cash still routes to the renamed envelope
        tx = env_service.add_to_cash(
            session,
            amount=Decimal("500.00"),
            source="Paycheck",
        )
        assert tx is not None
        assert get_balance_for_envelope(session, updated) == Decimal("500.00")

        # assign_to_envelope transfers from the renamed envelope
        env_service.create_envelope(
            session, EnvelopeBase(name="Groceries")
        )
        transfer = env_service.assign_to_envelope(
            session,
            destination="Groceries",
            amount=Decimal("150.00"),
        )
        assert transfer.new_balance_src == Decimal("350.00")
        assert transfer.new_balance_dest == Decimal("150.00")

        # Deleting or deactivating under the new name is still prohibited
        with pytest.raises(ValueError, match="Cannot delete system envelope 'Ready to Assign'"):
            env_service.perma_delete_envelope(session, "Ready to Assign")

        with pytest.raises(ValueError, match="Cannot deactivate system envelope 'Ready to Assign'"):
            env_service.deactivate_envelope(session, "Ready to Assign")

    def test_update_envelope_rename_credit_card_payment_succeeds(self, session):
        updated = env_service.update_envelope_info(
            session,
            target_name="Credit Card Payment",
            envelope_info=EnvelopeUpdate(name="Card Payment Holding"),
        )
        assert updated.name == "Card Payment Holding"
        assert updated.system_role == SystemEnvelopeType.CREDIT_CARD_PAYMENT

        # Create CC account linked to CC payment
        account_service.create_account(
            session,
            AccountBase(name="Chase Sapphire", account_type=AccountType.CREDIT_CARD),
        )
        # Create a spending envelope and fund it
        env_service.create_envelope(
            session, EnvelopeBase(name="Dining")
        )
        env_service.add_to_cash(session, Decimal("200.00"), "Bonus")
        env_service.assign_to_envelope(session, "Dining", Decimal("100.00"))

        # Log a regular CC transaction
        tx = tx_service.add_reg_transaction(
            session,
            TransactionRequest(
                merchant="Restaurant",
                payment_method_name="Chase Sapphire",
                transaction_type=TransactionType.EXPENSE,
                splits=[
                    EnvelopeSplitRequest(amount=Decimal("-60.00"), envelope_name="Dining")
                ],
            ),
        )
        assert tx is not None
        # Check that balancing split was added to the renamed CC payment envelope
        assert get_balance_for_envelope(session, updated) == Decimal("60.00")
        # Check that transaction total correctly filters out the balancing split
        total = tx_service.calculate_transaction_total(tx)
        assert total == Decimal("60.00")

    def test_update_envelope_rename_account_adjustment_succeeds(self, session):
        updated = env_service.update_envelope_info(
            session,
            target_name="Account Adjustment",
            envelope_info=EnvelopeUpdate(name="Reconciliation Debt"),
        )
        assert updated.name == "Reconciliation Debt"
        assert updated.system_role == SystemEnvelopeType.ACCOUNT_ADJUSTMENT

        # Creating a debt account with starting balance posts to the renamed envelope
        loan_acc = account_service.create_account(
            session,
            AccountBase(
                name="Auto Loan",
                account_type=AccountType.LOAN,
                current_balance=Decimal("5000.00"),
            ),
        )
        assert loan_acc is not None
        assert get_balance_for_envelope(session, updated) == Decimal("5000.00")

    def test_update_envelope_empty_target_name_raises_error(self, session):
        with pytest.raises(ValueError, match="envelope name cannot be empty"):
            env_service.update_envelope_info(
                session,
                target_name="   ",
                envelope_info=EnvelopeUpdate(name="Valid"),
            )

    def test_update_envelope_empty_new_name_raises_error(self, session):
        env_service.create_envelope(session, EnvelopeBase(name="ValidEnv"))
        with pytest.raises(ValueError, match="Envelope name cannot be empty"):
            env_service.update_envelope_info(
                session,
                target_name="ValidEnv",
                envelope_info=EnvelopeUpdate(name="   "),
            )

    def test_update_envelope_nonexistent_raises_error(self, session):
        with pytest.raises(ValueError, match="envelope 'Ghost' does not exist"):
            env_service.update_envelope_info(
                session,
                target_name="Ghost",
                envelope_info=EnvelopeUpdate(name="NewName"),
            )

    def test_update_envelope_category(self, session):
        from budget_app.services import category_service
        category_service.create_category(session, name="Category A")
        category_service.create_category(session, name="Category B")

        env = env_service.create_envelope(
            session, EnvelopeBase(name="CategorizedEnv"), category_name="Category A"
        )
        assert env.category_id is not None
        assert env.category is not None
        assert env.category.name == "Category A"

        # Update category to Category B
        updated = env_service.update_envelope_info(
            session,
            target_name="CategorizedEnv",
            envelope_info=EnvelopeUpdate(category_name="Category B"),
        )
        assert updated.category is not None
        assert updated.category.name == "Category B"

        # Unassign category
        unassigned = env_service.update_envelope_info(
            session,
            target_name="CategorizedEnv",
            envelope_info=EnvelopeUpdate(category_name=""),
        )
        assert unassigned.category_id is None

    def test_update_envelope_nonexistent_category_raises(self, session):
        env_service.create_envelope(session, EnvelopeBase(name="CatTestEnv"))
        with pytest.raises(ValueError, match="Category 'FakeCat' does not exist"):
            env_service.update_envelope_info(
                session,
                target_name="CatTestEnv",
                envelope_info=EnvelopeUpdate(category_name="FakeCat"),
            )


class TestEnvelopeCategoryIntegration:
    def test_create_envelope_with_category(self, session):
        from budget_app.services import category_service
        cat = category_service.create_category(session, name="Living Expenses")

        env = env_service.create_envelope(
            session, EnvelopeBase(name="Water"), category_name="Living Expenses"
        )
        assert env.category_id == cat.id

        with_bal = env_service.get_single_envelope_w_balance(session, "Water")
        assert with_bal.category_id == cat.id
        assert with_bal.category_name == "Living Expenses"

    def test_create_envelope_with_invalid_category_raises(self, session):
        with pytest.raises(ValueError, match="Category 'NonExistent' does not exist"):
            env_service.create_envelope(
                session, EnvelopeBase(name="Gas"), category_name="NonExistent"
            )