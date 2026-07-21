# IBOR Pack: Post-Fix End-to-End Validation

## Why this run exists

`data/ibor_portfolios.csv` previously hardcoded `SubHoldingKey1`/`SubHoldingKey2` as the
literal strings `Transaction/ibor-training-v7/Strategy` and
`Transaction/ibor-training-v7/CustodianAccount`, completely independent of the notebook's
`SCOPE` variable (`so-training-v1-1`). NB01 baked those literals into `sub_holding_keys` at
portfolio creation. NB03 builds transaction properties dynamically as
`Transaction/{SCOPE}/CustodianAccount`. The portfolio's registered SHK and the property the
transaction actually populates never matched, and the v7 property definition often doesn't
exist on the domain at all — hence `PropertyNotDefined (121)` on Serena's domain
(`fbn-serenah.lusid.com`) in NB03.

This has already been fixed in this pack:
- `data/ibor_portfolios.csv` — SHK columns now hold bare property names (`Strategy`,
  `CustodianAccount`), not scope-qualified strings.
- `NB01_Portfolio_Structure.ipynb` — builds the SHK key as `f"Transaction/{SCOPE}/{val}"` at
  creation time, matching the pattern NB03 already uses. Do not revert this to a literal
  string under any circumstances — that's exactly the bug.

**Do not re-litigate this decision.** The fix is scope-agnostic by design so a future scope
bump (`scope_rewrite.py`) can never desync SHKs from transaction properties again.

SHKs are immutable after portfolio creation. This means:
- A brand-new domain running the corrected pack from scratch needs no remediation — it's
  clean by construction.
- A domain that already ran the old (broken) pack — e.g. Serena's — has the seven affected
  portfolios (`IBOR-FI`, `IBOR-EQ`, `IBOR-MA`, `IBOR-SP500`, `IBOR-AITECH`, `IBOR-BLKC`,
  `IBOR-GAGG`) baked in wrong. `fix_stale_shk_portfolios.py` handles this: detect, delete,
  recreate. **This script has not been run against a live domain yet — treat its output as
  untested until you've confirmed it against a real API response.**

## Escalation protocol (do not skip)

Hard cap: 3-4 live API attempts per blocker before stopping and flagging to Nicholas for
escalation to Thomas Gemmell via Slack. Do not doom-loop on retries with minor variations.
If `fix_stale_shk_portfolios.py` throws an unexpected error on first run, read the actual
error body before changing anything — don't guess-and-retry blind.

## Step 1 — Clean-domain validation (mignot.lusid.com)

This is the control run: proves the fix works when there's no pre-existing stale state.

1. Confirm `secrets.json` is present via the multi-path lookup (working dir →
   `~/secrets.json` → `/home/jovyan/secrets.json` → `FBN_SECRETS_PATH`). Use
   `api_secrets_file=`, never `api_secrets_filename=`.
2. Run notebooks in order via papermill: `NB00` → `NB01` → `NB02` → `NB03` → `NB04` → `NB05`
   → `NB06` → `NB07` → `NB08` → `MEGA_VALIDATION`.
3. After NB01, inspect the created portfolios' `sub_holding_keys` directly via the API
   (`TransactionPortfoliosApi.get_details`) for all seven affected codes. Confirm each key
   reads `Transaction/so-training-v1-1/Strategy` and `Transaction/so-training-v1-1/CustodianAccount`
   — not `ibor-training-v7` anywhere.
4. After NB03, confirm no `PropertyNotDefined` errors were raised on any transaction load,
   for every portfolio, not just the previously-affected seven.
5. Run `MEGA_VALIDATION.ipynb` in full. Baseline is 52/52 checks passing — confirm it's still
   52/52 (or note exactly which checks changed and why, if the SHK fix altered any expected
   values).

Label every result explicitly as tested (ran against live API, saw the actual response) vs.
untested (code inspection only, not executed). Do not present untested code as if it had been
run.

## Step 2 — Remediation on affected domain (fbn-serenah.lusid.com)

This is a different domain and a different starting state — the stale portfolios already
exist. Do not skip to Step 3 until this is verified separately.

1. Get Serena's `secrets.json` for `fbn-serenah.lusid.com` (or confirm access another way —
   do not proceed on assumptions about credentials you don't have).
2. Run `python fix_stale_shk_portfolios.py --scope so-training-v1-1 --dry-run` first. Confirm
   it correctly identifies all seven portfolios as stale (or reports which ones aren't, if
   Serena's domain state differs from what's described here) before doing anything
   destructive.
3. If the dry run looks correct, run without `--dry-run`. Watch the actual delete and
   recreate calls succeed — don't assume success from the script printing "Recreated" without
   checking the response.
4. After recreation, transactions/holdings for those seven portfolios are gone (new portfolio,
   no history) — re-run NB03 onward for exactly those seven codes to reload them. Confirm no
   `PropertyNotDefined` errors this time.
5. Run `MEGA_VALIDATION.ipynb` (or the relevant subset) against this domain to confirm parity
   with Step 1's clean-domain result.

## Step 3 — Cross-check the master CSV assumption

The concern flagged was that other consultants might be running from the same stale
`ibor_portfolios.csv`. Since the CSV is now fixed in this pack, the residual risk is only for
consultants who already ran the *old* pack on their own domain before this fix landed. If
Nicholas provides a list of other domains, repeat Step 2 against each. Don't assume a domain
is clean without checking — `PropertyNotDefined` won't necessarily surface immediately if a
consultant hasn't reached NB03 yet.

## What "done" looks like

- Clean-domain run (`mignot.lusid.com`): all notebooks execute NB00→MEGA_VALIDATION with zero
  `PropertyNotDefined` errors, SHKs on all seven confirmed scope-correct, 52/52 (or documented
  delta) on MEGA_VALIDATION.
- Serena's domain: same end state after remediation, transactions reloaded, no errors on
  re-run.
- A short summary back to Nicholas stating explicitly which parts were tested live vs. code
  review only, and any check that didn't come back clean.
