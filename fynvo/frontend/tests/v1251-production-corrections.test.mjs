import assert from "node:assert/strict";
import test from "node:test";

import {
  accountFundingFallbackV1251,
  balanceDeltaV1251,
  commitmentScopeLabelV1251,
  normaliseDateKeyV1251,
  planningActionV1251,
} from "../src/productionCorrectionsV1251.js";

test("calendar date helper accepts Date objects and valid ISO dates", () => {
  assert.equal(normaliseDateKeyV1251(new Date(2026, 8, 16)), "2026-09-16");
  assert.equal(normaliseDateKeyV1251("2026-09-16"), "2026-09-16");
  assert.equal(normaliseDateKeyV1251("2026-02-31"), null);
  assert.equal(normaliseDateKeyV1251(new Date("invalid")), null);
});

test("partial commitment scope is labelled with its actual horizon", () => {
  assert.equal(
    commitmentScopeLabelV1251({
      incomplete: true,
      commitment_scope: { code: "generated_horizon", end_date: "2027-01-14" },
    }),
    "Known commitments to 14 Jan",
  );
  assert.equal(
    commitmentScopeLabelV1251({ commitment_scope: { code: "before_next_pay" } }),
    "Committed before next pay",
  );
});

test("planning actions point to the actual corrective destination", () => {
  assert.deepEqual(planningActionV1251("income"), {
    label: "Review income setup",
    destination: "Income",
  });
  assert.deepEqual(planningActionV1251("payments"), {
    label: "Review payments",
    destination: "Payments",
  });
  assert.equal(planningActionV1251("unknown"), null);
});

test("liquid account rows retain a funding state when cycle calculation is unavailable", () => {
  const fallback = accountFundingFallbackV1251(
    { id: 9, account_type: "transaction" },
    {
      status: "unavailable",
      reason: { code: "income_schedule_unavailable", action: "income" },
    },
  );
  assert.equal(fallback.status, "unavailable");
  assert.equal(fallback.setup_action, "income");
  assert.equal(
    accountFundingFallbackV1251({ id: 10, account_type: "mortgage" }, { status: "unavailable" }),
    null,
  );
});

test("balance review delta is explicit and safe for invalid edits", () => {
  assert.equal(balanceDeltaV1251("2671.00", "2812.42"), 141.42);
  assert.equal(balanceDeltaV1251("2671.00", ""), 0);
  assert.equal(balanceDeltaV1251("2671.00", "not-money"), null);
});
