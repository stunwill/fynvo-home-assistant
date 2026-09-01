import './pay-cycle-overview.css';

const number = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const money = (value) => {
  const parsed = number(value);
  return parsed === null ? 'Not known' : new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(parsed);
};

const dateLabel = (value) => value
  ? new Intl.DateTimeFormat('en-AU', { day: 'numeric', month: 'short' }).format(new Date(`${String(value).slice(0, 10)}T00:00:00`))
  : 'Not known';

const statusLabel = (status) => ({ funded: 'Funded', shortfall: 'Shortfall', low_buffer: 'Low buffer', unknown: 'Unknown' }[status] || 'Unknown');

export default function PayCycleOverviewCard({ planning, loading, onOpen, onIncome }) {
  if (loading && !planning) {
    return <section className="overview-pay-cycle panel" aria-label="Before next pay" aria-busy="true">
      <div className="overview-pay-cycle-head"><div><small>Before next pay</small><h2>Loading cash plan…</h2></div></div>
      <p className="muted">Checking the next Income event, commitments and available Account balances.</p>
    </section>;
  }

  const payCycle = planning?.pay_cycle;
  if (!payCycle) return null;
  if (!payCycle.next_income) {
    return <section className="overview-pay-cycle panel" aria-label="Before next pay">
      <div className="overview-pay-cycle-head"><div><small>Before next pay</small><h2>Next income not known</h2></div><span className="overview-pay-cycle-status unknown">Unknown</span></div>
      <p className="muted">Fynvo can show upcoming commitments, but it needs an active Income schedule to calculate a complete before-next-pay position.</p>
      <div className="overview-pay-cycle-actions"><button type="button" className="link-button" onClick={onIncome}>Review Income</button><button type="button" className="link-button" onClick={onOpen}>Open Payment Centre →</button></div>
    </section>;
  }

  const before = payCycle.before_next_income || {};
  const after = payCycle.after_next_income || {};
  const attention = (payCycle.accounts || []).find((row) => row.status === 'shortfall' || row.status === 'unknown');
  const noCommitments = Number(before.commitment_count || 0) === 0;
  return <section className="overview-pay-cycle panel dashboard-drilldown-panel" role="button" tabIndex="0" aria-label="Before next pay summary" onClick={onOpen} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onOpen(); } }}>
    <div className="overview-pay-cycle-head"><div><small>Before next pay</small><h2>{dateLabel(payCycle.next_income.date)}</h2><p>{payCycle.next_income.name}</p></div><span className={`overview-pay-cycle-status ${payCycle.status || 'unknown'}`}>{statusLabel(payCycle.status)}</span></div>
    <div className="overview-pay-cycle-grid">
      <div><span>Need before pay</span><strong>{money(before.commitments_total)}</strong><small>{before.commitment_count ?? 0} commitment{before.commitment_count === 1 ? '' : 's'}</small></div>
      <div><span>Available cash</span><strong>{money(before.current_available_cash)}</strong></div>
      <div><span>Projected before pay</span><strong>{money(before.projected_cash)}</strong></div>
      <div><span>After next pay</span><strong>{money(after.projected_cash)}</strong></div>
    </div>
    {noCommitments && <p className="overview-pay-cycle-message">No commitments are due before the next pay.</p>}
    {!noCommitments && attention?.status === 'shortfall' && <p className="overview-pay-cycle-message danger">{attention.account_name} is short by {money(attention.funding_shortfall)} before the next pay.</p>}
    {!noCommitments && attention?.status === 'unknown' && <p className="overview-pay-cycle-message">Funding information is incomplete for {attention.account_name}.</p>}
    <span className="link-button">Open Payment Centre →</span>
  </section>;
}
