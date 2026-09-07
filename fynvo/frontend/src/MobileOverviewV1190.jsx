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
  : 'No date';

const shortDate = (value) => value
  ? new Intl.DateTimeFormat('en-AU', { day: 'numeric', month: 'short' }).format(new Date(`${String(value).slice(0, 10)}T00:00:00`))
  : '—';

const amountOf = (row) => Math.abs(Number(row?.expected_amount ?? row?.amount ?? 0) || 0);
const dueOf = (row) => row?.expected_date || row?.due_date || null;

function activateNavigation(label) {
  const buttons = [...document.querySelectorAll('#fynvo-navigation button, .sidebar button, .nav-group button, main.content button')];
  buttons.find((button) => button.textContent?.trim() === label)?.click();
}

function useMobileShell(authenticated) {
  const [mobile, setMobile] = useState(() => window.matchMedia('(max-width: 980px)').matches);
  const [activePage, setActivePage] = useState('');

  useEffect(() => {
    const query = window.matchMedia('(max-width: 980px)');
    const sync = () => setMobile(query.matches);
    sync();
    query.addEventListener?.('change', sync);
    return () => query.removeEventListener?.('change', sync);
  }, []);

  useEffect(() => {
    if (!authenticated) return undefined;
    const sync = () => setActivePage(document.querySelector('main.content .header h1')?.textContent?.trim() || '');
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    sync();
    return () => observer.disconnect();
  }, [authenticated]);

  return { active: authenticated && mobile, activePage };
}

function statusLabel(balance, complete) {
  if (!complete) return 'Incomplete';
  if (balance === null) return 'Incomplete';
  if (balance < 0) return 'Shortfall';
  if (balance < 250) return 'Tight';
  return 'Comfortable';
}

function planningPriority(row, nextIncomeDate) {
  const status = String(row?.status || '').toLowerCase();
  const due = dueOf(row);
  if (status === 'overdue') return 0;
  if (row?.match_review_available || status === 'auto_payment_unconfirmed') return 1;
  if (nextIncomeDate && due && String(due).slice(0, 10) < String(nextIncomeDate).slice(0, 10)) return 2;
  if (status === 'due_today' || status === 'due') return 3;
  return 4;
}

function buildWeeklyPlan(planning) {
  const payCycle = planning?.pay_cycle;
  if (!payCycle?.planning_window?.start_date) return [];
  const start = new Date(`${payCycle.planning_window.start_date}T00:00:00`);
  const timelineRows = (planning.timeline || []).flatMap((group) => group.rows || []);
  const incomes = payCycle.upcoming_income_events || [];
  const availableNow = finite(payCycle.before_next_income?.current_available_cash);
  if (availableNow === null) return [];
  let running = availableNow;

  return [0, 1, 2].map((index) => {
    const periodStart = new Date(start);
    periodStart.setDate(periodStart.getDate() + index * 7);
    const periodEnd = new Date(periodStart);
    periodEnd.setDate(periodEnd.getDate() + 6);
    const startKey = periodStart.toISOString().slice(0, 10);
    const endKey = periodEnd.toISOString().slice(0, 10);
    const payments = timelineRows.filter((row) => {
      if (!['upcoming', 'due', 'due_today', 'overdue', 'expected_automatically', 'auto_payment_unconfirmed', 'unknown'].includes(row.status)) return false;
      const due = dueOf(row);
      if (!due) return false;
      const key = String(due).slice(0, 10);
      if (row.status === 'overdue') return index === 0;
      return key >= startKey && key <= endKey;
    });
    const outgoing = payments.reduce((sum, row) => sum + amountOf(row), 0);
    const income = incomes.filter((row) => String(row.date).slice(0, 10) >= startKey && String(row.date).slice(0, 10) <= endKey)
      .reduce((sum, row) => sum + Number(row.amount || 0), 0);
    const startingBalance = running;
    running = startingBalance + income - outgoing;
    return {
      label: index === 0 ? 'This week' : index === 1 ? 'Next week' : 'Following week',
      start: startKey,
      end: endKey,
      startingBalance,
      income,
      outgoing,
      projectedBalance: running,
      paymentCount: payments.length,
      status: statusLabel(running, payCycle.completeness?.complete !== false),
    };
  });
}

export default function MobileOverviewV1190({ authenticated = false, productionVersion = '' }) {
  const { active, activePage } = useMobileShell(authenticated);
  const isOverview = activePage === 'Overview' || activePage.startsWith('Good ');
  const [host, setHost] = useState(null);
  const [planning, setPlanning] = useState(null);
  const [accounts, setAccounts] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [moreOpen, setMoreOpen] = useState(false);

  useEffect(() => {
    if (!active || !isOverview) {
      document.body.classList.remove('fynvo-mobile-overview-v1190-active');
      setHost(null);
      return undefined;
    }
    const content = document.querySelector('main.content');
    const dashboard = content?.querySelector('.dashboard-page');
    if (!content || !dashboard) return undefined;
    const existing = content.querySelector('.fynvo-mobile-overview-v1190-host');
    existing?.remove();
    const node = document.createElement('div');
    node.className = 'fynvo-mobile-overview-v1190-host';
    content.insertBefore(node, dashboard);
    setHost(node);
    document.body.classList.add('fynvo-mobile-overview-v1190-active');
    return () => {
      document.body.classList.remove('fynvo-mobile-overview-v1190-active');
      node.remove();
      setHost(null);
    };
  }, [active, isOverview]);

  useEffect(() => {
    if (!active || !isOverview) return undefined;
    let cancelled = false;
    setLoading(true);
    setError('');
    Promise.all([apiRequest('/payment-planning'), apiRequest('/accounts')])
      .then(([nextPlanning, nextAccounts]) => {
        if (cancelled) return;
        setPlanning(nextPlanning || null);
        setAccounts(Array.isArray(nextAccounts) ? nextAccounts : []);
      })
      .catch(() => {
        if (!cancelled) setError('Household cash plan could not be refreshed.');
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [active, isOverview]);

  useEffect(() => { if (!active) setMoreOpen(false); }, [active]);

  const model = useMemo(() => {
    const payCycle = planning?.pay_cycle || {};
    const before = payCycle.before_next_income || {};
    const after = payCycle.after_next_income || {};
    const available = finite(before.current_available_cash);
    const reserved = finite(before.commitments_total);
    const safe = finite(before.projected_cash);
    const expectedIncome = finite(payCycle.next_income?.amount);
    const afterPay = finite(after.projected_cash);
    const complete = Boolean(payCycle.completeness?.complete && payCycle.next_income);
    const overdueRows = (planning?.attention || []).filter((row) => row.status === 'overdue');
    const overdueTotal = overdueRows.reduce((sum, row) => sum + amountOf(row), 0);
    const nextIncomeDate = payCycle.next_income?.date || null;
    const actionable = [...(planning?.attention || [])]
      .filter((row) => !['paid', 'skipped', 'cancelled'].includes(row.status))
      .sort((a, b) => planningPriority(a, nextIncomeDate) - planningPriority(b, nextIncomeDate)
        || String(dueOf(a) || '9999-12-31').localeCompare(String(dueOf(b) || '9999-12-31')))
      .slice(0, 3);
    const weekly = buildWeeklyPlan(planning);
    const activeAccounts = Array.isArray(accounts) ? accounts.filter((row) => row.is_active !== false && !row.archived_at) : [];
    const fundingAccounts = (payCycle.accounts || []).filter((row) => !row.archived);
    const shortfallCount = fundingAccounts.filter((row) => row.status === 'shortfall').length;

    let pressure = null;
    const projectedBase = available;
    if (projectedBase !== null) {
      let running = projectedBase;
      const events = [];
      (planning?.timeline || []).forEach((group) => (group.rows || []).forEach((row) => {
        if (['paid', 'skipped', 'cancelled'].includes(row.status)) return;
        const date = dueOf(row);
        if (date) events.push({ date: String(date).slice(0, 10), type: 'payment', amount: amountOf(row), name: row.name || 'Payment' });
      }));
      (payCycle.upcoming_income_events || []).forEach((row) => events.push({ date: String(row.date).slice(0, 10), type: 'income', amount: Number(row.amount || 0), name: row.name || 'Income' }));
      events.sort((a, b) => a.date.localeCompare(b.date) || (a.type === 'income' ? -1 : 1));
      let lowest = running;
      let lowestDate = null;
      let causes = [];
      for (const event of events) {
        if (event.type === 'income') {
          running += event.amount;
          continue;
        }
        running -= event.amount;
        if (running < lowest) {
          lowest = running;
          lowestDate = event.date;
          causes = [event];
        } else if (lowestDate && event.date === lowestDate) causes.push(event);
      }
      if (lowestDate) pressure = { date: lowestDate, projected: lowest, causes: causes.slice(0, 3), status: statusLabel(lowest, complete) };
    }

    return {
      available, reserved, safe, expectedIncome, afterPay, complete,
      overdueTotal, overdueCount: overdueRows.length,
      dueBeforePay: reserved,
      nextIncomeDate,
      nextIncomeDays: payCycle.next_income?.days_until,
      activePlanLabel: payCycle.planning_window?.next_income_date ? `Pay cycle to ${shortDate(payCycle.planning_window.next_income_date)}` : 'Pay cycle not available',
      actionable, weekly, pressure,
      activeAccountCount: activeAccounts.length,
      shortfallCount,
      incompleteMessage: payCycle.completeness?.message || 'Income or funding information is incomplete.',
    };
  }, [planning, accounts]);

  if (!active) return null;
  const open = (label) => { setMoreOpen(false); activateNavigation(label); };

  const content = isOverview && host ? createPortal(<section className="fynvo-overview-v1190" aria-label="Household cash plan overview">
    {error && <div className="v1190-warning" role="status"><span>{error}</span><button type="button" onClick={() => window.location.reload()}>Retry</button></div>}

    <article className={`v1190-card v1190-safe ${model.complete ? 'complete' : 'incomplete'}`}>
      <button type="button" className="v1190-card-link" onClick={() => open('Cash Plan')} aria-label="Open full Cash Plan">
        <span className="v1190-icon success" aria-hidden="true">$</span>
        <span><small>Safe to spend</small><strong>{model.complete ? money(model.safe) : 'Unavailable'}</strong><em>{model.complete ? 'After known commitments' : model.incompleteMessage}</em></span>
        <b aria-hidden="true">›</b>
      </button>
      <div className="v1190-safe-breakdown" aria-label="Cash plan breakdown">
        <div><span>Available now</span><strong>{money(model.available)}</strong></div>
        <div><span>Reserved</span><strong className="negative">{money(model.reserved)}</strong></div>
        <div><span>Expected income</span><strong className="positive">{model.expectedIncome === null ? '—' : `+${money(model.expectedIncome)}`}</strong></div>
      </div>
      <button type="button" className="v1190-plan-link" onClick={() => open('Cash Plan')}><span>Active plan: <strong>{model.activePlanLabel}</strong></span><b aria-hidden="true">›</b></button>
    </article>

    <article className="v1190-card v1190-before">
      <div className="v1190-card-head"><div><h2>Cash Plan - Before next pay</h2><p>{model.nextIncomeDays != null ? `${model.nextIncomeDays} days` : 'Planning window'}</p></div></div>
      {loading && !planning ? <div className="v1190-skeleton" aria-label="Loading cash plan"><span/><span/><span/></div> : <>
        <div className="v1190-kpi-pair"><div><span>Due before next pay</span><strong>{money(model.dueBeforePay)}</strong></div><div><span>Overdue</span><strong className={model.overdueTotal > 0 ? 'negative' : ''}>{money(model.overdueTotal)}</strong></div></div>
        <dl><div><dt>Projected balance</dt><dd>{money(model.safe)}</dd></div><div><dt>Next income{model.nextIncomeDays != null ? ` (in ${model.nextIncomeDays} days)` : ''}</dt><dd>{money(model.expectedIncome)}</dd></div><div><dt>Projected after next pay</dt><dd>{money(model.afterPay)}</dd></div></dl>
      </>}
    </article>

    <article className={`v1190-card v1190-pressure ${model.pressure?.status?.toLowerCase() || 'incomplete'}`}>
      <div className="v1190-card-head"><div><h2>Next pressure point</h2><p>{model.pressure ? dateLabel(model.pressure.date) : 'No reliable pressure point yet'}</p></div>{model.pressure && <span className={`v1190-status ${model.pressure.status.toLowerCase()}`}>{model.pressure.status}</span>}</div>
      {model.pressure ? <><p>Projected balance falls to</p><strong className="v1190-pressure-value">{money(model.pressure.projected)}</strong><p>Caused by: {model.pressure.causes.map((row) => `${row.name} (${money(row.amount)})`).join(' + ')}</p><button type="button" className="v1190-text-link" onClick={() => open('Cash Plan')}>See details ›</button></> : <><p>{model.incompleteMessage}</p><button type="button" className="v1190-text-link" onClick={() => open(model.nextIncomeDate ? 'Payment Centre' : 'Income')}>Fix setup ›</button></>}
    </article>

    <article className="v1190-card v1190-pay-next">
      <div className="v1190-card-head"><div><h2>What to pay next</h2><p>Top payments to clear or due soon</p></div></div>
      {model.actionable.length ? <div className="v1190-pay-list">{model.actionable.map((row, index) => {
        const automatic = row.payment_handling === 'automatic';
        return <div key={`${row.source_type || 'payment'}-${row.id || index}`}><span className="rank">{index + 1}</span><button type="button" className="payment" onClick={() => open('Payment Centre')}><strong>{row.name || 'Payment'}</strong><small>{money(amountOf(row))} · {dateLabel(dueOf(row))}</small></button>{automatic ? <span className="automatic">Automatic</span> : <button type="button" className="pay" onClick={() => open('Payment Centre')}>Pay</button>}</div>;
      })}</div> : <p className="v1190-empty">No payments require action right now.</p>}
      <button type="button" className="v1190-text-link" onClick={() => open('Payment Centre')}>View all payments ›</button>
    </article>

    <article className="v1190-card v1190-weekly">
      <div className="v1190-card-head"><div><h2>Weekly cash plan</h2><p>Next 3 weeks</p></div></div>
      {model.weekly.length ? <div className="v1190-weekly-table"><div className="head"><span>Week</span><span>Projected balance</span><span>Status</span></div>{model.weekly.map((week) => <button type="button" key={week.start} onClick={() => open('Cash Plan')}><span><strong>{week.label}</strong><small>{shortDate(week.start)} - {shortDate(week.end)}</small></span><strong>{money(week.projectedBalance)}</strong><em className={`v1190-status ${week.status.toLowerCase()}`}>{week.status}</em></button>)}</div> : <p className="v1190-empty">Weekly projections are unavailable until the cash plan is complete.</p>}
      <button type="button" className="v1190-text-link" onClick={() => open('Cash Plan')}>View full weekly plan ›</button>
    </article>

    <button type="button" className="v1190-card v1190-summary-row" onClick={() => open('Cash Plan')}><span><strong>Money reserved</strong><small>{model.reserved === null ? 'Reserved commitments unavailable' : `${money(model.reserved)} reserved for known commitments`}</small></span><b aria-hidden="true">›</b></button>
    <button type="button" className="v1190-card v1190-summary-row" onClick={() => open('Accounts')}><span><strong>Accounts at a glance</strong><small>{model.activeAccountCount} account{model.activeAccountCount === 1 ? '' : 's'} · {model.shortfallCount} shortfall{model.shortfallCount === 1 ? '' : 's'}</small></span><span className="v1190-inline-link">View accounts ›</span></button>
  </section>, host) : null;

  return <>
    {content}
    <nav className="fynvo-mobile-bottom-nav v1190-bottom-nav" aria-label="Primary mobile navigation">
      <button type="button" className={isOverview ? 'active' : ''} onClick={() => open('Overview')}><span aria-hidden="true">⌂</span><small>Overview</small></button>
      <button type="button" className={activePage === 'Payment Centre' ? 'active' : ''} onClick={() => open('Payment Centre')}><span aria-hidden="true">▣</span><small>Pay Centre</small></button>
      <button type="button" className={activePage === 'Cash Plan' ? 'active' : ''} onClick={() => open('Cash Plan')}><span aria-hidden="true">▤</span><small>Cash Plan</small></button>
      <button type="button" className={activePage === 'Accounts & Cards' ? 'active' : ''} onClick={() => open('Accounts')}><span aria-hidden="true">▭</span><small>Accounts</small></button>
      <button type="button" aria-expanded={moreOpen} onClick={() => setMoreOpen((value) => !value)}><span aria-hidden="true">•••</span><small>More</small></button>
    </nav>
    {moreOpen && <div className="fynvo-mobile-more-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setMoreOpen(false)}><section className="fynvo-mobile-more-sheet" aria-label="More navigation"><div className="fynvo-mobile-sheet-head"><strong>More</strong><button type="button" onClick={() => setMoreOpen(false)} aria-label="Close More">×</button></div><nav><button type="button" onClick={() => open('Cash Flow')}>Cash Flow</button><button type="button" onClick={() => open('Bills')}>Bills</button><button type="button" onClick={() => open('Recurring Expenses')}>Recurring Expenses</button><button type="button" onClick={() => open('Calendar')}>Calendar</button><button type="button" onClick={() => open('Transactions')}>Transactions</button><span className="fynvo-mobile-version">Fynvo v{productionVersion || '1.19.0'}</span></nav></section></div>}
  </>;
}
