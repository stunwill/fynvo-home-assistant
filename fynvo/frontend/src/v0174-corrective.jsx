export const APP_VERSION_V0174 = '1.16.3';

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

export function CategorySelect({ value, onChange, categories = [], placeholder = 'Choose category', required = false }) {
  const groups = categoryGroups(categories);
  return <label className="field"><span>Category</span><select required={required} value={value || ''} onChange={(event) => onChange(event.target.value || null)}><option value="">{placeholder}</option>{groups.map(({ parent, children }) => <optgroup key={parent.id} label={parent.name}><option value={parent.id}>{parent.name}</option>{children.map((child) => <option key={child.id} value={child.id}>{child.name}</option>)}</optgroup>)}</select></label>;
}

const finiteNumber = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const dateKey = (value) => String(value || '').slice(0, 10);

export function forecastSeries(forecast) {
  if (!forecast) return [];
  if (Array.isArray(forecast.series)) return forecast.series;
  if (Array.isArray(forecast.points)) return forecast.points;
  const events = Array.isArray(forecast.events) ? forecast.events : [];
  const starting = finiteNumber(forecast.starting_balance ?? forecast.start_balance ?? forecast.opening_balance) || 0;
  let running = starting;
  const byDate = new Map();
  for (const event of events) {
    running += finiteNumber(event.amount) || 0;
    byDate.set(dateKey(event.date), running);
  }
  return [...byDate.entries()].map(([date, balance]) => ({ date, balance }));
}

export function CashFlowChartV0174({ baseline, expected, Empty }) {
  const baselineSeries = forecastSeries(baseline);
  const expectedSeries = forecastSeries(expected);
  const points = [...baselineSeries, ...expectedSeries];
  if (!points.length) return Empty ? <Empty title="No forecast data">Add income, recurring expenses, bills or planned spending to build your forecast.</Empty> : null;
  const width = 960; const height = 280; const pad = 30;
  const allValues = points.map((point) => finiteNumber(point.balance ?? point.value ?? point.amount)).filter((value) => value !== null);
  const min = Math.min(...allValues); const max = Math.max(...allValues); const spread = max - min || 1;
  const maxLength = Math.max(baselineSeries.length, expectedSeries.length, 2);
  const pathFor = (series) => series.map((point, index) => {
    const value = finiteNumber(point.balance ?? point.value ?? point.amount) || 0;
    const x = pad + (index / Math.max(maxLength - 1, 1)) * (width - pad * 2);
    const y = height - pad - ((value - min) / spread) * (height - pad * 2);
    return `${index ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return <div className="cashflow-chart-v0174" role="img" aria-label="Projected household cash flow"><svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">{baselineSeries.length > 1 && <path className="baseline" d={pathFor(baselineSeries)}/>} {expectedSeries.length > 1 && <path className="expected" d={pathFor(expectedSeries)}/>}</svg><div className="cashflow-chart-legend"><span><i className="baseline"></i>Baseline</span><span><i className="expected"></i>Expected</span></div></div>;
}
