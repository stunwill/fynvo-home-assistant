import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../src/${path}`, import.meta.url), 'utf8');
const [panel, shell, accounts, activity, core, css] = await Promise.all([
  read('BankConnectionsPanel.jsx'), read('AppV13.jsx'), read('AccountsWorkspaceV1240.jsx'),
  read('TransactionWorkspace.jsx'), read('TransactionWorkspaceCore.jsx'), read('bank-connections-v126.css'),
]);

test('Accounts required action opens the precise unresolved bank account setup', () => {
  assert.match(accounts, /externalAccountId: action\.external_account_id/);
  assert.match(shell, /event\.detail\?\.externalAccountId/);
  assert.match(shell, /targetExternalAccountId=\{bankConnectionsTarget\}/);
  assert.match(panel, /row\.state === 'unresolved'/);
  assert.match(panel, /setSetup\(item\)/);
  assert.match(panel, /role="dialog" aria-modal="true"/);
  assert.match(panel, /backButton\.current\)\?\.focus\(\)/);
});

test('suggested mapping never preselects or silently links the account', () => {
  assert.match(panel, /comparable\(bank\.name\) === comparable\(account\.name\)/);
  assert.match(panel, /Suggested match:/);
  assert.match(panel, /setAccountId\(''\)/);
  assert.match(panel, /<option value="">Choose an account<\/option>/);
  assert.match(panel, /Confirm link/);
});

test('disconnected provider status does not masquerade as healthy current bank data', () => {
  assert.match(panel, /providerState = .*'Disconnected'/);
  assert.match(panel, /Reconnect Redbark/);
  assert.match(accounts, /Sync stopped/);
  assert.match(accounts, /Manual balance/);
  assert.match(css, /max-width:430px/);
  assert.match(css, /safe-area-inset-bottom/);
});

test('Accounts to Activity still uses protected adapter and full workspace', () => {
  assert.match(accounts, /view === "activity"/);
  assert.match(accounts, /<TransactionWorkspace/);
  assert.match(activity, /defaultMoney/);
  assert.match(activity, /defaultDateLabel/);
  assert.match(core, /Search transactions/);
  assert.match(core, /payments\/match-candidates/);
});
