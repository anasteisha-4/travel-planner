import logging
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.exceptions import AppException

logger = logging.getLogger(__name__)


def verify_trip_ownership(db: Session, trip_id: UUID, user_id: UUID) -> models.Trip:
    trip = (
        db.query(models.Trip)
        .filter(
            models.Trip.id == trip_id,
            models.Trip.user_id == user_id,
        )
        .first()
    )
    if not trip:
        raise AppException(status_code=404, code="NOT_FOUND", message="Trip not found")
    return trip


def verify_expense_ownership(db: Session, expense_id: UUID, user_id: UUID) -> models.Expense:
    expense = (
        db.query(models.Expense)
        .filter(
            models.Expense.id == expense_id,
            models.Expense.user_id == user_id,
        )
        .first()
    )
    if not expense:
        logger.error(f"Expense not found: expense_id={expense_id}, user_id={user_id}")
        raise AppException(status_code=404, code="NOT_FOUND", message="Expense not found")
    return expense


def create_expense(
    db: Session,
    user_id: UUID,
    trip_id: UUID,
    data: schemas.ExpenseCreate,
) -> models.Expense:
    trip = verify_trip_ownership(db, trip_id, user_id)
    if trip.status == "completed":
        raise AppException(
            status_code=400,
            code="TRIP_COMPLETED",
            message="Cannot add expenses to a completed trip",
        )
    expense = models.Expense(
        user_id=user_id,
        trip_id=trip_id,
        amount=data.amount,
        currency=data.currency,
        category=data.category,
        description=data.description,
        expense_date=data.expense_date,
        is_one_time=data.is_one_time,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def list_expenses(
    db: Session,
    user_id: UUID,
    trip_id: UUID,
    category: schemas.ExpenseCategory | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[models.Expense]:
    verify_trip_ownership(db, trip_id, user_id)
    query = db.query(models.Expense).filter(
        models.Expense.trip_id == trip_id,
        models.Expense.user_id == user_id,
    )
    if category:
        query = query.filter(models.Expense.category == category)
    if date_from:
        query = query.filter(models.Expense.expense_date >= date_from)
    if date_to:
        query = query.filter(models.Expense.expense_date <= date_to)
    return query.order_by(models.Expense.expense_date.desc(), models.Expense.created_at.desc()).all()


def update_expense(
    db: Session,
    user_id: UUID,
    expense_id: UUID,
    data: schemas.ExpenseUpdate,
) -> models.Expense:
    expense = verify_expense_ownership(db, expense_id, user_id)

    trip = db.query(models.Trip).filter(models.Trip.id == expense.trip_id).first()
    if trip and trip.status == "completed":
        raise AppException(
            status_code=400,
            code="TRIP_COMPLETED",
            message="Cannot update expenses of a completed trip",
        )

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(expense, field, value)
    db.commit()
    db.refresh(expense)
    return expense


def delete_expense(db: Session, user_id: UUID, expense_id: UUID) -> None:
    expense = verify_expense_ownership(db, expense_id, user_id)

    trip = db.query(models.Trip).filter(models.Trip.id == expense.trip_id).first()
    if trip and trip.status == "completed":
        raise AppException(
            status_code=400,
            code="TRIP_COMPLETED",
            message="Cannot delete expenses of a completed trip",
        )

    db.delete(expense)
    db.commit()


def get_summary(db: Session, user_id: UUID, trip_id: UUID) -> schemas.ExpenseSummary:
    verify_trip_ownership(db, trip_id, user_id)
    rows = (
        db.query(
            models.Expense.category,
            func.sum(models.Expense.amount),
        )
        .filter(
            models.Expense.trip_id == trip_id,
            models.Expense.user_id == user_id,
        )
        .group_by(models.Expense.category)
        .all()
    )
    by_category: dict[str, Decimal] = {}
    total = Decimal("0")
    for category, amount in rows:
        cat_name = category.value if hasattr(category, "value") else str(category)
        by_category[cat_name] = amount or Decimal("0")
        total += amount or Decimal("0")
    return schemas.ExpenseSummary(total=total, by_category=by_category)


async def get_converted_summary(
    db: Session, user_id: UUID, trip_id: UUID, target_currency: str
) -> schemas.ConvertedExpenseSummary:
    from app.services.currency_service import convert_amount, get_exchange_rates

    trip = verify_trip_ownership(db, trip_id, user_id)

    expenses = (
        db.query(models.Expense)
        .filter(
            models.Expense.trip_id == trip_id,
            models.Expense.user_id == user_id,
        )
        .all()
    )

    original_currencies: set[str] = set()
    for exp in expenses:
        original_currencies.add(exp.currency)

    rates = await get_exchange_rates(target_currency.upper())

    by_category: dict[str, Decimal] = {}
    total = Decimal("0")
    planning_total = Decimal("0")
    in_trip_total = Decimal("0")
    has_errors = False

    for exp in expenses:
        cat_name = exp.category.value if hasattr(exp.category, "value") else str(exp.category)
        converted = convert_amount(exp.amount, exp.currency, target_currency, rates)
        if converted is None:
            has_errors = True
            converted = exp.amount

        by_category[cat_name] = by_category.get(cat_name, Decimal("0")) + converted
        total += converted
        if exp.expense_date is not None and (exp.expense_date < trip.start_date or exp.expense_date > trip.end_date):
            planning_total += converted
        else:
            in_trip_total += converted

    return schemas.ConvertedExpenseSummary(
        total=total.quantize(Decimal("0.01")),
        planning_total=planning_total.quantize(Decimal("0.01")),
        in_trip_total=in_trip_total.quantize(Decimal("0.01")),
        by_category={k: v.quantize(Decimal("0.01")) for k, v in by_category.items()},
        target_currency=target_currency.upper(),
        original_currencies=sorted(original_currencies),
        has_conversion_errors=has_errors,
    )
