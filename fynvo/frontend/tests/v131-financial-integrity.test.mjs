import test from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import CashIntegrityNotice, { spendingState } from "../src/CashIntegrityNotice.js";

test("positive household capacity remains provisional until the payment account is funded", () => {
  const safe = { safe_to_spend: null, funding_action_required: true, transferable_capacity: "850.00", recommended_transfers: [{ amount: "150.00", from_account_name: "Savings", to_account_name: "Bills", required_by: "2026-09-18" }] };
  const html = renderToStaticMarkup(React.createElement(CashIntegrityNotice, { safe }));
  assert.match(html, /Transfer required/);
  assert.match(html, /Provisional household capacity: \$850.00/);
  assert.match(html, /from Savings to Bills/);
  assert.match(html, /has not been applied/);
});

test("stale balances require confirmation even with positive capacity", () => {
  assert.equal(spendingState({ incomplete: true, safe_to_spend: null, transferable_capacity: "1000.00" }).title, "Confirm your cash position");
});

test("verified covered cash produces no action notice", () => {
  assert.equal(renderToStaticMarkup(React.createElement(CashIntegrityNotice, { safe: { safe_to_spend: "100.00", incomplete: false } })), "");
});

test("bank account names render as text", () => {
  const html = renderToStaticMarkup(React.createElement(CashIntegrityNotice, { safe: { funding_action_required: true, recommended_transfers: [{ amount: "1.00", to_account_name: "<script>alert(1)</script>", required_by: "2026-09-18" }] } }));
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;script&gt;/);
});

test("mixed calculation inputs suppress a positive spendable headline", async () => {
  const { coherentSpendingResult } = await import("../src/CashIntegrityNotice.js");
  const result = coherentSpendingResult({ safe_to_spend: "500.00", input_fingerprint: "old" }, [{ input_fingerprint: "new" }]);
  assert.equal(result.safe_to_spend, null);
  assert.equal(result.incomplete, true);
  assert.match(result.unavailable_reason.message, /changed during refresh/);
});
