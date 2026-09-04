import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const apiClient = await read('src/apiClient.js');
const wrapper = await read('src/AppCorrectiveV1163.jsx');
const entry = await read('src/main.jsx');
const mobile = await read('src/mobile-v1177.css');
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

test('v1.17.7 mobile stylesheet loads last and keeps dense touch-friendly ingress layout', () => {
  assert.match(entry, /import '\.\/mobile-v1177\.css';\s*\n\nReactDOM/s);
  assert.match(mobile, /@media\(max-width:720px\)/);
  assert.match(mobile, /grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
  assert.match(mobile, /env\(safe-area-inset-bottom/);
  assert.match(mobile, /\.modal-actions\{position:sticky/);
  assert.match(mobile, /\.header h1\{font-size:clamp\(26px/);
});

test('v1.17.7 version surfaces align', () => {
  assert.match(shell, /PRODUCTION_VERSION = '1\.17\.7'/);
  assert.equal(pkg.version, '1.17.7');
});
