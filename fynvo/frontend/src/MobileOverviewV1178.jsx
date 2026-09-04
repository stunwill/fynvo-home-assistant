import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';

const money = (value) => {
  const amount = Number(value);
  return Number.isFinite(amount)
    ? new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(amount)
    : '—';
};

const dateLabel = (value) => value
  ? new Intl.DateTimeFormat('en-AU', { day: '2-digit', month: 'short' }).format(new Date(`${String(value).slice(0, 10)}T00:00:00`))
  : 'No date';

const accountTypeLabel = (value) => String(value || 'Account').replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase());

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
    const readShared = () => {
      const shared = globalThis.__fynvoMobileOverviewState;
      if (!shared) return;
      setCommand(shared.command || null);
      setAccounts(shared.accounts || []);
      setPlanning(shared.paymentPlanning || null);
    };
    readShared();
    window.addEventListener('fynvo:overview-data', readShared);
    return () => window.removeEventListener('fynvo:overview-data', readShared);
  }, [active, isOverview]);

  useEffect(() => {
    if (!active) setMoreOpen(false);
  }, [active]);

  const model = useMemo(() => {
    const kpis = command?.kpis || {};
    const events = command?.forecast?.expected?.events || command?.forecast?.baseline?.events || [];
    const inflow = events.filter((row) => row.direction === 'income').reduce((sum, row) => sum + Math.abs(Number(row.amount) || 0), 0);
    const outflow = events.filter((row) => row.direction === 'expense').reduce((sum, row) => sum + Math.abs(Number(row.amount) || 0), 0);
    const nextIncome = events.filter((row) => row.direction === 'income').sort((a, b) => String(a.date || '').localeCompare(String(b.date || '')))[0] || null;
    const totalBalance = accounts.reduce((sum, account) => sum + Number(account.current_balance ?? account.opening_balance ?? 0), 0);
    const commitments = Number(planning?.periods?.next_30_days?.remaining_funding ?? kpis.next_bills_total ?? kpis.scheduled_commitments ?? command?.upcoming_commitments_summary?.total ?? 0);
    const commitmentCount = Number(planning?.periods?.next_30_days?.remaining_count ?? kpis.next_bills_count ?? command?.upcoming_commitments?.length ?? 0);
    const topAccounts = [...accounts]
      .filter((account) => account.is_active !== false && !account.archived_at)
      .sort((a, b) => Math.abs(Number(b.current_balance ?? b.opening_balance ?? 0)) - Math.abs(Number(a.current_balance ?? a.opening_balance ?? 0)))
      .slice(0, 3);
    return {
      inflow,
      outflow,
      net: inflow - outflow,
      nextIncome,
      totalBalance,
      commitments,
      commitmentCount,
      discretionary: Number(kpis.discretionary_spend ?? 0),
      topAccounts,
    };
  }, [accounts, command, planning]);

  if (!active) return null;

  const open = (label) => {
    setMoreOpen(false);
    activateNavigation(label);
  };

  const overviewContent = isOverview && host ? createPortal(<section className="fynvo-mobile-overview" aria-label="Mobile Overview">
    <section className="fynvo-mobile-section" aria-labelledby="fynvo-mobile-snapshot">
      <div className="fynvo-mobile-section-head"><h2 id="fynvo-mobile-snapshot">Snapshot</h2></div>
      <div className="fynvo-mobile-snapshot-grid">
        <button type="button" onClick={() => open('Accounts')}><small>Total Balance</small><strong>{money(model.totalBalance)}</strong><span>{accounts.length} accounts</span></button>
        <button type="button" onClick={() => open('Income')}><small>Next Income</small><strong>{money(model.nextIncome?.amount)}</strong><span>{model.nextIncome ? `${model.nextIncome.name || 'Income'} · ${dateLabel(model.nextIncome.date)}` : 'No scheduled income'}</span></button>
        <button type="button" onClick={() => open('Payment Centre')}><small>Upcoming Commitments</small><strong>{money(model.commitments)}</strong><span>{model.commitmentCount} unresolved</span></button>
        <button type="button" onClick={() => open('Planned Spending')}><small>Discretionary</small><strong>{money(model.discretionary)}</strong><span>Available to use</span></button>
      </div>
    </section>

    <section className="fynvo-mobile-section" aria-labelledby="fynvo-mobile-cashflow">
      <div className="fynvo-mobile-section-head"><h2 id="fynvo-mobile-cashflow">Cash Flow <span>Next {rangeDays} days</span></h2><button type="button" onClick={() => open('Cash Flow')}>View details ›</button></div>
      <button type="button" className="fynvo-mobile-cashflow-card" onClick={() => open('Cash Flow')}>
        <span><small>Inflow</small><strong>{money(model.inflow)}</strong></span>
        <span><small>Outflow</small><strong>{money(model.outflow)}</strong></span>
        <span><small>Net</small><strong>{money(model.net)}</strong></span>
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
          {['Calendar', 'Payment Centre', 'Income', 'Bills', 'Recurring Expenses', 'Planned Spending', 'Budgeting', 'Goals', 'Insights', 'Spending Intelligence', 'CSV Import', 'Import History', 'Review Queue', 'Categories'].map((label) => <button type="button" key={label} onClick={() => open(label)}>{label}</button>)}
          <button type="button" onClick={() => { setMoreOpen(false); window.dispatchEvent(new CustomEvent('fynvo:open-tools')); }}>Tools</button>
        </nav>
      </section>
    </div>}
  </>;
}
