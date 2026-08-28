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
import { CardsPageV17, PaymentReconciliationV17, PaymentsAttentionV17, RecurringPaymentFieldsV17, recurringV17Values } from './PaymentManagementV17.jsx';
import { apiRequest } from './apiClient.js';
import './styles.css';

const api = (path, options = {}) => fetch(`api${path}`, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
const today = new Date().toISOString().slice(0, 10);
const APP_VERSION = '1.15.0';
const ATTENTION_STATUSES = new Set(['overdue', 'due', 'due_today', 'auto_payment_unconfirmed', 'unknown']);
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
  if (type === 'goals') return { name: row.name || '', description: row.description || '', goal_type: row.goal_type || 'savings', target_amount: row.target_amount || '', current_amount: row.current_amount || '', start_date: toDateInput(row.start_date) || today, target_date: toDateInput(row.target_date), priority: row.priority || 'medium', contribution_frequency: row.contribution_frequency || 'monthly', contribution_amount: row.contribution_amount || '', status: row.status || 'active', notes: row.notes || '', effective_from: '' };
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
  const [data, setData] = useState({ accounts: [], cards: [], transactions: [], income: [], recurring: [], scheduledPayments: [], paymentAttention: [], bills: [], planned: [], categories: [], expenseTypes: [], budgets: [], goals: [], imports: [], review: [], suggestions: [], insights: [], financialHealth: null, budgetAnalysis: null, forecast: null, command: null, paymentCentreOverview: null });
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [error, setError] = useState(''); const [success, setSuccess] = useState(''); const [edit, setEdit] = useState(null); const [quick, setQuick] = useState(null); const [quickMenuOpen, setQuickMenuOpen] = useState(false); const [detail, setDetail] = useState(null); const [greeting, setGreeting] = useState(() => greetingForNow()); const [mobileNavOpen, setMobileNavOpen] = useState(false); const [isMobile, setIsMobile] = useState(() => window.matchMedia('(max-width: 980px)').matches);
  const menuButtonRef = useRef(null); const closeButtonRef = useRef(null); const commandRequestRef = useRef(0); const initialLoadedRef = useRef(false);
  const [importState, setImportState] = useState({ filename: '', account_id: '', csv_text: '', source_name: 'Australian bank CSV', mapping: { date: 'Date', description: 'Description', debit: 'Debit', credit: 'Credit', amount: 'Amount' }, preview: null });

  async function loadAuth() { const res = await api('/auth/state'); setAuth(await res.json()); }
  async function j(path) { try { return await apiRequest(path); } catch { return null; } }
  async function refreshDashboard(days = rangeDays) { const requestId = ++commandRequestRef.current; setDashboardLoading(true); try { const command = await j(`/dashboard/command-centre?range_days=${days}`); if (requestId !== commandRequestRef.current) return; setData((current) => ({ ...current, command })); } finally { if (requestId === commandRequestRef.current) setDashboardLoading(false); } }
  async function loadSupportingData() {
    const scheduledRequest = active === 'Overview' ? j('/scheduled-payments') : Promise.resolve(null);
    const paymentCentreRequest = active === 'Overview' ? j('/payment-centre?date_range=next_30_days') : Promise.resolve(null);
    const [accounts, cards, transactions, income, recurring, scheduledPayments, bills, planned, categories, referenceData, budgets, goals, imports, review, suggestions, insights, financialHealth, budgetAnalysis, forecast, paymentCentreOverview] = await Promise.all([
      j('/accounts'), j('/cards?include_inactive=true'), j('/transactions'), j('/income'), j('/recurring-expenses'), scheduledRequest, j('/bills'), j('/planned-spending'), j('/categories'), j('/reference-data'), j('/budgets'), j('/goals'), j('/imports/history'), j('/reconciliation/review-queue'), j('/intelligence/suggestions'), j(`/insights?horizon_days=${rangeDays}&refresh=false`), j(`/insights/financial-health?horizon_days=${rangeDays}`), j('/budgets/analysis'), j(`/forecast?mode=expected&horizon=${rangeDays}d`), paymentCentreRequest,
    ]);
    setData((current) => {
      const resolvedScheduled = scheduledPayments === null ? current.scheduledPayments : scheduledPayments || [];
      const derivedAttention = paymentCentreOverview?.rows?.filter((row) => row.requires_action || ATTENTION_STATUSES.has(row.status)) || (scheduledPayments === null ? current.paymentAttention : resolvedScheduled.filter((row) => ATTENTION_STATUSES.has(row.status)));
      return { ...current, accounts: accounts || [], cards: cards || [], transactions: transactions || [], income: income || [], recurring: recurring || [], scheduledPayments: resolvedScheduled, paymentAttention: derivedAttention, bills: bills || [], planned: planned || [], categories: categories || [], expenseTypes: referenceData?.expense_types || [], budgets: budgets || [], goals: goals || [], imports: imports || [], review: review || [], suggestions: suggestions || [], insights: insights || [], financialHealth, budgetAnalysis, forecast, paymentCentreOverview };
    });
  }

  useEffect(() => { loadAuth(); }, []);
  useEffect(() => { if (auth?.authenticated) { loadSupportingData(); refreshDashboard(); } }, [auth?.authenticated]);
  useEffect(() => { localStorage.setItem('fynvo.view', active); setMobileNavOpen(false); }, [active]);
  useEffect(() => { localStorage.setItem('fynvo.rangeDays', String(rangeDays)); if (auth?.authenticated) refreshDashboard(rangeDays); }, [rangeDays]);
  useEffect(() => { const interval = window.setInterval(() => setGreeting(greetingForNow()), 60_000); return () => window.clearInterval(interval); }, []);
  useEffect(() => { const media = window.matchMedia('(max-width: 980px)'); const update = () => setIsMobile(media.matches); update(); media.addEventListener('change', update); return () => media.removeEventListener('change', update); }, []);

  async function submitAuth(event) { event.preventDefault(); const endpoint = auth?.setup_required ? '/auth/setup' : '/auth/login'; const response = await api(endpoint, { method: 'POST', body: JSON.stringify(form) }); const payload = await response.json().catch(() => ({})); if (!response.ok) { setError(friendlyError(payload, 'Sign in failed.')); return; } setError(''); await loadAuth(); }
  async function logout() { await api('/auth/logout', { method: 'POST' }); setAuth({ authenticated: false, setup_required: false }); }
  async function saveRecord(type, values, id = null) { const endpoint = id ? endpointFor(type, id) : createPath(type); const response = await api(endpoint, { method: id ? 'PUT' : 'POST', body: JSON.stringify(normaliseMutationValues(type, values)) }); const payload = await response.json().catch(() => ({})); if (!response.ok) throw new Error(friendlyError(payload, `Could not save ${recordLabels[type]}.`)); setSuccess(`${recordLabels[type]} saved.`); setError(''); setEdit(null); setQuick(null); await loadSupportingData(); await refreshDashboard(); return payload; }
  async function removeRecord(type, id) { const response = await api(endpointFor(type, id), { method: 'DELETE' }); const payload = await response.json().catch(() => ({})); if (!response.ok) { setError(friendlyError(payload, `Could not delete ${recordLabels[type]}.`)); return; } setSuccess(`${recordLabels[type]} deleted.`); setEdit(null); await loadSupportingData(); await refreshDashboard(); }

  if (!auth) return <div className="splash"><img src={logo} alt="Fynvo"/><p>Loading Fynvo…</p></div>;
  if (!auth.authenticated) return <main className="auth-shell"><form className="auth-card" onSubmit={submitAuth}><img src={logo} alt="Fynvo"/><h1>{auth.setup_required ? 'Create your Fynvo account' : 'Welcome back'}</h1><p>{auth.setup_required ? 'Set up the administrator account for this Fynvo household.' : 'Sign in to continue.'}</p><Field label="Username"><input autoComplete="username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })}/></Field>{auth.setup_required && <Field label="Display name"><input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })}/></Field>}<Field label="Password"><input type="password" autoComplete={auth.setup_required ? 'new-password' : 'current-password'} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}/></Field>{error && <p className="error">{error}</p>}<button className="primary" type="submit">{auth.setup_required ? 'Create account' : 'Sign in'}</button></form></main>;

  const render = () => {
    if (active === 'Overview') return <OverviewPage data={data} rangeDays={rangeDays} setRangeDays={setRangeDays} money={money} dateLabel={dateLabel} dashboardLoading={dashboardLoading} onNavigate={setActive} onEdit={(type, record) => setEdit({ type, record })} onRefresh={async () => { await loadSupportingData(); await refreshDashboard(); }}/>} ;
    if (active === 'Payment Centre') return <PaymentCentreV112 data={data} onNavigate={setActive} onRefreshSupporting={async () => { await loadSupportingData(); await refreshDashboard(); }} onEditBill={(row) => setEdit({ type: 'bills', record: row })} onOpenRecurring={(row) => { const recurring = data.recurring.find((item) => Number(item.id) === Number(row.recurring_expense_id)); if (recurring) setEdit({ type: 'recurring', record: recurring }); else setActive('Recurring Expenses'); }}/>} ;
    if (active === 'Cash Flow') return <CashFlowPage data={data} rangeDays={rangeDays} setRangeDays={setRangeDays} money={money} dateLabel={dateLabel} onEdit={(type, record) => setEdit({ type, record })}/>;
    if (active === 'Calendar') return <CalendarPage data={data} money={money} dateLabel={dateLabel} onEdit={(type, record) => setEdit({ type, record })}/>;
    if (active === 'Accounts') return <AccountsPageV14 data={data} money={money} onRefresh={loadSupportingData} onEdit={(row) => setEdit({ type: 'accounts', record: row })} onAdd={() => setQuick({ type: 'accounts', values: normaliseRecord('accounts') })}/>;
    if (active === 'Cards') return <CardsPageV17 accounts={data.accounts} cards={data.cards} onRefresh={loadSupportingData}/>;
    if (active === 'Transactions') return <TransactionWorkspace data={data} money={money} dateLabel={dateLabel} onRefresh={async () => { await loadSupportingData(); await refreshDashboard(); }} onEdit={(row) => setEdit({ type: 'transactions', record: row })} onAdd={() => setQuick({ type: 'transactions', values: normaliseRecord('transactions') })}/>;
    if (active === 'Income') return <IncomePageV14 data={data} money={money} dateLabel={dateLabel} onEdit={(row) => setEdit({ type: 'income', record: row })} onAdd={() => setQuick({ type: 'income', values: normaliseRecord('income') })}/>;
    if (active === 'Bills') return <BillsPageV14 data={data} money={money} dateLabel={dateLabel} onEdit={(row) => setEdit({ type: 'bills', record: row })} onAdd={() => setQuick({ type: 'bills', values: normaliseRecord('bills') })}/>;
    if (active === 'Recurring Expenses') return <RecurringExpensesPageV0174 data={data} money={money} dateLabel={dateLabel} onEdit={(row) => setEdit({ type: 'recurring', record: row })} onAdd={() => setQuick({ type: 'recurring', values: normaliseRecord('recurring') })}/>;
    if (active === 'Planned Spending') return <PlannedSpendingPageV14 data={data} money={money} dateLabel={dateLabel} onEdit={(row) => setEdit({ type: 'planned', record: row })} onAdd={() => setQuick({ type: 'planned', values: normaliseRecord('planned') })}/>;
    if (active === 'Budgeting') return <BudgetingPage data={data} money={money} onEdit={(row) => setEdit({ type: 'budgets', record: row })} onAdd={() => setQuick({ type: 'budgets', values: normaliseRecord('budgets') })}/>;
    if (active === 'Goals') return <GoalsPage data={data} money={money} dateLabel={dateLabel} onEdit={(row) => setEdit({ type: 'goals', record: row })} onAdd={() => setQuick({ type: 'goals', values: normaliseRecord('goals') })}/>;
    if (active === 'Insights') return <InsightsPage data={data} money={money} dateLabel={dateLabel}/>;
    if (active === 'Spending Intelligence') return <SpendingIntelligence data={data} money={money} dateLabel={dateLabel}/>;
    if (active === 'CSV Import') return <CsvImportPage data={data} state={importState} setState={setImportState} onRefresh={loadSupportingData}/>;
    if (active === 'Import History') return <ImportHistoryPage data={data} dateLabel={dateLabel}/>;
    if (active === 'Review Queue') return <PaymentReconciliationV17 money={money} dateLabel={dateLabel}/>;
    if (active === 'Categories') return <CategoriesPageV0174 data={data} onEdit={(row) => setEdit({ type: 'categories', record: row })} onAdd={() => setQuick({ type: 'categories', values: normaliseRecord('categories') })}/>;
    return <Empty title="Coming soon">This section is not available.</Empty>;
  };

  return <div className="app-shell"><aside className={`sidebar ${mobileNavOpen ? 'mobile-open' : ''}`}><div className="brand"><img src={logo} alt="Fynvo"/><small>v{APP_VERSION}</small></div><nav>{navGroups.map((group) => <div className="nav-group" key={group.label}><span>{group.label}</span>{group.items.map((item) => <button key={item} className={active === item ? 'active' : ''} onClick={() => setActive(item)}>{item}</button>)}</div>)}</nav><button className="logout" onClick={logout}>Sign out</button></aside><main className="content"><header className="mobile-header"><button ref={menuButtonRef} aria-label="Open menu" onClick={() => setMobileNavOpen(true)}>☰</button><img src={mark} alt=""/><strong>Fynvo</strong></header>{mobileNavOpen && <button ref={closeButtonRef} className="mobile-nav-close" aria-label="Close menu" onClick={() => setMobileNavOpen(false)}>×</button>}{success && <div className="success-toast">{success}</div>}{error && <div className="error-toast">{error}</div>}{render()}</main>{quick && <RecordModal title={`Add ${recordLabels[quick.type]}`} type={quick.type} values={quick.values} data={data} onClose={() => setQuick(null)} onSave={(values) => saveRecord(quick.type, values)}/>} {edit && <RecordModal title={`Edit ${recordLabels[edit.type]}`} type={edit.type} values={normaliseRecord(edit.type, edit.record)} data={data} onClose={() => setEdit(null)} onSave={(values) => saveRecord(edit.type, values, edit.record.id)} onDelete={() => removeRecord(edit.type, edit.record.id)}/>}<button className="quick-add" onClick={() => setQuickMenuOpen(!quickMenuOpen)}>+</button>{quickMenuOpen && <div className="quick-menu">{quickAddOptions.map(([type, label, description]) => <button key={type} onClick={() => { setQuick({ type, values: normaliseRecord(type) }); setQuickMenuOpen(false); }}><strong>{label}</strong><small>{description}</small></button>)}</div>}</div>;
}

function OverviewPage({ data, rangeDays, setRangeDays, money, dateLabel, dashboardLoading, onNavigate, onEdit, onRefresh }) {
  const command = data.command;
  return <section className="page-grid"><header className="overview-head"><div><span>{greetingForNow()}</span><h1>Household overview</h1></div><label>Forecast horizon<select value={rangeDays} onChange={(e) => setRangeDays(Number(e.target.value))}>{horizonOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label></header>{dashboardLoading && !command ? <div className="panel">Loading dashboard…</div> : <><DashboardSummary command={command} money={money}/><PaymentsAttentionV17 rows={data.paymentAttention} money={money} dateLabel={dateLabel} onRefresh={onRefresh}/><CashFlowChartV0174 command={command} money={money}/></>} </section>;
}

function DashboardSummary({ command, money }) { const balances = command?.balances || {}; return <div className="summary-grid"><article className="panel"><small>Available cash</small><strong>{money(balances.available_cash) || '$0.00'}</strong></article><article className="panel"><small>Expected income</small><strong>{money(command?.forecast?.expected?.income) || '$0.00'}</strong></article><article className="panel"><small>Expected expenses</small><strong>{money(command?.forecast?.expected?.expenses) || '$0.00'}</strong></article></div>; }

function CashFlowPage() { return <section className="panel"><h1>Cash Flow</h1><p className="muted">Cash Flow uses the canonical forecast and Scheduled Payment events.</p></section>; }
function CalendarPage() { return <section className="panel"><h1>Calendar</h1><p className="muted">Calendar uses the canonical financial-event schedule.</p></section>; }
function BudgetingPage() { return <section className="panel"><h1>Budgeting</h1></section>; }
function GoalsPage() { return <section className="panel"><h1>Goals</h1></section>; }
function CsvImportPage() { return <section className="panel"><h1>CSV Import</h1></section>; }
function ImportHistoryPage() { return <section className="panel"><h1>Import History</h1></section>; }
function RecordModal() { return null; }
