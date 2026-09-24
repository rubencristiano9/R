# HANDOFF — read this first

Context primer for a new Claude session working in `C:\Users\ruben\nq-backtest`.
Everything below is current as of 2026-09-02.

---

## 1. What exists

Two published artifacts. Both are owned by the user and update in place.

| | URL | What it is |
|---|---|---|
| **The Rolling Exam** | `claude.ai/code/artifact/99bede0c-9845-4d8e-87b7-f34e97bbf593` | Research dashboard: NQ/RTY walk-forward Stage 1+2, PBO, DSR, seasonality, factor-zoo, and Part Five prop-firm economics |
| **Tape Reader** | `claude.ai/code/artifact/1d721854-2245-4e2e-94f3-fdda5fcaa193` | Standalone TradingView-style chart + trade journal + prop-firm simulator. **Active development.** |

The user's goal for Tape Reader: *"my underlying thing I go to all the time for journaling,
for testing, for everything"* — eventually usable live.

---

## 2. The build chain (Tape Reader)

```
viewer_core.js          all real logic, ES5, no DOM. THE tested module.
build_viewer3.py        embeds viewer_core.js + continuous.json -> tape_reader.html
continuous.json         315,900 bars, 4,670 trades, volume. Built by build_continuous.py
test_core.py            250 assertions, runs viewer_core.js headlessly under dukpy
lint_viewer.py          52 checks on the built HTML, incl. an esprima parse gate
check_series_real.py    end-to-end prop-firm pass/fail table on the real trades
regen_payout_panels.py  rebuilds wealth_panel.json + sizing_panel.json by driving
                        Core.runStrategy in Chrome ($900 payout, account carries on).
                        Its printed medians are what test_ui.py's EXPECT pins.
build_news_calendar.py  builds news_calendar.json for the 'custom' Strategy entry;
                        run before build_viewer3.py. See the 2026-09-21 entry below.
```

Strategy panel, Ensemble block (2026-09-17): every press draws a fresh base seed and runs
N = 10/25/50/100/1000 consecutive seeds off the chart in 40 ms slices (Core.runStrategy +
Core.wealthCurve; 1000 takes 1-4 s). Up to 100 runs are drawn as lines, above that as
5-95 and 25-75 percentile bands, with the median; the run on the chart (STRES) is drawn
and ranked against the batch. Tied to a settings signature (ensSig) so a rule change
marks it stale but a seed change does not.

Instruments and the bar loader (2026-09-18): the Strategy panel's size ladder is now an
Instrument row (NQ MNQ ES MES RTY M2K CL MCL GC MGC VX, `INSTRUMENTS` in build_viewer3.py)
that sets $/pt, commission (micros $0.50, minis $1.75 a side) and one tick of slippage,
plus a Contracts row 1-10. `barsFromCSV` converts timestamps that carry a UTC offset
(databento's `+00:00`) to New York time and, with the RTH toggle in the Data bar on
(default, `S.rthOnly`), cuts to 09:30-15:59 -- exactly how the shipped NQ tape was built.
Before this it took the clock as written, so a databento "10:00" traded at 06:00 ET and
the "16:00 close" ran at 16:59. The subtitle now says what was done to the clock. The
user's files live in `OneDrive ...\Documents\Trading\Programming Stuff\Data for
Backtesting\databento` (1-min CL ES GC NQ RTY VX, 2010-2026, all UTC, all hours); the full
335 MB ES file loads in ~7 s. Finding: at 4 contracts and the right $/pt, the coin's
economics on ES match NQ (median net +$28k vs +$27k over 100 seeds, 24 mo); what looked
like "ES is much worse" was $/pt and contracts left on NQ values.

Five markets, one coin (2026-09-18): `underlying_sweep.py` loads each databento file through
the page's loader and runs Core.runStrategy in Chrome (NQ ES RTY CL GC; 1-10 micros and
1-10 minis; $250/$500/$1,000 a trade aimed one-shot at $2,150; 200 seeds; 24 months from
2024-03-13). `underlying_summary.py` -> `underlying_summary.json`; `build_underlying.py` ->
`underlying.html`, published as https://claude.ai/artifact/H3UvqgNfrx352UufsEnqX6. Result at
$1,000 a trade, best size each: NQ +$60k (1 NQ, 50-pt stop), RTY +$57k, GC +$51k, ES +$45k,
CL +$38k median net at one tick of slippage and $1.75/$0.50 commissions. Re-run with Lucid's
commissions and each market's NORMAL slippage preset (ES 1 tick, others 2): NQ +$59k, ES
+$45k, RTY +$45k, GC +$41k, CL +$23k -- the ES/RTY/GC order turns on the slippage
assumption, NQ first and CL last do not. Size moves the answer far more than market. Both
runs after the pass-line fix; the page shows the second.

Presets, costs (2026-09-18, later): `INSTRUMENTS` now carries Lucid Trading's published
per-side commissions (NQ/ES/RTY $1.75, CL $2.00, GC $2.30, MNQ/MES/M2K/MCL $0.50, MGC $0.80)
and three slippage assumptions per contract, `slip: [generous, normal, conservative]` in
points a side: ES 0/1/2 ticks (one ES tick is already 0.5% of a median day), the rest
1/2/4 ticks. Picking an instrument sets the normal figure; three buttons under the slippage
box switch it for the instrument the stage is on (`instOf`). VX was dropped (not on Lucid's
list, no timestamps in its files). The ResizeObserver callback now defers the canvas resize
to the next frame and the error strip ignores the browser's "ResizeObserver loop" notice,
which a 300 MB load used to surface as an error. `_patch_lucid_slippage.py` is spent.

Five Markets v2 (2026-09-19): `underlying_sweep2.py` -> `underlying_summary2.py` ->
`build_underlying.py` (v1 kept as `build_underlying_v1.py`; stylesheet in `_underlying_style.txt`).
Objective is return per dollar of tickets. Stage 1: 5 markets x 20 sizes x risk {250, 500, 750,
1,000} x target {1,000, 1,500, 2,150}, both stages alike, 100 seeds (1,200 cells). Stage 2:
evaluation size x risk {500, 1,000} against funded size at $1,000 one-shot (4,000 pairings).
Every evaluation trade tallied target / stop / close and compared with the driftless-walk
target-first probability risk/(risk + 625 + round turn). Results: best cell NQ 1 NQ, $1,000,
one-shot: ROI 218% (188-260), net $57k, pass 36.3%; every market's best risks the full $1,000;
one-shot wins everywhere but GC ($1,500). Split sizing: NQ eval 3 MNQ / funded 1 NQ gives ROI
233% but net $35k (fewer tickets). Pass-rate gap NQ 36% vs CL 31%: friction moves the walk
61.0% -> 59.8%, the path takes NQ to 58.9% and CL to 47.6%; cap-day rate squared tracks it.
Same artifact URL, version 3.

Ten markets (2026-09-19, later): `databento_extract.py` turns the parent-symbol batch zips in the
databento folder into continuous 1-min CSVs in the existing shape (volume roll over the previous
five days, forward only, reset if the front goes quiet; spreads dropped; Cboe `VX/Z5` symbols
handled). New files: YM, SI, HG (2010-2026-08), HE (2021-2026-09), NKD (2010-2026-09), VX with
timestamps (2018-2026-08), and ES/NQ/GC extensions to 2026-09-17 (99.2-100% identical closes on the
overlap; roll days differ by one). The GOOGL zip is tbbo trades, untouched. Presets added: YM/MYM,
SI/SIL, HG, HE, NKD with Lucid commissions. Page renamed "Ten Markets, One Coin" (same URL,
version 4), two facets of five markets. Result: no market beats NQ at its best cell on return per
dollar (218%), pass rate (36.3%) or net ($57k); ES 174%, YM 172%, RTY 159%, GC 144%, CL 108%,
SI 105%, HG 67%, NKD 30%, HE -1%. ES 7 MES at $1,000/$1,500 reaches 36.6% pass at ROI 164%.

Custom strategy: day / time / news (2026-09-21): a `custom` Strategy panel entry lets the
user build a rule on the fly -- which weekdays, a fixed entry time or an offset before a
news release, direction, and (optionally) a news-day filter -- instead of picking a fixed
STRATS entry. News data is `news_calendar.json` (`build_news_calendar.py`), a per-occurrence
reconciliation of Forex Factory's High-Impact USD calendar against two Investing.com
sources (`phase0_reconcile.py`; report:
https://claude.ai/artifact/7fgamHexC3WBjv8mNWDx6i). Two real bugs surfaced and fixed during
that reconciliation, not just data-quality notes: Iran abolished DST in Sept 2022 but the
Forex Factory file's own offset suffix keeps alternating seasonally through its end (fixed
by reconstructing post-2022-09-22 rows from the Iran wall-clock at a forced +03:30); and
`D2011-13.csv` was being read with the wrong CSV delimiter (semicolon instead of comma),
silently dropping its 2011-2013 contribution. Engine seams: `dowOf(day)` (Zeller's
congruence, no `Date` object, matching the rest of `viewer_core.js`), `entry.daysOfWeek` /
`entry.newsDays` (gate before slot generation, additive, no existing STRATS entry sets
either), `entry.tableSkipReason` (a narrowly-scoped opt-in -- only `custom` sets it -- so a
`slotsFromTable` candidate suppressed because the previous trade is still open becomes a
`skipped` ledger row with that reason, instead of the silent `continue` every other
`slotsFromTable` strategy still gets). The news-anchor table reuses the existing
`slotsFromTable` mechanism (verified, not assumed, that its values are never read when
`direction` isn't `'table'`) rather than a parallel field. Build order:
`python3 build_news_calendar.py` before the usual `build_viewer3.py && lint_viewer.py &&
test_core.py`; `test_ui.py` also gates this (249 assertions, up from 228). The Phase 0
report's own status enum (CROSS_VERIFIED / SINGLE_SOURCE_FF / SINGLE_SOURCE_INVESTING /
OFFICIAL_VERIFIED / OFFICIAL_STANDARD / DISAGREE / INVESTING_INTERNAL_CONFLICT / UNMATCHED /
AMBIGUOUS / DAY_ONLY) ships unchanged into `news_calendar.json`.

OFFICIAL_STANDARD, applied (2026-09-24): the user approved the per-category table in
`build_news_calendar.py` (`OFFICIAL_STANDARD`, 24 categories: BLS / DOL / Census / BEA 08:30,
ADP 08:15, ISM / Conference Board / UMich / NAR / JOLTS 10:00, Flash Services PMI 09:45) on
2026-09-21, but `main()` never applied it, so the shipped calendar had none. Now
`apply_official_standard(events)` fills only `DAY_ONLY` rows of those categories (never a row
with a real time, never a conflicting one, never the FOMC family) and tags each with
`standardSource`. 660 rows filled (633 in 2007-2014, 27 in 2021-2025); 87 stay `DAY_ONLY`
(FOMC family, New Home Sales, Philly Fed, speeches, Flash Manufacturing PMI, one Durable
Goods). No category's typical time moved. The raw FF / Investing files were not reachable
from the cloud session that did this, so the function was run on the checked-in
`news_calendar.json` rather than via a full `main()`; a full re-run gives the same rows.
`typical_et_minute` replaced the pandas `mode()` call (same value on all 52 categories).
Forex Factory to today via newfac (2026-09-24): from 2025-04-05 (the day after the Phase 0 FF
file ends) Forex Factory comes from newfac's nightly full-history CSV
(github.com/janickfarrell/newfac, release `calendar-data`, GMT times), downloaded fresh on every
`build_news_calendar.py` run; `--extend-only` redoes just that step on the checked-in JSON (no
Phase 0 source files needed; it refuses to write if any row before 2025-04-05 would change, and
a re-run is identical apart from the download stamp). Checked first against the Phase 0 ledger:
same date and time on 92.6% of CROSS_VERIFIED rows and 100% of OFFICIAL_STANDARD ones; it
repeats the old FF file's own odd times, so it is the same source continued. Rules are Phase 0's:
USD only, event names matched to the existing categories (plus one relabel, `Fed Chairman Powell
Testifies`); a (date, category) the calendar already had -- Investing rows to 2025-08-15 -- is
reconciled, not duplicated (within 1 min -> CROSS_VERIFIED, else DISAGREE; 182 and 6, the six all
speeches or an auction). New rows are SINGLE_SOURCE_FF (620), or UNMATCHED / AMBIGUOUS for those
categories. Rows whose FF "time" is a reference period ("Oct Data", "Sep 27th": the shutdown's
catch-up figures, 18) are skipped. Every added row carries `newfac: true`, every reconciled one
`preNewfac` (its state before), so the step is exactly reversible (`strip_newfac`). Result:
9,106 -> 9,742 events, 7,632 -> 8,255 with a usable time, coverage to 2026-09-24. `test_ui.py`
pins the 2025 shutdown (no October CPI; September CPI Oct 24; September payrolls Nov 20; Oct+Nov
payrolls Dec 16; Dec 18 y/y CPI only) and the 2026-09-16 FOMC day; 259 assertions.
`phase0_reconcile.py` now imports `lh5_tape` inside `main()` so its ALIAS table imports anywhere.
The FOMC decision-day step is now plain Python (`add_fomc_decision_days`), same values; its times
are written as 840 instead of pandas' 840.0.
Gaps and schedule from newfac (2026-09-24, later): newfac now also fills the calendar back to
2007 -- ONLY (date, category) pairs the Phase 0 ledger never had (the old FF file kept
High-impact rows only, so medium-rated releases such as CPI m/m and jobless claims were missing
whole years), and never one within a day of an existing row of that category (30 evening
releases the old file dated to the next day are skipped as the same release). 1,536
SINGLE_SOURCE_FF + 128 AMBIGUOUS/UNMATCHED rows added; claims now 52 a year every year. The
published schedule to 2026-12-31 (130 rows) is in too, each marked `scheduled: true`; a scheduled
row never anchors an entry and is replaced by the real one on the next `--extend-only`. Existing
rows before 2025-04-05 still unchanged (the build asserts it). 11,536 events.

Strategy -> Custom news redesign (2026-09-24): the panel now has quick picks (Big 3, Fed days,
Jobs, Inflation, 08:30 data, Top 10), picked releases as removable chips, a search box, grouped
collapsible lists with each release's usual time and its count in the run's span; three modes
(Only release days / Skip release days -- new, the complement of the day filter / Time the
entry to the release); entry before, at or AFTER the release (signed offset, custom minutes
either way); Source quality (any / verified or official / two sources agree only); "No bar at
that time": skip (old behaviour) or enter at the next bar that day (anchors record
plannedMinute + moved; the ledger tooltip says so); Hold N minutes (`entry.holdMin`, both the
timed and the fixed-time entry); and a live preview: the rule in one sentence, release days /
entry times / can trade / no bar there over the span, a warning with a one-click fix when
nothing (or part) can trade, and the next five scheduled releases with their entry times.
Why the preview matters: on the shipped RTH tape (09:30-15:59) every 08:30 release timed
"30 min before" lands at 08:00, where there is no bar, and the old panel silently showed 0
trades. Also fixed: mergeState only copies keys the default already has, so cuNews ({}) and
cuNewsOffset (null) were dropped on every reload -- `restoreCustom` restores them (known ids,
true values only). No engine change; `viewer_core.js` untouched. `test_ui.py` 279.
Still open: `FOMC Member Powell Speaks` (newfac's single label for Powell's speeches as governor,
chair and ex-chair) and `Fed Chairman Warsh Speaks/Testifies` are not mapped to any category --
the user decides. Forex Factory's own terms on automated collection have not been checked.

Restore points: `golden_2026-09-18/` holds build_viewer3.py, viewer_core.js, tape_reader.html
and the test files as they were before the 2026-09-18 pass-line fix (after the presets and
loader work). `golden_2026-09-04/` is the older one. The Website folder is in OneDrive, so
its `tape-reader/index.html` also has version history there, and the copy on Cloudflare is
whatever was last uploaded by hand. There is no git repo in this folder.

The LH5 study (2026-09-19, `LH5_README.md`): the user's last-hour candle rule, frozen in
`lh5_config.py` before any result, tested against a coin on its own entries, a random forest
with 46 inputs, and the firm's rules. Verdict: a coin; the forest no better than the rule;
nothing survives the contract. Pages `lh5_l1.html`/`lh5_l2.html` (site: `lh5/`), Strategy
panel entries `lh5`, `lh5coin`, `long1505`, `lh5rf`, `lh5rfdir`, a "Flat by" input, and the
Ensemble runs the coin on the same bar for any fixed rule. Engine seams: `pf_lh.py`,
`pf_fast.precompute(window=, exit_min=, sides=)`, `pf_ref.window_slots`, JS `'window'` mode,
`exitMin`, directions `'long'|'short'|'table'`. Gates: `test_lh5.py` (80), `test_rf.py` (17).

The RF2 study (2026-09-19, `RF2_README.md`): a random forest deciding every 30 minutes
(long / short / stand aside, 12 a day), 68 inputs incl. a technical-indicator family, trained
from 2017-07 with monthly refits, ~9,700 out-of-sample decisions on the tape, a sealed holdout
2026-03-16..2026-09-17 (new Databento files; `rf2_holdout.py` runs once, after the nulls).
Frozen in `rf2_config.py` (hash 5bbcb07325a7). Verdict: see the README's result paragraph
and `rf2_walk.json` / `rf2_holdout.json`. Pages `rf2_l1.html`/`rf2_l2.html` (site: `rf2/`),
Strategy entries `rf2` and `coin30`. Engine seams: `hold_min` / `holdMin` (per-entry exit),
`sides[day] = {minute: side}` (a decision per slot) in all four engines. Gates: `test_rf2.py`,
`test_engine_js.py` (217), `rf2_check.py`, `rf2_shoot.py`. Data caches in `rf2_cache/`.

The Breakout Academy study (2026-09-19, `bo_*`): three TradeStation systems published by
@onlybreakouts (NASDAQ Hitter: Highest(C,34) buy stop, ADX(50) < 17.5, Time 800-1500, $1,000
stop, exit on close; One rule one bar: 50-bar high/low stops, 2 entries a day, out next bar;
Trend indi 2: O + f|O-L| stops, DMI(100)[20] filter) re-implemented on the databento 1-min
files (NQ/ES/YM, 24-hour, roll-adjusted in `bo_data.py`; YM from 2016) and swept in
`bo_run.py` (10,800 configs, ~3 min). Engine `bo_engine.py` (one numba kernel, fills 1min /
30min-ts / 30min-pess / 30min-opt; `30min-ts` is TradeStation's own intrabar path and
reproduces their published NQ report to 2%), oracle `bo_test.py`, dashboard `bo_build.py`
(ASCII-only source) -> `out_bo/bo_dashboard.html`, published as
https://claude.ai/artifact/XBqZJpxjAUzfpBbQUyH6yU and on the site as `breakout/`. Verdict:
the Hitter and Trend indi 2 made money on NQ through 2023 and are flat to negative since
2024; One rule one bar is a cost problem. Strategy panel entries `bo_ti4`, `bo_hit41`,
`bo_hit34` replay each system's fills (minute, side, level per day, `bo_pack.py` ->
`out_bo/bo_tape.json`, per market, the micros use their parent's table). Engine seams:
`entry.slotsFromTable` (the per-slot table names the entry minutes), a stored `[side, level]`
fills at the level (or the open through it) and is refused with `stop level not in this bar`
on a tape that never reached it; `STRATS[].noTarget` sends rr 1e9 / targetUSD 1e12 and the
panel shows "none". The Ensemble keeps a table schedule and only draws the side. Gates:
`test_core.py` (316), `test_engine_js.py` (217), `test_ui.py` (196), `lint_viewer.py` (75).

Publishing (2026-09-17): the public site is the folder
`OneDrive - University of Cambridge\Desktop\Website`; `tape-reader\index.html` is a
byte copy of `tape_reader.html`. After a rebuild, copy it there and re-upload the
folder to Cloudflare by hand (see `HOW-TO-PUBLISH.txt` in that folder). The study pages go
to `Website\lh5\index.html` (l1) and `evidence.html` (l2); the research page links to `../lh5/`. The RF2 pages go to `Website\rf2\` the same way.

**The loop after ANY change:**

```bash
python3 build_viewer3.py && python3 lint_viewer.py && python3 test_core.py
```

All three must be green before publishing. Publish with the Artifact tool using the
file path `.../scratchpad/tape_reader.html` (no `note` parameter — it is rejected).

### The `patch_*.py` files are SPENT
Every `patch_*.py` in the directory has **already been applied** to `build_viewer3.py`
or `viewer_core.js`. They are one-shot and mostly assert on strings that no longer
exist. **Do not re-run them.** Edit `build_viewer3.py` / `viewer_core.js` directly, or
write a new patch file.

---

## 3. Hard-won workflow rules

1. **Bash heredocs mangle backslash escapes.** `<<'PYEOF'` still corrupted `\n` and
   `\\` repeatedly, producing broken Python. Write patch scripts with the Write tool
   instead. This cost several cycles; do not relearn it.
2. **The esprima parse gate is the most important check.** A syntax error once shipped
   with every bracket count *perfectly balanced* (`if {} else {}` with the else
   misplaced balances fine and is still invalid). The whole script failed to load, so
   no handler was attached and every button was dead. `lint_viewer.py` now parses the
   script first.
3. **dukpy's heap is small.** Holding several 315,900-bar aggregations at once throws
   `InternalError: out of memory`. Build one, exercise it, `= null` it, move on. See the
   replay and volume sections of `test_core.py`.
4. **Duktape is ES5.** `viewer_core.js` must stay ES5 (no arrow functions, no template
   literals) so it runs in both the browser and the test harness. The UI layer in
   `build_viewer3.py` may use ES6 freely — it is never parsed by dukpy.
5. **Test fixtures fail more often than the code.** Roughly a third of the failures in
   this session were bad assertions, not bad implementations. Check the fixture before
   assuming a bug.

---

## 4. Bugs found and fixed — the history matters

The user caught most of these. They are listed because the same classes recur.

| Bug | Consequence |
|---|---|
| Position risked more than the account held ($1,600 stop on $1,000 drawdown) | 56% of the original grid was not executable; those configs produced all the "profit" |
| Drawdown checked only at end of day | 42% of sessions touched the floor intraday; **9.8% of all sessions were dead accounts still trading** |
| `visibleTrades` compared base indices to aggregated view window | At 1H showed **2 trades where 59 were in range** — every timeframe above 1m hid nearly all trades |
| `candle` and `hollow` styles took the same branch | Identical rendering |
| `span * pad \|\| 1` | A legitimate pad of 0 is falsy, silently became 1 |
| Replay cursor stored in view space | Changing timeframe teleported it to an unrelated moment |
| Liquidation priced the move, not the exit | $1,000 account finished at **−$4.00**, below its own floor |
| One flag for "stopped" and "blown up" | A **PASS** reported *BLOWN UP* |
| Widgets read recorded P&L while balance moved by simulated P&L | Ledger, rail, tooltip and equity dots all disagreed |
| Equity pane scaled to the whole curve, drew only the visible slice | Flat sliver; drew nothing at all with one visible trade |
| Imported daily CSVs got one session per bar | Timeframe aggregation became a no-op |
| `} else {` misplaced | **Entire script failed to parse; every button dead** |
| `paintPanels` early `return` | Rail, ledger and navigator silently froze |
| Strategy tab's `stNet()` valued every payout at `ST.payoutAt` (the $2,100 profit **threshold**), not `q.payoutValue` (the $1,000 × 90% = $900 actually paid) | NET overstated by $1,200 per payout; user caught it by hand-checking a $27,100 payout — a seed showing NET −$435 was really −$1,635 |
| Evaluation trades were trimmed to the daily cap but NOT to the pass line, so an account at +$1,061.50 ran its last trade on to +$625 and "passed" at +$1,686.50 -- profit past the line thrown away on the reset, and $1,000 left at risk on a trade that should have closed at +$188.50. Same for the funded stage at the payout line. `runStrategy`, `simulateSeries` and `simulateAccount` all did it | User caught it on a CL ledger (2026-09-18), after I had checked the wrong invariant the same morning (no eval row *starting* above the line, rather than none *ending* above it). Fixed in all three engines: `gainRoom = min(cap room, pass room)`; rows carry `bind: 'cap' \| 'pass' \| 'payout'` and the ledger says PASS LINE / PAYOUT. Panels regenerated: 1 NQ median $72,160 -> $74,410 (no cap), $32,370 -> $31,888 (cap); pre-fix data kept as `*_overshoot.json`. **The Python engines (`propfirm_core.py`, `pf_stage.py`, `pf_fast.py`) still overshoot** -- every Rolling Exam / ORB / jobP number was computed that way; not yet fixed |
| The six Python engines had the same pass-line overshoot (`propfirm_core.walk`, `pf_stage.run_ticket`, `pf_fast.run`, `pf_ref`, `pf_engine.py_run`, `pf_capital.run_prop`), and `propfirm_core` alone also set its target without the round turn, so a capped day booked the cap gross and then traded half-point targets against a full stop | Fixed 2026-09-18 by `_patch_passline_py.py` plus two edits to `propfirm_core.py` (round turn in F, EPS on the line checks); pre-fix copies in `golden_2026-09-18/`. `test_engine_js.py` 87/87 (Python = JS on every field of every trade), `test_stage.py` green. `_check_passline_core.py` shows the size of the error on the foundation config |
| Loading a new bar file left the cached Strategy run and the Ensemble batch alive; the panel opened on the old tape's numbers and `ensCurves` threw `reading 'day'` indexing sessions the new tape did not have | `dropTapeResults()` on every tape change; a batch abandons itself if the tape changes under it |
| Trades the account did not take (cap reached, day over, no equity) were drawn as full boxes on the chart | `drawTrades` skips them; the rail keeps them with the reason |
| Wealth and Sizing panels shipped on `wealth_1nq.py` / `sizing_v2.py` data ($2,100 per payout, account retired) with a "these numbers are wrong" banner over a green PROFITABLE verdict | Live on the public site until 2026-09-17. Regenerated with `regen_payout_panels.py`; 1 NQ median went $108,882 → $72,160, 1 MNQ turned negative, old data kept as `*_2100retire.json` |

---

## 5. Research findings — what is actually true

> **Re-run 2026-09-18 (late)** on the corrected `propfirm_core.py`: `propfirm_core.json`
> (single seed, all 2,688 configs, every invariant held) and `propfirm_core_seeds.json`
> (200 seeds, 21 min on 16 workers), then `build_foundation_data.py` and
> `build_foundation_exhaustive.py` -> `foundation.json`. Pre-fix files kept as
> `*_overshoot.json`. Headlines: best $14.48/day -> **$64.94/day** (8 micros, 60-pt stop,
> R:R 0.5, $625 target, no loss limit, one-shot funded; P(payout) 0.0948, P(funded)
> 0.355); profitable configs 172 -> **416 of 2,688**; median config -$5.68 -> -$3.15/day.
> The best-by-dollars and best-by-P(payout) configs now coincide, so "the objectives
> disagree" and "optimum at R:R 1.0" below no longer hold; the four answers need
> re-deriving from the new grid. **The Rolling Exam page (§5.0) still shows the old
> numbers**: the only local copy of `rolling_exam.html` is the 2026-09-02 scratchpad one
> and the published artifact may be newer, so read the artifact before rebuilding §5.0
> into it (`build_foundation_js.py` -> `build_foundation_section.py` -> `build_foundation_v2.py`).
>
> **2026-09-18: every number in this section was computed by engines that let an
> evaluation run past the pass line, and `propfirm_core.py` also booked the daily cap
> GROSS (net landed $8.50 short of it, and the day went on taking half-point-target
> trades against a full stop). All six Python engines are now fixed (see the bug table),
> the JSON they produced is not regenerated. On the foundation's best config, one seed:
> $5.96/day before -> $23.81/day after; 10 MNQ one-shot: $3.74 -> $101.55/day. Treat the
> foundation figures below as WRONG in level until `propfirm_core_seeds.py` is re-run
> (2,688 configs x 200 seeds; 16 workers). The pf_stage-based studies (jobP*, jobF-H,
> orb*) had only the overshoot, so they move by a few percent, like the Wealth panel
> ($72,160 -> $74,410); still stale until re-run (jobE ~12 h, jobP6 ~16 h, orbF/orbV
> hours each on 19 workers).

### The foundation run (`propfirm_core.py`, `propfirm_core_seeds.py`)
Zero-edge arm: random long/short at 10:00 ET, re-entry every 30 min.
824 sessions (2023-01-03 → 2026-03-13), 2,688 feasible configs × 200 seeds.

- **Best: $14.48/day** — 5 micros, 60-pt stop, R:R 1.0, $625 daily target, no daily
  loss limit, one-shot funded.
- **Only 172 of 2,688 configs are profitable.** Median is **−$5.68/day**.
- The earlier "+$101/day" was entirely the two bugs above.

**The four questions, answered:**
1. **R:R matters** — highest single effect, but `R:R × risk ≤ daily target` caps it, so
   raising R:R forces risk (size or stop) down. Global optimum lands at R:R 1.0.
2. **Daily loss limit** — helps dollars, hurts payout probability. The two objectives
   genuinely conflict. Best overall config uses **none**.
3. **$625 in one day beats spreading it** — unambiguous, both metrics, 20/20 top configs.
   Reason: the trailing drawdown punishes every extra day alive.
4. **Size matters most**, and the objectives disagree: smaller is better for dollars,
   larger for payout probability. Optimum is interior at 5 micros.

Bonus: **one-shot $2,100 in the funded stage beats spreading it** — contradicts the
transaction-cost intuition, because exposure time dominates.

### Prop-firm pass rates (`check_series_real.py`)
LucidFlex 25k: $25,000, +$1,250 target, $625/day cap, $1,000 trailing DD freezing at
+$100, $65/eval.

Re-run 2026-09-18 on the corrected `simulateSeries` (the shipped CSV's 4,670 trades at
1 MNQ, 50-pt stop, re-priced at each size; net = payouts minus tickets):

| Size | Daily loss | Accounts | Pass | Pass rate | Net |
|---|---|---|---|---|---|
| 1 MNQ | none | 41 | 7 | 17.1% | −$2,665 |
| 2 MNQ | none | 128 | 25 | 19.5% | −$6,520 |
| 3 MNQ | none | 222 | 48 | 21.6% | −$9,930 |
| 5 MNQ | none | 455 | 90 | 19.8% | −$22,375 |
| 3 MNQ | $400 | 145 | 24 | 16.6% | −$6,725 |
| 5 MNQ | $200 | 107 | 10 | 9.3% | −$6,955 |

Pass rate sits in a **17–22% band regardless of size** with no loss limit. A tighter daily
loss limit makes it *worse*. **Every configuration is net negative after fees** on this
list, which is the shipped 1-MNQ trade list re-sized, not a run generated at size.

### The non-stationarity result (Rolling Exam §5.3, §5.8)
NQ's median daily range went 26 pts (2013) → 370 pts (2026), a ~10× growth in dollar
volatility, while the firm's thresholds are **fixed in dollars**. Re-optimised per year,
the same rules earn ~$0/day before 2019 (negative in two years) and $70–189/day after
2020. **The edge is the firm failing to reprice, not the strategy.**

---

## 6. What is trustworthy vs not

- **Trustworthy code (2026-09-18):** `viewer_core.js` (300 assertions), `pf_engine.py`
  (equal to the JS trade for trade, `test_engine_js.py` 87/87), `pf_stage.py` /
  `pf_fast.py` / `pf_ref.py` (`test_stage.py`), `propfirm_core.py` (runtime invariants
  incl. the pass and payout lines), `check_series_real.py`, `underlying_sweep.py`.
- **Trustworthy results:** the Tape Reader's Wealth and Sizing panels and the Five
  Markets page, all regenerated after the fix. **Stale results:** everything else that
  a Python engine produced before 2026-09-18 -- Rolling Exam §5.0 Foundation
  (`foundation.json`, `propfirm_core_seeds.json`), jobP1-P7, jobD-H, orbF/H/J/P/V,
  dash_d1-d7, orb_o1-o5, payout_dashboard. §5.0 is wrong in level; the rest by a few
  percent.
- **Superseded, banner-marked, do not cite:** Rolling Exam **Part Five §5.1 onward**
  (the old prop-firm section). Its numbers came from the buggy engine. It was kept
  deliberately — the user said *"do not discard"* — so the size of the correction stays
  visible.
- **Superseded code:** `propfirm_v5/v6/v7.py`, `propfirm_model/full/historical/v2/v3/v4.py`.
  `propfirm_core.py` replaced all of them.
- **On hold at the user's request:** `momentum_rf_grid_study.py` (random forest) —
  they want to revise factors first. Do not run it.

---

## 7. Open work

1. **In-browser self-test button** — offered, not built. Would port the Core invariants
   into a panel so verification travels with the tool. The user asked *"how do I run
   these results myself from the website?"* and the honest answer today is "you can't".
2. **Live data** — the data contract already supports appending bars; what is missing is
   a refresh path.
3. **Rebuild on the corrected engine** — multi-account/copy-trading, ATR-scaled window,
   uncertainty and slippage sweeps all exist but were computed with `propfirm_v6.py`,
   which had the intrabar bug. They are paused, not deleted.
4. **Two live sessions** — a second session of this conversation was open. If both arm
   comment replies on Tape Reader, every comment gets two replies. The user can end one
   in `/tasks`.

---

## 8. How the user works — this matters

- **Ask, do not assume.** Stated repeatedly and emphatically: *"You need to ask me
  stuff. Do not assume."* They are the domain professional and have corrected several
  wrong assumptions that would have invalidated whole sections.
- **They want exhaustiveness** — every table, every configuration, the whole space, not
  just the winner. *"I want to see the big picture. I want to see everything."*
- **They check the numbers.** Every substantive bug in section 4 was caught by them
  reading output carefully. Report faithfully; never smooth over a bad result.
- **State what is assumed.** They were rightly frustrated by tables with no window, no
  held-fixed parameters, and no explanation of the strategy. Caption everything.
