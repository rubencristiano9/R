"""
Tests for build_full_tape.py on synthetic databento files, so they run anywhere.

What must hold:
  - every bar comes back from the page's format exactly (prices, minutes, volume)
  - a bar's CME day and minute: Sunday 18:00 belongs to Monday at -360, a
    16:59 bar is the last of its own day, both across the two DST changes
  - gaps (minutes with no trade) survive: minutes are shipped, not assumed
  - volume over the Int16 limit is clamped and counted, never wrapped negative
  - the RTH self-check passes a tape that moves like the RTH tape and fails one
    that does not
"""
import csv, datetime, io, os, random, sys, tempfile
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_full_tape as B

PASS, FAIL = [], []
UTC, NY = datetime.timezone.utc, ZoneInfo('America/New_York')


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('  PASS  ' if cond else '  FAIL  ') + name + (('   ' + detail) if detail and not cond else ''))


def ny(y, mo, d, h, mi):
    return datetime.datetime(y, mo, d, h, mi, tzinfo=NY).astimezone(UTC)


# ---- CME day / minute of single bars ----
print('--- CME day and minute ---')
cases = [
    (ny(2023, 1, 8, 18, 0), ('2023-01-09', -360), 'Sunday 18:00 belongs to Monday'),
    (ny(2023, 1, 9, 16, 59), ('2023-01-09', 1019), '16:59 is the last minute of its own day'),
    (ny(2023, 1, 9, 23, 59), ('2023-01-10', -1), '23:59 is minute -1 of the next day'),
    (ny(2023, 1, 10, 0, 0), ('2023-01-10', 0), 'midnight is minute 0'),
    (ny(2024, 3, 10, 18, 0), ('2024-03-11', -360), 'Sunday 18:00 on the spring-forward day'),
    (ny(2024, 11, 3, 18, 0), ('2024-11-04', -360), 'Sunday 18:00 on the fall-back day'),
    (ny(2024, 3, 11, 9, 30), ('2024-03-11', 570), '09:30 after spring-forward'),
]
for ts, want, name in cases:
    got = B.cme_day_minute(ts)
    check(name, got == want, '%s -> %s, want %s' % (ts, got, want))


# ---- a synthetic databento file ----
def synth(days, rng, gap=0.01, rth_from=None):
    """rows for CME days `days`: 18:00 the evening before -> 16:59, random walk,
    `gap` of the overnight minutes missing; rth_from = {(day, m): (o,h,l,c)} pins
    the 09:30-15:59 bars to another tape"""
    rows, px = [], 11000.0
    for day in days:
        d = datetime.date.fromisoformat(day)
        start = datetime.datetime(d.year, d.month, d.day, tzinfo=NY) - datetime.timedelta(hours=6)
        t = start
        while True:
            local = t.astimezone(NY)
            m = local.hour * 60 + local.minute
            if local.date() == d and m > 1019:
                break
            key = B.cme_day_minute(t.astimezone(UTC))
            rth = key[0] == day and 570 <= key[1] <= 959
            if rth or rng.random() >= gap:
                if rth_from is not None and rth and key in rth_from:
                    o, h, l, c = rth_from[key]
                else:
                    o = px
                    c = o + rng.choice([-1, 1]) * rng.randint(0, 12) * 0.25
                    h = max(o, c) + rng.randint(0, 6) * 0.25
                    l = min(o, c) - rng.randint(0, 6) * 0.25
                    if rng.random() < 0.0005:
                        c = o + 60.0; h = c + 1                 # a jump too big for a byte
                px = c
                v = 45000 if rng.random() < 0.001 else rng.randint(1, 3000)
                rows.append((t.astimezone(UTC), o, h, l, c, v))
            t += datetime.timedelta(minutes=1)
    return rows


def write_csv(rows, path):
    with io.open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        for ts, o, h, l, c, v in rows:
            w.writerow([ts.strftime('%Y-%m-%d %H:%M:%S') + '+00:00', o, h, l, c, v])


rng = random.Random(7)
DAYS = ['2023-01-03', '2023-01-04', '2023-01-05', '2023-01-06', '2023-01-09',
        '2024-03-08', '2024-03-11', '2024-03-12', '2024-11-01', '2024-11-04',
        '2024-12-24', '2024-12-26']       # DST weeks, a Monday after a weekend, Christmas gap
tmp = tempfile.mkdtemp()
src = os.path.join(tmp, B.NAME)
rows = synth(DAYS, rng)
write_csv(rows, src)

print('\n--- read + pack + decode round trip ---')
bars = B.read_databento(src)
check('every synthetic bar is read', len(bars) == len(rows), '%d vs %d' % (len(bars), len(rows)))
raw = B.pack(bars, 't', 's')
o, h, l, c, v, mins = B.decode(raw)
same = all(abs(o[i] - b[2]) < 1e-9 and abs(h[i] - b[3]) < 1e-9 and abs(l[i] - b[4]) < 1e-9
           and abs(c[i] - b[5]) < 1e-9 for i, b in enumerate(bars))
check('prices come back exactly', same)
check('minutes come back exactly (gaps kept)', all(mins[i] == b[1] for i, b in enumerate(bars)))
check('volume comes back, clamped at 32767', all(v[i] == min(32767, int(b[6])) for i, b in enumerate(bars)))
check('clamped bars are counted', raw['volClamped'] == sum(1 for b in bars if b[6] > 32767))
check('one day per CME day, in order', [s['day'] for s in raw['sessions']] == DAYS)
check('minutes rise within every day',
      all(all(mins[i + 1] > mins[i] for i in range(s['a'], s['b'])) for s in raw['sessions']))
check('days run 18:00 -> 16:59',
      all(mins[s['a']] >= -360 and mins[s['b']] <= 1019 for s in raw['sessions']))
check('the file has overnight gaps to test', any(mins[i + 1] - mins[i] > 1
      for s in raw['sessions'] for i in range(s['a'], s['b'])))
check('a step too big for a byte went through the exception list',
      len(B.unpack_channel(raw['bars']['o'])) == len(bars) and any(
          abs(c[i] - o[i]) >= 60 for i in range(len(bars))))

print('\n--- RTH self-check ---')
# an RTH tape in the page's older format (no minutes channel: 09:30.. contiguous)
rth_bars = [b for b in bars if 570 <= b[1] <= 959]
rth = B.pack(rth_bars, 'rth', 'rth')
del rth['bars']['m']
same_n, diff_n, _ = B.check_against_rth(raw, rth)
check('a tape that moves like the RTH tape matches it everywhere', diff_n == 0 and same_n > 0,
      '%d same, %d different' % (same_n, diff_n))
other = B.pack([b[:5] + (b[5] + (0.25 if b[1] == 700 else 0),) + b[6:] for b in bars], 'x', 'x')
same_n, diff_n, bad = B.check_against_rth(other, rth)
check('a tape that moves differently is caught', diff_n > 0, '%d different' % diff_n)

os.environ['TAPE_NQ_FULL'] = src
B.CACHE = os.path.join(tmp, 'cache.json')
try:
    B.viewer_payload(rth_raw=B.pack([b for b in rth_bars], 'r', 'r'), min_match=0.99)
    check('viewer_payload passes the matching tape', True)
except B.TapeError as e:
    check('viewer_payload passes the matching tape', False, str(e))
# +1 on every other minute's close: the moves differ (a constant shift would not --
# the check compares moves, not levels, on purpose)
bad_rth = B.pack([b[:5] + (b[5] + (1.0 if b[1] % 2 else 0.0),) + b[6:] for b in rth_bars], 'r', 'r')
try:
    B.viewer_payload(rth_raw=bad_rth, min_match=0.99)
    check('viewer_payload stops the build on a mismatching tape', False)
except B.TapeError:
    check('viewer_payload stops the build on a mismatching tape', True)
check('the packed tape is cached for the next build', os.path.exists(B.CACHE))
os.environ.pop('TAPE_NQ_FULL')
B.CACHE = os.path.join(tmp, 'nothing.json')
check('no input file -> no tape, no error', B.viewer_payload() is None or not os.path.exists(
    os.path.join(B.HERE, B.NAME)))

print('\n' + '=' * 62)
print('  %d passed, %d failed' % (len(PASS), len(FAIL)))
for f in FAIL:
    print('    FAIL: ' + f)
print('=' * 62)
sys.exit(1 if FAIL else 0)
