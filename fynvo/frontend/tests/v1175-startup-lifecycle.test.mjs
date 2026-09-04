import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

const shell = await read('src/AppV13.jsx');
const wrapper = await read('src/AppCorrectiveV1163.jsx');
const base = await read('src/AppCorrectiveV0174.jsx');
const entry = await read('src/main.jsx');
const html = await read('index.html');


test('v1.17.7 retains one authoritative startup auth request owner', () => {
  assert.match(shell, /PRODUCTION_VERSION = '1\.17\.7'/);
  assert.match(shell, /useEffect\(\(\) => \{ refreshAuth\(\); \}, \[\]\)/);
  assert.doesNotMatch(shell, /__fynvoAuthFetchBridgeVersion/);
  assert.doesNotMatch(shell, /globalThis\.fetch\s*=/);
  assert.doesNotMatch(shell, /authStateResult/);
});


test('authenticated state is passed through without keyed remounts', () => {
  assert.match(shell, /<App authState=\{auth\}\/>/);
  assert.doesNotMatch(shell, /fynvo-startup-\$\{startupAttempt\}/);
  assert.doesNotMatch(shell, /setStartupAttempt/);
  assert.match(wrapper, /<BaseApp authState=\{authState\}\/>/);
  assert.match(base, /AppCorrectiveV0174\(\{ authState = null \}\)/);
});


test('installed startup emits observable backend stages', () => {
  assert.match(shell, /api\/household\/client-diagnostics/);
  assert.match(shell, /publishStartup\(state\.authenticated \? 'authenticated' : 'anonymous'\)/);
  assert.match(shell, /publishStartup\('workspace-mounted'\)/);
  assert.match(shell, /publishStartup\('workspace-rendered', heading\)/);
});


test('production entry performs one React root mount without StrictMode wrapper', () => {
  assert.match(entry, /createRoot\(document\.getElementById\('root'\)\)\.render\(<App \/>\)/);
  assert.doesNotMatch(entry, /StrictMode/);
});


test('HTML shell requests no-cache handling across Home Assistant upgrades', () => {
  assert.match(html, /Cache-Control" content="no-cache, no-store, must-revalidate/);
  assert.match(html, /Pragma" content="no-cache/);
  assert.match(html, /Expires" content="0/);
});
