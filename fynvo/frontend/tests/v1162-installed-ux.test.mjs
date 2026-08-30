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

test('Cash Flow reuses Overview forecast and never treats loading as empty', async () => {
  const page = await read('src/CashFlowPageV1161.jsx');
  const app = await read('src/AppCorrectiveV0174.jsx');

  assert.match(app, /forecastCache:\s*\{\}/);
  assert.match(app, /cacheForRange/);
  assert.match(app, /initialForecast=\{cacheForRange\}/);
  assert.match(app, /onForecastLoaded=\{rememberForecast\}/);
  assert.match(page, /hasCompleteSeed|complete = Boolean\(seededBaseline && seededExpected\)/);
  assert.match(page, /if \(!complete\) load/);
  assert.match(page, /needsBaseline \? apiRequest/);
  assert.match(page, /needsExpected \? apiRequest/);
  assert.match(page, /Loading cash flow…/);
  assert.match(page, /!state\.loading && !state\.error && hasExisting \? <Empty title="No forecast events"/);
  assert.match(page, /Events affecting this forecast/);
  assert.match(page, /Starting balance/);
  assert.match(page, /Projected balance/);
  assert.match(page, /Lowest balance/);
});

test('Overview summary cards drill into authoritative detail workspaces', async () => {
  const app = await read('src/AppCorrectiveV0174.jsx');
  assert.match(app, /label="Total Balance"[\s\S]*setActive\('Accounts'\)/);
  assert.match(app, /label="Next Income"[\s\S]*setActive\('Income'\)/);
  assert.match(app, /label="Upcoming Commitments"[\s\S]*setActive\('Payment Centre'\)/);
  assert.match(app, /label="Discretionary"[\s\S]*setActive\('Planned Spending'\)/);
  assert.match(app, /label="Goals"[\s\S]*setActive\('Goals'\)/);
  assert.match(app, /function Kpi\([\s\S]*<button type="button" className="kpi kpi-link"/);
  assert.match(app, /dashboard-forecast-panel[\s\S]*onClick=\{\(\) => setActive\('Cash Flow'\)\}[\s\S]*<h2>Cash Flow Forecast<\/h2>/);
});

test('Calendar and Cash Flow have distinct product responsibilities', async () => {
  const app = await read('src/AppCorrectiveV0174.jsx');
  const cashflow = await read('src/CashFlowPageV1161.jsx');
  assert.match(app, /See what is happening and when across your household finances/);
  assert.match(app, /What is happening and when across your household finances/);
  assert.match(app, /calendar-v1162-dates/);
  assert.match(app, /setSelectedDate/);
  assert.match(cashflow, /What will happen to your household balance/);
  assert.match(cashflow, /Events affecting this forecast/);
});
