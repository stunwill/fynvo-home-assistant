import { useEffect, useMemo, useState } from 'react';
import RecurringExpensesPageV151 from './RecurringExpensesPageV151.jsx';

const api = (path, options = {}) => fetch(`api${path}`, {
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  ...options,
});

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

export function RecurringExpensesPageV0174(props) {
  return <RecurringExpensesPageV151 {...props}/>;
}
