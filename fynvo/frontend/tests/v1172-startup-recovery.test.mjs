import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const shell = await readFile(new URL('../src/AppV13.jsx', import.meta.url), 'utf8');
const wrapper = await readFile(new URL('../src/AppCorrectiveV1163.jsx', import.meta.url), 'utf8');
const main = await readFile(new URL('../src/main.jsx', import.meta.url), 'utf8');
const css = await readFile(new URL('../src/startup-v1172.css', import.meta.url), 'utf8');


test('authenticated HA shell passes authoritative state directly through the wrapper chain', () => {
  assert.match(shell, /<App authState=\{auth\}\/>/);
  assert.match(wrapper, /<BaseApp authState=\{authState\}\/>/);
  assert.doesNotMatch(shell, /cacheAuthState/);
  assert.doesNotMatch(wrapper, /__fynvoSharedAuthState = authState/);
});


test('obsolete startup fetch interception remains removed', () => {
  assert.doesNotMatch(shell, /url\.endsWith\('\/api\/auth\/state'\)/);
  assert.doesNotMatch(shell, /authStateResult/);
  assert.doesNotMatch(shell, /globalThis\.fetch\s*=/);
  assert.doesNotMatch(shell, /new Response/);
});


test('production startup no longer remounts the workspace based on loading DOM', () => {
  assert.doesNotMatch(shell, /setStartupAttempt/);
  assert.doesNotMatch(shell, /startupAttempt/);
  assert.doesNotMatch(shell, /Retry Fynvo/);
  assert.match(shell, /publishStartup\('workspace-mounted'\)/);
  assert.match(shell, /publishStartup\('workspace-rendered', heading\)/);
});


test('v1.17.2 recovery presentation remains available and safe-area aware', () => {
  assert.match(main, /import '\.\/startup-v1172\.css';/);
  assert.match(css, /env\(safe-area-inset-bottom\)/);
  assert.match(css, /min-height: 44px/);
});
