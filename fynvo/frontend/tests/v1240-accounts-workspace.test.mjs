import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const accounts = await read('src/AccountsWorkspaceV1240.jsx');
const transactions = await read('src/TransactionWorkspace.jsx');
const css = await read('src/accounts-workspace-v1240.css');
const wrapper = await read('src/AppCorrectiveV1163.jsx');

test('Accounts has the approved Accounts, Activity and Cards information architecture', () => {
  for (const label of ['Total balance', 'Accounts', 'Activity', 'Cards', 'Manage accounts']) assert.match(accounts, new RegExp(label));
  assert.match(accounts, /fynvo\.accounts\.view\.v1240/);
  assert.match(accounts, /current_balance/);
  assert.match(accounts, /account_type/);
});

test('Account Detail preserves actual account activity, pending states and recurring links', () => {
  for (const label of ['Account details', 'Recent transactions', 'Pending transactions', 'Insights', 'Recurring from this account', 'View Activity', 'View all']) assert.match(accounts, new RegExp(label));
  assert.match(accounts, /status \|\| ''\)\.toLowerCase\(\) === 'pending'/);
  assert.match(accounts, /recurring\.filter/);
  assert.match(accounts, /apiRequest\('\/payments\/transactions\?limit=2000'/);
});

test('Activity keeps transaction search, filters and reconciliation workflows', () => {
  for (const label of ['Search transactions', 'Reconciliation filter', 'Confirm match', 'Not this payment', 'Remove match', 'Unmatched']) assert.match(transactions, new RegExp(label));
  assert.match(transactions, /accountId = null/);
  assert.match(transactions, /account: accountId == null/);
});

test('Cards and account editing use supported relative API contracts', () => {
  assert.match(accounts, /\/cards/);
  assert.match(accounts, /\/accounts\/\$\{account\.id\}/);
  assert.match(accounts, /Save Card/);
  assert.match(accounts, /Save Account/);
  assert.doesNotMatch(accounts, /Transfer/);
  assert.doesNotMatch(accounts, />Pay</);
});

test('Accounts mobile treatment protects ingress, values and required widths', () => {
  assert.match(css, /safe-area-inset-bottom/);
  assert.match(css, /overflow: auto/);
  assert.match(css, /overflow-wrap: anywhere/);
  for (const width of ['430px', '393px', '374px', '329px']) assert.match(css, new RegExp(`max-width: ${width}`));
  assert.match(wrapper, /AccountsWorkspaceV1240/);
  assert.match(wrapper, /mobileAccounts/);
});
