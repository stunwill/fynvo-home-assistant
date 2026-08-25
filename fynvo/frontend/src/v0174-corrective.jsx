export const APP_VERSION_V0174 = '1.11.1';

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

function compactMoney(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD', maximumFractionDigits: 0 }).format(number);
}

function chartPoints(forecast) {
  const points = forecast?.chart_points || forecast?.points || forecast?.series || [];
  return points.filter((row) => Number.isFinite(Number(row?.balance ?? row?.forecast_balance ?? row?.value ?? row?.amount)));
}

export function CashFlowChartV0174({ baseline, expected, Empty }) {
  const baselinePoints = chartPoints(baseline);
  const expectedPoints = chartPoints(expected);
  if (!baselinePoints.length && !expectedPoints.length) return <Empty title="No forecast yet">Add financial records to build a cash-flow forecast.</Empty>;
  const rows = baselinePoints.length ? baselinePoints : expectedPoints;
  const values = [...baselinePoints, ...expectedPoints].map((row) => Number(row.balance ?? row.forecast_balance ?? row.value ?? row.amount));
  const minimum = Math.min(...values, 0);
  const maximum = Math.max(...values, 0);
  const span = Math.max(maximum - minimum, 1);
  const width = 900;
  const height = 280;
  const pad = { left: 78, right: 22, top: 24, bottom: 46 };
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const x = (index, count) => pad.left + (count <= 1 ? 0 : (index / (count - 1)) * plotWidth);
  const y = (value) => pad.top + ((maximum - Number(value)) / span) * plotHeight;
  const valueFor = (row) => row.balance ?? row.forecast_balance ?? row.value ?? row.amount;
  const pathFor = (points) => points.map((row, index) => `${index ? 'L' : 'M'}${x(index, points.length).toFixed(1)} ${y(valueFor(row)).toFixed(1)}`).join(' ');
  const ticks = Array.from({ length: 5 }, (_, index) => maximum - (span * index / 4));
  const dateFor = (row) => row.date || row.day || row.label || '';
  const labels = rows.length > 1 ? [0, Math.round((rows.length - 1) / 2), rows.length - 1] : [0];
  return <div className="cashflow-chart-v111"><svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet" role="img" aria-label="Cash Flow Forecast"><g className="cashflow-grid-v111">{ticks.map((tick) => <g key={tick}><line x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)}/><text x={pad.left - 12} y={y(tick) + 4} textAnchor="end">{compactMoney(tick)}</text></g>)}</g>{baselinePoints.length > 0 && <path className="cashflow-line-v111 baseline" d={pathFor(baselinePoints)}/>} {expectedPoints.length > 0 && <path className="cashflow-line-v111 expected" d={pathFor(expectedPoints)}/>}<g className="cashflow-axis-v111">{labels.map((index) => <text key={index} x={x(index, rows.length)} y={height - 14} textAnchor={index === 0 ? 'start' : index === rows.length - 1 ? 'end' : 'middle'}>{dateFor(rows[index])}</text>)}</g></svg><div className="cashflow-legend-v111"><span><i className="baseline"></i>Baseline Forecast</span><span><i className="expected"></i>Expected Forecast</span></div></div>;
}
