import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { apiRequest } from './apiClient.js';

const finite = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const amount = Number(value);
  return Number.isFinite(amount) ? amount : null;
};

const money = (value) => {
  const amount = finite(value);
  return amount === null
    ? '—'
    : new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(amount);
};

const compactMoney = (value) => {
  const amount = finite(value);
  if (amount === null) return '—';
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

function readPreviousSnapshot() {
  try {
    const parsed = JSON.parse(localStorage.getItem('fynvo.overview.snapshot.v1181') || 'null');
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch {
    return null;
  }
}

function writePreviousSnapshot(snapshot) {
  try {
    localStorage.setItem('fynvo.overview.snapshot.v1181', JSON.stringify(snapshot));
  } catch {
    // Storage is optional in embedded webviews.
  }
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

function attentionRank(row) {
  const reason = String(row?.attention_reason || '').toLowerCase();
  const status = String(row?.status || '').toLowerCase();
  if (status === 'overdue') return 0;
  if (reason.includes('reconciliation')) return 1;
  if (reason.includes('funding') || reason.includes('account') || reason.includes('card')) return 2;
  if (status === 'due' || status === 'due_today') return 3;
  if (reason.includes('automatic payment not confirmed')) return 4;
  if (reason.includes('payment method')) return 5;
  return 6;
}

function attentionStatusLabel(row) {
  const reason = row?.attention_reason || '';
  if (row?.status === 'overdue') return 'Overdue';
  if (String(reason).toLowerCase().includes('funding')) return 'Funding incomplete';
  if (String(reason).toLowerCase().includes('payment method')) return 'Payment details incomplete';
  if (String(reason).toLowerCase().includes('automatic payment not confirmed')) return 'Confirmation needed';
  if (row?.status === 'due_today') return 'Due today';
  if (row?.status === 'due') return 'Due soon';
  return reason || 'Needs attention';
}

export default function MobileOverviewV1181({ authenticated = false, productionVersion = '' }) {
  const { active, activePage, rangeDays } = useMobileShellState(authenticated);
  const isOverview = activePage === 'Overview' || activePage.startsWith('Good ');
  const [host, setHost] = useState(null);
  const [command, setCommand] = useState(null);
  const [accounts, setAccounts] = useState(null);
  const [planning, setPlanning] = useState(null);
  const [previousSnapshot] = useState(() => readPreviousSnapshot());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [moreOpen, setMoreOpen] = useState(false);
  const snapshotWrittenRef = useRef(false);

  useEffect(() => {
    if (!active || !isOverview) {
      document.body.classList.remove('fynvo-mobile-overview-active');
      setHost(null);
      return undefined;
    }
    const content = document.querySelector('main.content');
    const dashboard = content?.querySelector('.dashboard-page');
    if (!content || !dashboard) return undefined;
    const existing = content.querySelector('.fynvo-mobile-overview-host');
    existing?.remove();
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
    snapshotWrittenRef.current = false;
    setLoading(true);
    setError('');
    setCommand(null);
    setAccounts(null);
    setPlanning(null);
    Promise.all([
      apiRequest(`/dashboard/command-centre?range_days=${rangeDays}`),
      apiRequest('/accounts'),
      apiRequest('/payment-planning'),
    ]).then(([nextCommand, nextAccounts, nextPlanning]) => {
      if (cancelled) return;
      setCommand(nextCommand || null);
      setAccounts(Array.isArray(nextAccounts) ? nextAccounts : []);
      setPlanning(nextPlanning || null);
    }).catch(() => {
      if (!cancelled) setError('Some Overview information could not be refreshed.');
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [active, isOverview, rangeDays]);

  useEffect(() => {
    if (!active) setMoreOpen(false);
  }, [active]);

  const model = useMemo(() => {
    const hasCommand = command !== null;
    const hasAccounts = Array.isArray(accounts);
    const hasPlanning = planning !== null;
    const kpis = command?.kpis || {};
    const expectedForecast = command?.forecast?.expected || null;
    const baselineForecast = command?.forecast?.baseline || null;
    const events = expectedForecast?.events || baselineForecast?.events || [];
    const inflow = hasCommand ? events.filter((row) => row.direction === 'income').reduce((sum, row) => sum + Math.abs(Number(row.amount) || 0), 0) : null;
    const outflow = hasCommand ? events.filter((row) => row.direction === 'expense').reduce((sum, row) => sum + Math.abs(Number(row.amount) || 0), 0) : null;
    const activeAccounts = hasAccounts ? accounts.filter((account) => account.is_active !== false && !account.archived_at) : [];
    const totalBalance = hasAccounts ? activeAccounts.reduce((sum, account) => sum + Number(account.current_balance ?? account.opening_balance ?? 0), 0) : null;
    const payCycle = planning?.pay_cycle || null;
    const before = payCycle?.before_next_income || null;
    const after = payCycle?.after_next_income || null;
    const nextIncomeKnown = Boolean(payCycle?.completeness?.next_income_known ?? payCycle?.next_income);
    const nextIncome = nextIncomeKnown ? payCycle?.next_income : null;
    const beforeCommitments = finite(before?.commitments_total);
    const beforeCash = finite(before?.current_available_cash);
    const beforeProjected = finite(before?.projected_cash);
    const afterProjectedRaw = finite(after?.projected_cash);
    const afterProjected = nextIncomeKnown ? afterProjectedRaw : null;
    const safeToSpend = beforeProjected !== null && beforeProjected > 0 ? beforeProjected : null;
    const shortfall = beforeProjected !== null && beforeProjected < 0 ? Math.abs(beforeProjected) : null;
    const commitmentCount = beforeCommitments === null ? null : finite(before?.commitment_count);
    const topAccounts = [...activeAccounts]
      .sort((a, b) => Math.abs(Number(b.current_balance ?? b.opening_balance ?? 0)) - Math.abs(Number(a.current_balance ?? a.opening_balance ?? 0)))
      .slice(0, 3);
    const totalFlow = inflow !== null && outflow !== null ? inflow + outflow : null;
    const inflowShare = totalFlow !== null && totalFlow > 0 ? Math.round((inflow / totalFlow) * 100) : null;
    const attention = Array.isArray(planning?.attention) ? planning.attention : [];
    const overdue = attention.filter((row) => row.status === 'overdue');
    const overdueTotal = hasPlanning ? overdue.reduce((sum, row) => sum + Math.abs(Number(row.expected_amount ?? row.amount ?? 0) || 0), 0) : null;
    const unknownAccounts = (payCycle?.accounts || []).filter((row) => row.status === 'unknown');
    const unassignedCount = hasPlanning ? Number(payCycle?.unassigned?.commitment_count || 0) : null;
    const unassignedTotal = hasPlanning ? Number(payCycle?.unassigned?.required || 0) : null;
    const status = !hasPlanning ? 'loading' : !nextIncomeKnown || payCycle?.status === 'unknown' ? 'unknown' : shortfall !== null && shortfall > 0 || payCycle?.status === 'shortfall' ? 'shortfall' : 'funded';
    const sortedAttention = [...attention].sort((a, b) => {
      const rank = attentionRank(a) - attentionRank(b);
      if (rank) return rank;
      const aDate = String(a.expected_date || a.due_date || '9999-12-31');
      const bDate = String(b.expected_date || b.due_date || '9999-12-31');
      if (aDate !== bDate) return aDate.localeCompare(bDate);
      return Math.abs(Number(b.expected_amount ?? b.amount ?? 0)) - Math.abs(Number(a.expected_amount ?? a.amount ?? 0));
    });
    const incompleteCount = hasPlanning ? attention.filter((row) => String(row.attention_reason || '').toLowerCase().includes('missing')).length + (unassignedCount || 0) : null;
    const unconfirmedCount = hasPlanning ? attention.filter((row) => row.status === 'auto_payment_unconfirmed').length : null;
    const next7 = finite(planning?.periods?.next_7_days?.remaining_funding);
    const next30 = finite(planning?.periods?.next_30_days?.remaining_funding);
    const forecastSummary = expectedForecast?.summary || expectedForecast?.kpis || {};
    const forecastBalanceCandidates = [finite(forecastSummary.lowest_balance), finite(forecastSummary.minimum_balance), finite(expectedForecast?.lowest_balance), finite(kpis.lowest_balance)].filter((value) => value !== null);
    const endBalanceCandidates = [finite(forecastSummary.projected_balance), finite(forecastSummary.end_balance), finite(expectedForecast?.projected_balance), finite(kpis.projected_balance)].filter((value) => value !== null);
    return {
      hasCommand, hasAccounts, hasPlanning, inflow, outflow,
      net: inflow !== null && outflow !== null ? inflow - outflow : null,
      nextIncome, nextIncomeKnown, totalBalance, commitments: beforeCommitments, commitmentCount,
      beforeCash: beforeCash ?? totalBalance, beforeProjected, afterProjected, safeToSpend, shortfall, status,
      attentionCount: hasPlanning ? Number(planning?.attention_count ?? attention.length) : null,
      overdueCount: hasPlanning ? overdue.length : null, overdueTotal, incompleteCount, unconfirmedCount,
      unknownAccountCount: hasPlanning ? unknownAccounts.length : null, unassignedCount, unassignedTotal,
      topAttention: sortedAttention.slice(0, 3), topAccounts,
      activeAccountCount: hasAccounts ? activeAccounts.length : null, inflowShare, next7, next30,
      lowestBalance: forecastBalanceCandidates.length ? forecastBalanceCandidates[0] : null,
      endBalance: endBalanceCandidates.length ? endBalanceCandidates[0] : null,
    };
  }, [accounts, command, planning]);

  useEffect(() => {
    if (!active || !isOverview || !model.hasPlanning || !model.hasCommand || !model.hasAccounts || snapshotWrittenRef.current) return;
    snapshotWrittenRef.current = true;
    writePreviousSnapshot({ savedAt: new Date().toISOString(), totalBalance: model.totalBalance, commitments: model.commitments, beforeProjected: model.beforeProjected, attentionCount: model.attentionCount, overdueCount: model.overdueCount });
  }, [active, isOverview, model]);

  if (!active) return null;

  const open = (label) => { setMoreOpen(false); activateNavigation(label); };
  const missingInfoDestination = model.unassignedCount > 0 ? 'Payment Centre' : 'Income';
  const flowStyle = model.inflowShare === null ? {} : { '--inflow-share': `${model.inflowShare}%` };
  const decisionLabel = model.status === 'shortfall' ? 'Funding shortfall' : model.status === 'unknown' ? 'Funding information incomplete' : model.status === 'funded' ? 'Funded before next pay' : 'Loading pay-cycle position';
  const decisionCopy = model.status === 'shortfall'
    ? `${money(model.shortfall)} is not currently covered before the next income.`
    : model.status === 'unknown'
      ? [model.unassignedCount ? `${model.unassignedCount} payment${model.unassignedCount === 1 ? '' : 's'} totalling ${money(model.unassignedTotal)} ${model.unassignedCount === 1 ? 'has' : 'have'} no funding account.` : null, !model.nextIncomeKnown ? 'The next income schedule needs confirmation.' : null].filter(Boolean).join(' ') || 'Some income or funding information needs confirmation.'
      : model.status === 'funded' ? `${money(model.safeToSpend ?? 0)} remains after known commitments before the next income.` : 'Refreshing the authoritative pay-cycle position.';

  const previousBalance = finite(previousSnapshot?.totalBalance);
  const balanceDelta = previousBalance !== null && model.totalBalance !== null ? model.totalBalance - previousBalance : null;
  const previousCommitments = finite(previousSnapshot?.commitments);
  const commitmentDelta = previousCommitments !== null && model.commitments !== null ? model.commitments - previousCommitments : null;
  const previousAttention = finite(previousSnapshot?.attentionCount);
  const attentionDelta = previousAttention !== null && model.attentionCount !== null ? model.attentionCount - previousAttention : null;
  const changeItems = [
    balanceDelta !== null && Math.abs(balanceDelta) >= 1 ? { label: `Available cash ${balanceDelta < 0 ? 'decreased' : 'increased'}`, value: balanceDelta } : null,
    commitmentDelta !== null && Math.abs(commitmentDelta) >= 1 ? { label: `Before-pay commitments ${commitmentDelta > 0 ? 'increased' : 'decreased'}`, value: commitmentDelta } : null,
    attentionDelta !== null && attentionDelta !== 0 ? { label: `${Math.abs(attentionDelta)} attention item${Math.abs(attentionDelta) === 1 ? '' : 's'} ${attentionDelta > 0 ? 'added' : 'resolved'}`, value: null } : null,
  ].filter(Boolean).slice(0, 3);

  const overviewContent = isOverview && host ? createPortal(<section className="fynvo-mobile-overview fynvo-overview-v1181" aria-label="Mobile Overview">
    {error && <div className="fynvo-overview-v1181-warning" role="status"><span>{error}</span><button type="button" onClick={() => window.location.reload()}>Retry</button></div>}
    <section className="fynvo-mobile-section" aria-labelledby="fynvo-mobile-decision"><article className={`fynvo-overview-v1181-card fynvo-overview-v1181-before ${model.status}`}><div className="fynvo-overview-v1181-card-head"><h2 id="fynvo-mobile-decision">Before next pay</h2><button type="button" onClick={() => open('Payment Centre')}>Details ›</button></div>{loading && !model.hasPlanning ? <div className="fynvo-overview-v1181-skeleton" aria-label="Loading before next pay"><span/><span/><span/><span/></div> : <><div className={`fynvo-overview-v1181-state ${model.status}`}><span aria-hidden="true">{model.status === 'shortfall' ? '!' : model.status === 'unknown' ? '△' : model.status === 'funded' ? '✓' : '…'}</span><div><strong>{decisionLabel}</strong><p>{decisionCopy}</p>{model.status === 'unknown' && <button type="button" onClick={() => open(missingInfoDestination)}>Fix missing information ›</button>}</div></div><div className="fynvo-overview-v1181-metrics"><button type="button" onClick={() => open('Accounts')}><span className="metric-icon available" aria-hidden="true">▣</span><span><small>Available now</small><strong className={model.beforeCash === null ? '' : 'positive'}>{money(model.beforeCash)}</strong><em>{model.activeAccountCount === null ? 'Accounts unavailable' : `${model.activeAccountCount} account${model.activeAccountCount === 1 ? '' : 's'}`}</em></span><b aria-hidden="true">›</b></button><button type="button" onClick={() => open('Payment Centre')}><span className="metric-icon commitments" aria-hidden="true">$</span><span><small>Committed before pay</small><strong className={model.commitments === null ? '' : 'attention'}>{model.commitments === null ? 'Not known' : money(model.commitments)}</strong><em>{model.commitments === null ? 'Next-pay window unavailable' : `${model.commitmentCount ?? 0} commitment${model.commitmentCount === 1 ? '' : 's'} · `}{model.commitments !== null && <u>View breakdown</u>}</em></span><b aria-hidden="true">›</b></button><button type="button" onClick={() => open('Income')}><span className="metric-icon income" aria-hidden="true">↗</span><span><small>Next income</small><strong className={model.nextIncome ? 'positive' : ''}>{model.nextIncome ? money(model.nextIncome.amount) : 'Not known'}</strong><em>{model.nextIncome ? `${model.nextIncome.name || 'Income'} · ${dateLabel(model.nextIncome.date)}` : 'Income schedule needs confirmation'}</em></span><b aria-hidden="true">›</b></button><button type="button" onClick={() => open('Payment Centre')}><span className="metric-icon projected" aria-hidden="true">↘</span><span><small>Projected after pay</small><strong className={model.afterProjected === null ? '' : model.afterProjected < 0 ? 'negative' : 'positive'}>{model.afterProjected === null ? 'Not known' : money(model.afterProjected)}</strong><em>{model.afterProjected === null ? 'Requires a confirmed next income' : 'After next income is applied'}</em></span><b aria-hidden="true">›</b></button></div></>}</article></section>
    <section className="fynvo-mobile-section" aria-labelledby="fynvo-mobile-attention"><article className="fynvo-overview-v1181-card fynvo-overview-v1181-attention"><div className="fynvo-overview-v1181-card-head attention-head"><div><h2 id="fynvo-mobile-attention">Needs attention</h2><p>{!model.hasPlanning ? 'Refreshing payment attention' : model.overdueCount ? `${model.overdueCount} overdue · ${money(model.overdueTotal)}` : 'No overdue payments'}</p></div><button type="button" className="attention-count" onClick={() => open('Payment Centre')}>{model.attentionCount === null ? '—' : `${model.attentionCount} items`} ›</button></div><div className="fynvo-overview-v1181-chips"><span className="danger">{model.overdueCount ?? '—'} Overdue</span><span className="warning">{model.unconfirmedCount ?? '—'} Unconfirmed</span><span>{model.incompleteCount ?? '—'} Incomplete</span></div>{!model.hasPlanning ? <div className="fynvo-overview-v1181-inline-loading" role="status">Loading payment attention…</div> : model.topAttention.length ? <div className="fynvo-overview-v1181-attention-list">{model.topAttention.map((row, index) => <button type="button" key={`${row.source_type || 'payment'}-${row.id || row.source_id || index}`} onClick={() => open('Payment Centre')}><span className="attention-mark" aria-hidden="true">{row.status === 'overdue' ? '!' : index === 1 ? '⌂' : '▣'}</span><strong>{row.name || row.merchant || row.payee || 'Payment'}</strong><span className={`attention-status ${row.status === 'overdue' ? 'danger' : ''}`}>{attentionStatusLabel(row)}</span><b>{money(row.expected_amount ?? row.amount)}</b><i aria-hidden="true">›</i></button>)}{model.attentionCount > model.topAttention.length && <small>and {model.attentionCount - model.topAttention.length} more…</small>}</div> : <p className="fynvo-overview-v1181-positive-empty">No payments need attention.</p>}<button type="button" className="fynvo-overview-v1181-link" onClick={() => open('Payment Centre')}>Review all in Payment Centre ›</button></article></section>
    <section className="fynvo-mobile-section"><article className="fynvo-overview-v1181-card fynvo-overview-v1181-needed"><div className="fynvo-overview-v1181-card-head"><h2>Money needed soon</h2><button type="button" onClick={() => open('Payment Centre')}>View upcoming payments ›</button></div><div className="fynvo-overview-v1181-needed-grid"><button type="button" onClick={() => open('Payment Centre')}><small>Next 7 days</small><strong>{model.next7 === null ? '—' : money(model.next7)}</strong></button><button type="button" onClick={() => open('Payment Centre')}><small>Before next pay</small><strong>{model.commitments === null ? 'Not known' : money(model.commitments)}</strong></button><button type="button" onClick={() => open('Payment Centre')}><small>Next 30 days</small><strong>{model.next30 === null ? '—' : money(model.next30)}</strong></button></div></article></section>
    <section className="fynvo-overview-v1181-two-up"><article className="fynvo-overview-v1181-card fynvo-overview-v1181-cash"><h2>Cash position</h2><small className="fynvo-overview-v1181-period">{rangeLabel(rangeDays)}</small><dl><div><dt>Income</dt><dd className={model.inflow === null ? '' : 'positive'}>{compactMoney(model.inflow)}</dd></div><div><dt>Spending</dt><dd className={model.outflow === null ? '' : 'negative'}>{model.outflow === null ? '—' : `−${compactMoney(model.outflow).replace(/^−|-/, '')}`}</dd></div><div className="net"><dt>Net</dt><dd className={model.net === null ? '' : model.net < 0 ? 'negative' : 'positive'}>{model.net === null ? '—' : `${model.net >= 0 ? '+' : ''}${compactMoney(model.net)}`}</dd></div></dl>{model.inflowShare === null ? <div className="fynvo-overview-v1181-inline-loading">Cash-flow data unavailable</div> : <><div className="fynvo-overview-v1181-flow" style={flowStyle}><span/><i/></div><div className="fynvo-overview-v1181-flow-labels"><span>{model.inflowShare}%<small>Income</small></span><span>{100 - model.inflowShare}%<small>Spending</small></span></div></>}</article><article className="fynvo-overview-v1181-card fynvo-overview-v1181-accounts"><h2>Accounts</h2><strong className="account-total">{money(model.totalBalance)}</strong><p>{model.activeAccountCount === null ? 'Account balances unavailable' : `available across ${model.activeAccountCount} account${model.activeAccountCount === 1 ? '' : 's'}`}</p><div>{model.topAccounts.map((account) => <button type="button" key={account.id} onClick={() => open('Accounts')}><span>▣</span><strong>{account.name}</strong><b>{money(Number(account.current_balance ?? account.opening_balance ?? 0))}</b></button>)}</div><button type="button" className="fynvo-overview-v1181-link" onClick={() => open('Accounts')}>View all accounts ›</button></article></section>
    <section className="fynvo-mobile-section"><article className="fynvo-overview-v1181-card fynvo-overview-v1181-changes"><div className="fynvo-overview-v1181-card-head"><h2>What changed?</h2><button type="button" onClick={() => open('Transactions')}>See transactions ›</button></div>{previousSnapshot && changeItems.length ? <div className="fynvo-overview-v1181-change-grid"><div className="change-primary"><span aria-hidden="true">↓</span><div><strong>{changeItems[0].label}{finite(changeItems[0].value) !== null ? ` ${money(Math.abs(changeItems[0].value))}` : ''}</strong><small>since your previous Overview snapshot</small></div></div><div className="change-secondary">{changeItems.slice(1).map((item) => <p key={item.label}><span>{item.label}</span>{finite(item.value) !== null && <b>{item.value > 0 ? '+' : '−'}{money(Math.abs(item.value))}</b>}</p>)}</div></div> : <p className="fynvo-overview-v1181-positive-empty">No material changes are available since the previous Overview snapshot.</p>}</article></section>
    <details className="fynvo-overview-v1181-insights"><summary>More financial insights</summary><article className="fynvo-overview-v1181-card fynvo-overview-v1181-outlook"><div className="fynvo-overview-v1181-card-head"><h2>Financial outlook</h2><button type="button" onClick={() => open('Cash Flow')}>View full forecast ›</button></div><div className="fynvo-overview-v1181-outlook-grid"><div><small>{rangeLabel(rangeDays)} outlook</small><strong>{model.lowestBalance === null ? '—' : money(model.lowestBalance)}</strong><span>Lowest projected balance</span></div><div><small>End balance</small><strong>{model.endBalance === null ? '—' : money(model.endBalance)}</strong><span>{model.lowestBalance === null ? 'Forecast data unavailable' : model.lowestBalance < 0 ? 'Projected shortfall detected' : 'No forecast shortfall detected'}</span></div></div></article></details>
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
          <section className="fynvo-mobile-more-group fynvo-mobile-about"><strong>ABOUT</strong><div><span className="fynvo-mobile-version">Fynvo v{productionVersion || '1.18.2'}</span></div></section>
        </nav>
      </section>
    </div>}
  </>;
}
