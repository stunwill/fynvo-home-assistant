export const APP_VERSION_V0174 = '1.10.1';

export function categoryGroups(categories = []) {
  const rows = categories.filter((item) => item && item.is_active !== false && (!item.category_type || item.category_type === 'expense'));
  const byParent = new Map();
  for (const row of rows) {
    const parentId = row.parent_id == null ? null : Number(row.parent_id);
    if (!byParent.has(parentId)) byParent.set(parentId, []);
    byParent.get(parentId).push(row);
  }
  for (const list of byParent.values()) list.sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')));
  return (byParent.get(null) || []).map((parent) => ({ parent, children: byParent.get(Number(parent.id)) || [] }));
}

export function CategorySelect({ categories = [], value = '', onChange }) {
  const groups = categoryGroups(categories);
  return <select value={value || ''} onChange={onChange}>
    <option value="">Choose category</option>
    {groups.map(({ parent, children }) => <optgroup key={parent.id} label={parent.name}>
      {children.length ? children.map((child) => <option key={child.id} value={child.path || child.name}>↳ {child.name}</option>) : <option key={parent.id} value={parent.path || parent.name}>{parent.name}</option>}
    </optgroup>)}
  </select>;
}

const compactCurrency = (value) => {
  const number = Number(value || 0);
  const absolute = Math.abs(number);
  if (absolute >= 10000) return `${number < 0 ? '-' : ''}$${Math.round(absolute / 1000)}k`;
  return new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD', maximumFractionDigits: 0 }).format(number);
};

export function CashFlowChartV0174({ rows = [] }) {
  const points = rows.slice(0, 30);
  if (!points.length) return <div className="empty"><strong>No forecast data</strong><p>Add income, bills or recurring expenses to build the cash-flow forecast.</p></div>;
  const values = points.map((row) => Number(row.balance ?? row.running_balance ?? row.amount ?? 0));
  const min = Math.min(...values, 0); const max = Math.max(...values, 1); const span = max - min || 1;
  return <div className="cashflow-v0174-chart" role="img" aria-label="Projected cash-flow balance"><div className="cashflow-v0174-bars">{points.map((row, index) => { const value = values[index]; const height = Math.max(5, Math.round(((value - min) / span) * 100)); return <div className="cashflow-v0174-point" key={`${row.date || index}-${index}`} title={`${row.date || ''} ${compactCurrency(value)}`}><span style={{ height: `${height}%` }}></span></div>; })}</div><div className="cashflow-v0174-axis"><span>{points[0]?.date || ''}</span><span>{points.at(-1)?.date || ''}</span></div></div>;
}
