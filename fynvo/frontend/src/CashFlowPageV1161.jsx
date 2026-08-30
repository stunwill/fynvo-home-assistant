import { useEffect, useState } from 'react';

import { apiRequest } from './apiClient.js';
import { CashFlowChartV0174 } from './v0174-corrective.jsx';

const finiteNumber = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const money = (value) => {
  const number = finiteNumber(value);
  return number === null ? null : new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(number);
};

const dateLabel = (value) => value
  ? new Intl.DateTimeFormat('en-AU', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(`${String(value).slice(0, 10)}T00:00:00`))
  : 'No date';

const amountClass = (value) => Number(value || 0) >= 0 ? 'positive' : 'negative';

function Empty({ title, children }) {
  return <div className="empty"><strong>{title}</strong><p>{children}</p></div>;
}

export default function CashFlowPageV1161({ rangeDays, onView }) {
  const [state, setState] = useState({ loading: true, error: '', baseline: null, expected: null });

  const load = async () => {
    setState((current) => ({ ...current, loading: true, error: '' }));
    try {
      const [baseline, expected] = await Promise.all([
        apiRequest(`/forecast?mode=baseline&horizon=${rangeDays}d`),
        apiRequest(`/forecast?mode=expected&horizon=${rangeDays}d`),
      ]);
      setState({ loading: false, error: '', baseline, expected });
    } catch (requestError) {
      setState((current) => ({ ...current, loading: false, error: requestError?.message || 'Could not load the Cash Flow forecast.' }));
    }
  };

  useEffect(() => { load(); }, [rangeDays]);

  const forecast = state.expected || state.baseline;
  const events = forecast?.events || [];
  const hasExisting = state.baseline || state.expected;

  return <div className="cashflow-page-v1161">
    <section className="panel cashflow-chart-panel">
      <div className="panel-head compact"><div><h2>Cash Flow Forecast</h2><p className="muted">Projected household balance over the selected period.</p></div><small>Next {rangeDays} days</small></div>
      {state.loading && !hasExisting && <div className="cashflow-loading" role="status"><div><strong>Loading cash flow…</strong><p>Building the latest household forecast.</p></div></div>}
      {state.error && !hasExisting && <div className="cashflow-error" role="alert"><div><strong>Cash Flow could not load</strong><p>{state.error}</p><button type="button" onClick={load}>Retry</button></div></div>}
      {hasExisting && <CashFlowChartV0174 baseline={state.baseline} expected={state.expected} Empty={Empty}/>} 
    </section>
    <section className="panel cashflow-event-panel">
      <div className="panel-head compact"><h2>Forecast events</h2><small>{events.length} events</small></div>
      {state.loading && hasExisting && <p className="muted" role="status">Refreshing forecast…</p>}
      {state.error && hasExisting && <p className="error" role="alert">{state.error} <button type="button" onClick={load}>Retry</button></p>}
      <div className="cashflow-event-list">{events.length ? events.map((event, index) => <button type="button" className="cashflow-event-row" onClick={() => onView(event)} key={`${event.source_type}-${event.source_id}-${event.date}-${index}`}><span><strong>{event.name}</strong><small>{dateLabel(event.date)} · {(event.source_type || 'financial event').replaceAll('_', ' ')}</small></span><strong className={amountClass(event.amount)}>{money(event.amount)}</strong></button>) : !state.loading && !state.error ? <Empty title="No forecast events">Add income, recurring expenses, bills or planned spending.</Empty> : null}</div>
    </section>
  </div>;
}
