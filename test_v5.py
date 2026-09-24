"""
Headless tests for the V5 strategies: the trade lists, the clock, the replay.

Runs viewer_core.js under dukpy, like test_core.py, against:
  - the V5 trade lists packed by v5_pack.py (checked against V5's own results)
  - the built-in RTH NQ tape (continuous2.json, or read out of tape_reader.html)
  - a small synthetic full-session tape (build_full_tape.py's own format)

The checklist this pins:
  - 7m/1% trades per year are V5's: 211 / 236 / 212 / 42
  - the frozen thresholds are the 2026 fold's cutoffs
  - Core.nyClock = Python zoneinfo, every minute around every DST change
    2008-2030 plus random minutes
  - RTH tape: every 7m/1% trade inside 09:30-15:59 is taken, each held exactly
    7 bars, and the tape's move agrees with V5's right/wrong on every one that
    has the bar before it (V5 measures from the close before the entry minute)
  - full-session tape: a Sunday 18:15 trade lands on Monday; flat by 16:45
    (the engine's exit minute 16:44, whose close is 16:45:00) opens nothing in
    that last minute or later and leaves nothing open at 16:45:00; no trade
    spans two days
"""
import base64, datetime, io, json, os, random, sys
from zoneinfo import ZoneInfo
import dukpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v5_pack, build_full_tape as BFT

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('  PASS  ' if cond else '  FAIL  ') + name + (('   ' + detail) if detail and not cond else ''))


CORE = io.open(os.path.join(HERE, 'viewer_core.js'), encoding='utf-8').read()


def rth_tape():
    """the built-in RTH tape: continuous2.json where the build keeps it, else the
    copy embedded in the built tape_reader.html"""
    for p in (os.environ.get('TAPE_RTH_JSON', ''), r'C:\Users\ruben\nq-backtest\continuous2.json',
              os.path.join(HERE, 'continuous2.json')):
        if p and os.path.exists(p):
            return json.load(io.open(p, encoding='utf-8'))
    page = io.open(os.path.join(HERE, 'tape_reader.html'), encoding='utf-8').read()
    k = page.index('const RAW = ') + len('const RAW = ')
    return json.JSONDecoder().raw_decode(page[k:])[0]


def interp():
    js = dukpy.JSInterpreter()
    js.evaljs(CORE)
    return js


P = v5_pack.viewer_payload()
RULES = {r['key']: r for r in P['rules']}


def times(r):
    out, acc = [], r['t0']
    for d in r['dt']:
        acc += d
        out.append(acc)
    return out


print('--- the trade lists ---')
x71 = RULES['x7_1']
check('7m/1% is available', x71['available'], x71['reason'])
per = {f['name']: sum(1 for i in x71['f'] if P['folds'][i] == f['name']) for f in x71['folds']}
check('7m/1% trades per year = V5 (211/236/212/42)',
      [per[k] for k in P['folds']] == [211, 236, 212, 42], str(per))
check('frozen thresholds are the 2026 cutoffs (0.57509003 / 0.42490997)',
      abs(x71['frozen']['buy'] - 0.57509003) < 1e-8 and abs(x71['frozen']['sell'] - 0.42490997) < 1e-8)
check('7m/5% frozen thresholds 0.56042236 / 0.43957764',
      RULES['x7_5']['frozen'] and abs(RULES['x7_5']['frozen']['buy'] - 0.56042236) < 1e-8)
check('Ranger frozen thresholds 0.57004634 / 0.42995366',
      RULES['r7_2']['frozen'] and abs(RULES['r7_2']['frozen']['buy'] - 0.57004634) < 1e-8)
check('1m frozen thresholds 0.56282097 / 0.43717903',
      RULES['x1_10']['frozen'] and abs(RULES['x1_10']['frozen']['buy'] - 0.56282097) < 1e-8)
check('a rule without its list says how to make one',
      all(r['available'] or 'V5_EXPORT_TRADES.R' in r['reason'] for r in P['rules']))
T71 = times(x71)
check('times rise and none is on or after 2026-03-14',
      all(b > a for a, b in zip(T71, T71[1:])) and
      T71[-1] < int(datetime.datetime(2026, 3, 14, tzinfo=datetime.timezone.utc).timestamp()) // 60)

# a bad list is refused with the file and the row named
import tempfile, csv as _csv
tmp = tempfile.mkdtemp()
src = os.path.join(v5_pack.WF, '16_champion_selected_predictions_all_folds.csv')
rows = list(_csv.DictReader(io.open(src, encoding='utf-8')))
ref = v5_pack.fold_results()['7__NQ_ES__xgb_d2__0.0100']


def refused(mutate, want):
    rr = [dict(r) for r in rows]
    mutate(rr)
    p = os.path.join(tmp, 'bad.csv')
    with io.open(p, 'w', newline='', encoding='utf-8') as fh:
        w = _csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rr)
    try:
        v5_pack.read_trades(p, 'bad.csv', ref)
        return False
    except v5_pack.PackError as e:
        return want in str(e)


check('a time with no zone is refused', refused(lambda rr: rr[5].update(signal_et='2023-02-01 10:00:00'), 'must be UTC'))
check('times out of order are refused', refused(lambda rr: rr.__setitem__(slice(3, 5), [rr[4], rr[3]]), 'must rise'))
check('a missing trade is refused', refused(lambda rr: rr.pop(10), 'V5 recorded'))
check('a side that disagrees with its score is refused',
      refused(lambda rr: rr[7].update(prediction=str(-int(float(rr[7]['prediction'])))), 'disagrees'))
check('a trade after the seal is refused', refused(lambda rr: rr[-1].update(signal_et='2026-03-20T15:00:00Z'), 'on or after'))

print('\n--- New York clock (Core.nyClock vs zoneinfo) ---')
js = interp()
NY = ZoneInfo('America/New_York')
mins = []
for y in range(2008, 2031):
    for mo in (3, 11):
        d = datetime.datetime(y, mo, 1, tzinfo=datetime.timezone.utc)
        for k in range(0, 14 * 24 * 60, 7):      # the first two weeks: both Sundays
            mins.append(int(d.timestamp()) // 60 + k)
rng = random.Random(5)
mins += [rng.randint(20000000, 32000000) for _ in range(20000)]
got = js.evaljs('var M = dukpy.m, out = []; for (var i = 0; i < M.length; i++) {'
                ' var c = Core.nyClock(M[i]); out.push([c.day, c.min, c.dow]); } out', m=mins)
bad = 0
for t, g in zip(mins, got):
    lt = datetime.datetime.fromtimestamp(t * 60, NY)
    want = [lt.date().isoformat(), lt.hour * 60 + lt.minute, (lt.weekday() + 1) % 7]
    if list(g) != want:
        bad += 1
check('%d minutes, incl. every DST change 2008-2030' % len(mins), bad == 0, '%d differ' % bad)

print('\n--- replay on the built-in RTH tape ---')
RAW = rth_tape()
o, h, l, c, v, bm = BFT.decode(RAW)
N = RAW['n']
tb = js.evaljs('Core.tableFromTrades(dukpy.t, dukpy.s, false)', t=T71, s=x71['s'])
check('no two trades share a minute', tb['dup'] == 0)
idx = {}
for s_ in RAW['sessions']:
    for i in range(s_['a'], s_['b'] + 1):
        idx[(s_['day'], bm[i])] = i
on_tape = {k: v_ for k, v_ in tb['at'].items() if (k.split(' ')[0], int(k.split(' ')[1])) in idx}
check('73 of the 701 trades are inside 09:30-15:59', len(on_tape) == 73, str(len(on_tape)))
# dukpy's heap is small (HANDOFF: build one thing, use it, drop it): hand the
# engine only the days that hold a trade, re-indexed, in a fresh interpreter
js = interp()
keep = sorted({k.split(' ')[0] for k in on_tape})
sub_s, so, sh, sl, sc, sm, back = [], [], [], [], [], [], []
for s_ in RAW['sessions']:
    if s_['day'] not in keep:
        continue
    a = len(so)
    for i in range(s_['a'], s_['b'] + 1):
        so.append(o[i]); sh.append(h[i]); sl.append(l[i]); sc.append(c[i]); sm.append(bm[i]); back.append(i)
    sub_s.append({'day': s_['day'], 'a': a, 'b': len(so) - 1})
js.evaljs('var B = {n:%d, o:%s, h:%s, l:%s, c:%s, mins:%s, sessions:%s};' % (
    len(so), json.dumps(so), json.dumps(sh), json.dumps(sl), json.dumps(sc), json.dumps(sm),
    json.dumps(sub_s)))
o = h = l = None
res = js.evaljs('''var r = Core.runStrategy(B, {entry: {mode: 'reentry', direction: 'table',
    sides: dukpy.sides, slotsFromTable: true, holdMin: 7},
    trade: {stopPts: 1e5, rr: 1e9},
    acct: {balance: 1e9, contracts: 1, pointValue: 20, commission: 0, slippage: 0},
    rules: {trailDD: 1e8, dailyCap: 1e8, target: 1e12, payoutAt: 1e12}});
  r.trades.map(function (t) { return [t.skipped ? 1 : 0, t.entry_bar, t.exit_bar, t.side, t.day]; })''',
    sides=tb['sides'])
taken = [t for t in res if not t[0]]
check('all 73 are taken', len(taken) == 73, str(len(taken)))
check('each is held exactly 7 bars (the open of minute m to the close of m+6)',
      all(t[2] - t[1] == 6 for t in taken))
agree = checked = 0
for t in taken:
    i0, i1, side, day = back[t[1]], back[t[2]], t[3], t[4]
    k = day + ' ' + str(bm[i0])
    ti = tb['at'][k]
    if bm[i0 - 1] != bm[i0] - 1:            # 09:30: the close before is not on the tape
        continue
    move = side * (c[i1] - c[i0 - 1])
    checked += 1
    agree += (move > 0) == bool(x71['w'][ti])
check('the tape agrees with V5 right/wrong on every trade with a prior bar (69)',
      checked == 69 and agree == 69, '%d of %d' % (agree, checked))
js = None

print('\n--- full-session tape: CME days and the firm\'s flat-by ---')
UTC = datetime.timezone.utc


def ny(y, mo, d, hh, mi):
    return int(datetime.datetime(y, mo, d, hh, mi, tzinfo=NY).astimezone(UTC).timestamp()) // 60


bars, px, rng = [], 12000.0, random.Random(9)
for day in ('2025-01-06', '2025-01-07'):         # a Monday (opens Sunday 18:00) and a Tuesday
    d = datetime.date.fromisoformat(day)
    t = datetime.datetime(d.year, d.month, d.day, tzinfo=NY) - datetime.timedelta(hours=6)
    while True:
        lt = t.astimezone(NY)
        if lt.date() == d and lt.hour * 60 + lt.minute > 1019:
            break
        dd, m = BFT.cme_day_minute(t.astimezone(UTC))
        cl = px + rng.choice([-1, 1]) * rng.randint(0, 8) * 0.25
        bars.append((dd, m, px, max(px, cl) + 0.5, min(px, cl) - 0.5, cl, 100))
        px = cl
        t += datetime.timedelta(minutes=1)
F = BFT.pack(bars, 'f', 'f')
fo, fh, fl, fc, fv, fm = BFT.decode(F)
# Lucid's flat-by is 16:45: flat BY 16:45:00, so the engine's exit minute is the
# 16:44 bar (1004), whose close is 16:45:00 -- the panel passes flat-by - 1
trades = [(ny(2025, 1, 5, 18, 15), 1),      # Sunday evening -> Monday's day
          (ny(2025, 1, 6, 16, 40), -1),     # a 7-minute hold would run to 16:46: cut at 16:45:00
          (ny(2025, 1, 6, 16, 44), 1),      # the last minute before the flat-by: never opens
          (ny(2025, 1, 6, 16, 55), 1),      # after it: never opens
          (ny(2025, 1, 6, 23, 30), -1),     # Monday evening -> Tuesday's day
          (ny(2025, 1, 7, 10, 0), 1)]
js = interp()
tb = js.evaljs('Core.tableFromTrades(dukpy.t, dukpy.s, true)', t=[x[0] for x in trades], s=[x[1] for x in trades])
check('Sunday 18:15 is filed on Monday at minute -345', tb['sides'].get('2025-01-06', {}).get('-345') == 1)
check('Monday 23:30 is filed on Tuesday at minute -30', tb['sides'].get('2025-01-07', {}).get('-30') == -1)
js.evaljs('var F = {n:%d, o:%s, h:%s, l:%s, c:%s, mins:%s, sessions:%s};' % (
    F['n'], json.dumps(fo), json.dumps(fh), json.dumps(fl), json.dumps(fc), json.dumps(fm),
    json.dumps(F['sessions'])))


def run_full(exit_min, hold):
    return js.evaljs('''var r = Core.runStrategy(F, {entry: {mode: 'reentry', direction: 'table',
        sides: dukpy.sides, slotsFromTable: true, holdMin: dukpy.hold, exitMin: dukpy.x},
        trade: {stopPts: 1e5, rr: 1e9},
        acct: {balance: 1e9, contracts: 1, pointValue: 20, commission: 0, slippage: 0},
        rules: {trailDD: 1e8, dailyCap: 1e8, target: 1e12, payoutAt: 1e12}});
      r.trades.filter(function (t) { return !t.skipped; }).map(function (t) {
        return [t.entry_bar, t.exit_bar, t.session, t.day]; })''', sides=tb['sides'], hold=hold, x=exit_min)


def sess_of(i):
    return next(k for k, s_ in enumerate(F['sessions']) if s_['a'] <= i <= s_['b'])


got = run_full(1004, 7)
mins_in = [fm[t[0]] for t in got]
check('flat by 16:45: the 16:44 and 16:55 trades never open', 1004 not in mins_in and 1015 not in mins_in,
      str(mins_in))
check('flat by 16:45: nothing is open at 16:45:00 (every exit at or before the 16:44 close)',
      all(fm[t[1]] <= 1004 for t in got))
t1640 = [t for t in got if fm[t[0]] == 1000]
check('the 16:40 trade is closed at the 16:44 close (16:45:00), not held to 16:46',
      len(t1640) == 1 and fm[t1640[0][1]] == 1004)
check('no trade spans two days', all(sess_of(t[0]) == sess_of(t[1]) for t in got))
check('4 trades taken (Sunday evening, 16:40, Monday evening, Tuesday 10:00)', len(got) == 4, str(len(got)))
# a day with NO 16:44 bar (no trade printed in that minute): the flat-by must
# still hold -- out at the last bar before it, never run on to 16:59
gap = [b for b in bars if not (b[0] == '2025-01-06' and b[1] == 1004)]
G = BFT.pack(gap, 'g', 'g')
go_, gh, gl, gc, gv, gm = BFT.decode(G)
js.evaljs('var F = {n:%d, o:%s, h:%s, l:%s, c:%s, mins:%s, sessions:%s};' % (
    G['n'], json.dumps(go_), json.dumps(gh), json.dumps(gl), json.dumps(gc), json.dumps(gm),
    json.dumps(G['sessions'])))
got = run_full(1004, 30)
check('no 16:44 bar that day: nothing is open past 16:43, nothing opens after it',
      all(gm[t[1]] <= 1003 and gm[t[0]] < 1003 for t in got if t[3] == '2025-01-06'),
      str([(gm[t[0]], gm[t[1]]) for t in got]))
js.evaljs('var F = {n:%d, o:%s, h:%s, l:%s, c:%s, mins:%s, sessions:%s};' % (
    F['n'], json.dumps(fo), json.dumps(fh), json.dumps(fl), json.dumps(fc), json.dumps(fm),
    json.dumps(F['sessions'])))
got = run_full(None, 600)                  # no flat-by, a 10-hour hold
check('a long hold still ends at the day\'s last bar (16:59), never the next day',
      all(sess_of(t[0]) == sess_of(t[1]) and fm[t[1]] <= 1019 for t in got))

print('\n' + '=' * 62)
print('  %d passed, %d failed' % (len(PASS), len(FAIL)))
for f in FAIL:
    print('    FAIL: ' + f)
print('=' * 62)
sys.exit(1 if FAIL else 0)
