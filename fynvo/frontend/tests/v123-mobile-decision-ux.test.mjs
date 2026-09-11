import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const overview = await read('src/MobileOverviewV1190.jsx');
const cashPlan = await read('src/CashPlanPageV121.jsx');
const css = await read('src/mobile-overview-v1190.css');

test('mobile Overview uses one concise action area and grouped navigation', () => {
  assert.match(overview, /Money requiring action/);
  assert.match(overview, /View all requiring action/);
  assert.match(overview, /<h3>Planning<\/h3>/);
  assert.match(overview, /<h3>Payments<\/h3>/);
  assert.match(overview, /Money &amp; accounts/);
});

test('Cash Plan distinguishes unavailable planning from a request failure', () => {
  assert.match(cashPlan, /Promise\.allSettled/);
  assert.match(cashPlan, /Safe to spend unavailable/);
  assert.match(cashPlan, /Some planning information is unavailable/);
  assert.match(cashPlan, /Cash Plan could not load\. Try again\./);
});

test('mobile decision surfaces preserve narrow-width and safe-area protections', () => {
  assert.match(css, /min-width:0/);
  assert.match(css, /safe-area-inset-bottom/);
  assert.match(css, /@media\(max-width:393px\)/);
  assert.match(css, /@media\(max-width:374px\)/);
  assert.match(css, /@media\(max-width:329px\)/);
});
