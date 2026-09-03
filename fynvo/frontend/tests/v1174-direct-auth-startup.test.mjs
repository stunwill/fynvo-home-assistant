import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

test('authenticated state is passed through every production wrapper', async () => {
  const shell = await read('src/AppV13.jsx');
  const wrapper = await read('src/AppCorrectiveV1163.jsx');
  const base = await read('src/AppCorrectiveV0174.jsx');

  assert.match(shell, /<App key=\{`fynvo-startup-\$\{startupAttempt\}`\} authState=\{auth\}\/>/);
  assert.match(wrapper, /<BaseApp authState=\{authState\}\/>/);
  assert.match(base, /AppCorrectiveV0174\(\{ authState = null \}\)/);
});

test('base workspace starts from supplied auth instead of a second startup request', async () => {
  const base = await read('src/AppCorrectiveV0174.jsx');

  assert.match(base, /useState\(\(\) => authState \|\| globalThis\.__fynvoSharedAuthState \|\| null\)/);
  assert.match(base, /if \(authState\) \{\s*setAuth\(authState\);\s*return;\s*\}/s);
  assert.match(base, /if \(!globalThis\.__fynvoSharedAuthState\) loadAuth\(\)/);
  assert.doesNotMatch(base, /useEffect\(\(\) => \{ loadAuth\(\); \}, \[\]\)/);
});

test('standalone login fallback remains available', async () => {
  const base = await read('src/AppCorrectiveV0174.jsx');

  assert.match(base, /async function loadAuth\(\)/);
  assert.match(base, /async function submitAuth\(e\)/);
  assert.match(base, /Sign in/);
  assert.match(base, /if \(!auth\) return/);
});

test('production shell reports v1.17.4', async () => {
  const shell = await read('src/AppV13.jsx');
  const pkg = JSON.parse(await read('package.json'));

  assert.match(shell, /PRODUCTION_VERSION = '1\.17\.4'/);
  assert.match(shell, /AUTH_BRIDGE_VERSION = '1\.17\.4'/);
  assert.equal(pkg.version, '1.17.4');
});
