import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const shell = await readFile(new URL('../src/AppV13.jsx', import.meta.url), 'utf8');

test('mobile More sheet exposes the existing Bank connections workspace', () => {
  assert.match(shell, /\.fynvo-mobile-more-sheet nav/);
  assert.match(shell, /fynvoBankConnections/);
  assert.match(shell, /button\.textContent = 'Bank connections'/);
  assert.match(shell, /setBankConnectionsOpen\(true\)/);
  assert.match(shell, /nav\.insertBefore\(button, version \|\| null\)/);
});
