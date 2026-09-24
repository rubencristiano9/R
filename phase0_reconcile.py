"""Phase 0: reconcile Forex Factory's High-Impact USD calendar against two
Investing.com source families, before any news-calendar timing data ships in the
Tape Reader's Strategy panel. Produces a report and stops there -- no manual
verification, no news_calendar.json here. See the plan at
C:\\Users\\ruben\\.claude\\plans\\tender-gliding-bunny.md for the full methodology
this implements.

Sources:
  Forex Factory  -- lh5_tape.ff_events(), already cached.
  Investing A    -- "Economic calendar Investing.com - 2011 to 2019.zip":
                    D2011-13.csv, D2014-18.csv (semicolon, no header, fixed UTC-5,
                    confirmed empirically via Nonfarm Payrolls' known 8:30am ET
                    release time across 2011-2018: displayed 08:30 in winter,
                    07:30 in summer -- exactly what a constant EST offset produces).
                    D2019-21.csv is NOT assumed to follow the same rule (its own NFP
                    times are internally inconsistent, three different clock times
                    with no clean seasonal split) -- it is used only as a
                    cross-check against Investing B within its own overlap.
  Investing B    -- "Economic-Calendar-Scraper-Investing.com-main.zip"'s
                    complete_direct_js_scraper_*.csv (comma, header, fixed UTC-4,
                    confirmed the same way: displayed 08:30 summer / 09:30 winter).
                    Covers 2015-01 to 2025-08 and is the primary Investing.com
                    source wherever it has coverage.

Neither Investing source's offset was tuned against Forex Factory -- both were
determined from Nonfarm Payrolls' own well-known, unchanging 8:30am ET release
time, so Forex Factory remains the fully independent comparison run below.
"""
import os
import sys
import datetime as dt

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'newscal_work')
INVESTING_A_ZIP = r'C:\Users\ruben\Downloads\Economic calendar Investing.com - 2011 to 2019.zip'
INVESTING_B_ZIP = r'C:\Users\ruben\Downloads\Economic-Calendar-Scraper-Investing.com-main.zip'

# ---------------------------------------------------------------- alias table
# FF event name -> Investing.com event name(s) that represent the same release.
# One name = a confident 1:1 match (occurrence-level date matching disambiguates
# same-name-different-vintage cases like GDP Advance/Second/Final on their own,
# since they land on different dates). Two names for FOMC Statement are synonyms
# from different eras of the same Investing.com scrape, not competing candidates.
# A list of 2+ genuinely DIFFERENT candidate series (not synonyms) = AMBIGUOUS.
# None = UNMATCHED, no plausible Investing.com counterpart found by name.
ALIAS = {
    '10-y Bond Auction': ['10-Year Note Auction'],
    '30-y Bond Auction': ['30-Year Bond Auction'],
    'ADP Non-Farm Employment Change': ['ADP Nonfarm Employment Change'],
    'Advance GDP q/q': ['GDP (QoQ)'],
    'Average Hourly Earnings m/m': ['Average Hourly Earnings (MoM)'],
    'CB Consumer Confidence': ['CB Consumer Confidence'],
    'CPI m/m': ['CPI (MoM)'],
    'CPI y/y': ['CPI (YoY)'],
    'Congressional Elections': None,
    'Core CPI m/m': ['Core CPI (MoM)'],
    'Core PCE Price Index m/m': ['Core PCE Price Index (MoM)'],
    'Core PPI m/m': ['Core PPI (MoM)'],
    'Core Retail Sales m/m': ['Core Retail Sales (MoM)'],
    'Durable Goods Orders m/m': ['Durable Goods Orders (MoM)'],
    'Empire State Manufacturing Index': ['NY Empire State Manufacturing Index'],
    'Employment Cost Index q/q': ['Employment Cost Index (QoQ)'],
    'FOMC Economic Projections': ['FOMC Economic Projections'],
    'FOMC Meeting Minutes': ['FOMC Meeting Minutes'],
    'FOMC Member Bullard Speaks': ['FOMC Member Bullard Speaks'],
    'FOMC Member Waller Speaks': ['Fed Waller Speaks'],
    'FOMC Member Williams Speaks': ['FOMC Member Williams Speaks'],
    'FOMC Press Conference': ['FOMC Press Conference'],
    'FOMC Statement': ['FOMC Statement', 'Fed Statement'],
    'Fed Announcement': None,
    'Fed Chair Powell Speaks': ['Fed Chair Powell Speaks'],
    'Fed Chair Powell Testifies': ['Fed Chair Powell Testifies'],
    'Federal Funds Rate': ['Fed Interest Rate Decision'],
    'Final GDP q/q': ['GDP (QoQ)'],
    'Final Manufacturing PMI': ['S&P Global Manufacturing PMI'],
    'Flash Manufacturing PMI': ['S&P Global Manufacturing PMI'],
    'Flash Services PMI': ['S&P Global Services PMI'],
    'Housing Starts': ['Housing Starts'],
    'ISM Manufacturing PMI': ['ISM Manufacturing PMI'],
    'ISM Services PMI': ['ISM Non-Manufacturing PMI'],
    'JOLTS Job Openings': ['JOLTS Job Openings'],
    'New Home Sales': ['New Home Sales'],
    'Non-Farm Employment Change': ['Nonfarm Payrolls'],
    'PPI m/m': ['PPI (MoM)'],
    'Pending Home Sales m/m': ['Pending Home Sales (MoM)'],
    'Philly Fed Manufacturing Index': ['Philadelphia Fed Manufacturing Index'],
    'Prelim GDP q/q': ['GDP (QoQ)'],
    'Prelim UoM Consumer Sentiment': ['Michigan Consumer Sentiment'],
    'Prelim UoM Inflation Expectations': [
        'Michigan 1-Year Inflation Expectations',
        'Michigan 5-Year Inflation Expectations',
    ],  # genuinely ambiguous: both release the same day, FF's name doesn't say which
    'President Trump Speaks': ['U.S. President Trump Speaks'],
    'Presidential Election': ['U.S. Presidential Election'],
    'Retail Sales m/m': ['Retail Sales (MoM)'],
    'Revised UoM Consumer Sentiment': ['Michigan Consumer Sentiment'],
    'S&P/CS Composite-20 HPI y/y': ['S&P/CS HPI Composite - 20 n.s.a. (YoY)'],
    'Treasury Currency Report': None,
    'Unemployment Claims': ['Initial Jobless Claims'],
    'Unemployment Rate': ['Unemployment Rate'],
}

# FF categories where ALIAS lists multiple candidate Investing names because they are
# genuinely DIFFERENT series (one ff category -> several plausible investing sources),
# not synonyms of one series (several investing names -> one ff category, which is the
# normal shared-name fan-out case). Every occurrence attributed to one of these stays
# AMBIGUOUS with no resolved time, regardless of which source produced it -- this is the
# opposite direction from the fan-out the source-occurrence audit accounts for, and
# conflating the two produced a spurious "two source occurrences for one ledger row"
# invariant failure the first time this was checked explicitly.
AMBIGUOUS_FF_CATEGORIES = {'Prelim UoM Inflation Expectations'}


def strip_period_suffix(s):
    """'Nonfarm Payrolls (Mar)' / '(Q1)' -> 'Nonfarm Payrolls'; leaves other
    parenthetical qualifiers (MoM)/(YoY)/(QoQ) alone, they are part of the name."""
    import re
    return re.sub(r' \((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Q[1-4])\)$', '', s)


def load_investing_semicolon(path, sep=';'):
    # D2011-13.csv is comma-delimited; D2014-18.csv and D2019-21.csv are
    # semicolon-delimited -- confirmed by direct inspection, not assumed.
    df = pd.read_csv(path, header=None, sep=sep,
                      names=['Date', 'Time', 'Country', 'Volatility', 'Event',
                             'Flag', 'Unit', 'Actual', 'Forecast', 'Previous'],
                      engine='python', on_bad_lines='skip', dtype=str)
    df = df.dropna(subset=['Country', 'Event'])
    df['Country'] = df.Country.str.strip()
    df['Event'] = df.Event.str.strip().map(strip_period_suffix)
    df = df[df.Country == 'United States'].copy()
    df['naive'] = pd.to_datetime(df.Date.str.strip() + ' ' + df.Time.str.strip(),
                                  format='%Y/%m/%d %H:%M:%S', errors='coerce')
    df = df.dropna(subset=['naive'])
    return df[['naive', 'Event']]


def load_investing_scraper(path):
    df = pd.read_csv(path, dtype=str)
    df = df[df.Currency == 'USD'].copy()
    df['Event'] = df.Event.str.strip().map(strip_period_suffix)
    df['naive'] = pd.to_datetime(df.DateTime, format='%Y/%m/%d %H:%M:%S', errors='coerce')
    df = df.dropna(subset=['naive'])
    return df[['naive', 'Event']]


def to_et(naive_series, fixed_utc_offset_hours):
    """naive local clock time at a FIXED (non-DST) UTC-N offset -> true America/New_York,
    which correctly applies the real US DST calendar. This is the whole point: two
    fixed-offset sources at DIFFERENT offsets both resolve to the same true instant
    once each is anchored to UTC correctly and re-expressed in NY time.
    A "UTC-N" local clock reads N hours BEHIND UTC, so UTC = local + N."""
    utc = naive_series + pd.Timedelta(hours=fixed_utc_offset_hours)
    return utc.dt.tz_localize('UTC').dt.tz_convert('America/New_York')


def main():
    # imported here, not at module level, so ALIAS can be imported on a machine that
    # does not have lh5_tape's source files (build_news_calendar.py --extend-only)
    import lh5_tape as L
    print('Loading Forex Factory...')
    # lh5_tape.ff_events() truncates to 2022-01-01 onward (built for the LH5 study's
    # own window); the Tape Reader's tape goes back to 2010, so read the same file
    # directly here without that truncation, replicating only its USD/High-Impact
    # filter and its date/time extraction rules.
    ff_raw = pd.read_csv(L.FF_CSV, usecols=['DateTime', 'Currency', 'Impact', 'Event'],
                          dtype=str)
    ff = ff_raw[(ff_raw.Currency == 'USD') & (ff_raw.Impact == 'High Impact Expected')].copy()
    ff['date'] = ff.DateTime.str[:10]
    ff['Event'] = ff.Event.str.strip()
    ff = ff[ff.Event.isin(ALIAS.keys())].copy()
    # placeholder timestamps: exactly 00:00:00 or 23:59:59 Iran-local carry no
    # reliable intraday time (confirmed in the FF README)
    ff['iran_time'] = ff.DateTime.str[11:19]
    ff['has_time'] = ~ff.iran_time.isin(['00:00:00', '23:59:59'])

    # Iran abolished DST in September 2022 and has held a fixed +03:30 offset since.
    # This file's own offset suffix keeps alternating +03:30/+04:30 seasonally through
    # its end (April 2025, confirmed empirically) -- the scraper is still simulating a
    # seasonal Iran DST shift that stopped happening in reality. For rows on/after the
    # abolition, reconstruct from the Iran-local WALL CLOCK (ignore the embedded, now
    # phantom offset) using the correct fixed +03:30, rather than trusting the suffix.
    # Iran's final 2022 DST transition happened AT the Sep 21/22 midnight boundary
    # (clocks set back from what would have been Sep 22 00:00 to Sep 21 23:00), so
    # Sep 21 daytime events were still legitimately +04:30 -- confirmed by two rows
    # (2022-09-21 Federal Funds Rate / FOMC Press Conference) that only resolved once
    # the cutoff was moved to exclude that date entirely, not just its DAYTIME hours.
    IRAN_DST_END = '2022-09-22'
    ff['wall'] = pd.to_datetime(ff.DateTime.str[:19], format='%Y-%m-%dT%H:%M:%S', errors='coerce')
    ff_dt_asis = pd.to_datetime(ff.DateTime, utc=True, errors='coerce')
    ff_dt_fixed = (ff['wall'] - pd.Timedelta(hours=3, minutes=30)).dt.tz_localize('UTC')
    post_abolition = ff.date >= IRAN_DST_END
    ff_dt = ff_dt_asis.where(~post_abolition, ff_dt_fixed)
    ff['et'] = ff_dt.dt.tz_convert('America/New_York')
    ff['et_asis'] = ff_dt_asis.dt.tz_convert('America/New_York')  # kept for before/after
    ff.loc[~ff.has_time, 'et'] = pd.NaT
    ff.loc[~ff.has_time, 'et_asis'] = pd.NaT

    print('Loading Investing.com sources...')
    inv_a1 = load_investing_semicolon(os.path.join(WORK, 'd2011_13.csv'), sep=',')
    inv_a2 = load_investing_semicolon(os.path.join(WORK, 'd2014_18.csv'))
    inv_a = pd.concat([inv_a1, inv_a2], ignore_index=True)
    inv_a['et'] = to_et(inv_a['naive'], 5)  # fixed UTC-5

    inv_b = load_investing_scraper(os.path.join(WORK, 'complete_scraper.csv'))
    inv_b['et'] = to_et(inv_b['naive'], 4)  # fixed UTC-4

    inv_c = load_investing_semicolon(os.path.join(WORK, 'd2019_21.csv'))
    inv_c['et'] = to_et(inv_c['naive'], 5)  # candidate only, cross-checked below

    b_min, b_max = inv_b['et'].min(), inv_b['et'].max()
    print('Investing B (scraper, primary) ET range:', b_min, '..', b_max)
    print('Investing A (2011-18) ET range:', inv_a['et'].min(), '..', inv_a['et'].max())
    print('Investing C (2019-21, cross-check only) ET range:', inv_c['et'].min(), '..', inv_c['et'].max())

    # ---------------- Investing-vs-Investing internal conflicts ----------------
    def index_by_date_event(df):
        d = {}
        for _, r in df.iterrows():
            key = (r['et'].date().isoformat(), r['Event'])
            d.setdefault(key, []).append(r['et'])
        return d

    relevant_names = set()
    for cats in ALIAS.values():
        if cats:
            relevant_names.update(cats)

    a_idx = index_by_date_event(inv_a[inv_a['et'].notna() & inv_a.Event.isin(relevant_names)])
    b_idx = index_by_date_event(inv_b[inv_b['et'].notna() & inv_b.Event.isin(relevant_names)])
    c_idx = index_by_date_event(inv_c[inv_c['et'].notna() & inv_c.Event.isin(relevant_names)])

    internal_conflicts = []
    # A vs B, in A's own coverage window (up to inv_a max date)
    for key, times in a_idx.items():
        if key in b_idx:
            ta, tb = times[0], b_idx[key][0]
            diff = abs((ta - tb).total_seconds()) / 60
            if diff > 1:
                internal_conflicts.append({'date': key[0], 'event': key[1],
                                            'sourceA': 'InvestingA(2011-18)', 'timeA': ta,
                                            'sourceB': 'InvestingB(scraper)', 'timeB': tb,
                                            'diff_min': diff})
    # C vs B, in C's window -- C never contributes standalone occurrences
    for key, times in c_idx.items():
        if key in b_idx:
            tc, tb = times[0], b_idx[key][0]
            diff = abs((tc - tb).total_seconds()) / 60
            if diff > 1:
                internal_conflicts.append({'date': key[0], 'event': key[1],
                                            'sourceA': 'InvestingC(2019-21)', 'timeA': tc,
                                            'sourceB': 'InvestingB(scraper)', 'timeB': tb,
                                            'diff_min': diff})

    print('\nInvesting-vs-Investing conflicts (>1 min apart):', len(internal_conflicts))

    conflict_keys = set((c['date'], c['event']) for c in internal_conflicts)

    # ---------------- combined Investing.com timeline ----------------
    # A proper set union of every (date, event) key either file has -- not a date-cutoff
    # approximation. A prior version used "A contributes only before B's coverage starts"
    # as a shortcut, which silently dropped genuine A-only occurrences that fall inside
    # B's nominal era but that B itself doesn't have. A conflicting key is deliberately
    # never written here -- an unresolved A/B disagreement stays non-tradable
    # (INVESTING_INTERNAL_CONFLICT, etMinute null) per the plan, and `combined` must not
    # even structurally offer a "resolved" value for it, so no future code path can
    # accidentally read one source's value as if it had settled the question. C
    # (D2019-21) is deliberately excluded from `combined` and from this union -- per the
    # agreed design it is cross-check-only against B, never an independent primary
    # source, so a C-only occurrence with nothing in A or B does not enter the timeline.
    combined = {}
    for key in set(a_idx) | set(b_idx):
        if key in conflict_keys:
            continue
        if key in b_idx:
            combined[key] = b_idx[key][0]
        else:
            combined[key] = a_idx[key][0]

    # ---------------- occurrence ledger: resolved by SOURCE OCCURRENCE first ----------------
    # A prior version looped over FF rows first and patched in Investing-only occurrences
    # afterward with an all-or-nothing per-key skip ("if ANY candidate category already has
    # an FF row that day, skip adding rows for ALL candidates") -- structurally capable of
    # losing a candidate that has no FF row of its own on a date where a *different*
    # candidate for the same Investing name does. Rewritten so every source occurrence --
    # every (date, Investing event name) pair, from either Investing A or B -- resolves
    # once, explicitly, against each of its candidate FF categories independently. Every
    # ledger row carries `sourceOccurrenceId` (the Investing occurrence it came from, or
    # blank for an FF-only row with no Investing match at all) and `candidateCategoryIds`
    # (every FF category that source occurrence could plausibly be), so the mapping from
    # unique occurrences to attributed rows is auditable, not just asserted in prose.
    REVERSE_ALIAS = {}
    for ff_name, cats in ALIAS.items():
        if not cats:
            continue
        for inv_name in cats:
            REVERSE_ALIAS.setdefault(inv_name, []).append(ff_name)

    ff_lookup = {(r.date, r.Event): r.et for _, r in ff.iterrows()}
    ff_all_keys = set(ff_lookup.keys())

    rows = []
    resolved_ff_keys = set()  # (date, ff_event) pairs already produced by an Investing-anchored row
    all_inv_keys = set(a_idx) | set(b_idx)

    for date, inv_name in all_inv_keys:
        candidates = REVERSE_ALIAS.get(inv_name, [])
        if not candidates:
            continue  # not alias-relevant; shouldn't happen, a_idx/b_idx are pre-filtered
        key = (date, inv_name)
        is_conflict = key in conflict_keys
        inv_time = None if is_conflict else combined.get(key)
        src_id = date + '|' + inv_name
        for ff_name in candidates:
            ffkey = (date, ff_name)
            ff_et = ff_lookup.get(ffkey, pd.NaT)
            if ff_name in AMBIGUOUS_FF_CATEGORIES:
                # a genuinely different, non-synonym investing series (not this occurrence's
                # own fan-out) -- never resolved, whichever source found it
                status, inv_time_row = 'AMBIGUOUS', None
            elif is_conflict:
                status, inv_time_row = 'INVESTING_INTERNAL_CONFLICT', inv_time
            elif pd.notna(ff_et):
                diff = abs((ff_et - inv_time).total_seconds()) / 60
                status, inv_time_row = ('CROSS_VERIFIED' if diff <= 1 else 'DISAGREE'), inv_time
            else:
                status, inv_time_row = 'SINGLE_SOURCE_INVESTING', inv_time
            rows.append({'date': date, 'ff_event': ff_name, 'ff_et': ff_et, 'inv_et': inv_time_row,
                         'status': status, 'sourceOccurrenceId': src_id,
                         'candidateCategoryIds': '|'.join(candidates)})
            if ffkey in ff_all_keys:
                resolved_ff_keys.add(ffkey)

    # FF rows with NO Investing-anchored resolution at all: UNMATCHED / AMBIGUOUS category,
    # or a genuine FF-only occurrence (no Investing occurrence exists for that date+category).
    for _, r in ff.iterrows():
        if (r.date, r.Event) in resolved_ff_keys:
            continue
        cats = ALIAS[r.Event]
        if cats is None:
            status = 'UNMATCHED'
        elif r.Event in AMBIGUOUS_FF_CATEGORIES:
            status = 'AMBIGUOUS'
        elif pd.notna(r.et):
            status = 'SINGLE_SOURCE_FF'
        else:
            status = 'DAY_ONLY'
        rows.append({'date': r.date, 'ff_event': r.Event, 'ff_et': r.et, 'inv_et': None,
                     'status': status, 'sourceOccurrenceId': None, 'candidateCategoryIds': None})

    # ---------------- per-occurrence audit: does 758 -> attributed rows reconcile exactly? ----------------
    # Two things can happen to a conflicting occurrence's candidate categories: a normal
    # candidate becomes an INVESTING_INTERNAL_CONFLICT row; a candidate that is itself an
    # AMBIGUOUS_FF_CATEGORIES member becomes an AMBIGUOUS row instead (category identity is
    # unknown, so it would be wrong to even claim a specific category's time conflicts --
    # this is a real interaction between the two mechanisms, not an accounting error).
    fanout = {}          # n_normal_candidates -> count of occurrences
    fanout_ambig = {}    # n_ambiguous_candidates -> count of occurrences
    for date, inv_name in conflict_keys:
        cands = REVERSE_ALIAS.get(inv_name, [])
        n_normal = sum(1 for c in cands if c not in AMBIGUOUS_FF_CATEGORIES)
        n_ambig = sum(1 for c in cands if c in AMBIGUOUS_FF_CATEGORIES)
        fanout[n_normal] = fanout.get(n_normal, 0) + 1
        if n_ambig:
            fanout_ambig[n_ambig] = fanout_ambig.get(n_ambig, 0) + 1
    total_conflict_rows_expected = sum(n * c for n, c in fanout.items())
    total_ambig_rows_expected = sum(n * c for n, c in fanout_ambig.items())
    print('\n=== Per-occurrence fan-out audit: 758 unique conflicts -> attributed rows ===')
    for n in sorted(fanout):
        print('  %d normal candidate FF category(ies): %d occurrences -> %d INVESTING_INTERNAL_CONFLICT rows'
              % (n, fanout[n], n * fanout[n]))
    for n in sorted(fanout_ambig):
        print('  %d AMBIGUOUS-category candidate(s) among them: %d occurrences -> %d AMBIGUOUS rows instead'
              % (n, fanout_ambig[n], n * fanout_ambig[n]))
    print('  total occurrences:', sum(fanout.values()), '(must equal 758)')
    print('  total INVESTING_INTERNAL_CONFLICT rows expected:', total_conflict_rows_expected)
    print('  total AMBIGUOUS rows expected (from conflicting occurrences only):', total_ambig_rows_expected)

    rec = pd.DataFrame(rows)
    actual_conflict_rows = (rec.status == 'INVESTING_INTERNAL_CONFLICT').sum()
    print('  actual INVESTING_INTERNAL_CONFLICT rows in the ledger:', actual_conflict_rows)
    assert sum(fanout.values()) == len(conflict_keys) == 758, \
        'fan-out audit does not cover all 758 unique conflicting occurrences'
    assert total_conflict_rows_expected == actual_conflict_rows, \
        'attributed-row count does not reconcile with the per-occurrence fan-out audit'
    print('  reconciled exactly.')

    # ---------------- invariants, checked, not just asserted in prose ----------------
    src_occ_rows = rec[rec.sourceOccurrenceId.notna()]
    n_unique_src_occ = src_occ_rows.sourceOccurrenceId.nunique()
    assert n_unique_src_occ == len(all_inv_keys), \
        'every eligible Investing source occurrence must appear in the ledger exactly once ' \
        'at the source-occurrence level (%d unique in ledger vs %d in A/B)' % (n_unique_src_occ, len(all_inv_keys))
    # no source occurrence silently dropped: every (date, inv_name) with a REVERSE_ALIAS
    # entry produced at least one row
    covered = set(src_occ_rows.sourceOccurrenceId.str.split('|', n=1).apply(tuple))
    dropped = [k for k in all_inv_keys if REVERSE_ALIAS.get(k[1]) and k not in covered]
    assert not dropped, 'source occurrences silently dropped: %s' % dropped[:5]
    # unresolved conflicts remain etMinute null / non-tradable
    conflict_rows_have_time = rec[(rec.status == 'INVESTING_INTERNAL_CONFLICT') & rec.inv_et.notna()]
    assert len(conflict_rows_have_time) == 0, \
        'INVESTING_INTERNAL_CONFLICT rows must never carry a resolved inv_et'
    # every category-attribution row points back to exactly one source occurrence, EXCEPT
    # AMBIGUOUS_FF_CATEGORIES rows, where two genuinely different Investing series can both
    # plausibly be the same-named FF category (that's the whole reason they're AMBIGUOUS,
    # not a violation -- the invariant is specifically about the shared-Investing-name
    # fan-OUT direction, which is a different relationship from this fan-IN one)
    non_ambiguous = src_occ_rows[~src_occ_rows.ff_event.isin(AMBIGUOUS_FF_CATEGORIES)]
    multi_source = non_ambiguous.groupby(['date', 'ff_event']).sourceOccurrenceId.nunique()
    assert (multi_source <= 1).all(), 'a non-ambiguous ledger row must not point to more than one source occurrence'
    print('\nAll invariants checked and held.')

    print('\n=== Occurrence status counts ===')
    print(rec.status.value_counts())

    print('\n=== FF categories: UNMATCHED / AMBIGUOUS ===')
    for name, cats in ALIAS.items():
        if cats is None:
            print('UNMATCHED:', name)
    print('AMBIGUOUS: Prelim UoM Inflation Expectations ->',
          ALIAS['Prelim UoM Inflation Expectations'])

    disagree = rec[rec.status == 'DISAGREE']
    print('\n=== DISAGREE rows (FF vs Investing time differs) ===', len(disagree))
    if len(disagree):
        for _, r in disagree.head(50).iterrows():
            diff = (r.ff_et - r.inv_et).total_seconds() / 60
            print(r.date, r.ff_event, '| FF', r.ff_et.time(), '| Investing', r.inv_et.time(),
                  '| diff_min', diff)

    print('\n=== INVESTING_INTERNAL_CONFLICT sample ===', len(internal_conflicts))
    for c in internal_conflicts[:50]:
        print(c['date'], c['event'], c['sourceA'], c['timeA'].time(),
              'vs', c['sourceB'], c['timeB'].time(), 'diff_min', round(c['diff_min'], 1))

    ff_cov = (ff.date.min(), ff.date.max())
    inv_dates = sorted(set(k[0] for k in combined.keys()))
    inv_cov = (inv_dates[0], inv_dates[-1]) if inv_dates else (None, None)
    print('\nffCoverage:', ff_cov)
    print('investingCoverage (combined A+B):', inv_cov)

    rec.to_csv(os.path.join(WORK, 'phase0_occurrences.csv'), index=False)
    pd.DataFrame(internal_conflicts).to_csv(
        os.path.join(WORK, 'phase0_internal_conflicts.csv'), index=False)
    print('\nWrote', os.path.join(WORK, 'phase0_occurrences.csv'),
          'and phase0_internal_conflicts.csv')

    return {'rec': rec, 'ff_coverage': ff_cov, 'investing_coverage': inv_cov,
            'reverse_alias': REVERSE_ALIAS}


if __name__ == '__main__':
    main()
