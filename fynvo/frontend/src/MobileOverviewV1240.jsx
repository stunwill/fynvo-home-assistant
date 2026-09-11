import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { apiRequest } from './apiClient.js';

const finite = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const money = (value) => {
  const number = finite(value);
  return number === null ? '—' : new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(number);
};

const dateLabel = (value) => value
  ? new Intl.DateTimeFormat('en-AU', { weekday: 'short', day: 'numeric', month: 'short' }).format(new Date(`${String(value).slice(0, 10)}T00:00:00`))
  : 'Date unavailable';

const dueOf = (row) => row?.expected_date || row?.due_date || row?.next_due_date || row?.date || null;
const amountOf = (row) => Math.abs(Number(row?.expected_amount ?? row?.amount ?? row?.estimated_amount ?? 0) || 0);
const inactiveStatuses = new Set(['paid', 'skipped', 'cancelled']);

function activateNavigation(label) {
  const aliases = { Payments: 'Payment Centre', Plan: 'Cash Plan', Accounts: 'Accounts' };
  const target = aliases[label] || label;
  const buttons = [...document.querySelectorAll('#fynvo-navigation button, .sidebar button, .nav-group button, main.content button')];
  buttons.find((button) => button.textContent?.trim() === target)?.click();
}

function useMobileShell(authenticated) {
  const [mobile, setMobile] = useState(() => window.matchMedia('(max-width: 980px)').matches);
  const [activePage, setActivePage] = useState('');
  useEffect(() => {
    const query = window.matchMedia('(max-width: 980px)');
    const sync = () => setMobile(query.matches);
    sync(); query.addEventListener?.('change', sync);
    return () => query.removeEventListener?.('change', sync);
  }, []);
  useEffect(() => {
    if (!authenticated) return undefined;
    const sync = () => setActivePage(document.querySelector('main.content .header h1')?.textContent?.trim() || '');
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    sync(); return () => observer.disconnect();
  }, [authenticated]);
  return { active: authenticated && mobile, activePage };
}

function attentionRank(row) {
  const status = String(row?.status || '').toLowerCase();
  if (status === 'overdue') return 0;
  if (row?.match_review_available || status === 'auto_payment_unconfirmed') return 1;
  return 2;
}

function eventRows(planning) {
  return (planning?.timeline || []).flatMap((group) => group.rows || [])
    .filter((row) => !inactiveStatuses.has(row.status) && dueOf(row))
    .sort((a, b) => String(dueOf(a)).localeCompare(String(dueOf(b))))
    .slice(0, 3);
}

function eventIcon(row) {
  const text = `${row?.name || ''} ${row?.merchant || ''}`.toLowerCase();
  if (text.includes('electric') || text.includes('power')) return 'ϟ';
  if (text.includes('loan') || text.includes('car')) return '▣';
  return '$';
}

export default function MobileOverviewV1240({ authenticated = false, productionVersion = '' }) {
  const { active, activePage } = useMobileShell(authenticated);
  const isOverview = activePage === 'Overview' || activePage.startsWith('Good ');
  const [host, setHost] = useState(null);
  const [planning, setPlanning] = useState(null);
  const [safeToSpend, setSafeToSpend] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [moreOpen, setMoreOpen] = useState(false);

  useEffect(() => {
    if (!active || !isOverview) {
      document.body.classList.remove('fynvo-overview-v1240-active'); setHost(null); return undefined;
    }
    const content = document.querySelector('main.content');
    const dashboard = content?.querySelector('.dashboard-page');
    if (!content || !dashboard) return undefined;
    const node = document.createElement('div');
    node.className = 'fynvo-overview-v1240-host';
    content.insertBefore(node, dashboard);
    setHost(node); document.body.classList.add('fynvo-overview-v1240-active');
    return () => { document.body.classList.remove('fynvo-overview-v1240-active'); node.remove(); setHost(null); };
  }, [active, isOverview]);

  useEffect(() => {
    if (!active || !isOverview) return undefined;
    let cancelled = false;
    setLoading(true); setError('');
    Promise.allSettled([apiRequest('/payment-planning'), apiRequest('/payment-planning/safe-to-spend')]).then(([planningResult, safeResult]) => {
      if (cancelled) return;
      if (planningResult.status === 'fulfilled') setPlanning(planningResult.value || null);
      if (safeResult.status === 'fulfilled') setSafeToSpend(safeResult.value || null);
      if (planningResult.status === 'rejected' && safeResult.status === 'rejected') setError('Overview information could not be refreshed.');
    }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [active, isOverview]);

  const model = useMemo(() => {
    const payCycle = planning?.pay_cycle || {};
    const before = payCycle.before_next_income || {};
    const authoritative = safeToSpend || planning?.safe_to_spend || {};
    const available = finite(authoritative.available_cash ?? before.current_available_cash);
    const committed = finite(authoritative.committed_outgoings ?? before.commitments_total);
    const buffer = finite(authoritative.protected_buffer);
    const safe = finite(authoritative.safe_to_spend ?? before.projected_cash);
    const safeAvailable = authoritative.safe_to_spend !== undefined && authoritative.safe_to_spend !== null && !authoritative.incomplete;
    const attention = (Array.isArray(planning?.attention) ? planning.attention : [])
      .filter((row) => !inactiveStatuses.has(row.status)).sort((a, b) => attentionRank(a) - attentionRank(b)).slice(0, 2);
    const upcoming = eventRows(planning);
    const nextIncome = payCycle.next_income;
    const projectedBalance = finite(payCycle.after_next_income?.projected_cash);
    const pressure = upcoming.find((row) => row.status === 'overdue' || row.status === 'due' || row.status === 'due_today');
    const progressBase = available !== null && committed !== null && buffer !== null ? available + committed + buffer : null;
    return {
      available, committed, buffer, safe, safeAvailable,
      attention, attentionCount: Number(planning?.attention_count ?? planning?.attention?.length ?? 0), upcoming,
      projectedBalance, nextIncome, pressure, progress: progressBase > 0 ? Math.max(0, Math.min(100, (safe / progressBase) * 100)) : null,
      planMessage: pressure ? `${pressure.name || 'An upcoming payment'} is the next pressure point.` : 'No immediate pressure point is identified.',
      warning: authoritative.warnings?.[0] || payCycle.completeness?.message || 'Some planning information is unavailable.',
    };
  }, [planning, safeToSpend]);

  if (!active) return null;
  const open = (label) => { setMoreOpen(false); activateNavigation(label); };
  const overview = isOverview && host ? createPortal(<section className="fynvo-overview-v1240" aria-label="Fynvo Overview">
    {error && <div className="fynvo-overview-v1240-error" role="alert"><span>{error}</span><button type="button" onClick={() => window.location.reload()}>Retry</button></div>}
    <header className="fynvo-overview-v1240-heading"><strong>Fynvo</strong><div aria-label="Overview actions"><button type="button" aria-label="Notifications">♧</button><button type="button" aria-label="Settings">⚙</button></div><h1>Overview</h1><p>Your financial position at a glance</p></header>

    <section className={`fynvo-ui-card fynvo-overview-v1240-safe ${model.safeAvailable ? 'available' : 'unavailable'}`} aria-labelledby="safe-to-spend-title">
      <div className="fynvo-overview-v1240-card-head"><div><h2 id="safe-to-spend-title">Safe to spend <span title="Calculated from available cash, committed payments and protected buffer">ⓘ</span></h2><strong>{model.safeAvailable ? money(model.safe) : 'Unavailable'}</strong></div>{model.safeAvailable && <span className="fynvo-ui-status">{model.safe < 0 ? 'At risk' : 'On track'}</span>}</div>
      <p>{model.safeAvailable ? 'After upcoming payments and your buffer' : model.warning}</p>
      {model.progress !== null && <div className="fynvo-overview-v1240-progress" role="progressbar" aria-label="Safe to spend position" aria-valuenow={model.progress} aria-valuemin="0" aria-valuemax="100"><span style={{ width: `${model.progress}%` }} /></div>}
      <div className="fynvo-overview-v1240-breakdown"><div><strong>{money(model.available)}</strong><span>Available cash</span></div><div><strong>{money(model.committed)}</strong><span>Committed</span></div><div><strong>{money(model.buffer)}</strong><span>Buffer</span></div></div>
    </section>

    <section className="fynvo-ui-card fynvo-overview-v1240-section fynvo-overview-v1240-attention" aria-labelledby="attention-title">
      <div className="fynvo-ui-section-head"><div><h2 id="attention-title">Needs attention</h2><p>{model.attentionCount ? `${model.attentionCount} payment${model.attentionCount === 1 ? '' : 's'} require your attention` : 'All good'}</p></div>{model.attentionCount > 0 && <button type="button" className="fynvo-ui-link" onClick={() => open('Payments')}>View all ›</button>}</div>
      {loading && !planning ? <div className="fynvo-ui-loading" role="status" aria-label="Loading payment attention" /> : model.attention.length ? <div className="fynvo-overview-v1240-events">{model.attention.map((row, index) => <button type="button" className="fynvo-ui-event-row" key={`${row.source_type || 'payment'}-${row.id || index}`} onClick={() => open('Payments')}><span className="fynvo-ui-event-icon danger">!</span><span className="fynvo-ui-event-copy"><strong>{row.name || row.merchant || row.payee || 'Payment'}</strong><small className={row.status === 'overdue' ? 'danger' : ''}>{row.attention_reason || (row.status === 'overdue' ? 'Overdue' : 'Payment needs review')}</small></span><strong className="fynvo-ui-event-amount">{money(amountOf(row))}</strong><span className="fynvo-ui-event-chevron">›</span></button>)}</div> : <p className="fynvo-ui-state">No payments need your attention right now.</p>}
    </section>

    <section className="fynvo-ui-card fynvo-overview-v1240-section" aria-labelledby="coming-up-title"><div className="fynvo-ui-section-head"><div><h2 id="coming-up-title">Coming up</h2><p>{model.upcoming.length ? `Next ${model.upcoming.length} payment${model.upcoming.length === 1 ? '' : 's'}` : 'No upcoming payments'}</p></div>{model.upcoming.length > 0 && <button type="button" className="fynvo-ui-link" onClick={() => open('Payments')}>View all ›</button>}</div>{loading && !planning ? <div className="fynvo-ui-loading" role="status" aria-label="Loading upcoming payments" /> : model.upcoming.length ? <div className="fynvo-overview-v1240-events">{model.upcoming.map((row, index) => <button type="button" className="fynvo-ui-event-row" key={`${row.source_type || 'payment'}-${row.id || index}`} onClick={() => open('Payments')}><span className="fynvo-ui-event-icon">{eventIcon(row)}</span><span className="fynvo-ui-event-copy"><strong>{row.name || row.merchant || row.payee || 'Payment'}</strong><small>{dateLabel(dueOf(row))}</small></span><strong className="fynvo-ui-event-amount">{money(amountOf(row))}</strong><span className="fynvo-ui-event-chevron">›</span></button>)}</div> : <p className="fynvo-ui-state">You’re all caught up.</p>}</section>

    <section className="fynvo-ui-card fynvo-overview-v1240-section fynvo-overview-v1240-plan" aria-labelledby="plan-title"><div className="fynvo-ui-section-head"><div><h2 id="plan-title">Your plan</h2><p>Projected balance after your next pay cycle</p></div><button type="button" className="fynvo-ui-link" onClick={() => open('Plan')}>View plan ›</button></div><strong className="fynvo-overview-v1240-plan-value">{money(model.projectedBalance)}</strong><p className={model.projectedBalance !== null && model.projectedBalance < 0 ? 'danger' : ''}>{model.planMessage}</p>{model.pressure && <div className="fynvo-overview-v1240-plan-detail"><span><strong>{dateLabel(dueOf(model.pressure))}</strong><small>Next pressure point</small></span><span><strong>{money(model.projectedBalance)}</strong><small>Projected balance</small></span></div>}</section>
  </section>, host) : null;

  return <>{overview}<nav className="fynvo-mobile-bottom-nav fynvo-overview-v1240-bottom-nav" aria-label="Primary mobile navigation"><button type="button" className={isOverview ? 'active' : ''} onClick={() => open('Overview')}><span aria-hidden="true">⌂</span><small>Overview</small></button><button type="button" className={activePage === 'Payment Centre' ? 'active' : ''} onClick={() => open('Payments')}><span aria-hidden="true">▣</span><small>Payments</small></button><button type="button" className={activePage === 'Cash Plan' ? 'active' : ''} onClick={() => open('Plan')}><span aria-hidden="true">▤</span><small>Plan</small></button><button type="button" className={activePage === 'Accounts & Cards' || activePage === 'Accounts' ? 'active' : ''} onClick={() => open('Accounts')}><span aria-hidden="true">▭</span><small>Accounts</small></button><button type="button" aria-expanded={moreOpen} onClick={() => setMoreOpen((value) => !value)}><span aria-hidden="true">•••</span><small>More</small></button></nav>{moreOpen && <div className="fynvo-mobile-more-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setMoreOpen(false)}><section className="fynvo-mobile-more-sheet" aria-label="More navigation"><div className="fynvo-mobile-sheet-head"><strong>More</strong><button type="button" onClick={() => setMoreOpen(false)} aria-label="Close More">×</button></div><nav><button type="button" onClick={() => open('Categories')}>Categories</button><button type="button" onClick={() => open('CSV Import')}>Import &amp; data</button><button type="button" onClick={() => open('Review Queue')}>Review queue</button><button type="button" onClick={() => open('Insights')}>Insights</button><button type="button" onClick={() => open('Goals')}>Goals</button><span className="fynvo-mobile-version">Fynvo v{productionVersion || '1.24.0'}</span></nav></section></div>}</>;
}
