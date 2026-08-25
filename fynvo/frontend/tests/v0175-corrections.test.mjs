import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const entry = await readFile(new URL('../src/main.jsx', import.meta.url), 'utf8');
const wrapper = await readFile(new URL('../src/AppV13.jsx', import.meta.url), 'utf8');
const app = await readFile(new URL('../src/AppCorrectiveV0174.jsx', import.meta.url), 'utf8');
const css = await readFile(new URL('../src/corrective-v0175.css', import.meta.url), 'utf8');
const corrective = await readFile(new URL('../src/v0174-corrective.jsx', import.meta.url), 'utf8');

test('v0.17.5 corrective stylesheet remains loaded after the earlier UX styles', () => {
  assert.match(entry, /import '\.\/corrective-v0175\.css';/);
  assert.ok(entry.indexOf("'./corrective-v0175.css'") > entry.indexOf("'./ux-v171.css'"));
  assert.match(corrective, /APP_VERSION_V0174 = '1\.10\.1'/);
});

test('overview no longer displays the redundant next seven days card', () => {
  assert.doesNotMatch(app, /PanelHead title="Upcoming" meta="Next 7 days"/);
  assert.match(app, /PanelHead title="Upcoming Commitments"/);
  assert.match(css, /\.dashboard-page > \.card-grid > article\.panel:first-child\s*\{\s*display:\s*none;/s);
});

test('income page hides the global date range selector without affecting other pages', () => {
  assert.match(wrapper, /heading === 'Income'/);
  assert.match(wrapper, /classList\.toggle\('fynvo-income-page'/);
  assert.match(wrapper, /classList\.remove\('fynvo-income-page'\)/);
  assert.match(css, /body\.fynvo-income-page \.header-actions > \.select-shell\s*\{\s*display:\s*none;/s);
});
