import { useEffect, useMemo, useState } from 'react';
import { apiRequest } from './apiClient.js';
import { paymentAttentionReason, paymentAvailableActions, paymentSourceLabel } from './paymentCentreModel.js';

const TERMINAL = new Set(['paid', 'skipped', 'cancelled']);
const ACTIVE_STATUSES = new Set(['upcoming', 'due', 'due_today', 'overdue', 'expected_automatically', 'auto_payment_unconfirmed', 'unknown']);
const finite = (value) => { if (value === null || value === undefined || value === '') return null; const number = Number(value); return Number.isFinite(number) ? number : null; };
const money = (value) => { const number = finite(value); return number === null ? '—' : new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(number); };
const dateValue = (value) => value ? String(value).slice(0, 10) : null;
const parseDate = (value) => { const key = dateValue(value); if (!key) return null; const [year, month, day] = key.split('-').map(Number); const date = new Date(year, month - 1, day); return Number.isNaN(date.getTime()) ? null : date; };
const dateLabel = (value) => { const date = parseDate(value); return date ? new Intl.DateTimeFormat('en-AU', { weekday: 'short', day: 'numeric', month: 'short' }).format(date) : 'Date unavailable'; };
const today = () => { const date = new Date(); date.setHours(0, 0, 0, 0); return date; };
const daysUntil = (value) => { const date = parseDate(value); if (!date) return null; return Math.round((date - today()) / 86400000); };
const timing = (row) => { const days = daysUntil(row.expected_date || row.due_date); if (row.status === 'overdue' || days < 0) return `Overdue by ${Math.max(1, Math.abs(days || 0))} day${Math.abs(days || 0) === 1 ? '' : 's'}`; if (days === 0) return 'Due today'; if (days === 1) return 'Due tomorrow'; if (days != null && days <= 7) return `Due in ${days} days`; return dateLabel(row.expected_date || row.due_date); };
const amount = (row) => Math.abs(Number(row?.actual_amount ?? row?.expected_amount ?? row?.amount ?? 0) || 0);
const rowKey = (row) => `${row.source_type || 'payment'}-${row.id}`;

function actionLabel(action) { return ({ mark_paid: 'Mark as paid', skip: 'Skip payment', change_date: 'Change payment date', edit: 'Edit bill', cancel: 'Cancel bill', open_recurring: 'Edit recurring schedule', review: 'Review payment' })[action] || action.replaceAll('_', ' '); }
function iconFor(row) { const text = `${row.name || ''} ${row.merchant || ''}`.toLowerCase(); if (text.includes('electric') || text.includes('power')) return 'ϟ'; if (text.includes('loan') || text.includes('car')) return '▣'; if (text.includes('internet')) return '◉'; return '$'; }

function groupUpcoming(rows) {
  const buckets = [{ key: 'within-7', label: 'Due within 7 days', rows: [] }, { key: 'within-30', label: 'Due in 8–30 days', rows: [] }, { key: 'later', label: 'Due later', rows: [] }];
  rows.forEach((row) => { const days = daysUntil(row.expected_date || row.due_date); const bucket = days != null && days <= 7 ? buckets[0] : days != null && days <= 30 ? buckets[1] : buckets[2]; bucket.rows.push(row); });
  return buckets.filter((bucket) => bucket.rows.length).map((bucket) => ({ ...bucket, total: bucket.rows.reduce((sum, row) => sum + amount(row), 0) }));
}

function EventRow({ row, onOpen, resolved = false }) {
  return <button type="button" className={`fynvo-payments-v1240-event ${resolved ? 'resolved' : ''}`} onClick={() => onOpen(row)}><span className="fynvo-payments-v1240-icon">{resolved ? '✓' : iconFor(row)}</span><span className="fynvo-payments-v1240-event-copy"><strong>{row.name || row.merchant || row.payee || 'Payment'}</strong><small>{resolved ? (row.status === 'paid' ? 'Marked as paid' : row.status) : row.attention_reason || timing(row)}</small>{!resolved && <small className="source">{paymentSourceLabel(row)}</small>}</span><strong className="fynvo-payments-v1240-amount">{money(amount(row))}</strong><span className="fynvo-payments-v1240-chevron">›</span></button>;
}

function ActionSheet({ row, onClose, onAction }) {
  if (!row) return null;
  const actions = paymentAvailableActions(row).filter((action) => action !== 'view');
  return <div className="fynvo-payments-v1240-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="fynvo-payments-v1240-sheet" role="dialog" aria-modal="true" aria-label={`Actions for ${row.name || 'payment'}`}><header><div><h2>{row.name || 'Payment'}</h2><p>{money(amount(row))} · {dateLabel(row.expected_date || row.due_date)}</p></div><button type="button" onClick={onClose} aria-label="Close payment actions">×</button></header><div className="fynvo-payments-v1240-sheet-actions">{actions.map((action) => <button type="button" key={action} className={['cancel', 'skip'].includes(action) ? 'destructive' : ''} onClick={() => onAction(action)}>{actionLabel(action)}</button>)}{!actions.length && <p>This payment has no further actions.</p>}</div></section></div>;
}

function ChangeDateDialog({ row, onClose, onSaved }) {
  const [date, setDate] = useState(dateValue(row?.expected_date || row?.due_date) || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  if (!row) return null;
  const submit = async (event) => {
    event.preventDefault(); setSaving(true); setError('');
    try {
      await apiRequest(`/scheduled-payments/${row.id}/reschedule`, { method: 'POST', body: JSON.stringify({ expected_date: date, reason: 'User requested different date', version: row.version }) });
      await onSaved();
    } catch (requestError) { setError(requestError?.message || 'Payment date could not be changed.'); }
    finally { setSaving(false); }
  };
  return <div className="fynvo-payments-v1240-backdrop" role="presentation"><form className="fynvo-payments-v1240-sheet" role="dialog" aria-modal="true" aria-label={`Change payment date for ${row.name || 'payment'}`} onSubmit={submit}><header><div><h2>Change payment date</h2><p>{row.name || 'Payment'} · {money(amount(row))}</p></div><button type="button" onClick={onClose} aria-label="Close change payment date">×</button></header><label className="fynvo-payments-v1240-date-field"><span>New expected date</span><input required type="date" value={date} onChange={(event) => setDate(event.target.value)} /></label>{error && <p className="fynvo-payments-v1240-form-error" role="alert">{error}</p>}<footer><button type="button" onClick={onClose}>Cancel</button><button className="primary" disabled={saving}>{saving ? 'Saving…' : 'Save date'}</button></footer></form></div>;
}

export default function PaymentWorkspaceV1240({ onNavigate = () => {}, onQuickAdd = () => {}, onAddBill = () => {}, onRefreshSupporting = null }) {
  const [view, setView] = useState(() => localStorage.getItem('fynvo.payments.view.v1240') || 'upcoming');
  const [rows, setRows] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);
  const [actionError, setActionError] = useState('');
  const [dateEditor, setDateEditor] = useState(null);
  const [attentionCount, setAttentionCount] = useState(null);

  const load = async () => {
    setLoading(true); setError(''); setActionError('');
    const results = await Promise.allSettled([
      apiRequest('/payment-centre?date_range=next_90_days'),
      apiRequest('/payment-centre?date_range=history'),
      apiRequest('/payment-centre?date_range=next_90_days&requires_action=true'),
    ]);
    if (results[0].status === 'fulfilled') setRows(results[0].value?.rows || []); else setError('Payments could not load. Try again.');
    if (results[1].status === 'fulfilled') setHistory(results[1].value?.rows || []); else setHistory([]);
    if (results[2].status === 'fulfilled') setAttentionCount(results[2].value?.rows?.length ?? 0); else setAttentionCount(null);
    setLoading(false);
  };
  useEffect(() => { load(); }, []);
  useEffect(() => { localStorage.setItem('fynvo.payments.view.v1240', view); }, [view]);

  const activeRows = useMemo(() => rows.filter((row) => !TERMINAL.has(row.status) && ACTIVE_STATUSES.has(row.status || 'upcoming')), [rows]);
  const attentionRows = useMemo(() => activeRows.filter((row) => row.requires_action || paymentAttentionReason(row)).sort((a, b) => String(a.status).localeCompare(String(b.status))), [activeRows]);
  const upcomingRows = useMemo(() => activeRows.filter((row) => !paymentAttentionReason(row)).sort((a, b) => String(a.expected_date || a.due_date || '').localeCompare(String(b.expected_date || b.due_date || ''))), [activeRows]);
  const groups = useMemo(() => groupUpcoming(upcomingRows), [upcomingRows]);
  const nextPayment = upcomingRows[0] || activeRows[0] || null;
  const resolvedRows = useMemo(() => history.filter((row) => TERMINAL.has(row.status)).slice(0, 3), [history]);

  const performAction = async (action) => {
    if (!selected) return;
    const row = selected; setSelected(null);
    if (action === 'edit' || action === 'cancel') return onNavigate('Bills');
    if (action === 'open_recurring') return onNavigate('Recurring Expenses');
    if (action === 'review') return onNavigate('Review Queue');
    if (action === 'change_date') { setDateEditor(row); return; }
    try {
      if (action === 'mark_paid') {
        const isBill = row.source_type === 'bill';
        await apiRequest(isBill ? `/bills/${row.id}/mark-paid` : `/scheduled-payments/${row.id}/mark-paid`, { method: 'POST', body: JSON.stringify(isBill ? { paid_date: new Date().toISOString().slice(0, 10), paid_amount: amount(row), note: 'Marked paid from Payments', version: row.version } : { actual_date: new Date().toISOString().slice(0, 10), actual_amount: amount(row), note: 'Marked paid from Payments' }) });
      } else if (action === 'skip') {
        await apiRequest(`/scheduled-payments/${row.id}/skip`, { method: 'POST', body: JSON.stringify({ reason: 'User requested skip', note: 'Skipped from Payments', version: row.version }) });
      } else { setActionError('This action is available from the payment details workflow.'); return; }
      await Promise.allSettled([load(), onRefreshSupporting?.()]);
    } catch (requestError) { setActionError(requestError?.message || 'The payment action could not be completed.'); }
  };

  const tab = (key, label) => <button type="button" className={view === key ? 'active' : ''} aria-pressed={view === key} onClick={() => setView(key)}>{label}{key === 'attention' && attentionCount > 0 && <span className="fynvo-payments-v1240-badge">{attentionCount}</span>}</button>;
  return <section className="fynvo-payments-v1240" aria-label="Payments"><header className="fynvo-payments-v1240-heading"><strong>Fynvo</strong><div><button type="button" aria-label="Notifications">♧</button><button type="button" aria-label="Settings">⚙</button></div><h1>Payments</h1><p>{view === 'attention' ? 'Payments that need your attention' : 'Your upcoming and recent payments'}</p></header><nav className="fynvo-payments-v1240-tabs" aria-label="Payments views">{tab('upcoming', 'Upcoming')}{tab('attention', 'Attention')}{tab('timeline', 'Timeline')}{tab('manage', 'Manage')}</nav>{actionError && <div className="fynvo-payments-v1240-error" role="alert">{actionError}<button type="button" onClick={() => setActionError('')}>Dismiss</button></div>}{loading ? <div className="fynvo-payments-v1240-loading" role="status" aria-label="Loading payments"><span/><span/><span/></div> : error ? <div className="fynvo-payments-v1240-empty" role="alert"><strong>{error}</strong><button type="button" onClick={load}>Retry</button></div> : <>
    {view === 'upcoming' && <><section className="fynvo-payments-v1240-next fynvo-ui-card"><div className="fynvo-payments-v1240-next-icon">▣</div><div><small>Next payment</small><strong>{nextPayment ? money(amount(nextPayment)) : 'No upcoming payments'}</strong>{nextPayment && <p>{nextPayment.name || 'Payment'}<br/>{dateLabel(nextPayment.expected_date || nextPayment.due_date)} · {timing(nextPayment)}</p>}</div>{nextPayment && <button type="button" onClick={() => setSelected(nextPayment)} aria-label={`Open ${nextPayment.name || 'payment'}`}>›</button>}</section><div className="fynvo-payments-v1240-section-head"><h2>Upcoming payments</h2><button type="button" onClick={() => setView('timeline')}>See all</button></div>{groups.length ? groups.map((group) => <section className="fynvo-payments-v1240-group" key={group.key}><div className="fynvo-payments-v1240-group-head"><strong>{group.label}</strong><b>{money(group.total)}</b></div>{group.rows.map((row) => <EventRow row={row} key={rowKey(row)} onOpen={setSelected}/>)}</section>) : <p className="fynvo-ui-state">No upcoming payments in the next 90 days.</p>}</>}
    {view === 'attention' && <><section className="fynvo-payments-v1240-attention-intro"><span>!</span><div><strong>{attentionCount || 0} payment{attentionCount === 1 ? '' : 's'} need attention</strong><p>Take action to keep your plan on track.</p></div></section>{attentionRows.length ? <><section className="fynvo-payments-v1240-group"><div className="fynvo-payments-v1240-group-head"><strong>Overdue</strong><b>{money(attentionRows.filter((row) => row.status === 'overdue').reduce((sum, row) => sum + amount(row), 0))}</b></div>{attentionRows.filter((row) => row.status === 'overdue').map((row) => <EventRow row={row} key={rowKey(row)} onOpen={setSelected}/>)}</section><section className="fynvo-payments-v1240-group"><div className="fynvo-payments-v1240-group-head"><strong>Action required</strong><b>{money(attentionRows.filter((row) => row.status !== 'overdue').reduce((sum, row) => sum + amount(row), 0))}</b></div>{attentionRows.filter((row) => row.status !== 'overdue').map((row) => <EventRow row={row} key={rowKey(row)} onOpen={setSelected}/>)}</section></> : <p className="fynvo-ui-state">All good. No payments need your attention right now.</p>}<aside className="fynvo-payments-v1240-keep-track"><strong>Keep on track</strong><p>Updating a payment method or marking a payment as paid helps keep your plan accurate.</p></aside>{resolvedRows.length > 0 && <section className="fynvo-payments-v1240-resolved"><div className="fynvo-payments-v1240-section-head"><h2>Resolved recently</h2><button type="button" onClick={() => setView('timeline')}>View all</button></div>{resolvedRows.map((row) => <EventRow row={row} resolved key={rowKey(row)} onOpen={setSelected}/>)}</section>}</>}
    {view === 'timeline' && <><div className="fynvo-payments-v1240-section-head"><h2>Payment timeline</h2><span>Chronological view</span></div>{[...activeRows, ...resolvedRows].sort((a, b) => String(a.expected_date || a.due_date || a.actual_date || '').localeCompare(String(b.expected_date || b.due_date || b.actual_date || ''))).map((row) => <EventRow row={row} resolved={TERMINAL.has(row.status)} key={rowKey(row)} onOpen={setSelected}/>)}{!activeRows.length && !resolvedRows.length && <p className="fynvo-ui-state">No payments to show in the timeline.</p>}</>}
    {view === 'manage' && <section className="fynvo-payments-v1240-manage"><div className="fynvo-payments-v1240-manage-intro"><strong>Manage your payments</strong><p>Configure the rules and records that create your household payment timeline.</p></div><button type="button" onClick={onQuickAdd}><span>＋</span><div><strong>Add payment</strong><small>Create a bill or recurring payment.</small></div>›</button><button type="button" onClick={() => onNavigate('Recurring Expenses')}><span>↻</span><div><strong>Recurring schedules</strong><small>Manage rules that create future payments.</small></div>›</button><button type="button" onClick={() => onNavigate('Bills')}><span>▤</span><div><strong>Bills and one-off obligations</strong><small>View and manage bill-backed payments.</small></div>›</button></section>}
  </>}<button type="button" className="fynvo-payments-v1240-add" onClick={onQuickAdd}>＋ Add payment</button><ActionSheet row={selected} onClose={() => setSelected(null)} onAction={performAction}/><ChangeDateDialog row={dateEditor} onClose={() => setDateEditor(null)} onSaved={async () => { setDateEditor(null); await Promise.allSettled([load(), onRefreshSupporting?.()]); }} /></section>;
}
