import { useCallback, useEffect, useState } from 'react';

import { apiRequest } from './apiClient.js';

const money = (value) => {
  if (value === null || value === undefined || value === '') return 'Not available';
  const number = Number(value);
  return Number.isFinite(number) ? new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(number) : 'Not available';
};

const dateLabel = (value) => value ? new Intl.DateTimeFormat('en-AU', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(`${String(value).slice(0, 10)}T00:00:00`)) : 'No date';

export default function CashPlanPageV121() {
  const [planning, setPlanning] = useState(null);
  const [safePlan, setSafePlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    const [planningResult, safeResult] = await Promise.allSettled([
      apiRequest('/payment-planning'),
      apiRequest('/payment-planning/safe-to-spend'),
    ]);
    if (planningResult.status === 'fulfilled') setPlanning(planningResult.value || null);
    if (safeResult.status === 'fulfilled') setSafePlan(safeResult.value || null);
    if (planningResult.status === 'rejected' && safeResult.status === 'rejected') setError('Cash Plan could not load. Try again.');
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const payCycle = planning?.pay_cycle;
  const incomplete = Boolean(safePlan?.incomplete || safePlan?.planning_status === 'unavailable' || (safePlan && safePlan.safe_to_spend == null));
  const safeValue = safePlan?.safe_to_spend;
  return <section className="cash-plan-v121" aria-label="Cash Plan">
    <div className="cash-plan-v121-head"><div><h2>Cash Plan</h2><p>Understand what is available, reserved and covered before your next pay.</p></div><button type="button" onClick={load} disabled={loading}>{loading ? 'Refreshing…' : 'Refresh'}</button></div>
    {error && <div className="cash-plan-v121-error" role="alert"><strong>{error}</strong><button type="button" onClick={load}>Retry</button></div>}
    {loading && !planning && !safePlan && <div className="cash-plan-v121-state" role="status">Loading cash plan…</div>}
    {!loading && !error && <>
      <article className={`cash-plan-v121-hero ${Number(safeValue) < 0 ? 'negative' : ''} ${incomplete ? 'incomplete' : ''}`}><span>{Number(safeValue) < 0 ? 'Projected shortfall' : incomplete ? 'Safe to spend unavailable' : 'Safe to spend'}</span><strong>{money(safeValue)}</strong><p>{safePlan?.planning_end ? `Until ${dateLabel(safePlan.planning_end)}` : safePlan?.warnings?.join(' ') || payCycle?.completeness?.message || 'A planning horizon needs configuration.'}</p></article>
      <section className="cash-plan-v121-breakdown" aria-label="Safe-to-Spend breakdown"><div><span>Available cash</span><strong>{money(safePlan?.available_cash)}</strong></div><div><span>Committed payments</span><strong>{money(safePlan?.committed_outgoings)}</strong></div><div><span>Protected buffer</span><strong>{money(safePlan?.protected_buffer)}</strong></div><div><span>Eligible income</span><strong>{money(safePlan?.eligible_confirmed_income)}</strong></div></section>
      {incomplete && <div className="cash-plan-v121-note" role="status"><strong>Some planning information is unavailable.</strong> {safePlan?.warnings?.join(' ') || payCycle?.completeness?.message || 'Known payments remain available below.'}</div>}
      {safePlan?.payment_coverage && <div className="cash-plan-v121-coverage"><strong>{safePlan.payment_coverage.first_insufficient_date ? `Funds become insufficient on ${dateLabel(safePlan.payment_coverage.first_insufficient_date)}` : safePlan.payment_coverage.covered_through ? `Known payments covered through ${dateLabel(safePlan.payment_coverage.covered_through)}` : 'Payment coverage is unavailable'}</strong></div>}
      <section className="cash-plan-v121-reserved"><h3>Reserved payments</h3>{safePlan?.reserved_payments?.length ? safePlan.reserved_payments.map((row, index) => <div key={`${row.source_type}-${row.id || index}`}><span><strong>{row.name || 'Payment'}</strong><small>{dateLabel(row.expected_date || row.due_date)}</small></span><strong>{money(row.expected_amount || row.amount)}</strong></div>) : <p>No unresolved payments are reserved in this planning horizon.</p>}</section>
      {planning?.pay_cycle?.completeness?.message && <div className="cash-plan-v121-note">{planning.pay_cycle.completeness.message}</div>}
    </>}
  </section>;
}
