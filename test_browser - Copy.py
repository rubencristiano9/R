"""
THE REAL BROWSER.

The dukpy harness stubs the DOM, and a stub is exactly as forgiving as you
write it -- ours returns [] from document.querySelectorAll for everything,
which silently hides every bug in code that walks real nodes. That is why the
page passes 117 checks and still throws on screen.

This drives actual Chrome: loads the page from disk, listens for pageerror and
console errors, clicks every control there is, and after each click reads the
on-screen error strip (#errbar) -- the thing the user is looking at.
"""
import io, sys, time, json, pathlib
from playwright.sync_api import sync_playwright

PAGE = pathlib.Path(r'C:\Users\ruben\nq-backtest\tape_reader.html')   # the built page

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('  PASS  ' if cond else '  FAIL  ') + name +
          (('   ' + detail) if detail and not cond else ''))


def errbar(pg):
    """Whatever is currently shown in the strip at the bottom of the screen."""
    return pg.evaluate("""() => {
      const b = document.getElementById('errbar');
      return (b && b.classList.contains('on')) ? (b.innerText || '').trim() : '';
    }""")


def clear(pg):
    pg.evaluate("""() => { const b = document.getElementById('errbar');
                           if (b) b.classList.remove('on'); }""")


def run(scale):
    print('\n' + '=' * 62)
    print('  Chrome, devicePixelRatio = %s' % scale)
    print('=' * 62)
    errors, console = [], []
    with sync_playwright() as p:
        br = p.chromium.launch(channel='chrome', headless=True)
        ctx = br.new_context(viewport={'width': 1500, 'height': 900},
                             device_scale_factor=scale)
        pg = ctx.new_page()
        _ = ctx
        pg.on('pageerror', lambda e: errors.append(str(e).split('\n')[0][:200]))
        pg.on('console', lambda m: console.append((m.type, m.text[:200]))
              if m.type in ('error', 'warning') else None)

        t0 = time.time()
        pg.goto(PAGE.as_uri())
        pg.wait_for_function("() => typeof BASE !== 'undefined' && BASE && BASE.n > 0",
                             timeout=60000)
        boot = (time.time() - t0) * 1000

        print('\n--- boot ---')
        check('the page boots (%.0f ms to data ready)' % boot, True)
        check('boot raises no uncaught error', not errors, ' | '.join(errors[:3]))
        bar = errbar(pg)
        check('the error strip is clear after load', not bar, bar[:200])
        n = pg.evaluate('BASE.n')
        check('all bars decoded (%s)' % format(n, ','), n == 315900, str(n))

        # the freeze: the canvas must reach a stable size and stay there
        print('\n--- the resize loop ---')
        s1 = pg.evaluate("() => [cvEl.width, cvEl.height]")
        pg.wait_for_timeout(700)
        s2 = pg.evaluate("() => [cvEl.width, cvEl.height]")
        check('the canvas size settles (%s then %s)' % (s1, s2), s1 == s2,
              'grew from %s to %s -- the resize loop is still live' % (s1, s2))
        wrapH = pg.evaluate("() => wrap.clientHeight")
        check('the chart pane fits the window (%dpx of 900)' % wrapH,
              0 < wrapH < 900, '%dpx' % wrapH)
        loop = [c for c in console if 'ResizeObserver' in c[1]]
        check('no ResizeObserver loop warning', not loop, str(loop[:2]))

        # EVERY control outside the modal, including the ones with no id --
        # the timeframe segment, the theme swatches, the calendar cells
        print('\n--- every control on the page, clicked for real ---')
        ctrls = pg.evaluate("""() => Array.from(
            document.querySelectorAll('button, input, select'))
            .filter(e => !e.closest('#sheet'))
            .map((e, i) => ({
              i: i,
              label: e.id || (e.dataset && (e.dataset.v || e.dataset.t || e.dataset.p ||
                     e.dataset.tag)) || (e.textContent || '').trim().slice(0, 18) ||
                     (e.tagName + '.' + e.className).slice(0, 24),
              tag: e.tagName, type: e.type || ''
            }))""")
        # tag each in the DOM so it can be clicked back by index
        pg.evaluate("""() => Array.from(
            document.querySelectorAll('button, input, select'))
            .forEach((e, i) => e.setAttribute('data-sweep', i))""")
        bad = []
        for c in ctrls:
            if c['type'] == 'file':
                continue          # opens an OS dialog, nothing to learn
            clear(pg)
            before = len(errors)
            try:
                pg.evaluate("""i => { const e = document.querySelector('[data-sweep=\"'+i+'\"]');
                                     if (e && e.click) e.click(); }""", c['i'])
            except Exception as e:
                bad.append((c['label'], 'click failed: ' + str(e)[:90]))
                continue
            pg.wait_for_timeout(30)
            b = errbar(pg)
            if b:
                bad.append((c['label'], 'errbar: ' + b.replace('\n', ' ')[:110]))
            elif len(errors) > before:
                bad.append((c['label'], 'threw: ' + errors[-1][:110]))
            pg.evaluate("""() => { const m = document.getElementById('modal');
                                   if (m) m.classList.remove('on'); }""")
        check('%d page controls, none produce an error' % len(ctrls), not bad,
              '%d broken' % len(bad))
        if bad:
            print('       the %d that error:' % len(bad))
            for x in bad:
                print('         %-20s %s' % x)


        # ---- what the page LOOKS like, which no exception test can see ----
        print('\n--- rendered appearance ---')

        LUM = """
          const lum = c => { const s = c.map(v => { v /= 255;
              return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); });
            return 0.2126*s[0] + 0.7152*s[1] + 0.0722*s[2]; };
          const rgb = t => { const m = /rgba?\\(([^)]+)\\)/.exec(t || ''); if (!m) return null;
            const q = m[1].split(',').map(parseFloat);
            return {c:[q[0],q[1],q[2]], a: q.length > 3 ? q[3] : 1}; };
          const behind = el => { let n = el;
            while (n && n !== document.documentElement){
              const b = rgb(getComputedStyle(n).backgroundColor);
              if (b && b.a > 0.5) return b.c; n = n.parentElement; }
            return [255,255,255]; };
          const unreadable = () => Array.from(document.querySelectorAll('*')).filter(el => {
            const txt = Array.from(el.childNodes).filter(n => n.nodeType === 3)
                             .map(n => n.textContent.trim()).join('');
            if (!txt) return false;
            const r = el.getBoundingClientRect();
            if (r.width < 2 || r.height < 2) return false;
            const cs = getComputedStyle(el);
            if (cs.visibility === 'hidden' || +cs.opacity < 0.15) return false;
            const fg = rgb(cs.color); if (!fg || fg.a < 0.15) return false;
            const bg = behind(el), l1 = lum(fg.c), l2 = lum(bg);
            return (Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05) < 2.2;
          }).map(e => (e.id ? '#'+e.id : e.tagName) + ' "' +
                      (e.textContent||'').trim().slice(0,18) + '"');
        """

        bad = pg.evaluate("() => { %s return unreadable(); }" % LUM)
        check('every label is legible as the page loads', not bad, str(bad[:5]))

        bad = pg.evaluate("""() => { %s
            document.querySelectorAll('.top button, .bar button')
                    .forEach(b => b.classList.add('on'));
            const r = unreadable();
            document.querySelectorAll('.top button, .bar button')
                    .forEach(b => b.classList.remove('on'));
            return r; }""" % LUM)
        check('every label stays legible when its button is active', not bad,
              '%d unreadable: %s' % (len(bad), bad[:4]))
        pg.reload()
        pg.wait_for_function("() => typeof BASE !== 'undefined' && BASE && BASE.n > 0",
                             timeout=60000)
        pg.wait_for_timeout(400)

        tr = pg.evaluate("""() => { const e = document.getElementById('tagrow');
            return e ? {h: Math.round(e.getBoundingClientRect().height),
                        txt: (e.innerText||'').trim().length} : null; }""")
        check('the tag row is painted, not an empty strip',
              tr and tr['h'] > 18 and tr['txt'] > 5, str(tr))

        # panel content must stay inside the panel, not land in a page corner
        stray = []
        for label, opener in [('Wealth', 'bwealth'), ('Sizing', 'bsize'),
                              ('Prop firm', 'bacct'), ('Setups', 'btags')]:
            pg.evaluate("id => document.getElementById(id).click()", opener)
            pg.wait_for_timeout(350)
            out = pg.evaluate("""() => { const s = document.getElementById('sheet');
                const r = s.getBoundingClientRect();
                return Array.from(s.querySelectorAll('*')).filter(e => {
                  const x = e.getBoundingClientRect();
                  return x.width > 1 && x.height > 1 &&
                         (x.left < r.left - 2 || x.right > r.right + 2);
                }).map(e => e.tagName + '.' + (e.className||'').toString().slice(0,18))
                  .slice(0, 5); }""")
            if out:
                stray.append('%s: %s' % (label, out))
            pg.evaluate("() => document.getElementById('modal').classList.remove('on')")
            pg.wait_for_timeout(80)
        check('no panel content escapes its panel sideways', not stray, ' | '.join(stray))

        # every control inside every panel
        print('\n--- every control inside every panel ---')
        PANELS = [('Wealth', 'bwealth'), ('Setups', 'btags'), ('Sizing', 'bsize'),
                  ('Strategy', 'bstrat'), ('Prop firm', 'bacct'),
                  ('Settings', 'bset'), ('Indicators', 'bind')]
        for label, opener in PANELS:
            clear(pg)
            ok = pg.evaluate("id => { const e = document.getElementById(id);"
                             " if (!e) return false; e.click(); return true; }", opener)
            if not ok:
                check('%s opens' % label, False, 'no #%s' % opener)
                continue
            pg.wait_for_timeout(120)
            b = errbar(pg)
            if b:
                check('%s opens cleanly' % label, False, b.replace('\n', ' ')[:140])
                continue
            inner = pg.evaluate("""() => Array.from(
                document.querySelectorAll('#sheet button, #sheet input, #sheet select'))
                .map(e => e.id).filter(Boolean)""")
            pbad = []
            for i in inner:
                clear(pg)
                before = len(errors)
                pg.evaluate("id => { const e = document.getElementById(id);"
                            " if (e && e.click) e.click(); }", i)
                pg.wait_for_timeout(30)
                bb = errbar(pg)
                if bb:
                    pbad.append((i, bb.replace('\n', ' ')[:110]))
                elif len(errors) > before:
                    pbad.append((i, 'threw: ' + errors[-1][:110]))
                # the panel may have been replaced; reopen it
                pg.evaluate("id => { const m = document.getElementById('modal');"
                            " if (m && !m.classList.contains('on'))"
                            "   document.getElementById(id).click(); }", opener)
                pg.wait_for_timeout(20)
            check('%s: %d controls, none error' % (label, len(inner)), not pbad,
                  ' || '.join('%s -> %s' % x for x in pbad[:5]))
            if pbad:
                for x in pbad:
                    print('         %-14s %s' % x)
            pg.evaluate("""() => { const m = document.getElementById('modal');
                                   if (m) m.classList.remove('on'); }""")


        # The control sweep above pressed the Strategy panel's "Run and load", so a
        # Strategy run is on the chart. Such a run carries its own books: the
        # ledger shows them and the Prop firm settings (and its re-pricing
        # report) do not apply to it. The prop-firm checks below are about the
        # simulator, so put the shipped list back first.
        pg.evaluate("() => document.getElementById('demo').click()")
        pg.wait_for_timeout(300)
        check('Demo restores the shipped trade list',
              pg.evaluate("() => TRADES === TRADES0"))

        # ---- instrument presets: the click wiring the stub cannot reach ----
        print('\n--- instrument presets ---')
        clear(pg)
        pg.evaluate("() => { ST.stageView = 'eval'; ST.funded.same = true; openStrategy(); }")
        pg.wait_for_timeout(150)
        PICK = ("k => { const b = Array.from(document.querySelectorAll('#sheet button[data-inst]'))"
                ".find(x => x.textContent === k); b.click(); }")
        pg.evaluate(PICK, 'CL')
        pg.wait_for_timeout(150)
        got = pg.evaluate("() => [ST.pointValue, ST.commission, ST.slippage]")
        check('picking CL sets $1,000 a point, Lucid $2.00 a side and its normal slippage 0.02',
              got == [1000, 2.0, 0.02], str(got))
        pg.evaluate("() => Array.from(document.querySelectorAll('#sheet button[data-slip]'))"
                    ".find(b => b.textContent.startsWith('Conservative')).click()")
        pg.wait_for_timeout(150)
        check('the conservative button sets 4 ticks on CL', pg.evaluate("() => ST.slippage") == 0.04)
        lit = pg.evaluate("() => Array.from(document.querySelectorAll('#sheet button[data-inst].on'))"
                          ".map(b => b.textContent)")
        check('the chosen preset lights up after the redraw', lit == ['CL'], str(lit))
        pg.evaluate("() => Array.from(document.querySelectorAll('#sheet button[data-con]'))"
                    ".find(b => b.textContent === '4').click()")
        pg.wait_for_timeout(150)
        check('the contracts row sets the size', pg.evaluate("() => ST.contracts") == 4)
        check('the exits paragraph quotes the slippage in force',
              pg.evaluate("() => document.getElementById('sheet').innerHTML.indexOf('(0.04 pt)') >= 0"))
        pg.evaluate(PICK, 'NQ')
        pg.wait_for_timeout(100)
        pg.evaluate("() => Array.from(document.querySelectorAll('#sheet button[data-con]'))"
                    ".find(b => b.textContent === '1').click()")
        pg.wait_for_timeout(100)
        check('no error while switching presets', not errbar(pg), errbar(pg))
        pg.evaluate("() => document.getElementById('modal').classList.remove('on')")
        # every preset click re-ran the strategy onto the chart; the checks
        # below want the shipped list back, as above
        pg.evaluate("() => document.getElementById('demo').click()")
        pg.wait_for_timeout(300)

        # ---- detecting the instrument from an actual uploaded file, not a
        # simulated File object: this is the one path the dukpy stub cannot
        # reach at all (its FileReader never really reads a file) ----
        print('\n--- detecting the loaded instrument from a real upload ---')
        clear(pg)
        csv_path = pathlib.Path(__file__).parent / 'ES_1min_test.csv'
        csv_path.write_text(
            'timestamp,open,high,low,close,volume\n'
            '2024-03-08 14:30:00+00:00,5000,5001,4999,5000.5,10\n'
            '2024-03-08 14:31:00+00:00,5000.5,5002,5000,5001,10\n'
            '2024-03-08 14:32:00+00:00,5001,5003,5000.5,5002,10\n')
        try:
            pg.set_input_files('#fbars', str(csv_path))
            pg.wait_for_timeout(300)
            check('an ES-named file loads without error', not errbar(pg), errbar(pg)[:140])
            got = pg.evaluate("() => [LOADED_SYM, ST.pointValue, ST.commission]")
            check('the ES file name is detected and the account is auto-priced for ES',
                  got == ['ES', 50, 1.75], str(got))
            pg.evaluate("() => { ST.stageView = 'eval'; ST.funded.same = true; openStrategy(); }")
            pg.wait_for_timeout(150)
            h = pg.evaluate("() => document.getElementById('sheet').innerHTML")
            check('the panel shows the detection and no mismatch for a matching price', 'MISMATCH' not in h)
            pg.evaluate(PICK, 'GC')
            pg.wait_for_timeout(150)
            h = pg.evaluate("() => document.getElementById('sheet').innerHTML")
            check('picking a different Instrument after an ES upload is flagged as a MISMATCH',
                  'priced as GC' in h and 'look like ES' in h)
            pg.evaluate("() => document.getElementById('modal').classList.remove('on')")
        finally:
            csv_path.unlink(missing_ok=True)
        pg.evaluate("() => document.getElementById('demo').click()")
        pg.wait_for_timeout(300)
        check('Demo after an ES upload restores NQ, not the stale ES pricing',
              pg.evaluate("() => [LOADED_SYM, ST.pointValue, ST.commission]") == ['NQ', 20, 1.75])

        # ---- the ensemble: many seeds at once, off the chart, in slices ----
        print('\n--- the ensemble ---')
        clear(pg)
        pg.evaluate("() => { ST.key = 'reentry'; ST.funded.same = true; ST.seed = 23;"
                    " ST.ensN = 10; ENS.res = null; ENS.busy = false; openStrategy(); }")
        pg.wait_for_timeout(150)
        on_chart = pg.evaluate("() => TRADES.length")
        t0 = time.time()
        pg.evaluate("() => document.getElementById('stEnsRun').click()")
        try:
            pg.wait_for_function("() => ENS.res && !ENS.busy", timeout=60000)
            ran = True
        except Exception:
            ran = False
        check('ten seeds run to completion (%.2fs)' % (time.time() - t0), ran)
        check('the ensemble leaves the chart alone',
              pg.evaluate("() => TRADES.length") == on_chart)
        b = errbar(pg)
        check('the error strip stays clear through the run', not b, b.replace('\n', ' ')[:140])
        if ran:
            info = pg.evaluate("""() => { const el = document.getElementById('stEns');
              const btn = document.getElementById('stEnsRun');
              return {svgs: el.querySelectorAll('svg').length,
                      seedPath: !!el.querySelector('path[data-seed="23"]'),
                      btn: btn.innerText, disabled: btn.disabled,
                      ends: ENS.res.curves.map(c => c[c.length - 1]), nets: ENS.res.nets}; }""")
            check('the block draws the curves and the histogram', info['svgs'] == 2,
                  '%d svgs' % info['svgs'])
            check('the seed on the chart is highlighted', info['seedPath'])
            check('the button offers another run once done',
                  not info['disabled'] and info['btn'].startswith('Run 10 seeds'), info['btn'])
            check("every curve ends on its run's net",
                  all(abs(a - b) < 1e-6 for a, b in zip(info['ends'], info['nets'])))
            first = pg.evaluate("() => ENS.res.seeds[0]")
            pg.evaluate("() => document.getElementById('stEnsRun').click()")
            try:
                pg.wait_for_function("() => ENS.res && !ENS.busy && ENS.res.seeds[0] !== %d" % first,
                                     timeout=60000)
                fresh = True
            except Exception:
                fresh = False
            check('pressing Run again draws a fresh batch of seeds', fresh,
                  'still seed %d' % first)
        pg.evaluate("() => document.getElementById('modal').classList.remove('on', 'peek')")
        # opening the Strategy panel put its run on the chart; the checks
        # below score the shipped list, so put it back
        pg.evaluate("() => document.getElementById('demo').click()")
        pg.wait_for_timeout(300)

        # ---- the last-hour candle: the rule, its coin batch, Flat by, the forest replay ----
        print('\n--- the last-hour candle ---')
        clear(pg)
        pg.evaluate("() => { ST.key = 'lh5'; ST.exitMin = 960; ST.ensN = 10; STRES = null; ENS.res = null; openStrategy(); }")
        pg.wait_for_timeout(200)
        b = errbar(pg)
        check('the Last-hour candle opens cleanly', not b, b.replace('\n', ' ')[:140])
        info = pg.evaluate("""() => { const r = STRES || runStrat();
          const taken = r.trades.filter(t => !t.skipped);
          return {n: taken.length, late: taken.filter(t => BASE.mins[t.exit_bar] > 949).length,
                  entry: taken.filter(t => BASE.mins[t.entry_bar] !== 905).length,
                  flat: r.trades.filter(t => t.skipped && t.reason === 'flat signal candle').length,
                  ensText: document.getElementById('stEns').innerText,
                  hasEnsRunBtn: !!document.getElementById('stEnsRun')}; }""")
        check('the rule trades once a day at 15:05 (%d trades, %d flat candles)' % (info['n'], info['flat']),
              0 < info['n'] <= 824 and info['entry'] == 0)
        check('no trade runs past 15:49', info['late'] == 0, '%d late exits' % info['late'])
        check('a deterministic rule gets no ensemble button, only the no-coin note',
              not info['hasEnsRunBtn'] and 'takes no random decision' in info['ensText'])
        check('the error strip stays clear', not errbar(pg), errbar(pg)[:140])
        pg.fill('#stFlat', '15:30')
        pg.evaluate("() => { const f = document.getElementById('stFlat'); f.dispatchEvent(new Event('change')); }")
        pg.wait_for_timeout(400)
        late = pg.evaluate("() => (STRES || runStrat()).trades.filter(t => !t.skipped && BASE.mins[t.exit_bar] > 930).length")
        check('Flat by 15:30 closes every trade by 15:30', late == 0, '%d later exits' % late)
        pg.fill('#stFlat', '16:00')
        pg.evaluate("() => { const f = document.getElementById('stFlat'); f.dispatchEvent(new Event('change')); }")
        pg.wait_for_timeout(300)
        pg.evaluate("() => { ST.key = 'lh5rf'; STRES = null; openStrategy(); }")
        pg.wait_for_timeout(200)
        rf = pg.evaluate("""() => { const r = STRES || runStrat();
          return {abst: r.trades.filter(t => t.skipped && t.reason === 'model abstained').length,
                  viol: r.violations.length, taken: r.trades.filter(t => !t.skipped).length}; }""")
        check('the forest replay stands aside on %d days, trades %d, no violations' % (rf['abst'], rf['taken']),
              rf['abst'] > 200 and rf['taken'] > 100 and rf['viol'] == 0)
        check('the error strip stays clear after the replay', not errbar(pg), errbar(pg)[:140])
        pg.evaluate("() => { ST.key = 'reentry'; ST.exitMin = 960; STRES = null; ENS.res = null;"
                    " document.getElementById('modal').classList.remove('on', 'peek'); }")
        # the replay is a Strategy run with its own books; put the shipped list back for
        # the prop-firm checks below, exactly as the control sweep does
        pg.evaluate("() => document.getElementById('demo').click()")
        pg.wait_for_timeout(300)
        check('Demo restores the shipped trade list after the LH5 block',
              pg.evaluate("() => TRADES === TRADES0"))

        # ---- the 30-minute forest: the replay, the 30-minute coin, the ensemble ----
        print('\n--- the 30-minute forest ---')
        clear(pg)
        pg.evaluate("() => { ST.key = 'rf2'; ST.exitMin = 960; ST.ensN = 10; STRES = null; ENS.res = null; openStrategy(); }")
        pg.wait_for_timeout(200)
        b = errbar(pg)
        check('the forest entry opens cleanly', not b, b.replace('\n', ' ')[:140])
        rf = pg.evaluate("""() => { const r = STRES || runStrat();
          const taken = r.trades.filter(t => !t.skipped);
          return {abst: r.trades.filter(t => t.skipped && t.reason === 'model abstained').length,
                  taken: taken.length, viol: r.violations.length,
                  late: taken.filter(t => BASE.mins[t.exit_bar] - BASE.mins[t.entry_bar] > 29).length,
                  wrong: taken.filter(t => RF2.sides[t.day][String(BASE.mins[t.entry_bar])] !== t.side).length,
                  ensText: document.getElementById('stEns').innerText,
                  hasEnsRunBtn: !!document.getElementById('stEnsRun')}; }""")
        check('the forest replay stands aside on %d slots, trades %d, no violations' % (rf['abst'], rf['taken']),
              rf['abst'] > 3000 and rf['taken'] > 1000 and rf['viol'] == 0)
        check('every trade is out within its 30 minutes and takes the stored side', rf['late'] == 0 and rf['wrong'] == 0)
        check('a stored-table replay gets no ensemble button, only the no-coin note',
              not rf['hasEnsRunBtn'] and 'takes no random decision' in rf['ensText'])
        pg.evaluate("() => { ST.key = 'coin30'; STRES = null; ENS.res = null; openStrategy(); }")
        pg.wait_for_timeout(200)
        sp = pg.evaluate("() => { const r = STRES || runStrat(); const t = r.trades.filter(t => !t.skipped);"
                         " return {n: t.length, late: t.filter(x => BASE.mins[x.exit_bar] - BASE.mins[x.entry_bar] > 29).length}; }")
        check('the 30-minute coin takes %d trades, none past 29 minutes' % sp['n'], sp['n'] > 1000 and sp['late'] == 0)
        check('the error strip stays clear after the forest block', not errbar(pg), errbar(pg)[:140])
        pg.evaluate("() => { ST.key = 'reentry'; ST.exitMin = 960; STRES = null; ENS.res = null;"
                    " document.getElementById('modal').classList.remove('on', 'peek'); }")
        pg.evaluate("() => document.getElementById('demo').click()")
        pg.wait_for_timeout(300)
        check('Demo restores the shipped trade list after the forest block',
              pg.evaluate("() => TRADES === TRADES0"))

        # ---- the live Breakout entries: real clicks on the entry-rule and
        # side/direction buttons, since the dukpy stub cannot keep a dynamic
        # button's handler alive across a redraw the way a real DOM does ----
        print('\n--- the live Breakout entries ---')
        clear(pg)
        pg.evaluate("() => { ST.key = 'bo_live_hit'; STRES = null; openStrategy(); }")
        pg.wait_for_timeout(200)
        b = errbar(pg)
        check('the live Hitter opens cleanly', not b, b.replace('\n', ' ')[:140])
        r0 = pg.evaluate("() => { const r = STRES || runStrat();"
                         " const t = r.trades.filter(x => !x.skipped);"
                         " return {n: t.length, viol: r.violations.length}; }")
        check('the live Hitter (default settings) fills real trades, no violations (%d trades)' % r0['n'],
              r0['n'] > 0 and r0['viol'] == 0)
        pg.evaluate("() => { document.querySelector('button[data-bo-side=\"short\"]').click(); }")
        pg.wait_for_timeout(150)
        check('clicking Short is clean', not errbar(pg), errbar(pg)[:140])
        r1 = pg.evaluate("() => { const r = STRES || runStrat();"
                         " return r.trades.filter(x => !x.skipped && x.side === 1).length; }")
        check('the Side button actually flips the side (no long trades left)', r1 == 0)
        pg.evaluate("() => { document.querySelector('button[data-bo-adxdir=\"above\"]').click();"
                    " const n = document.getElementById('stBoN'); n.value = 10;"
                    " n.dispatchEvent(new Event('input')); }")
        pg.wait_for_timeout(350)   # stLive() debounces a keystroke 200ms before it re-runs
        check('changing the ADX direction and N is clean', not errbar(pg), errbar(pg)[:140])
        check('the account run reflects the edits', pg.evaluate("() => STRES !== null"))
        # reset the side the Short click above left behind: Trend indi 2's
        # published config runs both sides, this one side at a time, and the
        # short side happens to have only 6 gate-passing bars on this tape
        # with none ever reaching the level -- a real, rare market outcome,
        # not something this check should depend on
        pg.evaluate("() => { ST.boSide = 'long';"
                    " document.querySelector('button[data-st=\"bo_live_ti\"]').click(); }")
        pg.wait_for_timeout(200)
        check('switching to the live Trend indi 2 from the panel is clean', not errbar(pg), errbar(pg)[:140])
        r2 = pg.evaluate("() => { const r = STRES || runStrat();"
                         " const t = r.trades.filter(x => !x.skipped);"
                         " return {n: t.length, viol: r.violations.length,"
                         " frac: document.getElementById('stBoFrac') ? 1 : 0}; }")
        check('the live Trend indi 2 fills real trades, no violations, and shows its own fields (%d trades)' % r2['n'],
              r2['n'] > 0 and r2['viol'] == 0 and r2['frac'] == 1)
        pg.evaluate("() => { ST.key = 'reentry'; STRES = null; ENS.res = null;"
                    " document.getElementById('modal').classList.remove('on', 'peek'); }")
        pg.evaluate("() => document.getElementById('demo').click()")
        pg.wait_for_timeout(300)
        check('Demo restores the shipped trade list after the live Breakout block',
              pg.evaluate("() => TRADES === TRADES0"))

        # ---- the account series must consume the data, not stall ----
        print('\n--- the prop firm series ---')
        SIZES = [('1 MNQ', 2, 0.75), ('5 MNQ', 10, 3.75), ('1 NQ', 20, 1.5)]
        for name, pv, comm in SIZES:
            r = pg.evaluate("""(a) => {
              Object.assign(S.acct, {on:true, balance:25000, floor:24000,
                sizeMode:'fixed', contracts:1, pointValue:a.pv,
                commission:a.comm, slippage:0.25});
              Object.assign(S.acct.evaluation, {on:true, repeat:true, target:1250,
                dailyCap:625, dailyLoss:0, trailDD:1000, cost:65, freezeOffset:100});
              S.filter.on = false; rebuild(); runAccount();
              let taken = 0, byRule = 0, byAccount = 0; const per = {};
              SIM.rows.forEach(x => { if (!x) return;
                if (!x.skipped) { taken++; return; }
                per[x.acct] = (per[x.acct]||0)+1;
                /* a day limit is the rule working; anything else means the
                   account itself could not take the trade */
                if (/daily|done for the day/.test(x.reason || '')) byRule++;
                else byAccount++; });
              const worst = Math.max(0, ...Object.values(per));
              return {taken: taken, total: TRADES.length, byRule: byRule,
                      byAccount: byAccount,
                      accounts: SERIES ? SERIES.accounts.length : 0,
                      worstStall: worst,
                      open: SERIES ? SERIES.accounts.filter(
                              x => x.verdict === 'INCOMPLETE').length : 0};
            }""", {'pv': pv, 'comm': comm})
            check('%s: no trade is lost to a dead account (%d taken, %d held '
                  'back by the daily cap)' % (name, r['taken'], r['byRule']),
                  r['byAccount'] == 0,
                  '%d trades dropped because the account could not take them'
                  % r['byAccount'])
            # a long run of skips is fine when the RULES caused them -- a funded
            # account that has just been promoted is done for the day. Only skips
            # caused by the account itself may accumulate.
            check('%s: no account stalls on the rest of the file (%d skips from the '
                  'account itself)' % (name, r['byAccount']), r['byAccount'] == 0,
                  'one account skipped %d trades in a row' % r['worstStall'])
            check('%s: buys a plausible number of accounts (%d)'
                  % (name, r['accounts']), r['accounts'] >= 5,
                  'only %d accounts over the whole period' % r['accounts'])
            check('%s: at most one account is still open at the end' % name,
                  r['open'] <= 1, '%d left open' % r['open'])
        pg.evaluate("() => { S.acct.on = false; S.acct.evaluation.on = false;"
                    " runAccount(); }")


        # ---- the full-analysis report ----
        print('\n--- the full analysis report ---')
        clear(pg)
        pg.evaluate("() => document.getElementById('bacct').click()")
        pg.wait_for_timeout(200)
        check('the analysis button is there on a COLD panel, before any setup',
              pg.evaluate("() => !!document.getElementById('acReport')"),
              'the button only appears once the simulator is configured')
        pg.evaluate("() => document.getElementById('apLucid').click()")
        pg.wait_for_timeout(600)
        check('the panel offers a full-analysis button',
              pg.evaluate("() => !!document.getElementById('acReport')"))
        try:
            with ctx.expect_page(timeout=20000) as pinfo:
                pg.evaluate("() => document.getElementById('acReport').click()")
            rp = pinfo.value
            rp.wait_for_timeout(2000)
            secs = rp.evaluate("() => document.querySelectorAll('h2').length")
            figs = rp.evaluate("() => document.querySelectorAll('svg').length")
            tabs_ = rp.evaluate("() => document.querySelectorAll('table.t').length")
            verd = rp.evaluate("() => { const v = document.querySelector('.verdict');"
                               " return v ? v.innerText.trim() : ''; }")
            check('the report opens with all six sections (%d)' % secs, secs >= 6)
            check('it draws its charts (%d)' % figs, figs >= 5)
            check('it tabulates the sweep (%d tables)' % tabs_, tabs_ >= 4)
            check('it names the best configuration', 'Best of' in verd and 'net' in verd,
                  verd[:110])
            check('it swept every size and both cap settings',
                  '60 configurations' in verd, verd[:110])
            lad = rp.evaluate("""() => { const ts = [...document.querySelectorAll('table.t')];
                const t = ts.find(x => x.innerText.includes('$/point'));
                return t ? t.querySelectorAll('tbody tr').length : 0; }""")
            check('the size ladder is exhaustive (%d sizes)' % lad, lad >= 30,
                  'only %d sizes listed' % lad)
            rows = rp.evaluate("() => document.querySelectorAll('table.t tbody tr').length")
            check('the sweep table has a row per size (%d rows total)' % rows, rows >= 15)
            over = rp.evaluate("() => document.body.scrollWidth > window.innerWidth + 2")
            check('the report does not scroll sideways', not over)
            rp.close()
        except Exception as e:
            check('the report opens', False, str(e).split(chr(10))[0][:140])
        pg.evaluate("() => { const m = document.getElementById('modal');"
                    " if (m) m.classList.remove('on'); }")

        # interactions that are not a click
        print('\n--- keyboard and pointer ---')
        for key in ['ArrowRight', 'ArrowLeft', 'Home', 'End', 'l', 'v', 'e', 'h', '?']:
            clear(pg)
            pg.keyboard.press(key)
            pg.wait_for_timeout(30)
            b = errbar(pg)
            check('key %-11s is clean' % key, not b, b.replace('\n', ' ')[:120])
        clear(pg)
        box = pg.evaluate("() => { const r = wrap.getBoundingClientRect();"
                          " return [r.x, r.y, r.width, r.height]; }")
        pg.mouse.move(box[0] + box[2] / 2, box[1] + box[3] / 2)
        pg.mouse.wheel(0, -300)
        pg.wait_for_timeout(60)
        pg.mouse.down(); pg.mouse.move(box[0] + 200, box[1] + 200); pg.mouse.up()
        pg.wait_for_timeout(60)
        b = errbar(pg)
        check('scroll-zoom and drag-pan are clean', not b, b.replace('\n', ' ')[:140])

        print('\n--- console ---')
        errs = [c for c in console if c[0] == 'error']
        check('no console errors', not errs, ' || '.join(t + ': ' + m for t, m in errs[:4]))
        check('no uncaught page errors overall (%d)' % len(errors), not errors,
              ' || '.join(errors[:4]))
        br.close()
    return errors


for scale in (1, 1.5):
    run(scale)

print('\n' + '=' * 62)
print('  %d passed, %d failed' % (len(PASS), len(FAIL)))
for f in FAIL:
    print('    FAIL: ' + f)
print('=' * 62)
sys.exit(1 if FAIL else 0)
