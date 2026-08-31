from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session as DbSession

from . import (
    accounts_cards_v1163,
    intelligence,
    v09,
    v12_mount,
    v13_cashflow,
)
from .auth import (
    SESSION_COOKIE,
    authenticate_user,
    create_initial_admin,
    get_client_key,
    get_current_user,
    revoke_current_session,
    setup_required,
    start_session,
)
from .config import APP_VERSION
from .dashboard import get_overview
from .database import get_db, run_migrations
from .finance import (
    annual_matrix,
    cancel_planned,
    create_bill,
    create_income,
    create_planned,
    create_recurring,
    ensure_seed_data,
    list_bills,
    list_income,
    list_planned,
    list_recurring,
    month_week_matrix,
    schedule_summary,
    today_local,
    update_planned,
)
from .forecast import (
    compare_scenario,
    create_effective_change,
    forecast_drilldown,
    generate_forecast,
    list_effective_changes,
)
from .ledger import (
    ACCOUNT_TYPES,
    archive_account,
    create_account,
    create_transaction,
    create_transfer,
    dashboard_position,
    delete_transaction,
    delete_transfer,
    get_account,
    list_accounts,
    list_transactions,
    running_transactions,
    update_account,
    update_transaction,
    update_transfer,
)
from .models import User
from .money import cents_to_decimal, parse_money
from .schemas import (
    AccountCreate,
    AccountUpdate,
    AuthStateResponse,
    BillCreate,
    DashboardResponse,
    IncomeCreate,
    LoginRequest,
    PasswordChangeRequest,
    PlannedSpendingCreate,
    PlannedSpendingUpdate,
    RecurringExpenseCreate,
    SetupRequest,
    TransactionCreate,
    TransactionUpdate,
    TransferCreate,
    TransferUpdate,
    UserResponse,
)
from .security import hash_password, verify_password

DB_DEPENDENCY = Depends(get_db)
USER_DEPENDENCY = Depends(get_current_user)


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    yield


app = FastAPI(title="Fynvo API", version=APP_VERSION, description="Fynvo household cash-flow forecasting API.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[], allow_credentials=True, allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type"])
app.include_router(v09.router)
app.include_router(intelligence.router)
app.include_router(v12_mount.router, prefix="/api")
app.include_router(v13_cashflow.router)
app.include_router(accounts_cards_v1163.router, prefix="/api")


def public_user(user: User) -> UserResponse:
    return UserResponse(id=user.id, username=user.username, display_name=user.display_name, is_admin=user.is_admin)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "Fynvo", "version": APP_VERSION}


@app.get("/api/version")
def version() -> dict[str, str]:
    return {"version": APP_VERSION}


@app.get("/api/auth/state", response_model=AuthStateResponse)
def auth_state(response: Response, db: DbSession = DB_DEPENDENCY, session_token: str | None = SESSION_COOKIE):
    try:
        user = get_current_user(response=response, db=db, session_token=session_token)
        return AuthStateResponse(authenticated=True, setup_required=False, user=public_user(user))
    except HTTPException:
        return AuthStateResponse(authenticated=False, setup_required=setup_required(db), user=None)


@app.post("/api/auth/setup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def setup_admin(payload: SetupRequest, response: Response, db: DbSession = DB_DEPENDENCY):
    user = create_initial_admin(db, payload.username, payload.password, payload.display_name)
    start_session(response, db, user)
    return public_user(user)


@app.post("/api/auth/login", response_model=UserResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: DbSession = DB_DEPENDENCY):
    user = authenticate_user(db, payload.username, payload.password, get_client_key(request))
    start_session(response, db, user)
    return public_user(user)


@app.post("/api/auth/logout")
def logout(response: Response, db: DbSession = DB_DEPENDENCY, session_token: str | None = SESSION_COOKIE):
    revoke_current_session(response, db, session_token)
    return {"status": "ok"}


@app.get("/api/auth/me", response_model=UserResponse)
def me(current_user: User = USER_DEPENDENCY):
    return public_user(current_user)


@app.post("/api/auth/change-password")
def change_password(payload: PasswordChangeRequest, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"status": "ok"}


@app.get("/api/dashboard/overview", response_model=DashboardResponse)
def dashboard_overview(range_days: int = 90, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    if range_days not in (30, 60, 90):
        range_days = 90
    ensure_seed_data(db, current_user)
    overview = get_overview(range_days)
    position = dashboard_position(db, current_user)
    start = today_local()
    scheduled = schedule_summary(db, current_user, start, start + timedelta(days=range_days))
    forecast = generate_forecast(db, current_user, "30d", "baseline")
    bills = list_bills(db, current_user)
    recurring = list_recurring(db, current_user)
    planned = list_planned(db, current_user)
    overdue_amount = sum(parse_money(item["amount"]) for item in bills if item["status"] == "overdue" and item["amount"] is not None)
    planned_forecast = sum(parse_money(item["estimated_amount"]) for item in planned if item["include_in_forecast"] and item["status"] in {"planned", "committed"} and item["estimated_amount"] is not None)
    overview.summary.available_cash = position["available_cash"]
    overview.summary.net_position = position["net_position"]
    overview.summary.assets = position["assets"]
    overview.summary.liabilities = position["liabilities"]
    overview.summary.account_count = position["account_count"]
    overview.summary.income = scheduled["income"]
    overview.summary.recurring_bills = scheduled["commitments"]
    overview.summary.planned_spending = cents_to_decimal(planned_forecast)
    overview.summary.projected_balance = forecast["final_balance"]
    overview.summary.overdue_amount = cents_to_decimal(overdue_amount)
    overview.summary.incomplete_recurring_count = len([item for item in recurring if "incomplete" in item["completeness"]])
    overview.summary.incomplete_planned_count = len([item for item in planned if item["completeness"] == "incomplete"])
    overview.summary.planned_item_count = len([item for item in planned if item["status"] != "cancelled"])
    overview.summary.high_priority_planned_count = len([item for item in planned if item["priority"] == "high" and item["status"] != "cancelled"])
    overview.summary.bills_due_count = len([item for item in bills if item["status"] in {"overdue", "due_today", "due_soon"}])
    overview.recent_transactions = position["recent_transactions"]
    overview.upcoming = [item for item in scheduled["events"] if item.get("status") != "paid"][:12]
    overview.top_planned_spending = [item for item in planned if item["estimated_amount"] is not None and item["status"] != "cancelled"][:5]
    overview.quick_stats = [
        {"label": "Incomplete recurring records", "value": overview.summary.incomplete_recurring_count},
        {"label": "Incomplete planned items", "value": overview.summary.incomplete_planned_count},
        {"label": "30-day forecast balance", "value": forecast["final_balance"]},
        {"label": "Lowest forecast balance", "value": forecast["lowest_balance"]["balance"]},
    ]
    if forecast["shortfall"]:
        overview.quick_stats.append({"label": "Projected shortfall", "value": forecast["shortfall"]["balance"], "date": forecast["shortfall"]["date"]})
    overview.empty_state = "Income, recurring expenses, bills, planned spending and forecasts are powering this overview."
    return overview


@app.get("/api/accounts/meta")
def account_meta(current_user: User = USER_DEPENDENCY):
    return {"account_types": sorted(ACCOUNT_TYPES)}


@app.get("/api/accounts")
def accounts(include_archived: bool = False, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return list_accounts(db, current_user, include_archived)


@app.post("/api/accounts", status_code=status.HTTP_201_CREATED)
def add_account(payload: AccountCreate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return create_account(db, current_user, payload)


@app.get("/api/accounts/{account_id}")
def account_detail(account_id: int, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    account = get_account(db, current_user, account_id)
    accounts_list = list_accounts(db, current_user, True)
    return {"account": accounts_list[[row["id"] for row in accounts_list].index(account.id)], "transactions": running_transactions(db, current_user, account.id)}


@app.put("/api/accounts/{account_id}")
def edit_account(account_id: int, payload: AccountUpdate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return update_account(db, current_user, account_id, payload)


@app.post("/api/accounts/{account_id}/archive")
def archive(account_id: int, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return archive_account(db, current_user, account_id)


@app.get("/api/transactions")
def transactions(account_id: int | None = None, transaction_type: str | None = None, date_from: date | None = None, date_to: date | None = None, search: str | None = None, limit: int = Query(100, ge=1, le=500), current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return list_transactions(db, current_user, account_id, transaction_type, date_from, date_to, search, limit)


@app.post("/api/transactions", status_code=status.HTTP_201_CREATED)
def add_transaction(payload: TransactionCreate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return create_transaction(db, current_user, payload)


@app.put("/api/transactions/{transaction_id}")
def edit_transaction(transaction_id: int, payload: TransactionUpdate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return update_transaction(db, current_user, transaction_id, payload)


@app.delete("/api/transactions/{transaction_id}")
def remove_transaction(transaction_id: int, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return delete_transaction(db, current_user, transaction_id)


@app.post("/api/transfers", status_code=status.HTTP_201_CREATED)
def add_transfer(payload: TransferCreate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return create_transfer(db, current_user, payload)


@app.put("/api/transfers/{transfer_id}")
def edit_transfer(transfer_id: int, payload: TransferUpdate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return update_transfer(db, current_user, transfer_id, payload)


@app.delete("/api/transfers/{transfer_id}")
def remove_transfer(transfer_id: int, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return delete_transfer(db, current_user, transfer_id)


@app.get("/api/income")
def income(current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return list_income(db, current_user)


@app.post("/api/income", status_code=status.HTTP_201_CREATED)
def add_income(payload: IncomeCreate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return create_income(db, current_user, payload)


@app.get("/api/recurring-expenses")
def recurring_expenses(filter: str = "all", current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return list_recurring(db, current_user, filter)


@app.post("/api/recurring-expenses", status_code=status.HTTP_201_CREATED)
def add_recurring(payload: RecurringExpenseCreate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return create_recurring(db, current_user, payload)


@app.get("/api/bills")
def bills(filter: str = "all", current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return list_bills(db, current_user, filter)


@app.post("/api/bills", status_code=status.HTTP_201_CREATED)
def add_bill(payload: BillCreate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return create_bill(db, current_user, payload)


@app.get("/api/planned-spending")
def planned_spending(filter: str = "all", search: str | None = None, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return list_planned(db, current_user, filter, search)


@app.post("/api/planned-spending", status_code=status.HTTP_201_CREATED)
def add_planned_spending(payload: PlannedSpendingCreate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return create_planned(db, current_user, payload)


@app.put("/api/planned-spending/{planned_id}")
def edit_planned_spending(planned_id: int, payload: PlannedSpendingUpdate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return update_planned(db, current_user, planned_id, payload)


@app.post("/api/planned-spending/{planned_id}/cancel")
def cancel_planned_spending(planned_id: int, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return cancel_planned(db, current_user, planned_id)


@app.get("/api/schedule")
def schedule(view: str = "month", start: date | None = None, end: date | None = None, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    start = start or today_local()
    if end is None:
        end = start + timedelta(days=7 if view == "week" else 28 if view == "pay_cycle" else 31)
    return schedule_summary(db, current_user, start, end)


@app.get("/api/schedule/month/{year}/{month}")
def schedule_month(year: int, month: int, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return month_week_matrix(db, current_user, year, month)


@app.get("/api/schedule/year/{year}")
def schedule_year(year: int, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return annual_matrix(db, current_user, year)


@app.get("/api/forecast")
def forecast(horizon: str = "30d", mode: str = "baseline", start: date | None = None, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    if mode not in {"baseline", "expected"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mode must be baseline or expected")
    return generate_forecast(db, current_user, horizon, mode, start)


@app.get("/api/forecast/drilldown")
def forecast_breakdown(period: str = "month", horizon: str = "30d", mode: str = "baseline", current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    if period not in {"day", "month"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period must be day or month")
    return forecast_drilldown(db, current_user, horizon, mode, period)


@app.post("/api/forecast/effective-change", status_code=status.HTTP_201_CREATED)
def add_effective_change(payload: dict, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return create_effective_change(db, current_user, payload)


@app.get("/api/forecast/effective-changes")
def effective_changes(current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return list_effective_changes(db, current_user)


@app.post("/api/scenarios/compare")
def scenario_compare(payload: dict, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return compare_scenario(db, current_user, payload)


@app.get("/api/files/{filename}")
def file_download(filename: str):
    safe_name = Path(filename).name
    target = Path("/data") / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(target)


@app.get("/{full_path:path}", response_class=HTMLResponse)
def frontend(full_path: str, request: Request):
    static_root = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    candidate = static_root / full_path
    if full_path and candidate.is_file():
        return FileResponse(candidate)
    index = static_root / "index.html"
    if index.exists():
        return FileResponse(index)
    return HTMLResponse("Fynvo frontend is not built.", status_code=503)
