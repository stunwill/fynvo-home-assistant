import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const shell = await readFile(new URL('../src/AppV13.jsx', import.meta.url), 'utf8');
const wrapper = await readFile(new URL('../src/AppCorrectiveV1163.jsx', import.meta.url), 'utf8');


test('production shell publishes authoritative auth state before the nested app starts', () => {
  assert.match(shell, /cacheAuthState\(auth\)/);
  assert.match(shell, /<App key=\{`fynvo-startup-\$\{startupAttempt\}`\} authState=\{auth\}\/>/);
  assert.match(wrapper, /globalThis\.__fynvoSharedAuthState = authState/);
});


test('auth bridge accepts relative and ingress-expanded auth-state URLs without constructing Response', () => {
  assert.match(shell, /url === 'api\/auth\/state' \|\| url\.endsWith\('\/api\/auth\/state'\)/);
  assert.match(shell, /Promise\.resolve\(authStateResult\(globalThis\.__fynvoSharedAuthState\)\)/);
  assert.doesNotMatch(shell, /new Response\(/);
});


test('outer shell no longer refreshes auth when the nested loading DOM appears', () => {
  assert.match(shell, /new MutationObserver\(syncProductionShell\)/);
  assert.doesNotMatch(shell, /document\.querySelector\('main\.login'\).*refreshAuth/);
});


test('stuck nested startup automatically retries and then exposes a manual recovery action', () => {
  assert.match(shell, /node\.textContent\?\.trim\(\) === 'Loading\.\.\.'/);
  assert.match(shell, /startupAttempt < 1/);
  assert.match(shell, /Fynvo could not finish starting inside Home Assistant\./);
  assert.match(shell, />Retry Fynvo</);
});


test('v1.17.2 production shell reports the corrective release version', () => {
  assert.match(shell, /PRODUCTION_VERSION = '1\.17\.2'/);
  assert.match(shell, /AUTH_BRIDGE_VERSION = '1\.17\.2'/);
});
