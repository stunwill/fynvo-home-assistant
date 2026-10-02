# Redbark Open Banking in Fynvo

Fynvo 1.26.0 adds an optional Redbark Open Banking connection for importing actual bank balances and posted banking transactions into the existing Fynvo Accounts and Activity workflows.

## What it does

- Connects to the Redbark REST API using a backend-only API key.
- Discovers Redbark connections and bank accounts.
- Lets you map each discovered bank account to an existing Fynvo account, create a new Fynvo account, or ignore the bank account.
- Synchronises current and available balances where Redbark reports them.
- Imports posted transactions with stable Redbark transaction identifiers.
- Uses a seven-day overlap on incremental transaction syncs and provider transaction IDs for idempotent deduplication.
- Runs an automatic backend sync approximately every 30 minutes, with a manual **Sync now** action available from **Settings · Bank connections**.
- Preserves the last successful balances and transaction history if Redbark or a connected bank is temporarily unavailable.
- Keeps imported transactions available to Fynvo's existing Activity and reconciliation workflows.

Fynvo does not initiate bank payments, transfers or other write operations against bank accounts.

## Redbark API requirements and verified behaviour

The integration targets Redbark API v1 at `https://api.redbark.com` and uses Bearer API-key authentication.

The current Redbark API exposes:

- `GET /v1/connections`
- `GET /v1/accounts`
- `GET /v1/balances?accountIds=...`
- `GET /v1/transactions?connectionId=...`

### Household connections and ownership

A provider configuration (credential), a bank connection (consent), a discovered bank account, and a Fynvo planning account are separate records. One Redbark key may return multiple connections; Fynvo keeps two connections to ING separate by stable connection IDs, and identically named Orange Everyday accounts separate by stable account IDs. Institution names, account names, owner labels and masked suffixes are not identity keys.

Connections can have an editable household label and optional owner chosen from active household members. This describes the connection; it does not transfer bank consent, change provider identity, change an already-linked Fynvo account's household ownership or grant new access. A newly created Fynvo account inherits the connection's chosen household owner; an existing account keeps its own owner when linked. Household account ownership remains managed under Household settings. Manual Fynvo accounts remain valid without a bank mapping or warning.

The database separates provider configuration from its connections so additional credential identities can be represented in future. **Fynvo currently supports one configured Redbark API key per installation.** Redbark's published developer material describes a key accessing the signed-in customer's own linked connections, but does not verify that a second household member can establish another same-bank consent under that key. Fynvo therefore does not present an unverified second-key or second-consent flow. A generic Fiskil authorisation failure does not establish a Fynvo defect. Check the consent in Redbark and contact Redbark/Fiskil support for a second customer's failed authorisation.

Redbark's dashboard may show **Add to sync** for discovered accounts. The documented Fynvo adapter has read-only connections, accounts, balances and transactions operations; it has no verified account-activation call. If balances are unavailable, check Redbark's account sync/destination setup. Fynvo never turns an absent bank balance into a reported $0 or a false update time. A new mapped Fynvo account requires an explicit manual starting balance if Redbark supplies none; a later successful bank sync replaces that provisional balance.

The connection reports its last successful account discovery and its last successful sync separately. Account rows date the bank balance only when that balance was actually received; a transaction refresh does not imply a fresh balance. Mapped transactions can import while balances are unavailable, and the partial connection health remains visible. A failure for one connection does not erase another's health or block its next background sync. Historical balances and transactions survive disconnection.

Accounts and transactions are paginated using limit/offset pagination. Fynvo requests up to 200 records per page and follows `hasMore` until the available result set has been processed.

Redbark currently documents a 30 authenticated requests-per-minute rate limit. Fynvo keeps scheduled syncs conservative and handles `429` responses without discarding last-known banking data.

### Pending transaction limitation

Although the Redbark transaction endpoint exposes an `includePending` query switch, Redbark's current public documentation describes the banking feed as posted-transaction data. Fynvo 1.26.0 therefore deliberately treats Redbark as a posted-only source and does not manufacture pending transaction states.

## Setup

1. Create or obtain a Redbark API key through Redbark.
2. Ensure the desired bank connections/consents have been established in Redbark.
3. Open Fynvo.
4. Open **Tools → Settings · Bank connections**.
5. Paste the Redbark API key and choose **Connect Redbark**.
6. Review each discovered account.
7. Map it to an existing Fynvo account, create a new Fynvo account, or ignore it.
8. Choose **Sync now** for the first transaction synchronisation.

The API key is stored in Fynvo's Home Assistant add-on data directory in a backend-only file with owner-only file permissions. The frontend receives only a configured/not-configured state. The key is never returned by Fynvo's API.

## Balance semantics

Fynvo keeps three concepts separate:

### Actual bank balance

The current balance reported by Redbark. Fynvo uses it to reconcile the mapped account's actual ledger position while preserving transaction history.

### Planned or forecast balance

A Fynvo calculation based on current account state plus future income, bills, recurring expenses and other planning events. Provider synchronisation does not overwrite forecast values.

### Safe-to-Spend

A Fynvo planning calculation based on its existing pay-cycle, commitment and buffer rules. It is not simply the bank balance minus bills.

## Transaction synchronisation

The first sync requests the history Redbark makes available for the mapped connection/account. Later syncs use the last successful sync date with a seven-day overlap so that recently-posted or corrected transactions can be seen again safely.

Redbark transaction IDs are the primary deduplication key. Repeating **Sync now** does not create a second copy of a transaction with the same provider identifier.

Manual Fynvo transactions are not silently deleted or merged with imported banking transactions.

## Failures and stale data

A provider failure does not zero an account or delete imported history. Fynvo keeps the last successful balance and transactions and records that the connection or account needs attention.

When a multi-account connection partially fails, successful account updates remain committed and failed accounts retain their previous known state for later retry.

## Disconnecting

Disconnecting a bank or removing the Redbark API key stops future synchronisation. It does not delete existing Fynvo accounts or imported transaction history.

## Privacy and CDR responsibility

Redbark operates within Australia's Consumer Data Right ecosystem and currently describes itself as a CDR Representative of its accredited data recipient partner. Fynvo itself does not claim to be an Accredited Data Recipient.

Once banking data is synchronised into Fynvo's local Home Assistant add-on storage, that copy is controlled by the Fynvo installation. Protect Home Assistant access, backups and exported data accordingly.

## Troubleshooting

**Redbark rejected the API key**

Replace the API key from Bank connections and test again.

**Bank data could not be refreshed**

The previous successful data remains available. Use **Test connection**, then **Sync now** after the provider/bank is available again.

**An account is missing**

Choose **Refresh accounts**. If it remains missing, confirm that the account is part of an active Redbark connection/consent.

**Transactions did not appear immediately**

Redbark data may depend on the connected institution's refresh cycle. Fynvo imports the posted transactions returned by Redbark and does not fabricate pending activity.
