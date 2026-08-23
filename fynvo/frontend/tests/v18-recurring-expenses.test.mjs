import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';

const page = fs.readFileSync(new URL('../src/RecurringExpensesPage.jsx', import.meta.url), 'utf8');
const shim = fs.readFileSync(new URL('../src/RecurringExpensesPageV151.jsx', import.meta.url), 'utf8');
const css = fs.readFileSync(new URL('../src/recurring-v18.css', import.meta.url), 'utf8');

const has = (value, message) => assert.ok(page.includes(value), message || `Expected RecurringExpensesPage.jsx to contain ${value}`);

test('v1.8 uses Scheduled Payments as the authoritative list, calendar and summary pipeline', () => {
  has('data.scheduledPayments');
  has('enrichScheduledPayments');
  has('filterScheduledPayments');
  has('sortScheduledPayments');
  has('summarisePayments');
  assert.doesNotMatch(page, /RecurringExpensesPageV180/);
  assert.match(shim, /RecurringExpensesPage from '\.\/RecurringExpensesPage\.jsx'/);
});

test('v1.8 filters cover household-facing search and real payment fields', () => {
  for (const text of ['Search expenses...', 'Next {d} days', 'All frequencies', 'All categories', 'All payment methods', 'All statuses', 'Show overdue only', 'Show payments requiring attention']) has(text);
  for (const searchable of ['row.name', 'row.category', 'row.merchant', 'row.displaySource', 'row.linkedAccountName']) has(searchable);
  has('activeFilterCount(filters)');
  has("Number(filters.paymentMethod !== 'all')");
  has("Number(filters.paymentStatus !== 'all')");
});

test('mobile filters use draft state and explicit Apply/Clear semantics', () => {
  has('const [draft, setDraft] = useState(applied)');
  has('setDraft(applied)');
  has('Apply filters');
  has('Clear filters');
  has('aria-modal="true"');
  has("event.key === 'Tab'");
  has("event.key === 'Escape'");
  assert.match(css, /env\(safe-area-inset-bottom\)/);
});

test('summary totals, next payment, breakdown, largest expense and status totals share filtered payments', () => {
  has('const summary = useMemo(() => summarisePayments(filtered), [filtered])');
  has('Scheduled total');
  has('Next payment');
  has('Breakdown by period');
  has('Largest upcoming expense');
  has('Expected automatically');
  has('Requires payment');
  has('Overdue / Needs attention');
  has('Status categories above are mutually exclusive');
  has('aria-expanded={expanded}');
});

test('list supports grouping, real status/source display and state-aware actions', () => {
  for (const group of ['OVERDUE', 'TODAY', 'TOMORROW', 'IN 3 DAYS', 'IN 7 DAYS', 'LATER']) has(group);
  for (const field of ['next_due_date', 'name', 'amount', 'frequency', 'status']) has(`value=\"${field}\"`);
  has('Linked to account:');
  has('Matched to transaction');
  has('Mark as paid');
  has('Review payment');
  has('Review match');
  has('Skip payment');
  has('/mark-paid');
  has('/skip');
});

test('calendar is functional, month-scoped and preserves list relative range state', () => {
  has("viewMode === 'list' ?");
  has("<CalendarView allRows={rows}");
  has('Previous month');
  has('Next month');
  has("temporalScope === 'month'");
  has('Calendar month is the temporal scope; List keeps your relative date range.');
  has("['MON','TUE','WED','THU','FRI','SAT','SUN']");
  has('+{items.length - 2} more');
  has('selectedRows');
  has('Payment status legend');
  has("selected ? dateLabel(selected) : 'Upcoming'");
});

test('payment lifecycle presentation uses v1.7 statuses and matched transaction evidence', () => {
  for (const status of ['expected_automatically', 'auto_payment_unconfirmed', 'paid', 'overdue', 'due', 'skipped', 'cancelled']) has(status);
  has('payment.matched_transaction_id');
  has('payment.actual_date');
  has('payment.actual_amount');
  has("payment.payment_method === 'automatic_card_payment'");
});

test('responsive styles prevent normal mobile horizontal tables and provide touch-friendly controls', () => {
  assert.match(css, /@media\(max-width:980px\)/);
  assert.match(css, /overflow-x:hidden/);
  assert.match(css, /\.recurring-v18-table\{display:none\}/);
  assert.match(css, /\.recurring-v18-mobile-list\{display:grid/);
  assert.match(css, /width:44px;height:44px/);
  assert.match(css, /grid-template-columns:repeat\(7,minmax\(0,1fr\)\)/);
});
