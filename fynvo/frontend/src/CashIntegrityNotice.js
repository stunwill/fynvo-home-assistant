import React from "react";

export function coherentSpendingResult(safe, peers = []) {
  if (!safe) return null;
  const mismatch = safe.input_fingerprint && peers.some((peer) => peer?.input_fingerprint && peer.input_fingerprint !== safe.input_fingerprint);
  if (!mismatch) return safe;
  return { ...safe, safe_to_spend: null, incomplete: true, unavailable_reason: { message: "Your finances changed during refresh. Refresh again to confirm available cash." } };
}

export function spendingState(safe = {}) {
  const capacity = safe.transferable_capacity;
  const reason = safe.unavailable_reason?.message;
  if (safe.funding_action_required) {
    return { title: "Transfer required", capacity, reason, transfers: safe.recommended_transfers || [] };
  }
  if (safe.incomplete || safe.safe_to_spend === null) {
    return { title: "Confirm your cash position", capacity, reason, transfers: [] };
  }
  return { title: null, capacity: null, reason: null, transfers: [] };
}

export default function CashIntegrityNotice({ safe }) {
  const state = spendingState(safe);
  if (!state.title) return null;
  const h = React.createElement;
  return h("aside", { className: "fynvo-cash-integrity", role: "status" },
    h("strong", null, state.title),
    state.reason && h("p", null, state.reason),
    state.capacity != null && h("p", null, `Provisional household capacity: $${state.capacity}`),
    ...state.transfers.map((transfer, index) => h("p", { key: index },
      `$${transfer.amount} from ${transfer.from_account_name || "another account"} to ${transfer.to_account_name || "the payment account"} by ${transfer.required_by}. This recommendation has not been applied.`)),
  );
}
