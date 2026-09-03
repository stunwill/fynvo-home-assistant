import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const household = fs.readFileSync(new URL('../src/HouseholdControlCenter.jsx', import.meta.url), 'utf8');
const app = fs.readFileSync(new URL('../src/AppV13.jsx', import.meta.url), 'utf8');
const css = fs.readFileSync(new URL('../src/household-v12.css', import.meta.url), 'utf8');


test('household management exposes the three approved roles', () => {
  assert.match(household, /administrator: 'Administrator'/);
  assert.match(household, /household_member: 'Household Member'/);
  assert.match(household, /read_only: 'Read Only'/);
  assert.match(household, /Add household member/);
  assert.match(household, /Deactivate/);
  assert.match(household, /Reactivate/);
  assert.match(household, /Reset password/);
  assert.match(household, /Reset MFA/);
  assert.match(household, /Revoke sessions/);
});


test('temporary-password users are forced through a password-change experience', () => {
  assert.match(app, /householdSecurity\?\.must_change_password/);
  assert.match(household, /Choose your own password/);
  assert.match(household, /change-temporary-password/);
  assert.match(household, /Please sign in again/);
});


test('household controls describe v1.3 permission boundary honestly', () => {
  assert.match(household, /Detailed financial permissions arrive in v1\.3\.0/);
  assert.match(household, /Full record visibility enforcement is intentionally deferred to v1\.3\.0/);
});


test('household management has phone and desktop responsive treatment', () => {
  assert.match(css, /@media\(max-width:800px\)/);
  assert.match(css, /@media\(max-width:420px\)/);
  assert.match(css, /max-width:1180px/);
  assert.match(css, /max-height:calc\(100dvh - 32px\)/);
});


test('household information is available from the authenticated app launcher', () => {
  assert.match(app, />Household<\/button>/);
  assert.match(app, /HouseholdControlCenter/);
  assert.match(app, /household\/me\/security/);
});
