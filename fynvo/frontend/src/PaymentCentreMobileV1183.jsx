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
const SKIPPABLE = new Set(['upcoming', 'due', 'due_today', 'overdue', 'expected_automatically', 'auto_payment_unconfirmed', 'unknown']);

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
const rowKey = (row) => `${row.source_type}-${row.id}`;

const startOfToday = () => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return today;
};

const daysFromToday = (value) => {
  if (!value) return null;
  const due = new Date(`${String(value).slice(0, 10)}T00:00:00`);
  if (Number.isNaN(due.getTime())) return null;
  return Math.round((due - startOfToday()) / 86400000);
};

const timingLabel = (row) => {
  if (TERMINAL.has(row.status)) return row.status === 'paid' ? 'Paid' : row.status === 'skipped' ? 'Skipped' : 'Cancelled';
  const delta = daysFromToday(row.expected_date || row.due_date);
  if (delta === null) return 'Due date missing';
  if (delta < 0) return `${Math.abs(delta)} day${Math.abs(delta) === 1 ? '' : 's'} overdue`;
  if (delta === 0) return 'Due today';
  if (delta === 1) return 'Due tomorrow';
  if (delta <= 7) return `Due in ${delta} days`;
  return `Due ${dateLabel(row.expected_date || row.due_date)}`;
};

const missingFields = (row) => {
  const missing = [];
  if (!(row.expected_date || row.due_date)) missing.push('Due date');
  if (!row.payment_method || row.payment_method === 'not_set') missing.push('Payment method');
  if (!row.account_id && !row.card_id && !row.linked_account_name) missing.push('Funding account');
  if (!row.category_id && !row.category) missing.push('Category');
  return missing;
};

const attentionRank = (row) => {
  const reason = String(paymentAttentionReason(row) || '').toLowerCase();
  const status = String(row?.status || '').toLowerCase();
  if (status === 'overdue') return 0;
  if (row?.match_review_available || reason.includes('reconciliation')) return 1;
  if (reason.includes('funding') || reason.includes('account')) return 2;
  if (status === 'auto_payment_unconfirmed') return 3;
  if (reason.includes('payment method')) return 4;
  if (status === 'due' || status === 'due_today') return 5;
  return 6;
};

function groupedRows(rows = [], mode = 'grouped', nextIncomeDate = null) {
  if (mode === 'chronological') {
    const groups = new Map();
    rows.forEach((row) => {
      const raw = row.expected_date || row.due_date;
      const key = TERMINAL.has(row.status) ? 'Payment history' : raw ? String(raw).slice(0, 10) : 'Date not specified';
      groups.set(key, [...(groups.get(key) || []), row]);
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
        total: values.reduce((sum, row) => sum + rowAmount(row), 0),
      }));
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const seven = new Date(today);
  seven.setDate(seven.getDate() + 7);
  const nextIncome = nextIncomeDate ? new Date(`${String(nextIncomeDate).slice(0, 10)}T00:00:00`) : null;
  const buckets = [
    { key: 'overdue', label: 'Overdue', rows: [] },
    { key: 'today', label: 'Due today', rows: [] },
    { key: 'before-pay', label: 'Due before next pay', rows: [] },
    { key: 'next-seven', label: 'Next 7 days', rows: [] },
    { key: 'later', label: 'Later this month', rows: [] },
    { key: 'missing', label: 'Date not specified', rows: [] },
    { key: 'history', label: 'Payment history', rows: [] },
  ];
  const byKey = new Map(buckets.map((group) => [group.key, group]));

  rows.forEach((row) => {
    if (TERMINAL.has(row.status)) return byKey.get('history').rows.push(row);
    const raw = row.expected_date || row.due_date;
    if (!raw) return byKey.get('missing').rows.push(row);
    const due = new Date(`${String(raw).slice(0, 10)}T00:00:00`);
    const delta = Math.round((due - today) / 86400000);
    if (row.status === 'overdue' || (row.status === 'auto_payment_unconfirmed' && delta < 0) || delta < 0) return byKey.get('overdue').rows.push(row);
    if (delta === 0) return byKey.get('today').rows.push(row);
    if (nextIncome && due >= today && due < nextIncome) return byKey.get('before-pay').rows.push(row);
    if (due >= today && due <= seven) return byKey.get('next-seven').rows.push(row);
    return byKey.get('later').rows.push(row);
  });

  return buckets.filter((group) => group.rows.length).map((group) => ({
    ...group,
    total: group.rows.reduce((sum, row) => sum + rowAmount(row), 0),
    rows: [...group.rows].sort((a, b) => attentionRank(a) - attentionRank(b) || String(a.expected_date || a.due_date || '').localeCompare(String(b.expected_date || b.due_date || '')) || rowAmount(b) - rowAmount(a)),
  }));
}

function PayCycleDecision({ planning, onIncome, onFixSetup }) {
  const payCycle = planning?.pay_cycle;
  if (!payCycle) return null;
  const before = payCycle.before_next_income || {};
  const projected = finite(before.projected_cash);
  const hasIncome = Boolean(payCycle.next_income);
  const unknownAccounts = (payCycle.accounts || []).filter((row) => row.status === 'unknown');
  const status = !hasIncome || payCycle.status === 'unknown' ? 'unknown' : payCycle.status === 'shortfall' || projected !== null && projected < 0 ? 'shortfall' : 'funded';
  const headline = status === 'shortfall'
    ? `${money(Math.abs(projected ?? before.shortfall ?? 0))} short`
    : status === 'unknown'
      ? 'Cash position needs setup'
      : projected === null ? 'Funded before next pay' : `${money(Math.max(projected, 0))} remaining`;
  const explanation = !hasIncome
    ? 'Next income amount or date must be confirmed.'
    : unknownAccounts.length
      ? `${unknownAccounts.length} funding account${unknownAccounts.length === 1 ? '' : 's'} need assignment or balance information.`
      : payCycle.completeness?.message || 'Funding account assignments or balances are incomplete.';

  return <section className={`payment-v1183-decision ${status}`} aria-label="Before next pay">
    <div className="payment-v1183-decision-head"><div><small>BEFORE NEXT PAY</small><h2>{hasIncome ? `${payCycle.next_income.name || 'Income'} · ${dateLabel(payCycle.next_income.date)}` : 'Next income not confirmed'}</h2></div><strong className="payment-v1183-decision-value">{headline}</strong></div>
    <p className="payment-v1183-decision-copy">{status === 'unknown' ? explanation : status === 'shortfall' ? 'Available funds do not cover known commitments before the next income.' : 'Known commitments are covered before the next income.'}</p>
    {status === 'unknown' && <div className="payment-v1183-decision-actions">{!hasIncome ? <button type="button" className="primary ghost" onClick={onIncome}>Review Income</button> : <button type="button" className="primary" onClick={onFixSetup}>Fix setup</button>}</div>}
    <div className="payment-v1183-decision-grid"><div><span>Available now</span><strong>{money(before.current_available_cash)}</strong></div><div><span>Required before pay</span><strong>{money(before.commitments_total)}</strong></div><div><span>Next income</span><strong>{hasIncome ? money(payCycle.next_income.amount) : 'Not known'}</strong></div></div>
    <details className="payment-v1183-calculation"><summary>View calculation</summary><div className="payment-v1183-calculation-grid"><div><span>Payments due</span><strong>{before.commitment_count ?? '—'}</strong></div><div><span>Overdue included</span><strong>{money(before.overdue_total)}</strong></div><div><span>Automatic payments</span><strong>{money(before.automatic_payment_total)}</strong></div><div><span>Projected before pay</span><strong>{money(before.projected_cash)}</strong></div><div><span>Projected after pay</span><strong>{money(payCycle.after_next_income?.projected_cash)}</strong></div><div><span>Next pay date</span><strong>{hasIncome ? dateLabel(payCycle.next_income.date) : '—'}</strong></div></div></details>
  </section>;
}

function MissingInfoDialog({ row, onClose, onFix }) {
  if (!row) return null;
  const missing = missingFields(row);
  return <div className="payment-centre-modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="payment-v1183-missing-dialog" role="dialog" aria-modal="true" aria-label={`Missing information for ${row.name}`}><header><div><h2>Missing information</h2><p>{row.name}</p></div><button type="button" onClick={onClose} aria-label="Close missing information">×</button></header><ul>{missing.map((item) => <li key={item}>{item}</li>)}</ul><footer><button type="button" onClick={onClose}>Close</button><button type="button" className="primary" onClick={onFix}>Fix details</button></footer></section></div>;
}

function MarkPaidDialog({ row, onClose, onSaved }) {
  const [form, setForm] = useState({ paid_date: new Date().toISOString().slice(0, 10), paid_amount: row?.expected_amount ?? row?.amount ?? '', note: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  if (!row) return null;
  const submit = async (event) => {
    event.preventDefault(); setSaving(true); setError('');
    try {
      const isBill = row.source_type === 'bill';
      await apiRequest(isBill ? `/bills/${row.id}/mark-paid` : `/scheduled-payments/${row.id}/mark-paid`, {
        method: 'POST',
        body: JSON.stringify(isBill ? { paid_date: form.paid_date, paid_amount: form.paid_amount, note: form.note, version: row.version } : { actual_date: form.paid_date, actual_amount: form.paid_amount, note: form.note }),
      });
      await onSaved();
    } catch (requestError) { setError(requestError?.message || 'Could not mark this payment paid.'); }
    finally { setSaving(false); }
  };
  return <div className="payment-centre-modal-backdrop"><form className="payment-centre-mark-paid" onSubmit={submit}><header><div><h2>Mark as paid</h2><p>{row.name} · expected {money(row.expected_amount ?? row.amount)}</p></div><button type="button" onClick={onClose} aria-label="Close mark paid">×</button></header><div className="payment-centre-form"><label><span>Actual date</span><input required type="date" value={form.paid_date} onChange={(event) => setForm({ ...form, paid_date: event.target.value })}/></label><label><span>Actual amount</span><input required inputMode="decimal" value={form.paid_amount} onChange={(event) => setForm({ ...form, paid_amount: event.target.value })}/></label><label><span>Note (optional)</span><textarea rows="3" value={form.note} onChange={(event) => setForm({ ...form, note: event.target.value })}/></label>{error && <p className="error">{error}</p>}</div><footer><button type="button" onClick={onClose}>Cancel</button><button className="primary" disabled={saving}>{saving ? 'Saving…' : 'Mark as paid'}</button></footer></form></div>;
}

function PaymentCard({ row, selecting, selected, onToggle, onMarkPaid, onOpenDetailed, onShowMissing, onNavigate }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const cardRef = useRef(null);
  const primary = paymentPrimaryAction(row);
  const actions = paymentAvailableActions(row).filter((action) => !['view', 'mark_paid'].includes(action));
  const missing = missingFields(row);
  const due = row.expected_date || row.due_date;
  const overdue = Number(row.days_overdue || 0);
  const automatic = row.payment_handling === 'automatic';
  const method = row.payment_method_label || PAYMENT_METHOD_LABELS[row.payment_method];
  const funding = row.card_name || row.account_name || row.linked_account_name;
  useEffect(() => {
    if (!menuOpen) return undefined;
    const closeOnOutside = (event) => {
      if (!cardRef.current?.contains(event.target)) setMenuOpen(false);
    };
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') setMenuOpen(false);
    };
    document.addEventListener('pointerdown', closeOnOutside);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('pointerdown', closeOnOutside);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [menuOpen]);
  const statusText = row.status === 'auto_payment_unconfirmed' ? 'Automatic payment unconfirmed' : automatic && !TERMINAL.has(row.status) ? 'Expected automatically' : timingLabel(row);
  const issueLabel = missing.length === 1 ? `Missing ${missing[0].toLowerCase()}` : missing.length > 1 ? `${missing.length} details missing` : '';
  const runAction = (action) => {
    setMenuOpen(false);
    if (action === 'review') return onNavigate(row.source_type === 'scheduled_payment' ? 'Review Queue' : 'Transactions');
    if (action === 'open_recurring') return onNavigate('Recurring Expenses');
    if (action === 'edit') return onNavigate('Bills');
    return onOpenDetailed();
  };
  return <article ref={cardRef} className={`payment-v1183-card ${row.status === 'overdue' || Number(row.days_overdue || 0) > 0 ? 'overdue' : paymentAttentionReason(row) || missing.length ? 'attention' : ''}`}>
    {selecting && <label className="payment-v1183-select-box"><input type="checkbox" checked={selected} onChange={() => onToggle(row)}/><span className="sr-only">Select {row.name}</span></label>}
    <button type="button" className="payment-v1183-card-main" onClick={selecting ? () => onToggle(row) : onOpenDetailed}><span className="payment-v1183-card-name"><strong>{row.name}</strong><small>{row.category || 'Uncategorised'} · {paymentSourceLabel(row)}</small></span><strong className="payment-v1183-card-amount">{money(rowAmount(row))}</strong><span className="payment-v1183-card-meta"><span className={overdue > 0 ? 'danger' : automatic ? 'automatic' : ''}>{statusText}</span><span>· {automatic ? 'Automatic' : 'Manual'}</span>{method && row.payment_method !== 'not_set' && <span>· {method}</span>}{funding && <span>· {funding}</span>}</span></button>
    {issueLabel && <button type="button" className="payment-v1183-missing" onClick={() => onShowMissing(row)}>⚠ {issueLabel}</button>}
    {!selecting && <div className={`payment-v1183-card-actions ${primary !== 'mark_paid' ? 'single' : ''}`}>{primary === 'mark_paid' && <button type="button" className="mark-paid" onClick={() => onMarkPaid(row)}>Mark paid</button>}{automatic && primary !== 'mark_paid' && !TERMINAL.has(row.status) && <span className="automatic-status">Expected automatically</span>}<button type="button" className="overflow" aria-expanded={menuOpen} aria-label={`More actions for ${row.name}`} onClick={() => setMenuOpen((open) => !open)}>⋯</button></div>}
    {menuOpen && <div className="payment-v1183-overflow" role="menu"><button type="button" role="menuitem" onClick={() => { setMenuOpen(false); onOpenDetailed(); }}>View payment details</button>{missing.length > 0 && <button type="button" role="menuitem" onClick={() => { setMenuOpen(false); onShowMissing(row); }}>Review missing information</button>}{actions.map((action) => <button type="button" role="menuitem" key={action} onClick={() => runAction(action)}>{({ review: 'Review', edit: 'Edit Bill', cancel: 'Cancel Bill', change_date: 'Change payment date', skip: 'Skip payment', restore: 'Restore payment', open_recurring: 'Open Recurring Expense' })[action] || action.replaceAll('_', ' ')}</button>)}</div>}
  </article>;
}

export default function PaymentCentreMobileV1183({ data = {}, onNavigate = () => {}, onQuickAdd = () => {}, onAddBill = () => {}, onRefreshSupporting = null }) {
  const initial = useMemo(() => defaultPaymentCentreFilters(), []);
  const [filters, setFilters] = useState(initial);
  const [result, setResult] = useState(null);
  const [planning, setPlanning] = useState(null);
  const [safePlan, setSafePlan] = useState(null);
  const [summary, setSummary] = useState({ next30: null, overdue: null, attention: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [fullWorkspace, setFullWorkspace] = useState(false);
  const [markingPaid, setMarkingPaid] = useState(null);
  const [missingRow, setMissingRow] = useState(null);
  const [selecting, setSelecting] = useState(false);
  const [selected, setSelected] = useState([]);
  const [collapsed, setCollapsed] = useState({});
  const [bulkBusy, setBulkBusy] = useState(false);
  const [actionError, setActionError] = useState('');
  const [mode, setMode] = useState(() => localStorage.getItem('fynvo.paymentCentre.timelineMode.v1183') || 'grouped');
  const query = useMemo(() => buildPaymentCentreQuery(filters), [filters]);
  const groups = useMemo(() => groupedRows(result?.rows || [], mode, planning?.pay_cycle?.next_income?.date), [result?.rows, mode, planning?.pay_cycle?.next_income?.date]);
  const selectedRows = useMemo(() => (result?.rows || []).filter((row) => selected.includes(rowKey(row))), [result?.rows, selected]);

  const load = async () => {
    setLoading(true); setError('');
    try {
      const results = await Promise.allSettled([
        apiRequest(query), apiRequest('/payment-planning'), apiRequest('/payment-centre?date_range=next_30_days'), apiRequest('/payment-centre?date_range=overdue'), apiRequest('/payment-centre?date_range=next_30_days&requires_action=true'), apiRequest('/payment-planning/safe-to-spend'),
      ]);
      const [paymentsResult, planResult, next30Result, overdueResult, attentionResult, safeResult] = results;
      if (paymentsResult.status === 'rejected') throw paymentsResult.reason;
      const payments = paymentsResult.value;
      const plan = planResult.status === 'fulfilled' ? planResult.value : null;
      const next30 = next30Result.status === 'fulfilled' ? next30Result.value : null;
      const overdue = overdueResult.status === 'fulfilled' ? overdueResult.value : null;
      const attention = attentionResult.status === 'fulfilled' ? attentionResult.value : null;
      const safe = safeResult.status === 'fulfilled' ? safeResult.value : null;
      const metric = (payload) => ({ count: payload?.rows?.length || 0, total: (payload?.rows || []).reduce((sum, row) => sum + rowAmount(row), 0) });
      setResult(payments); setPlanning(plan); setSafePlan(safe || null); setSummary({ next30: metric(next30), overdue: metric(overdue), attention: metric(attention) });
    } catch (requestError) { setError(requestError?.message || 'Payment Centre could not load.'); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [query]);
  useEffect(() => { localStorage.setItem('fynvo.paymentCentre.timelineMode.v1183', mode); }, [mode]);

  const refreshed = async () => { setMarkingPaid(null); setMissingRow(null); await Promise.allSettled([load(), onRefreshSupporting?.()]); };
  const quick = (next) => setFilters((current) => ({ ...current, ...next }));
  const toggle = (row) => setSelected((current) => current.includes(rowKey(row)) ? current.filter((key) => key !== rowKey(row)) : [...current, rowKey(row)]);
  const selectAll = () => setSelected((result?.rows || []).filter((row) => !TERMINAL.has(row.status)).map(rowKey));

  const bulkMarkPaid = async () => {
    const rows = selectedRows.filter((row) => paymentAvailableActions(row).includes('mark_paid'));
    if (!rows.length) return;
    const total = rows.reduce((sum, row) => sum + rowAmount(row), 0);
    if (!window.confirm(`Mark ${rows.length} payment${rows.length === 1 ? '' : 's'} paid for ${money(total)}?`)) return;
    setBulkBusy(true);
    try {
      for (const row of rows) {
        const isBill = row.source_type === 'bill';
        await apiRequest(isBill ? `/bills/${row.id}/mark-paid` : `/scheduled-payments/${row.id}/mark-paid`, {
          method: 'POST',
          body: JSON.stringify(isBill ? { paid_date: new Date().toISOString().slice(0, 10), paid_amount: rowAmount(row), note: 'Bulk marked paid', version: row.version } : { actual_date: new Date().toISOString().slice(0, 10), actual_amount: rowAmount(row), note: 'Bulk marked paid' }),
        });
      }
      setSelected([]); setSelecting(false); await refreshed();
    } catch (requestError) {
      setActionError(requestError?.message || 'Some selected payments could not be marked as paid. No unsuccessful payment was presented as complete.');
    } finally { setBulkBusy(false); }
  };

  const bulkSkip = async () => {
    const rows = selectedRows.filter((row) => row.source_type === 'scheduled_payment' && SKIPPABLE.has(row.status) && !row.matched_transaction_id);
    if (!rows.length) return;
    const total = rows.reduce((sum, row) => sum + rowAmount(row), 0);
    if (!window.confirm(`Skip ${rows.length} scheduled payment${rows.length === 1 ? '' : 's'} totalling ${money(total)}?`)) return;
    setBulkBusy(true);
    try {
      for (const row of rows) {
        await apiRequest(`/scheduled-payments/${row.id}/skip`, { method: 'POST', body: JSON.stringify({ reason: 'User requested skip', note: 'Bulk skipped from Payment Centre', version: row.version }) });
      }
      setSelected([]); setSelecting(false); await refreshed();
    } catch (requestError) {
      setActionError(requestError?.message || 'Some selected payments could not be skipped.');
    } finally { setBulkBusy(false); }
  };

  if (fullWorkspace) return <section className="payment-v1183-shell payment-v1183-full-workspace"><div className="payment-v1183-toolbar"><button type="button" className="payment-v1183-back" onClick={() => setFullWorkspace(false)}>‹ Back to compact queue</button></div><PaymentCentreV112 data={data} onNavigate={onNavigate}/></section>;

  return <section className="payment-v1183-shell" aria-label="Payment Centre mobile workspace">
    <div className="payment-v1183-toolbar"><div className="payment-v1183-create-row"><button type="button" className="primary ghost" onClick={onQuickAdd}>+ Add…</button><button type="button" className="primary" onClick={onAddBill}>+ Add Bill</button></div><div className="payment-v1183-mode" role="group" aria-label="Payment timeline view"><button type="button" className={mode === 'grouped' ? 'active' : ''} aria-pressed={mode === 'grouped'} onClick={() => setMode('grouped')}>Grouped</button><button type="button" className={mode === 'chronological' ? 'active' : ''} aria-pressed={mode === 'chronological'} onClick={() => setMode('chronological')}>Chronological</button></div><div className="payment-v1183-filter-row"><button type="button" className={filters.dateRange === 'next_30_days' && !filters.requiresAction ? 'active' : ''} onClick={() => quick({ dateRange: 'next_30_days', requiresAction: false })}>Next 30 days · {summary.next30?.count ?? '—'}</button><button type="button" className={filters.dateRange === 'overdue' ? 'active' : ''} onClick={() => quick({ dateRange: 'overdue', requiresAction: false })}>Overdue · {summary.overdue?.count ?? '—'}</button><button type="button" className={filters.requiresAction ? 'active' : ''} onClick={() => quick({ dateRange: 'next_30_days', requiresAction: true })}>Needs attention · {summary.attention?.count ?? '—'}</button><button type="button" onClick={() => setFullWorkspace(true)}>Filters & details</button></div></div>

    <section className="payment-v1183-summary" aria-label="Payment Centre summary"><div><span>Safe to spend</span><strong>{safePlan?.safe_to_spend == null ? '—' : money(safePlan.safe_to_spend)}</strong></div><div><span>Overdue</span><strong>{summary.overdue ? money(summary.overdue.total) : '—'}</strong></div><div><span>Before next pay</span><strong>{money(planning?.pay_cycle?.before_next_income?.commitments_total)}</strong></div><div><span>Protected buffer</span><strong>{safePlan?.protected_buffer == null ? '—' : money(safePlan.protected_buffer)}</strong></div><div><span>Next 30 days</span><strong>{summary.next30 ? money(summary.next30.total) : '—'}</strong></div></section>
    {!loading && planning && <PayCycleDecision planning={planning} onIncome={() => onNavigate('Income')} onFixSetup={() => setFullWorkspace(true)}/>} 
    <div className="payment-v1183-selection-bar"><button type="button" onClick={() => { setActionError(''); setSelecting((value) => !value); setSelected([]); }}>{selecting ? 'Cancel selection' : 'Select'}</button>{selecting && <><button type="button" onClick={selectAll}>Select all</button><span>{selected.length} selected</span><button type="button" disabled={bulkBusy || !selectedRows.some((row) => paymentAvailableActions(row).includes('mark_paid'))} onClick={bulkMarkPaid}>Mark paid</button><button type="button" disabled={bulkBusy || !selectedRows.some((row) => row.source_type === 'scheduled_payment' && SKIPPABLE.has(row.status) && !row.matched_transaction_id)} onClick={bulkSkip}>Skip</button></>}</div>
    {actionError && <div className="payment-v1183-action-error" role="alert"><strong>Payment action could not be completed</strong><p>{actionError}</p><button type="button" onClick={() => setActionError('')}>Dismiss</button></div>}

    {loading && !result ? <div className="payment-v1183-skeleton" role="status" aria-label="Loading payments">{[0, 1, 2].map((item) => <div className="payment-v1183-skeleton-row" key={item}/>)}</div> : error ? <div className="payment-v1183-error"><strong>Payment Centre could not load</strong><p>{error}</p><button type="button" onClick={load}>Retry</button></div> : result?.rows?.length ? <section className="payment-v1183-timeline">{groups.map((group) => <section className="payment-v1183-group" key={group.key}><button type="button" className="payment-v1183-group-head" aria-expanded={!collapsed[group.key]} onClick={() => setCollapsed((current) => ({ ...current, [group.key]: !current[group.key] }))}><span><strong>{group.label}</strong><small>{group.rows.length} payment{group.rows.length === 1 ? '' : 's'} · {money(group.total)}</small></span><span aria-hidden="true">{collapsed[group.key] ? '+' : '−'}</span></button>{!collapsed[group.key] && group.rows.map((row) => <PaymentCard key={rowKey(row)} row={row} selecting={selecting} selected={selected.includes(rowKey(row))} onToggle={toggle} onMarkPaid={setMarkingPaid} onOpenDetailed={() => setFullWorkspace(true)} onShowMissing={setMissingRow} onNavigate={onNavigate}/>)}</section>)}</section> : <div className="payment-v1183-empty"><strong>No payments in this view</strong><p>Choose a different quick filter or open Filters & details.</p></div>}

    <MarkPaidDialog row={markingPaid} onClose={() => setMarkingPaid(null)} onSaved={refreshed}/>
    <MissingInfoDialog row={missingRow} onClose={() => setMissingRow(null)} onFix={() => { setMissingRow(null); setFullWorkspace(true); }}/>
  </section>;
}
