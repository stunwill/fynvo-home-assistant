import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const apiClient = await read('src/apiClient.js');
const wrapper = await read('src/AppCorrectiveV1163.jsx');
const entry = await read('src/main.jsx');
const mobile = await read('src/mobile-v1177.css');
const mobile1178 = await read('src/mobile-overview-v1178.css');
const shell = await read('src/AppV13.jsx');
const pkg = JSON.parse(await read('package.json'));

test('startup API client deduplicates identical GET requests', () => {
  assert.match(apiClient, /const inFlightGets = new Map\(\)/);
  assert.match(apiClient, /const existing = inFlightGets\.get\(path\)/);
  assert.match(apiClient, /if \(existing\) return existing/);
});

test('command centre supplies duplicate expected forecast and financial health reads', () => {
  assert.match(apiClient, /commandCentreByRange/);
  assert.match(apiClient, /command\?\.forecast\?\.expected/);
  assert.match(apiClient, /command\?\.financial_health/);
  assert.match(apiClient, /rangeFromForecastPath/);
  assert.match(apiClient, /rangeFromHealthPath/);
});

test('mutations invalidate short read caches', () => {
  assert.match(apiClient, /if \(method !== 'GET'\) \{\s*clearReadCaches\(\)/s);
  assert.match(apiClient, /shortCache\.clear\(\)/);
  assert.match(apiClient, /commandCentreByRange\.clear\(\)/);
});

test('Accounts and Cards wrapper shares the canonical API client', () => {
  assert.match(wrapper, /import \{ apiRequest \} from '\.\/apiClient\.js'/);
  assert.match(wrapper, /apiRequest\('\/accounts'\)/);
  assert.match(wrapper, /apiRequest\('\/cards\?include_inactive=true'\)/);
  assert.doesNotMatch(wrapper, /const api =/);
});

test('v1.17.8 mobile styles retain v1.17.7 density protections and load the corrective layer last', () => {
  assert.match(entry, /import '\.\/mobile-v1177\.css';\s*\nimport '\.\/mobile-overview-v1178\.css';\s*\n\nReactDOM/s);
  assert.match(mobile, /@media\(max-width:720px\)/);
  assert.match(mobile, /grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
  assert.match(mobile, /env\(safe-area-inset-bottom/);
  assert.match(mobile, /\.modal-actions\{position:sticky/);
  assert.match(mobile, /\.header h1\{font-size:clamp\(26px/);
  assert.match(mobile1178, /@media\(max-width:980px\)/);
  assert.match(mobile1178, /\.mobile-app-bar\{display:none!important\}/);
  assert.match(mobile1178, /\.fynvo-tools-menu-shell\{display:none!important\}/);
  assert.match(mobile1178, /body\.fynvo-accounts-cards-v1163-active main\.content>\.header-actions\{display:none!important\}/);
});

test('v1.17.8 version surfaces align in the production shell', () => {
  assert.match(shell, /PRODUCTION_VERSION = '1\.17\.8'/);
  assert.equal(pkg.version, '1.17.8');
});
