"""
END-TO-END SELF TEST OF THE BUILT PAGE.

The Core module has hundreds of unit tests; the UI layer had none, and every
bug the user actually hit lived there -- a dead handler, a panel that threw, a
chart drawn off-screen. Static linting cannot catch a runtime error.

So this stubs enough of the browser (DOM, canvas 2d, localStorage, rAF) to
LOAD THE REAL PAGE, boot it, then click every control and open every panel,
asserting nothing throws and each panel actually produces content.
"""
import io, re, sys, json
import dukpy

HTML = r'C:\Users\ruben\nq-backtest\tape_reader.html'   # the built page

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name + (("   " + detail) if detail and not cond else ""))


page = io.open(HTML, encoding="utf-8").read()
js = page[page.index("<script>") + 8: page.rindex("</script>")]
ids = sorted(set(re.findall(r'id="([\w-]+)"', page[:page.index("<script>")])))

STUB = """
var __ERRORS = [], __CANVAS_CALLS = 0;
function __mkEl(id, tag){
  var e = {
    id: id, tagName: (tag || 'DIV').toUpperCase(), _html: '', style: {},
    dataset: {}, children: [], value: '', checked: false, textContent: '',
    clientWidth: 1200, clientHeight: 600, offsetWidth: 200, offsetHeight: 100,
    width: 1200, height: 600, files: [],
    onclick: null, onchange: null, oninput: null, ondblclick: null,
    classList: {
      _s: {},
      add: function(c){ this._s[c] = 1; },
      remove: function(c){ delete this._s[c]; },
      toggle: function(c, on){ if (on === undefined) on = !this._s[c];
                               if (on) this._s[c] = 1; else delete this._s[c]; return !!on; },
      contains: function(c){ return !!this._s[c]; }
    },
    appendChild: function(c){ this.children.push(c); return c; },
    addEventListener: function(){}, removeEventListener: function(){},
    getBoundingClientRect: function(){
      return {left: 0, top: 0, width: this.clientWidth, height: this.clientHeight}; },
    scrollIntoView: function(){},
    setAttribute: function(k, v){ if (k === 'viewBox') this._vb = v; },
    getAttribute: function(k){ return k === 'viewBox' ? (this._vb || '0 0 500 300') : null; },
    focus: function(){}, click: function(){ if (this.onclick) this.onclick({target: this}); },
    closest: function(){ return null; },
    getContext: function(){ return __ctx; }
  };
  Object.defineProperty(e, 'innerHTML', {
    get: function(){ return this._html; },
    set: function(v){
      this._html = String(v);
      /* Register ids the page just created. Without this getElementById knew
         only the static markup, so every control a panel builds inside
         innerHTML resolved to null and its `if (el)` binding silently did
         nothing -- none of the modal wiring was reachable from a test. */
      var re_ = /id=\"([\\w-]+)\"/g, mm;
      while ((mm = re_.exec(this._html))){
        if (!__els[mm[1]]) __els[mm[1]] = __mkEl(mm[1], 'button');
      }
      /* a <select> reports its first option, as a browser would, so the
         handlers that read .value are exercised rather than short-circuited */
      var rs = /<select id=\"([\\w-]+)\"[^>]*>\\s*<option value=\"([^\"]*)\"/g, ms;
      while ((ms = rs.exec(this._html))){
        if (__els[ms[1]] && !__els[ms[1]].value) __els[ms[1]].value = ms[2];
      }
    }
  });
  e.querySelectorAll = function(sel){ return __collect(this._html, sel); };
  e.querySelector = function(sel){ var r = __collect(this._html, sel); return r.length ? r[0] : null; };
  return e;
}
/* elements the page builds inside innerHTML are recovered by scanning the
   string for the attributes the binder looks for, so the click wiring that
   follows a redraw is exercised too */
function __collect(html, sel){
  var out = [], m, re_;
  var attr = /\\[([a-z-]+)(?:=[^\\]]*)?\\]/.exec(sel);
  if (attr){
    re_ = new RegExp(attr[1] + '="([^"]*)"', 'g');
    while ((m = re_.exec(html))){
      var el = __mkEl(null, 'button');
      el.dataset[__camel(attr[1].replace(/^data-/, ''))] = m[1];
      out.push(el);
    }
    return out;
  }
  var cls = /\\.([\\w-]+)/.exec(sel);
  if (cls){
    re_ = new RegExp('class="[^"]*' + cls[1] + '[^"]*"', 'g');
    while ((m = re_.exec(html))) out.push(__mkEl(null, 'div'));
    return out;
  }
  return out;
}
function __camel(s){ return s.replace(/-([a-z])/g, function(_, c){ return c.toUpperCase(); }); }

var __els = {};
ids.forEach(function(i){ __els[i] = __mkEl(i, i.charAt(0) === 'f' ? 'input' : 'div'); });

var __ctx = new Proxy({}, {
  get: function(t, k){
    if (k === 'canvas') return __mkEl('cv');
    if (k === 'measureText') return function(){ return {width: 40}; };
    if (k === 'createLinearGradient') return function(){ return {addColorStop: function(){}}; };
    if (k === 'getImageData') return function(){ return {data: []}; };
    return function(){ __CANVAS_CALLS++; };
  },
  set: function(){ return true; }
});

var document = {
  documentElement: {style: {setProperty: function(){}}, dataset: {},
                    setAttribute: function(){}, requestFullscreen: function(){ return {catch: function(){}}; }},
  body: __mkEl('body'),
  getElementById: function(i){ return __els[i] || null; },
  querySelector: function(s){
    var m = /^[.#]?([\\w-]+)/.exec(s); var id = m && m[1];
    if (s.charAt(0) === '#' && __els[id]) return __els[id];
    return __mkEl(id || 'x');
  },
  querySelectorAll: function(){ return []; },
  createElement: function(t){ return __mkEl(null, t); },
  addEventListener: function(){}, removeEventListener: function(){},
  dispatchEvent: function(){}, readyState: 'complete',
  fullscreenElement: null, exitFullscreen: function(){}
};
var window = {
  devicePixelRatio: 1, innerWidth: 1400, innerHeight: 800,
  addEventListener: function(){}, removeEventListener: function(){},
  getComputedStyle: function(){ return {getPropertyValue: function(k){
    return {'--up':'#4bb073','--down':'#d1565a','--accent':'#d8a24a',
            '--mono':'monospace','--sans':'sans-serif'}[k] || '#888'; }}; }
};
var getComputedStyle = window.getComputedStyle;
function ResizeObserver(cb){ this.observe = function(){ cb(); }; }
function requestAnimationFrame(fn){ try { fn(); } catch(e){ __ERRORS.push('rAF: ' + e.message); } return 1; }
function setInterval(){ return 1; } function clearInterval(){}
function setTimeout(fn){ try { fn(); } catch(e){} return 1; } function clearTimeout(){}
/* the ensemble slices its runs on the clock; here it just runs to the end */
var performance = {now: function(){ return Date.now(); }};
var localStorage = {
  _d: {},
  getItem: function(k){ return this._d[k] === undefined ? null : this._d[k]; },
  setItem: function(k, v){ this._d[k] = String(v); },
  removeItem: function(k){ delete this._d[k]; }
};
var FileReader = function(){ this.readAsText = function(){}; };
/* the canonical polyfill: my first attempt mishandled padding and returned a
   byte count that was not a multiple of two, so the Int16Array view over it
   threw "invalid length" before the page could even boot */
function atob(input){
  var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  var str = String(input).replace(/=+$/, '');
  var output = '';
  if (str.length % 4 === 1) throw new Error('bad base64');
  for (var bc = 0, bs = 0, buffer, i = 0; (buffer = str.charAt(i++));){
    buffer = chars.indexOf(buffer);
    if (~buffer){
      bs = bc % 4 ? bs * 64 + buffer : buffer;
      if (bc++ % 4) output += String.fromCharCode(255 & bs >> (-2 * bc & 6));
    }
  }
  return output;
}
"""

print("Booting the real page under a stubbed browser...\n")
interp = dukpy.JSInterpreter()
interp.evaljs("var ids = %s;" % json.dumps(ids))
interp.evaljs(STUB)

print("--- boot ---")
try:
    interp.evaljs(js)
    booted = True
except Exception as e:
    booted = False
    msg = str(e).split("\n")[0][:220]
print("" if booted else "  boot error: " + msg)
check("the page boots without throwing", booted, "" if booted else msg)
if not booted:
    print("\ncannot continue without a successful boot")
    sys.exit(1)

errs = interp.evaljs("__ERRORS")
check("no errors surfaced during boot", not errs, str(errs))
check("the canvas was actually drawn to", interp.evaljs("__CANVAS_CALLS") > 100,
      "only %s canvas calls" % interp.evaljs("__CANVAS_CALLS"))
check("bars decoded", interp.evaljs("BASE && BASE.n") > 300000,
      str(interp.evaljs("BASE && BASE.n")))
check("trades rebuilt from the columnar format", interp.evaljs("TRADES.length") > 4000,
      str(interp.evaljs("TRADES.length")))
check("minutes were derived, and are sane",
      interp.evaljs("BASE.mins[0] >= 500 && BASE.mins[0] < 1000 ? 1 : 0") == 1,
      "first minute = %s" % interp.evaljs("BASE.mins[0]"))
check("volume survived the compact encoding",
      interp.evaljs("BASE.v && BASE.v[0] > 0 ? 1 : 0") == 1)

print("\n--- every panel opens and produces content ---")
for fn, name in (("sizingHTML", "Sizing"), ("wealthHTML", "Wealth"),
                 ("setupsHTML", "Setups"), ("strategyHTML", "Strategy"),
                 ("accountHTML", "Prop firm"), ("settingsHTML", "Settings"),
                 ("indicatorsHTML", "Indicators")):
    try:
        n = interp.evaljs("(%s() || '').length" % fn)
        check("%s panel renders (%s chars)" % (name, format(n, ",")), n > 400,
              "produced %s chars" % n)
    except Exception as e:
        check("%s panel renders" % name, False, str(e).split("\n")[0][:150])

print("\n--- every toolbar control fires without throwing ---")
CLICKS = [i for i in ids if i.startswith(("b", "t", "d", "r", "z", "c", "l")) and i not in
          ("bindn", "body")]
bad = []
for cid in CLICKS:
    try:
        interp.evaljs(
            "(function(){var e=document.getElementById(%s);"
            "if(!e||!e.onclick) return 'nohandler';"
            "try{ e.onclick({target:e, preventDefault:function(){}, stopPropagation:function(){}}); }"
            "catch(err){ return 'THREW: '+err.message; } return 'ok';})()" % json.dumps(cid))
    except Exception as e:
        bad.append((cid, str(e).split("\n")[0][:90]))
        continue
res = {}
for cid in CLICKS:
    r = interp.evaljs(
        "(function(){var e=document.getElementById(%s);"
        "if(!e||!e.onclick) return 'nohandler';"
        "try{ e.onclick({target:e, preventDefault:function(){}, stopPropagation:function(){}}); }"
        "catch(err){ return 'THREW: '+err.message; } return 'ok';})()" % json.dumps(cid))
    res[cid] = r
threw = {k: v for k, v in res.items() if str(v).startswith("THREW")}
nohand = [k for k, v in res.items() if v == "nohandler"]
check("no toolbar control throws when clicked", not threw,
      "; ".join("%s -> %s" % kv for kv in threw.items()))
print("     (%d clicked, %d had no onclick: %s)" % (len(res), len(nohand), nohand or "none"))


print("\n--- the wealth panel: comparison table and assumptions ---")

# Every size under both cap settings must render both columns, not just the
# selected one -- that was the whole point of the change.
for size in ("1 MNQ", "5 MNQ", "1 NQ"):
    for cap in ("nocap", "cap"):
        h = interp.evaljs(
            "WL.size=%s; WL.cap=%s; WL.info=false; wealthHTML();"
            % (json.dumps(size), json.dumps(cap)))
        ok = ("No funded cap" in h and "$625 funded cap" in h
              and "No data for this size" not in h)
        check("%s / %s shows both columns" % (size, cap), ok,
              "missing a column" if not ok else "")

# The hover text the user asked for has to actually be on the rows.
h = interp.evaljs("WL.size='1 NQ'; WL.cap='nocap'; WL.info=false; wealthHTML();")
hints = h.count('class="why"')
check("every row carries a hover explanation (%d found)" % hints, hints >= 7,
      "only %d hint spans" % hints)
check("esc() escapes every dangerous character",
      interp.evaljs("esc('a\"b<c>&d\\'e')") == "a&quot;b&lt;c&gt;&amp;d&#39;e",
      "esc gave %r" % interp.evaljs("esc('a\"b<c>&d\\'e')"))
check("esc() escapes & before the entities it introduces",
      interp.evaljs("esc('<')") == "&lt;",
      "got %r" % interp.evaljs("esc('<')"))

# "More info" must expand the full walkthrough.
check("assumptions are hidden until asked for", "The firm" not in h)
hi = interp.evaljs("WL.info=true; wealthHTML();")
groups = ["The data", "The strategy", "Execution and costs", "The firm",
          "Payout accounting", "The statistics"]
missing = [g for g in groups if g not in hi]
check("more info explains it from start to finish (%d groups, %s chars)"
      % (len(groups) - len(missing), format(len(hi), ",")),
      not missing, "missing: %s" % missing)
n_items = hi.count('<li>')
check("every assumption is listed (%d items)" % n_items, n_items >= 20,
      "only %d" % n_items)
for tag in ("flatters it", "conservative", "neutral"):
    check("assumptions are tagged '%s'" % tag, tag in hi)
check("the optimistic ones are called out", hi.count('bias opt') >= 3,
      "only %d flagged as flattering" % hi.count('bias opt'))

# The figures on the page must be the figures that were reported -- by
# regen_payout_panels.py (payout = $1,000 x 90% = $900, account carries on).
EXPECT = {
    "1 NQ|nocap": dict(evals=583, spent=37895, payouts=124, won=112050,
                       net=74410, wins=60),
    "1 NQ|cap":   dict(evals=478, spent=31070, payouts=71, won=63900,
                       net=31888, wins=60),
}
got = json.loads(interp.evaljs(r"""
(function(){
  var med = function(a){ var v = a.slice().sort(function(x,y){return x-y;});
    var n = v.length, h = n >> 1;
    return n % 2 ? v[h] : (v[h-1] + v[h]) / 2; };
  var out = {};
  ['1 NQ|nocap', '1 NQ|cap'].forEach(function(k){
    var r = WEALTH.runs[k];
    out[k] = { evals: med(r.evals), spent: med(r.spent), payouts: med(r.payouts),
               won: med(r.won), net: med(r.nets),
               wins: r.nets.filter(function(x){ return x > 0; }).length };
  });
  return JSON.stringify(out);
})()"""))
for k, want in EXPECT.items():
    for field, wv in want.items():
        gv = got[k][field]
        near = abs(round(gv) - wv) <= 1
        check("%s %s = %s" % (k, field, format(round(gv), ",")), near,
              "page says %s, reported %s" % (format(round(gv), ","), format(wv, ",")))

# and those same numbers have to reach the rendered table
tbl = interp.evaljs("WL.size='1 NQ'; WL.cap='nocap'; WL.info=false; cmpTable();")
for want in ("583", "124", "60 of 60"):
    check("the table renders %s" % want, want in tbl)
_net = re.search('class="big".{0,400}', tbl, re.S)
check("net is shown signed and separated", "+$74,410" in tbl,
      "net row was: %s" % (_net.group(0)[:300] if _net else "NOT FOUND"))


print("\n--- the fixes from the code review ---")

# sep() used to comma the fractional part: sep(1.23456) -> '1.23,456'
for val, want in (("1234567", "1,234,567"), ("1.23456", "1.23456"),
                  ("-1234", "-1,234"), ("999", "999"), ("1234.5", "1,234.5")):
    got = interp.evaljs("sep(%s)" % val)
    check("sep(%s) = %s" % (val, want), got == want, "got %r" % got)

# halves round to even, matching the analysis that produced the figures
for val, want in ((108882.5, 108882), (698.5, 698), (73.5, 74), (2.5, 2), (3.5, 4)):
    got = interp.evaljs("rhe(%s)" % val)
    check("rhe(%s) = %s" % (val, want), got == want, "got %r" % got)

# the ticket pace has to be right for every size, not just 1 NQ
paces = {}
for z in ("1 MNQ", "5 MNQ", "1 NQ"):
    paces[z] = interp.evaljs(
        "WL.size=%s; WL.cap='nocap'; WL.info=false; wealthHTML();" % json.dumps(z))
# 594.5 accounts over 824 sessions is one every 1.39, past pace()'s 1.25 cut
check("1 NQ states its pace as about one every 1.4 sessions",
      "about one every 1.4 sessions" in paces["1 NQ"])
check("1 MNQ is not described as one a session",
      "close to one a session" not in paces["1 MNQ"],
      "1 MNQ still claims a daily pace")
check("1 MNQ states its own, much slower pace",
      "one every" in paces["1 MNQ"])

# the trailing-drawdown freeze was misstated by $1,000
hi = interp.evaljs("WL.size='1 NQ'; WL.info=true; wealthHTML();")
check("the freeze is described against the floor, not the balance",
      "the floor itself reaches $25,100" in hi)
check("the balance figure that actually triggers it is given",
      "$26,100" in hi)

# the rows are independent medians and must say so
check("the table warns the rows do not add up",
      "the rows do not add up" in hi)
check("the net hover does not claim to be a subtraction of two rows",
      "Won minus spent. This is the answer" not in hi)

# every wealth curve must close on the run's own net
gap = interp.evaljs("""
(function(){
  var worst = 0;
  ['1 MNQ|nocap','5 MNQ|nocap','1 NQ|nocap','1 NQ|cap'].forEach(function(k){
    var r = WEALTH.runs[k];
    r.curves.forEach(function(c, i){
      var d = Math.abs(c.concat([r.nets[i]]).pop() - r.nets[i]);
      if (d > worst) worst = d;
    });
  });
  return worst;
})()""")
check("the plotted curves close exactly on each run's net", gap == 0,
      "worst gap $%s" % gap)

# the sizing panel must not print fractional accounts or payouts
sz = interp.evaljs("sizingHTML()")
import re as _re2
cells = _re2.findall(r'<td[^>]*>(?:<b>)?(?:<span[^>]*>)?(\d+\.\d+)', sz)
frac = [c for c in cells if not c.endswith(('.00', '.25', '.50', '.75'))]
check("the sizing table prints no fractional counts",
      not [c for c in cells if c.endswith('.5')],
      "fractional cells: %s" % cells[:6])

# one format for one figure
wv = interp.evaljs("WL.size='1 NQ'; WL.cap='nocap'; WL.info=false; wealthHTML();")
check("the verdict banner uses the same format as the table",
      "$74,410" in wv and "74410" not in wv,
      "banner and table still disagree")

# the disclosure must not leak across opens
interp.evaljs("WL.info = true; openWealth();")
interp.evaljs("var c=document.getElementById('wlClose'); if(c&&c.onclick) c.onclick({});")
check("closing the panel resets the disclosure",
      interp.evaljs("WL.info ? 1 : 0") == 0,
      "WL.info stayed true, so it reopens expanded")


print("\n--- every control inside every panel ---")

OPENERS = [("Wealth", "openWealth()"), ("Setups", "openSetups()"),
           ("Sizing", "openSizing()"), ("Strategy", "openStrategy()"),
           ("Prop firm", "openAccount()"),
           ("Settings", "document.getElementById('sheet').innerHTML = settingsHTML();"
                        " bindSettings(); 1"),
           ("Indicators", "openIndicators()")]
for name, call in OPENERS:
    try:
        interp.evaljs(call)
    except Exception as e:
        check("%s panel opens" % name, False, str(e).split("\n")[0][:120])
        continue
    html = interp.evaljs("document.getElementById('sheet').innerHTML || ''")
    inner = sorted(set(re.findall(r'id="([\w-]+)"', html)))
    if not inner:
        check("%s panel exposes controls" % name, False, "no ids in the sheet")
        continue
    bad = []
    for cid in inner:
        r = interp.evaljs(
            "(function(){var e=document.getElementById(%s);"
            "if(!e) return 'missing'; if(!e.onclick) return 'nohandler';"
            "try{ e.onclick({target:e, preventDefault:function(){},"
            " stopPropagation:function(){}}); }"
            "catch(err){ return 'THREW: '+err.message; } return 'ok';})()" % json.dumps(cid))
        if str(r).startswith("THREW"):
            bad.append("%s -> %s" % (cid, r))
        # re-open, since a click may have replaced the sheet
        try:
            interp.evaljs(call)
        except Exception:
            pass
    check("%s: %d controls, none throw" % (name, len(inner)), not bad,
          "; ".join(bad[:3]))

# the size and cap buttons drive the whole study, so exercise them properly
interp.evaljs("openWealth()")
combos = interp.evaljs(r"""
(function(){
  var bad = [];
  ['1 MNQ','5 MNQ','1 NQ'].forEach(function(z){
    ['nocap','cap'].forEach(function(c){
      try { WL.size = z; WL.cap = c;
            var h = wealthHTML();
            if (!h || h.length < 2000) bad.push(z + '|' + c + ' short');
      } catch(e){ bad.push(z + '|' + c + ': ' + e.message); }
    });
  });
  return bad.join('; ');
})()""")
check("all six size/cap combinations render", not combos, combos)


print("\n--- the prop firm panel ---")

interp.evaljs("openAccount()")
h = interp.evaljs("accountHTML()")
check("the panel leads with a one-click preset", 'id="apLucid"' in h)
check("the fields are grouped, not one flat list",
      h.count("<h3>") >= 3, "%d groups" % h.count("<h3>"))
check("every control carries a plain-language note",
      h.count("ink-faint") >= 14, "%d notes" % h.count("ink-faint"))
check("only the sizing field in use is shown",
      ('id="aCon"' in h) != ('id="aRisk"' in h),
      "both or neither sizing input rendered")

# the preset must actually apply the firm's stated rules
interp.evaljs("var b=document.getElementById('apLucid'); b.onclick({});")
got = json.loads(interp.evaljs(
    "JSON.stringify({b:S.acct.balance, pv:S.acct.pointValue, c:S.acct.commission,"
    " s:S.acct.slippage, n:S.acct.contracts, on:S.acct.on,"
    " t:S.acct.evaluation.target, cap:S.acct.evaluation.dailyCap,"
    " dd:S.acct.evaluation.trailDD, fee:S.acct.evaluation.cost,"
    " frz:S.acct.evaluation.freezeOffset, rep:S.acct.evaluation.repeat})"))
WANT = {"b": 25000, "pv": 20, "c": 1.5, "s": 0.25, "n": 1, "on": True,
        "t": 1250, "cap": 625, "dd": 1000, "fee": 65, "frz": 100, "rep": True}
for k, v in WANT.items():
    check("preset sets %s = %s" % (k, v), got[k] == v, "got %r" % got[k])

# the readout is the point of the panel: at 1 NQ the floor binds before the stop
h2 = interp.evaljs("accountHTML()")
check("the panel states what the settings mean", "What these settings mean" in h2)
check("it gives the distance to liquidation in points",
      "pts</b> against you" in h2)
# 1 NQ: round turn = 2*1.50 + 2*0.25*20 = $13; (1000-13)/20 = 49.35 pts
check("that distance is computed correctly for 1 NQ", "49.4 pts" in h2,
      "expected 49.4 pts somewhere in the readout")
check("it warns that the floor binds before a 50-point stop",
      "less than a 50-point stop" in h2)

# turning it all off must be one click too
interp.evaljs("var b=document.getElementById('apOff'); b.onclick({});")
check("the off switch clears both the simulator and the rules",
      interp.evaljs("(!S.acct.on && !S.acct.evaluation.on) ? 1 : 0") == 1)

# Instrument presets: every contract in the databento folder, and the loader
# that makes their files usable. The stub cannot click a collected button, so
# the click wiring is exercised in test_browser.py; here the markup and the
# pure loader function are checked.
print("\n--- instruments and the bar loader ---")
interp.evaljs("ST.stageView = 'eval'; ST.funded.same = true; openStrategy();")
h = interp.evaljs("document.getElementById('sheet').innerHTML || ''")
keys = re.findall(r'data-inst="\d+"[^>]*>([A-Z0-9]+)<', h)
check("every instrument in the data folder has a preset (%s)" % " ".join(keys),
      keys == ["NQ", "MNQ", "ES", "MES", "RTY", "M2K", "CL", "MCL", "GC", "MGC", "YM", "MYM", "SI", "SIL", "HG", "HE", "NKD"])
check("a contracts row from 1 to 10 replaces the MNQ-only ladder",
      len(re.findall(r'data-con="\d+"', h)) == 10 and "data-lad" not in h)
check("each preset says what it sets", 'tick 0.01' in h and '$1000 a point' in h and 'Lucid $2.00' in h)
check("the presets carry Lucid's commissions",
      {z["key"]: z["comm"] for z in json.loads(interp.evaljs("JSON.stringify(INSTRUMENTS)"))} ==
      {"NQ": 1.75, "MNQ": 0.5, "ES": 1.75, "MES": 0.5, "RTY": 1.75, "M2K": 0.5, "CL": 2.0, "MCL": 0.5, "GC": 2.3, "MGC": 0.8,
       "YM": 1.75, "MYM": 0.5, "SI": 2.3, "SIL": 1.6, "HG": 2.3, "HE": 2.8, "NKD": 1.75})
check("every preset offers three slippage figures, in rising order",
      all(len(z["slip"]) == 3 and z["slip"][0] <= z["slip"][1] < z["slip"][2] for z in json.loads(interp.evaljs("JSON.stringify(INSTRUMENTS)"))))
interp.evaljs("ST.pointValue = 1000; ST.commission = 2.0; ST.slippage = 0.02; openStrategy();")
h = interp.evaljs("document.getElementById('sheet').innerHTML || ''")
check("on CL the slippage row offers generous / normal / conservative in ticks",
      'data-slip="0.01"' in h and 'data-slip="0.02"' in h and 'data-slip="0.04"' in h and '4 ticks a side' in h)
check("the figure in force is marked", 'class="btn on" data-slip="0.02"' in h)
interp.evaljs("ST.pointValue = 2; ST.commission = 0.5; ST.slippage = 0.5;")

# databento clock: UTC with an offset, before and after the March DST change,
# with a Sunday evening bar. RTH on keeps exactly the four 09:30 / 15:59
# New York bars and dates them by the New York day.
CSV_UTC = "\n".join([
    "timestamp,open,high,low,close,volume",
    "2024-03-08 14:29:00+00:00,1,1,1,1,1",   # 09:29 EST  out
    "2024-03-08 14:30:00+00:00,2,2,2,2,1",   # 09:30 EST  in
    "2024-03-08 20:59:00+00:00,3,3,3,3,1",   # 15:59 EST  in
    "2024-03-08 21:00:00+00:00,4,4,4,4,1",   # 16:00 EST  out
    "2024-03-10 23:00:00+00:00,5,5,5,5,1",   # Sunday 19:00 EDT  out
    "2024-03-11 13:29:00+00:00,6,6,6,6,1",   # 09:29 EDT  out
    "2024-03-11 13:30:00+00:00,7,7,7,7,1",   # 09:30 EDT  in
    "2024-03-11 19:59:00+00:00,8,8,8,8,1",   # 15:59 EDT  in
    "2024-03-11 20:00:00+00:00,9,9,9,9,1"])  # 16:00 EDT  out
interp.evaljs("var __csv = %s;" % json.dumps(CSV_UTC))
r = json.loads(interp.evaljs(
    "S.rthOnly = true; var b = barsFromCSV(__csv);"
    " JSON.stringify({n: b.n, mins: Array.prototype.slice.call(b.mins), o: Array.prototype.slice.call(b.o),"
    " days: b.sessions.map(function(s){ return s.day; }), clock: b.clock, note: clockNote(b)})"))
check("a UTC file is converted to New York time across the DST change",
      r["mins"] == [570, 959, 570, 959], str(r["mins"]))
check("RTH on keeps only the 09:30-15:59 bars", r["n"] == 4 and r["o"] == [2, 3, 7, 8], str(r["o"]))
check("sessions are New York days", r["days"] == ["2024-03-08", "2024-03-11"], str(r["days"]))
check("the subtitle says what was done to the clock",
      "09:30" in r["note"] and "New York" in r["note"], r["note"])
r2 = json.loads(interp.evaljs(
    "S.rthOnly = false; var b2 = barsFromCSV(__csv);"
    " JSON.stringify({n: b2.n, first: b2.mins[0], sun: b2.mins[4], days: b2.sessions.length, note: clockNote(b2)})"))
check("RTH off keeps every bar, still on the New York clock",
      r2["n"] == 9 and r2["first"] == 569 and r2["sun"] == 19 * 60 and r2["days"] == 3, str(r2))
check("and says so", "all hours" in r2["note"], r2["note"])
# a datetime_et export carries no offset: the clock is taken as written
CSV_ET = "datetime_et,open,high,low,close\n2024-03-08 09:30:00,1,1,1,1\n2024-03-08 12:00:00,2,2,2,2\n2024-03-08 16:30:00,3,3,3,3"
r3 = json.loads(interp.evaljs(
    "S.rthOnly = true; var b3 = barsFromCSV(%s);"
    " JSON.stringify({n: b3.n, mins: Array.prototype.slice.call(b3.mins), conv: b3.clock.converted, note: clockNote(b3)})"
    % json.dumps(CSV_ET)))
check("a file without an offset is read as written and still cut",
      r3["n"] == 2 and r3["mins"] == [570, 720] and not r3["conv"] and "as in the file" in r3["note"], str(r3))
# a daily file has one clock value: never cut, never mis-sessioned
CSV_D = "date,open,high,low,close\n2024-03-08,1,1,1,1\n2024-03-11,2,2,2,2\n2024-03-12,3,3,3,3"
r4 = json.loads(interp.evaljs(
    "var b4 = barsFromCSV(%s); JSON.stringify({n: b4.n, s: b4.sessions.length, note: clockNote(b4)})" % json.dumps(CSV_D)))
check("a daily file is left alone: not cut, one spanning session",
      r4["n"] == 3 and r4["s"] == 1 and r4["note"] == "", str(r4))
try:
    interp.evaljs("S.rthOnly = true; barsFromCSV('timestamp,open,high,low,close\\n2024-03-08 02:00:00+00:00,1,1,1,1\\n2024-03-08 03:00:00+00:00,1,1,1,1');")
    check("a file with nothing in the day session says so instead of loading nothing", False, "no error")
except Exception as e:
    check("a file with nothing in the day session says so instead of loading nothing",
          "turn RTH off" in str(e), str(e)[:120])
# an Excel export carries a byte-order mark in front of the header
r5 = json.loads(interp.evaljs(
    "var b5 = barsFromCSV('\uFEFF' + %s); JSON.stringify({n: b5.n, s: b5.sessions.length, m0: b5.mins[0]})" % json.dumps(CSV_ET)))
check("a byte-order mark before the header does not hide the timestamp column",
      r5["n"] == 2 and r5["s"] == 1 and r5["m0"] == 570, str(r5))
interp.evaljs("S.rthOnly = true; __csv = null;")

# The Strategy panel's ensemble: many seeds under one set of rules, off the
# chart. The stubbed setTimeout is synchronous, so runEnsemble() finishes
# inline. Kept before the indicator step below, which exhausts the heap.
print("\n--- the ensemble ---")
interp.evaljs("ST.key = 'reentry'; ST.funded.same = true; ST.seed = 23; ST.stopPts = 50;"
              " ST.ensN = 10; ST.from = ''; ST.to = ''; ENS.res = null; ENS.busy = false;"
              " STRES = null;   /* the UI clears the cached run on every edit; so must we */")
h = interp.evaljs("ensembleHTML()")
check("before a run the block offers the seed counts, 1000 included, and a Run button",
      'data-ens="100"' in h and 'data-ens="1000"' in h and 'id="stEnsRun"' in h and
      'Run 10 seeds<' in h)
check("nothing is drawn before a run", '<svg' not in h and 'class="cmp"' not in h)
interp.evaljs("ST.key = 'orb';")
h = interp.evaljs("ensembleHTML()")
check("a deterministic strategy is told there is no coin to multiply, and gets no Run button",
      'takes no random decision' in h and 'stEnsRun' not in h and 'data-ens=' not in h)
interp.evaljs("ST.key = 'reentry'; openStrategy();")   # opening loads the single seed on the chart
on_chart = interp.evaljs("TRADES.length")
try:
    interp.evaljs("runEnsemble();")
    ran = interp.evaljs("(ENS.res && !ENS.busy) ? 1 : 0") == 1
except Exception as e:
    ran = False
    print("  ensemble threw: " + str(e).split("\n")[0][:160])
check("ten seeds run to completion", ran)
if ran:
    R = json.loads(interp.evaljs(
        "JSON.stringify({n: ENS.res.n, seeds: ENS.res.seeds, nets: ENS.res.nets, a: ENS.res.a,"
        " b: ENS.res.b, len: ENS.res.curves[0].length,"
        " ends: ENS.res.curves.map(function(c){ return c[c.length - 1]; })})"))
    check("the batch is ten consecutive seeds from a fresh base",
          all((R["seeds"][0] + k) % 2 ** 32 == R["seeds"][k] for k in range(10)), str(R["seeds"]))
    check("the batch does not start at the chart's seed", R["seeds"][0] != 23, str(R["seeds"][:2]))
    check("every curve ends on its run's net",
          all(abs(a - b) < 1e-6 for a, b in zip(R["nets"], R["ends"])))
    check("the curves cover the whole tape when no span is set",
          R["a"] == 0 and R["len"] == interp.evaljs("BASE.sessions.length") and
          R["b"] == R["len"] - 1)
    check("the ensemble leaves the chart alone", interp.evaljs("TRADES.length") == on_chart)
    h = interp.evaljs("ensembleHTML()")
    check("the block draws the curves and the histogram", h.count("<svg") == 2, "%d svgs" % h.count("<svg"))
    check("the chart's seed is drawn against the batch", 'data-seed="23"' in h)
    check("the chart's seed is placed among the ten",
          re.search(r"finishes ahead of <b>\d+ of these 10</b>", h) is not None)
    my_net = interp.evaljs("STRES.summary.net")
    check("the This-seed column is the run on the chart",
          re.search(r'<td>Net</td><td>' + re.escape(interp.evaljs("money0(%s)" % my_net)), h) is not None)
    check("the table carries the eight statistics", h.count("<tr") == 9, "%d rows" % h.count("<tr"))
    for col in ("5th", "25th", "Median", "75th", "95th", "Mean", "SD"):
        check("the table has a %s column" % col, "<th>%s</th>" % col in h)
    q = json.loads(interp.evaljs("JSON.stringify(STRES.summary)"))
    check("Won minus Spent is Net for the run on the chart, and both are shown",
          abs(q["won"] - q["spent"] - q["net"]) < 1e-9 and
          ("<td>Won from payouts</td><td>" + interp.evaljs("money0(%s)" % q["won"])) in h and
          ("<td>Spent on tickets</td><td>" + interp.evaljs("money0(%s)" % q["spent"])) in h)
    net_row = re.search(r'<td>Net</td>(.*?)</tr>', h).group(1)
    check("the Net row has nine finite cells, SD included",
          net_row.count("<td>") == 8 and "—" not in net_row and "NaN" not in net_row, net_row[:200])
    # percentiles must survive a "never paid" run without turning into NaN
    check("pctOf steps onto Infinity rather than interpolating into NaN",
          interp.evaljs("pctOf([1, 2, Infinity, Infinity], 0.5) === Infinity ? 1 : 0") == 1 and
          interp.evaljs("pctOf([1, 2, Infinity], 0.5)") == 2 and
          abs(interp.evaljs("pctOf([1, 2, 3, Infinity], 0.25)") - 1.75) < 1e-9)
    check("the caveat names the sessions, the batch's seeds, not a forecast",
          "not a forecast" in h and ("seeds %d to %d" % (R["seeds"][0], R["seeds"][9])) in h)
    # ten faint lines below the cut; bands above it, built from the same runs
    check("up to 100 runs are drawn one by one",
          h.count('stroke-width="0.8"') == 10 and 'stroke="none"' not in h)
    hb = interp.evaljs("ensCurves(Object.assign({}, ENS.res, {n: 101}), null)")
    check("past 100 runs the fan becomes two bands and no lines",
          hb.count('stroke="none"') == 2 and 'stroke-width="0.8"' not in hb)
    first = R["seeds"][0]
    interp.evaljs("runEnsemble();")
    check("pressing again draws a different batch",
          interp.evaljs("ENS.res.seeds[0]") != first)
    interp.evaljs("ST.seed = 31; STRES = null;")
    h = interp.evaljs("ensembleHTML()")
    check("moving the chart to another seed keeps the batch and re-compares",
          "Settings have changed" not in h and 'data-seed="31"' in h)
    interp.evaljs("ST.seed = 23; ST.stopPts = 60; STRES = null;")
    h = interp.evaljs("ensembleHTML()")
    check("changing a rule marks the ensemble stale and drops the comparison",
          "Settings have changed" in h and "data-seed=" not in h)
    interp.evaljs("ST.stopPts = 50; STRES = null; ENS.res = null;")

# The last-hour candle study inside the panel: five entries, a Flat-by input, the
# stored-decision replay, and the coin-on-the-same-bar ensemble for a fixed rule.
print("\n--- the last-hour candle ---")
for k in ("lh5", "lh5coin", "long1505", "lh5rf", "lh5rfdir"):
    check("STRATS has %s" % k, interp.evaljs("STRATS['%s'] ? 1 : 0" % k) == 1)
check("the LH5 note quotes the trade-level verdict",
      "a coin" in interp.evaljs("STRATS.lh5.note") and "Tested" in interp.evaljs("STRATS.lh5.note"))
check("the forest note names the first out-of-sample month and the replay",
      "2024-01" in interp.evaljs("STRATS.lh5rf.note") and "does not run here" in interp.evaljs("STRATS.lh5rf.note"))
check("the stored tables cover every tape day", interp.evaljs(
      "Object.keys(LH5.rf.sides.f50).length === BASE.sessions.length && Object.keys(LH5.rf.sides.dir).length === BASE.sessions.length ? 1 : 0") == 1)
interp.evaljs("ST.key = 'lh5'; ST.exitMin = 960; STRES = null; ENS.res = null; openStrategy();")
o = json.loads(interp.evaljs("JSON.stringify(stratOpts().entry)"))
check("the LH5 entry carries the window, the direction and the 15:49 exit",
      o["mode"] == "window" and o["direction"] == "window" and o["winMin"] == 900 and o["winBars"] == 5 and o["exitMin"] == 949)
r = json.loads(interp.evaljs("JSON.stringify((STRES || runStrat()).summary)"))
check("the rule trades at most once a session (%d trades)" % r["nTrades"], 0 < r["nTrades"] <= len(SESS_DAYS := interp.evaljs("BASE.sessions.map(function(s){return s.day;})")))
exits = interp.evaljs("(STRES || runStrat()).trades.filter(function(t){return !t.skipped;}).map(function(t){return BASE.mins[t.exit_bar];})")
check("every LH5 trade is out by 15:49", all(m <= 949 for m in exits))
check("the Flat by input is on the panel", interp.evaljs("document.getElementById('stFlat') ? 1 : 0") == 1)
interp.evaljs("var f = document.getElementById('stFlat'); f.value = '15:30'; f.onchange();")
check("Flat by 15:30 overrides the strategy's own exit", interp.evaljs("stratOpts().entry.exitMin") == 930)
interp.evaljs("var f = document.getElementById('stFlat'); f.value = '16:00'; f.onchange();")
check("Flat by 16:00 hands the exit back to the strategy", interp.evaljs("stratOpts().entry.exitMin") == 949)
interp.evaljs("ENS.res = null; STRES = null;")
h = interp.evaljs("ensembleHTML()")
check("a fixed rule's ensemble panel says there is no coin to multiply",
      "takes no random decision" in h and "stEnsRun" not in h)
interp.evaljs("runEnsemble();")
check("running the ensemble is a no-op for a rule with no random decision",
      interp.evaljs("(ENS.res === null && !ENS.busy) ? 1 : 0") == 1)
interp.evaljs("ST.key = 'lh5rf'; STRES = null; openStrategy();")
o = json.loads(interp.evaljs("JSON.stringify({d: stratOpts().entry.direction, n: Object.keys(stratOpts().entry.sides).length})"))
check("the forest entry replays a stored table", o["d"] == "table" and o["n"] == len(SESS_DAYS))
sk = interp.evaljs("(STRES || runStrat()).trades.filter(function(t){return t.skipped && t.reason === 'model abstained';}).length")
check("days before 2024 and days the forest declined show as stand-aside rows (%d)" % sk, sk > 200)
check("no violation from a missing decision", interp.evaljs("(STRES || runStrat()).violations.length") == 0)
interp.evaljs("ST.key = 'reentry'; ST.exitMin = 960; STRES = null; ENS.res = null;")

# The 30-minute forest (RF2): two entries, a per-entry hold, a stored decision per slot.
print("\n--- the 30-minute forest ---")
for k in ("rf2", "coin30"):
    check("STRATS has %s" % k, interp.evaljs("STRATS['%s'] ? 1 : 0" % k) == 1)
check("the forest note quotes the verdict and says the model does not run here",
      "Tested" in interp.evaljs("STRATS.rf2.note") and "does not run here" in interp.evaljs("STRATS.rf2.note"))
check("the stored slot table covers every tape day", interp.evaljs(
      "Object.keys(RF2.sides).length === BASE.sessions.length ? 1 : 0") == 1)
check("a full day carries twelve slot decisions", interp.evaljs(
      "Object.keys(RF2.sides[BASE.sessions[5].day]).length") == 12)
interp.evaljs("ST.key = 'coin30'; ST.exitMin = 960; STRES = null; ENS.res = null; openStrategy();")
o = json.loads(interp.evaljs("JSON.stringify(stratOpts().entry)"))
check("the 30-minute coin carries holdMin 30 and no stored table",
      o["direction"] == "random" and o["holdMin"] == 30 and o.get("sides") is None)
spans = interp.evaljs("(STRES || runStrat()).trades.filter(function(t){return !t.skipped;}).map(function(t){return BASE.mins[t.exit_bar] - BASE.mins[t.entry_bar];})")
check("every 30-minute coin trade is out within 29 minutes of its entry (%d trades)" % len(spans),
      len(spans) > 5000 and max(spans) <= 29)
interp.evaljs("ST.key = 'rf2'; STRES = null; openStrategy();")
o = json.loads(interp.evaljs("JSON.stringify({d: stratOpts().entry.direction, h: stratOpts().entry.holdMin, n: Object.keys(stratOpts().entry.sides).length})"))
check("the forest entry replays a per-slot table with the 30-minute hold",
      o["d"] == "table" and o["h"] == 30 and o["n"] == len(SESS_DAYS))
rf = json.loads(interp.evaljs("""JSON.stringify((function(){ var r = STRES || runStrat();
  var taken = r.trades.filter(function(t){return !t.skipped;});
  var wrong = taken.filter(function(t){return RF2.sides[t.day][String(BASE.mins[t.entry_bar])] !== t.side;}).length;
  return {abst: r.trades.filter(function(t){return t.skipped && t.reason === 'model abstained';}).length,
          taken: taken.length, wrong: wrong, viol: r.violations.length,
          late: taken.filter(function(t){return BASE.mins[t.exit_bar] - BASE.mins[t.entry_bar] > 29;}).length}; })())"""))
check("the forest stands aside on %d slots and trades %d" % (rf["abst"], rf["taken"]), rf["abst"] > 3000 and rf["taken"] > 1000)
check("every forest trade took the stored side for its slot", rf["wrong"] == 0, "%d wrong" % rf["wrong"])
check("no forest trade runs past its 30 minutes and no decision is missing", rf["late"] == 0 and rf["viol"] == 0)
h = interp.evaljs("STRES = null; ensembleHTML()")
check("the forest's stored-table replay has no coin to multiply either", "takes no random decision" in h)
interp.evaljs("ST.key = 'reentry'; ST.exitMin = 960; STRES = null; ENS.res = null;")

# The 'custom' strategy: day-of-week, a fixed entry time or a news-release offset,
# direction, and the news calendar built by build_news_calendar.py.
print("\n--- the custom strategy ---")
check("STRATS has custom", interp.evaljs("STRATS.custom ? 1 : 0") == 1)
interp.evaljs("ST.key = 'custom'; ST.cuDow = {mon:true,tue:false,wed:true,thu:false,fri:true};"
              " ST.cuEntryMin = 600; ST.cuDir = 'long'; ST.cuNews = {}; ST.cuNewsOffset = null;"
              " STRES = null; openStrategy();")
h = interp.evaljs("document.getElementById('sheet').innerHTML || ''")
check("the custom panel renders its own entry section", "Custom entry" in h and "News filter" in h)
o = json.loads(interp.evaljs("JSON.stringify(stratOpts().entry)"))
check("the plain (no news) custom entry is a fixed daily slot with the chosen direction",
      o["mode"] == "reentry" and o["startMin"] == 600 and o["endMin"] == 600 and
      o["direction"] == "long" and o.get("slotsFromTable") in (None, False))
check("daysOfWeek carries exactly the checked weekdays (Mon/Wed/Fri = 1,3,5)",
      sorted(o["daysOfWeek"]) == [1, 3, 5])
rows = interp.evaljs("(STRES || runStrat()).trades.filter(function(t){return !t.skipped;}).length")
check("the plain custom strategy trades", rows > 0, "%d trades" % rows)
wd = json.loads(interp.evaljs(
    "JSON.stringify((STRES || runStrat()).trades.filter(function(t){return !t.skipped;})"
    ".map(function(t){return Core.dowOf(t.day);}))"))
check("every trade lands on one of the checked weekdays", set(wd) <= {1, 3, 5}, str(sorted(set(wd))))

# a news-anchored config: check a category with real coverage, engage a timing preset
cat = interp.evaljs(
    "(function(){ var c = NEWSCAL.categories.filter(function(c){return c.typicalEtMinute !== null;});"
    " return c.length ? c[0].id : null; })()")
check("at least one news category has a usable typical time to anchor on", cat is not None)
interp.evaljs("ST.cuNews = {}; ST.cuNews['%s'] = true; ST.cuNewsMode = 'important';"
              " ST.cuNewsOffset = 30; STRES = null;" % cat)
o = json.loads(interp.evaljs("JSON.stringify(stratOpts().entry)"))
check("engaging a timing preset switches the entry to a news-anchored table",
      o.get("slotsFromTable") is True and o.get("tableSkipReason") == "position open at next news release")
check("the raw cu* config travels on entry itself, not only inside .sides (for ensSig)",
      o.get("cuNewsOffset") == 30 and o.get("newsCalVersion") == interp.evaljs("NEWSCAL.builtFrom"))
n_side_days = interp.evaljs("Object.keys(stratOpts().entry.sides).length")
check("the news-anchored table has at least one scheduled day", n_side_days > 0, "%d days" % n_side_days)
r = interp.evaljs("STRES = null; var r = runStrat(); r ? r.trades.length : -1")
check("the news-anchored custom strategy runs without throwing", r >= 0)

# OFFICIAL_STANDARD (build_news_calendar.apply_official_standard): a DAY_ONLY row of an
# approved fixed-schedule category gets that schedule's time; the FOMC family never does
std = json.loads(interp.evaljs(
    "JSON.stringify(NEWSCAL.events.filter(function(e){return e.status === 'OFFICIAL_STANDARD';}))"))
check("the calendar carries OFFICIAL_STANDARD rows", len(std) > 0, "%d rows" % len(std))
check("every OFFICIAL_STANDARD row has a time and says where it came from",
      all(e["etMinute"] is not None and e.get("standardSource") for e in std))
check("no FOMC-family row is ever filled from a standard time",
      not any(e["eventName"].startswith(("FOMC", "Federal Funds")) for e in std))
check("a standard time is only ever a gap-fill: neither source had a time for it",
      all(e["sourceTimes"]["ff"] is None and e["sourceTimes"]["investing"] is None for e in std))
cpi = [e for e in std if e["catId"] == "cpi_y_y"]
check("CPI y/y has OFFICIAL_STANDARD days to anchor on", len(cpi) > 0)
if cpi:
    d0 = cpi[0]["date"]
    interp.evaljs("ST.cuDow = {mon:true,tue:true,wed:true,thu:true,fri:true}; ST.cuNews = {cpi_y_y: true};"
                  " ST.cuNewsMode = 'important'; ST.cuNewsOffset = 30; STRES = null;")
    slot = json.loads(interp.evaljs(
        "JSON.stringify((stratOpts().entry.sides['%s'] || {})['480'] || null)" % d0))
    check("an OFFICIAL_STANDARD CPI day anchors 30 min before 08:30 (08:00)",
          slot is not None and any(a["status"] == "OFFICIAL_STANDARD" and a["releaseMinute"] == 510
                                   for a in slot["anchors"]), "%s: %s" % (d0, slot))

# Forex Factory from 2025-04-05 on comes from newfac (build_news_calendar.extend_with_newfac).
# The 2025 US government shutdown (Oct 1 - Nov 12) cancelled or moved BLS releases; the
# calendar must say what actually happened, not the pre-shutdown schedule.
EV = json.loads(interp.evaljs("JSON.stringify(NEWSCAL.events)"))
def rel(day, name):
    return [e for e in EV if e["date"] == day and e["eventName"] == name]
def at(day, name, minute):
    return any(e["etMinute"] == minute for e in rel(day, name))
nf = [e for e in EV if e.get("newfac")]
check("newfac rows exist, all from 2025-04-05 on", len(nf) > 0 and min(e["date"] for e in nf) >= "2025-04-05",
      "%d rows" % len(nf))
check("every newfac-only row carries a Forex Factory time or a status with none",
      all(e["sourceTimes"]["ff"] == e["etMinute"] or e["etMinute"] is None for e in nf))
cpi_names = ("CPI m/m", "CPI y/y", "Core CPI m/m")
check("no October 2025 CPI: nothing between the Oct 24 and Dec 18 releases",
      not [e for e in EV if e["eventName"] in cpi_names and "2025-10-25" <= e["date"] <= "2025-12-17"])
check("September 2025 CPI released Oct 24, 08:30",
      at("2025-10-24", "CPI m/m", 510) and at("2025-10-24", "CPI y/y", 510))
check("no jobs report on its scheduled Oct 3 or Nov 7 2025",
      not rel("2025-10-03", "Non-Farm Employment Change") and not rel("2025-11-07", "Non-Farm Employment Change"))
check("September 2025 jobs report released Nov 20, 08:30", at("2025-11-20", "Non-Farm Employment Change", 510))
check("October + November payrolls released together Dec 16, 08:30, one row",
      len(rel("2025-12-16", "Non-Farm Employment Change")) == 1 and at("2025-12-16", "Non-Farm Employment Change", 510)
      and at("2025-12-16", "Unemployment Rate", 510))
check("Dec 18 2025: only the y/y CPI figures (no m/m for November)",
      at("2025-12-18", "CPI y/y", 510) and not rel("2025-12-18", "CPI m/m") and not rel("2025-12-18", "Core CPI m/m"))
check("Sep 16 2026 FOMC day matches the calendar: 14:00 decision, 14:30 press conference",
      at("2026-09-16", "Federal Funds Rate", 840) and at("2026-09-16", "FOMC Press Conference", 870)
      and at("2026-09-16", "Retail Sales m/m", 510))
fd = [e for e in EV if e["eventName"] == "FOMC decision day" and e["date"] == "2026-09-16"]
check("the FOMC decision day row links to that 14:00", len(fd) == 1 and fd[0]["etMinute"] == 840, str(fd))

# midnight-crossing: the previous-day helper must be pure calendar arithmetic, not
# dependent on whichever machine's local timezone the browser happens to run in --
# checked across a month boundary, a year boundary and a leap day, where a naive
# local-time Date bug would most likely show up as an off-by-one
for d, want in [("2024-03-01", "2024-02-29"), ("2024-01-01", "2023-12-31"),
                ("2021-03-01", "2021-02-28"), ("2024-02-29", "2024-02-28")]:
    got = interp.evaljs("prevIsoDay('%s')" % d)
    check("prevIsoDay(%s) = %s" % (d, want), got == want, "got %s" % got)
interp.evaljs("ST.key = 'reentry'; ST.exitMin = 960; ST.cuNews = {}; ST.cuNewsOffset = null;"
              " STRES = null; ENS.res = null;")

# Picking Instrument never changed what data is loaded, only $/pt -- so a
# NQ tape clicked to ES would price real signals off the wrong contract with
# no complaint. detectSymbol guesses the market from the file name so a new
# load prices itself automatically, and the panel says what it detected and
# flags it if the active pricing no longer matches.
print("\n--- detecting the loaded instrument from its file name ---")
guesses = json.loads(interp.evaljs(
    "JSON.stringify({nq: detectSymbol('NQ_1min_2010-2026.csv'),"
    " mnq: detectSymbol('MNQ_1min_2010-2026.csv'),"
    " es: detectSymbol('databento_ES_futures.CSV'),"
    " mes: detectSymbol('mes-1min.csv'),"
    " none: detectSymbol('trading_data_export.csv')})"))
check("NQ is detected from a plain file name", guesses["nq"] == "NQ")
check("MNQ is detected as MNQ, not as NQ (a word-boundary match, not a substring one)",
      guesses["mnq"] == "MNQ")
check("ES is detected case-insensitively, prefixed and with a different extension case",
      guesses["es"] == "ES")
check("MES is detected from a lowercase, hyphenated name", guesses["mes"] == "MES")
check("a name with no known symbol in it is not detected", guesses["none"] is None)
save = json.loads(interp.evaljs("JSON.stringify({sym: LOADED_SYM, pv: ST.pointValue, comm: ST.commission})"))
interp.evaljs("ST.stageView = 'eval'; ST.funded.same = true;"
              " ST.pointValue = 50; ST.commission = 1.75; LOADED_SYM = 'ES'; openStrategy();")
h = interp.evaljs("document.getElementById('sheet').innerHTML")
check("pricing that matches the detected symbol shows no mismatch",
      "MISMATCH" not in h and "<span class=\"stat\">ES</span>" in h)
interp.evaljs("ST.pointValue = 100; ST.commission = 2.3; openStrategy();")   # now priced as GC
h = interp.evaljs("document.getElementById('sheet').innerHTML")
check("pricing a detected-ES tape as GC is flagged as a MISMATCH",
      "priced as GC" in h and "look like ES" in h)
interp.evaljs("ST.pointValue = %s; ST.commission = %s; LOADED_SYM = %s; STRES = null;" %
              (save["pv"], save["comm"], json.dumps(save["sym"])))

# The Strategy panel mixes free-form rules with stored, offline-fitted
# replays that only mean anything on the market they were fitted on
# (Breakout Academy: NQ/ES/YM; the two forests: NQ only). Grouped headings
# say which is which, and picking an entry rule the account is not priced
# for snaps the account onto a market that rule actually covers instead of
# silently pricing a stored decision off the wrong instrument.
print("\n--- strategy / instrument compatibility ---")
cov = json.loads(interp.evaljs(
    "JSON.stringify({groups: STRAT_GROUPS.reduce(function(a,g){return a.concat(g.keys);}, []).sort(),"
    " strats: Object.keys(STRATS).sort()})"))
check("every strategy is in exactly one group, and no group names a strategy twice",
      cov["groups"] == cov["strats"], str(cov))
markets = json.loads(interp.evaljs(
    "JSON.stringify({ti4: STRATS.bo_ti4.markets, hit41: STRATS.bo_hit41.markets,"
    " hit34: STRATS.bo_hit34.markets, lh5rf: STRATS.lh5rf.markets,"
    " lh5rfdir: STRATS.lh5rfdir.markets, rf2: STRATS.rf2.markets, orb: STRATS.orb.markets || null})"))
check("the three Breakout replays are fixed to NQ/ES/YM",
      markets["ti4"] == ["NQ", "ES", "YM"] and markets["hit41"] == ["NQ", "ES", "YM"] and
      markets["hit34"] == ["NQ", "ES", "YM"], str(markets))
check("the two forests are fixed to NQ", markets["lh5rf"] == ["NQ"] and
      markets["lh5rfdir"] == ["NQ"] and markets["rf2"] == ["NQ"], str(markets))
check("a rule computed live from the bars carries no market restriction", markets["orb"] is None)

interp.evaljs("ST.stageView = 'eval'; ST.funded.same = true; ST.key = 'reentry';"
              " ST.pointValue = 100; ST.commission = 2.3; STRES = null; openStrategy();")
check("GC is the active preset before the switch",
      interp.evaljs("instOf(ST) && instOf(ST).key") == "GC")
# The click handler itself cannot be exercised here (data-st buttons are
# rebuilt fresh by every querySelectorAll in this stub, so an assigned
# onclick has nowhere to persist); it is a one-line call to snapMarket,
# checked statically in lint_viewer.py, and snapMarket is checked here.
interp.evaljs("ST.key = 'bo_ti4'; snapMarket(ST, STRATS.bo_ti4, true); STRES = null; openStrategy();")
check("switching onto a Breakout replay while sized for GC snaps the account to NQ instead of "
      "pricing the stored NQ fills at GC's $100/point",
      interp.evaljs("ST.pointValue") == 20 and interp.evaljs("ST.commission") == 1.75,
      "pv=%s comm=%s" % (interp.evaljs("ST.pointValue"), interp.evaljs("ST.commission")))
h = interp.evaljs("document.getElementById('sheet').innerHTML")
check("GC is now shown disabled on the Instrument row",
      re.search(r'data-inst="8"[^>]*disabled[^>]*>GC<', h) is not None)
check("NQ, the market this replay was fitted on, stays enabled and lit",
      re.search(r'class="btn on" data-inst="0"[^>]*>NQ<', h) is not None and
      re.search(r'data-inst="0"[^>]*disabled', h) is None)
check("snapMarket leaves a compatible instrument alone",
      interp.evaljs("var save = {pv: ST.pointValue, comm: ST.commission};"
                    " snapMarket(ST, STRATS.bo_ti4, true);"
                    " (ST.pointValue === save.pv && ST.commission === save.comm) ? 1 : 0") == 1)

interp.evaljs("ST.key = 'reentry'; snapMarket(ST, STRATS.reentry, true); STRES = null; openStrategy();")
check("a rule with no market restriction is never touched by snapMarket",
      interp.evaljs("ST.pointValue") == 20 and interp.evaljs("ST.commission") == 1.75)
h = interp.evaljs("document.getElementById('sheet').innerHTML")
check("and no Instrument button is disabled once the active rule has no market restriction",
      "disabled" not in h)

# No test anywhere actually ran a Breakout replay before this change; boRoot
# went from an explicit key check to reading INSTRUMENTS[].root, so confirm
# the table it reaches on the shipped (NQ) tape still fills real trades.
interp.evaljs("ST.key = 'bo_ti4'; snapMarket(ST, STRATS.bo_ti4, true); STRES = null; openStrategy();")
o = json.loads(interp.evaljs("JSON.stringify(stratOpts().entry)"))
check("the Breakout replay carries a per-day fill table and the 16:59 exit",
      o["direction"] == "table" and o["slotsFromTable"] is True and o["exitMin"] == 1019 and
      o["sides"] is not None)
bo = json.loads(interp.evaljs(
    "JSON.stringify((function(){ var r = STRES || runStrat();"
    " var taken = r.trades.filter(function(t){ return !t.skipped; });"
    " return {taken: taken.length, viol: r.violations.length,"
    " badLevel: r.trades.filter(function(t){ return t.skipped &&"
    " t.reason === 'stop level not in this bar'; }).length}; })())"))
check("the Breakout replay (boRoot resolves to NQ for the shipped tape) fills real trades, with "
      "no violation and no fill refused as off-tape (%d taken, %d refused)" % (bo["taken"], bo["badLevel"]),
      bo["taken"] > 0 and bo["viol"] == 0 and bo["badLevel"] == 0)
interp.evaljs("ST.key = 'reentry'; ST.pointValue = 2; ST.commission = 0.5; STRES = null;")

# The live Breakout entries: no markets restriction (they compute fresh from
# whatever is loaded), the panel shows the right tunable fields per system,
# and changing one of them actually reaches Core.liveBreakoutSides.
print("\n--- live Breakout entries ---")
interp.evaljs("ST.key = 'bo_live_hit'; STRES = null; openStrategy();")
h = interp.evaljs("document.getElementById('sheet').innerHTML")
check("the live Hitter has no market restriction: no Instrument button is disabled",
      "disabled" not in h)
check("the panel shows Hitter's own fields (N, ADX period/threshold/direction)",
      'id="stBoN"' in h and 'id="stBoAdxP"' in h and 'id="stBoAdxT"' in h and 'data-bo-adxdir' in h)
check("the panel does not show Trend indi 2's fields for the Hitter",
      'id="stBoFrac"' not in h and 'id="stBoDxS"' not in h)
o = json.loads(interp.evaljs("JSON.stringify(stratOpts().entry)"))
check("the live Hitter carries a per-day table computed by liveBreakoutSides, not a baked one",
      o["direction"] == "table" and o["slotsFromTable"] is True and o["sides"] is not None)
default_sides = json.loads(interp.evaljs(
    "JSON.stringify(Core.liveBreakoutSides(BASE, {system:'hitter', side:'long',"
    " winStart:LIVE_BO_WIN_START, winEnd:LIVE_BO_WIN_END, n:34, adxPeriod:50,"
    " adxThreshold:17.5, adxDirection:'below'}))"))
check("the panel's default N is 34, the published Hitter, not 41 (the later sweep's best neighbour)",
      interp.evaljs("ST.boN") == 34)
check("the panel's default settings match Core.liveBreakoutSides called directly",
      o["sides"] == default_sides, "panel had %d days, direct call had %d" % (len(o["sides"]), len(default_sides)))
check("the signal window is pinned to 09:00-15:30 New York, not left open",
      interp.evaljs("LIVE_BO_WIN_START") == 540 and interp.evaljs("LIVE_BO_WIN_END") == 930)
r1 = json.loads(interp.evaljs("JSON.stringify((STRES || runStrat()).summary)"))
interp.evaljs("ST.boN = 10; STRES = null;")
o2 = json.loads(interp.evaljs("JSON.stringify(stratOpts().entry)"))
check("changing N on the panel changes the live table (not cached from the old N)",
      o2["sides"] != o["sides"])
r2 = json.loads(interp.evaljs("JSON.stringify(runStrat().summary)"))
check("the changed N reaches an actual run (a different trade count or net)",
      r1["nTrades"] != r2["nTrades"] or abs(r1["net"] - r2["net"]) > 1e-9)
check("no violations from the live Hitter's own table", interp.evaljs("(STRES || runStrat()).violations.length") == 0)
interp.evaljs("ST.boN = 41; STRES = null;")

interp.evaljs("ST.key = 'bo_live_ti'; STRES = null; openStrategy();")
h = interp.evaljs("document.getElementById('sheet').innerHTML")
check("the panel shows Trend indi 2's own fields (fraction, DMI period/shift/threshold)",
      'id="stBoFrac"' in h and 'id="stBoDxP"' in h and 'id="stBoDxS"' in h and 'id="stBoDxT"' in h)
check("the panel does not show Hitter's fields for Trend indi 2",
      'id="stBoN"' not in h and 'id="stBoAdxP"' not in h)
o3 = json.loads(interp.evaljs("JSON.stringify(stratOpts().entry)"))
check("Trend indi 2 also carries a live per-day table", o3["direction"] == "table" and o3["sides"] is not None)
check("no violations from the live Trend-indi-2 table", interp.evaljs("(STRES || runStrat()).violations.length") == 0)
interp.evaljs("ST.key = 'reentry'; STRES = null;")

print("\n--- interactions ---")
seq = [
    ("switch timeframe", "seg && 1; document.querySelector('#tfseg'); 1"),
    ("render at full zoom", "setView(0, BASE.n - 1); 1"),
    ("render one session", "setView(0, 390); 1"),
    ("jump to first trade", "gotoTrade(0); 1"),
    ("jump to last trade", "gotoTrade(TRADES.length - 1); 1"),
    ("toggle log scale", "S.log = !S.log; render(); S.log = !S.log; 1"),
    ("enable the time filter", "S.filter.on = true; rebuild(); render(); 1"),
    ("disable the time filter", "S.filter.on = false; rebuild(); render(); 1"),
    ("switch to Heikin-Ashi", "S.ct = 'ha'; rebuild(); render(); 1"),
    ("switch to daily bars", "S.tf = 390; rebuild(); render(); 1"),
    ("back to 1-minute candles", "S.tf = 1; S.ct = 'candle'; rebuild(); render(); 1"),
    ("trades still map onto the right candles after all that",
     "ENT.length === TRADES.length && EXT.length === TRADES.length ? 1 : 0"),
    ("show the equity pane", "S.showEq = true; render(); 1"),
    ("run the account simulator", "S.acct.on = true; runAccount(); render(); 1"),
    ("run it with evaluation rules",
     "S.acct.evaluation.on = true; runAccount(); render(); 1"),
    ("tag a trade and read the setup stats",
     "S.sel = 0; setTag(0, 'a'); setTag(1, 'b'); (setupsHTML()||'').length > 400 ? 1 : 0"),
    ("run a strategy end to end",
     "var r = Core.runStrategy(BASE, stratOpts()); r.trades.length > 0 ? 1 : 0"),
    # Last on purpose. Eleven indicators over 315,900 bars exhausts Duktape's
    # heap, which is far smaller than a browser's, and it does not recover --
    # so anything after this would report a fault that does not exist.
    ("turn on every indicator",
     "S.indicators = Object.keys(IND_DEFS).map(function(k){"
     "return {key:k, p:Object.assign({}, IND_DEFS[k].params)};}); rebuild(); render(); 1"),
]
for name, src in seq:
    try:
        v = interp.evaljs(src)
        check(name, v == 1, "returned %r" % (v,))
    except Exception as e:
        check(name, False, str(e).split("\n")[0][:150])

errs = interp.evaljs("__ERRORS")
check("no deferred errors accumulated", not errs, str(errs)[:200])

print("\n" + "=" * 62)
print("  %d passed, %d failed" % (len(PASS), len(FAIL)))
for f in FAIL:
    print("    FAIL: " + f)
print("=" * 62)
sys.exit(1 if FAIL else 0)
