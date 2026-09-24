"""The V5 frozen models' trades, packed for the Tape Reader's Strategy panel.

The models themselves (R: XGBoost / ranger on NQ+ES features, built by
NQ_ES_ROLLSAFE_WALKFORWARD_V5.R) never run in the page. R saved every trade each
rule took -- the minute and the side -- and the page replays that list through
Core.tableFromTrades + Core.runStrategy, exactly as the Breakout and forest
replays do. Stop, target, size, costs and the firm's rules are the page's own.

Where the trades come from, per rule, first match wins:
  v5_trades/<candidate_id>.csv
      written by V5_EXPORT_TRADES.R: every trade of the rule in each
      walk-forward year (2023, 2024, 2025, 2026 to 13 March), each year's from a
      model fitted only on the years before it -- all out of sample.
  nq_es_rollsafe_walkforward_v5/16_champion_selected_predictions_all_folds.csv
      V5's own save of its champion (the 7m XGB 1% rule) -- the same rows, so
      that rule works before the export has been run.
A rule with neither is packed as unavailable and its button says why.

Every list is checked against V5's own per-year results
(nq_es_rollsafe_walkforward_v5/08_walkforward_fold_results.csv): the cutoff, the
number of trades and the win rate must all match, or the build stops and says
which file, which year and what differed. So a wrong file cannot quietly become
a strategy on the page.

Timestamps: V5's `signal_et` is UTC and marks the END of the bar the model read,
despite the name: a 14:45Z row is a 09:45 New York trade entered at the 09:45
open. test_v5.py pins this against the tape.

Folders are looked for next to this file, or in $V5_DIR.
"""
import csv, io, os, datetime

HERE = os.environ.get('V5_DIR') or os.path.dirname(os.path.abspath(__file__))
WF = os.path.join(HERE, 'nq_es_rollsafe_walkforward_v5')
TRADES = os.path.join(HERE, 'v5_trades')
SEAL = '2026-03-14'      # nothing on or after this UTC day ever enters the page
FOLDS = ['2023', '2024', '2025', '2026_YTD']

# The four frozen rules. The two 7m XGB rules are the SAME fitted model with
# different cutoffs; the thresholds shown are the 2026 fold's, i.e. the frozen ones.
RULES = [
    {'key': 'x7_1', 'cid': '7__NQ_ES__xgb_d2__0.0100', 'label': '7m XGB NQ+ES · 1%',
     'hold': 7, 'model': 'XGBoost depth 2', 'inputs': 'NQ + ES, 118 inputs', 'coverage': '1%',
     'fallback': '16_champion_selected_predictions_all_folds.csv'},
    {'key': 'x7_5', 'cid': '7__NQ_ES__xgb_d2__0.0500', 'label': '7m XGB NQ+ES · 5%',
     'hold': 7, 'model': 'XGBoost depth 2', 'inputs': 'NQ + ES, 118 inputs', 'coverage': '5%'},
    {'key': 'r7_2', 'cid': '7__NQ_ONLY__ranger__0.0200', 'label': '7m Ranger NQ · 2%',
     'hold': 7, 'model': 'ranger random forest', 'inputs': 'NQ only, 64 inputs', 'coverage': '2%'},
    {'key': 'x1_10', 'cid': '1__NQ_ONLY__xgb_d2__0.1000', 'label': '1m XGB NQ · 10%',
     'hold': 1, 'model': 'XGBoost depth 2', 'inputs': 'NQ only, 64 inputs', 'coverage': '10%'},
]


class PackError(Exception):
    pass


def epoch_min(stamp, where):
    """'2023-01-03T02:45:00Z' -> UTC epoch minutes. A stamp with no zone is
    refused: read as New York time it would move every trade 4-5 hours."""
    s = stamp.strip().replace(' ', 'T')
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    try:
        t = datetime.datetime.fromisoformat(s)
    except ValueError:
        raise PackError('%s: cannot read the time %r' % (where, stamp))
    if t.tzinfo is None or t.utcoffset() != datetime.timedelta(0):
        raise PackError('%s: time %r must be UTC (end in Z or +00:00), as V5 writes it'
                        % (where, stamp))
    if t.second:
        raise PackError('%s: time %r is not on a whole minute' % (where, stamp))
    return int(t.timestamp()) // 60


def fold_results():
    """V5's own per-year results for the four rules: {cid: {fold: row}}"""
    p = os.path.join(WF, '08_walkforward_fold_results.csv')
    if not os.path.exists(p):
        return None
    want = {r['cid'] for r in RULES}
    out = {}
    with io.open(p, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['candidate_id'] in want:
                out.setdefault(r['candidate_id'], {})[r['fold']] = r
    return out


def read_trades(path, name, ref):
    """rows (t, side, p_up, fold, win), checked row by row and against V5's totals"""
    seal = epoch_min(SEAL + 'T00:00:00Z', 'SEAL')
    rows, last = [], None
    with io.open(path, encoding='utf-8') as fh:
        rd = csv.DictReader(fh)
        need = {'fold', 'signal_et', 'p_up', 'prediction', 'win'}
        miss = need - set(rd.fieldnames or [])
        if miss:
            raise PackError('%s: missing column(s) %s' % (name, ', '.join(sorted(miss))))
        for i, r in enumerate(rd, start=2):          # line 1 is the header
            where = '%s line %d' % (name, i)
            if 'selected' in r and r['selected'].strip().upper() not in ('TRUE', '1'):
                continue                              # a full score file: only the trades
            t = epoch_min(r['signal_et'], where)
            if t >= seal:
                raise PackError('%s: %s is on or after %s; the months after that are never '
                                'put in the page' % (where, r['signal_et'], SEAL))
            if last is not None and t <= last:
                raise PackError('%s: times must rise; %s is not after the row before'
                                % (where, r['signal_et']))
            last = t
            side, p = int(float(r['prediction'])), float(r['p_up'])
            if side not in (1, -1):
                raise PackError('%s: prediction must be 1 or -1, got %r' % (where, r['prediction']))
            if (p >= 0.5) != (side == 1):
                raise PackError('%s: p_up %.4f disagrees with prediction %d' % (where, p, side))
            if r['fold'] not in FOLDS or r['fold'] not in ref:
                raise PackError('%s: unknown fold %r' % (where, r['fold']))
            cut = float(ref[r['fold']]['confidence_cutoff'])
            if abs(p - 0.5) < cut - 1e-9:
                raise PackError('%s: score %.6f is inside the %s cutoff %.6f -- not a trade'
                                % (where, p, r['fold'], cut))
            rows.append((t, side, p, r['fold'], int(float(r['win']))))
    # the totals must be V5's, year by year
    for f in FOLDS:
        mine = [x for x in rows if x[3] == f]
        n, wins = len(mine), sum(x[4] for x in mine)
        want_n, want_w = int(ref[f]['selected_n']), int(ref[f]['wins'])
        if n != want_n or wins != want_w:
            raise PackError('%s: %s has %d trades / %d wins; V5 recorded %d / %d'
                            % (name, f, n, wins, want_n, want_w))
    return rows


def viewer_payload():
    ref = fold_results()
    out = []
    for R in RULES:
        rule = {k: R[k] for k in ('key', 'cid', 'label', 'hold', 'model', 'inputs', 'coverage')}
        rule.update(available=False, reason='', source=None, t0=0, dt=[], s=[], q=[], f=[], w=[],
                    folds=[], frozen=None)
        if ref is None or R['cid'] not in ref:
            rule['reason'] = ('V5 results (nq_es_rollsafe_walkforward_v5/'
                              '08_walkforward_fold_results.csv) not found next to the build')
            out.append(rule)
            continue
        fr = ref[R['cid']]
        missing = [f for f in FOLDS if f not in fr]
        if missing:
            rule['reason'] = ('V5 results have no %s row for this rule '
                              '(08_walkforward_fold_results.csv)' % ', '.join(missing))
            out.append(rule)
            continue
        c26 = float(fr['2026_YTD']['confidence_cutoff'])
        rule['frozen'] = {'buy': 0.5 + c26, 'sell': 0.5 - c26}
        rule['folds'] = [{'name': f, 'n': int(fr[f]['selected_n']), 'wins': int(fr[f]['wins']),
                          'cutoff': float(fr[f]['confidence_cutoff'])} for f in FOLDS]
        cands = [(os.path.join(TRADES, R['cid'] + '.csv'), 'v5_trades/' + R['cid'] + '.csv')]
        if R.get('fallback'):
            cands.append((os.path.join(WF, R['fallback']),
                          'nq_es_rollsafe_walkforward_v5/' + R['fallback']))
        src = next(((p, n) for p, n in cands if os.path.exists(p)), None)
        if src is None:
            rule['reason'] = ('trade list not exported yet: run V5_EXPORT_TRADES.R and put '
                              'its v5_trades folder next to the build (V5_README.md)')
            out.append(rule)
            continue
        rows = read_trades(src[0], src[1], fr)
        t0 = rows[0][0] if rows else 0
        rule.update(available=True, source=src[1], t0=t0,
                    # compact: minutes as deltas, p_up in millionths
                    dt=[r[0] - (rows[i - 1][0] if i else t0) for i, r in enumerate(rows)],
                    s=[r[1] for r in rows], q=[round(r[2] * 1e6) for r in rows],
                    f=[FOLDS.index(r[3]) for r in rows], w=[r[4] for r in rows])
        out.append(rule)
    return {'seal': SEAL, 'folds': FOLDS, 'rules': out}


if __name__ == '__main__':
    for r in viewer_payload()['rules']:
        print('%-6s %-24s %s' % (r['key'], r['label'],
              ('%d trades from %s' % (len(r['s']), r['source'])) if r['available']
              else 'UNAVAILABLE: ' + r['reason']))
