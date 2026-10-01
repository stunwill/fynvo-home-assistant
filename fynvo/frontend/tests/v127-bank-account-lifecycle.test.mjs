import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (file) => readFile(new URL(`../src/${file}`, import.meta.url), 'utf8');
const panel = await read('BankConnectionsPanel.jsx');
const accounts = await read('AccountsWorkspaceV1240.jsx');
const css = await read('bank-connections-v126.css');

test('bank account setup requires a reviewed choice and confirmation', () => {
  for (const label of ['Needs setup', 'Connected accounts', 'Ignored accounts', 'Needs attention', 'Link to existing Fynvo account', 'Create new Fynvo account', 'Ignore this bank account', 'Confirm link', 'Create and link account']) assert.ok(panel.includes(label), label);
  assert.match(panel, /choice === 'link' && !accountId/);
  assert.match(panel, /fynvo_account_id: Number\(accountId\)/);
  assert.match(panel, /\['link', 'create'\]\.includes\(payload\.action\)\) await sync\(item\.connection\)/);
  assert.match(panel, /role="dialog" aria-modal="true" aria-labelledby=/);
  assert.match(panel, /event\.key === 'Tab'/);
  assert.match(panel, /trigger\.current\?\.isConnected \? trigger\.current : backButton\.current\)\?\.focus\(\)/);
});

test('required actions integrate with Accounts and manual accounts remain valid', () => {
  assert.match(accounts, /required_actions/);
  assert.match(accounts, /Bank accounts needing attention/);
  assert.match(accounts, /fynvo:open-bank-connections/);
  assert.match(accounts, /Manual balance/);
  assert.match(accounts, /Bank balance/);
  assert.match(accounts, /TransactionWorkspace/);
});

test('bank account controls fit mobile ingress and preserve backend credentials', () => {
  assert.match(css, /max-width:430px/);
  assert.match(css, /safe-area-inset-bottom/);
  assert.match(css, /max-height:calc\(100dvh/);
  assert.match(panel, /apiRequest\('\/bank-connections\/redbark\/status'\)/);
  assert.doesNotMatch(panel, /localStorage.*apiKey|savedApiKey/i);
});
