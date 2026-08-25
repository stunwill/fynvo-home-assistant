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

const niceStep = (span) => {
  const rough = Math.max(span / 4, 1);
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const normalized = rough / magnitude;
  const factor = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return factor * magnitude;
};

export function CashFlowChartV0174({ baseline, expected, dateLabel, Empty }) {
  const points = baseline?.chart_points || [];
  const expectedPoints = expected?.chart_points || [];
  const all = [...points, ...expectedPoints];
  if (!all.length) return <Empty title="No forecast yet">Add income, recurring expenses, bills or planned spending to generate a forecast.</Empty>;

  const values = all.map((point) => Number(point.balance || 0));
  const rawMin = Math.min(...values, 0);
  const rawMax = Math.max(...values, 0);
  const step = niceStep(Math.max(rawMax - rawMin, 1));
  const min = Math.floor(rawMin / step) * step;
  const max = Math.ceil(rawMax / step) * step || step;
  const span = Math.max(max - min, step);
  const width = 960;
  const height = 330;
  const padLeft = 92;
  const padRight = 22;
  const padTop = 22;
  const padBottom = 52;
  const plotWidth = width - padLeft - padRight;
  const plotHeight = height - padTop - padBottom;
  const line = (rows) => rows.map((point, index) => {
    const x = padLeft + (index / Math.max(rows.length - 1, 1)) * plotWidth;
    const y = padTop + plotHeight - ((Number(point.balance || 0) - min) / span) * plotHeight;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  const yTicks = Array.from({ length: 5 }, (_, index) => max - (span * index / 4));
  const dateRows = points.length ? points : expectedPoints;
  const tickCount = Math.min(5, dateRows.length);
  const indexes = [...new Set(Array.from({ length: tickCount }, (_, index) => Math.round(index * (dateRows.length - 1) / Math.max(tickCount - 1, 1))))];

  return <div className="chart-wrap chart-with-axes" role="img" aria-label="Cash flow forecast chart with readable balance and date axes">
    <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
      {yTicks.map((tick, index) => {
        const y = padTop + (index / 4) * plotHeight;
        return <g key={`y-${index}`}><line x1={padLeft} y1={y} x2={width - padRight} y2={y}/><text className="axis-label axis-y" x={padLeft - 12} y={y + 4} textAnchor="end">{compactCurrency(tick)}</text></g>;
      })}
      {indexes.map((index) => {
        const x = padLeft + (index / Math.max(dateRows.length - 1, 1)) * plotWidth;
        return <g key={`x-${index}`}><line x1={x} y1={padTop} x2={x} y2={padTop + plotHeight}/><text className="axis-label axis-x" x={x} y={height - 14} textAnchor={index === 0 ? 'start' : index === dateRows.length - 1 ? 'end' : 'middle'}>{dateLabel(dateRows[index]?.date).replace(/\s\d{4}$/, '')}</text></g>;
      })}
      {points.length > 0 && <polyline className="baseline" points={line(points)}/>}
      {expectedPoints.length > 0 && <polyline className="expected" points={line(expectedPoints)}/>}
    </svg>
    <div className="chart-legend"><span><i className="solid"></i>Baseline Forecast</span><span><i className="dash"></i>Expected Forecast</span></div>
  </div>;
}