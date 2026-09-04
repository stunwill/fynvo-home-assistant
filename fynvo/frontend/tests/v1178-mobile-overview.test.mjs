import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const mobileShell = await read('src/MobileOverviewV1178.jsx');
const mobileCss = await read('src/mobile-overview-v1178.css');
const appShell = await read('src/AppV13.jsx');
const base = await read('src/AppCorrectiveV0174.jsx');
const entry = await read('src/main.jsx');
const pkg = JSON.parse(await read('package.json'));

test('mobile shell owns five primary destinations across all mobile pages', () => {
  assert.match(mobileShell, /Primary mobile navigation/);
  for (const label of ['Overview', 'Accounts', 'Cash Flow', 'Transactions', 'More']) assert.match(mobileShell, new RegExp(`>${label}<`));
  assert.match(mobileShell, /if \(!active\) return null/);
  assert.doesNotMatch(mobileShell, /if \(!active \|\| !host\) return null/);
});

test('More exposes Tools and a usable mobile tools sheet without the floating trigger', () => {
  assert.match(mobileShell, /fynvo:open-tools/);
  assert.match(appShell, /fynvo-mobile-tools-sheet/);
  assert.match(appShell, /setToolsOpen\(true\)/);
  assert.match(mobileCss, /\.fynvo-tools-menu-shell\{display:none!important\}/);
  assert.match(mobileCss, /\.fynvo-mobile-more-backdrop,\.fynvo-mobile-tools-backdrop/);
});

test('Home Assistant mobile chrome suppresses the duplicate internal Fynvo app bar', () => {
  assert.match(base, /className="mobile-app-bar"/);
  assert.match(mobileCss, /\.mobile-app-bar\{display:none!important\}/);
  assert.match(mobileCss, /main\.content>\.header\{margin:0 0 12px!important/);
  assert.match(mobileCss, /@media\(max-width:980px\)/);
});

test('Accounts mobile workspace removes irrelevant global controls and large empty header space', () => {
  assert.match(mobileCss, /fynvo-accounts-cards-v1163-active main\.content>\.header-actions\{display:none!important\}/);
  assert.match(mobileCss, /accounts-cards-v1163-overlay\{margin:0!important;padding:0 0 4px!important/);
  assert.match(mobileCss, /accounts-cards-action-row\{display:flex!important/);
  assert.match(mobileCss, /accounts-cards-tabs\{width:100%!important/);
});

test('Accounts summary and rows are compact and responsive', () => {
  assert.match(mobileCss, /accounts-cards-summary\{grid-template-columns:repeat\(2,minmax\(0,1fr\)\)!important/);
  assert.match(mobileCss, /accounts-cards-summary article\{min-height:84px!important/);
  assert.match(mobileCss, /accounts-cards-toolbar\{display:grid!important;grid-template-columns:minmax\(0,1fr\) 106px!important/);
  assert.match(mobileCss, /@media\(max-width:329px\)/);
  assert.match(mobileCss, /accounts-cards-toolbar\{grid-template-columns:1fr!important\}/);
  assert.match(mobileCss, /accounts-cards-account-row\{grid-template-columns:38px minmax\(0,1fr\) minmax\(90px,auto\) 12px!important/);
  assert.match(mobileCss, /min-height:78px!important/);
});

test('mobile Overview keeps exactly four snapshot actions then cash flow and top accounts', () => {
  const snapshot = mobileShell.match(/fynvo-mobile-snapshot-grid[\s\S]*?<\/div>\s*<\/section>/)?.[0] || '';
  assert.equal((snapshot.match(/<button/g) || []).length, 4);
  const snapshotIndex = mobileShell.indexOf('fynvo-mobile-snapshot');
  const cashIndex = mobileShell.indexOf('fynvo-mobile-cashflow');
  const accountsIndex = mobileShell.indexOf('fynvo-mobile-accounts');
  assert.ok(snapshotIndex >= 0 && cashIndex > snapshotIndex && accountsIndex > cashIndex);
  assert.match(mobileShell, /\.slice\(0, 3\)/);
});

test('mobile Overview uses canonical deduplicating API client for already requested data', () => {
  assert.match(mobileShell, /import \{ apiRequest \} from '\.\/apiClient\.js'/);
  assert.match(mobileShell, /apiRequest\(`\/dashboard\/command-centre\?range_days=\$\{rangeDays\}`\)/);
  assert.match(mobileShell, /apiRequest\('\/accounts'\)/);
  assert.match(mobileShell, /apiRequest\('\/payment-planning'\)/);
});

test('v1.17.8 production stylesheet is last and version surfaces agree', () => {
  assert.match(entry, /import '\.\/mobile-overview-v1178\.css';\s*\n\nReactDOM/s);
  assert.equal(pkg.version, '1.17.8');
  assert.match(appShell, /PRODUCTION_VERSION = '1\.17\.8'/);
});
