"""The full-session NQ tape: every 1-minute bar, 18:00 -> 16:59 New York.

Used by build_viewer3.py as the page's second built-in tape (the first, the
09:30-15:59 tape in continuous2.json, is untouched). The V5 model trades need it:
about 90% of them are taken between 18:00 and 09:30.

Days are CME trading days: a day runs from 18:00 New York the evening before to
16:59, so a Sunday 18:00 bar belongs to Monday. Evening bars are stored at
minute - 1440 (18:00 is -360) so the minutes rise through each day, which is
what the engine's per-day logic (slot lookup, hold, flat-by) relies on; the
page shows them as 18:00-23:59. The engine closes every trade by the end of its
day, so nothing is ever carried from one day to the next.

Input: the databento file the V5 R scripts read,
    NQ_1min_2010-06-07_to_2026-03-13_databento.csv
columns timestamp (UTC, the bar's START minute), open, high, low, close, volume.
Looked for next to build_viewer3.py, or at $TAPE_NQ_FULL. Absent -> the page is
built without this tape and says so; nothing else changes.

Output format is the page's own (see buildBars in build_viewer3.py): prices as
Int8 steps in ticks with an exception list for the rare step that does not fit,
plus one more channel of the same kind for the minutes, because overnight NQ
has minutes with no trade (a gap) where the RTH tape has none.

The packed result is cached in full_tape_nq.json and rebuilt only when the
input file changes (reading 5 million rows takes a while).
"""
import base64, csv, io, json, os, sys, datetime
from array import array
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = 'NQ_1min_2010-06-07_to_2026-03-13_databento.csv'
CACHE = os.path.join(HERE, 'full_tape_nq.json')
FIRST_DAY, LAST_DAY = '2023-01-03', '2026-03-13'   # CME trading days, inclusive
TICK = 0.25
FORMAT = 'full-v1'
NY = ZoneInfo('America/New_York')
UTC = datetime.timezone.utc


class TapeError(Exception):
    pass


def source_path():
    p = os.environ.get('TAPE_NQ_FULL') or os.path.join(HERE, NAME)
    return p if os.path.exists(p) else None


# ---------------------------------------------------------------- packing --
def _b64(a):
    return base64.b64encode(a.tobytes()).decode('ascii')


def pack_channel(vals):
    """ints -> {d: Int8 b64, ei: Int32 b64 indices, ev: Int32 b64 values}"""
    d, ei, ev = array('b'), array('i'), array('i')
    for i, v in enumerate(vals):
        if -128 <= v <= 127:
            d.append(v)
        else:
            d.append(0); ei.append(i); ev.append(v)
    return {'d': _b64(d), 'ei': _b64(ei), 'ev': _b64(ev)}


def unpack_channel(o):
    d = array('b'); d.frombytes(base64.b64decode(o['d']))
    ei = array('i'); ei.frombytes(base64.b64decode(o['ei']))
    ev = array('i'); ev.frombytes(base64.b64decode(o['ev']))
    out = list(d)
    for i, v in zip(ei, ev):
        out[i] = v
    return out


def decode(raw):
    """the page's buildBars(), in Python: -> o, h, l, c, v, mins lists"""
    T, n = raw['tick'], raw['n']
    dO, dH, dL, dC = (unpack_channel(raw['bars'][k]) for k in 'ohlc')
    o, h, l, c = [0.0] * n, [0.0] * n, [0.0] * n, [0.0] * n
    acc = raw['bars']['base']
    for i in range(n):
        acc = raw['bars']['base'] if i == 0 else acc + dO[i] * T
        o[i], h[i], l[i], c[i] = acc, acc + dH[i] * T, acc + dL[i] * T, acc + dC[i] * T
    v = None
    if raw['bars'].get('v'):
        va = array('h'); va.frombytes(base64.b64decode(raw['bars']['v'])); v = list(va)
    mins = [0] * n
    dM = unpack_channel(raw['bars']['m']) if raw['bars'].get('m') else None
    for s in raw['sessions']:
        for i in range(s['a'], s['b'] + 1):
            if dM is None:
                mins[i] = s['m0'] + (i - s['a'])
            else:
                mins[i] = s['m0'] if i == s['a'] else mins[i - 1] + dM[i]
    return o, h, l, c, v, mins


def pack(bars, title, subtitle):
    """bars: list of (day, minute, o, h, l, c, v) in time order -> page payload"""
    n = len(bars)
    if not n:
        raise TapeError('no bars between %s and %s' % (FIRST_DAY, LAST_DAY))
    tk = []
    for b in bars:
        q = [round(x / TICK) for x in b[2:6]]
        if any(abs(x * TICK - y) > 1e-9 for x, y in zip(q, b[2:6])):
            raise TapeError('%s %s: a price is not on the %.2f tick' % (b[0], b[1], TICK))
        tk.append(q)
    base = tk[0][0]
    dO = [0] + [tk[i][0] - tk[i - 1][0] for i in range(1, n)]
    dH = [x[1] - x[0] for x in tk]
    dL = [x[2] - x[0] for x in tk]
    dC = [x[3] - x[0] for x in tk]
    sessions, dM, clamped = [], [], 0
    for i, b in enumerate(bars):
        if not sessions or sessions[-1]['day'] != b[0]:
            sessions.append({'day': b[0], 'a': i, 'b': i, 'm0': b[1]})
            dM.append(0)
        else:
            sessions[-1]['b'] = i
            dM.append(b[1] - bars[i - 1][1])
    va = array('h')
    for b in bars:
        x = int(b[6])
        if x > 32767:
            x = 32767; clamped += 1
        va.append(max(0, x))
    return {'title': title, 'subtitle': subtitle, 'n': n, 'tick': TICK, 'v2': True,
            'fullSession': True, 'cmeDay': True, 'volClamped': clamped,
            'bars': {'base': base * TICK, 'o': pack_channel(dO), 'h': pack_channel(dH),
                     'l': pack_channel(dL), 'c': pack_channel(dC), 'm': pack_channel(dM),
                     'v': _b64(va)},
            'sessions': sessions, 'days': [s['day'] for s in sessions],
            'ntrades': 0, 'tcols': {}, 'tconst': {}}


# ---------------------------------------------------------------- reading --
def cme_day_minute(ts_utc):
    """UTC bar start -> (CME trading day, minute of that day; evening < 0)"""
    t = ts_utc.astimezone(NY)
    m = t.hour * 60 + t.minute
    day = t.date()
    if m >= 1080:
        day += datetime.timedelta(days=1)
        m -= 1440
    return day.isoformat(), m


def read_databento(path):
    lo = datetime.date.fromisoformat(FIRST_DAY) - datetime.timedelta(days=3)
    hi = datetime.date.fromisoformat(LAST_DAY) + datetime.timedelta(days=1)
    out, last = [], None
    with io.open(path, encoding='utf-8', newline='') as fh:
        rd = csv.DictReader(fh)
        need = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
        if not need <= set(rd.fieldnames or []):
            raise TapeError('%s: needs columns %s' % (path, ', '.join(sorted(need))))
        for k, r in enumerate(rd, start=2):
            s = r['timestamp']
            d = datetime.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
            if d < lo or d > hi:
                continue
            # the first 19 characters, as V5's read_market takes them, read as UTC
            ts = datetime.datetime.strptime(s[:19].replace('T', ' '), '%Y-%m-%d %H:%M:%S').replace(tzinfo=UTC)
            if last is not None and ts <= last:
                raise TapeError('%s line %d: timestamps must rise (%s)' % (path, k, s))
            last = ts
            day, m = cme_day_minute(ts)
            if day < FIRST_DAY or day > LAST_DAY:
                continue
            out.append((day, m, float(r['open']), float(r['high']), float(r['low']),
                        float(r['close']), float(r['volume'] or 0)))
    return out


# ------------------------------------------------------------- self-check --
def check_against_rth(full, rth):
    """The 09:30-15:59 part of the full tape must move like the RTH tape: for
    every day and minute both have (and the minute before it), the close-to-close
    change must be identical. Levels are not compared, so a tape built from a
    back-adjusted series would still pass; the moves are what trades are priced on."""
    fo, fh, fl, fc, fv, fm = decode(full)
    ro, rh, rl, rc, rv, rm = decode(rth)

    def index(raw, mins, close):
        ix = {}
        for s in raw['sessions']:
            for i in range(s['a'], s['b'] + 1):
                ix[(s['day'], mins[i])] = close[i]
        return ix
    F, R = index(full, fm, fc), index(rth, rm, rc)
    same = diff = 0
    bad = {}
    for (day, m), c in R.items():
        if m < 571 or m > 959:
            continue
        a, b = F.get((day, m)), F.get((day, m - 1))
        pr = R.get((day, m - 1))
        if a is None or b is None or pr is None:
            continue
        if abs((a - b) - (c - pr)) < 1e-9:
            same += 1
        else:
            diff += 1; bad[day] = bad.get(day, 0) + 1
    return same, diff, sorted(bad.items(), key=lambda x: -x[1])[:10]


def viewer_payload(rth_raw=None, min_match=0.99):
    """the packed tape (from cache when the input is unchanged), or None"""
    src = source_path()
    if src is None:
        print('full-session tape: %s not found next to the build (or $TAPE_NQ_FULL); '
              'the page is built without it' % NAME)
        return None
    st = os.stat(src)
    # FORMAT changes whenever the packed shape does, so an old cache is rebuilt
    key = '%s|%s|%d|%d|%s|%s' % (FORMAT, os.path.basename(src), st.st_size, int(st.st_mtime),
                                 FIRST_DAY, LAST_DAY)
    raw = None
    if os.path.exists(CACHE):
        try:
            c = json.load(io.open(CACHE, encoding='utf-8'))
            if c.get('key') == key:
                raw = c['tape']
        except (ValueError, KeyError):
            raw = None
    if raw is None:
        print('full-session tape: reading %s ...' % src)
        # the subtitle names the file the bars came from, so the page always
        # says what it is showing
        raw = pack(read_databento(src), 'NQ 1-min full session',
                   'NQ 1-min · full session, CME days 18:00–16:59 New York · '
                   '%s to %s · from %s' % (FIRST_DAY, LAST_DAY, os.path.basename(src)))
        json.dump({'key': key, 'tape': raw}, io.open(CACHE, 'w', encoding='utf-8'),
                  separators=(',', ':'))
    if rth_raw is not None:
        same, diff, bad = check_against_rth(raw, rth_raw)
        share = same / float(same + diff) if same + diff else 0.0
        print('full-session tape: %d bars, %d days; RTH moves identical on %d of %d shared minutes (%.2f%%)'
              % (raw['n'], len(raw['sessions']), same, same + diff, 100 * share))
        if share < min_match:
            raise TapeError('the full-session tape does not move like the built-in RTH tape '
                            '(%.2f%% identical, need %.0f%%); worst days: %s' %
                            (100 * share, 100 * min_match, bad))
    return raw


if __name__ == '__main__':
    t = viewer_payload()
    if t:
        print(t['n'], 'bars', len(t['sessions']), 'days', 'volume clamped on', t['volClamped'])
