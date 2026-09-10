import { useEffect, useMemo, useRef, useState } from 'react';

import PaymentCentreV112 from './PaymentCentreV112.jsx';
import { apiRequest } from './apiClient.js';
import {
  PAYMENT_METHOD_LABELS,
  buildPaymentCentreQuery,
  defaultPaymentCentreFilters,
  paymentAttentionReason,
  paymentAvailableActions,
  paymentPrimaryAction,
  paymentSourceLabel,
} from './paymentCentreModel.js';

const TERMINAL = new Set(['paid', 'skipped', 'cancelled']);

const finite = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const money = (value) => {
  const number = finite(value);
  return number === null ? '—' : new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(number);
};

const dateLabel = (value) => value
  ? new Intl.DateTimeFormat('en-AU', { weekday: 'short', day: 'numeric', month: 'short' }).format(new Date(`${String(value).slice(0, 10)}T00:00:00`))
  : 'No date';

const rowAmount = (row) => Math.abs(Number(row.status === 'paid' && row.actual_amount != null ? row.actual_amount : row.expected_amount ?? row.amount ?? 0) || 0);

const missingFields = (row) => {
  const missing = [];
  if (!(row.expected_date || row.due_date)) missing.push('due date');
  if (!row.payment_method || row.payment_method === 'not_set') missing.push('payment method');
  if (!row.account_id && !row.card_id && !row.linked_account_name) missing.push('funding account');
  return missing;
};

const attentionRank = (row) => {
  const reason = String(paymentAttentionReason(row) || '').toLowerCase();
  const status = String(row?.status || '').toLowerCase();
  if (status === 'overdue') return 0;
  if (row?.match_review_available || reason.includes('reconciliation')) return 1;
  if (reason.includes('funding') || reason.includes('account')) return 2;
  if (status === 'due' || status === 'due_today') return 3;
  if (status === 'auto_payment_unconfirmed') return 4;
  if (reason.includes('payment method')) return 5;
  return 6;
};

function groupRows(rows = [], mode = 'grouped') {
  if (mode === 'chronological') {
    const groups = new Map();
    rows.forEach((row) => {
      const raw = row.expected_date || row.due_date;
      const key = TERMINAL.has(row.status) ? 'Payment history' : raw ? String(raw).slice(0, 10) : 'Date not specified';
      const list = groups.get(key) || [];
      list.push(row);
      groups.set(key, list);
    });
    return [...groups.entries()]
      .sort(([a], [b]) => {
        if (a === 'Payment history') return 1;
        if (b === 'Payment history') return -1;
        if (a === 'Date not specified') return 1;
        if (b === 'Date not specified') return -1;
        return a.localeCompare(b);
      })
      .map(([key, values]) => ({
        key,
        label: key === 'Payment history' || key === 'Date not specified' ? key : dateLabel(key),
        rows: [...values].sort((a, b) => attentionRank(a) - attentionRank(b) || rowAmount(b) - rowAmount(a)),
      }));
  }

  const today = new Date(); today.setHours(0, 0, 0, 0);
  const seven = new Date(today); seven.setDate(seven.getDate() + 7);
  const buckets = [
    { key: 'overdue', label: 'Overdue', rows: [] },
    { key: 'today', label: 'Due today', rows: [] },
    { key: 'soon', label: 'Due in next 7 days', rows: [] },
    { key: 'later', label: 'Due later', rows: [] },
    { key: 'missing', label: 'Date not specified', rows: [] },
    { key: 'history', label: 'Payment history', rows: [] },
  ];
  const byKey = new Map(buckets.map((group) => [group.key, group]));
  rows.forEach((row) => {
    if (TERMINAL.has(row.status)) return byKey.get('history').rows.push(row);
    const raw = row.expected_date || row.due_date;
    if (!raw) return byKey.get('missing').rows.push(row);
    if (row.status === 'overdue' || row.status === 'auto_payment_unconfirmed') return byKey.get('overdue').rows.push(row);
    const due = new Date(`${String(raw).slice(0, 10)}T00:00:00`);
    if (due.getTime() === today.getTime()) return byKey.get('today').rows.push(row);
    if (due > today && due <= seven) return byKey.get('soon').rows.push(row);
    return byKey.get('later').rows.push(row);
  });
  return buckets.filter((group) => group.rows.length).map((group) => ({
    ...group,
    rows: [...group.rows].sort((a, b) => attentionRank(a) - attentionRank(b) || String(a.expected_date || a.due_date || '').localeCompare(String(b.expected_date || b.due_date || '')) || rowAmount(b) - rowAmount(a)),
  }));
}

function PaymentSkeleton() {
  return <div className="payment-v1182-skeleton" role="status" aria-label="Loading payments">
    {[0, 1, 2].map((item) => <div className="payment-v1182-skeleton-row" key={item}/>)}
  </div>;
}

function PayCycleDecision({ planning, onIncome }) {
  const payCycle = planning?.pay_cycle;
  if (!payCycle) return null;
  const before = payCycle.before_next_income || {};
  const projected = finite(before.projected_cash);
  const shortfallAmount = projected !== null && projected < 0 ? Math.abs(projected) : finite(before.shortfall);
  const hasIncome = Boolean(payCycle.next_income);
  const status = !hasIncome || payCycle.status === 'unknown'
    ? 'unknown'
    : payCycle.status === 'shortfall' || projected !== null && projected < 0
      ? 'shortfall'
      : 'funded';
  const headline = status === 'shortfall'
    ? shortfallAmount === null ? 'Funding shortfall' : `${money(shortfallAmount)} shortfall`
    : status === 'unknown'
      ? 'Before-pay position unavailable'
      : 'Funded before next pay';
  const copy = status === 'shortfall'
    ? 'Available funds do not cover known commitments before the next income.'
    : status === 'unknown'
      ? !hasIncome
        ? 'Next income amount/date must be confirmed before the before-pay position can be calculated.'
        : 'Funding account assignments or balances are incomplete, so the before-pay position cannot be confirmed.'
      : 'Known commitments are covered before the next income.';
  return <section className={`payment-v1182-decision ${status}`} aria-label="Before next pay">
    <div className="payment-v1182-decision-head"><div><small>BEFORE NEXT PAY</small><h2>{hasIncome ? `${payCycle.next_income.name || 'Income'} · ${dateLabel(payCycle.next_income.date)}` : 'Next income not confirmed'}</h2></div><strong className="payment-v1182-decision-value">{headline}</strong></div>
    <p className="payment-v1182-decision-copy">{copy}</p>
    {status === 'unknown' && !hasIncome && <button type="button" className="primary ghost" onClick={onIncome}>Review Income</button>}
    <div className="payment-v1182-decision-grid">
      <div><span>Available now</span><strong>{money(before.current_available_cash)}</strong></div>
      <div><span>Required before pay</span><strong>{money(before.commitments_total)}</strong></div>
      <div><span>Next income</span><strong>{hasIncome ? money(payCycle.next_income.amount) : 'Not known'}</strong></div>
    </div>
    <details className="payment-v1182-calculation"><summary>View calculation</summary><div className="payment-v1182-calculation-grid">
      <div><span>Payments due</span><strong>{before.commitment_count ?? '—'}</strong></div>
      <div><span>Overdue included</span><strong>{money(before.overdue_total)}</strong></div>
      <div><span>Automatic payments</span><strong>{money(before.automatic_payment_total)}</strong></div>
      <div><span>Projected before pay</span><strong>{money(before.projected_cash)}</strong></div>
      <div><span>Projected after pay</span><strong>{money(payCycle.after_next_income?.projected_cash)}</strong></div>
    </div></details>
  </section>;
}

function FilterSheet({ open, draft, setDraft, data, onApply, onClear, onClose }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const prior = document.activeElement;
    const frame = requestAnimationFrame(() => ref.current?.querySelector('input,select,button')?.focus());
    const onKey = (event) => { if (event.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => { cancelAnimationFrame(frame); document.removeEventListener('keydown', onKey); prior?.focus?.(); };
  }, [open, onClose]);
  if (!open) return null;
  const set = (key, value) => setDraft((current) => ({ ...current, [key]: value }));
  return <div className="payment-v1180-filter-sheet-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section ref={ref} className="payment-v1180-filter-sheet" role="dialog" aria-modal="true" aria-label="Payment filters"><header><strong>Filters</strong><button type="button" onClick={onClose} aria-label="Close filters">×</button></header><div className="payment-v1180-filter-grid">
    <label><span>Search</span><input value={draft.search} onChange={(event) => set('search', event.target.value)} placeholder="Name, merchant, category, account or card"/></label>
    <label><span>Date range</span><select value={draft.dateRange} onChange={(event) => set('dateRange', event.target.value)}><option value="overdue">Overdue</option><option value="today">Today</option><option value="next_7_days">Next 7 days</option><option value="next_14_days">Next 14 days</option><option value="next_30_days">Next 30 days</option><option value="next_90_days">Next 90 days</option><option value="this_month">This month</option><option value="next_month">Next month</option><option value="history">Payment history</option></select></label>
    <label><span>Status</span><select value={draft.status} onChange={(event) => set('status', event.target.value)}><option value="">All statuses</option><option value="overdue">Overdue</option><option value="due">Due today</option><option value="auto_payment_unconfirmed">Confirmation needed</option><option value="paid">Paid</option><option value="skipped">Skipped</option></select></label>
    <label><span>Category</span><select value={draft.categoryId} onChange={(event) => set('categoryId', event.target.value)}><option value="">All categories</option>{(data.categories || []).filter((row) => row.is_active !== false).map((row) => <option value={row.id} key={row.id}>{row.path || row.name}</option>)}</select></label>
    <label><span>Account</span><select value={draft.accountId} onChange={(event) => set('accountId', event.target.value)}><option value="">All Accounts</option>{(data.accounts || []).filter((row) => row.is_active !== false && !row.archived_at).map((row) => <option value={row.id} key={row.id}>{row.name}</option>)}</select></label>
    <label><span>Payment method</span><select value={draft.paymentMethod} onChange={(event) => set('paymentMethod', event.target.value)}><option value="">All methods</option>{Object.entries(PAYMENT_METHOD_LABELS).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
    <label className="payment-centre-check"><input type="checkbox" checked={draft.requiresAction} onChange={(event) => set('requiresAction', event.target.checked)}/><span>Requires action only</span></label>
  </div><div className="payment-v1180-filter-actions"><button type="button" onClick={() => { onClear(); onClose(); }}>Clear</button><button type="button" className="primary" onClick={() => { onApply(); onClose(); }}>Apply</button></div></section></div>;
}

function QuickMarkPaid({ row, onClose, onSaved }) {
  const [form, setForm] = useState({ paid_date: new Date().toISOString().slice(0, 10), paid_amount: row?.expected_amount || row?.amount || '', note: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  if (!row) return null;
  const submit = async (event) => {
    event.preventDefault(); setSaving(true); setError('');
    try {
      const isBill = row.source_type === 'bill';
      await apiRequest(isBill ? `/bills/${row.id}/mark-paid` : `/scheduled-payments/${row.id}/mark-paid`, {
        method: 'POST',
        body: JSON.stringify(isBill
          ? { paid_date: form.paid_date, paid_amount: form.paid_amount, note: form.note, version: row.version }
          : { actual_date: form.paid_date, actual_amount: form.paid_amount, note: form.note }),
      });
      await onSaved();
    } catch (requestError) { setError(requestError?.message || 'Could not mark this payment paid.'); }
    finally { setSaving(false); }
  };
  return <div className="payment-centre-modal-backdrop"><form className="payment-centre-mark-paid" onSubmit={submit}><header><div><h2>Mark as paid</h2><p>{row.name} · expected {money(row.expected_amount ?? row.amount)}</p></div><button type="button" onClick={onClose} aria-label="Close mark paid">×</button></header><div className="payment-centre-form"><label><span>Actual date</span><input required type="date" value={form.paid_date} onChange={(event) => setForm({ ...form, paid_date: event.target.value })}/></label><label><span>Actual amount</span><input required inputMode="decimal" value={form.paid_amount} onChange={(event) => setForm({ ...form, paid_amount: event.target.value })}/></label><label><span>Note (optional)</span><textarea rows="3" value={form.note} onChange={(event) => setForm({ ...form, note: event.target.value })}/></label>{error && <p className="error">{error}</p>}</div><footer><button type="button" onClick={onClose}>Cancel</button><button className="primary" disabled={saving}>{saving ? 'Saving…' : 'Mark as paid'}</button></footer></form></div>;
}

function PaymentCard({ row, onMarkPaid, onOpenDetailed, onEditBill, onOpenRecurring, onNavigate }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const primary = paymentPrimaryAction(row);
  const actions = paymentAvailableActions(row).filter((action) => action !== 'view' && action !== 'mark_paid');
  const missing = missingFields(row);
  const reason = paymentAttentionReason(row);
  const due = row.expected_date || row.due_date;
  const overdue = Number(row.days_overdue || 0);
  const handling = row.payment_handling === 'automatic' ? 'Automatic' : 'Manual';
  const funding = row.card_name || row.account_name || row.linked_account_name || null;
  const method = row.payment_method_label || PAYMENT_METHOD_LABELS[row.payment_method];
  const meta = [
    overdue > 0 ? `Due ${dateLabel(due)} · ${overdue} day${overdue === 1 ? '' : 's'} overdue` : due ? `Due ${dateLabel(due)}` : 'Due date missing',
    handling,
    method && row.payment_method !== 'not_set' ? method : null,
    funding,
  ].filter(Boolean);
  const doAction = (action) => {
    setMenuOpen(false);
    if (action === 'edit') return onEditBill?.(row) || onNavigate('Bills');
    if (action === 'open_recurring') return onOpenRecurring?.(row) || onNavigate('Recurring Expenses');
    if (action === 'review') return onNavigate(row.source_type === 'scheduled_payment' ? 'Review Queue' : 'Transactions');
    return onOpenDetailed();
  };
  return <article className={`payment-v1182-card ${row.status === 'overdue' ? 'overdue' : reason || missing.length ? 'attention' : ''}`}>
    <button type="button" className="payment-v1182-card-main" onClick={onOpenDetailed}>
      <span className="payment-v1182-card-name"><strong>{row.name}</strong><small>{row.category || 'Uncategorised'} · {paymentSourceLabel(row)}</small></span>
      <strong className="payment-v1182-card-amount">{money(rowAmount(row))}</strong>
      <span className="payment-v1182-card-meta"><span className={overdue > 0 ? 'danger' : ''}>{meta[0]}</span>{meta.slice(1).map((item) => <span key={item}>· {item}</span>)}{reason && overdue === 0 && <span className="warning">· {reason}</span>}</span>
      {missing.length > 0 && <span className="payment-v1182-missing">⚠ {missing.length} detail{missing.length === 1 ? '' : 's'} missing</span>}
    </button>
    <div className={`payment-v1182-card-actions ${primary !== 'mark_paid' ? 'single' : ''}`}>
      {primary === 'mark_paid' && <button type="button" className="mark-paid" onClick={() => onMarkPaid(row)}>Mark paid</button>}
      <button type="button" className="overflow" aria-expanded={menuOpen} aria-label={`More actions for ${row.name}`} onClick={() => setMenuOpen((open) => !open)}>⋯</button>
    </div>
    {menuOpen && <div className="payment-v1182-overflow"><button type="button" onClick={onOpenDetailed}>View payment details</button>{missing.length > 0 && <button type="button" onClick={onOpenDetailed}>Review {missing.length} missing detail{missing.length === 1 ? '' : 's'}</button>}{actions.map((action) => <button type="button" key={action} onClick={() => doAction(action)}>{({ review: 'Review', edit: 'Edit Bill', cancel: 'Cancel Bill', change_date: 'Change payment date', skip: 'Skip payment', restore: 'Restore payment', open_recurring: 'Open Recurring Expense' })[action] || action.replaceAll('_', ' ')}</button>)}</div>}
  </article>;
}

export default function PaymentCentreMobileV1182(props) {
  const { data, onNavigate, onQuickAdd, onAddBill, onRefreshSupporting, onEditBill, onOpenRecurring } = props;
  const initial = useMemo(() => { const next = defaultPaymentCentreFilters(); if (localStorage.getItem('fynvo.paymentCentreRequiresAction') === 'true') { next.requiresAction = true; localStorage.removeItem('fynvo.paymentCentreRequiresAction'); } return next; }, []);
  const [draft, setDraft] = useState(initial);
  const [filters, setFilters] = useState(initial);
  const [result, setResult] = useState(null);
  const [planning, setPlanning] = useState(null);
  const [loadingPayments, setLoadingPayments] = useState(true);
  const [loadingPlanning, setLoadingPlanning] = useState(true);
  const [paymentError, setPaymentError] = useState('');
  const [planningError, setPlanningError] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [markingPaid, setMarkingPaid] = useState(null);
  const [fullWorkspace, setFullWorkspace] = useState(false);
  const [mode, setMode] = useState(() => localStorage.getItem('fynvo.paymentCentre.timelineMode.v1182') || 'grouped');
  const query = useMemo(() => buildPaymentCentreQuery(filters), [filters]);
  const groups = useMemo(() => groupRows(result?.rows || [], mode), [result?.rows, mode]);

  const loadPayments = async () => {
    setLoadingPayments(true); setPaymentError('');
    try { setResult(await apiRequest(query)); }
    catch (error) { setPaymentError(error?.message || 'Payment list could not load.'); }
    finally { setLoadingPayments(false); }
  };
  const loadPlanning = async () => {
    setLoadingPlanning(true); setPlanningError('');
    try { setPlanning(await apiRequest('/payment-planning')); }
    catch (error) { setPlanningError(error?.message || 'Before-pay funding could not load.'); }
    finally { setLoadingPlanning(false); }
  };

  useEffect(() => { loadPayments(); }, [query]);
  useEffect(() => { loadPlanning(); }, []);
  useEffect(() => { localStorage.setItem('fynvo.paymentCentre.timelineMode.v1182', mode); }, [mode]);

  const activeCount = [filters.search, filters.status, filters.categoryId, filters.source, filters.paymentMethod, filters.paymentHandling, filters.accountId, filters.cardId, filters.requiresAction].filter(Boolean).length;
  const quick = (next) => { setDraft((current) => ({ ...current, ...next })); setFilters((current) => ({ ...current, ...next })); };
  const clear = () => { const next = defaultPaymentCentreFilters(); setDraft(next); setFilters(next); };
  const refreshed = async () => { setMarkingPaid(null); await Promise.allSettled([loadPayments(), loadPlanning(), onRefreshSupporting?.()]); };

  if (fullWorkspace) return <section className="payment-v1182-shell payment-v1182-full-workspace"><div className="payment-v1182-toolbar"><button type="button" className="payment-v1182-back" onClick={() => setFullWorkspace(false)}>‹ Back to compact queue</button></div><PaymentCentreV112 {...props}/></section>;

  return <section className="payment-v1182-shell" aria-label="Payment Centre mobile workspace">
    <div className="payment-v1182-toolbar">
      <div className="payment-v1182-create-row"><button type="button" className="primary ghost" onClick={onQuickAdd}>+ Quick Add</button><button type="button" className="primary" onClick={onAddBill}>+ Add Bill</button></div>
      <div className="payment-v1182-mode" role="group" aria-label="Payment timeline view"><button type="button" className={mode === 'grouped' ? 'active' : ''} aria-pressed={mode === 'grouped'} onClick={() => setMode('grouped')}>Grouped</button><button type="button" className={mode === 'chronological' ? 'active' : ''} aria-pressed={mode === 'chronological'} onClick={() => setMode('chronological')}>Chronological</button></div>
      <div className="payment-v1182-filter-row" aria-label="Quick payment filters"><button type="button" className={filters.dateRange === 'next_30_days' ? 'active' : ''} onClick={() => quick({ dateRange: 'next_30_days' })}>Next 30 days</button><button type="button" className={filters.dateRange === 'overdue' ? 'active' : ''} onClick={() => quick({ dateRange: 'overdue' })}>Overdue</button><button type="button" className={filters.requiresAction ? 'active' : ''} onClick={() => quick({ requiresAction: !filters.requiresAction })}>Needs attention</button><button type="button" onClick={() => setFiltersOpen(true)}>Filters{activeCount ? ` (${activeCount})` : ''}</button></div>
    </div>

    {loadingPlanning && !planning ? <div className="payment-v1182-skeleton" role="status" aria-label="Loading before-pay funding"><div className="payment-v1182-skeleton-row"/></div> : planningError ? <div className="payment-v1182-error"><strong>Before-pay funding unavailable</strong><p>{planningError}</p><button type="button" onClick={loadPlanning}>Retry funding</button></div> : <PayCycleDecision planning={planning} onIncome={() => onNavigate('Income')}/>} 

    {loadingPayments && !result ? <PaymentSkeleton/> : paymentError ? <div className="payment-v1182-error"><strong>Payment list could not load</strong><p>{paymentError}</p><button type="button" onClick={loadPayments}>Retry payments</button></div> : result?.rows?.length ? <section className={`payment-v1182-timeline ${loadingPayments ? 'refreshing' : ''}`}>
      {groups.map((group) => <section className="payment-v1182-group" key={group.key}><div className="payment-v1182-group-head"><h3>{group.label}</h3><span>{group.rows.length} payment{group.rows.length === 1 ? '' : 's'}</span></div>{group.rows.map((row) => <PaymentCard key={`${row.source_type}-${row.id}`} row={row} onMarkPaid={setMarkingPaid} onOpenDetailed={() => setFullWorkspace(true)} onEditBill={onEditBill} onOpenRecurring={onOpenRecurring} onNavigate={onNavigate}/>)}</section>)}
    </section> : <div className="payment-v1182-empty"><strong>{activeCount || filters.dateRange !== 'next_30_days' ? 'No payments match these filters' : 'No payments in this period'}</strong><p>{activeCount || filters.dateRange !== 'next_30_days' ? 'Try clearing filters or selecting a broader date range.' : 'There are no payment obligations in the selected period.'}</p>{(activeCount || filters.dateRange !== 'next_30_days') && <button type="button" onClick={clear}>Clear filters</button>}</div>}

    <QuickMarkPaid row={markingPaid} onClose={() => setMarkingPaid(null)} onSaved={refreshed}/>
    <FilterSheet open={filtersOpen} draft={draft} setDraft={setDraft} data={data} onApply={() => setFilters({ ...draft })} onClear={clear} onClose={() => setFiltersOpen(false)}/>
  </section>;
}
