import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../src/${path}`, import.meta.url), 'utf8');
const [panel, accounts, css, app] = await Promise.all([
  read('BankConnectionsPanel.jsx'), read('AccountsWorkspaceV1240.jsx'),
  read('bank-connections-v126.css'), read('AppV13.jsx'),
]);

test('same-institution connections remain separate cards with editable household context', () => {
  assert.match(panel, /state\.connections \|\| \[\]\)\.map\(\(connection\) => <section/);
  assert.match(panel, /key=\{connection\.id\}/);
  assert.match(panel, /item\.connection\.id === connection\.id/);
  assert.match(panel, /connection\.display_label \|\| connection\.institution_name/);
  assert.match(panel, /household_members/);
  assert.match(panel, /Edit label \/ owner/);
  assert.match(panel, /owner_user_id: connectionOwner/);
});

test('same-name bank accounts retain masked distinctions and require confirmed mapping', () => {
  assert.match(panel, /item\.masked_identifier/);
  assert.match(panel, /account\.account_suffix \|\| 'No suffix'/);
  assert.match(panel, /<option value="">Choose an account<\/option>/);
  assert.match(panel, /Confirm link/);
  assert.match(panel, /Start using in Fynvo/);
});

test('balance freshness does not use transaction or discovery timestamps', () => {
  assert.match(panel, /item\.balance_timestamp \? \x60\$\{money\(item\.current_balance\)\}/);
  assert.match(panel, /Balance unavailable · No bank balance received yet/);
  assert.match(panel, /Accounts discovered · No successful sync yet/);
  assert.match(panel, /Manual starting balance/);
  assert.match(accounts, /bankAccount\.balance_timestamp \? freshness\(bankAccount\.balance_timestamp\) : "Balance unavailable"/);
  assert.match(accounts, /Manual balance/);
});

test('narrow ingress layout retains account and context controls', () => {
  assert.match(css, /max-width:430px/);
  assert.match(css, /safe-area-inset-bottom/);
  assert.match(css, /overflow-wrap:anywhere/);
  assert.match(css, /min-height:44px/);
  assert.match(panel, /role="dialog" aria-modal="true"/);
  assert.match(app, /BankConnectionsPanel/);
});
