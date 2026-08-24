import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const css = await readFile(new URL('../src/v143.css', import.meta.url), 'utf8');
const entry = await readFile(new URL('../src/main.jsx', import.meta.url), 'utf8');

test('v1.4.3 keeps the drawer above the backdrop and fully interactive', () => {
  assert.match(css, /\.sidebar\{[\s\S]*z-index:100!important/);
  assert.match(css, /pointer-events:auto!important/);
  assert.match(css, /opacity:1!important/);
  assert.match(css, /\.mobile-nav-backdrop\{[\s\S]*z-index:80!important/);
});

test('mobile close control remains absolutely positioned and out of drawer flex flow', () => {
  const interactiveBlock = css.slice(css.indexOf('.sidebar nav,'), css.indexOf('.sidebar .mobile-nav-close'));
  assert.doesNotMatch(interactiveBlock, /mobile-nav-close/);
  assert.match(css, /\.sidebar \.mobile-nav-close\{[\s\S]*position:absolute!important/);
  assert.match(css, /right:12px!important/);
  assert.match(css, /width:44px!important/);
});

test('open backdrop begins outside the drawer so it cannot intercept menu taps', () => {
  assert.match(css, /\.mobile-nav-open \.mobile-nav-backdrop\{[\s\S]*left:min\(86vw,350px\)/);
  assert.match(css, /left:min\(88vw,340px\)/);
  assert.match(css, /left:min\(90vw,320px\)/);
});

test('v1.4.3 corrective CSS loads after v1.4.2 styles', () => {
  assert.ok(entry.indexOf("'./v143.css'") > entry.indexOf("'./v142.css'"));
});
