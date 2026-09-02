import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const shell = await readFile(new URL('../src/AppV13.jsx', import.meta.url), 'utf8');
const wrapper = await readFile(new URL('../src/AppCorrectiveV1163.jsx', import.meta.url), 'utf8');
const main = await readFile(new URL('../src/main.jsx', import.meta.url), 'utf8');
const css = await readFile(new URL('../src/startup-v1172.css', import.meta.url), 'utf8');


test('authenticated HA shell synchronously seeds nested startup state', () => {
  assert.match(shell, /cacheAuthState\(auth\);\n  return <>/);
  assert.match(shell, /authState=\{auth\}/);
  assert.match(wrapper, /if \(authState\) globalThis\.__fynvoSharedAuthState = authState/);
});


test('startup auth bridge is ingress path tolerant and response-constructor free', () => {
  assert.match(shell, /url\.endsWith\('\/api\/auth\/state'\)/);
  assert.match(shell, /json: async \(\) => state/);
  assert.doesNotMatch(shell, /new Response/);
});


test('nested loading cannot remain indefinite', () => {
  assert.match(shell, /3500/);
  assert.match(shell, /setStartupAttempt\(\(value\) => value \+ 1\)/);
  assert.match(shell, /Retry Fynvo/);
  assert.match(shell, /role="alert"/);
});


test('v1.17.2 recovery presentation is loaded last and safe-area aware', () => {
  assert.match(main, /import '\.\/startup-v1172\.css';/);
  assert.match(css, /env\(safe-area-inset-bottom\)/);
  assert.match(css, /min-height: 44px/);
});
