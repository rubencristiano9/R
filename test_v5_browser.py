"""
THE REAL BROWSER, for the V5 strategies (same approach as test_browser.py).

  1. Regression: every strategy that existed before gives the SAME result on
     the new page as on the previous page (the RTH tape, default settings, and
     again under the LucidFlex 25k preset) -- the V5 work must not move any of
     them.
  2. The V5 buttons: picking one runs, the count line adds up, a V5 trade's
     tooltip names its row in R's file, rules without a trade list are named
     under the row instead of being buttons.
  3. With the full-session tape in the build: picking a V5 rule switches to it,
     evening trades show 18:00-23:59 clock times, and under the firm's 16:45
     flat-by nothing opens at or after 16:44 and nothing is open at 16:45:00;
     no trade spans two days; the last-hour rule still exits by 15:49; a rule
     built for 09:30-15:59 (ORB, last hour) moves the chart back to that tape;
     D is one candle per day on both tapes; Demo's trades get no V5 label.
  4. Settings saved before this change run the same trades after it.

Usage: python3 test_v5_browser.py NEW_PAGE [PREVIOUS_PAGE]
  NEW_PAGE       the page built with the V5 changes (with or without the
                 full-session tape; section 3 runs only when it has one)
  PREVIOUS_PAGE  a page built before them, for section 1 (skipped if absent)
Chrome: channel 'chrome', or $CHROME_PATH.
"""
import json, os, sys, pathlib
from playwright.sync_api import sync_playwright

NEW = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\ruben\nq-backtest\tape_reader.html')
OLD = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else None
PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('  PASS  ' if cond else '  FAIL  ') + name + (('   ' + detail) if detail and not cond else ''))


def launch(p):
    exe = os.environ.get('CHROME_PATH')
    return p.chromium.launch(executable_path=exe, headless=True) if exe else \
        p.chromium.launch(channel='chrome', headless=True)


def open_page(br, path):
    pg = br.new_page(viewport={'width': 1500, 'height': 950})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(path.resolve().as_uri())
    pg.wait_for_function('typeof ST !== "undefined" && typeof BASE !== "undefined"', timeout=120000)
    pg.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
    return pg, errs


def errbar(pg):
    return pg.evaluate("""() => { const b = document.getElementById('errbar');
      return (b && b.classList.contains('on')) ? (b.innerText || '').trim() : ''; }""")


SUMMARY_JS = """(args) => {
  const [key, lucid] = args;
  if (lucid) applyLucidPreset('25k');
  ST.key = key; ST.funded.same = true; STRES = null;
  const r = Core.runStrategy(BASE, stratOpts());
  const s = r.summary;
  return JSON.stringify({key, n: s.nTrades, rows: s.nRows, evals: s.evals, passes: s.passes,
    busts: s.busts, payouts: s.payouts, net: s.net, end: s.end,
    pts: r.trades.filter(t => !t.skipped).reduce((a, t) => a + t.pts, 0)});
}"""

with sync_playwright() as p:
    br = launch(p)

    # ---------------- 1. regression against the previous page ----------------
    if OLD and OLD.exists():
        print('--- 1. every existing strategy: previous page vs new page ---')
        old, _ = open_page(br, OLD)
        new, _ = open_page(br, NEW)
        keys = old.evaluate("() => Object.keys(STRATS).filter(k => k !== 'custom')")
        for lucid in (False, True):
            same, diffs = 0, []
            for k in keys:
                for pg in (old, new):
                    pg.evaluate("() => { localStorage.clear(); }")
                a = old.evaluate(SUMMARY_JS, [k, lucid])
                b = new.evaluate(SUMMARY_JS, [k, lucid])
                if a == b:
                    same += 1
                else:
                    diffs.append((k, a, b))
                old.reload(); new.reload()
                old.wait_for_function('typeof ST !== "undefined"', timeout=120000)
                new.wait_for_function('typeof ST !== "undefined"', timeout=120000)
            check('%d existing strategies give identical results%s' %
                  (len(keys), ' under the LucidFlex 25k preset' if lucid else ' at default settings'),
                  not diffs, '; '.join('%s: %s -> %s' % d for d in diffs[:3]))
        old.close(); new.close()
    else:
        print('--- 1. skipped: no previous page given ---')

    # ---------------- 2. the V5 buttons ----------------
    print('\n--- 2. the V5 strategies in the panel ---')
    pg, errs = open_page(br, NEW)
    has_full = pg.evaluate("() => !!FULL")
    rules = pg.evaluate("() => V5.rules.map(r => ({key: r.key, label: r.label, ok: r.available, n: r.s.length}))")
    avail = [r for r in rules if r['ok']]
    check('the four V5 rules are in STRATS', pg.evaluate("() => V5_KEYS.every(k => !!STRATS[k])") and len(rules) == 4)
    check('they have their own group row', pg.evaluate(
        "() => STRAT_GROUPS.some(g => g.keys.join() === V5_KEYS.join())"))
    pg.click('#bstrat')
    pg.wait_for_selector('#sheet button[data-st]')
    for r in rules:
        btn = pg.query_selector('#sheet button[data-st="v5_%s"]' % r['key'])
        if r['ok']:
            check('%s is a button' % r['label'], btn is not None)
        else:
            check('%s (no trade list yet) is named, not a button' % r['label'],
                  btn is None and 'not yet' in pg.inner_text('#sheet') and r['label'] in pg.inner_text('#sheet'))
    for r in avail:
        pg.click('#sheet button[data-st="v5_%s"]' % r['key'])
        pg.wait_for_timeout(300)
        info = json.loads(pg.evaluate("""() => { const r = STRES || runStrat();
          const t = r.trades.filter(x => !x.skipped);
          return JSON.stringify({taken: t.length, held: t.map(x => BASE.mins[x.exit_bar] - BASE.mins[x.entry_bar]),
            cme: !!BASE.cmeDay, sub: document.getElementById('sub').textContent,
            count: (document.querySelector('#sheet .v5count') || {}).innerText || '',
            viol: r.violations.length}); }"""))
        check('%s runs with no error and no engine violation' % r['label'],
              not errbar(pg) and not errs and info['viol'] == 0, errbar(pg) + ' ' + ';'.join(errs))
        check('%s: the count line starts with the %d trades in its list' % (r['label'], r['n']),
              info['count'].startswith('Trades: %d in the list' % r['n']), info['count'][:120])
        check('%s: picking it moves to the full-session tape when the build has one' % r['label'],
              info['cme'] == has_full)
        hold = pg.evaluate("(k) => STRATS['v5_' + k].holdMin", r['key'])
        check('%s: no trade held longer than %d minutes' % (r['label'], hold),
              all(h <= hold - 1 for h in info['held']), str(sorted(set(info['held']))[-3:]))
        if not has_full and r['key'] == 'x7_1':
            check('on the RTH tape the 7m/1% takes its 73 RTH trades', info['taken'] == 73, str(info['taken']))
            check('and the count line says 73 of 701 are on this tape',
                  '701 in the list \u00b7 73 on this tape' in info['count'], info['count'][:120])
        tip = pg.evaluate("""() => { const r = STRES; const t = r.trades.filter(x => !x.skipped)[0];
          return t ? v5InfoText(t) : ''; }""")
        check('%s: a trade names its model time, score and row in R\'s file' % r['label'],
              'model time' in tip and 'UTC' in tip and 'file row' in tip, tip)

    # ---------------- 3. full-session tape, the firm's flat-by ----------------
    if has_full:
        print('\n--- 3. full-session tape and the firm\'s flat-by ---')
        pg.click('#sheet button[data-lucid="25k"]')
        pg.wait_for_timeout(200)
        check('the Lucid preset sets flat by 16:45', pg.evaluate("() => ST.exitMin") == 1005)
        check('the Flat by box shows 16:45', pg.input_value('#stFlat') == '16:45')
        pg.click('#sheet button[data-st="v5_x7_1"]')
        pg.wait_for_timeout(300)
        res = json.loads(pg.evaluate("""() => { const r = STRES || runStrat();
          const t = r.trades.filter(x => !x.skipped);
          const sess = i => Core.sessionOf(BASE.sessions, i);
          return JSON.stringify({n: t.length,
            maxExit: Math.max.apply(null, t.map(x => BASE.mins[x.exit_bar])),
            maxEntry: Math.max.apply(null, t.map(x => BASE.mins[x.entry_bar])),
            evening: t.filter(x => BASE.mins[x.entry_bar] < 0).length,
            eveningClock: t.filter(x => BASE.mins[x.entry_bar] < 0).slice(0, 3).map(x => hhmm(BASE.mins[x.entry_bar])),
            spans: t.filter(x => sess(x.entry_bar) !== sess(x.exit_bar)).length,
            sub: document.getElementById('sub').textContent}); }"""))
        check('the tape is the full-session one and names its source file', 'full session' in res['sub'].lower() or
              'full session' in pg.evaluate("() => FULL.subtitle"))
        check('overnight V5 trades are taken (%d of %d start before midnight)' % (res['evening'], res['n']),
              res['evening'] > 0)
        check('evening entries show clock times 18:00-23:59', all('18:00' <= c <= '23:59' for c in res['eveningClock']),
              str(res['eveningClock']))
        check('flat by 16:45: no trade opens at or after 16:44', res['maxEntry'] < 1004, str(res['maxEntry']))
        check('flat by 16:45: nothing is open at 16:45:00', res['maxExit'] <= 1004, str(res['maxExit']))
        check('no trade spans two days', res['spans'] == 0)
        pg.click('#sheet button[data-st="lh5"]')
        pg.wait_for_timeout(300)
        ex = pg.evaluate("() => (STRES || runStrat()).trades.filter(t => !t.skipped).map(t => BASE.mins[t.exit_bar])")
        check('the last-hour rule still exits by 15:49 under the 16:45 flat-by', ex and max(ex) <= 949)
        check('a rule built for 09:30-15:59 (the last-hour rule) moves the chart back to the RTH tape',
              not pg.evaluate("() => !!BASE.cmeDay"))
        pg.click('#sheet button[data-st="v5_x7_1"]')
        pg.wait_for_timeout(300)
        pg.click('#sheet button[data-st="orb"]')
        pg.wait_for_timeout(300)
        orb = pg.evaluate("() => (STRES || runStrat()).trades.filter(t => !t.skipped).map(t => BASE.mins[t.entry_bar])")
        check('and the ORB enters at 09:56 there, never at 18:26 the evening before',
              not pg.evaluate("() => !!BASE.cmeDay") and orb and set(orb) == {596}, str(sorted(set(orb))[:5]))
        pg.evaluate("() => closeStrategy()")
        pg.click('#bfull')
        check('the Full session button loads it again', pg.evaluate("() => !!BASE.cmeDay"))
        pg.evaluate("() => { S.tf = 1440; rebuild(); }")
        check('D on the full-session tape is one candle per CME day',
              pg.evaluate("() => V.n === BASE.sessions.length"))
        pg.evaluate("() => { S.tf = 1; rebuild(); }")
        pg.click('#demo')
        check('Demo returns to the RTH tape', not pg.evaluate("() => !!BASE.cmeDay"))
        check('D on the RTH tape is still one 390-bar candle per day', pg.evaluate(
            "() => { S.tf = 1440; rebuild(); const ok = V.n === BASE.sessions.length; S.tf = 1; rebuild(); return ok; }"))
        check('Demo\'s own trades never carry a V5 label',
              pg.evaluate("() => TRADES.every(t => !v5Info(t))"))
    else:
        print('\n--- 3. skipped: this build has no full-session tape ---')
        check('the Full session button says why it is off',
              pg.evaluate("() => document.getElementById('bfull').disabled") and
              'databento' in pg.evaluate("() => document.getElementById('bfull').title"))
    check('no uncaught page errors', not errs, ';'.join(errs))

    # ---------------- 4. saves from before this change keep their meaning ----------------
    print('\n--- 4. older saved settings ---')
    def after_reload(strat, view=None):
        pg.evaluate("(a) => { localStorage.setItem('tape.strat', JSON.stringify(a[0]));"
                    " if (a[1]) localStorage.setItem('tape.v3', JSON.stringify(a[1])); }", [strat, view])
        pg.reload()
        pg.wait_for_function('typeof ST !== "undefined"', timeout=120000)
        return pg.evaluate("() => ({exitMin: ST.exitMin, tf: S.tf, flatClock: ST.flatClock})")
    lucid = pg.evaluate("() => Object.assign({}, LUCID_PRESETS['25k'])")
    lucid_save = {k: lucid[k] for k in ('balance', 'target', 'dailyCap', 'trailDD', 'freezeOffset',
                  'payoutAt', 'payoutDraw', 'payoutSplit', 'ticket', 'pointValue', 'commission')}
    got = after_reload({'exitMin': 960, 'key': 'reentry'})
    check('an old "16:00" (the strategy\'s own exit or the close) becomes none', got['exitMin'] == 1440, str(got))
    got = after_reload({'exitMin': 930, 'key': 'reentry'})
    check('an old 15:30 (out at the 15:30 close) becomes flat by 15:31: the same trades', got['exitMin'] == 931, str(got))
    got = after_reload(dict(lucid_save, exitMin=960, key='reentry'))
    check('an old Lucid 25k save takes Lucid\'s 16:45', got['exitMin'] == 1005 and
          pg.evaluate("() => lucidPresetOn('25k')"), str(got))
    if has_full:
        after_reload({'exitMin': 1005, 'flatClock': True, 'key': 'v5_x7_1'})
        pg.click('#bstrat')
        pg.wait_for_selector('#sheet button[data-st]')
        check('a V5 rule saved as selected opens the panel on the full-session tape',
              pg.evaluate("() => !!BASE.cmeDay"))
        pg.evaluate("() => closeStrategy()")
    got = after_reload({'exitMin': 1005, 'flatClock': True, 'key': 'reentry'}, {'tf': 390})
    check('a new save is read as it is', got['exitMin'] == 1005, str(got))
    check('an old D (390 bars) becomes the whole-session D', got['tf'] == 1440, str(got))
    pg.evaluate("() => localStorage.clear()")
    br.close()

print('\n' + '=' * 62)
print('  %d passed, %d failed' % (len(PASS), len(FAIL)))
for f in FAIL:
    print('    FAIL: ' + f)
print('=' * 62)
sys.exit(1 if FAIL else 0)
