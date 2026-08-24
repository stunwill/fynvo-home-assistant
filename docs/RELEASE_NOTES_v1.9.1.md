# Fynvo v1.9.1

## Recurring Expense Mobile Modal & Payment Fixes

Baseline: merged v1.9.0 (`main`, PR #44).

### Corrected

- The Recurring Expense editor is constrained below Fynvo's fixed 64 px mobile application bar so its title and close action are no longer obscured by the header.
- The recurring editor now uses a viewport-contained scroll region with a sticky dialog header and sticky Save/Cancel footer.
- Mobile form, Payment fieldset, inputs, selects and explanatory text are constrained to the available dialog width, removing the sideways movement shown in installed iPhone/Home Assistant ingress testing.
- Payment Method selection no longer immediately reverts to `Not Set`.

### Payment Method root cause

`RecurringPaymentFieldsV17.setMethod` previously invoked the parent field setter multiple times in the same event. The active editor setter is based on the render's `values` object, so each subsequent Account/Card clearing call was built from stale form state and overwrote the Payment Method selected by the first call. The corrective implementation performs Payment Method as a single state transition. Existing backend recurring-link resolution remains responsible for ignoring/clearing incompatible Account or Card relationships when the record is persisted.

### Modal root cause

Fynvo's mobile application bar is fixed at the top of the ingress viewport with a higher stacking order than the legacy modal backdrop. The generic modal also scrolled as one large surface and several nested form controls could establish widths larger than the available mobile content area. v1.9.1 adds a recurring-editor-specific responsive containment layer rather than globally hiding page overflow.

### Regression protection

- Existing v1.7 Payment Handling, Card/Account relationships, Scheduled Payments and reconciliation are preserved.
- Existing v1.8 Recurring Expenses List, Calendar, filters, summary and responsive page design are preserved.
- Existing v1.9.0 recurring edit/save and nullable-reference corrections are preserved.
- No database migration is required.

### Validation

Automated frontend coverage verifies the single Payment Method state transition, conditional Direct Debit/Card fields, linked Account presentation, mobile viewport containment, horizontal-overflow prevention, sticky modal controls and v1.9.1 stylesheet load order.

Installed iPhone/Home Assistant ingress acceptance remains a manual release gate before merge.
