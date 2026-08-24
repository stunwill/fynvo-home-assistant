from __future__ import annotations
from calendar import monthrange
from datetime import date,timedelta
from typing import Any
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import Field
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession
from . import v1
from .auth import get_current_user
from .database import get_db
from .models import User
from .money import cents_to_decimal,parse_money
from .security import utcnow
router=APIRouter();DB=Depends(get_db);USER=Depends(get_current_user)
AUTOMATIC_METHODS={'direct_debit','automatic_card_payment'};PAYMENT_HANDLING={'automatic','manual'};TERMINAL_STATUSES={'paid','skipped','cancelled'};DEFAULT_GRACE_DAYS=3
class RecurringExpenseCreateV17(v1.RecurringExpenseCreateV1):
    payment_handling:str|None=None
    auto_payment_grace_days:int=Field(default=DEFAULT_GRACE_DAYS,ge=0,le=30)
def default_payment_handling(method):return 'automatic' if method in AUTOMATIC_METHODS else 'manual'
def _handling(method,requested):
    value=requested or default_payment_handling(method)
    if value not in PAYMENT_HANDLING:raise HTTPException(status_code=400,detail='Payment Handling must be Automatic or Manual')
    return value
def ensure_payment_schema(engine):
    with engine.begin() as connection:
        def columns(table):return {row[1] for row in connection.execute(text(f'PRAGMA table_info({table})')).all()}
        def add(table,definition):
            if definition.split()[0] not in columns(table):connection.execute(text(f'ALTER TABLE {table} ADD COLUMN {definition}'))
        add('recurring_expenses','payment_handling VARCHAR(20)');add('recurring_expenses','auto_payment_grace_days INTEGER NOT NULL DEFAULT 3')
        connection.execute(text("UPDATE recurring_expenses SET payment_handling=CASE WHEN payment_method IN ('direct_debit','automatic_card_payment') THEN 'automatic' ELSE 'manual' END WHERE payment_handling IS NULL OR payment_handling=''"))
        connection.execute(text('''CREATE TABLE IF NOT EXISTS scheduled_payments(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,recurring_expense_id INTEGER NOT NULL,expected_date DATE NOT NULL,expected_amount_cents INTEGER,status VARCHAR(40) NOT NULL,payment_method VARCHAR(40) NOT NULL,payment_handling VARCHAR(20) NOT NULL,account_id INTEGER,card_id INTEGER,actual_date DATE,actual_amount_cents INTEGER,matched_transaction_id INTEGER,match_confidence VARCHAR(20),confirmation_source VARCHAR(40),note TEXT,created_at DATETIME NOT NULL,updated_at DATETIME NOT NULL,UNIQUE(user_id,recurring_expense_id,expected_date))'''))
        connection.execute(text('''CREATE TABLE IF NOT EXISTS scheduled_payment_history(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,scheduled_payment_id INTEGER NOT NULL,from_status VARCHAR(40),to_status VARCHAR(40) NOT NULL,source VARCHAR(40) NOT NULL,note TEXT,created_at DATETIME NOT NULL)'''))
        connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS idx_scheduled_payment_occurrence ON scheduled_payments(user_id,recurring_expense_id,expected_date)'))
def create_recurring_v17(db,user,payload):
    method=payload.payment_method or ('direct_debit' if payload.direct_debit else 'not_set');handling=_handling(method,payload.payment_handling);base=v1.RecurringExpenseCreateV1(**payload.model_dump(exclude={'payment_handling','auto_payment_grace_days'}));created=v1.create_recurring_v1(db,user,base);db.execute(text('UPDATE recurring_expenses SET payment_handling=:handling,auto_payment_grace_days=:grace WHERE id=:id AND user_id=:uid'),{'handling':handling,'grace':payload.auto_payment_grace_days,'id':created['id'],'uid':user.id});db.commit();row=db.execute(text('SELECT * FROM recurring_expenses WHERE id=:id'),{'id':created['id']}).first();return v1._recurring_response(db,user,row)
def _add_months(value,months):
    index=value.month-1+months;year=value.year+index//12;month=index%12+1;return date(year,month,min(value.day,monthrange(year,month)[1]))
def _next_occurrence(value,frequency,interval_count):
    if frequency=='weekly':return value+timedelta(days=7)
    if frequency=='fortnightly':return value+timedelta(days=14)
    if frequency in {'every_28_days','every_4_weeks'}:return value+timedelta(days=28)
    if frequency=='monthly':return _add_months(value,1)
    if frequency=='quarterly':return _add_months(value,3)
    if frequency=='yearly':return _add_months(value,12)
    if frequency=='custom':return value+timedelta(days=max(int(interval_count or 1),1))
    return None
def _status_for(expected,handling,grace,today):
    if expected>today:return 'upcoming'
    if handling=='automatic':return 'paid' if expected<=today else 'upcoming'
    return 'due' if expected==today else 'overdue'
def ensure_scheduled_payments(db,user,horizon_days=120,today=None):
    today=today or date.today();end=today+timedelta(days=horizon_days);rows=db.execute(text('SELECT r.*,c.account_id AS card_account_id FROM recurring_expenses r LEFT JOIN cards c ON c.id=r.card_id AND c.user_id=r.user_id WHERE r.user_id=:uid AND r.is_active=1 AND r.next_due_date IS NOT NULL'),{'uid':user.id}).mappings().all();now=utcnow()
    for row in rows:
        due=row['next_due_date'] if isinstance(row['next_due_date'],date) else date.fromisoformat(str(row['next_due_date'])[:10]);method=row['payment_method'] or ('direct_debit' if row['direct_debit'] else 'not_set');handling=row.get('payment_handling') or default_payment_handling(method);account_id=int(row['card_account_id']) if method=='automatic_card_payment' and row.get('card_account_id') else row['account_id'];generated=0
        while due<=end and generated<400:
            if row.get('end_date') and due>date.fromisoformat(str(row['end_date'])[:10]):break
            status_name=_status_for(due,handling,int(row.get('auto_payment_grace_days') or DEFAULT_GRACE_DAYS),today);existing=db.execute(text('SELECT * FROM scheduled_payments WHERE user_id=:uid AND recurring_expense_id=:rid AND expected_date=:due'),{'uid':user.id,'rid':row['id'],'due':due}).mappings().first()
            if not existing:
                confirmation='automatic_schedule' if status_name=='paid' else None;actual_date=due if status_name=='paid' else None;actual_amount=row['amount_cents'] if status_name=='paid' else None
                db.execute(text('INSERT INTO scheduled_payments(user_id,recurring_expense_id,expected_date,expected_amount_cents,status,payment_method,payment_handling,account_id,card_id,actual_date,actual_amount_cents,confirmation_source,created_at,updated_at) VALUES(:uid,:rid,:due,:amount,:status,:method,:handling,:account,:card,:actual_date,:actual_amount,:source,:now,:now)'),{'uid':user.id,'rid':row['id'],'due':due,'amount':row['amount_cents'],'status':status_name,'method':method,'handling':handling,'account':account_id,'card':row['card_id'],'actual_date':actual_date,'actual_amount':actual_amount,'source':confirmation,'now':now})
            elif existing['status'] not in TERMINAL_STATUSES and existing['status']!=status_name:
                db.execute(text('UPDATE scheduled_payments SET status=:status,actual_date=:actual_date,actual_amount_cents=:actual_amount,confirmation_source=:source,updated_at=:now WHERE id=:id'),{'status':status_name,'actual_date':due if status_name=='paid' else existing.get('actual_date'),'actual_amount':row['amount_cents'] if status_name=='paid' else existing.get('actual_amount_cents'),'source':'automatic_schedule' if status_name=='paid' else existing.get('confirmation_source'),'now':now,'id':existing['id']})
            generated+=1;next_due=_next_occurrence(due,row['frequency'],row['interval_count']);
            if next_due is None or next_due<=due:break
            due=next_due
    db.commit()
def _scheduled_response(row):
    d=dict(row._mapping) if hasattr(row,'_mapping') else dict(row);return{'id':d['id'],'recurring_expense_id':d['recurring_expense_id'],'name':d.get('name'),'expected_date':d['expected_date'],'expected_amount':cents_to_decimal(d['expected_amount_cents']) if d.get('expected_amount_cents') is not None else None,'status':d['status'],'payment_method':d['payment_method'],'payment_method_label':v1.PAYMENT_METHODS.get(d['payment_method'],d['payment_method']),'payment_handling':d['payment_handling'],'account_id':d.get('account_id'),'account_name':d.get('account_name'),'card_id':d.get('card_id'),'card_name':d.get('card_name'),'linked_account_name':d.get('linked_account_name'),'actual_date':d.get('actual_date'),'actual_amount':cents_to_decimal(d['actual_amount_cents']) if d.get('actual_amount_cents') is not None else None,'confirmation_source':d.get('confirmation_source')}
@router.put('/recurring-expenses/{expense_id}')
def update_recurring_v17(expense_id:int,payload:dict[str,Any],current_user:User=USER,db:DbSession=DB):
    existing=db.execute(text('SELECT * FROM recurring_expenses WHERE id=:id AND user_id=:uid'),{'id':expense_id,'uid':current_user.id}).mappings().first()
    if not existing:raise HTTPException(status_code=404,detail='Recurring Expense not found')
    values=dict(payload);requested_handling=values.pop('payment_handling',existing.get('payment_handling'));requested_grace=values.pop('auto_payment_grace_days',existing.get('auto_payment_grace_days') or DEFAULT_GRACE_DAYS);result=v1.update_recurring_v1(expense_id,values,current_user,db);handling=_handling(result.get('payment_method'),requested_handling);db.execute(text('UPDATE recurring_expenses SET payment_handling=:handling,auto_payment_grace_days=:grace WHERE id=:id AND user_id=:uid'),{'handling':handling,'grace':int(requested_grace),'id':expense_id,'uid':current_user.id});db.commit();row=db.execute(text('SELECT * FROM recurring_expenses WHERE id=:id'),{'id':expense_id}).first();return v1._recurring_response(db,current_user,row)
@router.get('/payment-methods')
def payment_methods(current_user:User=USER):return [{'id':key,'label':label,'default_handling':default_payment_handling(key)} for key,label in v1.PAYMENT_METHODS.items()]
@router.get('/scheduled-payments')
def scheduled_payments(status_filter:str|None=None,current_user:User=USER,db:DbSession=DB):
    ensure_scheduled_payments(db,current_user);sql="SELECT sp.*,r.name,a.name AS account_name,CASE WHEN c.id IS NULL THEN NULL ELSE c.name || ' ••••' || c.last_four END AS card_name,ca.name AS linked_account_name FROM scheduled_payments sp JOIN recurring_expenses r ON r.id=sp.recurring_expense_id LEFT JOIN accounts a ON a.id=sp.account_id LEFT JOIN cards c ON c.id=sp.card_id LEFT JOIN accounts ca ON ca.id=c.account_id WHERE sp.user_id=:uid";params={'uid':current_user.id};
    if status_filter:sql+=' AND sp.status=:status';params['status']=status_filter
    sql+=' ORDER BY sp.expected_date,sp.id';return[_scheduled_response(row) for row in db.execute(text(sql),params).all()]
@router.get('/payments/attention')
def payment_attention(current_user:User=USER,db:DbSession=DB):
    ensure_scheduled_payments(db,current_user);rows=db.execute(text("SELECT sp.*,r.name,a.name AS account_name FROM scheduled_payments sp JOIN recurring_expenses r ON r.id=sp.recurring_expense_id LEFT JOIN accounts a ON a.id=sp.account_id WHERE sp.user_id=:uid AND sp.status IN ('overdue','due','auto_payment_unconfirmed') ORDER BY sp.expected_date"),{'uid':current_user.id}).all();return[_scheduled_response(row) for row in rows]
@router.post('/scheduled-payments/{payment_id}/mark-paid')
def mark_paid(payment_id:int,payload:dict[str,Any],current_user:User=USER,db:DbSession=DB):
    row=db.execute(text('SELECT * FROM scheduled_payments WHERE id=:id AND user_id=:uid'),{'id':payment_id,'uid':current_user.id}).mappings().first()
    if not row:raise HTTPException(status_code=404,detail='Scheduled Payment not found')
    if row['status']=='paid':return{'status':'paid','scheduled_payment_id':payment_id,'already_paid':True}
    if row['status'] in {'skipped','cancelled'}:raise HTTPException(status_code=409,detail='Skipped or cancelled payments cannot be marked paid')
    actual=parse_money(payload.get('paid_amount')) if payload.get('paid_amount') not in(None,'') else row['expected_amount_cents'];paid_date=date.fromisoformat(str(payload.get('paid_date') or date.today())[:10]);db.execute(text("UPDATE scheduled_payments SET status='paid',actual_date=:date,actual_amount_cents=:amount,confirmation_source='manual',note=:note,updated_at=:now WHERE id=:id"),{'date':paid_date,'amount':actual,'note':payload.get('note'),'now':utcnow(),'id':payment_id});db.commit();return{'status':'paid','scheduled_payment_id':payment_id,'actual_amount':cents_to_decimal(actual)}
@router.post('/scheduled-payments/{payment_id}/skip')
def skip_payment(payment_id:int,payload:dict[str,Any],current_user:User=USER,db:DbSession=DB):
    row=db.execute(text('SELECT * FROM scheduled_payments WHERE id=:id AND user_id=:uid'),{'id':payment_id,'uid':current_user.id}).mappings().first()
    if not row:raise HTTPException(status_code=404,detail='Scheduled Payment not found')
    if row['status']=='skipped':return{'status':'skipped','scheduled_payment_id':payment_id,'already_skipped':True}
    if row['status']=='paid':raise HTTPException(status_code=409,detail='Paid payments cannot be skipped')
    db.execute(text("UPDATE scheduled_payments SET status='skipped',note=:note,updated_at=:now WHERE id=:id"),{'note':payload.get('note'),'now':utcnow(),'id':payment_id});db.commit();return{'status':'skipped','scheduled_payment_id':payment_id}
