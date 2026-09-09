import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const legacyMobileShell = await read('src/MobileOverviewV1178.jsx');
const mobileShell = await read('src/MobileOverviewV1181.jsx');
const mobileCss = await read('src/mobile-overview-v1178.css');
const refinementCss = await read('src/mobile-workspace-v1179.css');
const decisionCss = await read('src/mobile-financial-decision-v1180.css');
const overviewCss = await read('src/overview-decision-v1181.css');
const payment1183Css = await read('src/payment-centre-mobile-v1183.css');
const appShell = await read('src/AppV13.jsx');
const base = await read('src/AppCorrectiveV0174.jsx');
const entry = await read('src/main.jsx');
const pkg = JSON.parse(await read('package.json'));
const renderedOverview = mobileShell.slice(mobileShell.indexOf('const overviewContent ='), mobileShell.indexOf('const moreGroups ='));

test('mobile shell owns five primary destinations across all mobile pages', () => {
  assert.match(mobileShell, /Primary mobile navigation/);
  for (const label of ['Overview', 'Accounts', 'Cash Flow', 'Transactions', 'More']) assert.match(mobileShell, new RegExp(`>${label}<`));
  assert.match(mobileShell, /if \(!active\) return null/);
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

test('Accounts summary and rows remain compact and responsive with v1.17.9 refinement', () => {
  assert.match(mobileCss, /accounts-cards-summary\{grid-template-columns:repeat\(2,minmax\(0,1fr\)\)!important/);
  assert.match(refinementCss, /accounts-cards-summary article\{min-height:80px!important/);
  assert.match(mobileCss, /accounts-cards-toolbar\{display:grid!important;grid-template-columns:minmax\(0,1fr\) 106px!important/);
  assert.match(mobileCss, /@media\(max-width:329px\)/);
  assert.match(mobileCss, /accounts-cards-toolbar\{grid-template-columns:1fr!important\}/);
  assert.match(mobileCss, /accounts-cards-account-row\{grid-template-columns:38px minmax\(0,1fr\) minmax\(90px,auto\) 12px!important/);
  assert.match(mobileCss, /min-height:78px!important/);
});

test('v1.18.1 supersedes the four-card Snapshot with the decision-first Overview hierarchy', () => {
  assert.match(legacyMobileShell, /fynvo-mobile-snapshot-grid/);
  assert.doesNotMatch(mobileShell, /fynvo-mobile-snapshot-grid/);
  const decisionIndex = renderedOverview.indexOf('<h2 id="fynvo-mobile-decision">Before next pay</h2>');
  const attentionIndex = renderedOverview.indexOf('<h2 id="fynvo-mobile-attention">Needs attention</h2>');
  const neededIndex = renderedOverview.indexOf('<h2>Money needed soon</h2>');
  const cashIndex = renderedOverview.indexOf('<h2>Cash position</h2>');
  const accountsIndex = renderedOverview.indexOf('<h2>Accounts</h2>');
  assert.ok(decisionIndex >= 0 && attentionIndex > decisionIndex && neededIndex > attentionIndex && cashIndex > neededIndex && accountsIndex > cashIndex);
  assert.match(mobileShell, /topAttention: sortedAttention\.slice\(0, 3\)/);
});

test('mobile Overview uses canonical deduplicating API client for already requested data', () => {
  assert.match(mobileShell, /import \{ apiRequest \} from '\.\/apiClient\.js'/);
  assert.match(mobileShell, /apiRequest\(`\/dashboard\/command-centre\?range_days=\$\{rangeDays\}`\)/);
  assert.match(mobileShell, /apiRequest\('\/accounts'\)/);
  assert.match(mobileShell, /apiRequest\('\/payment-planning'\)/);
});

test('historical Overview layers remain ordered before the current v1.19.0 mobile layer and release surfaces agree', () => {
  assert.match(entry, /import '\.\/mobile-overview-v1178\.css';\s*\nimport '\.\/mobile-workspace-v1179\.css';\s*\nimport '\.\/mobile-financial-decision-v1180\.css';\s*\nimport '\.\/overview-decision-v1181\.css';\s*\nimport '\.\/payment-centre-mobile-v1182\.css';\s*\nimport '\.\/payment-centre-mobile-v1183\.css';\s*\nimport '\.\/mobile-overview-v1190\.css';\s*\n\nReactDOM/s);
  assert.match(decisionCss, /fynvo-mobile-decision-card/);
  assert.match(overviewCss, /fynvo-overview-v1181-before/);
  assert.match(payment1183Css, /payment-v1183-shell/);
  assert.equal(pkg.version, '1.21.0');
  assert.match(appShell, /PRODUCTION_VERSION = '1\.21\.0'/);
});
