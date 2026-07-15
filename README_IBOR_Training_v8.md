# IBOR Implementation Training Pack — v8

Scope: `ibor-training-v9`  |  Quote scope: `ibor-training-v9-quotes`  |  SDK: Python (SDK v3)

## Contents
- NB00–NB08 Jupyter notebooks
- IBOR_Implementation_Training_Guide.html (implementation guide + data/events reference)

## How to run
1. Create a fresh `ibor-training-v9` scope (or run against an empty one).
2. Place the nine notebooks beside your `data/` folder of CSVs and `secrets.json`.
3. Run NB00 → NB08 in order on the "Python (SDK v3)" kernel.
   - After a kernel restart, run the first (auth) cell of a notebook before any other cell.

## Notebook sequence
| NB | Purpose |
|----|---------|
| NB00 | Instrument enrichment + market data (equities, bonds, OTC, F&O, all quotes, FX) |
| NB01 | Portfolio structure, sub-holding keys, CA source (IBOR-CA-SOURCE-V3) |
| NB02 | Transaction type configuration (incl. F&O lifecycle types) |
| NB03 | Transaction loading (equity, FI, MA, OTC, iShares portfolios) |
| NB04 | Holdings & position management |
| NB05 | Corporate actions (AAPL 2:1 split) + F&O expiry/exercise events |
| NB06 | Valuation recipe + valuations (grouped by name + SubHoldingKey) |
| NB07 | Reconciliation |
| NB08 | Luminesce showcase queries |

## Key design decisions baked in
- **OTC as SimpleInstrument:** IRS, Term Deposit and the Zero Coupon Bond are created as
  `SimpleInstrument` (not native types), priced from monthly MTM quotes. Native
  `InterestRateSwap`/`TermDeposit` pricing models produce unrealistic valuations; native
  zero-coupon `Bond` is rejected for zero payment frequency.
- **Futures:** created without the `convention` field (rejected by FuturesContractDetails).
- **FX:** all iShares currency pairs loaded in slash + dot formats, as Price + Rate;
  recipe carries an `Fx.*.*` rule with `suppliers={"Fx": "Client"}`.
- **Valuation grouping:** group by instrument name **and** `Holding/default/SubHoldingKey`.
  Grouping by name alone collapses any instrument spanning two SHK buckets to a null PV.
- **Valuation date:** fixed at 2024-09-30 (full holdings + quote coverage). A
  "latest priceable date" probe is unreliable here because near-empty early dates
  trivially succeed.
- **IEC recipe link:** NB01 attempts it and skips cleanly if the recipe doesn't exist yet
  (the recipe is created in NB06).

## Expected valuation totals (2024-09-30, grouped by name + SHK)
| Portfolio | Total MV |
|-----------|----------|
| IBOR-EQ | ~$12.0M |
| IBOR-FI | ~$29.0M |
| IBOR-MA | ~$21.6M |
| IBOR-SP500 | ~$50.2M |
| IBOR-AITECH | ~$10.3M |
| IBOR-BLKC | ~$5.1M |
| IBOR-GAGG | ~$130.9M |

## Note
Verified end-to-end by live execution against a fresh `ibor-training-v9` scope (NB00→NB08 +
MEGA_VALIDATION: 52/52 checks pass). Bond coupon rates in the CSVs are percentages (e.g. 4.50);
NB00 divides by 100 when building `Bond`/`ComplexBond` definitions so LUSID receives a decimal
coupon (0.045). The FI/MA totals above reflect that corrected coupon (an earlier draft passed the
raw percentage, which made LUSID's analytic bond model value a $1M-face bond at ~$21M).


## Data files (`data/` folder)
The `data/` folder contains all 28 CSVs. Place it beside the notebooks (the notebooks read
from `data/...`). 24 are loaded directly by the notebooks; the rest are provenance:

- **Source (iShares fund holdings):** AGSGDX_holdings.csv, BLKC_holdings.csv, GSPX_holdings.csv
  (used to derive the iShares portfolios; not loaded at runtime).
- **Instruments:** ibor_equities.csv, ibor_equities_new.csv, ibor_bonds_vanilla.csv,
  ibor_bonds_complex.csv, ibor_bonds_gagg.csv, ibor_futures_options.csv, ibor_otc_definitions.csv
- **Market data:** ibor_market_data_equity.csv, ibor_market_data_new_equities.csv,
  ibor_market_data_bonds.csv, ibor_market_data_gagg.csv, ibor_market_data_futures_options.csv,
  ibor_market_data_fx.csv, ibor_market_data_sofr.csv
- **Transactions:** ibor_transactions_{equity,fi,ma,otc,cash,sp500,aitech,blkc,gagg}.csv
- **Reference:** ibor_portfolios.csv, ibor_custodian_positions.csv

Note: the ZCB row in ibor_bonds_vanilla.csv carries PaymentFrequency=0Y; NB00 handles this by
creating the zero coupon bond as a SimpleInstrument rather than a native Bond.
