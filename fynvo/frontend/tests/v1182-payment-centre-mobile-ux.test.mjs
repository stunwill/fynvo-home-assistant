import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const payment = await read('src/PaymentCentreMobileV1182.jsx');
const css = await read('src/payment-centre-mobile-v1182.css');
const app = await read('src/AppCorrectiveV0174.jsx');
const shell = await read('src/AppV13.jsx');
const mobileShell = await read('src/MobileOverviewV1181.jsx');
const main = await read('src/main.jsx');
const config = await read('../config.yaml');
const backendConfig = await read('../backend/app/config.py');
const packageJson = JSON.parse(await read('package.json'));

test('mobile Payment Centre is mounted only for mobile while desktop keeps the existing workspace', () => {
  assert.match(app, /PaymentCentreMobileV1182/);
  assert.match(app, /isMobile \? <PaymentCentreMobileV1182/);
  assert.match(app, /: <PaymentCentreV1161/);
  assert.match(main, /payment-centre-mobile-v1182\.css/);
  assert.match(css, /@media\(min-width:981px\)/);
});

test('compact payment cards keep name and full currency amount prominent', () => {
  assert.match(payment, /payment-v1182-card-name/);
  assert.match(payment, /payment-v1182-card-amount/);
  assert.match(payment, /Intl\.NumberFormat\('en-AU', \{ style: 'currency', currency: 'AUD' \}\)/);
  assert.match(css, /payment-v1182-card-main/);
  assert.match(css, /payment-v1182-card-amount[^}]*white-space:nowrap/);
});

test('payment metadata is consolidated and overdue state is expressed once in readable text', () => {
  assert.match(payment, /const meta = \[/);
  assert.match(payment, /overdue > 0 \? `Due \$\{dateLabel\(due\)\} · \$\{overdue\} day\$\{overdue === 1 \? '' : 's'\} overdue`/);
  assert.match(payment, /payment_handling === 'automatic' \? 'Automatic' : 'Manual'/);
  assert.match(payment, /PAYMENT_METHOD_LABELS/);
  assert.match(css, /payment-v1182-card-meta/);
});

test('incomplete payment information is compact and actionable', () => {
  assert.match(payment, /missingFields/);
  for (const field of ['due date', 'payment method', 'funding account']) assert.match(payment, new RegExp(field));
  assert.match(payment, /detail\{missing\.length === 1 \? '' : 's'\} missing/);
  assert.match(payment, /Review \{missing\.length\} missing detail/);
  assert.match(css, /payment-v1182-missing/);
});

test('Mark paid remains visible and secondary lifecycle actions use overflow', () => {
  assert.match(payment, /Mark paid/);
  assert.match(payment, /payment-v1182-card-actions/);
  assert.match(payment, /paymentAvailableActions/);
  assert.match(payment, /payment-v1182-overflow/);
  assert.match(payment, /setMenuOpen\(false\)/);
  assert.match(css, /grid-template-columns:minmax\(0,1fr\) 48px/);
});

test('overflow actions retain the existing lifecycle/detail workspaces', () => {
  assert.match(payment, /PaymentCentreV112/);
  assert.match(payment, /Back to compact queue/);
  assert.match(payment, /onEditBill/);
  assert.match(payment, /onOpenRecurring/);
  assert.match(payment, /onNavigate/);
});

test('grouped and chronological modes form one persisted segmented selector', () => {
  assert.match(payment, /timelineMode\.v1182/);
  assert.match(payment, /aria-label="Payment timeline view"/);
  assert.match(payment, />Grouped</);
  assert.match(payment, />Chronological</);
  assert.match(payment, /aria-pressed=\{mode === 'grouped'\}/);
  assert.match(payment, /aria-pressed=\{mode === 'chronological'\}/);
  assert.match(css, /payment-v1182-mode/);
});

test('chronological date headers include readable dates and payment count pluralisation', () => {
  assert.match(payment, /weekday: 'short'/);
  assert.match(payment, /group\.rows\.length} payment\{group\.rows\.length === 1 \? '' : 's'\}/);
  assert.match(payment, /Date not specified/);
  assert.match(payment, /Payment history/);
});

test('priority ordering is explicit without breaking chronological grouping', () => {
  assert.match(payment, /const attentionRank/);
  assert.match(payment, /status === 'overdue'/);
  assert.match(payment, /match_review_available/);
  assert.match(payment, /status === 'due' \|\| status === 'due_today'/);
  assert.match(payment, /status === 'auto_payment_unconfirmed'/);
  assert.match(payment, /a\.localeCompare\(b\)/);
});

test('creation controls remain compact and Add Bill uses the real bill creation workflow', () => {
  assert.match(payment, /\+ Quick Add/);
  assert.match(payment, /\+ Add Bill/);
  assert.match(app, /onQuickAdd=\{\(\) => setQuickMenuOpen\(true\)\}/);
  assert.match(app, /onAddBill=\{\(\) => setQuick\(quickDefaults\('bills'\)\)\}/);
  assert.match(css, /payment-v1182-create-row\{display:grid;grid-template-columns:1fr 1fr/);
  assert.match(css, /white-space:nowrap/);
});

test('filters are progressive, show active count and can be cleared', () => {
  assert.match(payment, /Filters\{activeCount \? ` \(\$\{activeCount\}\)` : ''\}/);
  assert.match(payment, /Next 30 days/);
  assert.match(payment, /Overdue/);
  assert.match(payment, /Needs attention/);
  assert.match(payment, /const clear = \(\) =>/);
  assert.match(payment, /Clear filters/);
  assert.match(payment, /role="dialog" aria-modal="true" aria-label="Payment filters"/);
});

test('pay-cycle summary prioritises conclusion and progressively discloses authoritative calculation', () => {
  assert.match(payment, /BEFORE NEXT PAY/);
  assert.match(payment, /shortfall/);
  assert.match(payment, /Funded before next pay/);
  assert.match(payment, /Before-pay position unavailable/);
  for (const label of ['Available now', 'Required before pay', 'Next income', 'View calculation', 'Overdue included', 'Projected before pay', 'Projected after pay']) assert.match(payment, new RegExp(label));
  assert.match(payment, /planning\?\.pay_cycle/);
});

test('unknown funding and income states are explicit and never fake a zero shortfall', () => {
  assert.match(payment, /Next income not confirmed/);
  assert.match(payment, /Funding shortfall/);
  assert.match(payment, /shortfallAmount === null \? 'Funding shortfall'/);
  assert.match(payment, /Funding account assignments or balances are incomplete/);
  assert.doesNotMatch(payment, />Unknown</);
});

test('payment and funding loading/error states are independent', () => {
  assert.match(payment, /loadPayments/);
  assert.match(payment, /loadPlanning/);
  assert.match(payment, /loadingPayments/);
  assert.match(payment, /loadingPlanning/);
  assert.match(payment, /Payment list could not load/);
  assert.match(payment, /Before-pay funding unavailable/);
  assert.match(payment, /Retry payments/);
  assert.match(payment, /Retry funding/);
});

test('loading uses structure-preserving skeletons with reduced-motion support', () => {
  assert.match(payment, /PaymentSkeleton/);
  assert.match(payment, /aria-label="Loading payments"/);
  assert.match(payment, /aria-label="Loading before-pay funding"/);
  assert.match(css, /payment-v1182-skeleton-row/);
  assert.match(css, /prefers-reduced-motion:reduce/);
  assert.match(css, /animation:none/);
});

test('empty states distinguish no period results from filtered results', () => {
  assert.match(payment, /No payments match these filters/);
  assert.match(payment, /No payments in this period/);
  assert.match(payment, /Try clearing filters/);
  assert.match(payment, /Clear filters/);
});

test('mobile footer is suppressed and bottom navigation safe-area clearance is explicit', () => {
  assert.match(css, /body\.fynvo-payment-centre-page \.app-footer\{display:none!important\}/);
  assert.match(css, /padding-bottom:calc\(96px \+ env\(safe-area-inset-bottom,0px\)\)/);
  assert.match(app, /fynvo-payment-centre-page/);
  assert.match(mobileShell, /ABOUT/);
  assert.match(mobileShell, /productionVersion \|\| '1.22.0'/);
});

test('Home Assistant ingress and modal layering protections remain explicit', () => {
  assert.match(css, /position:sticky/);
  assert.match(css, /100dvh/);
  assert.match(css, /safe-area-inset-top/);
  assert.match(css, /safe-area-inset-bottom/);
  assert.match(css, /payment-centre-modal-backdrop\{z-index:220\}/);
  assert.match(payment, /setMenuOpen\(false\)/);
});

test('responsive breakpoints cover narrow iPhone, standard iPhone, tablet edge and legacy 980px boundary', () => {
  assert.match(css, /@media\(max-width:980px\)/);
  assert.match(css, /@media\(max-width:430px\)/);
  assert.match(css, /@media\(max-width:393px\)/);
  assert.match(css, /@media\(max-width:374px\)/);
  assert.match(css, /@media\(max-width:329px\)/);
  assert.match(css, /@media\(min-width:981px\)/);
});

test('current release metadata remains aligned while v1.22.0 behaviour stays under regression coverage', () => {
  assert.match(config, /version: "1.24.0"/);
  assert.equal(packageJson.version, '1.24.0');
  assert.match(backendConfig, /APP_VERSION = "1.24.0"/);
  assert.match(shell, /PRODUCTION_VERSION = '1.24.0'/);
});
