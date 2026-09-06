import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const shell = await readFile(new URL('../src/AppV13.jsx', import.meta.url), 'utf8');
const wrapper = await readFile(new URL('../src/AppCorrectiveV1163.jsx', import.meta.url), 'utf8');


test('production shell passes authoritative auth state directly into the nested app', () => {
  assert.match(shell, /<App authState=\{auth\}\/>/);
  assert.match(wrapper, /<BaseApp authState=\{authState\}\/>/);
  assert.doesNotMatch(shell, /__fynvoSharedAuthState/);
  assert.doesNotMatch(wrapper, /__fynvoSharedAuthState/);
});


test('production startup no longer intercepts fetch or remounts the workspace', () => {
  assert.doesNotMatch(shell, /globalThis\.fetch\s*=/);
  assert.doesNotMatch(shell, /authStateResult/);
  assert.doesNotMatch(shell, /startupAttempt/);
  assert.doesNotMatch(shell, /Retry Fynvo/);
});


test('household security lookup cannot block the main Fynvo workspace', () => {
  assert.match(shell, /HOUSEHOLD_SECURITY_TIMEOUT_MS = 3500/);
  assert.match(shell, /controller\.abort\(\)/);
  assert.match(shell, /signal: controller\.signal/);
  assert.doesNotMatch(shell, /if \(!householdSecurity\) return/);
  assert.doesNotMatch(shell, /Loading Household identity/);
  assert.match(shell, /householdSecurity\?\.must_change_password/);
  assert.match(shell, /Fynvo has continued loading\. Retry the household security check when convenient\./);
});


test('v1.18.0 production shell exposes installed startup diagnostics', () => {
  assert.match(shell, /PRODUCTION_VERSION = '1\.18\.0'/);
  assert.match(shell, /publishStartup\('workspace-mounted'\)/);
  assert.match(shell, /publishStartup\('workspace-rendered', heading\)/);
});
