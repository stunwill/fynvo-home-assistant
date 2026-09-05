import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

test('authenticated state is passed through every production wrapper', async () => {
  const shell = await read('src/AppV13.jsx');
  const wrapper = await read('src/AppCorrectiveV1163.jsx');
  const base = await read('src/AppCorrectiveV0174.jsx');

  assert.match(shell, /<App authState=\{auth\}\/>/);
  assert.match(wrapper, /<BaseApp authState=\{authState\}\/>/);
  assert.match(base, /AppCorrectiveV0174\(\{ authState = null \}\)/);
});

test('base workspace starts from supplied auth instead of an unconditional second startup request', async () => {
  const base = await read('src/AppCorrectiveV0174.jsx');

  assert.match(base, /useState\(\(\) => authState \|\| globalThis\.__fynvoSharedAuthState \|\| null\)/);
  assert.match(base, /if \(authState\) \{\s*setAuth\(authState\);\s*return;\s*\}/s);
  assert.doesNotMatch(base, /useEffect\(\(\) => \{ loadAuth\(\); \}, \[\]\)/);
});

test('standalone login fallback remains available for legacy direct mounting', async () => {
  const base = await read('src/AppCorrectiveV0174.jsx');

  assert.match(base, /async function loadAuth\(\)/);
  assert.match(base, /async function submitAuth\(e\)/);
  assert.match(base, /Sign in/);
  assert.match(base, /if \(!auth\) return/);
});

test('production shell reports v1.17.9 without the legacy fetch bridge', async () => {
  const shell = await read('src/AppV13.jsx');
  const pkg = JSON.parse(await read('package.json'));

  assert.match(shell, /PRODUCTION_VERSION = '1\.17\.9'/);
  assert.doesNotMatch(shell, /AUTH_BRIDGE_VERSION/);
  assert.equal(pkg.version, '1.17.9');
});
