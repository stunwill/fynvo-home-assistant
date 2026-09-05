import { useEffect, useMemo, useState } from 'react';

import PaymentCentreV112 from './PaymentCentreV112.jsx';
import { apiRequest } from './apiClient.js';
import {
  PAYMENT_DATE_RANGES,
  PAYMENT_METHOD_LABELS,
  PAYMENT_STATUS_LABELS,
  buildPaymentCentreQuery,
  defaultPaymentCentreFilters,
  paymentAttentionReason,
  paymentPrimaryAction,
  paymentSourceLabel,
  paymentStatusLabel,
} from './paymentCentreModel.js';
import './payment-centre-v112.css';

const TERMINAL = new Set(['paid', 'skipped', 'cancelled']);
const GROUP_PREVIEW_COUNT = 3;

const finiteNumber = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const money = (value) => {
  const number = finiteNumber(value);
  return number === null ? 'Not known' : new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(number);
};

const dateLabel = (value) => value
  ? new Intl.DateTimeFormat('en-AU', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(`${String(value).slice(0, 10)}T00:00:00`))
  : 'No date';

const localDateKey = (date = new Date()) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
const rowAmount = (row) => Math.abs(Number(row.status === 'paid' && row.actual_amount != null ? row.actual_amount : row.expected_amount ?? row.amount ?? 0) || 0);

function StatusBadge({ status }) {
  return <span className={`payment-centre-status status-${status}`}>{paymentStatusLabel(status)}</span>;
}

function PayCycleStatus({ status }) {
  const label = { funded: 'Funded', shortfall: 'Shortfall', low_buffer: 'Low buffer', unknown: 'Unknown' }[status] || 'Unknown';
  return <span className={`pay-cycle-status pay-cycle-${status || 'unknown'}`}>{label}</span>;
}

function DecisionSummary({ planning, onIncome }) {
  const payCycle = planning?.pay_cycle;
  if (!payCycle) return null;
  if (!payCycle.next_income) {
    return <section className="payment-v1180-decision unknown" aria-label="Funding decision"><small>FUNDING INCOMPLETE</small><strong>Not known</strong><p>Add or correct the next Income schedule before Fynvo can confirm whether commitments are covered.</p><button type="button" className="primary ghost" onClick={onIncome}>Review Income</button></section>;
  }
  const before = payCycle.before_next_income || {};
  const projected = finiteNumber(before.projected_cash);
  const status = payCycle.status === 'shortfall' || projected !== null && projected < 0 ? 'shortfall' : payCycle.status === 'unknown' ? 'unknown' : 'funded';
  const value = status === 'shortfall' && projected !== null ? Math.abs(projected) : projected;
  const message = status === 'shortfall'
    ? 'Current available funds do not cover known commitments before the next Income.'
    : status === 'unknown'
      ? 'Funding cannot be confirmed because one or more account assignments or balances are incomplete.'
      : 'Known commitments are covered before the next Income.';
  return <section className={`payment-v1180-decision ${status}`} aria-label="Funding decision"><small>{status === 'shortfall' ? 'FUNDING SHORTFALL' : status === 'unknown' ? 'FUNDING INCOMPLETE' : 'FUNDED BEFORE NEXT PAY'}</small><strong>{value === null ? 'Not known' : money(value)}</strong><p>{message}</p></section>;
}

function PayCycleSummary({ planning, onIncome }) {
  const payCycle = planning?.pay_cycle;
  if (!payCycle) return null;
  if (!payCycle.next_income) {
    return <section className="pay-cycle-panel pay-cycle-unknown" aria-label="Before next pay"><div className="pay-cycle-head"><div><span>Before next pay</span><h2>Next income not known</h2></div><PayCycleStatus status="unknown"/></div><p>Fynvo can still show upcoming commitments, but a complete before-next-pay plan needs an active Income schedule.</p><div className="pay-cycle-fallback"><span>Upcoming commitments, next 30 days</span><strong>{money(payCycle.fallback_upcoming_commitments?.next_30_days)}</strong></div><button type="button" className="primary ghost" onClick={onIncome}>Review Income</button></section>;
  }
  const before = payCycle.before_next_income || {};
  const after = payCycle.after_next_income || {};
  const attention = (payCycle.accounts || []).filter((row) => row.status !== 'funded');
  return <section className="pay-cycle-panel" aria-label="Before next pay">
    <div className="pay-cycle-head"><div><span>Before next pay</span><h2>{dateLabel(payCycle.next_income.date)}</h2><small>{payCycle.next_income.name} · {payCycle.next_income.days_until === 0 ? 'today' : `${payCycle.next_income.days_until} day${payCycle.next_income.days_until === 1 ? '' : 's'} away`}</small></div><PayCycleStatus status={payCycle.status}/></div>
    <div className="pay-cycle-metrics"><article><span>Payments due</span><strong>{before.commitment_count ?? 0}</strong></article><article><span>Required</span><strong>{money(before.commitments_total)}</strong></article><article><span>Available</span><strong>{money(before.current_available_cash)}</strong></article><article><span>Projected before pay</span><strong>{money(before.projected_cash)}</strong></article><article><span>Next income</span><strong>+{money(payCycle.next_income.amount)}</strong></article><article><span>Projected after pay</span><strong>{money(after.projected_cash)}</strong></article></div>
    <div className="pay-cycle-detail-row"><span>Includes {money(before.overdue_total)} overdue, {money(before.automatic_payment_total)} automatic and {money(before.planned_spending_total)} forecast-included Planned Spending.</span><small>Income is applied before commitments on the same date.</small></div>
    <section className="pay-cycle-accounts"><h3>Accounts needing attention</h3>{attention.length ? attention.map((row) => <article className={`pay-cycle-account pay-cycle-account-${row.status}`} key={row.account_id ?? 'unknown'}><div><strong>{row.account_name}</strong><small>{row.commitment_count} commitment{row.commitment_count === 1 ? '' : 's'}</small></div><div><span>Balance {money(row.current_balance)}</span><span>Required {money(row.required_before_pay)}</span>{row.status === 'shortfall' ? <strong>Shortfall {money(row.funding_shortfall)}</strong> : <strong>Funding unknown</strong>}</div></article>) : <p className="muted">All assigned Accounts are funded for commitments before the next pay.</p>}</section>
    {payCycle.completeness?.message && <p className="pay-cycle-note">{payCycle.completeness.message}</p>}
  </section>;
}

function groupForSimplifiedTimeline(rows = [], reference = new Date()) {
  const today = new Date(reference.getFullYear(), reference.getMonth(), reference.getDate());
  const inSeven = new Date(today); inSeven.setDate(inSeven.getDate() + 7);
  const groups = [{ key: 'overdue', label: 'Overdue', rows: [] }, { key: 'due-soon', label: 'Due in next 7 days', rows: [] }, { key: 'later', label: 'Due later', rows: [] }, { key: 'no-date', label: 'No date set', rows: [] }, { key: 'history', label: 'Payment history', rows: [] }];
  const byKey = new Map(groups.map((group) => [group.key, group]));
  rows.forEach((row) => {
    const raw = row.expected_date || row.due_date;
    if (TERMINAL.has(row.status)) return byKey.get('history').rows.push(row);
    if (!raw) return byKey.get('no-date').rows.push(row);
    if (row.status === 'overdue' || row.status === 'auto_payment_unconfirmed') return byKey.get('overdue').rows.push(row);
    const due = new Date(`${String(raw).slice(0, 10)}T00:00:00`);
    if (due <= inSeven) byKey.get('due-soon').rows.push(row); else byKey.get('later').rows.push(row);
  });
  return groups.filter((group) => group.rows.length).map((group) => ({ ...group, total: group.rows.reduce((sum, row) => sum + rowAmount(row), 0) }));
}

function PlanningOverview({ planning, onAttention }) {
  if (!planning) return null;
  const soon = planning.money_needed_soon || {};
  const next7 = planning.periods?.next_7_days || {};
  return <section className="payment-v1161-overview" aria-label="Upcoming payment planning"><article className="payment-v1161-hero"><span>Money required for upcoming commitments</span><strong>{money(soon.next_7_days)}</strong><small>Next 7 days</small><div className="payment-v1161-breakdown"><span>Manual<strong>{money(next7.manual_amount)}</strong></span><span>Automatic<strong>{money(next7.automatic_amount)}</strong></span><span className="danger">Overdue<strong>{money(next7.overdue_amount)}</strong></span><span>Already paid<strong>{money(next7.paid_amount)}</strong></span></div></article><article className="payment-v1161-glance"><h2>Upcoming at a glance</h2><div className="payment-v1161-glance-grid"><div><span>Next 7 days</span><strong>{money(soon.next_7_days)}</strong><small>{planning.periods?.next_7_days?.remaining_count ?? 0} payments</small></div><div><span>Next 14 days</span><strong>{money(soon.next_14_days)}</strong><small>{planning.periods?.next_14_days?.remaining_count ?? 0} payments</small></div><div><span>Next 30 days</span><strong>{money(soon.next_30_days)}</strong><small>{planning.periods?.next_30_days?.remaining_count ?? 0} payments</small></div></div><button type="button" className="payment-v1161-attention" onClick={onAttention}><span>Payments requiring attention<strong>{planning.attention_count ?? 0}</strong></span><b>View all</b></button></article></section>;
}

function SummaryStrip({ summary }) {
  const items = [['total_scheduled', 'Total scheduled'], ['overdue', 'Overdue'], ['requires_payment', 'Due soon'], ['upcoming', 'Upcoming'], ['paid', 'Paid']];
  return <section className="payment-v1161-summary" aria-label="Payment summary">{items.map(([key, label]) => <article key={key} className={key === 'overdue' ? 'danger' : ''}><span>{label}</span><strong>{money(summary?.[key]?.amount)}</strong><small>{summary?.[key]?.count || 0} item{summary?.[key]?.count === 1 ? '' : 's'}</small></article>)}</section>;
}

function FundingDetails({ planning }) {
  if (!planning) return null;
  const household = planning.household_funding || {};
  return <details className="payment-v1161-funding"><summary>7-day funding details <span>Account requirements and available funds</span></summary><div className="payment-funding-grid payment-v1161-funding-grid"><article className="payment-funding-panel"><h2>Money needed by account</h2>{(planning.funding_requirements || []).length ? planning.funding_requirements.map((row) => <div className={`payment-funding-row ${row.has_shortfall ? 'has-shortfall' : ''}`} key={row.account_id ?? 'unknown'}><span><strong>{row.account_name}</strong><small>{row.payment_count} payment{row.payment_count === 1 ? '' : 's'}</small></span><span className="payment-funding-values"><strong>{money(row.required)} required</strong>{row.balance_known ? <small>{money(row.available)} available</small> : <small>Available funds unknown</small>}{row.has_shortfall && <em>Likely shortfall {money(row.shortfall)}</em>}</span></div>) : <p className="muted">No unresolved commitments require funding in the next 7 days.</p>}</article><article className="payment-funding-panel"><h2>Available funds vs commitments</h2>{household.balance_known ? <><div className="payment-funding-row"><span>Available funds</span><strong>{money(household.available)}</strong></div><div className="payment-funding-row"><span>Upcoming commitments</span><strong>{money(household.upcoming_commitments)}</strong></div><div className="payment-funding-row"><span>Remaining after commitments</span><strong>{money(household.remaining_after_commitments)}</strong></div>{finiteNumber(household.shortfall) > 0 && <p className="payment-shortfall">Upcoming commitments exceed available funds by <strong>{money(household.shortfall)}</strong>.</p>}</> : <p className="muted">A reliable household comparison is not available because one or more funding accounts or balances are unknown. Unknown balances are not treated as $0.</p>}</article></div></details>;
}

function FilterPanel({ draft, setDraft, data, onApply, onClear }) {
  const [advanced, setAdvanced] = useState(false);
  const set = (key, value) => setDraft((current) => ({ ...current, [key]: value }));
  return <section className="payment-v1161-filters"><h2>Filter payments</h2><div className="payment-v1161-filter-primary"><label><span>Search</span><input aria-label="Search payments" value={draft.search} onChange={(event) => set('search', event.target.value)} placeholder="Name, merchant, category, account or card"/></label><label><span>Date range</span><select value={draft.dateRange} onChange={(event) => set('dateRange', event.target.value)}>{PAYMENT_DATE_RANGES.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label><label><span>Status</span><select value={draft.status} onChange={(event) => set('status', event.target.value)}><option value="">All statuses</option>{Object.entries(PAYMENT_STATUS_LABELS).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label><label><span>Category</span><select value={draft.categoryId} onChange={(event) => set('categoryId', event.target.value)}><option value="">All categories</option>{(data.categories || []).filter((row) => row.is_active !== false).map((row) => <option value={row.id} key={row.id}>{row.path || row.name}</option>)}</select></label></div>{draft.dateRange === 'custom' && <div className="payment-v1161-custom-range"><label><span>From</span><input type="date" value={draft.dateFrom} onChange={(event) => set('dateFrom', event.target.value)}/></label><label><span>To</span><input type="date" value={draft.dateTo} onChange={(event) => set('dateTo', event.target.value)}/></label></div>}<button type="button" className="payment-v1161-more" aria-expanded={advanced} onClick={() => setAdvanced((value) => !value)}>{advanced ? 'Hide extra filters' : 'More filters'}</button>{advanced && <div className="payment-v1161-filter-extra"><label><span>Source</span><select value={draft.source} onChange={(event) => set('source', event.target.value)}><option value="">Bills and recurring payments</option><option value="bill">Bills</option><option value="scheduled_payment">Recurring / Scheduled Payments</option></select></label><label><span>Account</span><select value={draft.accountId} onChange={(event) => set('accountId', event.target.value)}><option value="">All Accounts</option>{(data.accounts || []).filter((row) => row.is_active !== false && !row.archived_at).map((row) => <option value={row.id} key={row.id}>{row.name}</option>)}</select></label><label><span>Card</span><select value={draft.cardId} onChange={(event) => set('cardId', event.target.value)}><option value="">All Cards</option>{(data.cards || []).filter((row) => row.is_active !== false).map((row) => <option value={row.id} key={row.id}>{row.display_name}</option>)}</select></label><label><span>Payment method</span><select value={draft.paymentMethod} onChange={(event) => set('paymentMethod', event.target.value)}><option value="">All methods</option>{Object.entries(PAYMENT_METHOD_LABELS).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label><label><span>Payment handling</span><select value={draft.paymentHandling} onChange={(event) => set('paymentHandling', event.target.value)}><option value="">Automatic and manual</option><option value="automatic">Paid automatically</option><option value="manual">I pay this manually</option></select></label><label className="payment-centre-check"><input type="checkbox" checked={draft.requiresAction} onChange={(event) => set('requiresAction', event.target.checked)}/><span>Requires action only</span></label></div>}<div className="payment-v1161-filter-actions"><button type="button" onClick={onClear}>Clear filters</button><button type="button" className="primary" onClick={onApply}>Apply</button></div></section>;
}

function MobileFilterBar({ filters, setDraft, setFilters, onOpen }) {
  const quick = (next) => { setDraft((current) => ({ ...current, ...next })); setFilters((current) => ({ ...current, ...next })); };
  const activeCount = [filters.search, filters.status, filters.categoryId, filters.source, filters.paymentMethod, filters.paymentHandling, filters.accountId, filters.cardId, filters.requiresAction].filter(Boolean).length;
  return <div className="payment-v1180-filter-bar" aria-label="Payment filters"><button type="button" className={filters.dateRange === 'next_30_days' ? 'active' : ''} onClick={() => quick({ dateRange: 'next_30_days' })}>Next 30 days</button><button type="button" className={filters.dateRange === 'overdue' ? 'active' : ''} onClick={() => quick({ dateRange: 'overdue' })}>Overdue</button><button type="button" className={filters.requiresAction ? 'active' : ''} onClick={() => quick({ requiresAction: !filters.requiresAction })}>Needs attention</button><button type="button" onClick={onOpen}>+ Filters{activeCount ? ` (${activeCount})` : ''}</button></div>;
}

function MobileFilterSheet({ open, draft, setDraft, data, onApply, onClear, onClose }) {
  if (!open) return null;
  const set = (key, value) => setDraft((current) => ({ ...current, [key]: value }));
  return <div className="payment-v1180-filter-sheet-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="payment-v1180-filter-sheet" role="dialog" aria-modal="true" aria-label="Payment filters"><header><strong>Filters</strong><button type="button" onClick={onClose} aria-label="Close filters">×</button></header><div className="payment-v1180-filter-grid"><label><span>Search</span><input value={draft.search} onChange={(event) => set('search', event.target.value)} placeholder="Name, merchant, category, account or card"/></label><label><span>Date range</span><select value={draft.dateRange} onChange={(event) => set('dateRange', event.target.value)}>{PAYMENT_DATE_RANGES.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label><label><span>Status</span><select value={draft.status} onChange={(event) => set('status', event.target.value)}><option value="">All statuses</option>{Object.entries(PAYMENT_STATUS_LABELS).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label><label><span>Category</span><select value={draft.categoryId} onChange={(event) => set('categoryId', event.target.value)}><option value="">All categories</option>{(data.categories || []).filter((row) => row.is_active !== false).map((row) => <option value={row.id} key={row.id}>{row.path || row.name}</option>)}</select></label><label><span>Account</span><select value={draft.accountId} onChange={(event) => set('accountId', event.target.value)}><option value="">All Accounts</option>{(data.accounts || []).filter((row) => row.is_active !== false && !row.archived_at).map((row) => <option value={row.id} key={row.id}>{row.name}</option>)}</select></label><label><span>Payment method</span><select value={draft.paymentMethod} onChange={(event) => set('paymentMethod', event.target.value)}><option value="">All methods</option>{Object.entries(PAYMENT_METHOD_LABELS).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label><label className="payment-centre-check"><input type="checkbox" checked={draft.requiresAction} onChange={(event) => set('requiresAction', event.target.checked)}/><span>Requires action only</span></label></div><div className="payment-v1180-filter-actions"><button type="button" onClick={() => { onClear(); onClose(); }}>Clear</button><button type="button" className="primary" onClick={() => { onApply(); onClose(); }}>Apply</button></div></section></div>;
}

function CompactPaymentRow({ row, onView, onMarkPaid }) {
  const primary = paymentPrimaryAction(row);
  const reason = paymentAttentionReason(row);
  const source = paymentSourceLabel(row);
  const actionLabel = primary === 'mark_paid' ? 'Mark as paid' : 'View';
  const missing = [];
  if (!(row.expected_date || row.due_date)) missing.push('due date');
  if (!row.payment_method || row.payment_method === 'not_set') missing.push('payment method');
  if (!row.account_id && !row.card_id && !row.linked_account_name) missing.push('funding account');
  return <article className="payment-v1161-row"><button type="button" className="payment-v1161-row-main" onClick={() => onView(row)}><span className="name"><strong>{row.name}</strong><small>{row.category || 'Uncategorised'} · {source}</small></span><span className="date"><strong>{dateLabel(row.expected_date || row.due_date)}</strong>{row.days_overdue ? <small>Overdue by {row.days_overdue} day{row.days_overdue === 1 ? '' : 's'}</small> : null}</span><span className="funding"><strong>{row.payment_method_label || PAYMENT_METHOD_LABELS[row.payment_method] || 'Not Set'}</strong><small>{row.card_name || row.account_name || row.linked_account_name || reason || (row.payment_handling === 'automatic' ? 'Automatic' : 'Manual')}</small></span><strong className="amount">{money(rowAmount(row))}</strong><StatusBadge status={row.status}/>{missing.length > 0 && <span className="payment-v1180-incomplete">Payment details incomplete: missing {missing.join(', ')}.</span>}</button><button type="button" className="payment-v1161-row-action" onClick={() => primary === 'mark_paid' ? onMarkPaid(row) : onView(row)}>{actionLabel}</button></article>;
}

function QuickMarkPaid({ row, onClose, onSaved }) {
  const [form, setForm] = useState({ paid_date: localDateKey(), paid_amount: row?.expected_amount || row?.amount || '', note: '' });
  const [saving, setSaving] = useState(false); const [error, setError] = useState('');
  if (!row) return null;
  const submit = async (event) => { event.preventDefault(); setSaving(true); setError(''); try { const isBill = row.source_type === 'bill'; const path = isBill ? `/bills/${row.id}/mark-paid` : `/scheduled-payments/${row.id}/mark-paid`; const payload = isBill ? { paid_date: form.paid_date, paid_amount: form.paid_amount, note: form.note, version: row.version } : { actual_date: form.paid_date, actual_amount: form.paid_amount, note: form.note }; await apiRequest(path, { method: 'POST', body: JSON.stringify(payload) }); await onSaved(); } catch (requestError) { setError(requestError?.message || 'Could not mark this payment paid.'); } finally { setSaving(false); } };
  return <div className="payment-centre-modal-backdrop"><form className="payment-centre-mark-paid" onSubmit={submit}><header><div><h2>Mark as paid</h2><p>{row.name} · expected {money(row.expected_amount ?? row.amount)}</p></div><button type="button" onClick={onClose} aria-label="Close mark paid">×</button></header><div className="payment-centre-form"><label><span>Actual date</span><input required type="date" value={form.paid_date} onChange={(event) => setForm({ ...form, paid_date: event.target.value })}/></label><label><span>Actual amount</span><input required inputMode="decimal" value={form.paid_amount} onChange={(event) => setForm({ ...form, paid_amount: event.target.value })}/></label><label><span>Note (optional)</span><textarea rows="3" value={form.note} onChange={(event) => setForm({ ...form, note: event.target.value })}/></label>{error && <p className="error">{error}</p>}</div><footer><button type="button" onClick={onClose}>Cancel</button><button className="primary" disabled={saving}>{saving ? 'Saving…' : 'Mark as paid'}</button></footer></form></div>;
}

export default function PaymentCentreV1161(props) {
  const { data, onNavigate, onRefreshSupporting } = props;
  const initial = useMemo(() => defaultPaymentCentreFilters(), []);
  const [draft, setDraft] = useState(initial); const [filters, setFilters] = useState(initial); const [result, setResult] = useState(null); const [planning, setPlanning] = useState(null); const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const [expanded, setExpanded] = useState(() => new Set()); const [markingPaid, setMarkingPaid] = useState(null); const [mode, setMode] = useState(() => localStorage.getItem('fynvo.paymentCentre.timelineMode') || 'grouped'); const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const query = useMemo(() => buildPaymentCentreQuery(filters), [filters]);
  const load = async () => { setLoading(true); setError(''); try { const [centre, plan] = await Promise.all([apiRequest(query), apiRequest('/payment-planning')]); setResult(centre); setPlanning(plan); } catch (requestError) { setError(requestError?.message || 'Could not load the Payment Centre.'); } finally { setLoading(false); } };
  useEffect(() => { load(); }, [query]);
  useEffect(() => { localStorage.setItem('fynvo.paymentCentre.timelineMode', mode); }, [mode]);
  const groups = useMemo(() => groupForSimplifiedTimeline(result?.rows || []), [result?.rows]);
  const toggleGroup = (key) => setExpanded((current) => { const next = new Set(current); if (next.has(key)) next.delete(key); else next.add(key); return next; });
  const clear = () => { const next = defaultPaymentCentreFilters(); setDraft(next); setFilters(next); };
  const refreshed = async () => { setMarkingPaid(null); await Promise.allSettled([load(), onRefreshSupporting?.()]); };

  if (mode === 'detailed') return <section className="payment-v1161-shell"><div className="payment-v1161-top-actions"><button type="button" className="primary" onClick={() => onNavigate('Bills')}>+ Add Bill</button><div className="payment-v1161-mode"><button type="button" onClick={() => setMode('grouped')}>Grouped view</button><button type="button" className="active" aria-pressed="true">Chronological view</button></div></div><PaymentCentreV112 {...props}/></section>;

  return <section className="payment-v1161-shell"><div className="payment-v1161-top-actions"><button type="button" className="primary" onClick={() => onNavigate('Bills')}>+ Add Bill</button></div>{loading && !planning && !error && <div className="payment-centre-state pay-cycle-loading" role="status"><strong>Loading before-next-pay plan…</strong><p>Calculating the next Income event, commitments and Account funding.</p></div>}{planning && !error && <DecisionSummary planning={planning} onIncome={() => onNavigate('Income')}/>} {planning && !error && <PayCycleSummary planning={planning} onIncome={() => onNavigate('Income')}/>} {planning && !error && <PlanningOverview planning={planning} onAttention={() => { setDraft((current) => ({ ...current, requiresAction: true })); setFilters((current) => ({ ...current, requiresAction: true })); }}/>} {result && !error && <SummaryStrip summary={result.summary}/>}<FundingDetails planning={planning}/><MobileFilterBar filters={filters} setDraft={setDraft} setFilters={setFilters} onOpen={() => setMobileFiltersOpen(true)}/><FilterPanel draft={draft} setDraft={setDraft} data={data} onApply={() => setFilters({ ...draft })} onClear={clear}/>{loading && !result && <div className="payment-centre-state" role="status"><strong>Loading payments…</strong><p>Getting the latest household obligations.</p></div>}{error && <div className="payment-centre-state error-state" role="alert"><strong>Payment Centre could not load</strong><p>{error}</p><button type="button" onClick={load}>Retry</button></div>}{!loading && !error && result && result.rows.length === 0 && <div className="payment-centre-state"><strong>Nothing matches these filters</strong><p>No payment obligations were returned for this date range and filter combination.</p><button type="button" onClick={clear}>Clear filters</button></div>}{!error && result && result.rows.length > 0 && <section className={`payment-v1161-timeline ${loading ? 'refreshing' : ''}`}><div className="payment-v1161-timeline-head"><h2>Payment timeline</h2><div className="payment-v1161-mode"><button type="button" className="active" aria-pressed="true">Grouped view</button><button type="button" onClick={() => setMode('detailed')}>Chronological view</button></div></div>{groups.map((group) => { const isExpanded = expanded.has(group.key); const visible = isExpanded ? group.rows : group.rows.slice(0, GROUP_PREVIEW_COUNT); return <section className={`payment-v1161-group group-${group.key}`} key={group.key}><button type="button" className="payment-v1161-group-head" aria-expanded={isExpanded} onClick={() => toggleGroup(group.key)}><span><i aria-hidden="true"></i><strong>{group.label} ({group.rows.length})</strong></span><b>{money(group.total)}</b><em aria-hidden="true">⌃</em></button>{visible.map((row) => <CompactPaymentRow key={`${row.source_type}-${row.id}`} row={row} onView={() => setMode('detailed')} onMarkPaid={setMarkingPaid}/>)}{group.rows.length > GROUP_PREVIEW_COUNT && <button type="button" className="payment-v1161-view-all" onClick={() => toggleGroup(group.key)}>{isExpanded ? 'Show fewer' : `View all ${group.rows.length} ${group.label.toLowerCase()} payments`}</button>}</section>; })}</section>}<QuickMarkPaid row={markingPaid} onClose={() => setMarkingPaid(null)} onSaved={refreshed}/><MobileFilterSheet open={mobileFiltersOpen} draft={draft} setDraft={setDraft} data={data} onApply={() => setFilters({ ...draft })} onClear={clear} onClose={() => setMobileFiltersOpen(false)}/></section>;
}
