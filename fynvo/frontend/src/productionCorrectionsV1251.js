export const PLANNING_ENDPOINTS_V1251 = {
  planning: "/payment-planning/v1251",
  safeToSpend: "/payment-planning/safe-to-spend/v1251",
  accountFunding: "/payment-planning/account-funding/v1251",
};

export const LIQUID_ACCOUNT_TYPES_V1251 = new Set([
  "transaction",
  "savings",
  "offset",
  "cash",
]);

export const SETUP_NEEDED_LABEL_V1251 = "Setup needed";

export function normaliseDateKeyV1251(value) {
  if (!value) return null;
  if (value instanceof Date) {
    if (Number.isNaN(value.getTime())) return null;
    return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
  }
  const key = String(value).slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(key)) return null;
  const [year, month, day] = key.split("-").map(Number);
  const parsed = new Date(year, month - 1, day);
  if (
    parsed.getFullYear() !== year ||
    parsed.getMonth() !== month - 1 ||
    parsed.getDate() !== day
  )
    return null;
  return key;
}

export function planningActionV1251(action) {
  return {
    income: { label: "Review income setup", destination: "Income" },
    accounts: { label: "Review accounts", destination: "Accounts" },
    payments: { label: "Review payments", destination: "Payments" },
    retry: { label: "Retry", destination: null },
  }[action] || null;
}

export function commitmentScopeLabelV1251(safe) {
  const scope = safe?.commitment_scope;
  if (!scope) return safe?.incomplete ? "Known commitments" : "Committed before next pay";
  if (scope.code === "before_next_pay") return "Committed before next pay";
  if (scope.code === "generated_horizon" && scope.end_date)
    return `Known commitments to ${new Intl.DateTimeFormat("en-AU", {
      day: "numeric",
      month: "short",
    }).format(new Date(`${scope.end_date}T00:00:00`))}`;
  return scope.label || "Known commitments";
}

export function accountFundingFallbackV1251(account, currentCycle) {
  if (!LIQUID_ACCOUNT_TYPES_V1251.has(String(account?.account_type || ""))) return null;
  if (currentCycle?.status === "unavailable") {
    return {
      account_id: account.id,
      status: "unavailable",
      title: "Unavailable",
      commitment_count: null,
      target_balance: null,
      cycle_end_date: null,
      funding_shortfall: null,
      funding_surplus: null,
      reason: currentCycle.reason || null,
      setup_action: currentCycle.setup_action || currentCycle.reason?.action || "retry",
    };
  }
  if (currentCycle?.status === "needs_setup") {
    return {
      account_id: account.id,
      status: "needs_setup",
      title: SETUP_NEEDED_LABEL_V1251,
      commitment_count: null,
      target_balance: null,
      cycle_end_date: currentCycle.cycle_end_date || null,
      funding_shortfall: null,
      funding_surplus: null,
      reason: currentCycle.reason || null,
      setup_action: currentCycle.setup_action || currentCycle.reason?.action || "income",
    };
  }
  return null;
}

export function balanceDeltaV1251(previous, next) {
  if (
    previous === null ||
    previous === undefined ||
    next === null ||
    next === undefined ||
    String(previous).trim() === "" ||
    String(next).trim() === ""
  )
    return null;
  const left = Number(previous);
  const right = Number(next);
  if (!Number.isFinite(left) || !Number.isFinite(right)) return null;
  return right - left;
}
