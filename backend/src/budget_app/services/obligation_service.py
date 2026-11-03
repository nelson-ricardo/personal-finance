"""Service layer for managing obligations, account linking, and calendar due states."""

import calendar
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlmodel import Session, select

from budget_app.models.account import Account
from budget_app.models.obligation import NotificationConfig, Obligation
from budget_app.schemas.account import AccountType
from budget_app.schemas.obligation import (
    NotificationConfigResponse,
    NotificationConfigUpdate,
    ObligationCreate,
    ObligationMarkPaidRequest,
    ObligationResponse,
    ObligationUpdate,
)


def get_target_due_date(year: int, month: int, due_day: int) -> date:
    """Clamps due day to the maximum days in the target month (e.g. Feb 31 -> Feb 28)."""
    _, max_days = calendar.monthrange(year, month)
    clamped_day = min(due_day, max_days)
    return date(year, month, clamped_day)


def compute_obligation_status(
    due_day: int,
    last_paid_date: Optional[date],
    today: Optional[date] = None,
) -> Tuple[date, int, bool, bool]:
    """Computes next_due_date, days_until_due, is_overdue, and is_paid_this_month.

    Returns:
        (next_due_date, days_until_due, is_overdue, is_paid_this_month)
    """
    if today is None:
        today = date.today()

    this_month_due = get_target_due_date(today.year, today.month, due_day)

    # Check if paid for this calendar month cycle
    is_paid_this_month = False
    if last_paid_date is not None:
        if last_paid_date.year == today.year and last_paid_date.month == today.month:
            is_paid_this_month = True
        elif last_paid_date >= this_month_due:
            is_paid_this_month = True

    if is_paid_this_month:
        # Next due is next month
        if today.month == 12:
            next_due_date = get_target_due_date(today.year + 1, 1, due_day)
        else:
            next_due_date = get_target_due_date(today.year, today.month + 1, due_day)
        is_overdue = False
    else:
        if today > this_month_due:
            # Past due date this month and unpaid
            next_due_date = this_month_due
            is_overdue = True
        else:
            next_due_date = this_month_due
            is_overdue = False

    days_until_due = (next_due_date - today).days
    return next_due_date, days_until_due, is_overdue, is_paid_this_month


def _build_response(obligation: Obligation, session: Session) -> ObligationResponse:
    """Helper to convert Obligation model to rich ObligationResponse schema."""
    account_name = None
    account_type = None

    if obligation.account_id:
        acc = session.get(Account, obligation.account_id)
        if acc:
            account_name = acc.name
            account_type = acc.account_type.value if hasattr(acc.account_type, "value") else str(acc.account_type)

    next_due_date, days_until_due, is_overdue, is_paid_this_month = compute_obligation_status(
        obligation.due_day, obligation.last_paid_date
    )

    return ObligationResponse(
        id=obligation.id or 0,
        name=obligation.name,
        due_day=obligation.due_day,
        amount=obligation.amount,
        note=obligation.note,
        account_id=obligation.account_id,
        account_name=account_name,
        account_type=account_type,
        is_active=obligation.is_active,
        last_paid_date=obligation.last_paid_date,
        last_paid_amount=obligation.last_paid_amount,
        created_at=obligation.created_at,
        next_due_date=next_due_date,
        days_until_due=days_until_due,
        is_overdue=is_overdue,
        is_paid_this_month=is_paid_this_month,
    )


def get_all_obligations(
    session: Session, is_active: Optional[bool] = None
) -> List[ObligationResponse]:
    """Lists all obligations sorted by due day."""
    stmt = select(Obligation)
    if is_active is not None:
        stmt = stmt.where(Obligation.is_active == is_active)
    stmt = stmt.order_by(Obligation.due_day.asc())

    obligations = session.exec(stmt).all()
    return [_build_response(o, session) for o in obligations]


def get_obligation_by_id(session: Session, obligation_id: int) -> Optional[ObligationResponse]:
    """Retrieves an obligation by ID."""
    obligation = session.get(Obligation, obligation_id)
    if not obligation:
        return None
    return _build_response(obligation, session)


def create_obligation(session: Session, data: ObligationCreate) -> ObligationResponse:
    """Creates a new obligation, auto-generating default note if linked to an account."""
    note = data.note
    if data.account_id and not note:
        acc = session.get(Account, data.account_id)
        if acc:
            note = f"Monthly payment for {acc.name}"

    obligation = Obligation(
        name=data.name,
        due_day=data.due_day,
        amount=data.amount,
        note=note,
        account_id=data.account_id,
    )
    session.add(obligation)
    session.commit()
    session.refresh(obligation)
    return _build_response(obligation, session)


def update_obligation(
    session: Session, obligation_id: int, data: ObligationUpdate
) -> Optional[ObligationResponse]:
    """Updates an existing obligation."""
    obligation = session.get(Obligation, obligation_id)
    if not obligation:
        return None

    if data.name is not None:
        obligation.name = data.name
    if data.due_day is not None:
        obligation.due_day = data.due_day
    if data.amount is not None:
        obligation.amount = data.amount
    if data.note is not None:
        obligation.note = data.note
    if data.account_id is not None:
        obligation.account_id = data.account_id
    if data.is_active is not None:
        obligation.is_active = data.is_active

    session.add(obligation)
    session.commit()
    session.refresh(obligation)
    return _build_response(obligation, session)


def delete_obligation(session: Session, obligation_id: int) -> bool:
    """Deletes an obligation."""
    obligation = session.get(Obligation, obligation_id)
    if not obligation:
        return False
    session.delete(obligation)
    session.commit()
    return True


def mark_obligation_paid(
    session: Session, obligation_id: int, req: ObligationMarkPaidRequest
) -> Optional[ObligationResponse]:
    """Marks an obligation as paid or unpaid for the current period."""
    obligation = session.get(Obligation, obligation_id)
    if not obligation:
        return None

    if req.paid:
        obligation.last_paid_date = req.paid_date or date.today()
        obligation.last_paid_amount = req.paid_amount or obligation.amount
    else:
        obligation.last_paid_date = None
        obligation.last_paid_amount = None

    session.add(obligation)
    session.commit()
    session.refresh(obligation)
    return _build_response(obligation, session)


def sync_obligations_from_accounts(session: Session) -> dict:
    """Finds all Credit Card and Loan accounts with due_date and syncs obligations."""
    stmt = select(Account).where(
        Account.account_type.in_([AccountType.CREDIT_CARD, AccountType.LOAN]),
        Account.due_date.isnot(None),
        Account.is_active == True,  # noqa: E712
    )
    accounts = session.exec(stmt).all()

    created_count = 0
    updated_count = 0

    for acc in accounts:
        if acc.id is None or acc.due_date is None:
            continue

        amount = acc.monthly_payment or Decimal("0.00")
        default_note = f"Monthly payment for {acc.name}"

        # Find existing obligation linked to this account
        obl_stmt = select(Obligation).where(Obligation.account_id == acc.id)
        existing = session.exec(obl_stmt).first()

        if existing:
            # Sync details from account if changed
            existing.due_day = acc.due_date
            if acc.monthly_payment is not None and acc.monthly_payment > 0:
                existing.amount = acc.monthly_payment
            if not existing.note:
                existing.note = default_note
            session.add(existing)
            updated_count += 1
        else:
            new_obl = Obligation(
                name=acc.name,
                due_day=acc.due_date,
                amount=amount,
                note=default_note,
                account_id=acc.id,
            )
            session.add(new_obl)
            created_count += 1

    session.commit()
    return {
        "accounts_scanned": len(accounts),
        "obligations_created": created_count,
        "obligations_updated": updated_count,
    }


def get_notification_config(session: Session) -> NotificationConfigResponse:
    """Retrieves or creates the single notification configuration record."""
    config = session.exec(select(NotificationConfig)).first()
    if not config:
        config = NotificationConfig()
        session.add(config)
        session.commit()
        session.refresh(config)

    return NotificationConfigResponse(
        reminder_time=config.reminder_time,
        reminder_days_ahead=config.reminder_days_ahead,
        is_enabled=config.is_enabled,
        last_dispatched_date=config.last_dispatched_date,
    )


def update_notification_config(
    session: Session, data: NotificationConfigUpdate
) -> NotificationConfigResponse:
    """Updates notification configuration."""
    config = session.exec(select(NotificationConfig)).first()
    if not config:
        config = NotificationConfig()
        session.add(config)

    if data.reminder_time is not None:
        config.reminder_time = data.reminder_time
    if data.reminder_days_ahead is not None:
        config.reminder_days_ahead = data.reminder_days_ahead
    if data.is_enabled is not None:
        config.is_enabled = data.is_enabled

    session.add(config)
    session.commit()
    session.refresh(config)

    return NotificationConfigResponse(
        reminder_time=config.reminder_time,
        reminder_days_ahead=config.reminder_days_ahead,
        is_enabled=config.is_enabled,
        last_dispatched_date=config.last_dispatched_date,
    )
