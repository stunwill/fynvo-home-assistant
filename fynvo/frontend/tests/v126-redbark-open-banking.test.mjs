import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const panel = await read('src/BankConnectionsPanel.jsx');
const shell = await read('src/AppV13.jsx');
const css = await read('src/bank-connections-v126.css');
const accounts = await read('src/AccountsWorkspaceV1240.jsx');
const activity = await read('src/TransactionWorkspace.jsx');
const activityCore = await read('src/TransactionWorkspaceCore.jsx');

test('Settings exposes Redbark Bank connections without leaking the saved credential', () => {
  assert.match(shell, /Settings · Bank connections/);
  assert.match(shell, /BankConnectionsPanel/);
  assert.match(panel, /type="password"/);
  assert.match(panel, /\/bank-connections\/redbark\/credentials/);
  assert.match(panel, /Test connection/);
  assert.match(panel, /Sync now/);
  assert.doesNotMatch(panel, /credential\.api_key|savedApiKey|localStorage.*api/i);
});

test('Bank connections supports explicit account mapping and safe disconnect', () => {
  assert.match(panel, /Create new Fynvo account/);
  assert.match(panel, /Ignore this bank account/);
  assert.match(panel, /Unlink from Fynvo/);
  assert.match(panel, /Existing Fynvo accounts and imported transaction history will be kept/);
  assert.match(panel, /history was preserved/i);
});

test('Bank connection UX exposes freshness, stale errors and backend automatic sync', () => {
  assert.match(panel, /Updated just now/);
  assert.match(panel, /Never synced/);
  assert.match(panel, /error_state/);
  assert.match(panel, /Automatic sync runs approximately every/);
  assert.match(panel, /Fynvo does not need to remain open/);
  assert.match(panel, /posted transactions only/);
});

test('Bank connection workspace protects supported mobile ingress widths and accessibility', () => {
  assert.match(css, /safe-area-inset-bottom/);
  assert.match(css, /max-width:430px/);
  assert.match(css, /overflow-wrap:anywhere/);
  assert.match(css, /prefers-reduced-motion/);
  assert.match(panel, /role="alert"/);
  assert.match(panel, /role="status"/);
});

test('Open Banking preserves Accounts and Activity authoritative workspaces', () => {
  assert.match(accounts, /TransactionWorkspace/);
  assert.match(activity, /TransactionWorkspaceCore/);
  assert.match(activityCore, /Search transactions/);
  assert.match(activityCore, /payments\/match-candidates/);
});
