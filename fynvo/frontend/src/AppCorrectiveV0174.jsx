import { useEffect, useRef, useState } from 'react';
import InsightsPage from './InsightsPage.jsx';
import PaymentCentreV112 from './PaymentCentreV112.jsx';
import SpendingIntelligence from './SpendingIntelligence.jsx';
import TransactionWorkspace from './TransactionWorkspace.jsx';
import logo from './assets/fynvo-logo.svg';
import mark from './assets/fynvo-mark.svg';
import { CategoriesPageV0174, RecurringExpensesPageV0174 } from './CorrectiveV0174Pages.jsx';
import { AccountsPageV14, BillsPageV14, IncomePageV14, PlannedSpendingPageV14 } from './V14RecordPages.jsx';
import { CashFlowChartV0174, CategorySelect } from './v0174-corrective.jsx';
import { CardsPageV17, PaymentReconciliationV17, RecurringPaymentFieldsV17, recurringV17Values } from './PaymentManagementV17.jsx';
import { apiRequest } from './apiClient.js';
import './styles.css';

const api = (path, options = {}) => fetch(`api${path}`, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
const today = new Date().toISOString().slice(0, 10);
const APP_VERSION = '1.13.0';
const navGroups = [
  { label: 'Core', items: ['Overview', 'Cash Flow', 'Calendar', 'Accounts'] },
  { label: 'Money', items: ['Payment Centre', 'Transactions', 'Income', 'Bills', 'Recurring Expenses', 'Planned Spending', 'Cards'] },
  { label: 'Planning', items: ['Budgeting', 'Goals'] },
  { label: 'Intelligence', items: ['Insights', 'Spending Intelligence'] },
  { label: 'Import & Data', items: ['CSV Import', 'Import History', 'Review Queue', 'Categories'] },
];
const accountTypeOptions = [['transaction', 'Transaction Account'], ['cash', 'Cash']];
const legacyAccountTypeLabels = {
  savings: 'Savings Account', offset: 'Offset Account', credit_card: 'Credit Card', mortgage: 'Mortgage', personal_loan: 'Personal Loan', car_loan: 'Car Loan', vehicle_loan: 'Car Loan', line_of_credit: 'Line of Credit', investment: 'Investment Account', superannuation: 'Superannuation', other_asset: 'Other Asset', other_liability: 'Other Liability',
};
const recordLabels = { accounts: 'Account', transactions: 'Transaction', income: 'Income', recurring: 'Recurring Expense', bills: 'Bill', planned: 'Planned Spending', categories: 'Category', budgets: 'Budget', goals: 'Goal' };
const quickAddOptions = [
  ['transactions', 'Transaction', 'Record a purchase, payment or deposit.'],
  ['income', 'Income', 'Add a recurring or expected income source.'],
  ['recurring', 'Recurring Expense', 'Add a repeating household commitment.'],
  ['bills', 'Bill', 'Add a bill or one-off obligation.'],
  ['planned', 'Planned Spending', 'Add a future planned purchase or expense.'],
  ['accounts', 'Account', 'Add another financial account.'],
  ['goals', 'Goal', 'Add a savings, purchase or debt goal.'],
];
const accountTypeLabel = (value) => accountTypeOptions.find(([id]) => id === value)?.[1] || legacyAccountTypeLabels[value] || value?.replaceAll('_', ' ') || 'Account';
const horizonOptions = [
  { label: 'Next 7 days', value: 7 }, { label: 'Next 30 days', value: 30 }, { label: 'Next 90 days', value: 90 }, { label: 'Next 6 months', value: 184 }, { label: 'Next 12 months', value: 365 },
];
const finiteNumber = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};
const money = (value) => {
  const number = finiteNumber(value);
  return number === null ? null : new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(number);
};
const dateLabel = (value) => value ? new Intl.DateTimeFormat('en-AU', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(`${String(value).slice(0, 10)}T00:00:00`)) : 'No date';
const amountClass = (value) => Number(value || 0) >= 0 ? 'positive' : 'negative';
const greetingForNow = () => { const hour = new Date().getHours(); if (hour < 12) return 'Good morning'; if (hour < 17) return 'Good afternoon'; return 'Good evening'; };
const Field = ({ label, children, error, className = '', ...props }) => <label className={`field ${className} ${error ? 'field-error' : ''}`.trim()}><span>{label}</span>{children || <input {...props}/>} {error && <small className="field-error-message">{error}</small>}</label>;
const Empty = ({ title, children, action }) => <div className="empty"><strong>{title}</strong><p>{children}</p>{action}</div>;
const toDateInput = (value) => value ? String(value).slice(0, 10) : '';

function friendlyError(payload, fallback) {
  const detail = payload?.detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => { const field = item.loc?.slice(-1)[0]; if (field === 'account_id' || field === 'destination_account_id') return 'Choose a valid account.'; if (field === 'card_id') return 'Choose a valid Card.'; if (field === 'category_id') return 'Choose a valid Category.'; if (field === 'expense_type_id') return 'Choose a valid Expense Type.'; if (field === 'end_date') return 'Check the End Date.'; if (item.type === 'missing') return `${String(field || 'A required field').replaceAll('_', ' ')} is required.`; if (field) return `Check ${String(field).replaceAll('_', ' ')}.`; return null; }).filter(Boolean);
    return [...new Set(messages)].join(' ') || fallback;
  }
  if (typeof detail === 'string') return detail;
  return fallback;
}

function normaliseMutationValues(type, values = {}) {
  if (!['recurring', 'bills'].includes(type)) return values;
  const nullable = (value) => value === '' || value === undefined ? null : value;
  const normalized = {
    ...values,
    account_id: nullable(values.account_id),
    card_id: nullable(values.card_id),
    category_id: nullable(values.category_id),
    expense_type_id: nullable(values.expense_type_id),
  };
  if (type === 'recurring') return { ...normalized, end_date: nullable(values.end_date), reminder_days_before: nullable(values.reminder_days_before), effective_from: nullable(values.effective_from) };
  return { ...normalized, recurring_expense_id: nullable(values.recurring_expense_id), paid_through_date: nullable(values.paid_through_date) };
}

export function normaliseRecord(type, row = {}) {
  if (type === 'accounts') return { name: row.name || '', account_type: row.account_type || 'transaction', institution: row.institution || '', opening_balance: row.opening_balance || '0.00', description: row.description || '', account_suffix: row.account_suffix || '', icon: row.icon || '', color: row.color || '' };
  if (type === 'transactions') return { account_id: row.account_id || '', date: toDateInput(row.date || row.transaction_date) || today, amount: row.amount || '', transaction_type: row.transaction_type || 'expense', description: row.description || '', merchant: row.merchant || '', category: row.category || '', notes: row.notes || '', status: row.status || 'cleared' };
  if (type === 'income') return { name: row.name || '', amount: row.amount || '', frequency: row.frequency || 'monthly', next_payment_date: toDateInput(row.next_payment_date) || today, destination_account_id: row.destination_account_id || '', payer: row.payer || '', category: row.category || '', is_active: row.is_active ?? true, notes: row.notes || '', effective_from: '' };
  if (type === 'recurring') return recurringV17Values({ ...row, next_due_date: toDateInput(row.next_due_date) || today });
  if (type === 'bills') return { name: row.name || '', provider: row.provider || '', payee_merchant: row.payee_merchant || row.provider || '', bill_type: row.bill_type || '', priority: row.priority || 'normal', amount: row.expected_amount ?? row.amount ?? '', due_date: toDateInput(row.due_date || row.expected_date) || today, account_id: row.account_id ?? null, card_id: row.card_id ?? null, category_id: row.category_id ?? null, expense_type_id: row.expense_type_id ?? null, payment_handling: row.payment_handling || 'manual', payment_method: row.payment_method || 'not_set', auto_payment_grace_days: row.auto_payment_grace_days ?? 3, paid_through_date: toDateInput(row.paid_through_date), notes: row.notes || '', recurring_expense_id: row.recurring_expense_id || '', version: row.version ?? null };
  if (type === 'planned') return { name: row.name || '', description: row.description || '', estimated_amount: row.estimated_amount || '', planned_date: toDateInput(row.planned_date) || today, category: row.category || '', account_id: row.account_id ?? null, priority: row.priority || 'medium', status: row.status || 'planned', include_in_forecast: row.include_in_forecast ?? true, notes: row.notes || '' };
  if (type === 'categories') return { name: row.name || '', parent_id: row.parent_id || '', icon: row.icon || '', color: row.color || '', category_type: row.category_type || 'expense', budget_relationship: row.budget_relationship || 'independent', is_active: row.is_active ?? true, notes: row.notes || '' };
  if (type === 'budgets') return { name: row.name || '', category_id: row.category_id || '', category_name: row.category_name || '', direction: row.direction || 'expense', period: row.period || 'monthly', amount: row.amount || '', allocation_strategy: row.allocation_strategy || 'spend_during_period', relationship_mode: row.relationship_mode || 'independent', anchor_date: toDateInput(row.anchor_date) || today, start_date: toDateInput(row.start_date) || today, end_date: toDateInput(row.end_date), rollover_enabled: row.rollover_enabled ?? false, negative_rollover_enabled: row.negative_rollover_enabled ?? false, is_active: row.is_active ?? true, notes: row.notes || '', effective_from: '' };
  if (type === 'goals') return { name: row.name || '', description: row.description || '', goal_type: row.goal_type || 'savings', target_amount: row.target_amount || '', current_amount: row.current_amount || '', start_date: toDateInput(row.start_date) || today, target_date: toDateInput(row.target_date), priority: row.priority || 'medium', contribution_frequency: row.contribution_frequency || 'monthly', contribution_amount: row.contribution_amount || '', status: row.status || 'active', notes: row.notes || '' };
  return { ...row };
}

function endpointFor(type, id) { return ({ accounts: `/accounts/${id}`, transactions: `/transactions/${id}`, income: `/income/${id}`, recurring: `/recurring-expenses/${id}`, bills: `/bills/${id}`, planned: `/planned-spending/${id}`, categories: `/categories/${id}`, budgets: `/budgets/${id}`, goals: `/goals/${id}` })[type]; }
function createPath(type) { return ({ accounts: '/accounts', transactions: '/transactions', income: '/income', recurring: '/recurring-expenses', bills: '/bills', planned: '/planned-spending', categories: '/categories', budgets: '/budgets', goals: '/goals' })[type]; }
function forecastSource(event, data) { const mapping = { income: ['income', data.income], recurring_expense: ['recurring', data.recurring], bill: ['bills', data.bills], planned_spending: ['planned', data.planned] }; const matched = mapping[event?.source_type]; if (!matched) return { type: null, record: null }; const [type, rows] = matched; return { type, record: (rows || []).find((row) => Number(row.id) === Number(event.source_id)) || null }; }

export default function AppCorrectiveV0174() {
  const [auth, setAuth] = useState(null);
  const [active, setActive] = useState(localStorage.getItem('fynvo.view') || 'Overview');
  const [rangeDays, setRangeDays] = useState(Number(localStorage.getItem('fynvo.rangeDays') || 90));
  const [form, setForm] = useState({ username: '', display_name: '', password: '' });
  const [data, setData] = useState({ accounts: [], cards: [], transactions: [], income: [], recurring: [], scheduledPayments: [], bills: [], planned: [], categories: [], expenseTypes: [], budgets: [], goals: [], imports: [], review: [], suggestions: [], insights: [], financialHealth: null, budgetAnalysis: null, forecast: null, command: null, paymentCentreOverview: null });
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [error, setError] = useState(''); const [success, setSuccess] = useState(''); const [edit, setEdit] = useState(null); const [quick, setQuick] = useState(null); const [quickMenuOpen, setQuickMenuOpen] = useState(false); const [detail, setDetail] = useState(null); const [greeting, setGreeting] = useState(() => greetingForNow()); const [mobileNavOpen, setMobileNavOpen] = useState(false); const [isMobile, setIsMobile] = useState(() => window.matchMedia('(max-width: 980px)').matches);
  const menuButtonRef = useRef(null); const closeButtonRef = useRef(null); const commandRequestRef = useRef(0); const initialLoadedRef = useRef(false);
  const [importState, setImportState] = useState({ filename: '', account_id: '', csv_text: '', source_name: 'Australian bank CSV', mapping: { date: 'Date', description: 'Description', debit: 'Debit', credit: 'Credit', amount: 'Amount' }, preview: null });

  async function loadAuth() { const res = await api('/auth/state'); setAuth(await res.json()); }
  async function j(path) { try { return await apiRequest(path); } catch { return null; } }
  async function refreshDashboard(days = rangeDays) { const requestId = ++commandRequestRef.current; setDashboardLoading(true); try { const command = await j(`/dashboard/command-centre?range_days=${days}`); if (requestId !== commandRequestRef.current) return; setData((current) => ({ ...current, command })); } finally { if (requestId === commandRequestRef.current) setDashboardLoading(false); } }
  async function loadSupportingData() {
    const paymentCentreRequest = active === 'Overview' ? j('/payment-centre?date_range=next_30_days') : Promise.resolve(null);
    const [accounts, cards, transactions, income, recurring, scheduledPayments, bills, planned, categories, referenceData, budgets, goals, imports, review, suggestions, insights, financialHealth, budgetAnalysis, forecast, paymentCentreOverview] = await Promise.all([
      j('/accounts'), j('/cards?include_inactive=true'), j('/transactions'), j('/income'), j('/recurring-expenses'), j('/scheduled-payments'), j('/bills'), j('/planned-spending'), j('/categories'), j('/reference-data'), j('/budgets'), j('/goals'), j('/imports/history'), j('/reconciliation/review-queue'), j('/intelligence/suggestions'), j(`/insights?horizon_days=${rangeDays}&refresh=false`), j(`/insights/financial-health?horizon_days=${rangeDays}`), j('/budgets/analysis'), j(`/forecast?mode=expected&horizon=${rangeDays}d`), paymentCentreRequest,
    ]);
    setData((current) => ({ ...current, accounts: accounts || [], cards: cards || [], transactions: transactions || [], income: income || [], recurring: recurring || [], scheduledPayments: scheduledPayments || [], bills: bills || [], planned: planned || [], categories: categories || [], expenseTypes: referenceData?.expense_types || [], budgets: budgets || [], goals: goals || [], imports: imports || [], review: review || [], suggestions: suggestions || [], insights: insights || [], financialHealth, budgetAnalysis, forecast, paymentCentreOverview: paymentCentreOverview === null ? current.paymentCentreOverview : paymentCentreOverview }));
  }
  async function loadAll() { await Promise.allSettled([refreshDashboard(rangeDays), loadSupportingData()]); }
  async function refreshRecurringSlice() {
    const recurring = await apiRequest('/recurring-expenses');
    setData((current) => ({ ...current, recurring: recurring || [] }));
    try {
      const scheduledPayments = await apiRequest('/scheduled-payments');
      setData((current) => ({ ...current, scheduledPayments: scheduledPayments || [] }));
      return { scheduleError: false };
    } catch {
      return { scheduleError: true };
    }
  }
  async function refreshCards() { const cards = await apiRequest('/cards?include_inactive=true'); setData((current) => ({ ...current, cards: cards || [] })); }
  useEffect(() => { loadAuth(); }, []);
  useEffect(() => { if (auth?.authenticated && !initialLoadedRef.current) { initialLoadedRef.current = true; loadAll(); } }, [auth?.authenticated]);
  useEffect(() => { if (auth?.authenticated) refreshDashboard(rangeDays); localStorage.setItem('fynvo.rangeDays', String(rangeDays)); }, [rangeDays]);
  useEffect(() => { localStorage.setItem('fynvo.view', active); setError(''); setSuccess(''); setEdit(null); setQuick(null); setDetail(null); setQuickMenuOpen(false); if (auth?.authenticated && active === 'Overview') loadSupportingData(); }, [active]);
  useEffect(() => { const update = () => { const mobile = window.matchMedia('(max-width: 980px)').matches; setIsMobile(mobile); if (!mobile) setMobileNavOpen(false); }; window.addEventListener('resize', update); return () => window.removeEventListener('resize', update); }, []);
  useEffect(() => { setGreeting(greetingForNow()); const timer = window.setInterval(() => setGreeting(greetingForNow()), 60000); return () => window.clearInterval(timer); }, []);

  async function submitAuth(e) { e.preventDefault(); setError(''); const endpoint = auth.setup_required ? '/auth/setup' : '/auth/login'; const res = await api(endpoint, { method: 'POST', body: JSON.stringify(form) }); if (res.ok) await loadAuth(); else setError('Sign in failed. Check your credentials.'); }
  async function logout() { await api('/auth/logout', { method: 'POST' }); initialLoadedRef.current = false; setData((current) => ({ ...current, paymentCentreOverview: null })); await loadAuth(); }
  async function saveEdit(e) {
    e.preventDefault(); setError(''); setSuccess('');
    const creating = edit.row?.id === null || edit.row?.id === undefined;
    const path = creating ? createPath(edit.type) : endpointFor(edit.type, edit.row.id);
    const values = normaliseMutationValues(edit.type, edit.values);
    try {
      const payload = await apiRequest(path, { method: creating ? 'POST' : 'PUT', body: JSON.stringify(values) });
      if (edit.type === 'recurring') {
        const refresh = await refreshRecurringSlice();
        if (refresh.scheduleError) setError('Recurring Expense saved, but scheduled payment information could not be refreshed yet.');
      } else await loadSupportingData();
      setEdit(null);
      setSuccess(`${creating ? edit.label.replace(/^New /, '') + ' created.' : edit.label + ' updated.'}`);
      if (payload && edit.type === 'recurring') setData((current) => ({ ...current, recurring: current.recurring.map((row) => Number(row.id) === Number(payload.id) ? payload : row) }));
    } catch (requestError) {
      const payload = requestError?.payload;
      setError(friendlyError(payload, requestError?.message || `Could not ${creating ? 'create' : 'save'} ${edit.label}. Check the fields and try again.`));
    }
  }
  async function createRecord(type, values) {
    setError(''); setSuccess('');
    if (['recurring', 'transactions', 'bills'].includes(type)) {
      try {
        await apiRequest(createPath(type), { method: 'POST', body: JSON.stringify(normaliseMutationValues(type, values)) });
        setQuick(null); setSuccess(`${recordLabels[type]} created.`); await loadAll();
      } catch (requestError) {
        setError(friendlyError(requestError?.payload, requestError?.message || `Could not create ${recordLabels[type]}. Check the fields and try again.`));
      }
      return;
    }
    const res = await api(createPath(type), { method: 'POST', body: JSON.stringify(values) });
    if (res.ok) { setQuick(null); setSuccess(`${recordLabels[type] || 'Record'} created.`); await loadAll(); } else setError(friendlyError(await res.json().catch(() => null), 'Could not create this record. Check the fields and try again.'));
  }
  async function previewImport(e) { e.preventDefault(); const res = await api('/imports/preview', { method: 'POST', body: JSON.stringify(importState) }); if (res.ok) setImportState({ ...importState, preview: await res.json() }); else setError('CSV preview failed. Check the account, headers and mapping.'); }
  async function commitImport() { const res = await api('/imports/commit', { method: 'POST', body: JSON.stringify(importState) }); if (res.ok) { setImportState({ ...importState, preview: await res.json() }); await loadAll(); } else setError('CSV import failed. Review invalid rows and duplicates.'); }
  async function acceptMatch(id) { const res = await api(`/reconciliation/${id}/accept`, { method: 'POST' }); if (res.ok) await loadAll(); else setError('Could not accept match.'); }
  async function completeGoal(id) { const res = await api(`/goals/${id}/complete`, { method: 'POST' }); if (res.ok) { setSuccess('Goal completed.'); await loadAll(); } }
  async function dismissSuggestion(id) { const res = await api(`/intelligence/suggestions/${id}/dismiss`, { method: 'POST' }); if (res.ok) await loadAll(); }
  async function dismissInsight(id) { const res = await api(`/insights/${id}/dismiss`, { method: 'POST' }); if (res.ok) await loadAll(); else setError('Could not dismiss Insight.'); }
  async function reviewInsight(id) { const res = await api(`/insights/${id}/reviewed`, { method: 'POST' }); if (res.ok) await loadAll(); else setError('Could not mark Insight as reviewed.'); }
  async function refreshInsights() { const res = await api(`/insights/refresh?horizon_days=${rangeDays}`, { method: 'POST' }); if (res.ok) { setSuccess('Financial Insights refreshed.'); await loadAll(); } else setError('Could not refresh Financial Insights.'); }

  const quickDefaults = (type) => {
    const defaults = ['recurring', 'bills'].includes(type) ? { account_id: null, card_id: null } : { account_id: type === 'planned' ? null : data.accounts[0]?.id || '', destination_account_id: data.accounts[0]?.id || '' };
    return { type, values: normaliseRecord(type, defaults) };
  };
  const openQuickAdd = (type) => { setQuickMenuOpen(false); setQuick(quickDefaults(type)); };
  const openForecastDetail = (event) => { const source = forecastSource(event, data); setDetail({ event, ...source }); };
  const editForecastSource = () => { if (!detail?.type || !detail?.record) return; const { type, record } = detail; setDetail(null); setEdit({ type, label: recordLabels[type], row: record, values: normaliseRecord(type, record) }); };
  const navigate = (item) => { setError(''); setSuccess(''); setActive(item); if (isMobile) { setMobileNavOpen(false); window.requestAnimationFrame(() => window.scrollTo({ top: 0, left: 0, behavior: 'auto' })); } };
  const closeMobileNav = (restoreFocus = true) => { setMobileNavOpen(false); if (restoreFocus) window.requestAnimationFrame(() => menuButtonRef.current?.focus({ preventScroll: true })); };

  if (!auth) return <main className="login"><div className="login-card"><img className="login-logo" src={logo} alt="Fynvo"/><p>Loading...</p></div></main>;
  if (!auth.authenticated) return <main className="login"><form className="login-card" onSubmit={submitAuth}><img className="login-logo" src={logo} alt="Fynvo"/><p>Know what's coming.</p>{auth.setup_required && <p className="notice">Create the first administrator account.</p>}<Field label="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })}/>{auth.setup_required && <Field label="Display name" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })}/>}<Field label="Password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}/>{error && <p className="error">{error}</p>}<button className="primary">{auth.setup_required ? 'Create account' : 'Sign in'}</button></form></main>;

  return <div className={`shell ${mobileNavOpen ? 'mobile-nav-open' : ''}`}>
    <aside className="sidebar" id="fynvo-navigation" aria-label="Fynvo navigation" aria-hidden={isMobile && !mobileNavOpen ? 'true' : undefined} inert={isMobile && !mobileNavOpen ? true : undefined}>
      <button ref={closeButtonRef} className="mobile-nav-close" type="button" aria-label="Close Fynvo navigation" onClick={() => closeMobileNav()}>×</button>
      <div className="brand"><img src={mark} alt=""/><div><strong>Fynvo</strong><small>Know what's coming.</small></div></div>
      <nav aria-label="Primary navigation">{navGroups.map((group) => <div className="nav-group" key={group.label}><small>{group.label}</small>{group.items.map((item) => <button key={item} className={active === item ? 'active' : ''} aria-current={active === item ? 'page' : undefined} onClick={() => navigate(item)}>{item}</button>)}</div>)}</nav>
      <button className="sidebar-logout" type="button" onClick={logout}>Logout</button>
      <div className="user-card"><span>{(auth.user?.display_name || 'SP').slice(0, 2).toUpperCase()}</span><div><strong>{auth.user?.display_name}</strong><small>Household</small></div></div>
    </aside>
    <button className="mobile-nav-backdrop" type="button" aria-label="Close Fynvo navigation" tabIndex={mobileNavOpen ? 0 : -1} onClick={() => closeMobileNav()}></button>
    <main className="content">
      <div className="mobile-app-bar" aria-label="Fynvo application controls"><button ref={menuButtonRef} className="mobile-menu-button" type="button" aria-label={mobileNavOpen ? 'Close Fynvo navigation' : 'Open Fynvo navigation'} aria-expanded={mobileNavOpen} aria-controls="fynvo-navigation" onClick={() => setMobileNavOpen((open) => !open)}><span aria-hidden="true">☰</span><span className="sr-only">Menu</span></button><strong className="mobile-app-identity">Fynvo</strong></div>
      <header className="header"><div><h1>{active === 'Overview' ? `${greeting}, ${auth.user?.display_name || 'there'}! 👋` : active}</h1><p>{active === 'Overview' ? "Here's your financial overview and what's ahead." : active === 'Insights' ? 'Understand what is changing, why it matters and which data supports it.' : active === 'Payment Centre' ? 'Manage household obligations, payment status and actions.' : 'Manage household financial records and planning.'}</p></div><div className="header-actions"><label className="select-shell">Date range<select value={rangeDays} onChange={(e) => setRangeDays(Number(e.target.value))}>{horizonOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label><button className="primary ghost" onClick={() => setQuickMenuOpen(true)}>+ Quick Add</button></div></header>{error && <p className="error banner">{error}</p>}{success && <p className="success banner">{success}</p>}
      {active === 'Overview' && <Overview data={data} setActive={navigate} rangeDays={rangeDays} setQuick={setQuick} quickDefaults={quickDefaults}/>} 
      {active === 'Payment Centre' && <PaymentCentreV112 data={data} onNavigate={navigate} onRefreshSupporting={loadAll} onEditBill={(row) => setEdit({ type: 'bills', label: 'Bill', row, values: normaliseRecord('bills', row) })}/>} 
      {active === 'Cash Flow' && <ForecastPage forecast={data.command?.forecast?.expected || data.forecast} onView={openForecastDetail}/>} 
      {active === 'Calendar' && <CalendarPage command={data.command}/>} 
      {active === 'CSV Import' && <CsvImport state={importState} setState={setImportState} accounts={data.accounts} previewImport={previewImport} commitImport={commitImport}/>} 
      {active === 'Import History' && <ImportHistory rows={data.imports}/>} 
      {active === 'Review Queue' && <><ReviewQueue rows={data.review} acceptMatch={acceptMatch}/><PaymentReconciliationV17 money={money} dateLabel={dateLabel}/></>} 
      {active === 'Spending Intelligence' && <SpendingIntelligence suggestions={data.suggestions} onDismiss={dismissSuggestion}/>} 
      {active === 'Insights' && <InsightsPage insights={data.insights} health={data.financialHealth || data.command?.financial_health} onDismiss={dismissInsight} onReviewed={reviewInsight} onNavigate={navigate} onRefresh={refreshInsights}/>} 
      {active === 'Budgeting' && <Budgeting budgets={data.budgets} analysis={data.budgetAnalysis} onEdit={(row) => setEdit({ type: 'budgets', label: 'Budget', row, values: normaliseRecord('budgets', row) })}/>} 
      {active === 'Goals' && <GoalsPage goals={data.goals} accounts={data.accounts} onEdit={(row) => setEdit({ type: 'goals', label: 'Goal', row, values: normaliseRecord('goals', row) })} onAdd={() => setQuick(quickDefaults('goals'))} onComplete={completeGoal}/>} 
      {active === 'Categories' && <CategoriesPageV0174 rangeDays={rangeDays} onEdit={setEdit} money={money}/>} 
      {active === 'Recurring Expenses' && <RecurringExpensesPageV0174 data={data} rangeDays={rangeDays} onEdit={setEdit} money={money} dateLabel={dateLabel} normaliseRecord={normaliseRecord}/>} 
      {active === 'Accounts' && <AccountsPageV14 rows={data.accounts} cards={data.cards} onEdit={setEdit} onAdd={() => setQuick(quickDefaults('accounts'))} onOpenCards={() => navigate('Cards')} money={money} normaliseRecord={normaliseRecord}/>} 
      {active === 'Cards' && <CardsPageV17 accounts={data.accounts} cards={data.cards} onRefresh={refreshCards}/>} 
      {active === 'Income' && <IncomePageV14 rows={data.income} onEdit={setEdit} onAdd={() => setQuick(quickDefaults('income'))} money={money} dateLabel={dateLabel} normaliseRecord={normaliseRecord}/>} 
      {active === 'Bills' && <BillsPageV14 rows={data.bills} onEdit={setEdit} onAdd={() => setQuick(quickDefaults('bills'))} money={money} dateLabel={dateLabel} normaliseRecord={normaliseRecord}/>} 
      {active === 'Planned Spending' && <PlannedSpendingPageV14 rows={data.planned} onEdit={setEdit} onAdd={() => setQuick(quickDefaults('planned'))} money={money} dateLabel={dateLabel} normaliseRecord={normaliseRecord}/>} 
      {active === 'Transactions' && <TransactionWorkspace accounts={data.accounts} categories={data.categories} money={money} dateLabel={dateLabel} refreshKey={data.transactions}/>} 
      <footer className="app-footer">Fynvo v{APP_VERSION}</footer>
    </main>
    {edit && <EditModal edit={edit} setEdit={setEdit} onSubmit={saveEdit} data={data}/>} 
    {quick && <EditModal edit={{ ...quick, row: { id: null }, label: `New ${recordLabels[quick.type] || 'Record'}` }} setEdit={setQuick} onSubmit={(e) => { e.preventDefault(); createRecord(quick.type, quick.values); }} data={data}/>} 
    {quickMenuOpen && <QuickAddModal onClose={() => setQuickMenuOpen(false)} onChoose={openQuickAdd}/>} 
    {detail && <ForecastDetailModal detail={detail} data={data} onClose={() => setDetail(null)} onEdit={editForecastSource}/>} 
  </div>;
}

function Overview({ data, setActive, rangeDays, setQuick, quickDefaults }) {
  const command = data.command || {};
  const kpis = command.kpis || {};
  const forecast = command.forecast?.baseline;
  const expected = command.forecast?.expected;
  const events = expected?.events || forecast?.events || [];
  const planned = command.top_planned_spending || data.planned || [];
  const paymentCentreOverview = data.paymentCentreOverview || {};
  const paymentRows = paymentCentreOverview.rows || [];
  const actionable = paymentRows.filter((row) => row.requires_action || row.match_review_available).slice(0, 6);
  const upcoming = paymentRows.filter((row) => !['paid', 'skipped', 'cancelled'].includes(row.status)).slice(0, 7);
  const health = data.financialHealth || command.financial_health || {};
  const attentionCount = Number(actionable.length || health.issue_count || health.attention_count || 0);
  const baselineEnd = forecast?.final_balance ?? forecast?.end_balance ?? forecast?.ending_balance;
  const expectedEnd = expected?.final_balance ?? expected?.end_balance ?? expected?.ending_balance;
  const lowestRecord = expected?.lowest_balance ?? forecast?.lowest_balance;
  const lowest = lowestRecord && typeof lowestRecord === 'object' ? (lowestRecord.balance ?? lowestRecord.amount ?? lowestRecord.value) : lowestRecord;
  const nextIncome = events.find((row) => row.direction === 'income');
  const totalBalance = finiteNumber(kpis.total_balance ?? kpis.available_cash ?? forecast?.starting_balance ?? expected?.starting_balance);
  const nextIncomeAmount = finiteNumber(kpis.next_income?.amount ?? nextIncome?.amount);
  const nextIncomeName = kpis.next_income?.name ?? nextIncome?.name;
  const nextIncomeDate = kpis.next_income?.date ?? nextIncome?.date;
  const commitmentsTotal = finiteNumber(paymentCentreOverview.summary?.total_scheduled?.amount ?? kpis.next_bills_total ?? kpis.scheduled_commitments ?? command.upcoming_commitments_summary?.total);
  const commitmentsCount = Number(paymentCentreOverview.summary?.total_scheduled?.count ?? kpis.next_bills_count ?? command.upcoming_commitments?.length ?? 0);
  const dueWithin = (days) => paymentRows.filter((row) => {
    if (['paid', 'skipped', 'cancelled'].includes(row.status)) return false;
    const raw = row.expected_date || row.due_date;
    if (!raw) return false;
    const delta = Math.ceil((new Date(`${raw}T00:00:00`) - new Date(`${today}T00:00:00`)) / 86400000);
    return delta >= 0 && delta <= days;
  });
  const totalFor = (rows) => rows.reduce((sum, row) => sum + Math.abs(finiteNumber(row.expected_amount ?? row.amount) || 0), 0);
  const next7 = dueWithin(7);
  const next30 = dueWithin(30);
  const manual30 = next30.filter((row) => row.payment_handling !== 'automatic');
  const automatic30 = next30.filter((row) => row.payment_handling === 'automatic');
  return <div className="dashboard-page">
    <section className="kpi-grid five"><Kpi icon="💵" label="Total Balance" value={money(totalBalance)} sub={`${data.accounts.length} accounts`}/><Kpi icon="📈" label="Next Income" value={money(nextIncomeAmount)} sub={nextIncomeDate ? `${nextIncomeName || 'Income'} · ${dateLabel(nextIncomeDate)}` : 'No scheduled income'}/><Kpi icon="🧾" label="Next Bills" value={money(commitmentsTotal)} sub={`${commitmentsCount} commitments in range`}/><Kpi icon="💸" label="Discretionary" value={money(kpis.discretionary_spend)} sub={`Next ${rangeDays} days`}/><Kpi icon="🏁" label="Goals" value={`${kpis.active_goal_count || 0} active`} sub={kpis.next_goal ? `Next: ${kpis.next_goal.name}` : 'No target dates'}/></section>
    <section className="dashboard-secondary-row">
      <article className="panel dashboard-compact-panel"><div className="panel-head compact"><h2>Top Planned Spending</h2><button type="button" className="link-button" onClick={() => setQuick(quickDefaults('planned'))}>+ Quick Add</button></div>{planned.length ? planned.slice(0, 3).map((row) => <div className="list-row" key={`planned-${row.id || row.source_id}`}><span>{row.name}<small>{row.date || row.planned_date ? dateLabel(row.date || row.planned_date) : 'No date'}</small></span><strong>{money(row.amount || row.estimated_amount)}</strong></div>) : <Empty title="No planned spending">No planned purchases during this period.</Empty>}</article>
      <article className="panel dashboard-compact-panel"><div className="panel-head compact"><h2>Payments</h2><button type="button" className="link-button" onClick={() => setActive('Payment Centre')}>View All Payments →</button></div><strong className="dashboard-health-number">{attentionCount} item{attentionCount === 1 ? '' : 's'} need attention</strong>{actionable.length ? actionable.slice(0, 3).map((row) => <div className="list-row" key={`attention-${row.source_type}-${row.id}`}><span>{row.name}<small>{row.status === 'overdue' && row.days_overdue ? `${row.days_overdue} days overdue` : row.status === 'auto_payment_unconfirmed' ? 'Automatic payment not confirmed' : row.match_review_available ? 'Possible transaction match' : 'Requires action'}</small></span><strong>{money(row.expected_amount ?? row.amount) || 'Not set'}</strong></div>) : <p className="muted">Nothing needs your attention right now.</p>}</article>
      <article className="panel dashboard-compact-panel dashboard-forecast-summary"><PanelHead title="Money Needed Soon" meta="Upcoming household payments"/><div className="list-row"><span>Next 7 days</span><strong>{money(totalFor(next7))}</strong></div><div className="list-row"><span>Next 30 days</span><strong>{money(totalFor(next30))}</strong></div><div className="list-row"><span>Manual payments</span><strong>{money(totalFor(manual30))}</strong></div><div className="list-row"><span>Automatic payments</span><strong>{money(totalFor(automatic30))}</strong></div><button type="button" className="link-button" onClick={() => setActive('Payment Centre')}>View All Payments →</button></article>
    </section>
    <section className="dashboard-main-row"><article className="panel dashboard-forecast-panel"><div className="panel-head compact"><h2>Cash Flow Forecast</h2><button type="button" className="link-button" onClick={() => setActive('Cash Flow')}>View full cash flow →</button></div><CashFlowChartV0174 baseline={forecast} expected={expected} dateLabel={dateLabel} Empty={Empty}/></article><div className="dashboard-side-stack"><article className="panel dashboard-compact-panel"><div className="panel-head compact"><h2>Upcoming Commitments</h2><button type="button" className="link-button" onClick={() => setActive('Payment Centre')}>Open Payment Centre →</button></div>{upcoming.length ? upcoming.map((row) => <div className="list-row" key={`upcoming-${row.source_type}-${row.id}`}><span>{row.name}<small>{dateLabel(row.expected_date || row.due_date)} · {row.payment_handling === 'automatic' ? 'Automatic' : 'Manual'}</small></span><strong>{money(row.expected_amount ?? row.amount) || 'Not set'}</strong></div>) : <Empty title="No upcoming payments">No payment obligations are scheduled in the next 30 days.</Empty>}</article></div></section>
  </div>;
}

// Existing components below are intentionally preserved from the established application shell.
function Kpi({ icon, label, value, sub }) { return <article className="kpi"><span className="kpi-icon">{icon}</span><div><small>{label}</small><strong>{value || '—'}</strong><span>{sub}</span></div></article>; }
function PanelHead({ title, meta }) { return <div className="panel-head compact"><h2>{title}</h2>{meta && <span>{meta}</span>}</div>; }
function ForecastPage({ forecast, onView }) { if (!forecast) return <Empty title="No forecast available">Add accounts and scheduled financial events to build a forecast.</Empty>; const events = forecast.events || []; return <section className="panel"><PanelHead title="Cash Flow" meta="Expected mode"/><CashFlowChartV0174 baseline={forecast} expected={forecast} dateLabel={dateLabel} Empty={Empty}/>{events.map((row, index) => <button type="button" className="list-row" key={`${row.source_type}-${row.source_id}-${index}`} onClick={() => onView(row)}><span>{row.name}<small>{dateLabel(row.date)}</small></span><strong className={amountClass(row.amount)}>{money(row.amount)}</strong></button>)}</section>; }
function CalendarPage({ command }) { const rows = command?.upcoming_commitments || command?.forecast?.expected?.events || []; return <section className="panel"><PanelHead title="Financial Calendar" meta={`${rows.length} events`}/>{rows.length ? rows.map((row, index) => <div className="list-row" key={`${row.kind || row.source_type}-${row.id || row.source_id}-${index}`}><span>{row.name}<small>{dateLabel(row.date || row.expected_date)}</small></span><strong>{money(row.amount || row.expected_amount)}</strong></div>) : <Empty title="No calendar events">No upcoming financial events are available.</Empty>}</section>; }
function CsvImport() { return <section className="panel"><h2>CSV Import</h2><p>Import Review is for transaction data quality and reconciliation.</p></section>; }
function ImportHistory({ rows }) { return <section className="panel"><PanelHead title="Import History" meta={`${rows.length} imports`}/></section>; }
function ReviewQueue({ rows }) { return <section className="panel"><PanelHead title="Payment Review" meta={`${rows.length} items`}/></section>; }
function Budgeting() { return <section className="panel"><h2>Budgeting</h2></section>; }
function GoalsPage() { return <section className="panel"><h2>Goals</h2></section>; }
function EditModal() { return null; }
function QuickAddModal() { return null; }
function ForecastDetailModal() { return null; }
