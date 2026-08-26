import { useEffect, useMemo, useState } from 'react';

import { apiRequest } from './apiClient.js';
import {
  PAYMENT_DATE_RANGES,
  PAYMENT_METHOD_LABELS,
  PAYMENT_STATUS_LABELS,
  buildPaymentCentreQuery,
  defaultPaymentCentreFilters,
  groupPayments,
  paymentNeedsAction,
  paymentPrimaryAction,
  paymentSourceLabel,
  paymentStatusLabel,
} from './paymentCentreModel.js';
import './payment-centre-v112.css';

const finiteNumber = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};
const money = (value) => {
  const number = finiteNumber(value);
  return number === null ? 'Not set' : new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(number);
};
const dateLabel = (value) => value ? new Intl.DateTimeFormat('en-AU', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(`${String(value).slice(0, 10)}T00:00:00`)) : 'No date';
const todayInput = () => new Date().toISOString().slice(0, 10);

function StatusBadge({ status }) {
  return <span className={`payment-centre-status status-${status}`}>{paymentStatusLabel(status)}</span>;
}

function Summary({ summary }) {
  const items = [
    ['total_scheduled', 'Total scheduled'], ['overdue', 'Overdue'], ['requires_payment', 'Requires payment'],
    ['expected_automatically', 'Expected automatically'], ['awaiting_confirmation', 'Awaiting confirmation'],
    ['upcoming', 'Upcoming'], ['paid', 'Paid'],
  ];
  return <div className="payment-centre-summary" aria-label="Payment summary">
    {items.map(([key, label]) => <article key={key} className={`payment-centre-summary-card summary-${key}`}><small>{label}</small><strong>{money(summary?.[key]?.amount)}</strong><span>{summary?.[key]?.count || 0} item{summary?.[key]?.count === 1 ? '' : 's'}</span></article>)}
  </div>;
}

function Filters({ filters, setFilters, data, onClear, mobileOpen, setMobileOpen }) {
  const controls = <>
    <label><span>Search</span><input aria-label="Search payments" value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} placeholder="Name, merchant, category, account or card"/></label>
    <label><span>Date range</span><select value={filters.dateRange} onChange={(event) => setFilters({ ...filters, dateRange: event.target.value })}>{PAYMENT_DATE_RANGES.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
    {filters.dateRange === 'custom' && <><label><span>From</span><input type="date" value={filters.dateFrom} onChange={(event) => setFilters({ ...filters, dateFrom: event.target.value })}/></label><label><span>To</span><input type="date" value={filters.dateTo} onChange={(event) => setFilters({ ...filters, dateTo: event.target.value })}/></label></>}
    <label><span>Status</span><select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}><option value="">All statuses</option>{Object.entries(PAYMENT_STATUS_LABELS).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
    <label><span>Source</span><select value={filters.source} onChange={(event) => setFilters({ ...filters, source: event.target.value })}><option value="">Bills and recurring payments</option><option value="bill">Bills</option><option value="scheduled_payment">Recurring / Scheduled Payments</option></select></label>
    <label><span>Category</span><select value={filters.categoryId} onChange={(event) => setFilters({ ...filters, categoryId: event.target.value })}><option value="">All categories</option>{(data.categories || []).filter((row) => row.is_active !== false).map((row) => <option value={row.id} key={row.id}>{row.path || row.name}</option>)}</select></label>
    <label><span>Payment Method</span><select value={filters.paymentMethod} onChange={(event) => setFilters({ ...filters, paymentMethod: event.target.value })}><option value="">All methods</option>{Object.entries(PAYMENT_METHOD_LABELS).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
    <label><span>Payment Handling</span><select value={filters.paymentHandling} onChange={(event) => setFilters({ ...filters, paymentHandling: event.target.value })}><option value="">Automatic and manual</option><option value="automatic">Paid automatically</option><option value="manual">I pay this manually</option></select></label>
    <label><span>Account</span><select value={filters.accountId} onChange={(event) => setFilters({ ...filters, accountId: event.target.value })}><option value="">All Accounts</option>{(data.accounts || []).filter((row) => row.is_active !== false && !row.archived_at).map((row) => <option value={row.id} key={row.id}>{row.name}</option>)}</select></label>
    <label><span>Card</span><select value={filters.cardId} onChange={(event) => setFilters({ ...filters, cardId: event.target.value })}><option value="">All Cards</option>{(data.cards || []).filter((row) => row.is_active !== false).map((row) => <option value={row.id} key={row.id}>{row.display_name}</option>)}</select></label>
    <label className="payment-centre-check"><input type="checkbox" checked={filters.requiresAction} onChange={(event) => setFilters({ ...filters, requiresAction: event.target.checked })}/><span>Requires action only</span></label>
    <button type="button" className="payment-centre-clear" onClick={onClear}>Clear Filters</button>
  </>;
  return <>
    <button type="button" className="payment-centre-mobile-filter-button" onClick={() => setMobileOpen(true)}>Filters</button>
    <div className="payment-centre-filters desktop-filters">{controls}</div>
    {mobileOpen && <div className="payment-centre-filter-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setMobileOpen(false)}><section className="payment-centre-filter-sheet" role="dialog" aria-modal="true" aria-label="Payment filters"><div className="payment-centre-sheet-head"><h2>Filters</h2><button type="button" onClick={() => setMobileOpen(false)} aria-label="Close filters">×</button></div><div className="payment-centre-filters mobile-filters">{controls}</div><button className="primary payment-centre-apply" type="button" onClick={() => setMobileOpen(false)}>Apply Filters</button></section></div>}
  </>;
}

function PaymentRow({ row, onOpen, onAction }) {
  const amount = row.status === 'paid' && row.actual_amount != null ? row.actual_amount : row.expected_amount ?? row.amount;
  const primary = paymentPrimaryAction(row);
  const actionLabel = primary === 'mark_paid' ? 'Mark as paid' : primary === 'review' ? 'Review' : 'View';
  return <article className={`payment-centre-row ${paymentNeedsAction(row) ? 'needs-action' : ''}`}>
    <button type="button" className="payment-centre-row-main" onClick={() => onOpen(row)}>
      <span className="payment-centre-date"><small>Due</small><strong>{dateLabel(row.expected_date || row.due_date)}</strong>{row.days_overdue ? <em>Overdue by {row.days_overdue} day{row.days_overdue === 1 ? '' : 's'}</em> : null}</span>
      <span className="payment-centre-name"><strong>{row.name}</strong><small>{row.category || 'Uncategorised'} · {paymentSourceLabel(row)}</small></span>
      <span className="payment-centre-amount"><strong>{money(amount)}</strong>{row.actual_amount != null && row.expected_amount != null && <small>Expected {money(row.expected_amount)}</small>}</span>
      <span className="payment-centre-method"><strong>{row.payment_method_label || PAYMENT_METHOD_LABELS[row.payment_method] || 'Not Set'}</strong><small>{row.card_name || row.account_name || (row.payment_handling === 'automatic' ? 'Automatic' : 'Manual')}</small></span>
      <StatusBadge status={row.status}/>
    </button>
    <button type="button" className="payment-centre-row-action" onClick={() => onAction(row, primary)}>{actionLabel}</button>
  </article>;
}

function DetailModal({ detail, onClose, onMarkPaid, onSkip, onReview, onViewTransaction }) {
  if (!detail) return null;
  const expected = detail.expected_amount ?? detail.amount;
  const canReviewMatch = detail.source_type === 'scheduled_payment' && (detail.match_review_available || detail.status === 'auto_payment_unconfirmed');
  return <div className="payment-centre-modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="payment-centre-detail" role="dialog" aria-modal="true" aria-label={`${detail.name} payment detail`}><header><div><StatusBadge status={detail.status}/><h2>{detail.name}</h2><p>{paymentSourceLabel(detail)}</p></div><button type="button" onClick={onClose} aria-label="Close payment detail">×</button></header><div className="payment-centre-detail-body">
    <div className="payment-centre-detail-grid"><div><span>Expected</span><strong>{money(expected)}</strong></div><div><span>Actual</span><strong>{detail.actual_amount != null ? money(detail.actual_amount) : 'Not confirmed'}</strong></div><div><span>Difference</span><strong>{detail.difference != null ? `${Number(detail.difference) > 0 ? '+' : ''}${money(detail.difference)}` : 'Not available'}</strong></div><div><span>Due date</span><strong>{dateLabel(detail.expected_date || detail.due_date)}</strong></div><div><span>Paid date</span><strong>{detail.actual_date ? dateLabel(detail.actual_date) : 'Not paid'}</strong></div><div><span>Category</span><strong>{detail.category || 'Not set'}</strong></div><div><span>Expense Type</span><strong>{detail.expense_type || 'Not set'}</strong></div><div><span>Payee / Merchant</span><strong>{detail.payee_merchant || detail.provider || 'Not set'}</strong></div><div><span>Payment Handling</span><strong>{detail.payment_handling === 'automatic' ? 'Paid automatically' : 'I pay this manually'}</strong></div><div><span>Payment Method</span><strong>{detail.payment_method_label || PAYMENT_METHOD_LABELS[detail.payment_method] || 'Not Set'}</strong></div><div><span>Account</span><strong>{detail.account_name || detail.linked_account_name || 'Not set'}</strong></div><div><span>Card</span><strong>{detail.card_name || 'Not set'}</strong></div></div>
    {detail.card_name && detail.linked_account_name && <p className="payment-centre-linked-account">Linked to account: <strong>{detail.linked_account_name}</strong></p>}
    {detail.source_type === 'bill' && detail.status === 'auto_payment_unconfirmed' && <div className="payment-centre-evidence"><span>Transaction confirmation</span><strong>No automatic Bill transaction link has been confirmed.</strong><small>Use Transactions to inspect imported evidence. Fynvo does not fabricate a Transaction or create a separate Bill reconciliation model.</small><button type="button" onClick={() => onViewTransaction(null)}>Review Transactions</button></div>}
    {detail.notes && <div className="payment-centre-note"><span>Notes</span><p>{detail.notes}</p></div>}
    {detail.matched_transaction && <div className="payment-centre-evidence"><span>Matched transaction</span><strong>{detail.matched_transaction.merchant || detail.matched_transaction.description}</strong><small>{dateLabel(detail.matched_transaction.date)} · {money(detail.matched_transaction.amount)}</small><button type="button" onClick={() => onViewTransaction(detail.matched_transaction)}>View Transaction</button></div>}
    {(detail.history || []).length > 0 && <div className="payment-centre-history"><h3>Status history</h3>{detail.history.map((item, index) => <div key={`${item.created_at}-${index}`}><span>{dateLabel(item.created_at)}</span><strong>{paymentStatusLabel(item.to_status)}</strong>{item.note && <small>{item.note}</small>}</div>)}</div>}
  </div><footer>{detail.source_type === 'scheduled_payment' && !['paid', 'skipped', 'cancelled'].includes(detail.status) && <button type="button" onClick={() => onSkip(detail)}>Skip payment</button>}{canReviewMatch ? <button type="button" onClick={() => onReview(detail)}>Review Match</button> : null}{(detail.payment_handling === 'manual' || ['due', 'due_today', 'overdue'].includes(detail.status)) && !['paid', 'skipped', 'cancelled'].includes(detail.status) && <button type="button" className="primary" onClick={() => onMarkPaid(detail)}>Mark as paid</button>}<button type="button" onClick={onClose}>Close</button></footer></section></div>;
}

function MarkPaidModal({ payment, onClose, onSaved }) {
  const [form, setForm] = useState({ paid_date: todayInput(), paid_amount: payment?.expected_amount || payment?.amount || '', note: '' });
  const [saving, setSaving] = useState(false); const [error, setError] = useState('');
  if (!payment) return null;
  const submit = async (event) => {
    event.preventDefault(); setSaving(true); setError('');
    try {
      const isBill = payment.source_type === 'bill';
      const path = isBill ? `/bills/${payment.id}/mark-paid` : `/scheduled-payments/${payment.id}/mark-paid`;
      const payload = isBill
        ? { paid_date: form.paid_date, paid_amount: form.paid_amount, note: form.note, version: payment.version }
        : { actual_date: form.paid_date, actual_amount: form.paid_amount, note: form.note };
      await apiRequest(path, { method: 'POST', body: JSON.stringify(payload) });
      await onSaved();
    } catch (requestError) { setError(requestError.message || 'Could not mark this payment paid.'); } finally { setSaving(false); }
  };
  return <div className="payment-centre-modal-backdrop"><form className="payment-centre-mark-paid" onSubmit={submit}><header><div><h2>Mark as paid</h2><p>{payment.name} · expected {money(payment.expected_amount ?? payment.amount)}</p></div><button type="button" onClick={onClose} aria-label="Close mark paid">×</button></header><div className="payment-centre-form"><label><span>Actual date</span><input required type="date" value={form.paid_date} onChange={(event) => setForm({ ...form, paid_date: event.target.value })}/></label><label><span>Actual amount</span><input required inputMode="decimal" value={form.paid_amount} onChange={(event) => setForm({ ...form, paid_amount: event.target.value })}/></label><label><span>Note (optional)</span><textarea rows="3" value={form.note} onChange={(event) => setForm({ ...form, note: event.target.value })}/></label>{error && <p className="error">{error}</p>}<p className="muted">This records payment evidence. It does not invent a bank Transaction.</p></div><footer><button type="button" onClick={onClose}>Cancel</button><button className="primary" disabled={saving}>{saving ? 'Saving…' : 'Mark as paid'}</button></footer></form></div>;
}

export default function PaymentCentreV112({ data, onNavigate, onRefreshSupporting }) {
  const [filters, setFilters] = useState(defaultPaymentCentreFilters);
  const [result, setResult] = useState(null); const [loading, setLoading] = useState(true); const [error, setError] = useState('');
  const [detail, setDetail] = useState(null); const [markingPaid, setMarkingPaid] = useState(null); const [mobileFilters, setMobileFilters] = useState(false);
  const query = useMemo(() => buildPaymentCentreQuery(filters), [filters]);
  const load = async () => { setLoading(true); setError(''); try { setResult(await apiRequest(query)); } catch (requestError) { setError(requestError.message || 'Could not load the Payment Centre.'); } finally { setLoading(false); } };
  useEffect(() => { const timer = window.setTimeout(load, filters.search ? 180 : 0); return () => window.clearTimeout(timer); }, [query]);
  const open = async (row) => { try { setDetail(await apiRequest(`/payment-centre/${row.source_type}/${row.id}`)); } catch (requestError) { setError(requestError.message || 'Could not load payment detail.'); } };
  const refreshed = async () => { setMarkingPaid(null); setDetail(null); await Promise.allSettled([load(), onRefreshSupporting?.()]); };
  const action = (row, kind) => {
    if (kind === 'mark_paid') setMarkingPaid(row);
    else if (kind === 'review' && row.source_type === 'scheduled_payment') onNavigate('Review Queue');
    else if (kind === 'review') onNavigate('Transactions');
    else open(row);
  };
  const skip = async (row) => { try { if (row.source_type !== 'scheduled_payment') return; await apiRequest(`/scheduled-payments/${row.id}/skip`, { method: 'POST', body: JSON.stringify({ note: 'Skipped from Payment Centre' }) }); await refreshed(); } catch (requestError) { setError(requestError.message || 'Could not skip this payment.'); } };
  const groups = groupPayments(result?.rows || []);
  return <section className="payment-centre-page"><div className="payment-centre-head"><div><h1>Payment Centre</h1><p>What needs to be paid, what will be paid automatically, and what needs review.</p></div><button type="button" className="primary ghost" onClick={() => onNavigate('Bills')}>+ Add Bill</button></div>
    {result && !error && <Summary summary={result.summary}/>} 
    <Filters filters={filters} setFilters={setFilters} data={data} onClear={() => setFilters(defaultPaymentCentreFilters())} mobileOpen={mobileFilters} setMobileOpen={setMobileFilters}/>
    {loading && !result && <div className="payment-centre-state" role="status"><strong>Loading payments…</strong><p>Getting the latest household obligations.</p></div>}
    {error && <div className="payment-centre-state error-state" role="alert"><strong>Payment Centre could not load</strong><p>{error}</p><button type="button" onClick={load}>Retry</button></div>}
    {!loading && !error && result && result.rows.length === 0 && <div className="payment-centre-state"><strong>Nothing matches these filters</strong><p>No payment obligations were returned for this Date Range and filter combination.</p><button type="button" onClick={() => setFilters(defaultPaymentCentreFilters())}>Clear Filters</button></div>}
    {!error && result && result.rows.length > 0 && <div className={`payment-centre-groups ${loading ? 'refreshing' : ''}`}>{groups.map(([label, rows]) => <section className="payment-centre-group" key={label}><div className="payment-centre-group-head"><h2>{label}</h2><span>{rows.length}</span></div>{rows.map((row) => <PaymentRow key={`${row.source_type}-${row.id}`} row={row} onOpen={open} onAction={action}/>)}</section>)}</div>}
    <DetailModal detail={detail} onClose={() => setDetail(null)} onMarkPaid={(row) => { setDetail(null); setMarkingPaid(row); }} onSkip={skip} onReview={() => { setDetail(null); onNavigate('Review Queue'); }} onViewTransaction={() => { setDetail(null); onNavigate('Transactions'); }}/>
    <MarkPaidModal payment={markingPaid} onClose={() => setMarkingPaid(null)} onSaved={refreshed}/>
  </section>;
}
