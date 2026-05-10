from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.deps import get_current_user_id
from app.services import expense_service
from app.services.currency_service import get_exchange_rates

router = APIRouter()


def expense_to_response(expense) -> schemas.ExpenseResponse:
    return schemas.ExpenseResponse(
        id=expense.id,
        trip_id=expense.trip_id,
        user_id=expense.user_id,
        amount=expense.amount,
        currency=expense.currency,
        category=expense.category.value if hasattr(expense.category, "value") else expense.category,
        description=expense.description,
        expense_date=expense.expense_date,
        is_one_time=expense.is_one_time,
        created_at=expense.created_at.isoformat() if expense.created_at else "",
        updated_at=expense.updated_at.isoformat() if expense.updated_at else None,
    )


@router.post("/trips/{trip_id}/expenses", response_model=schemas.ExpenseResponse, status_code=201)
def create_expense(
    trip_id: UUID,
    data: schemas.ExpenseCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    expense = expense_service.create_expense(db, user_id, trip_id, data)
    return expense_to_response(expense)


@router.get("/trips/{trip_id}/expenses", response_model=list[schemas.ExpenseResponse])
def list_expenses(
    trip_id: UUID,
    category: schemas.ExpenseCategory | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    expenses = expense_service.list_expenses(db, user_id, trip_id, category, date_from, date_to)
    return [expense_to_response(e) for e in expenses]


@router.get("/trips/{trip_id}/expenses/summary", response_model=schemas.ExpenseSummary)
def get_expenses_summary(
    trip_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return expense_service.get_summary(db, user_id, trip_id)


@router.get("/trips/{trip_id}/expenses/converted-summary", response_model=schemas.ConvertedExpenseSummary)
async def get_converted_expenses_summary(
    trip_id: UUID,
    target_currency: str = Query(...),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return await expense_service.get_converted_summary(db, user_id, trip_id, target_currency)


@router.get("/exchange-rates", response_model=schemas.ExchangeRatesResponse)
async def get_rates(base: str = Query("USD")):
    rates = await get_exchange_rates(base.upper())
    return schemas.ExchangeRatesResponse(
        base=base.upper(),
        rates={k: float(v) for k, v in rates.items()},
    )


@router.put("/expenses/{expense_id}", response_model=schemas.ExpenseResponse)
def update_expense(
    expense_id: UUID,
    data: schemas.ExpenseUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    expense = expense_service.update_expense(db, user_id, expense_id, data)
    return expense_to_response(expense)


@router.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(
    expense_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    expense_service.delete_expense(db, user_id, expense_id)
