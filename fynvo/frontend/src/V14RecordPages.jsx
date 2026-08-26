import { useMemo, useState } from 'react';

const statusLabel = (value) => String(value || 'active').replaceAll('_', ' ');

function RecordCard({ date, title, subtitle, amount, meta, status, onEdit, children }) {
  return <article className="v14-record-card">
    <div className="v14-record-date-row"><span>{date}</span>{status && <span className="v14-record-status">{status}</span>}</div>
    <div className="v14-record-main"><div><strong>{title}</strong>{subtitle && <small>{subtitle}</small>}</div>{amount && <strong className="v14-record-amount">{amount}</strong>}</div>
    {children}
    <div className="v14-record-footer"><span>{meta || ''}</span><button type="button" onClick={onEdit}>Edit</button></div>
  </article>;
}

function PageShell({ title, description, onAdd, children, secondaryAction }) {
  return <section className="panel v14-record-page"><div className="panel-head"><div><h2>{title}</h2><p className="muted">{description}</p></div><div className="v14-page-actions">{secondaryAction}<button className="primary ghost" type="button" onClick={onAdd}>+ Add</button></div></div><div className="v14-record-list">{children}</div></section>;
}

export function BillsPageV14({ rows, onEdit, onAdd, money, dateLabel, normaliseRecord, onOpenPaymentCentre }) {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [sort, setSort] = useState('due_asc');
  const visibleRows = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return [...rows]
      .filter((row) => !status || row.status === status)
      .filter((row) => !needle || [row.name, row.provider, row.payee_merchant, row.category, row.bill_type, row.account_name, row.card_name].some((value) => String(value || '').toLowerCase().includes(needle)))
      .sort((left, right) => {
        if (sort === 'amount_desc') return Number(right.expected_amount ?? right.amount ?? 0) - Number(left.expected_amount ?? left.amount ?? 0);
        if (sort === 'name_asc') return String(left.name || '').localeCompare(String(right.name || ''));
        const leftDate = String(left.due_date || left.expected_date || '9999-12-31');
        const rightDate = String(right.due_date || right.expected_date || '9999-12-31');
        return sort === 'due_desc' ? rightDate.localeCompare(leftDate) : leftDate.localeCompare(rightDate);
      });
  }, [rows, search, status, sort]);
  return <PageShell title="Bills" description="Manage one-off household obligations. Repeating payments belong in Recurring Expenses." onAdd={onAdd} secondaryAction={onOpenPaymentCentre && <button type="button" onClick={onOpenPaymentCentre}>Open Payment Centre</button>}>
    <div className="v14-bill-tools">
      <label><span>Search</span><input aria-label="Search bills" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name, merchant, category, account or card"/></label>
      <label><span>Status</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All statuses</option><option value="overdue">Overdue</option><option value="due_today">Due today</option><option value="upcoming">Upcoming</option><option value="expected_automatically">Expected automatically</option><option value="auto_payment_unconfirmed">Automatic payment not confirmed</option><option value="paid">Paid</option><option value="cancelled">Cancelled</option></select></label>
      <label><span>Sort</span><select value={sort} onChange={(event) => setSort(event.target.value)}><option value="due_asc">Due date, earliest first</option><option value="due_desc">Due date, latest first</option><option value="amount_desc">Amount, highest first</option><option value="name_asc">Name</option></select></label>
      {(search || status || sort !== 'due_asc') && <button type="button" onClick={() => { setSearch(''); setStatus(''); setSort('due_asc'); }}>Clear Filters</button>}
    </div>
    {visibleRows.length ? visibleRows.map((row) => <RecordCard key={row.id} date={dateLabel(row.due_date || row.expected_date)} title={row.name || row.provider || 'Bill'} subtitle={row.category || row.bill_type || row.provider || 'Uncategorised'} amount={money(row.status === 'paid' ? row.actual_amount ?? row.expected_amount : row.expected_amount ?? row.amount)} meta={row.card_name || row.account_name || row.payee_merchant || row.priority || ''} status={statusLabel(row.status)} onEdit={() => onEdit({ type: 'bills', label: 'Bill', row, values: normaliseRecord('bills', row) })}>
      <div className="v14-bill-payment-meta"><small>{row.payment_handling === 'automatic' ? 'Paid automatically' : 'Manual payment'} · {row.payment_method_label || statusLabel(row.payment_method || 'not_set')}</small>{row.card_name && row.linked_account_name && <small>Linked to account: {row.linked_account_name}</small>}{row.days_overdue ? <small className="negative">Overdue by {row.days_overdue} day{row.days_overdue === 1 ? '' : 's'}</small> : null}</div>
    </RecordCard>) : <p className="muted">{rows.length ? 'No Bills match these filters.' : 'No bills yet.'}</p>}
  </PageShell>;
}

export function IncomePageV14({ rows, onEdit, onAdd, money, dateLabel, normaliseRecord }) {
  return <PageShell title="Income" description="Recurring and expected household income." onAdd={onAdd}>{rows.length ? rows.map((row) => <RecordCard key={row.id} date={dateLabel(row.next_payment_date)} title={row.name || row.payer || 'Income'} subtitle={row.category || row.payer || 'Income'} amount={money(row.amount)} meta={row.frequency ? String(row.frequency).replaceAll('_', ' ') : row.account_name || ''} status={row.is_active === false ? 'inactive' : 'active'} onEdit={() => onEdit({ type: 'income', label: 'Income', row, values: normaliseRecord('income', row) })}/>) : <p className="muted">No income records yet.</p>}</PageShell>;
}

export function AccountsPageV14({ rows, cards = [], onEdit, onAdd, onOpenCards, money, normaliseRecord }) {
  return <PageShell title="Accounts" description="Household accounts, current position and linked Cards." onAdd={onAdd} secondaryAction={<button type="button" onClick={onOpenCards}>Manage Cards</button>}>{rows.length ? rows.map((row) => {
    const linkedCards = cards.filter((card) => Number(card.account_id) === Number(row.id));
    return <RecordCard key={row.id} date={row.institution || 'Account'} title={row.name || 'Account'} subtitle={String(row.account_type || 'account').replaceAll('_', ' ')} amount={money(row.current_balance ?? row.opening_balance)} meta={row.minimum_balance ? `Safety buffer ${money(row.minimum_balance)}` : row.account_suffix ? `••••${row.account_suffix}` : ''} status={row.archived_at ? 'inactive' : 'active'} onEdit={() => onEdit({ type: 'accounts', label: 'Account', row, values: normaliseRecord('accounts', row) })}>
      <div className="v17-account-cards"><span>Cards</span>{linkedCards.length ? linkedCards.map((card) => <small key={card.id}><strong>{card.display_name}</strong> · {card.card_type} · {card.is_active ? 'Active' : 'Inactive'}</small>) : <small>No Cards linked</small>}{onOpenCards && <button type="button" className="link-button" onClick={onOpenCards}>+ Add or manage Card</button>}</div>
    </RecordCard>;
  }) : <p className="muted">No accounts yet.</p>}</PageShell>;
}

export function PlannedSpendingPageV14({ rows, onEdit, onAdd, money, dateLabel, normaliseRecord }) {
  return <PageShell title="Planned Spending" description="Planned and committed future purchases." onAdd={onAdd}>{rows.length ? rows.map((row) => <RecordCard key={row.id} date={dateLabel(row.planned_date)} title={row.name || 'Planned Spending'} subtitle={row.category || 'Uncategorised'} amount={money(row.estimated_amount)} meta={row.priority || ''} status={statusLabel(row.status)} onEdit={() => onEdit({ type: 'planned', label: 'Planned Spending', row, values: normaliseRecord('planned', row) })}/>) : <p className="muted">No planned spending yet.</p>}</PageShell>;
}
