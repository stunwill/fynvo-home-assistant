# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v1.9.0 - Recurring Expense Management, Workflow Completion & Regression Fixes

### Fixed
- Restored reliable edit/save for existing and legacy Recurring Expenses by sending the complete v1.7/v1.9 payment model through the active update route.
- Closed the three-dot action menu before Edit or Mark as Paid opens, preventing stale menus from covering mobile modal actions.
- Scoped Recurring Expense errors to their workflow and clears them when navigating away or closing the edit modal.
- Reconciled Category integrity warnings with every backend issue class and added expandable issue details instead of an unexplained headline count.

### Added
- Added an explicit "Automatically mark scheduled payments as paid" control independent of Payment Method.
- Added End Date and reminder fields to the active Recurring Expense editor, while preserving Payment Method, Card to Account derivation, fixed/variable amount and Payee/Merchant fields.
- Automatic scheduled occurrences transition to Paid exactly once using the existing unique occurrence key. Manual payments remain Due/Overdue until actioned.
- Added v1.9 regression tests for modal lifecycle, error state, automatic handling, calendar recurrence and Category health presentation.

### Compatibility
- v1.8.0 remains the visual baseline.
- Existing recurring, Account, Card, Category, forecasting and Scheduled Payment data is preserved. No destructive migration is introduced.

## v1.8.0 - Recurring Expenses Responsive UI/UX Completion

See `docs/RELEASE_NOTES_v1.8.0.md` for the complete v1.8.0 implementation history. Earlier release history remains available in the repository release-note documents and Git history.
