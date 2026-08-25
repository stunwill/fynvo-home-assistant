import { useEffect, useMemo, useState } from 'react';
import RecurringExpensesPageV151 from './RecurringExpensesPageV151.jsx';
import { apiRequest } from './apiClient.js';

const api = (path, options = {}) => fetch(`api${path}`, {
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  ...options,
});
const ATTENTION_STATUSES = new Set(['overdue', 'due', 'auto_payment_unconfirmed']);

export function CategoriesPageV0174({ rangeDays, onEdit, money }) {
  const [rows, setRows] = useState([]);
  const [expanded, setExpanded] = useState(() => new Set());
  const [selected, setSelected] = useState(null);
  const [entries, setEntries] = useState([]);
  const [loadingEntries, setLoadingEntries] = useState(false);
  const [health, setHealth] = useState(null);
  const [checkingHealth, setCheckingHealth] = useState(false);
  const [revision, setRevision] = useState(0);
  const [merge, setMerge] = useState(null);

  const loadHealth = async () => {
    setCheckingHealth(true);
    const response = await api('/v018/categories/health');
    setHealth(response.ok ? await response.json() : null);
    setCheckingHealth(false);
  };

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api(`/corrective-v0174/categories/summary?range_days=${rangeDays}`).then(async (response) => response.ok ? response.json() : []),
      api('/v018/categories/health').then(async (response) => response.ok ? response.json() : null),
    ]).then(([summary, integrity]) => {
      if (cancelled) return;
      setRows(Array.isArray(summary) ? summary : []);
      setHealth(integrity);
    });
    return () => { cancelled = true; };
  }, [rangeDays, revision]);

  const byParent = useMemo(() => {
    const map = new Map();
    for (const row of rows) {
      const parent = row.parent_id == null ? null : Number(row.parent_id);
      if (!map.has(parent)) map.set(parent, []);
      map.get(parent).push(row);
    }
    for (const list of map.values()) list.sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')));
    return map;
  }, [rows]);

  const parents = byParent.get(null) || [];
  const activeRows = rows.filter((row) => row.is_active !== false);
  const toggle = (id) => setExpanded((current) => { const next = new Set(current); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  const open = async (row) => {
    setSelected(row);
    setLoadingEntries(true);
    const response = await api(`/corrective-v0174/categories/${row.id}/entries?range_days=${rangeDays}`);
    setEntries(response.ok ? await response.json() : []);
    setLoadingEntries(false);
  };
  const beginMerge = (source = null) => setMerge({ source_id: source?.id ? String(source.id) : '', destination_id: '', preview: null, error: '', saving: false });
  const previewMerge = async () => {
    if (!merge?.source_id || !merge?.destination_id || merge.source_id === merge.destination_id) return;
    const response = await api('/v018/categories/merge/preview', { method: 'POST', body: JSON.stringify({ source_id: Number(merge.source_id), destination_id: Number(merge.destination_id) }) });
    const payload = await response.json().catch(() => null);
    setMerge((current) => ({ ...current, preview: response.ok ? payload : null, error: response.ok ? '' : payload?.detail || 'Could not preview this merge.' }));
  };
  const confirmMerge = async () => {
    setMerge((current) => ({ ...current, saving: true, error: '' }));
    const response = await api('/v018/categories/merge', { method: 'POST', body: JSON.stringify({ source_id: Number(merge.source_id), destination_id: Number(merge.destination_id) }) });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      setMerge((current) => ({ ...current, saving: false, error: payload?.detail || 'Could not merge these categories.' }));
      return;
    }
    setMerge(null);
    setSelected(null);
    setRevision((value) => value + 1);
  };

  return <section className="panel categories-v0174 categories-v018"><div className="panel-head"><div><h2>Categories</h2><p className="muted">One authoritative parent/child hierarchy. Parent totals include child activity for the selected period.</p></div><div className="category-actions-v018"><button type="button" onClick={loadHealth}>{checkingHealth ? 'Checking…' : 'Check Category Data'}</button><button type="button" onClick={() => beginMerge()}>Merge Category</button><button className="primary ghost" onClick={() => onEdit({ type: 'categories', label: 'New Category', row: { id: null }, values: { name: '', parent_id: '', category_type: 'expense', budget_relationship: 'independent', is_active: true, notes: '' } })}>+ Add</button></div></div>
    {health && <div className={`category-health-v018 ${health.status === 'ok' ? 'is-ok' : 'has-attention'}`}><div><strong>{health.status === 'ok' ? 'Category data is healthy' : `${health.issue_count} category data issue${health.issue_count === 1 ? '' : 's'} detected`}</strong><small>Duplicates {health.duplicate_groups?.length || 0} · Orphans {(health.orphan_children?.length || 0) + Object.values(health.orphan_references || {}).reduce((sum, value) => sum + Number(value || 0), 0)} · Stale paths {Object.values(health.stale_paths || {}).reduce((sum, value) => sum + Number(value || 0), 0)}</small></div>{health.status !== 'ok' && <span>Review before making destructive changes.</span>}</div>}
    <div className="category-list-v0174">{parents.map((parent) => {
      const children = byParent.get(Number(parent.id)) || [];
      const isOpen = expanded.has(parent.id);
      return <div className="category-group-v0174" key={parent.id}><div className="category-row-v0174 parent"><button className="category-accordion-v0174" type="button" aria-expanded={isOpen} onClick={() => toggle(parent.id)}>{children.length ? (isOpen ? '▾' : '▸') : '•'}</button><button className="category-name-v0174" type="button" onClick={() => open(parent)}>{parent.name}</button><strong>{money(parent.total) || '$0.00'}</strong>{parent.entry_count > 0 ? <button className="category-count-v0174" type="button" onClick={() => open(parent)}>{parent.entry_count} entries</button> : <span className="category-count-empty-v018"></span>}</div>
        {isOpen && children.map((child) => <div className="category-row-v0174 child" key={child.id}><span></span><button className="category-name-v0174" type="button" onClick={() => open(child)}>{child.name}</button><strong>{money(child.total) || '$0.00'}</strong>{child.entry_count > 0 ? <button className="category-count-v0174" type="button" onClick={() => open(child)}>{child.entry_count} entries</button> : <span className="category-count-empty-v018"></span>}</div>)}</div>;
    })}</div>
    {selected && <div className="modal-backdrop" role="presentation"><section className="modal detail-modal" role="dialog" aria-modal="true"><div className="panel-head"><div><h2>{selected.name}</h2><p className="muted">{selected.path}</p></div><button type="button" onClick={() => setSelected(null)}>×</button></div><div className="detail-grid"><div className="detail-item"><span>Total</span><strong>{money(selected.total) || '$0.00'}</strong></div><div className="detail-item"><span>Assigned entries</span><strong>{selected.entry_count}</strong></div></div><h3>Matching entries</h3>{loadingEntries ? <p>Loading…</p> : entries.length ? <div className="category-entry-list-v0174">{entries.map((entry) => <div className="list-row" key={`${entry.source_type}-${entry.id}`}><span>{entry.name}<small>{entry.source_type.replaceAll('_', ' ')} · {entry.date || 'No date'}</small></span><strong>{money(entry.amount) || '$0.00'}</strong></div>)}</div> : <p className="muted">No matching entries in this date range.</p>}<div className="modal-actions"><button type="button" onClick={() => setSelected(null)}>Close</button><button type="button" onClick={() => { const row = selected; setSelected(null); beginMerge(row); }}>Merge</button><button type="button" className="primary" onClick={() => { const row = selected; setSelected(null); onEdit({ type: 'categories', label: 'Category', row, values: { name: row.name || '', parent_id: row.parent_id || '', category_type: row.category_type || 'expense', budget_relationship: row.budget_relationship || 'independent', is_active: row.is_active ?? true, notes: row.notes || '' } }); }}>Edit</button></div></section></div>}
    {merge && <div className="modal-backdrop" role="presentation"><section className="modal detail-modal category-merge-v018" role="dialog" aria-modal="true"><div className="panel-head"><div><h2>Merge Category</h2><p className="muted">Move all linked records to the destination, then archive the source.</p></div><button type="button" onClick={() => setMerge(null)}>×</button></div><div className="form-grid"><label className="field"><span>Source Category</span><select value={merge.source_id} onChange={(event) => setMerge({ ...merge, source_id: event.target.value, preview: null, error: '' })}><option value="">Choose source</option>{activeRows.map((row) => <option key={row.id} value={row.id}>{row.path || row.name}</option>)}</select></label><label className="field"><span>Destination Category</span><select value={merge.destination_id} onChange={(event) => setMerge({ ...merge, destination_id: event.target.value, preview: null, error: '' })}><option value="">Choose destination</option>{activeRows.filter((row) => String(row.id) !== String(merge.source_id)).map((row) => <option key={row.id} value={row.id}>{row.path || row.name}</option>)}</select></label></div>{merge.error && <p className="error">{merge.error}</p>}{merge.preview && <div className="merge-preview-v018"><strong>Merge “{merge.preview.source.name}” into “{merge.preview.destination.name}”?</strong><p>The following records will be reassigned:</p><ul>{Object.entries(merge.preview.will_reassign || {}).filter(([, count]) => Number(count) > 0).map(([name, count]) => <li key={name}>{count} {name.replaceAll('_', ' ')}</li>)}</ul><p>The source Category will then be archived. Financial history will not be deleted.</p></div>}<div className="modal-actions"><button type="button" onClick={() => setMerge(null)}>Cancel</button>{!merge.preview ? <button type="button" className="primary" disabled={!merge.source_id || !merge.destination_id} onClick={previewMerge}>Preview Merge</button> : <button type="button" className="primary" disabled={merge.saving} onClick={confirmMerge}>{merge.saving ? 'Merging…' : 'Confirm Merge'}</button>}</div></section></div>}
  </section>;
}

function normaliseNullableRecurringValues(values = {}) {
  const nullable = (value) => value === '' || value === undefined ? null : value;
  return {
    ...values,
    account_id: nullable(values.account_id),
    card_id: nullable(values.card_id),
    category_id: nullable(values.category_id),
    expense_type_id: nullable(values.expense_type_id),
    end_date: nullable(values.end_date),
    reminder_days_before: nullable(values.reminder_days_before),
    effective_from: nullable(values.effective_from),
  };
}

function RecurringRulesWhileScheduling({ rows, scheduleState, scheduleError, retrySchedule, onEdit, money }) {
  return <section className="panel recurring-rules-fast-path"><div className="panel-head"><div><h2>Recurring Expenses</h2><p className="muted">Your recurring rules are available. Scheduled payment information is {scheduleState === 'error' ? 'temporarily unavailable' : 'still refreshing'}.</p></div>{scheduleState === 'error' && <button type="button" onClick={retrySchedule}>Retry scheduled payments</button>}</div>
    {scheduleState === 'error' && <p className="notice" role="alert">Recurring expenses loaded, but scheduled payment information could not be refreshed. {scheduleError}</p>}
    <div className="recurring-rule-fast-list">{rows.map((row) => <button type="button" className="list-row button-row" key={row.id} onClick={() => onEdit({ type: 'recurring', label: 'Recurring Expense', row, values: normaliseNullableRecurringValues(row) })}><span><strong>{row.name}</strong><small>{row.frequency ? String(row.frequency).replaceAll('_', ' ') : 'Frequency not set'} · next due {row.next_due_date ? String(row.next_due_date).slice(0, 10) : 'not set'}</small></span><strong>{money(row.amount) || 'Amount not set'}</strong></button>)}</div>
  </section>;
}

export function RecurringExpensesPageV0174(props) {
  const existingRecurring = props.data?.recurring || [];
  const existingScheduled = props.data?.scheduledPayments || [];
  const existingAttention = props.data?.paymentAttention || [];
  const [recurringData, setRecurringData] = useState(existingRecurring);
  const [scheduledData, setScheduledData] = useState(existingScheduled);
  const [attentionData, setAttentionData] = useState(existingAttention);
  const [recurringState, setRecurringState] = useState(existingRecurring.length ? 'loaded' : 'loading');
  const [scheduleState, setScheduleState] = useState(existingScheduled.length ? 'loaded' : 'loading');
  const [recurringError, setRecurringError] = useState('');
  const [scheduleError, setScheduleError] = useState('');
  const [recurringRevision, setRecurringRevision] = useState(0);
  const [scheduleRevision, setScheduleRevision] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const loadRecurring = async () => {
      if (!recurringData.length) setRecurringState('loading');
      setRecurringError('');
      try {
        const recurring = await apiRequest('/recurring-expenses');
        if (cancelled) return;
        setRecurringData(Array.isArray(recurring) ? recurring : []);
        setRecurringState('loaded');
      } catch (requestError) {
        if (cancelled) return;
        setRecurringError(requestError?.message || 'Could not load recurring expenses.');
        setRecurringState('error');
      }
    };
    loadRecurring();
    return () => { cancelled = true; };
  }, [props.rangeDays, recurringRevision]);

  useEffect(() => {
    let cancelled = false;
    const loadScheduled = async () => {
      if (!scheduledData.length) setScheduleState('loading');
      setScheduleError('');
      try {
        const scheduledPayments = await apiRequest('/scheduled-payments');
        if (cancelled) return;
        const resolved = Array.isArray(scheduledPayments) ? scheduledPayments : [];
        setScheduledData(resolved);
        setAttentionData(resolved.filter((row) => ATTENTION_STATUSES.has(row.status)));
        setScheduleState('loaded');
      } catch (requestError) {
        if (cancelled) return;
        setScheduleError(requestError?.message || 'Scheduled payment information could not be loaded.');
        setScheduleState('error');
      }
    };
    loadScheduled();
    return () => { cancelled = true; };
  }, [props.rangeDays, scheduleRevision]);

  const onEdit = (edit) => props.onEdit({
    ...edit,
    values: normaliseNullableRecurringValues(edit?.values || {}),
  });
  const refresh = () => { setRecurringRevision((value) => value + 1); setScheduleRevision((value) => value + 1); };

  if (recurringState === 'loading' && !recurringData.length) {
    return <section className="panel"><div className="panel-head"><h2>Recurring Expenses</h2></div><p className="muted" role="status">Loading recurring expenses…</p></section>;
  }

  if (recurringState === 'error' && !recurringData.length) {
    return <section className="panel"><div className="panel-head"><h2>Recurring Expenses</h2></div><div className="empty"><strong>Could not load recurring expenses</strong><p>{recurringError}</p><button type="button" className="primary" onClick={() => setRecurringRevision((value) => value + 1)}>Retry</button></div></section>;
  }

  if (recurringState === 'loaded' && recurringData.length > 0 && scheduleState !== 'loaded' && scheduledData.length === 0) {
    return <RecurringRulesWhileScheduling rows={recurringData} scheduleState={scheduleState} scheduleError={scheduleError} retrySchedule={() => setScheduleRevision((value) => value + 1)} onEdit={onEdit} money={props.money}/>;
  }

  const effectiveData = { ...props.data, recurring: recurringData, scheduledPayments: scheduledData, paymentAttention: attentionData };
  return <><div className="recurring-schedule-state">{scheduleState === 'loading' && <p className="muted" role="status">Refreshing scheduled payment information…</p>}{scheduleState === 'error' && <p className="notice" role="alert">Recurring expenses are available, but scheduled payment information could not be refreshed. {scheduleError} <button type="button" onClick={() => setScheduleRevision((value) => value + 1)}>Retry</button></p>}</div><RecurringExpensesPageV151 {...props} data={effectiveData} onEdit={onEdit} onRefresh={refresh}/></>;
}
