import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

test('v1.16.2 current-day override loads last and survives mobile stylesheet precedence', async () => {
  const entry = await read('src/main.jsx');
  const source = await read('src/RecurringExpensesPage.jsx');
  const css = await read('src/corrective-v1162.css');

  assert.match(source, /const todayKey = localDateKey\(\)/);
  assert.match(source, /aria-current=\{isToday \? 'date' : undefined\}/);
  assert.match(source, /isToday \? 'today' : ''/);

  assert.match(entry, /import '\.\/corrective-v1162\.css';/);
  assert.ok(
    entry.indexOf("'./corrective-v1162.css'") > entry.indexOf("'./corrective-v1161.css'"),
    'v1.16.2 corrective CSS must load after v1.16.1',
  );

  assert.match(css, /button\[aria-current="date"\]/);
  assert.match(css, /button\.today/);
  assert.match(css, /background:\s*#dcebff\s*!important/);
  assert.match(css, /box-shadow:\s*inset 0 0 0 3px #1769e0\s*!important/);
  assert.match(css, /color:\s*#ffffff\s*!important/);
  assert.match(css, /@media \(max-width: 980px\)/);
});
