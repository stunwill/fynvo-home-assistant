import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { apiRequest } from './apiClient.js';

const money = (value) => {
  const amount = Number(value);
  return Number.isFinite(amount)
    ? new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(amount)
    : '—';
};

const compactMoney = (value) => {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return '—';
  const absolute = Math.abs(amount);
  const digits = absolute >= 100000 ? 0 : 2;
  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(amount);
};

const dateLabel = (value) => value
  ? new Intl.DateTimeFormat('en-AU', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(`${String(value).slice(0, 10)}T00:00:00`))
  : 'No date';

const accountTypeLabel = (value) => String(value || 'Account').replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase());
const rangeLabel = (days) => ({ 7: 'Next 7 days', 30: 'Next 30 days', 90: 'Next 90 days', 184: 'Next 6 months', 365: 'Next 12 months' })[Number(days)] || `Next ${days} days`;

function activateNavigation(label) {
  const buttons = [...document.querySelectorAll('#fynvo-navigation button, .sidebar button, main.content button')];
  const target = buttons.find((button) => button.textContent?.trim() === label);
  target?.click();
}

function readRangeDays() {
  const value = Number(localStorage.getItem('fynvo.rangeDays') || 90);
  return Number.isFinite(value) && value > 0 ? value : 90;
}

function useMobileShellState(authenticated) {
  const [isMobile, setIsMobile] = useState(() => window.matchMedia('(max-width: 980px)').matches);
  const [activePage, setActivePage] = useState('');
  const [rangeDays, setRangeDays] = useState(readRangeDays);

  useEffect(() => {
    const query = window.matchMedia('(max-width: 980px)');
    const syncMedia = () => setIsMobile(query.matches);
    syncMedia();
    query.addEventListener?.('change', syncMedia);
    return () => query.removeEventListener?.('change', syncMedia);
  }, []);

  useEffect(() => {
    if (!authenticated) return undefined;
    const sync = () => {
      const heading = document.querySelector('main.content .header h1')?.textContent?.trim() || '';
      setActivePage(heading);
      const nextRange = readRangeDays();
      setRangeDays((current) => current === nextRange ? current : nextRange);
    };
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    document.addEventListener('change', sync, true);
    sync();
    return () => {
      observer.disconnect();
      document.removeEventListener('change', sync, true);
    };
  }, [authenticated]);

  return { active: authenticated && isMobile, activePage, rangeDays };
}

export default function MobileOverviewV1178({ authenticated = false }) {
  const { active, activePage, rangeDays } = useMobileShellState(authenticated);
  const isOverview = activePage === 'Overview' || activePage.startsWith('Good ');
  const [host, setHost] = useState(null);
  const [command, setCommand] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [planning, setPlanning] = useState(null);
  const [moreOpen, setMoreOpen] = useState(false);

  useEffect(() => {
    if (!active || !isOverview) {
      document.body.classList.remove('fynvo-mobile-overview-active');
      setHost(null);
      return undefined;
    }
    const content = document.querySelector('main.content');
    const dashboard = content?.querySelector('.dashboard-page');
    if (!content || !dashboard) return undefined;
    const node = document.createElement('div');
    node.className = 'fynvo-mobile-overview-host';
    content.insertBefore(node, dashboard);
    setHost(node);
    document.body.classList.add('fynvo-mobile-overview-active');
    return () => {
      document.body.classList.remove('fynvo-mobile-overview-active');
      node.remove();
      setHost(null);
    };
  }, [active, isOverview]);

  useEffect(() => {
    if (!active || !isOverview) return undefined;
    let cancelled = false;
    Promise.all([
      apiRequest(`/dashboard/command-centre?range_days=${rangeDays}`),
      apiRequest('/accounts'),
      apiRequest('/payment-planning'),
    ]).then(([nextCommand, nextAccounts, nextPlanning]) => {
      if (cancelled) return;
      setCommand(nextCommand || null);
      setAccounts(nextAccounts || []);
      setPlanning(nextPlanning || null);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [active, isOverview, rangeDays]);

  useEffect(() => {
    if (!active) setMoreOpen(false);
  }, [active]);

  const model = useMemo(() => {
    const kpis = command?.kpis || {};
    const events = command?.forecast?.expected?.events || command?.forecast?.baseline?.events || [];
    const inflow = events.filter((row) => row.direction === 'income').reduce((sum, row) => sum + Math.abs(Number(row.amount) || 0), 0);
    const outflow = events.filter((row) => row.direction === 'expense').reduce((sum, row) => sum + Math.abs(Number(row.amount) || 0), 0);
    const fallbackIncome = events.filter((row) => row.direction === 'income').sort((a, b) => String(a.date || '').localeCompare(String(b.date || '')))[0] || null;
    const activeAccounts = accounts.filter((account) => account.is_active !== false && !account.archived_at);
    const totalBalance = activeAccounts.reduce((sum, account) => sum + Number(account.current_balance ?? account.opening_balance ?? 0), 0);
    const payCycle = planning?.pay_cycle || null;
    const before = payCycle?.before_next_income || {};
    const after = payCycle?.after_next_income || {};
    const nextIncome = payCycle?.next_income || fallbackIncome;
    const beforeCommitments = Number(before.commitments_total);
    const beforeCash = Number(before.current_available_cash);
    const beforeProjected = Number(before.projected_cash);
    const afterProjected = Number(after.projected_cash);
    const safeToSpend = Number.isFinite(beforeProjected) && beforeProjected > 0 ? beforeProjected : 0;
    const shortfall = Number.isFinite(beforeProjected) && beforeProjected < 0 ? Math.abs(beforeProjected) : 0;
    const commitments = Number.isFinite(beforeCommitments) ? beforeCommitments : Number(planning?.periods?.next_30_days?.remaining_funding ?? kpis.next_bills_total ?? kpis.scheduled_commitments ?? command?.upcoming_commitments_summary?.total ?? 0);
    const commitmentCount = Number(before.commitment_count ?? planning?.periods?.next_30_days?.remaining_count ?? kpis.next_bills_count ?? command?.upcoming_commitments?.length ?? 0);
    const topAccounts = [...activeAccounts]
      .sort((a, b) => Math.abs(Number(b.current_balance ?? b.opening_balance ?? 0)) - Math.abs(Number(a.current_balance ?? a.opening_balance ?? 0)))
      .slice(0, 3);
    const totalFlow = inflow + outflow;
    const inflowShare = totalFlow > 0 ? Math.round((inflow / totalFlow) * 100) : 50;
    const attention = planning?.attention || [];
    const overdue = attention.filter((row) => row.status === 'overdue');
    const overdueTotal = overdue.reduce((sum, row) => sum + Math.abs(Number(row.expected_amount ?? row.amount ?? 0) || 0), 0);
    const unknownAccounts = (payCycle?.accounts || []).filter((row) => row.status === 'unknown');
    const status = !payCycle?.next_income || payCycle?.status === 'unknown' ? 'unknown' : shortfall > 0 || payCycle?.status === 'shortfall' ? 'shortfall' : 'funded';
    return {
      inflow,
      outflow,
      net: inflow - outflow,
      nextIncome,
      totalBalance,
      commitments,
      commitmentCount,
      beforeCash: Number.isFinite(beforeCash) ? beforeCash : totalBalance,
      beforeProjected,
      afterProjected,
      safeToSpend,
      shortfall,
      status,
      attentionCount: Number(planning?.attention_count ?? attention.length ?? 0),
      overdueCount: overdue.length,
      overdueTotal,
      unknownAccountCount: unknownAccounts.length,
      discretionary: Number(kpis.discretionary_spend ?? 0),
      topAccounts,
      activeAccountCount: activeAccounts.length,
      inflowShare,
    };
  }, [accounts, command, planning]);

  if (!active) return null;

  const open = (label) => {
    setMoreOpen(false);
    activateNavigation(label);
  };

  const flowStyle = { '--inflow-share': `${model.inflowShare}%`, '--flow-share': '100%' };
  const decisionLabel = model.status === 'shortfall' ? 'Funding shortfall' : model.status === 'unknown' ? 'Funding incomplete' : 'Safe to spend before payday';
  const decisionValue = model.status === 'shortfall' ? model.shortfall : model.status === 'unknown' ? null : model.safeToSpend;
  const decisionMessage = model.status === 'shortfall'
    ? `${money(model.shortfall)} is not currently covered before the next income.`
    : model.status === 'unknown'
      ? 'Fynvo needs complete income and funding-account information before it can confirm the before-pay position.'
      : `${money(model.safeToSpend)} remains after known commitments before the next income.`;

  const overviewContent = isOverview && host ? createPortal(<section className="fynvo-mobile-overview" aria-label="Mobile Overview">
    <section className="fynvo-mobile-section" aria-labelledby="fynvo-mobile-decision">
      <div className="fynvo-mobile-section-head"><h2 id="fynvo-mobile-decision">Before next pay</h2><button type="button" onClick={() => open('Payment Centre')}>Details ›</button></div>
      <article className="fynvo-mobile-decision-card">
        <header><div><small>{decisionLabel}</small><strong>{decisionValue === null ? 'Not known' : money(decisionValue)}</strong></div><span className={`fynvo-mobile-decision-status ${model.status}`}>{model.status === 'shortfall' ? 'SHORTFALL' : model.status === 'funded' ? 'FUNDED' : 'UNKNOWN'}</span></header>
        <div className="fynvo-mobile-decision-grid">
          <div><span>Available now</span><strong>{money(model.beforeCash)}</strong><small>{model.activeAccountCount} active account{model.activeAccountCount === 1 ? '' : 's'}</small></div>
          <div><span>Next income</span><strong>{money(model.nextIncome?.amount)}</strong><small>{model.nextIncome ? `${model.nextIncome.name || 'Income'} · ${dateLabel(model.nextIncome.date)}` : 'No scheduled income'}</small></div>
          <div><span>Committed before pay</span><strong>{compactMoney(model.commitments)}</strong><small>{model.commitmentCount} commitment{model.commitmentCount === 1 ? '' : 's'}</small></div>
          <div><span>Projected after pay</span><strong>{Number.isFinite(model.afterProjected) ? money(model.afterProjected) : 'Not known'}</strong><small>After next income is applied</small></div>
        </div>
        <p className={`fynvo-mobile-decision-message ${model.status === 'shortfall' ? 'danger' : ''}`}>{decisionMessage}</p>
        <div className="fynvo-mobile-decision-actions"><button type="button" onClick={() => open('Payment Centre')}>Review payment plan</button>{model.status === 'unknown' && <button type="button" onClick={() => open('Income')}>Review income</button>}</div>
      </article>
    </section>

    {(model.attentionCount > 0 || model.unknownAccountCount > 0) && <section className="fynvo-mobile-section" aria-labelledby="fynvo-mobile-attention">
      <div className="fynvo-mobile-section-head"><h2 id="fynvo-mobile-attention">Needs attention</h2></div>
      <div className="fynvo-mobile-exceptions">
        {model.attentionCount > 0 && <button type="button" className="fynvo-mobile-exception" onClick={() => open('Payment Centre')}><span><strong>{model.attentionCount} payment{model.attentionCount === 1 ? '' : 's'} need attention</strong><small>{model.overdueCount ? `${model.overdueCount} overdue · ${money(model.overdueTotal)}` : 'Review due and incomplete payments'}</small></span><b>Review ›</b></button>}
        {model.unknownAccountCount > 0 && <button type="button" className="fynvo-mobile-exception" onClick={() => open('Payment Centre')}><span><strong>Funding information incomplete</strong><small>{model.unknownAccountCount} account allocation{model.unknownAccountCount === 1 ? '' : 's'} cannot be confirmed</small></span><b>Fix ›</b></button>}
      </div>
    </section>}

    <section className="fynvo-mobile-section" aria-labelledby="fynvo-mobile-snapshot">
      <div className="fynvo-mobile-section-head"><h2 id="fynvo-mobile-snapshot">Snapshot</h2></div>
      <div className="fynvo-mobile-snapshot-grid">
        <button type="button" data-icon="▣" onClick={() => open('Accounts')}><small>Total Balance</small><strong>{money(model.totalBalance)}</strong><span>{model.activeAccountCount} account{model.activeAccountCount === 1 ? '' : 's'}</span></button>
        <button type="button" data-icon="↗" onClick={() => open('Income')}><small>Next Income</small><strong>{money(model.nextIncome?.amount)}</strong><span>{model.nextIncome ? `${model.nextIncome.name || 'Income'} · ${dateLabel(model.nextIncome.date)}` : 'No scheduled income'}</span></button>
        <button type="button" data-icon="$" onClick={() => open('Payment Centre')}><small>Before-pay Commitments</small><strong>{compactMoney(model.commitments)}</strong><span>{model.commitmentCount} unresolved</span></button>
        <button type="button" data-icon="◇" onClick={() => open('Planned Spending')}><small>Discretionary</small><strong>{money(model.discretionary)}</strong><span>Planning allowance</span></button>
      </div>
    </section>

    <section className="fynvo-mobile-section" aria-labelledby="fynvo-mobile-cashflow">
      <div className="fynvo-mobile-section-head"><h2 id="fynvo-mobile-cashflow">Cash Flow <span>({rangeLabel(rangeDays)})</span></h2><button type="button" onClick={() => open('Cash Flow')}>View details ›</button></div>
      <button type="button" className="fynvo-mobile-cashflow-card" style={flowStyle} onClick={() => open('Cash Flow')}>
        <span><small>Inflow</small><strong>{compactMoney(model.inflow)}</strong></span>
        <span><small>Outflow</small><strong>{compactMoney(model.outflow)}</strong></span>
        <span><small>Net</small><strong className={model.net < 0 ? 'negative' : 'positive'}>{compactMoney(model.net)}</strong></span>
      </button>
    </section>

    <section className="fynvo-mobile-section" aria-labelledby="fynvo-mobile-accounts">
      <div className="fynvo-mobile-section-head"><h2 id="fynvo-mobile-accounts">Top Accounts</h2><button type="button" onClick={() => open('Accounts')}>View all ›</button></div>
      <div className="fynvo-mobile-top-accounts">
        {model.topAccounts.length ? model.topAccounts.map((account) => {
          const balance = Number(account.current_balance ?? account.opening_balance ?? 0);
          return <button type="button" key={account.id} onClick={() => open('Accounts')}>
            <span className="fynvo-mobile-account-mark" aria-hidden="true">▥</span>
            <span><strong>{account.name}</strong><small>{account.institution || accountTypeLabel(account.account_type)}</small></span>
            <span className="fynvo-mobile-account-balance"><strong>{money(balance)}</strong><small>{balance < 0 ? 'Outstanding' : 'Available'}</small></span>
            <b aria-hidden="true">›</b>
          </button>;
        }) : <p className="fynvo-mobile-empty">No accounts yet.</p>}
      </div>
    </section>
  </section>, host) : null;

  const moreGroups = [
    ['PLAN', ['Calendar', 'Planned Spending', 'Budgeting', 'Goals']],
    ['PAYMENTS', ['Payment Centre', 'Bills', 'Recurring Expenses']],
    ['MONEY', ['Income', 'Insights', 'Spending Intelligence']],
    ['DATA & SYSTEM', ['CSV Import', 'Import History', 'Review Queue', 'Categories']],
  ];

  return <>
    {overviewContent}
    <nav className="fynvo-mobile-bottom-nav" aria-label="Primary mobile navigation">
      <button type="button" className={isOverview ? 'active' : ''} onClick={() => open('Overview')}><span aria-hidden="true">⌂</span><small>Overview</small></button>
      <button type="button" className={activePage === 'Accounts & Cards' ? 'active' : ''} onClick={() => open('Accounts')}><span aria-hidden="true">▭</span><small>Accounts</small></button>
      <button type="button" className={activePage === 'Cash Flow' ? 'active' : ''} onClick={() => open('Cash Flow')}><span aria-hidden="true">▥</span><small>Cash Flow</small></button>
      <button type="button" className={activePage === 'Transactions' ? 'active' : ''} onClick={() => open('Transactions')}><span aria-hidden="true">☷</span><small>Transactions</small></button>
      <button type="button" aria-expanded={moreOpen} onClick={() => setMoreOpen((value) => !value)}><span aria-hidden="true">•••</span><small>More</small></button>
    </nav>

    {moreOpen && <div className="fynvo-mobile-more-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setMoreOpen(false)}>
      <section className="fynvo-mobile-more-sheet" aria-label="More navigation">
        <div className="fynvo-mobile-sheet-head"><strong>More</strong><button type="button" onClick={() => setMoreOpen(false)} aria-label="Close More">×</button></div>
        <nav>
          {moreGroups.map(([group, labels]) => <section className="fynvo-mobile-more-group" key={group}><strong>{group}</strong><div>{labels.map((label) => <button type="button" key={label} onClick={() => open(label)}>{label}</button>)}</div></section>)}
          <section className="fynvo-mobile-more-group"><strong>TOOLS</strong><div><button type="button" onClick={() => { setMoreOpen(false); window.dispatchEvent(new CustomEvent('fynvo:open-tools')); }}>Tools</button></div></section>
        </nav>
      </section>
    </div>}
  </>;
}
