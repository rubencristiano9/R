# V5 models in Tape Reader: how to run, read and check them

## What it is
The Strategy panel has a row **"V5 frozen models — NQ (trades from R)"** with four rules:

| Button | Model | Inputs | Hold | Frozen thresholds (BUY ≥ / SELL ≤) |
|---|---|---|---|---|
| 7m XGB NQ+ES · 1% | XGBoost depth 2 | NQ + ES, 118 | 7 min | 0.5751 / 0.4249 |
| 7m XGB NQ+ES · 5% | same model as 1% | NQ + ES, 118 | 7 min | 0.5604 / 0.4396 |
| 7m Ranger NQ · 2% | ranger forest | NQ, 64 | 7 min | 0.5700 / 0.4300 |
| 1m XGB NQ · 10% | XGBoost depth 2 | NQ, 64 | 1 min | 0.5628 / 0.4372 |

**The model never runs in the page.** R already decided every trade, meaning the minute and the side.
The page replays those trades. Each trade enters at the open of that minute and exits 7 (or 1) minutes
later at the close.

Stop, target, size, costs and the firm's rules come from the panel, like any other strategy. They were
not part of the model's test. The history covers 2023-01-03 to 2026-03-13. Each year's trades come from
a model fitted only on earlier years, so all of it is out of sample.

## What to run, once, in this order
1. **Export the trades (R, on your PC).** Put `V5_EXPORT_TRADES.R` next to
   `NQ_ES_ROLLSAFE_WALKFORWARD_V5.R` and your Databento NQ/ES files, then run it. It:
   - runs V5's data and feature code only (V5's own folder is not touched);
   - refits the four rules year by year exactly as V5 did;
   - writes `v5_trades/` only if every year's cutoff, trade count and win count equal
     `nq_es_rollsafe_walkforward_v5/08_walkforward_fold_results.csv`. Otherwise it stops and writes
     nothing.

   Until you run it, only the 7m/1% rule is available, from V5's own file 16. The other three are
   listed as "not yet".
2. **Copy files next to `build_viewer3.py`:**
   - the `v5_trades` folder;
   - `NQ_1min_2010-06-07_to_2026-03-13_databento.csv`, for the overnight bars.
3. **Build as usual:**
   `python3 build_viewer3.py && python3 lint_viewer.py && python3 test_core.py && python3 test_v5.py`

   The build prints how the full-session tape matched your RTH tape. It must say 100% or very close,
   or the build stops. The first build reads the big file (about 30 s). Later builds use the cache,
   `full_tape_nq.json`.

## What you see
- **Full session** button (Data bar): every NQ minute from 18:00 to 16:59 New York, one day per CME
  trading day. A Sunday 18:00 bar belongs to Monday. Demo goes back to the 09:30–15:59 tape.
  - Picking a V5 rule switches to the full-session tape. About 90% of its trades are overnight.
  - Picking any other rule switches back, because those rules were built on 09:30–15:59.
- **Flat by** is now the firm's end of day, the clock time you must be flat by. The Lucid presets set
  16:45: anything open is closed at the end of the 16:44 bar (16:45:00), and nothing opens in that
  minute or later.
  - A strategy's own earlier exit still wins. The last-hour rules keep 15:49.
  - Settings saved before this change run the same trades as before.
  - To add another firm, add an entry to `LUCID_PRESETS` with its own `flatBy`.
- **Count line** (Result block): "Trades: 701 in the list · N on this tape · taken · stood aside (why) ·
  not reached". "Not reached" means after the flat-by, or after the day ended at the cap, pass or
  payout line. If the numbers don't add up, look there first.
- **Hover a trade:** the chart tooltip and the ledger row show that trade's model time (UTC), score and
  year, whether V5 recorded it right, and its row number in R's file. Any single trade can be checked
  against the CSV by hand.

## If a check fails
| Message | Meaning / what to do |
|---|---|
| `v5_pack ... has N trades / W wins; V5 recorded ...` | A trade file doesn't match V5. Re-run the export. Don't edit the file by hand. |
| `... must be UTC (end in Z or +00:00)` | A time lost its zone (e.g. after opening in Excel). Use the file exactly as R wrote it. |
| `... does NOT reproduce V5 ...` (R) | The refit differs from V5, e.g. other package versions. Compare `v5_trades/00_check.csv` with V5's `00_package_versions.csv`. |
| `full-session tape does not move like the built-in RTH tape` | The Databento file is not the one the RTH tape came from. The worst days are listed. |
| "Full session" button greyed out | The Databento file wasn't next to the build. |

## Timestamps (the easiest thing to get wrong)
V5's `signal_et` is **UTC** and marks the **end** of the bar the model read. Example: `14:45:00Z` is a
09:45 New York trade, made from the 09:44 bar and entered at the 09:45 open. `test_v5.py` pins this
against the tape: the tape's move matches V5's right/wrong on all 69 RTH trades that have a prior bar.

## Known limits
- Timeframes above 1m group a fixed number of bars, not clock time. On the overnight tape a minute with
  no trade therefore shifts later candles slightly. This is the same as any all-hours file loaded before.
  D is always one whole day.
- Time-of-day shading and marks set between 18:00 and 23:59 don't draw on the full-session tape.
- The R export and the real Databento file can only run on your PC. Here they were tested on
  synthetic stand-ins (`test_v5_export.R`, `test_full_tape.py`). None of that synthetic data is in the
  repo or in any page.
