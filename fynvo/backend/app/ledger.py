from datetime import date
from enum import StrEnum

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session as DbSession

from .models import Account, Transaction, Transfer, User
from .money import cents_to_decimal, parse_money
from .security import utcnow


class AccountType(StrEnum):
    TRANSACTION = "transaction"
    SAVINGS = "savings"
    OFFSET = "offset"
    CREDIT_CARD = "credit_card"
    CASH = "cash"
    MORTGAGE = "mortgage"
    PERSONAL_LOAN = "personal_loan"
    CAR_LOAN = "car_loan"
    VEHICLE_LOAN = "vehicle_loan"  # Legacy identifier retained for existing data.
    LINE_OF_CREDIT = "line_of_credit"
    INVESTMENT = "investment"
    SUPERANNUATION = "superannuation"
    OTHER_ASSET = "other_asset"
    OTHER_LIABILITY = "other_liability"


LIABILITY_TYPES = {
    "credit_card",
    "mortgage",
    "personal_loan",
    "car_loan",
    "vehicle_loan",
    "line_of_credit",
    "other_liability",
}
LIQUID_ASSET_TYPES = {"transaction", "savings", "offset", "cash"}
ACCOUNT_TYPES = {item.value for item in AccountType}


def _record_edit(
    db: DbSession,
    user: User,
    record_type: str,
    record_id: int,
    original: dict,
    updated: dict,
) -> None:
    """Persist an explainable UI edit alongside the financial record change."""
    db.execute(
        text(
            """
            INSERT INTO edit_history (
                user_id, record_type, record_id, original_json, updated_json, source, created_at
            ) VALUES (
                :user_id, :record_type, :record_id, :original, :updated, 'ui', :now
            )
            """
        ),
        {
            "user_id": user.id,
            "record_type": record_type,
            "record_id": record_id,
            "original": str(original),
            "updated": str(updated),
            "now": utcnow(),
        },
    )


def signed_amount_cents(account: Account, transaction_type: str, amount_cents: int) -> int:
    if transaction_type == "transfer":
        return amount_cents
    liability = account.account_type in LIABILITY_TYPES
    if transaction_type == "income":
        return -abs(amount_cents) if liability else abs(amount_cents)
    if transaction_type == "expense":
        return abs(amount_cents) if liability else -abs(amount_cents)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid transaction type")


def transfer_delta_cents(account: Account, amount_cents: int, incoming: bool) -> int:
    """Return the balance delta for an internal transfer.

    Asset balances represent money owned, while liability balances represent money owed.
    Therefore a payment into a liability reduces its balance rather than increasing it.
    """
    amount = abs(amount_cents)
    if account.account_type in LIABILITY_TYPES:
        return -amount if incoming else amount
    return amount if incoming else -amount


def get_account(db: DbSession, user: User, account_id: int) -> Account:
    account = db.scalar(select(Account).where(Account.id == account_id, Account.user_id == user.id))
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


def account_balance_cents(db: DbSession, account: Account) -> int:
    total = db.scalar(select(func.coalesce(func.sum(Transaction.amount_cents), 0)).where(Transaction.account_id == account.id))
    return account.opening_balance_cents + int(total or 0)


def account_response(db: DbSession, account: Account) -> dict:
    return {
        "id": account.id,
        "name": account.name,
        "account_type": account.account_type,
        "account_class": "liability" if account.account_type in LIABILITY_TYPES else "asset",
        "institution": account.institution,
        "opening_balance": cents_to_decimal(account.opening_balance_cents),
        "current_balance": cents_to_decimal(account_balance_cents(db, account)),
        "description": account.description,
        "account_suffix": account.account_suffix,
        "icon": account.icon,
        "color": account.color,
        "is_active": account.is_active,
        "archived_at": account.archived_at.isoformat() if account.archived_at else None,
        "created_at": account.created_at.isoformat(),
        "updated_at": account.updated_at.isoformat(),
    }


def list_accounts(db: DbSession, user: User, include_archived: bool = False) -> list[dict]:
    query = select(Account).where(Account.user_id == user.id).order_by(Account.name)
    if not include_archived:
        query = query.where(Account.is_active.is_(True))
    return [account_response(db, row) for row in db.scalars(query).all()]


def create_account(db: DbSession, user: User, payload) -> dict:
    if payload.account_type not in ACCOUNT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported account type")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account name is required")
    account = Account(
        user_id=user.id,
        name=name,
        account_type=payload.account_type,
        institution=payload.institution.strip() if payload.institution else None,
        opening_balance_cents=abs(parse_money(payload.opening_balance)),
        description=payload.description.strip() if payload.description else None,
        account_suffix=payload.account_suffix,
        icon=payload.icon,
        color=payload.color,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account_response(db, account)


def update_account(db: DbSession, user: User, account_id: int, payload) -> dict:
    account = get_account(db, user, account_id)
    original = account_response(db, account)
    if payload.account_type and payload.account_type not in ACCOUNT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported account type")
    for field in ("name", "account_type", "institution", "description", "account_suffix", "icon", "color"):
        value = getattr(payload, field)
        if value is not None:
            value = value.strip() if isinstance(value, str) else value
            if field == "name" and not value:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account name is required")
            setattr(account, field, value)
    if payload.opening_balance is not None:
        account.opening_balance_cents = abs(parse_money(payload.opening_balance))
    account.updated_at = utcnow()
    updated = account_response(db, account)
    _record_edit(db, user, "accounts", account.id, original, updated)
    db.commit()
    return account_response(db, account)


def archive_account(db: DbSession, user: User, account_id: int) -> dict:
    account = get_account(db, user, account_id)
    account.is_active = False
    account.archived_at = utcnow()
    account.updated_at = utcnow()
    db.commit()
    return account_response(db, account)


def tx_response(tx: Transaction, running_balance: int | None = None) -> dict:
    return {
        "id": tx.id,
        "account_id": tx.account_id,
        "account_name": tx.account.name if tx.account else None,
        "transfer_id": tx.transfer_id,
        "date": tx.transaction_date.isoformat(),
        "amount": cents_to_decimal(tx.amount_cents),
        "transaction_type": tx.transaction_type,
        "description": tx.description,
        "merchant": tx.merchant,
        "category": tx.category,
        "notes": tx.notes,
        "source": tx.source,
        "status": tx.status,
        "running_balance": cents_to_decimal(running_balance) if running_balance is not None else None,
    }


def list_transactions(db: DbSession, user: User, account_id: int | None = None, transaction_type: str | None = None, date_from: date | None = None, date_to: date | None = None, search: str | None = None, limit: int = 100) -> list[dict]:
    query = select(Transaction).join(Account).where(Transaction.user_id == user.id).order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
    if account_id is not None:
        query = query.where(Transaction.account_id == account_id)
    if transaction_type:
        query = query.where(Transaction.transaction_type == transaction_type)
    if date_from:
        query = query.where(Transaction.transaction_date >= date_from)
    if date_to:
        query = query.where(Transaction.transaction_date <= date_to)
    if search:
        pattern = f"%{search}%"
        query = query.where(or_(Transaction.description.ilike(pattern), Transaction.merchant.ilike(pattern)))
    return [tx_response(row) for row in db.scalars(query.limit(min(limit, 500))).all()]


def create_transaction(db: DbSession, user: User, payload) -> dict:
    account = get_account(db, user, payload.account_id)
    if not account.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Choose an active account")
    if payload.transaction_type not in {"income", "expense"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use transfer endpoint for transfers")
    tx = Transaction(user_id=user.id, account_id=account.id, transaction_date=payload.date, amount_cents=signed_amount_cents(account, payload.transaction_type, parse_money(payload.amount)), transaction_type=payload.transaction_type, description=payload.description.strip(), merchant=payload.merchant, category=payload.category, notes=payload.notes, source=payload.source, status=payload.status, raw_description=payload.raw_description)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx_response(tx)


def update_transaction(db: DbSession, user: User, transaction_id: int, payload) -> dict:
    tx = db.scalar(select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user.id))
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    if tx.transfer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Edit transfers through the transfer endpoint")
    original = tx_response(tx)
    account = tx.account
    if payload.account_id is not None:
        account = get_account(db, user, payload.account_id)
        if not account.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Choose an active account")
        tx.account_id = account.id
    if payload.transaction_type is not None:
        tx.transaction_type = payload.transaction_type
    if payload.amount is not None:
        tx.amount_cents = signed_amount_cents(account, tx.transaction_type, parse_money(payload.amount))
    for field, attr in (("date", "transaction_date"), ("description", "description"), ("merchant", "merchant"), ("category", "category"), ("notes", "notes"), ("source", "source"), ("status", "status"), ("raw_description", "raw_description")):
        value = getattr(payload, field)
        if value is not None:
            setattr(tx, attr, value)
    tx.updated_at = utcnow()
    updated = tx_response(tx)
    _record_edit(db, user, "transactions", tx.id, original, updated)
    db.commit()
    return tx_response(tx)


def delete_transaction(db: DbSession, user: User, transaction_id: int) -> dict:
    tx = db.scalar(select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user.id))
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    if tx.transfer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Delete transfers through the transfer endpoint")
    db.delete(tx)
    db.commit()
    return {"status": "ok"}


def running_transactions(db: DbSession, user: User, account_id: int) -> list[dict]:
    account = get_account(db, user, account_id)
    balance = account.opening_balance_cents
    output = []
    for tx in db.scalars(select(Transaction).where(Transaction.account_id == account.id).order_by(Transaction.transaction_date, Transaction.id)).all():
        balance += tx.amount_cents
        output.append(tx_response(tx, balance))
    return output


def create_transfer(db: DbSession, user: User, payload) -> dict:
    from_account = get_account(db, user, payload.from_account_id)
    to_account = get_account(db, user, payload.to_account_id)
    if not from_account.is_active or not to_account.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transfers require active accounts")
    if from_account.id == to_account.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transfer destination must differ from source")
    amount = abs(parse_money(payload.amount))
    transfer = Transfer(user_id=user.id, from_account_id=from_account.id, to_account_id=to_account.id, amount_cents=amount, transaction_date=payload.date, description=payload.description.strip(), notes=payload.notes)
    db.add(transfer)
    db.flush()
    db.add_all([
        Transaction(user_id=user.id, account_id=from_account.id, transfer_id=transfer.id, transaction_date=payload.date, amount_cents=transfer_delta_cents(from_account, amount, incoming=False), transaction_type="transfer", description=payload.description.strip(), notes=payload.notes, source="manual"),
        Transaction(user_id=user.id, account_id=to_account.id, transfer_id=transfer.id, transaction_date=payload.date, amount_cents=transfer_delta_cents(to_account, amount, incoming=True), transaction_type="transfer", description=payload.description.strip(), notes=payload.notes, source="manual"),
    ])
    db.commit()
    return {"id": transfer.id, "amount": cents_to_decimal(amount), "from_account_id": from_account.id, "to_account_id": to_account.id, "date": payload.date.isoformat(), "description": payload.description}


def update_transfer(db: DbSession, user: User, transfer_id: int, payload) -> dict:
    transfer = db.scalar(select(Transfer).where(Transfer.id == transfer_id, Transfer.user_id == user.id))
    if not transfer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found")
    from_account = get_account(db, user, payload.from_account_id or transfer.from_account_id)
    to_account = get_account(db, user, payload.to_account_id or transfer.to_account_id)
    if not from_account.is_active or not to_account.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transfers require active accounts")
    if from_account.id == to_account.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transfer destination must differ from source")
    amount = abs(parse_money(payload.amount)) if payload.amount is not None else transfer.amount_cents
    if payload.date is not None:
        transfer.transaction_date = payload.date
    if payload.description is not None:
        transfer.description = payload.description.strip()
    if payload.notes is not None:
        transfer.notes = payload.notes
    transfer.from_account_id = from_account.id
    transfer.to_account_id = to_account.id
    transfer.amount_cents = amount
    db.query(Transaction).filter(Transaction.transfer_id == transfer.id).delete()
    db.flush()
    db.add_all([
        Transaction(user_id=user.id, account_id=from_account.id, transfer_id=transfer.id, transaction_date=transfer.transaction_date, amount_cents=transfer_delta_cents(from_account, amount, incoming=False), transaction_type="transfer", description=transfer.description, notes=transfer.notes, source="manual"),
        Transaction(user_id=user.id, account_id=to_account.id, transfer_id=transfer.id, transaction_date=transfer.transaction_date, amount_cents=transfer_delta_cents(to_account, amount, incoming=True), transaction_type="transfer", description=transfer.description, notes=transfer.notes, source="manual"),
    ])
    transfer.updated_at = utcnow()
    db.commit()
    return {"id": transfer.id, "amount": cents_to_decimal(amount), "from_account_id": from_account.id, "to_account_id": to_account.id, "date": transfer.transaction_date.isoformat(), "description": transfer.description}


def delete_transfer(db: DbSession, user: User, transfer_id: int) -> dict:
    transfer = db.scalar(select(Transfer).where(Transfer.id == transfer_id, Transfer.user_id == user.id))
    if not transfer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found")
    db.query(Transaction).filter(Transaction.transfer_id == transfer.id).delete()
    db.delete(transfer)
    db.commit()
    return {"status": "ok"}


def dashboard_position(db: DbSession, user: User) -> dict:
    accounts = db.scalars(select(Account).where(Account.user_id == user.id, Account.is_active.is_(True)).order_by(Account.name)).all()
    assets = 0
    liabilities = 0
    account_rows = []
    for account in accounts:
        balance = account_balance_cents(db, account)
        if account.account_type in LIABILITY_TYPES:
            liabilities += balance
        else:
            assets += balance
        account_rows.append({**account_response(db, account), "balance": cents_to_decimal(balance)})
    recent = list_transactions(db, user, limit=8)
    return {
        "assets": cents_to_decimal(assets),
        "liabilities": cents_to_decimal(liabilities),
        "net_position": cents_to_decimal(assets - liabilities),
        "available_cash": cents_to_decimal(sum(account_balance_cents(db, account) for account in accounts if account.account_type in LIQUID_ASSET_TYPES)),
        "account_count": len(accounts),
        "accounts": account_rows,
        "recent_transactions": recent,
    }
