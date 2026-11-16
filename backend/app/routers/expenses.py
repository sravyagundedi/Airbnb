import datetime
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import Trip, TripMember, User, Expense, ExpenseShare, EventLog
from app.schemas import (
    ExpenseCreateRequest, ExpenseResponse, ExpenseShareResponse,
    SettlementItem, ExpenseSummaryResponse
)
from app.security import current_user, get_room_role
from app.budget.split import even_split

router = APIRouter(prefix="/api/v1/trips", tags=["Expenses"])


def compute_settlement_plan(
    members: Dict[int, str],
    net_balances: Dict[int, int],
    currency: str = "EUR"
) -> List[SettlementItem]:
    """
    Computes minimal pairwise settlement transactions from integer cent net balances.
    Positive net balance = creditor (is owed money)
    Negative net balance = debtor (owes money)
    """
    debtors = []
    creditors = []
    for uid, net in net_balances.items():
        if net < -1:  # owes money
            debtors.append({"id": uid, "amount": -net, "name": members.get(uid, f"User {uid}")})
        elif net > 1:  # is owed money
            creditors.append({"id": uid, "amount": net, "name": members.get(uid, f"User {uid}")})

    # Sort descending
    debtors.sort(key=lambda x: x["amount"], reverse=True)
    creditors.sort(key=lambda x: x["amount"], reverse=True)

    settlements: List[SettlementItem] = []
    d_idx = 0
    c_idx = 0

    while d_idx < len(debtors) and c_idx < len(creditors):
        debtor = debtors[d_idx]
        creditor = creditors[c_idx]

        settle_cents = min(debtor["amount"], creditor["amount"])
        if settle_cents > 0:
            settlements.append(
                SettlementItem(
                    from_user_id=debtor["id"],
                    from_user_name=debtor["name"],
                    to_user_id=creditor["id"],
                    to_user_name=creditor["name"],
                    amount=round(settle_cents / 100.0, 2),
                    currency=currency
                )
            )

        debtor["amount"] -= settle_cents
        creditor["amount"] -= settle_cents

        if debtor["amount"] <= 1:
            d_idx += 1
        if creditor["amount"] <= 1:
            c_idx += 1

    return settlements


@router.post("/{trip_id}/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    trip_id: int,
    req: ExpenseCreateRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db)
):
    role = await get_room_role(user, trip_id, db)

    if not role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Must be a member of the trip room")

    trip = await db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    # Determine payer
    payer_id = req.paid_by_user_id or user.id
    payer = await db.get(User, payer_id)
    payer_name = payer.display_name if payer else user.display_name

    # Determine participants to split between
    if req.split_user_ids and len(req.split_user_ids) > 0:
        split_uids = req.split_user_ids
    else:
        mem_stmt = select(TripMember.user_id).where(TripMember.trip_id == trip_id)
        split_uids = (await db.execute(mem_stmt)).scalars().all()
        if not split_uids:
            split_uids = [user.id]

    total_cents = int(round(req.amount * 100))
    shares_cents = even_split(total_cents, len(split_uids))

    # Fetch names for participants
    users_stmt = select(User).where(User.id.in_(split_uids))
    split_users = {u.id: u.display_name for u in (await db.execute(users_stmt)).scalars().all()}

    expense = Expense(
        trip_id=trip_id,
        paid_by_user_id=payer_id,
        paid_by_name=payer_name,
        title=req.title.strip(),
        category=req.category or "dining",
        amount_cents=total_cents,
        currency=trip.currency or "EUR",
        created_at=datetime.datetime.utcnow()
    )
    db.add(expense)
    await db.flush()

    expense_shares = []
    for uid, s_cents in zip(split_uids, shares_cents):
        share = ExpenseShare(
            expense_id=expense.id,
            user_id=uid,
            user_name=split_users.get(uid, f"User {uid}"),
            share_cents=s_cents,
            is_settled=(uid == payer_id)  # Payer is settled with themselves
        )
        db.add(share)
        expense_shares.append(share)

    # Log event
    log = EventLog(
        trip_id=trip_id,
        user_id=user.id,
        type="expense_recorded",
        payload={
            "expense_id": expense.id,
            "title": expense.title,
            "amount": req.amount,
            "currency": trip.currency or "EUR",
            "payer": payer_name,
            "split_count": len(split_uids)
        }
    )
    db.add(log)
    await db.commit()
    await db.refresh(expense)

    return ExpenseResponse(
        id=expense.id,
        trip_id=trip.id,
        title=expense.title,
        amount=round(expense.amount_cents / 100.0, 2),
        currency=expense.currency,
        category=expense.category,
        paid_by_user_id=expense.paid_by_user_id,
        paid_by_name=expense.paid_by_name,
        created_at=expense.created_at,
        shares=[
            ExpenseShareResponse(
                user_id=s.user_id,
                user_name=s.user_name,
                share_amount=round(s.share_cents / 100.0, 2),
                is_settled=s.is_settled
            )
            for s in expense_shares
        ]
    )


@router.get("/{trip_id}/expenses", response_model=ExpenseSummaryResponse)
async def get_trip_expenses(
    trip_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db)
):
    role = await get_room_role(user, trip_id, db)

    if not role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Must be a member of the trip room")

    trip = await db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    # Fetch all members of the trip
    mem_stmt = (
        select(TripMember.user_id, User.display_name)
        .join(User, TripMember.user_id == User.id)
        .where(TripMember.trip_id == trip_id)
    )
    members_map = {row[0]: row[1] for row in (await db.execute(mem_stmt)).all()}

    # Fetch expenses with shares
    stmt = (
        select(Expense)
        .options(selectinload(Expense.shares))
        .where(Expense.trip_id == trip_id)
        .order_by(Expense.created_at.desc())
    )
    expenses = (await db.execute(stmt)).scalars().all()

    total_cents = 0
    cat_totals: Dict[str, float] = {}
    net_balances: Dict[int, int] = {uid: 0 for uid in members_map}

    expense_responses: List[ExpenseResponse] = []
    for exp in expenses:
        total_cents += exp.amount_cents
        cat_totals[exp.category] = cat_totals.get(exp.category, 0.0) + (exp.amount_cents / 100.0)

        # Payer paid the full amount
        net_balances[exp.paid_by_user_id] = net_balances.get(exp.paid_by_user_id, 0) + exp.amount_cents

        share_resps = []
        for s in exp.shares:
            share_resps.append(
                ExpenseShareResponse(
                    user_id=s.user_id,
                    user_name=s.user_name,
                    share_amount=round(s.share_cents / 100.0, 2),
                    is_settled=s.is_settled
                )
            )
            # Each participant owes their share
            net_balances[s.user_id] = net_balances.get(s.user_id, 0) - s.share_cents

        expense_responses.append(
            ExpenseResponse(
                id=exp.id,
                trip_id=exp.trip_id,
                title=exp.title,
                amount=round(exp.amount_cents / 100.0, 2),
                currency=exp.currency,
                category=exp.category,
                paid_by_user_id=exp.paid_by_user_id,
                paid_by_name=exp.paid_by_name,
                created_at=exp.created_at,
                shares=share_resps
            )
        )

    settlement_plan = compute_settlement_plan(
        members=members_map,
        net_balances=net_balances,
        currency=trip.currency or "EUR"
    )

    return ExpenseSummaryResponse(
        trip_id=trip_id,
        total_expenses=round(total_cents / 100.0, 2),
        currency=trip.currency or "EUR",
        category_totals={k: round(v, 2) for k, v in cat_totals.items()},
        expenses=expense_responses,
        settlement_plan=settlement_plan
    )


@router.post("/{trip_id}/expenses/settle")
async def settle_trip_expenses(
    trip_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db)
):
    role = await get_room_role(user, trip_id, db)

    if not role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Must be a member of the trip room")

    # Mark all shares in trip as settled
    stmt = (
        select(ExpenseShare)
        .join(Expense, ExpenseShare.expense_id == Expense.id)
        .where(Expense.trip_id == trip_id)
    )
    shares = (await db.execute(stmt)).scalars().all()
    for s in shares:
        s.is_settled = True

    log = EventLog(
        trip_id=trip_id,
        user_id=user.id,
        type="expenses_settled",
        payload={"settled_by": user.display_name}
    )
    db.add(log)
    await db.commit()

    return {"message": "All trip expenses marked as settled."}
