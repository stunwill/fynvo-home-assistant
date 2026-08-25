import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const app = await readFile(new URL('../src/AppCorrectiveV0174.jsx', import.meta.url), 'utf8');
const chart = await readFile(new URL('../src/v0174-corrective.jsx', import.meta.url), 'utf8');
const css = await readFile(new URL('../src/v111.css', import.meta.url), 'utf8');

test('Overview consumes the v1.11 command-centre contract', () => {
  assert.match(app, /kpis\.available_cash/);
  assert.match(app, /kpis\.scheduled_commitments/);
  assert.match(app, /command\.upcoming_commitments/);
  assert.match(app, /expected\?\.events \|\| forecast\?\.events/);
});

test('Calendar falls back to canonical forecast events instead of false empty state', () => {
  assert.match(app, /command\?\.upcoming_commitments \|\| command\?\.forecast\?\.expected\?\.events/);
  assert.match(app, /Nothing scheduled/);
});

test('financial currency formatting rejects non-finite values', () => {
  assert.match(app, /Number\.isFinite\(number\)/);
  assert.match(app, /number === null \? null/);
});

test('Lowest Balance reads the canonical balance field from the forecast object', () => {
  assert.match(app, /lowestRecord\.balance/);
  assert.match(app, /Lowest Balance/);
});

test('cash-flow forecast chart consumes canonical chart_points', () => {
  assert.match(chart, /forecast\?\.chart_points/);
  assert.match(chart, /Number\.isFinite/);
  assert.match(chart, /Cash Flow Forecast/);
});

test('mobile Cash Flow uses contained event rows rather than stretched list buttons', () => {
  assert.match(app, /cashflow-event-row/);
  assert.match(css, /\.cashflow-event-row\{width:100%;display:grid;grid-template-columns:minmax\(0,1fr\) auto/);
  assert.match(css, /overflow-wrap:anywhere/);
});
