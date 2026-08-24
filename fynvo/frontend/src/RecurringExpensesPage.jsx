import { useEffect, useMemo, useRef, useState } from 'react';

const api = (path, options = {}) => fetch(`api${path}`, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
const DAY_MS = 86400000;
export const DEFAULT_FILTERS = { rangeDays: 30, frequency: 'all', category: 'all', paymentMethod: 'all', paymentStatus: 'all', overdueOnly: false, attentionOnly: false };
export const RANGE_OPTIONS = [7, 14, 30, 60, 90];
export const PAYMENT_METHOD_LABELS = { direct_debit: 'Direct Debit', automatic_card_payment: 'Automatic Card Payment', bpay: 'BPAY', bank_transfer: 'Bank Transfer', manual_payment: 'Manual Payment', cash: 'Cash', other: 'Other', not_set: 'Not Set' };
export const PAYMENT_STATUS_LABELS = { upcoming: 'Upcoming', due: 'Requires payment', overdue: 'Overdue', expected_automatically: 'Expected automatically', auto_payment_unconfirmed: 'Automatic payment not confirmed', paid: 'Paid', skipped: 'Skipped', cancelled: 'Cancelled' };
const ATTENTION = new Set(['due', 'overdue', 'auto_payment_unconfirmed']);
const TERMINAL = new Set(['paid', 'skipped', 'cancelled']);

const iso = (value) => String(value || '').slice(0, 10);
const dateAtMidnight = (value = new Date()) => { const d = value instanceof Date ? value : new Date(`${iso(value)}T00:00:00`); return new Date(d.getFullYear(), d.getMonth(), d.getDate()); };
const dayDiff = (value, reference = new Date()) => Math.round((dateAtMidnight(value) - dateAtMidnight(reference)) / DAY_MS);
const compareText = (a, b) => String(a || '').localeCompare(String(b || ''), undefined, { sensitivity: 'base', numeric: true });
const frequencyLabel = (value) => { const raw = String(value || '').trim(); if (!raw) return 'Not set'; if (['every_28_days', 'every_4_weeks'].includes(raw)) return 'Every 28 days'; if (raw === 'yearly') return 'Annually'; return raw.replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase()); };
const formatMonthKey = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
const monthTitle = (date) => new Intl.DateTimeFormat('en-AU', { month: 'long', year: 'numeric' }).format(date);
const categoryName = (rule, categories) => rule?.category || categories.find((item) => Number(item.id) === Number(rule?.category_id))?.name || 'Uncategorised';
const sourceText = (payment) => payment.card_name || payment.account_name || '';
const relativeDue = (payment, reference = new Date()) => {
  const diff = dayDiff(payment.expected_date, reference);
  if (payment.status === 'overdue' || diff < 0 && !TERMINAL.has(payment.status)) return { label: 'Overdue', group: 'OVERDUE', tone: 'danger', diff };
  if (diff === 0) return { label: 'Due today', group: 'TODAY', tone: 'warning', diff };
  if (diff === 1) return { label: 'Tomorrow', group: 'TOMORROW', tone: 'warning', diff };
  if (diff <= 3) return { label: `In ${diff} days`, group: 'IN 3 DAYS', tone: 'soon', diff };
  if (diff <= 7) return { label: `In ${diff} days`, group: 'IN 7 DAYS', tone: 'soon', diff };
  return { label: diff > 0 ? `In ${diff} days` : 'Completed', group: 'LATER', tone: 'normal', diff };
};
const paymentPriority = (payment) => payment.status === 'overdue' ? 0 : payment.status === 'due' ? 1 : payment.status === 'auto_payment_unconfirmed' ? 2 : payment.payment_handling === 'manual' && !TERMINAL.has(payment.status) ? 3 : 4;

export function enrichScheduledPayments({ scheduledPayments = [], recurring = [], categories = [], cards = [], accounts = [] }) {
  const rules = new Map(recurring.map((row) => [Number(row.id), row]));
  const cardMap = new Map(cards.map((row) => [Number(row.id), row]));
  const accountMap = new Map(accounts.map((row) => [Number(row.id), row]));
  return scheduledPayments.map((payment) => {
    const rule = rules.get(Number(payment.recurring_expense_id)) || {};
    const card = cardMap.get(Number(payment.card_id));
    const linkedAccount = card ? accountMap.get(Number(card.account_id)) : null;
    return {
      ...payment,
      name: payment.name || rule.name || 'Recurring expense',
      amount: payment.expected_amount,
      date: iso(payment.expected_date),
      frequency: rule.frequency || '',
      category: categoryName(rule, categories),
      merchant: rule.payee_merchant || '',
      rule,
      card,
      displaySource: payment.card_name || card?.display_name || payment.account_name || '',
      linkedAccountName: payment.linked_account_name || linkedAccount?.name || '',
    };
  });
}

export function activeFilterCount(filters) {
  return Number(filters.rangeDays !== DEFAULT_FILTERS.rangeDays) + Number(filters.frequency !== 'all') + Number(filters.category !== 'all') + Number(filters.paymentMethod !== 'all') + Number(filters.paymentStatus !== 'all') + Number(filters.overdueOnly) + Number(filters.attentionOnly);
}

export function filterScheduledPayments(rows, filters, search, referenceDate = new Date(), temporalScope = 'range', calendarMonth = referenceDate) {
  const query = search.trim().toLowerCase();
  return rows.filter((row) => {
    const diff = dayDiff(row.expected_date, referenceDate);
    if (temporalScope === 'range' && (diff < 0 && row.status !== 'overdue' || diff > filters.rangeDays)) return false;
    if (temporalScope === 'month' && formatMonthKey(dateAtMidnight(row.expected_date)) !== formatMonthKey(calendarMonth)) return false;
    if (filters.frequency !== 'all' && String(row.frequency) !== filters.frequency) return false;
    if (filters.category !== 'all' && row.category !== filters.category) return false;
    if (filters.paymentMethod !== 'all' && String(row.payment_method || 'not_set') !== filters.paymentMethod) return false;
    if (filters.paymentStatus !== 'all' && String(row.status) !== filters.paymentStatus) return false;
    if (filters.overdueOnly && row.status !== 'overdue') return false;
    if (filters.attentionOnly && !ATTENTION.has(row.status)) return false;
    if (query && !`${row.name} ${row.category} ${row.merchant} ${PAYMENT_METHOD_LABELS[row.payment_method] || ''} ${row.displaySource} ${row.linkedAccountName}`.toLowerCase().includes(query)) return false;
    return true;
  });
}

export function sortScheduledPayments(rows, sort) {
  const direction = sort.direction === 'desc' ? -1 : 1;
  return [...rows].sort((a, b) => {
    let result = 0;
    if (sort.key === 'name') result = compareText(a.name, b.name);
    else if (sort.key === 'amount') result = Number(a.expected_amount || 0) - Number(b.expected_amount || 0);
    else if (sort.key === 'frequency') result = compareText(frequencyLabel(a.frequency), frequencyLabel(b.frequency));
    else if (sort.key === 'status') result = paymentPriority(a) - paymentPriority(b) || compareText(a.status, b.status);
    else result = compareText(iso(a.expected_date), iso(b.expected_date));
    return (result || compareText(a.name, b.name)) * direction;
  });
}

export function summarisePayments(rows, referenceDate = new Date()) {
  const total = rows.reduce((sum, row) => sum + Number(row.expected_amount || 0), 0);
  const unresolved = rows.filter((row) => !TERMINAL.has(row.status));
  const next = [...unresolved].sort((a, b) => compareText(iso(a.expected_date), iso(b.expected_date)))[0] || null;
  const largest = [...rows].sort((a, b) => Number(b.expected_amount || 0) - Number(a.expected_amount || 0))[0] || null;
  const nextMonth = new Date(referenceDate.getFullYear(), referenceDate.getMonth() + 1, 1);
  const boundary = iso(nextMonth.toISOString());
  const bucketRows = [
    ['Before ' + new Intl.DateTimeFormat('en-AU', { day: 'numeric', month: 'short' }).format(nextMonth), rows.filter((r) => iso(r.expected_date) < boundary)],
    ['On ' + new Intl.DateTimeFormat('en-AU', { day: 'numeric', month: 'short' }).format(nextMonth), rows.filter((r) => iso(r.expected_date) === boundary)],
    ['After ' + new Intl.DateTimeFormat('en-AU', { day: 'numeric', month: 'short' }).format(nextMonth), rows.filter((r) => iso(r.expected_date) > boundary)],
  ];
  const breakdown = bucketRows.map(([label, bucket]) => ({ label, count: bucket.length, total: bucket.reduce((sum, row) => sum + Number(row.expected_amount || 0), 0) }));
  const exclusiveStatus = { automatic: [], manual: [], paid: [], attention: [] };
  rows.forEach((row) => {
    if (row.status === 'paid') exclusiveStatus.paid.push(row);
    else if (ATTENTION.has(row.status)) exclusiveStatus.attention.push(row);
    else if (row.payment_handling === 'automatic' || row.status === 'expected_automatically') exclusiveStatus.automatic.push(row);
    else exclusiveStatus.manual.push(row);
  });
  const status = Object.fromEntries(Object.entries(exclusiveStatus).map(([key, bucket]) => [key, { count: bucket.length, total: bucket.reduce((sum, row) => sum + Number(row.expected_amount || 0), 0) }]));
  return { total, count: rows.length, average: rows.length ? total / rows.length : 0, next, largest, breakdown, status };
}

function navigateReload(view) { localStorage.setItem('fynvo.view', view); window.location.reload(); }
function StatusBadge({ payment }) { return <span className={`recurring-v18-status status-${payment.status}`}>{PAYMENT_STATUS_LABELS[payment.status] || payment.status}</span>; }
function Due({ payment, dateLabel }) { const due = relativeDue(payment); return <div className={`recurring-v18-due ${due.tone}`}><strong>{dateLabel(payment.expected_date)}</strong><small>{due.label}</small></div>; }
function PaymentSource({ payment }) { const method = PAYMENT_METHOD_LABELS[payment.payment_method] || payment.payment_method_label || 'Not Set'; return <div className="recurring-v18-payment"><div><strong>{method}</strong><StatusBadge payment={payment}/></div>{payment.displaySource && <small>{payment.displaySource}</small>}{payment.payment_method === 'automatic_card_payment' && payment.linkedAccountName && <small>Linked to account: {payment.linkedAccountName}</small>}{payment.status === 'paid' && payment.matched_transaction_id && <small>Matched to transaction · {payment.actual_date || payment.expected_date}{payment.actual_amount != null ? ` · ${payment.actual_amount}` : ''}</small>}</div>; }

function PaymentActions({ payment, onEdit, normaliseRecord, onRefresh, money, dateLabel }) {
  const [open, setOpen] = useState(false); const [paying, setPaying] = useState(false); const root = useRef(null);
  const [form, setForm] = useState({ paid_date: new Date().toISOString().slice(0, 10), paid_amount: payment.expected_amount || '', note: '' });
  useEffect(() => { if (!open) return undefined; const close = (event) => { if (event.key === 'Escape' || event.type === 'mousedown' && !root.current?.contains(event.target)) setOpen(false); }; document.addEventListener('keydown', close); document.addEventListener('mousedown', close); return () => { document.removeEventListener('keydown', close); document.removeEventListener('mousedown', close); }; }, [open]);
  const markPaid = async (event) => { event.preventDefault(); const response = await api(`/scheduled-payments/${payment.id}/mark-paid`, { method: 'POST', body: JSON.stringify(form) }); if (response.ok) { setPaying(false); setOpen(false); await onRefresh?.(); } };
  const skip = async () => { const response = await api(`/scheduled-payments/${payment.id}/skip`, { method: 'POST', body: JSON.stringify({ note: 'Skipped from Recurring Expenses' }) }); if (response.ok) { setOpen(false); await onRefresh?.(); } };
  const editable = payment.rule && onEdit;
  const canPay = payment.payment_handling === 'manual' && ['due', 'overdue', 'upcoming'].includes(payment.status);
  return <div className="recurring-v18-actions" ref={root}><button type="button" className="recurring-v18-action-trigger" aria-label={`Actions for ${payment.name}`} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((v) => !v)}>⋯</button>{open && <div className="recurring-v18-action-menu" role="menu">{canPay && <button role="menuitem" type="button" onClick={() => setPaying(true)}>Mark as paid</button>}{payment.status === 'auto_payment_unconfirmed' && <button role="menuitem" type="button" onClick={() => navigateReload('Review Queue')}>Review payment</button>}{payment.status === 'paid' && payment.matched_transaction_id && <button role="menuitem" type="button" onClick={() => navigateReload('Review Queue')}>Review match</button>}{editable && <button role="menuitem" type="button" onClick={() => { setOpen(false); onEdit({ type: 'recurring', label: 'Recurring Expense', row: payment.rule, values: normaliseRecord('recurring', payment.rule) }); }}>Edit recurring expense</button>}{!TERMINAL.has(payment.status) && <button role="menuitem" type="button" onClick={skip}>Skip payment</button>}</div>}{paying && <div className="modal-backdrop recurring-v18-modal-layer"><form className="modal recurring-v18-pay-modal" onSubmit={markPaid}><div className="panel-head"><div><h2>Mark as paid</h2><p>{payment.name} · {money(payment.expected_amount)}</p></div><button type="button" aria-label="Close" onClick={() => setPaying(false)}>×</button></div><div className="detail-grid"><div className="detail-item"><span>Expected date</span><strong>{dateLabel(payment.expected_date)}</strong></div><div className="detail-item"><span>Expected amount</span><strong>{money(payment.expected_amount)}</strong></div></div><div className="form-grid"><label className="field"><span>Actual paid date</span><input type="date" value={form.paid_date} onChange={(e) => setForm({ ...form, paid_date: e.target.value })}/></label><label className="field"><span>Actual amount</span><input value={form.paid_amount} onChange={(e) => setForm({ ...form, paid_amount: e.target.value })}/></label><label className="field wide"><span>Note (optional)</span><input value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })}/></label></div><div className="modal-actions"><button type="button" onClick={() => setPaying(false)}>Cancel</button><button className="primary">Mark as paid</button></div></form></div>}</div>;
}

function FilterSheet({ applied, onApply, frequencies, categories, open, onClose }) {
  const [draft, setDraft] = useState(applied); const dialogRef = useRef(null); const priorFocus = useRef(null);
  useEffect(() => { if (!open) return undefined; priorFocus.current = document.activeElement; setDraft(applied); const timer = requestAnimationFrame(() => dialogRef.current?.querySelector('select, input, button')?.focus()); const key = (event) => { if (event.key === 'Escape') onClose(); if (event.key === 'Tab') { const items = [...dialogRef.current.querySelectorAll('button,select,input')].filter((el) => !el.disabled); if (!items.length) return; const first = items[0], last = items.at(-1); if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); } else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); } } }; document.addEventListener('keydown', key); return () => { cancelAnimationFrame(timer); document.removeEventListener('keydown', key); priorFocus.current?.focus?.(); }; }, [open]);
  if (!open) return null;
  const set = (key, value) => setDraft((current) => ({ ...current, [key]: value }));
  return <div className="recurring-v18-sheet-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><section className="recurring-v18-sheet" role="dialog" aria-modal="true" aria-labelledby="recurring-filter-title" ref={dialogRef}><div className="recurring-v18-sheet-head"><h2 id="recurring-filter-title">Filters</h2><button type="button" aria-label="Close filters" onClick={onClose}>×</button></div><div className="recurring-v18-sheet-body"><label>Date range<select value={draft.rangeDays} onChange={(e) => set('rangeDays', Number(e.target.value))}>{RANGE_OPTIONS.map((d) => <option key={d} value={d}>Next {d} days</option>)}</select></label><label>Frequency<select value={draft.frequency} onChange={(e) => set('frequency', e.target.value)}><option value="all">All frequencies</option>{frequencies.map((v) => <option key={v} value={v}>{frequencyLabel(v)}</option>)}</select></label><label>Category<select value={draft.category} onChange={(e) => set('category', e.target.value)}><option value="all">All categories</option>{categories.map((v) => <option key={v} value={v}>{v}</option>)}</select></label><label>Payment method<select value={draft.paymentMethod} onChange={(e) => set('paymentMethod', e.target.value)}><option value="all">All payment methods</option>{Object.entries(PAYMENT_METHOD_LABELS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label><label>Payment status<select value={draft.paymentStatus} onChange={(e) => set('paymentStatus', e.target.value)}><option value="all">All statuses</option>{Object.entries(PAYMENT_STATUS_LABELS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label><label className="recurring-v18-toggle"><input type="checkbox" checked={draft.overdueOnly} onChange={(e) => set('overdueOnly', e.target.checked)}/><span>Show overdue only</span></label><label className="recurring-v18-toggle"><input type="checkbox" checked={draft.attentionOnly} onChange={(e) => set('attentionOnly', e.target.checked)}/><span>Show payments requiring attention</span></label></div><div className="recurring-v18-sheet-actions"><button type="button" onClick={() => setDraft({ ...DEFAULT_FILTERS })}>Clear filters</button><button type="button" className="primary" onClick={() => { onApply(draft); onClose(); }}>Apply filters</button></div></section></div>;
}

function Summary({ summary, filters, money, dateLabel, attentionCount }) {
  const [expanded, setExpanded] = useState(false);
  return <section className={`recurring-v18-summary ${expanded ? 'expanded' : ''}`}><div className="recurring-v18-summary-primary"><div><span>Scheduled total</span><strong>{money(summary.total) || '$0.00'}</strong><small>Scheduled in next {filters.rangeDays} days</small><p>{summary.count} {summary.count === 1 ? 'payment' : 'payments'} · {money(summary.average) || '$0.00'} avg</p></div><div className="recurring-v18-next"><span>Next payment</span>{summary.next ? <><strong>{relativeDue(summary.next).label}</strong><small>{summary.next.name}</small><b>{money(summary.next.expected_amount)}</b></> : <small>No unresolved payment</small>}</div></div><button className="recurring-v18-summary-disclosure" type="button" aria-expanded={expanded} onClick={() => setExpanded((v) => !v)}>{expanded ? 'Hide summary' : 'View summary'} <span aria-hidden="true">{expanded ? '⌃' : '⌄'}</span></button><div className="recurring-v18-summary-details"><div className="recurring-v18-breakdown"><h3>Breakdown by period</h3>{summary.breakdown.map((bucket) => <div key={bucket.label}><span>{bucket.label}<small>{bucket.count} payments</small></span><strong>{money(bucket.total)}</strong></div>)}</div><div className="recurring-v18-largest"><h3>Largest upcoming expense</h3>{summary.largest ? <><strong>{summary.largest.name}</strong><span>{money(summary.largest.expected_amount)}</span><small>{dateLabel(summary.largest.expected_date)}</small></> : <p>No payment in this period.</p>}</div><div className="recurring-v18-status-summary"><h3>Payment status (next {filters.rangeDays} days)</h3><div><span>Expected automatically<small>{summary.status.automatic.count} payments</small></span><strong>{money(summary.status.automatic.total)}</strong></div><div><span>Requires payment<small>{summary.status.manual.count} payments</small></span><strong>{money(summary.status.manual.total)}</strong></div><div><span>Paid<small>{summary.status.paid.count} payments</small></span><strong>{money(summary.status.paid.total)}</strong></div><div className="attention"><span>Overdue / Needs attention<small>{summary.status.attention.count} payments</small></span><strong>{money(summary.status.attention.total)}</strong></div><p className="recurring-v18-reconcile-note">Status categories above are mutually exclusive, so they reconcile to Scheduled Total.</p></div><div className="recurring-v18-quick-actions"><h3>Quick actions</h3><button type="button" onClick={() => navigateReload('CSV Import')}><strong>Import bank CSV</strong><small>Match payments</small></button><button type="button" onClick={() => navigateReload('Overview')}><strong>Payments requiring attention</strong><small>{attentionCount} payments</small></button></div></div></section>;
}

function Segmented({ view, setView }) { return <div className="recurring-v18-segmented" role="group" aria-label="Recurring expenses view"><button type="button" className={view === 'list' ? 'active' : ''} aria-pressed={view === 'list'} onClick={() => setView('list')}>List</button><button type="button" className={view === 'calendar' ? 'active' : ''} aria-pressed={view === 'calendar'} onClick={() => setView('calendar')}>Calendar</button></div>; }

function ListView({ rows, sort, setSort, money, dateLabel, onEdit, normaliseRecord, onRefresh }) {
  const grouped = useMemo(() => { const groups = new Map(); rows.forEach((row) => { const key = relativeDue(row).group; if (!groups.has(key)) groups.set(key, []); groups.get(key).push(row); }); return groups; }, [rows]);
  const sortField = (key) => setSort((current) => current.key === key ? { key, direction: current.direction === 'asc' ? 'desc' : 'asc' } : { key, direction: 'asc' });
  const headers = [['next_due_date','Next due'],['name','Name'],[null,'Category'],['amount','Amount'],['frequency','Frequency'],['status','Payment']];
  return <><div className="recurring-v18-mobile-sort"><span>Sorted by {sort.key === 'next_due_date' ? 'next due' : sort.key}</span><select aria-label="Sort recurring expenses" value={sort.key} onChange={(e) => setSort({ key: e.target.value, direction: 'asc' })}><option value="next_due_date">Next due</option><option value="name">Name</option><option value="amount">Amount</option><option value="frequency">Frequency</option><option value="status">Payment status</option></select></div><div className="recurring-v18-table" role="table" aria-label="Scheduled recurring payments"><div className="recurring-v18-table-head" role="row">{headers.map(([key,label]) => <span role="columnheader" key={label}>{key ? <button type="button" onClick={() => sortField(key)}>{label}{sort.key === key ? sort.direction === 'asc' ? ' ↑' : ' ↓' : ''}</button> : label}</span>)}<span role="columnheader" className="sr-only">Actions</span></div>{[...grouped.entries()].map(([group, items]) => <div className="recurring-v18-group" key={group}><div className="recurring-v18-group-label">{group}</div>{items.map((payment) => <div className="recurring-v18-table-row" role="row" key={payment.id}><span role="cell"><Due payment={payment} dateLabel={dateLabel}/></span><span role="cell"><strong>{payment.name}</strong>{payment.merchant && <small>{payment.merchant}</small>}</span><span role="cell">{payment.category}</span><span role="cell" className="amount">{money(payment.expected_amount)}</span><span role="cell">{frequencyLabel(payment.frequency)}</span><span role="cell"><PaymentSource payment={payment}/></span><span role="cell"><PaymentActions payment={payment} onEdit={onEdit} normaliseRecord={normaliseRecord} onRefresh={onRefresh} money={money} dateLabel={dateLabel}/></span></div>)}</div>)}</div><div className="recurring-v18-mobile-list">{[...grouped.entries()].map(([group, items]) => <section key={group}><h3>{group}</h3>{items.map((payment) => <article className="recurring-v18-mobile-row" key={payment.id}><div className="recurring-v18-mobile-row-top"><strong>{payment.name}</strong><b>{money(payment.expected_amount)}</b></div><p>{payment.category} · {frequencyLabel(payment.frequency)}</p><p>{dateLabel(payment.expected_date)} · {relativeDue(payment).label}</p><PaymentSource payment={payment}/><PaymentActions payment={payment} onEdit={onEdit} normaliseRecord={normaliseRecord} onRefresh={onRefresh} money={money} dateLabel={dateLabel}/></article>)}</section>)}</div></>;
}

function CalendarView({ allRows, filters, search, month, setMonth, money, dateLabel, onEdit, normaliseRecord, onRefresh }) {
  const monthRows = useMemo(() => filterScheduledPayments(allRows, filters, search, new Date(), 'month', month), [allRows, filters, search, month]);
  const [selected, setSelected] = useState(null);
  useEffect(() => setSelected(null), [month]);
  const first = new Date(month.getFullYear(), month.getMonth(), 1); const startOffset = (first.getDay() + 6) % 7; const gridStart = new Date(first); gridStart.setDate(first.getDate() - startOffset);
  const days = Array.from({ length: 42 }, (_, i) => { const d = new Date(gridStart); d.setDate(gridStart.getDate() + i); return d; });
  const byDate = new Map(); monthRows.forEach((row) => { const key = iso(row.expected_date); if (!byDate.has(key)) byDate.set(key, []); byDate.get(key).push(row); });
  for (const items of byDate.values()) items.sort((a,b) => paymentPriority(a) - paymentPriority(b) || Number(b.expected_amount || 0) - Number(a.expected_amount || 0));
  const selectedRows = selected ? byDate.get(selected) || [] : [];
  const upcoming = [...monthRows].sort((a,b) => paymentPriority(a) - paymentPriority(b) || compareText(iso(a.expected_date), iso(b.expected_date))).slice(0, 8);
  const shift = (delta) => setMonth(new Date(month.getFullYear(), month.getMonth() + delta, 1));
  return <section className="recurring-v18-calendar"><div className="recurring-v18-calendar-nav"><button type="button" aria-label="Previous month" onClick={() => shift(-1)}>‹</button><strong>{monthTitle(month)}</strong><button type="button" aria-label="Next month" onClick={() => shift(1)}>›</button></div><div className="recurring-v18-weekdays" aria-hidden="true">{['MON','TUE','WED','THU','FRI','SAT','SUN'].map((d) => <span key={d}>{d}</span>)}</div><div className="recurring-v18-calendar-grid">{days.map((day) => { const key = iso(day.toISOString()); const items = byDate.get(key) || []; const inMonth = day.getMonth() === month.getMonth(); return <button type="button" key={key} className={`${inMonth ? '' : 'adjacent'} ${selected === key ? 'selected' : ''}`} aria-label={`${dateLabel(key)}, ${items.length} scheduled payment${items.length === 1 ? '' : 's'}`} onClick={() => setSelected(key)}><time>{day.getDate()}</time><div>{items.slice(0, 2).map((row) => <span key={row.id} className={`calendar-status-${row.status}`}><i aria-hidden="true">•</i><em>{row.name}</em><b>{money(row.expected_amount)}</b></span>)}{items.length > 2 && <strong className="more">+{items.length - 2} more</strong>}</div></button>; })}</div><div className="recurring-v18-calendar-legend" aria-label="Payment status legend"><span className="due">Requires payment</span><span className="expected">Expected automatically</span><span className="paid">Paid</span><span className="attention">Needs attention</span><span className="overdue">Overdue</span></div><section className="recurring-v18-selected-date"><h3>{selected ? dateLabel(selected) : 'Upcoming'}</h3>{(selected ? selectedRows : upcoming).length ? (selected ? selectedRows : upcoming).map((payment) => <article key={payment.id}><div><strong>{payment.name}</strong><small>{dateLabel(payment.expected_date)}</small><PaymentSource payment={payment}/></div><b>{money(payment.expected_amount)}</b><PaymentActions payment={payment} onEdit={onEdit} normaliseRecord={normaliseRecord} onRefresh={onRefresh} money={money} dateLabel={dateLabel}/></article>) : <div className="recurring-v18-empty"><strong>{selected ? 'No scheduled payments on this date' : 'No scheduled payments this month'}</strong></div>}</section></section>;
}

export default function RecurringExpensesPage({ data, onEdit, money, dateLabel, normaliseRecord, onRefresh }) {
  const [filters, setFilters] = useState({ ...DEFAULT_FILTERS }); const [search, setSearch] = useState(''); const [sort, setSort] = useState({ key: 'next_due_date', direction: 'asc' }); const [viewMode, setViewMode] = useState('list'); const [sheetOpen, setSheetOpen] = useState(false); const [month, setMonth] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const rows = useMemo(() => enrichScheduledPayments(data), [data.scheduledPayments, data.recurring, data.categories, data.cards, data.accounts]);
  const frequencies = useMemo(() => [...new Set((data.recurring || []).map((r) => r.frequency).filter(Boolean))].sort(compareText), [data.recurring]);
  const categories = useMemo(() => [...new Set(rows.map((r) => r.category).filter(Boolean))].sort(compareText), [rows]);
  const filtered = useMemo(() => filterScheduledPayments(rows, filters, search), [rows, filters, search]);
  const sorted = useMemo(() => sortScheduledPayments(filtered, sort), [filtered, sort]);
  const summary = useMemo(() => summarisePayments(filtered), [filtered]);
  const nonSearchCount = activeFilterCount(filters);
  const add = () => onEdit({ type: 'recurring', label: 'New Recurring Expense', row: { id: null }, values: normaliseRecord('recurring', {}) });
  const clear = () => { setFilters({ ...DEFAULT_FILTERS }); setSearch(''); };
  const hasRecords = (data.recurring || []).length > 0;
  return <section className="recurring-v18-page"><header className="recurring-v18-page-head"><div><h2>Recurring Expenses</h2><p>Manage recurring bills, subscriptions and household commitments.</p></div><button type="button" className="primary recurring-v18-add" onClick={add}><span className="desktop-label">+ Quick Add</span><span className="mobile-label">+</span></button></header><div className="recurring-v18-desktop-filters"><input type="search" aria-label="Search recurring expenses" placeholder="Search expenses..." value={search} onChange={(e) => setSearch(e.target.value)}/><select aria-label="Date range" value={filters.rangeDays} onChange={(e) => setFilters({ ...filters, rangeDays: Number(e.target.value) })}>{RANGE_OPTIONS.map((d) => <option key={d} value={d}>Next {d} days</option>)}</select><select aria-label="Frequency" value={filters.frequency} onChange={(e) => setFilters({ ...filters, frequency: e.target.value })}><option value="all">All frequencies</option>{frequencies.map((v) => <option key={v} value={v}>{frequencyLabel(v)}</option>)}</select><select aria-label="Category" value={filters.category} onChange={(e) => setFilters({ ...filters, category: e.target.value })}><option value="all">All categories</option>{categories.map((v) => <option key={v}>{v}</option>)}</select><select aria-label="Payment method" value={filters.paymentMethod} onChange={(e) => setFilters({ ...filters, paymentMethod: e.target.value })}><option value="all">All payment methods</option>{Object.entries(PAYMENT_METHOD_LABELS).map(([id,label]) => <option key={id} value={id}>{label}</option>)}</select><select aria-label="Payment status" value={filters.paymentStatus} onChange={(e) => setFilters({ ...filters, paymentStatus: e.target.value })}><option value="all">All statuses</option>{Object.entries(PAYMENT_STATUS_LABELS).map(([id,label]) => <option key={id} value={id}>{label}</option>)}</select><button type="button" disabled={!nonSearchCount && !search} onClick={clear}>Clear filters</button></div><div className="recurring-v18-mobile-search"><input type="search" aria-label="Search recurring expenses" placeholder="Search expenses..." value={search} onChange={(e) => setSearch(e.target.value)}/><button type="button" onClick={() => setSheetOpen(true)}>Filters{nonSearchCount ? ` ${nonSearchCount}` : ''}</button></div><FilterSheet applied={filters} onApply={setFilters} frequencies={frequencies} categories={categories} open={sheetOpen} onClose={() => setSheetOpen(false)}/>{rows.length ? <><Summary summary={summary} filters={filters} money={money} dateLabel={dateLabel} attentionCount={(data.paymentAttention || []).length}/><div className="recurring-v18-view-head"><div><strong>{viewMode === 'list' ? 'Upcoming recurring expenses' : 'Recurring expense calendar'}</strong><span>{viewMode === 'list' ? 'Scheduled payments generated from recurring-expense rules' : 'Calendar month is the temporal scope; List keeps your relative date range.'}</span></div><Segmented view={viewMode} setView={setViewMode}/></div>{viewMode === 'list' ? sorted.length ? <ListView rows={sorted} sort={sort} setSort={setSort} money={money} dateLabel={dateLabel} onEdit={onEdit} normaliseRecord={normaliseRecord} onRefresh={onRefresh}/> : <div className="recurring-v18-empty"><strong>No expenses match these filters</strong><button type="button" onClick={clear}>Clear filters</button></div> : <CalendarView allRows={rows} filters={filters} search={search} month={month} setMonth={setMonth} money={money} dateLabel={dateLabel} onEdit={onEdit} normaliseRecord={normaliseRecord} onRefresh={onRefresh}/>}</> : <div className="recurring-v18-empty"><strong>{hasRecords ? 'No scheduled payments yet' : 'No recurring expenses yet'}</strong><p>{hasRecords ? 'Scheduled payments will appear when active recurring rules have due dates.' : 'Add recurring bills, subscriptions and household commitments to start forecasting future expenses.'}</p><button type="button" className="primary" onClick={add}>+ Add recurring expense</button></div>}</section>;
}
