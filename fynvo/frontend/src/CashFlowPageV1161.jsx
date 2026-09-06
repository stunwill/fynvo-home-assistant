import { useEffect, useMemo, useState } from 'react';

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

const rangeLabel = (days) => ({ 7: 'Next 7 days', 30: 'Next 30 days', 90: 'Next 90 days', 184: 'Next 6 months', 365: 'Next 12 months' })[Number(days)] || `Next ${days} days`;
const amountClass = (value) => Number(value || 0) >= 0 ? 'positive' : 'negative';

const forecastNumber = (forecast, keys) => {
  for (const key of keys) {
    const value = finiteNumber(forecast?.[key]);
    if (value !== null) return value;
  }
  return null;
};

const forecastSeries = (forecast) => forecast?.chart_points || forecast?.points || forecast?.series || [];

const deriveSummary = (forecast) => {
  if (!forecast) return null;
  const events = Array.isArray(forecast.events) ? forecast.events : [];
  const points = forecastSeries(forecast);
  const pointValues = points.map((row) => finiteNumber(row?.balance ?? row?.forecast_balance ?? row?.value ?? row?.amount)).filter((value) => value !== null);
  const income = events.reduce((sum, row) => {
    const amount = finiteNumber(row?.amount) || 0;
    return row?.direction === 'income' || amount > 0 ? sum + Math.max(amount, 0) : sum;
  }, 0);
  const outgoing = events.reduce((sum, row) => {
    const amount = finiteNumber(row?.amount) || 0;
    return row?.direction === 'expense' || amount < 0 ? sum + Math.abs(Math.min(amount, 0) || amount) : sum;
  }, 0);
  const starting = forecastNumber(forecast, ['starting_balance', 'start_balance', 'opening_balance']) ?? pointValues[0] ?? null;
  const ending = forecastNumber(forecast, ['final_balance', 'end_balance', 'ending_balance']) ?? pointValues.at(-1) ?? null;
  const lowestRecord = forecast?.lowest_balance;
  const lowest = lowestRecord && typeof lowestRecord === 'object'
    ? finiteNumber(lowestRecord.balance ?? lowestRecord.amount ?? lowestRecord.value)
    : finiteNumber(lowestRecord) ?? (pointValues.length ? Math.min(...pointValues) : null);
  const lowestDate = lowestRecord && typeof lowestRecord === 'object' ? (lowestRecord.date || lowestRecord.day || null) : null;
  const net = starting !== null && ending !== null ? ending - starting : income - outgoing;
  return { starting, income, outgoing, net, ending, lowest, lowestDate };
};

function Empty({ title, children }) {
  return <div className="empty"><strong>{title}</strong><p>{children}</p></div>;
}

export default function CashFlowPageV1161({ rangeDays, onView, initialForecast = null, initialBaseline = null, onForecastLoaded }) {
  const initialExpected = initialForecast?.expected || (!initialForecast?.baseline ? initialForecast : null) || null;
  const initialBase = initialForecast?.baseline || initialBaseline || null;
  const hasCompleteSeed = Boolean(initialExpected && initialBase);
  const hasAnySeed = Boolean(initialExpected || initialBase);
  const [state, setState] = useState({ loading: !hasAnySeed, refreshing: false, error: '', baseline: initialBase, expected: initialExpected });
  const [showAllEvents, setShowAllEvents] = useState(false);
  const [eventMode, setEventMode] = useState('next');

  const load = async ({ background = false, seedBaseline = null, seedExpected = null } = {}) => {
    const existingBaseline = seedBaseline || state.baseline;
    const existingExpected = seedExpected || state.expected;
    const needsBaseline = !existingBaseline;
    const needsExpected = !existingExpected;
    if (!needsBaseline && !needsExpected && background) return;
    setState((current) => ({ ...current, loading: !background && !(current.baseline || current.expected || seedBaseline || seedExpected), refreshing: background, error: '' }));
    try {
      const [baseline, expected] = await Promise.all([
        needsBaseline ? apiRequest(`/forecast?mode=baseline&horizon=${rangeDays}d`) : Promise.resolve(existingBaseline),
        needsExpected ? apiRequest(`/forecast?mode=expected&horizon=${rangeDays}d`) : Promise.resolve(existingExpected),
      ]);
      setState({ loading: false, refreshing: false, error: '', baseline, expected });
      onForecastLoaded?.({ baseline, expected, rangeDays });
    } catch (requestError) {
      setState((current) => ({ ...current, loading: false, refreshing: false, error: requestError?.message || 'Could not load the Cash Flow forecast.' }));
    }
  };

  useEffect(() => {
    const seededBaseline = initialForecast?.baseline || initialBaseline || null;
    const seededExpected = initialForecast?.expected || (!initialForecast?.baseline ? initialForecast : null) || null;
    const complete = Boolean(seededBaseline && seededExpected);
    const anySeed = Boolean(seededBaseline || seededExpected);
    setState({ loading: !anySeed, refreshing: false, error: '', baseline: seededBaseline, expected: seededExpected });
    setShowAllEvents(false);
    if (!complete) load({ background: anySeed, seedBaseline: seededBaseline, seedExpected: seededExpected });
  }, [rangeDays]);

  const forecast = state.expected || state.baseline;
  const events = forecast?.events || [];
  const hasExisting = Boolean(state.baseline || state.expected);
  const summary = useMemo(() => deriveSummary(forecast), [forecast]);
  const chronologicalEvents = useMemo(() => [...events].sort((a, b) => String(a.date || '').localeCompare(String(b.date || ''))), [events]);
  const impactEvents = useMemo(() => [...events].sort((a, b) => Math.abs(Number(b?.amount || 0)) - Math.abs(Number(a?.amount || 0))), [events]);
  const orderedEvents = eventMode === 'largest' ? impactEvents : chronologicalEvents;
  const visibleEvents = showAllEvents ? orderedEvents : orderedEvents.slice(0, 5);
  const risk = summary?.lowest !== null && Number(summary?.lowest) < 0;

  return <div className="cashflow-page-v1161 cashflow-page-v1162">
    {summary && <section className={`cashflow-decision-v1180 ${risk ? 'risk' : ''}`} aria-label="Cash Flow decision summary">
      <small>{risk ? 'Cash shortfall predicted' : 'Lowest projected balance'}</small>
      <strong>{money(summary.lowest) || 'Not known'}{summary.lowestDate ? ` · ${dateLabel(summary.lowestDate)}` : ''}</strong>
      <p>{risk ? `The forecast drops below $0 by ${money(Math.abs(summary.lowest)) || 'an unknown amount'}.` : 'No cash shortfall is predicted in the selected forecast period.'}</p>
    </section>}

    <section className="cashflow-summary-v1162" aria-label="Cash Flow summary">
      <article><span>Starting balance</span><strong>{summary ? money(summary.starting) || '—' : '—'}</strong></article>
      <article><span>Income</span><strong className="positive">{summary ? money(summary.income) || '—' : '—'}</strong></article>
      <article><span>Outgoing</span><strong className="negative">{summary ? money(summary.outgoing ? -summary.outgoing : summary.outgoing) || '—' : '—'}</strong></article>
      <article><span>Net movement</span><strong className={summary && Number(summary.net || 0) < 0 ? 'negative' : 'positive'}>{summary ? money(summary.net) || '—' : '—'}</strong></article>
      <article><span>Projected balance</span><strong>{summary ? money(summary.ending) || '—' : '—'}</strong></article>
      <article className={risk ? 'risk' : ''}><span>Lowest balance</span><strong>{summary ? money(summary.lowest) || '—' : '—'}</strong>{summary?.lowestDate && <small>{dateLabel(summary.lowestDate)}</small>}</article>
    </section>

    <section className="panel cashflow-chart-panel">
      <div className="panel-head compact"><div><h2>Cash Flow Forecast</h2><p className="muted">What will happen to your household balance over the selected period.</p></div><small>{rangeLabel(rangeDays)}</small></div>
      {state.loading && !hasExisting && <div className="cashflow-loading" role="status" aria-live="polite"><div><strong>Loading cash flow…</strong><p>Building the latest household forecast.</p></div></div>}
      {state.error && !hasExisting && <div className="cashflow-error" role="alert"><div><strong>Cash Flow could not load</strong><p>{state.error}</p><button type="button" onClick={() => load()}>Retry</button></div></div>}
      {hasExisting && <CashFlowChartV0174 baseline={state.baseline} expected={state.expected} Empty={Empty}/>} 
      {state.refreshing && hasExisting && <p className="muted cashflow-refreshing" role="status">Loading the missing forecast series…</p>}
      {state.error && hasExisting && <p className="error" role="alert">Showing the last available forecast. Refresh failed: {state.error} <button type="button" onClick={() => load({ background: true })}>Retry</button></p>}
    </section>

    <section className="panel cashflow-event-panel">
      <div className="panel-head compact"><div><h2>Events affecting this forecast</h2><p className="muted">{eventMode === 'next' ? 'The next movements in chronological order.' : 'The largest movements by absolute value.'}</p></div>{hasExisting && <small>{events.length} events</small>}</div>
      <div className="payment-v1161-mode" aria-label="Cash Flow event ordering"><button type="button" className={eventMode === 'next' ? 'active' : ''} aria-pressed={eventMode === 'next'} onClick={() => { setEventMode('next'); setShowAllEvents(false); }}>Next events</button><button type="button" className={eventMode === 'largest' ? 'active' : ''} aria-pressed={eventMode === 'largest'} onClick={() => { setEventMode('largest'); setShowAllEvents(false); }}>Largest movements</button></div>
      <div className="cashflow-event-list">{visibleEvents.length ? visibleEvents.map((event, index) => <button type="button" className="cashflow-event-row" onClick={() => onView(event)} key={`${event.source_type}-${event.source_id}-${event.date}-${index}`}><span><strong>{event.name}</strong><small>{dateLabel(event.date)} · {(event.source_type || 'financial event').replaceAll('_', ' ')}</small></span><strong className={amountClass(event.amount)}>{money(event.amount)}</strong></button>) : !state.loading && !state.error && hasExisting ? <Empty title="No forecast events">No financial events affect this selected period.</Empty> : null}</div>
      {events.length > 5 && <div className="cashflow-impact-note"><span className="muted">{showAllEvents ? `Showing all ${events.length} events.` : `Showing the first 5 ${eventMode === 'next' ? 'chronological events' : 'largest movements'}.`}</span><button type="button" className="link-button" onClick={() => setShowAllEvents((value) => !value)}>{showAllEvents ? 'Show less' : `View all ${events.length} events`}</button></div>}
    </section>
  </div>;
}
