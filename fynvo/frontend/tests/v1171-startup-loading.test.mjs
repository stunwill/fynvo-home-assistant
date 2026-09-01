import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const shell = await readFile(new URL('../src/AppV13.jsx', import.meta.url), 'utf8');


test('production shell shares its authoritative auth state with the nested app startup read', () => {
  assert.match(shell, /const nativeFetch = window\.fetch\.bind\(window\)/);
  assert.match(shell, /window\.__fynvoSharedAuthState = state/);
  assert.match(shell, /url === 'api\/auth\/state'/);
  assert.match(shell, /Promise\.resolve\(authStateResponse\(window\.__fynvoSharedAuthState\)\)/);
  assert.match(shell, /const response = await api\('\/auth\/state'\)/);
});


test('authoritative outer auth refresh bypasses the shared-state bridge', () => {
  assert.match(shell, /nativeFetch\(`api\$\{path\}`/);
  assert.match(shell, /cacheAuthState\(state\)/);
  assert.match(shell, /cacheAuthState\(unavailable\)/);
});


test('v1.17.1 production shell reports the corrective release version', () => {
  assert.match(shell, /PRODUCTION_VERSION = '1\.17\.1'/);
});
