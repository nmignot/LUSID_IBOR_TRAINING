"""
Remediation for PropertyNotDefined (121) on Transaction/ibor-training-v7/CustodianAccount.

Root cause: data/ibor_portfolios.csv previously hardcoded SubHoldingKey1/2 as
"Transaction/ibor-training-v7/Strategy" and "Transaction/ibor-training-v7/CustodianAccount"
literal strings, independent of SCOPE. NB01 baked these into the portfolio at creation.
NB03 builds transaction properties dynamically off SCOPE (e.g. "so-training-v1-1"), so the
portfolio's registered SHK never matched the transaction property actually being populated,
and the v7-scoped property definition frequently does not exist on the domain at all.

SubHoldingKeys are immutable once a portfolio is created, so the fix for portfolios that
already exist with the stale SHK is: delete and recreate from the corrected CSV (already
fixed in this pack) and corrected NB01 (already fixed in this pack).

This script:
  1. Checks each of the seven affected portfolios for the stale v7 SHK.
  2. Deletes any that have it.
  3. Recreates them using the corrected CSV + current SCOPE.
  4. Leaves already-correct portfolios untouched (idempotent / safe to re-run).

Does NOT touch IBOR-CASH (no SHKs, unaffected).

Usage:
    python fix_stale_shk_portfolios.py --domain fbn-serenah.lusid.com --scope so-training-v1-1

Run this once per affected consultant domain before re-running NB03+.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd
import lusid as lu
import lusid.models as lm

AFFECTED_CODES = [
    "IBOR-FI", "IBOR-EQ", "IBOR-MA", "IBOR-SP500",
    "IBOR-AITECH", "IBOR-BLKC", "IBOR-GAGG",
]
# LUSID error 165 (FailedToDelete) blocks deleting a parent portfolio while derived
# portfolios reference it, so any derived children of an affected parent must be
# deleted first and recreated after. Mirrors NB01_Portfolio_Structure.ipynb's `derived` list.
DERIVED_PORTFOLIOS = [
    {"code": "IBOR-MA-USD", "name": "Multi Asset (USD Share Class)", "parent": "IBOR-MA"},
    {"code": "IBOR-MA-GBP", "name": "Multi Asset (GBP Share Class)", "parent": "IBOR-MA"},
]
STALE_SHK_MARKER = "ibor-training-v7"
DATA_DIR = "data"
CSV_PATH = f"{DATA_DIR}/ibor_portfolios.csv"


def get_factory(secrets_path="secrets.json"):
    candidates = [
        secrets_path,
        os.path.expanduser("~/secrets.json"),
        "/home/jovyan/secrets.json",
        os.environ.get("FBN_SECRETS_PATH", ""),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            with open(path) as f:
                secrets = json.load(f)
            api_section = secrets.get("api", {})
            pat = api_section.get("accessToken")
            if pat:
                config_loaders = [lu.extensions.ArgsConfigurationLoader(
                    api_url=api_section.get("lusidUrl", ""),
                    access_token=pat,
                )]
            else:
                config_loaders = [lu.extensions.SecretsFileConfigurationLoader(path)]
            return lu.extensions.SyncApiClientFactory(config_loaders=config_loaders)
    raise FileNotFoundError(f"No secrets.json found in any of: {candidates}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", required=True, help="Current training scope, e.g. so-training-v1-1")
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not delete/recreate")
    args = parser.parse_args()

    scope = args.scope
    factory = get_factory()
    portfolios_api = factory.build(lu.PortfoliosApi)
    txn_portfolios_api = factory.build(lu.TransactionPortfoliosApi)

    df_ports = pd.read_csv(CSV_PATH)
    df_ports = df_ports[df_ports["PortfolioCode"].isin(AFFECTED_CODES)]

    to_fix = []
    for code in AFFECTED_CODES:
        # get_portfolio belongs to PortfoliosApi, not TransactionPortfoliosApi (confirmed pattern
        # from this project's prior debugging). sub_holding_keys is on the transaction portfolio,
        # so read it via the transaction portfolios endpoint.
        try:
            portfolios_api.get_portfolio(scope=scope, code=code)
        except lu.ApiException as e:
            if "PortfolioNotFound" in str(e.body) or getattr(e, "status", None) == 404:
                print(f"  {code}: does not exist on this domain, skipping")
                continue
            raise

        try:
            tp = txn_portfolios_api.get_details(scope=scope, code=code)
            registered_shks = tp.sub_holding_keys or []
        except lu.ApiException as e:
            print(f"  {code}: could not read SHKs ({str(e.body)[:150]}), skipping")
            continue

        is_stale = any(STALE_SHK_MARKER in shk for shk in registered_shks)
        if is_stale:
            print(f"  {code}: STALE v7 SHK detected -> needs delete+recreate")
            to_fix.append(code)
        else:
            print(f"  {code}: SHK already correct, leaving untouched")

    if not to_fix:
        print("\nNo affected portfolios found on this domain. Nothing to do.")
        return

    if args.dry_run:
        print(f"\nDry run: would delete and recreate {to_fix}")
        return

    children_to_recreate = [d for d in DERIVED_PORTFOLIOS if d["parent"] in to_fix]
    for d in children_to_recreate:
        print(f"\nDeleting derived child {d['code']} (blocks parent {d['parent']} delete)...")
        try:
            portfolios_api.delete_portfolio(scope=scope, code=d["code"])
            print(f"  Deleted {d['code']}")
        except lu.ApiException as e:
            if "PortfolioNotFound" in str(e.body):
                print(f"  {d['code']} does not exist, nothing to delete")
            else:
                print(f"  Delete failed for {d['code']}: {str(e.body)[:200]}")

    for code in to_fix:
        print(f"\nDeleting {code}...")
        try:
            portfolios_api.delete_portfolio(scope=scope, code=code)
            print(f"  Deleted {code}")
        except lu.ApiException as e:
            print(f"  Delete failed for {code}: {str(e.body)[:200]}")
            continue

    print("\nRecreating from corrected CSV...")
    for _, row in df_ports[df_ports["PortfolioCode"].isin(to_fix)].iterrows():
        shks = []
        for col in ["SubHoldingKey1", "SubHoldingKey2"]:
            val = str(row.get(col, "")).strip()
            if val and val != "nan":
                shks.append(f"Transaction/{scope}/{val}")

        props = {}
        for prop_code, csv_col in [
            ("Region", "Region"), ("FundType", "FundType"),
            ("PortfolioManager", "PortfolioManager"),
            ("Benchmark", "Benchmark"), ("InvestmentStrategy", "InvestmentStrategy"),
        ]:
            if pd.notna(row.get(csv_col)) and str(row[csv_col]).strip():
                key = f"Portfolio/{scope}/{prop_code}"
                props[key] = lm.ModelProperty(
                    key=key, value=lm.PropertyValue(label_value=str(row[csv_col]).strip())
                )

        try:
            txn_portfolios_api.create_portfolio(
                scope=scope,
                create_transaction_portfolio_request=lm.CreateTransactionPortfolioRequest(
                    display_name=row["DisplayName"],
                    code=row["PortfolioCode"],
                    base_currency=row["BaseCurrency"],
                    created=datetime(2024, 1, 1, tzinfo=timezone.utc),
                    sub_holding_keys=shks,
                    corporate_action_source_id=lm.ResourceId(scope=scope, code="IBOR-CA-SOURCE-V3"),
                    instrument_scopes=[scope],
                    properties=props if props else None,
                )
            )
            print(f"  Recreated {row['PortfolioCode']} with corrected SHKs: {shks}")
        except lu.ApiException as e:
            print(f"  Recreate failed for {row['PortfolioCode']}: {str(e.body)[:200]}")

    if children_to_recreate:
        print("\nRecreating derived children...")
        for d in children_to_recreate:
            try:
                body = {
                    "displayName": d["name"],
                    "code": d["code"],
                    "parentPortfolioId": {"scope": scope, "code": d["parent"]},
                }
                response_data = txn_portfolios_api.api_client.call_api(
                    f'/api/derivedtransactionportfolios/{scope}', 'POST',
                    path_params={}, query_params=[],
                    header_params={'Content-Type': 'application/json', 'Accept': 'application/json'},
                    body=body, post_params=[], files={},
                    response_types_map={},
                    auth_settings=['oauth2'], _return_http_data_only=False,
                    collection_formats={}, _preload_content=True, _request_timeout=None,
                )
                resp_body = json.loads(response_data.raw_data)
                print(f"  Recreated derived: {d['code']} (isDerived={resp_body.get('isDerived')})")
            except lu.ApiException as e:
                print(f"  Recreate failed for derived {d['code']}: {str(e.body)[:200]}")

    fixed_and_children = to_fix + [d["code"] for d in children_to_recreate]
    print(f"\nDone. Re-run NB03 onward for: {fixed_and_children}")
    print("Note: transactions/holdings for these portfolios must also be reloaded since the portfolio was recreated.")


if __name__ == "__main__":
    main()
