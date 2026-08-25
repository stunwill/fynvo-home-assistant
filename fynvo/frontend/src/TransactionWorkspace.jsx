import { useEffect, useMemo, useState } from 'react';
import { apiRequest } from './apiClient.js';

const DEFAULT_FILTERS = { range: '30', account: 'all', category: 'all', type: 'all', reconciliation: 'all', source: 'all' };
const DAY_MS = 86400000;
const iso = (value) => String(value || '').slice(0, 10);
const midnight = (value = new Date()) => { const date = value instanceof Date ? value : new Date(`${iso(value)}T00:00:00`); return new Date(date.getFullYear(), date.getMonth(), date.getDate()); };
const dayDiff = (value, reference = new Date()) => Math.round((midnight(value) - midnight(reference)) / DAY_MS);
const displayCategory = (row) => row.category || 'Uncategorised';
const reconciliationLabel = (value) => ({ matched: 'Matched', ignored: 'Ignored / Not applicable', duplicate: 'Duplicate', unmatched: 'Unmatched' })[value] || 'Unmatched';
const confidenceLabel = (value) => ({ high: 'High confidence', medium: 'Possible match', low: 'Needs review' })[value] || 'Needs review';

function inDateRange(row, range, reference = new Date()) {
  if (range === 'all') return true;
  const date = midnight(row.date);
  const today = midnight(reference);
  if (range === 'month') return date.getFullYear() === today.getFullYear() && date.getMonth() === today.getMonth();
  if (range === 'last-month') {
    const target = new Date(today.getFullYear(), today.getMonth() - 1, 1);
    return date.getFullYear() === target.getFullYear() && date.getMonth() === target.getMonth();
  }
  if (range === 'year') return date.getFullYear() === today.getFullYear();
  const days = Number(range);
  const delta = dayDiff(row.date, today);
  return Number.isFinite(days) && delta <= 0 && delta >= -days;
}

function SummaryCard({ label, value, hint }) {
  return <article className="transaction-summary-card"><small>{label}</small><strong>{value}</strong>{hint && <span>{hint}</span>}</article>;
}

function FilterBar({ filters, setFilters, accounts, categories, search, setSearch }) {
  const set = (key, value) => setFilters((current) => ({ ...current, [key]: value }));
  return <div className="transaction-filters">
    <input aria-label="Search transactions" placeholder="Search description, merchant, account or category…" value={search} onChange={(event) => setSearch(event.target.value)}/>
    <select aria-label="Transaction date range" value={filters.range} onChange={(event) => set('range', event.target.value)}><option value="7">Last 7 days</option><option value="30">Last 30 days</option><option value="month">This month</option><option value="last-month">Last month</option><option value="90">Last 90 days</option><option value="year">This year</option><option value="all">All loaded</option></select>
    <select aria-label="Account filter" value={filters.account} onChange={(event) => set('account', event.target.value)}><option value="all">All accounts</option>{accounts.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select>
    <select aria-label="Category filter" value={filters.category} onChange={(event) => set('category', event.target.value)}><option value="all">All categories</option><option value="uncategorised">Uncategorised</option>{categories.filter((row) => row.is_active !== false).map((row) => <option key={row.id} value={row.id}>{row.path || row.name}</option>)}</select>
    <select aria-label="Transaction type filter" value={filters.type} onChange={(event) => set('type', event.target.value)}><option value="all">Money in & out</option><option value="income">Money in</option><option value="expense">Money out</option><option value="transfer">Transfers</option></select>
    <select aria-label="Reconciliation filter" value={filters.reconciliation} onChange={(event) => set('reconciliation', event.target.value)}><option value="all">All reconciliation</option><option value="matched">Matched</option><option value="unmatched">Unmatched</option><option value="ignored">Ignored</option></select>
    <select aria-label="Transaction source filter" value={filters.source} onChange={(event) => set('source', event.target.value)}><option value="all">All sources</option><option value="manual">Manual</option><option value="imported">Imported</option></select>
    <button type="button" disabled={JSON.stringify(filters) === JSON.stringify(DEFAULT_FILTERS) && !search} onClick={() => { setFilters(DEFAULT_FILTERS); setSearch(''); }}>Clear filters</button>
  </div>;
}

function TransactionDetail({ row, categories, candidates, money, dateLabel, onClose, onChanged }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ description: row.description || '', merchant: row.merchant || '', notes: row.notes || '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const matches = candidates.filter((candidate) => Number(candidate.transaction_id) === Number(row.id));
  const saveMetadata = async () => {
    setBusy(true); setError('');
    try {
      await apiRequest(`/transactions/${row.id}`, { method: 'PUT', body: JSON.stringify(form) });
      setEditing(false); await onChanged();
    } catch (requestError) { setError(requestError?.message || 'Could not update this Transaction.'); }
    finally { setBusy(false); }
  };
  const categoryChanged = async (categoryId) => {
    setBusy(true); setError('');
    try {
      await apiRequest(`/payments/transactions/${row.id}/category`, { method: 'PUT', body: JSON.stringify({ category_id: categoryId ? Number(categoryId) : null }) });
      await onChanged();
    } catch (requestError) { setError(requestError?.message || 'Could not update the Category.'); }
    finally { setBusy(false); }
  };
  const confirm = async (candidate) => {
    setBusy(true); setError('');
    try {
      await apiRequest(`/scheduled-payments/${candidate.scheduled_payment_id}/match`, { method: 'POST', body: JSON.stringify({ transaction_id: row.id, confidence: candidate.confidence }) });
      await onChanged();
    } catch (requestError) { setError(requestError?.message || 'Could not confirm this match.'); }
    finally { setBusy(false); }
  };
  const reject = async (candidate) => {
    setBusy(true); setError('');
    try {
      await apiRequest(`/scheduled-payments/${candidate.scheduled_payment_id}/reject-match`, { method: 'POST', body: JSON.stringify({ transaction_id: row.id }) });
      await onChanged();
    } catch (requestError) { setError(requestError?.message || 'Could not reject this match.'); }
    finally { setBusy(false); }
  };
  const unmatch = async () => {
    setBusy(true); setError('');
    try {
      await apiRequest(`/scheduled-payments/${row.matched_id}/unmatch`, { method: 'POST' });
      await onChanged();
    } catch (requestError) { setError(requestError?.message || 'Could not remove this match.'); }
    finally { setBusy(false); }
  };

  return <div className="modal-backdrop"><section className="modal transaction-detail-modal" role="dialog" aria-modal="true" aria-label={`Transaction ${row.description}`}><div className="panel-head"><div><h2>{row.merchant || row.description}</h2><p>{dateLabel(row.date)} · {row.account_name || 'Account not available'}</p></div><button type="button" aria-label="Close" onClick={onClose}>×</button></div>
    {error && <p className="error">{error}</p>}
    <div className="transaction-detail-grid"><div><span>Amount</span><strong>{money(row.amount)}</strong></div><div><span>Type</span><strong>{row.transaction_type}</strong></div><div><span>Reconciliation</span><strong>{reconciliationLabel(row.reconciliation_status)}</strong></div><div><span>Source</span><strong>{row.source || 'manual'}</strong></div></div>
    <label className="field"><span>Category</span><select disabled={busy} value={row.category_id || ''} onChange={(event) => categoryChanged(event.target.value)}><option value="">Uncategorised</option>{categories.filter((category) => category.is_active !== false || Number(category.id) === Number(row.category_id)).map((category) => <option key={category.id} value={category.id}>{category.path || category.name}{category.is_active === false ? ' (Archived)' : ''}</option>)}</select></label>
    {editing ? <div className="form-grid"><label className="field wide"><span>Description</span><input value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })}/></label><label className="field"><span>Merchant / Payee</span><input value={form.merchant} onChange={(event) => setForm({ ...form, merchant: event.target.value })}/></label><label className="field wide"><span>Notes</span><textarea rows="3" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })}/></label><div className="modal-actions"><button type="button" onClick={() => setEditing(false)}>Cancel</button><button type="button" className="primary" disabled={busy} onClick={saveMetadata}>Save Transaction</button></div></div> : <div className="transaction-description"><p><strong>Description:</strong> {row.description}</p>{row.raw_description && row.raw_description !== row.description && <p><strong>Original import:</strong> {row.raw_description}</p>}{row.notes && <p><strong>Notes:</strong> {row.notes}</p>}<button type="button" onClick={() => setEditing(true)}>Edit details</button></div>}
    {row.reconciliation_status === 'matched' && row.matched_id ? <section className="transaction-match-section"><div className="panel-head compact"><h3>Matched Scheduled Payment</h3><span className="transaction-match-badge high">Matched</span></div><p>This Transaction is linked to Scheduled Payment #{row.matched_id}.</p><button type="button" disabled={busy} onClick={unmatch}>Remove match</button></section> : <section className="transaction-match-section"><div className="panel-head compact"><h3>Possible payment matches</h3><small>{matches.length ? `${matches.length} candidate${matches.length === 1 ? '' : 's'}` : 'No suitable candidates'}</small></div>{matches.map((candidate) => <article className="transaction-match-candidate" key={candidate.scheduled_payment_id}><div><strong>{candidate.recurring_name}</strong><span>{dateLabel(candidate.expected_date)} · Expected {money(candidate.expected_amount)} · Actual {money(candidate.actual_amount)}</span><span className={`transaction-match-badge ${candidate.confidence}`}>{confidenceLabel(candidate.confidence)}</span>{candidate.automatic_match_eligible && <span className="transaction-auto-eligible">Strong, unambiguous evidence</span>}<ul>{(candidate.evidence || []).map((evidence) => <li key={evidence}>{evidence}</li>)}</ul></div><div className="transaction-match-actions"><button type="button" disabled={busy} onClick={() => reject(candidate)}>Not this payment</button><button type="button" className="primary" disabled={busy} onClick={() => confirm(candidate)}>Confirm match</button></div></article>)}</section>}
  </section></div>;
}

export default function TransactionWorkspace({ accounts = [], categories = [], money, dateLabel }) {
  const [rows, setRows] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [loadState, setLoadState] = useState('loading');
  const [candidateState, setCandidateState] = useState('loading');
  const [error, setError] = useState('');
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState({ key: 'date', direction: 'desc' });
  const [selectedId, setSelectedId] = useState(null);
  const [revision, setRevision] = useState(0);

  const load = async () => {
    setLoadState('loading'); setError('');
    try {
      const transactions = await apiRequest('/payments/transactions?limit=2000');
      setRows(Array.isArray(transactions) ? transactions : []);
      setLoadState('loaded');
    } catch (requestError) { setError(requestError?.message || 'Could not load Transactions.'); setLoadState('error'); }
  };
  const loadCandidates = async () => {
    setCandidateState('loading');
    try { const result = await apiRequest('/payments/match-candidates?date_tolerance_days=7'); setCandidates(Array.isArray(result) ? result : []); setCandidateState('loaded'); }
    catch { setCandidates([]); setCandidateState('error'); }
  };
  useEffect(() => { let cancelled = false; Promise.allSettled([load(), loadCandidates()]).then(() => { if (cancelled) return; }); return () => { cancelled = true; }; }, [revision]);

  const categoryById = useMemo(() => new Map(categories.map((row) => [Number(row.id), row])), [categories]);
  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return rows.filter((row) => {
      if (!inDateRange(row, filters.range)) return false;
      if (filters.account !== 'all' && Number(row.account_id) !== Number(filters.account)) return false;
      if (filters.category === 'uncategorised' && row.category_id) return false;
      if (filters.category !== 'all' && filters.category !== 'uncategorised' && Number(row.category_id) !== Number(filters.category)) return false;
      if (filters.type !== 'all' && row.transaction_type !== filters.type) return false;
      if (filters.reconciliation !== 'all' && row.reconciliation_status !== filters.reconciliation) return false;
      if (filters.source === 'manual' && row.source !== 'manual') return false;
      if (filters.source === 'imported' && row.source === 'manual') return false;
      if (query && !`${row.description} ${row.merchant || ''} ${row.account_name || ''} ${row.category || ''}`.toLowerCase().includes(query)) return false;
      return true;
    }).sort((left, right) => {
      let result = 0;
      if (sort.key === 'amount') result = Math.abs(Number(left.amount || 0)) - Math.abs(Number(right.amount || 0));
      else if (sort.key === 'merchant') result = String(left.merchant || left.description).localeCompare(String(right.merchant || right.description));
      else if (sort.key === 'category') result = displayCategory(left).localeCompare(displayCategory(right));
      else if (sort.key === 'account') result = String(left.account_name || '').localeCompare(String(right.account_name || ''));
      else result = iso(left.date).localeCompare(iso(right.date));
      return result * (sort.direction === 'asc' ? 1 : -1);
    });
  }, [rows, filters, search, sort]);
  const nonTransfers = filtered.filter((row) => row.transaction_type !== 'transfer');
  const moneyIn = nonTransfers.filter((row) => row.transaction_type === 'income').reduce((sum, row) => sum + Math.abs(Number(row.amount || 0)), 0);
  const moneyOut = nonTransfers.filter((row) => row.transaction_type === 'expense').reduce((sum, row) => sum + Math.abs(Number(row.amount || 0)), 0);
  const unmatched = filtered.filter((row) => row.reconciliation_status === 'unmatched').length;
  const uncategorised = filtered.filter((row) => !row.category_id && !row.category).length;
  const selected = rows.find((row) => Number(row.id) === Number(selectedId));
  const refresh = async () => { await Promise.allSettled([load(), loadCandidates()]); };
  const toggleSort = (key) => setSort((current) => ({ key, direction: current.key === key && current.direction === 'desc' ? 'asc' : 'desc' }));

  return <section className="transaction-workspace"><div className="panel-head transaction-workspace-head"><div><h2>Transactions</h2><p>Review actual money movements, categorise them and reconcile expected payments.</p></div><span>{filtered.length} shown · {rows.length} loaded</span></div>
    <FilterBar filters={filters} setFilters={setFilters} accounts={accounts} categories={categories} search={search} setSearch={setSearch}/>
    {loadState === 'loading' && !rows.length ? <div className="panel transaction-load-state" role="status">Loading Transactions…</div> : loadState === 'error' && !rows.length ? <div className="panel transaction-load-state"><strong>Could not load Transactions</strong><p>{error}</p><button className="primary" type="button" onClick={() => setRevision((value) => value + 1)}>Retry</button></div> : <>
      {error && <p className="error banner">{error}</p>}
      {candidateState === 'error' && <p className="notice transaction-reconciliation-warning">Transactions loaded, but payment-match candidates could not be refreshed. Transaction data remains available.</p>}
      <div className="transaction-summary-grid"><SummaryCard label="Money In" value={money(moneyIn)}/><SummaryCard label="Money Out" value={money(moneyOut)}/><SummaryCard label="Net Movement" value={money(moneyIn - moneyOut)} hint="Transfers excluded"/><SummaryCard label="Transactions" value={filtered.length}/><SummaryCard label="Uncategorised" value={uncategorised}/><SummaryCard label="Needs Review" value={unmatched}/></div>
      <div className="panel transaction-table-panel">{filtered.length ? <div className="transaction-table"><div className="transaction-row transaction-head"><button type="button" onClick={() => toggleSort('date')}>Date</button><button type="button" onClick={() => toggleSort('merchant')}>What happened</button><button type="button" onClick={() => toggleSort('account')}>Account</button><button type="button" onClick={() => toggleSort('category')}>Category</button><button type="button" onClick={() => toggleSort('amount')}>Amount</button><span>Reconciliation</span></div>{filtered.map((row) => <button type="button" className="transaction-row transaction-data-row" key={row.id} onClick={() => setSelectedId(row.id)}><span>{dateLabel(row.date)}</span><span><strong>{row.merchant || row.description}</strong>{row.merchant && <small>{row.description}</small>}<small>{row.source === 'manual' ? 'Manual' : 'Imported'}</small></span><span>{row.account_name || '—'}</span><span>{categoryById.get(Number(row.category_id))?.path || displayCategory(row)}</span><strong className={row.transaction_type === 'expense' ? 'negative' : row.transaction_type === 'income' ? 'positive' : ''}>{money(Math.abs(Number(row.amount || 0)))}</strong><span><i className={`transaction-status status-${row.reconciliation_status || 'unmatched'}`}>{reconciliationLabel(row.reconciliation_status)}</i></span></button>)}</div> : <div className="empty"><strong>No Transactions match these filters</strong><p>Clear filters or choose another date range.</p></div>}</div>
    </>}
    {selected && <TransactionDetail row={selected} categories={categories} candidates={candidates} money={money} dateLabel={dateLabel} onClose={() => setSelectedId(null)} onChanged={refresh}/>} 
  </section>;
}
