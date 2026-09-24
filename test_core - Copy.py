"""
Headless tests for the chart core, run against the REAL NQ data.

The point is to catch the class of bug that a dashboard hides: aggregation that
silently drops a bar, an index map that drifts by one, a statistic that looks
plausible but is wrong. Every assertion here is checked against an independent
brute-force computation in Python, not against the JavaScript's own opinion.
"""
import io, json, base64, datetime
import numpy as np
import dukpy

CORE = io.open(r"C:\Users\ruben\nq-backtest\viewer_core.js", encoding="utf-8").read()
D = json.load(io.open(r"C:\Users\ruben\nq-backtest\continuous.json"))
TICK = D["tick"]

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name + (("   " + detail) if detail and not cond else ""))


def unpack(b64):
    return np.frombuffer(base64.b64decode(b64), dtype="<i2").astype(float)


# ---- reconstruct bars exactly as the browser does ----
dO, dH, dL, dC = (unpack(D["bars"][k]) for k in "ohlc")
O = np.cumsum(dO) * TICK + D["bars"]["base"]
H = O + dH * TICK
L = O + dL * TICK
C = O + dC * TICK
MINS = unpack(D["mins"]).astype(int)
SESS = D["sessions"]
N = D["n"]
print(f"loaded {N:,} bars, {len(SESS)} sessions, {len(D['trades']):,} trades\n")

js = dukpy.JSInterpreter()
js.evaljs(CORE)
# hand the engine a plain-array bar set (Duktape has no typed arrays from Python)
js.evaljs("var B = {n:%d, o:%s, h:%s, l:%s, c:%s, mins:%s, sessions:%s};" % (
    N, json.dumps([round(x, 4) for x in O]), json.dumps([round(x, 4) for x in H]),
    json.dumps([round(x, 4) for x in L]), json.dumps([round(x, 4) for x in C]),
    json.dumps(MINS.tolist()), json.dumps(SESS)))

print("--- decode ---")
check("bar count matches header", N == len(O))
check("high >= low on every bar", bool(np.all(H >= L - 1e-9)))
check("high >= open and close", bool(np.all((H >= O - 1e-9) & (H >= C - 1e-9))))
check("low <= open and close", bool(np.all((L <= O + 1e-9) & (L <= C + 1e-9))))
check("prices are positive", bool(np.all(O > 0)))
check("sessions tile the series exactly",
      SESS[0]["a"] == 0 and SESS[-1]["b"] == N - 1 and
      all(SESS[i + 1]["a"] == SESS[i]["b"] + 1 for i in range(len(SESS) - 1)))
check("minutes ascend within each session",
      all(bool(np.all(np.diff(MINS[s["a"]:s["b"] + 1]) > 0)) for s in SESS))

print("\n--- aggregation ---")
for tf in (1, 2, 5, 15, 30, 60, 390):
    # map/src are Int32Array at 1m (built once and shared), so flatten them
    # here rather than have the assertions care which container they arrive in
    agg = js.evaljs(f"var A = Core.aggregate(B, {tf}); "
                    "({n:A.n, o:A.o, h:A.h, l:A.l, c:A.c, "
                    " map:Array.prototype.slice.call(A.map),"
                    " src:Array.prototype.slice.call(A.src),"
                    " sessions:A.sessions})")
    ao, ah, al, ac = (np.array(agg[k], dtype=float) for k in "ohlc")
    src = np.array(agg["src"], dtype=int)
    mp = np.array(agg["map"], dtype=int)
    # independent brute force
    eo, eh, el, ec, esrc = [], [], [], [], []
    for s in SESS:
        i = s["a"]
        while i <= s["b"]:
            e = min(s["b"], i + tf - 1)
            eo.append(O[i]); eh.append(H[i:e + 1].max())
            el.append(L[i:e + 1].min()); ec.append(C[e]); esrc.append(i)
            i += tf
    ok = (len(eo) == agg["n"] and
          np.allclose(ao, eo, atol=1e-6) and np.allclose(ah, eh, atol=1e-6) and
          np.allclose(al, el, atol=1e-6) and np.allclose(ac, ec, atol=1e-6) and
          np.array_equal(src, esrc))
    check(f"tf={tf:>3}: OHLC matches brute force ({agg['n']:,} bars)", ok)
    check(f"tf={tf:>3}: map is non-decreasing", bool(np.all(np.diff(mp) >= 0)))
    check(f"tf={tf:>3}: map lands each base bar inside its own candle",
          bool(np.all(src[mp] <= np.arange(N))) and
          bool(np.all(np.arange(N) < src[mp] + tf)))
    # no aggregated candle may straddle two sessions
    sess_of_base = np.zeros(N, dtype=int)
    for k, s in enumerate(SESS):
        sess_of_base[s["a"]:s["b"] + 1] = k
    straddle = False
    for k in range(agg["n"]):
        members = np.where(mp == k)[0]
        if len(members) and sess_of_base[members].min() != sess_of_base[members].max():
            straddle = True; break
    check(f"tf={tf:>3}: no candle straddles a session boundary", not straddle)
    check(f"tf={tf:>3}: aggregate range equals base range",
          abs(ah.max() - H.max()) < 1e-6 and abs(al.min() - L.min()) < 1e-6)

print("\n--- Heikin-Ashi ---")
ha = js.evaljs("var HA = Core.heikinAshi(Core.aggregate(B,5)); "
               "({o:HA.o.slice(0,400), h:HA.h.slice(0,400), l:HA.l.slice(0,400), c:HA.c.slice(0,400)})")
a5 = js.evaljs("var A5 = Core.aggregate(B,5); ({o:A5.o.slice(0,400),h:A5.h.slice(0,400),"
               "l:A5.l.slice(0,400),c:A5.c.slice(0,400)})")
ho, hh, hl, hc = (np.array(ha[k], dtype=float) for k in "ohlc")
bo, bh, bl, bc = (np.array(a5[k], dtype=float) for k in "ohlc")
check("haC = (o+h+l+c)/4", np.allclose(hc, (bo + bh + bl + bc) / 4, atol=1e-9))
check("haO seeds at (o+c)/2", abs(ho[0] - (bo[0] + bc[0]) / 2) < 1e-9)
check("haO[i] = (haO[i-1]+haC[i-1])/2", np.allclose(ho[1:], (ho[:-1] + hc[:-1]) / 2, atol=1e-9))
check("haH is the max of its inputs", np.allclose(hh, np.maximum.reduce([bh, ho, hc]), atol=1e-9))
check("haL is the min of its inputs", np.allclose(hl, np.minimum.reduce([bl, ho, hc]), atol=1e-9))

print("\n--- indicators ---")
src = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
r = js.evaljs("Core.sma(%s, 3)" % json.dumps(src))
check("SMA(3) warm-up is null", r[0] is None and r[1] is None)
check("SMA(3) values correct", all(abs(r[i] - (src[i] + src[i - 1] + src[i - 2]) / 3) < 1e-9
                                   for i in range(2, 10)))
r = js.evaljs("Core.ema(%s, 3)" % json.dumps(src))
check("EMA(3) seeds with the SMA", abs(r[2] - 2.0) < 1e-9)
check("EMA(3) recursion correct", abs(r[3] - (4 * 0.5 + 2.0 * 0.5)) < 1e-9)
bb = js.evaljs("Core.bollinger(%s, 5, 2)" % json.dumps(src))
check("Bollinger mid equals SMA", abs(bb["mid"][4] - 3.0) < 1e-9)
check("Bollinger bands straddle the mid",
      bb["up"][4] > bb["mid"][4] > bb["dn"][4])
check("Bollinger width uses population sd",
      abs((bb["up"][4] - bb["mid"][4]) - 2 * np.std([1, 2, 3, 4, 5])) < 1e-9)
vw = js.evaljs("var V = Core.vwapSession(Core.aggregate(B,1)); "
               "[V[0], V[%d], V[%d]]" % (SESS[0]["b"], SESS[1]["a"]))
tp0 = (H[0] + L[0] + C[0]) / 3
check("VWAP starts at the first typical price", abs(vw[0] - tp0) < 1e-6)
s1a = SESS[1]["a"]
check("VWAP re-anchors on each session",
      abs(vw[2] - (H[s1a] + L[s1a] + C[s1a]) / 3) < 1e-6)

print("\n--- Wilder DX/ADX ---")
# Independent brute-force Wilder's DX/ADX (RMA-smoothed DM/TR give DI+/DI-,
# DX = 100|DI+-DI-|/(DI++DI-), ADX = RMA of DX -- TradeStation's DMI
# function), written fresh rather than imported from bo_data.py, and run on
# a slice of the real tape so the Breakout systems' live entries below trust
# the same trend-strength reading the offline study was fitted against.
def py_wilder_dx_adx(h, l, c, period):
    n = len(c)
    dx, adx = [None] * n, [None] * n
    if n < period:
        return dx, adx
    pdm, mdm, tr = [0.0] * n, [0.0] * n, [0.0] * n
    for i in range(n):
        up = 0.0 if i == 0 else h[i] - h[i - 1]
        dn = 0.0 if i == 0 else l[i - 1] - l[i]
        pdm[i] = up if (up > dn and up > 0) else 0.0
        mdm[i] = dn if (dn > up and dn > 0) else 0.0
        pc = c[0] if i == 0 else c[i - 1]
        tr[i] = max(h[i] - l[i], abs(h[i] - pc), abs(l[i] - pc))

    def rma(x):
        out = [None] * n
        out[period - 1] = sum(x[:period]) / period
        a = 1.0 / period
        for i in range(period, n):
            out[i] = out[i - 1] + a * (x[i] - out[i - 1])
        return out
    atrR, spdm, smdm = rma(tr), rma(pdm), rma(mdm)
    for i in range(n):
        if atrR[i] is None:
            continue
        pdi = 100 * spdm[i] / atrR[i] if atrR[i] != 0 else float("inf")
        mdi = 100 * smdm[i] / atrR[i] if atrR[i] != 0 else float("inf")
        denom = pdi + mdi
        dx[i] = 100 * abs(pdi - mdi) / denom if denom not in (0, float("inf")) else 0.0
    for i in range(period):
        dx[i] = None
    start = 2 * period - 1
    if n > start:
        adx[start] = sum(dx[period:start + 1]) / period
        a2 = 1.0 / period
        for i in range(start + 1, n):
            adx[i] = adx[i - 1] + a2 * (dx[i] - adx[i - 1])
    return dx, adx


WSLICE = 2500   # >> 2*period-1 for every period tested, so every one warms up
wh, wl, wc = H[:WSLICE].tolist(), L[:WSLICE].tolist(), C[:WSLICE].tolist()
for period in (14, 50, 100):
    py_dx, py_adx = py_wilder_dx_adx(wh, wl, wc, period)
    r = js.evaljs("Core.wilderDxAdx(%s, %s, %s, %d)" % (json.dumps(wh), json.dumps(wl), json.dumps(wc), period))
    js_dx, js_adx = r["dx"], r["adx"]
    check("DX(%d): warm-up nulls land on the same bars" % period,
          [x is None for x in js_dx] == [x is None for x in py_dx])
    check("ADX(%d): warm-up nulls land on the same bars" % period,
          [x is None for x in js_adx] == [x is None for x in py_adx])
    dx_diff = max((abs(a - b) for a, b in zip(js_dx, py_dx) if a is not None), default=0)
    adx_diff = max((abs(a - b) for a, b in zip(js_adx, py_adx) if a is not None), default=0)
    check("DX(%d) matches the independent Python RMA to 1e-6 (max diff %.2e)" % (period, dx_diff),
          dx_diff < 1e-6)
    check("ADX(%d) matches the independent Python RMA to 1e-6 (max diff %.2e)" % (period, adx_diff),
          adx_diff < 1e-6)
check("ADX/DX stay within their defined 0-100 range",
      all(0 <= x <= 100 for x in js_dx if x is not None) and
      all(0 <= x <= 100 for x in js_adx if x is not None))

print("\n--- volume and VWAP ---")
VOL = unpack(D["bars"]["v"]) if "v" in D["bars"] else None
check("volume is present in the export", VOL is not None and len(VOL) == N)
if VOL is not None:
    check("all volumes are positive", bool(np.all(VOL > 0)))
    js.evaljs("B.v = %s;" % json.dumps([float(x) for x in VOL]))
    for tf in (5, 60):
        got = js.evaljs(f"var AV = Core.aggregate(B, {tf});"
                        "({n:AV.n, v0:AV.v[0], v1:AV.v[1], tot:(function(){"
                        "var s=0; for(var i=0;i<AV.v.length;i++) s+=AV.v[i]; return s;})()})")
        check(f"tf={tf}: volume SUMS within the candle",
              abs(got["v0"] - VOL[:tf].sum()) < 1e-6)
        check(f"tf={tf}: total volume is preserved by aggregation",
              abs(got["tot"] - VOL.sum()) < 1e-3,
              f"{got['tot']} vs {VOL.sum()}")
    # VWAP must now be genuinely volume-weighted
    s0a, s0b = SESS[0]["a"], SESS[0]["b"]
    vw = js.evaljs("var A1v = Core.aggregate(B,1); var VW = Core.vwapSession(A1v); "
                   "[VW[%d], VW.weighted]" % s0b)
    tp = (H[s0a:s0b+1] + L[s0a:s0b+1] + C[s0a:s0b+1]) / 3
    w = VOL[s0a:s0b+1]
    check("VWAP reports itself as volume-weighted", vw[1] is True)
    check("VWAP equals sum(typical x volume)/sum(volume)",
          abs(vw[0] - (tp * w).sum() / w.sum()) < 1e-6,
          f"got {vw[0]}, expected {(tp*w).sum()/w.sum()}")
    check("weighted VWAP differs from the unweighted average",
          abs((tp * w).sum() / w.sum() - tp.mean()) > 1e-6)
    nov = js.evaljs("var NB = {n:3, o:[1,2,3], h:[2,3,4], l:[0,1,2], c:[1,2,3],"
                    " sessions:[{day:'d',a:0,b:2}]};"
                    "var NV = Core.vwapSession(NB); [NV[2], NV.weighted]")
    check("without volume VWAP falls back and admits it", nov[1] is False)
    va = js.evaljs("Core.volumeAvg(Core.aggregate(B,60), 3) !== null ? 1 : 0")
    check("volumeAvg returns a series when volume exists", va == 1)
    check("volumeAvg returns null when it does not",
          js.evaljs("Core.volumeAvg({n:3,v:null}, 3) === null ? 1 : 0") == 1)
    # release the volume array and its aggregations; Duktape's heap is small and
    # the remaining sections need the room
    js.evaljs("B.v = undefined; AV = null; A1v = null;")

print("\n--- oscillators ---")
# RSI against an independent Wilder implementation
px = [44.34,44.09,44.15,43.61,44.33,44.83,45.10,45.42,45.84,46.08,
      45.89,46.03,45.61,46.28,46.28,46.00,46.03,46.41,46.22,45.64]
def wilder_rsi(s, p=14):
    g = l = 0.0
    for i in range(1, p + 1):
        d = s[i] - s[i-1]
        g += max(d, 0.0); l += max(-d, 0.0)
    g /= p; l /= p
    out = [None]*len(s)
    out[p] = 100.0 if l == 0 else 100 - 100/(1 + g/l)
    for i in range(p+1, len(s)):
        d = s[i] - s[i-1]
        g = (g*(p-1) + max(d, 0.0))/p
        l = (l*(p-1) + max(-d, 0.0))/p
        out[i] = 100.0 if l == 0 else 100 - 100/(1 + g/l)
    return out
r = js.evaljs("Core.rsi(%s, 14)" % json.dumps(px))
exp = wilder_rsi(px)
check("RSI matches an independent Wilder implementation",
      all(a is None and b is None or abs(a-b) < 1e-9 for a, b in zip(r, exp)))
check("RSI warm-up is null before the period", all(x is None for x in r[:14]))
check("RSI stays inside 0..100",
      all(0 <= x <= 100 for x in r if x is not None))
up = js.evaljs("Core.rsi(%s, 14)" % json.dumps([float(i) for i in range(40)]))
check("RSI of a monotonic rise is 100", abs(up[-1] - 100) < 1e-9)
dn = js.evaljs("Core.rsi(%s, 14)" % json.dumps([float(40-i) for i in range(40)]))
check("RSI of a monotonic fall is 0", abs(dn[-1]) < 1e-9)

mc = js.evaljs("Core.macd(%s, 12, 26, 9)" % json.dumps([float(i % 17) + i*0.3 for i in range(120)]))
ef = js.evaljs("Core.ema(%s, 12)" % json.dumps([float(i % 17) + i*0.3 for i in range(120)]))
es = js.evaljs("Core.ema(%s, 26)" % json.dumps([float(i % 17) + i*0.3 for i in range(120)]))
check("MACD line equals fastEMA minus slowEMA",
      all(abs(mc["macd"][i] - (ef[i] - es[i])) < 1e-9
          for i in range(len(ef)) if mc["macd"][i] is not None))
check("MACD line is null until the slow EMA exists",
      all(mc["macd"][i] is None for i in range(25)))
check("MACD histogram equals line minus signal",
      all(abs(mc["hist"][i] - (mc["macd"][i] - mc["signal"][i])) < 1e-9
          for i in range(len(mc["hist"])) if mc["hist"][i] is not None))
check("MACD signal is not poisoned by the leading nulls",
      mc["signal"][-1] is not None and abs(mc["signal"][-1]) < 1e6)

js.evaljs("var SB = {n:6, o:[1,2,3,4,5,6], h:[10,12,11,13,14,15],"
          " l:[0,1,2,3,4,5], c:[5,11,4,13,9,15]};")
st = js.evaljs("Core.stochastic(SB, 3, 2, 1)")
check("Stochastic %K is 100 when the close is the period high",
      abs(st["k"][3] - 100) < 1e-9)
check("Stochastic warm-up is null", st["k"][0] is None and st["k"][1] is None)
check("Stochastic stays inside 0..100",
      all(0 <= x <= 100 for x in st["k"] if x is not None))
check("Stochastic %D is an average of %K",
      st["d"][4] is not None and abs(st["d"][4] - (st["k"][3] + st["k"][4]) / 2) < 1e-9)
sn = js.evaljs("Core.smaNull([null,null,2,4,6], 2)")
check("smaNull refuses to average across a null", sn[2] is None)
check("smaNull averages once the window is clean", abs(sn[3] - 3) < 1e-9)

dc = js.evaljs("Core.donchian(SB, 3)")
check("Donchian upper is the rolling high", abs(dc["up"][2] - 12) < 1e-9)
check("Donchian lower is the rolling low", abs(dc["dn"][2] - 0) < 1e-9)
check("Donchian mid is the midpoint", abs(dc["mid"][2] - 6) < 1e-9)
kc = js.evaljs("Core.keltner(SB, 3, 2)")
check("Keltner bands straddle the mid where defined",
      all(kc["up"][i] > kc["mid"][i] > kc["dn"][i]
          for i in range(6) if kc["mid"][i] is not None))
rc = js.evaljs("Core.roc([100,110,121], 1)")
check("ROC reports percent change", abs(rc[1] - 10) < 1e-9 and abs(rc[2] - 10) < 1e-9)
check("ROC warm-up is null", rc[0] is None)

print("\n--- search + windows ---")
arr = [0, 2, 4, 6, 8, 10]
ok = all(js.evaljs("Core.lowerBound(%s,%d)" % (json.dumps(arr), v)) ==
         int(np.searchsorted(arr, v, "left")) for v in range(-1, 12))
check("lowerBound matches searchsorted over every case", ok)
so = js.evaljs("[Core.sessionOf(B.sessions,0), Core.sessionOf(B.sessions,%d), "
               "Core.sessionOf(B.sessions,%d)]" % (SESS[3]["a"], SESS[-1]["b"]))
check("sessionOf resolves first, middle and last bar",
      so == [0, 3, len(SESS) - 1])
pr = js.evaljs("Core.priceRange(Core.aggregate(B,1), 100, 500, 0)")
check("priceRange matches brute force",
      abs(pr["lo"] - L[100:501].min()) < 1e-6 and abs(pr["hi"] - H[100:501].max()) < 1e-6)

print("\n--- trades ---")
TRD = D["trades"]
ent = [t["entry_bar"] for t in TRD]
maxspan = max(t["exit_bar"] - t["entry_bar"] for t in TRD)
check("trades are sorted by entry bar", ent == sorted(ent))
check("every exit is at or after its entry", all(t["exit_bar"] >= t["entry_bar"] for t in TRD))
check("every trade index is inside the series",
      all(0 <= t["entry_bar"] < N and 0 <= t["exit_bar"] < N for t in TRD))
check("no two trades overlap in time",
      all(TRD[i + 1]["entry_bar"] > TRD[i]["exit_bar"] for i in range(len(TRD) - 1)))
exits = [t["exit_bar"] for t in TRD]
js.evaljs("var TR = %s; var ENT = %s; var EXT = %s;" % (
    json.dumps([{"pnl": t["pnl"]} for t in TRD]), json.dumps(ent), json.dumps(exits)))
bad = 0
for (a, b) in [(0, 400), (5000, 5400), (100000, 100900), (0, N - 1), (N - 200, N - 1)]:
    got = js.evaljs("Core.visibleTrades(ENT, EXT, %d, %d, %d)" % (a, b, maxspan))
    exp = [i for i, t in enumerate(TRD) if t["exit_bar"] >= a and t["entry_bar"] <= b]
    if got != exp:
        bad += 1
check("visibleTrades matches brute force on 5 windows", bad == 0, f"{bad} mismatched")

# the bug this signature change fixes: at 1-hour the aggregated view indices are
# ~60x smaller than the base indices. Passing base indices made the scan break on
# its first iteration and almost every trade disappeared from the chart.
ent60 = [e // 60 for e in ent]
ext60 = [e // 60 for e in exits]
js.evaljs("var E60 = %s; var X60 = %s;" % (json.dumps(ent60), json.dumps(ext60)))
mis = 0
for (a, b) in [(0, 66), (100, 400), (0, max(ent60)), (max(ent60) - 50, max(ent60))]:
    got = js.evaljs("Core.visibleTrades(E60, X60, %d, %d, 2)" % (a, b))
    exp = [i for i in range(len(ent60)) if ext60[i] >= a and ent60[i] <= b]
    if got != exp:
        mis += 1
check("visibleTrades is correct in AGGREGATED index space", mis == 0, f"{mis} windows wrong")
check("a filtered-out trade (entry -1) is skipped, not drawn",
      js.evaljs("Core.visibleTrades([-1, 5, -1, 9], [-1, 6, -1, 10], 0, 20, 2)") == [1, 3])

print("\n--- time filter and session marks ---")
js.evaljs("var A1t = Core.aggregate(B, 1);")
FROM, TO = 9 * 60 + 30, 10 * 60 + 30
tf_ = js.evaljs("var TFI = Core.timeFilter(A1t, %d, %d);"
                "({n:TFI.n, sess:TFI.sessions.length, m0:TFI.mins[0],"
                " mlast:TFI.mins[TFI.n-1]})" % (FROM, TO))
keep = int(((MINS >= FROM) & (MINS <= TO)).sum())
check("timeFilter keeps exactly the bars inside the window", tf_["n"] == keep,
      f"{tf_['n']} vs {keep}")
check("filtered bars all sit inside the window",
      js.evaljs("var ok=1; for(var i=0;i<TFI.n;i++) if(TFI.mins[i]<%d||TFI.mins[i]>%d) ok=0; ok"
                % (FROM, TO)) == 1)
check("filtered series still has one session per day",
      tf_["sess"] == len(SESS), f"{tf_['sess']} vs {len(SESS)}")
check("fwd/back are inverse where the bar survived",
      js.evaljs("var bad=0; for(var j=0;j<TFI.n;j++) if(TFI.fwd[TFI.back[j]]!==j) bad++; bad") == 0)
check("dropped bars map to -1",
      js.evaljs("var bad=0; for(var i=0;i<A1t.n;i++){"
                "  var inw = A1t.mins[i]>=%d && A1t.mins[i]<=%d;"
                "  if(!inw && TFI.fwd[i]!==-1) bad++;"
                "} bad" % (FROM, TO)) == 0)
check("filtered sessions tile the filtered series",
      js.evaljs("var s=TFI.sessions; var ok = s[0].a===0 && s[s.length-1].b===TFI.n-1;"
                "for(var k=0;k+1<s.length;k++) if(s[k+1].a!==s[k].b+1) ok=0; ok?1:0") == 1)
check("a window matching nothing yields an empty series",
      js.evaljs("Core.timeFilter(A1t, 3, 4).n") == 0)
check("filtering then aggregating still respects sessions",
      js.evaljs("var AF = Core.aggregate(TFI, 5); AF.sessions.length") == len(SESS))

mk = js.evaljs("Core.timeMarks(A1t, %d, 0, 5000)" % (9 * 60 + 30))
check("timeMarks finds one mark per session in range", len(mk) == len(set(mk)))
check("every mark is at or after the requested minute",
      js.evaljs("var ok=1; var m=Core.timeMarks(A1t,%d,0,5000);"
                "for(var i=0;i<m.length;i++) if(A1t.mins[m[i]]<%d) ok=0; ok"
                % (10 * 60, 10 * 60)) == 1)
check("timeMarks returns nothing for a minute past the close",
      js.evaljs("Core.timeMarks(A1t, 1400, 0, 5000).length") == 0)
js.evaljs("TFI = null; A1t = null;")

st = js.evaljs("Core.tradeStats(TR)")
pn = np.array([t["pnl"] for t in TRD])
cum = np.cumsum(pn)
dd = float(np.max(np.maximum.accumulate(cum) - cum))
check("stats: trade count", st["n"] == len(TRD))
check("stats: win count", st["wins"] == int((pn > 0).sum()))
check("stats: net P&L", abs(st["net"] - pn.sum()) < 1e-6)
check("stats: win rate", abs(st["winRate"] - (pn > 0).mean()) < 1e-9)
check("stats: profit factor", abs(st["profitFactor"] -
      pn[pn > 0].sum() / -pn[pn < 0].sum()) < 1e-9)
check("stats: expectancy", abs(st["expectancy"] - pn.mean()) < 1e-9)
check("stats: max drawdown matches brute force", abs(st["maxDrawdown"] - dd) < 1e-6)
check("stats: equity curve ends at net", abs(st["equity"][-1] - pn.sum()) < 1e-6)

print("\n--- candle styles ---")
# a deliberately constructed series: up bar, down bar, up bar that closed
# below the previous close, down bar that closed above the previous close
js.evaljs("var CB = {n:4, o:[10,20,14,11], h:[21,21,16,13], l:[9,13,13,10], c:[20,14,15,12]};")
cs = js.evaljs("[Core.candleStyle(CB,0,'candle'),Core.candleStyle(CB,1,'candle'),"
               " Core.candleStyle(CB,2,'candle'),Core.candleStyle(CB,3,'candle')]")
hs = js.evaljs("[Core.candleStyle(CB,0,'hollow'),Core.candleStyle(CB,1,'hollow'),"
               " Core.candleStyle(CB,2,'hollow'),Core.candleStyle(CB,3,'hollow')]")
check("candle: never hollow", all(not x["hollow"] for x in cs))
check("candle: colour from close vs open", [x["up"] for x in cs] == [True, False, True, True])
check("hollow: body hollow when close >= open", [x["hollow"] for x in hs] == [True, False, True, True])
check("hollow: colour from close vs PREVIOUS close",
      [x["up"] for x in hs] == [True, False, True, False])
check("candle and hollow genuinely differ",
      any(cs[i] != hs[i] for i in range(4)),
      "the two styles produced identical output")
check("hollow bar 3 is the discriminating case: up body, down colour",
      hs[2]["hollow"] is True and hs[2]["up"] is True and
      hs[3]["hollow"] is True and hs[3]["up"] is False)
real = js.evaljs("var A1x = Core.aggregate(B,1); var d=0;"
                 "for (var i=0;i<5000;i++){var a=Core.candleStyle(A1x,i,'candle'),"
                 "b=Core.candleStyle(A1x,i,'hollow'); if(a.up!==b.up||a.hollow!==b.hollow) d++;}"
                 "d")
check("styles differ on real data too", real > 0, f"identical on all 5000 bars")

print("\n--- edge cases ---")
js.evaljs("var TINY = {n:1, o:[5], h:[5], l:[5], c:[5], mins:[570], "
          "sessions:[{day:'2020-01-01',a:0,b:0}]};")
pr = js.evaljs("Core.priceRange(TINY,0,0,0.06)")
check("flat single-bar window still yields a usable range", pr["hi"] > pr["lo"])
a1 = js.evaljs("var Z = Core.aggregate(TINY, 60); ({n:Z.n, o:Z.o, map:Z.map})")
check("aggregating a 1-bar session gives exactly 1 candle", a1["n"] == 1)
check("aggregating beyond session length does not overrun", a1["map"][0] == 0)
big = js.evaljs("var Zb = Core.aggregate(B, 100000); Zb.n")
check("timeframe larger than any session gives one candle per session",
      big == len(SESS), f"got {big}, expected {len(SESS)}")
vt = js.evaljs("Core.visibleTrades(ENT, EXT, -500, -1, %d)" % maxspan)
check("visibleTrades on a window before the data is empty", vt == [])
vt2 = js.evaljs("Core.visibleTrades([], [], 0, 100, 1)")
check("visibleTrades with no trades returns empty", vt2 == [])
st0 = js.evaljs("Core.tradeStats([])")
check("tradeStats on an empty list does not divide by zero", st0["n"] == 0)
allwin = js.evaljs("Core.tradeStats([{pnl:5},{pnl:3}])")
# Infinity is not representable in JSON, so it crosses the bridge as None.
# That is the transport, not the value: the UI guards with isFinite().
check("profit factor is Infinity when there are no losses",
      allwin["profitFactor"] is None or allwin["profitFactor"] == float("inf"))
check("max drawdown is zero on a monotonically rising curve", allwin["maxDrawdown"] == 0)
alllose = js.evaljs("Core.tradeStats([{pnl:-5},{pnl:-3}])")
check("all-losing set reports the full drawdown", abs(alllose["maxDrawdown"] - 8) < 1e-9)
check("all-losing set has zero profit factor", alllose["profitFactor"] == 0)
sm = js.evaljs("Core.sma([1,2],5)")
check("SMA longer than the series is all null", sm == [None, None])
em = js.evaljs("Core.ema([1,2],5)")
check("EMA longer than the series is all null", em == [None, None])

print("\n--- price scale: linear and log must invert exactly ---")
for log in (0, 1):
    rt = js.evaljs(f"var SC = Core.makeScale(14000, 16000, 12, 400, {log});"
                   "var worst = 0;"
                   "for (var v = 14000; v <= 16000; v += 7){"
                   "  var back = SC.vAt(SC.Y(v));"
                   "  var e = Math.abs(back - v); if (e > worst) worst = e; } worst")
    check(f"{'log' if log else 'linear'}: vAt(Y(v)) returns v", rt < 1e-6, f"worst error {rt}")
    mono = js.evaljs(f"var SC2 = Core.makeScale(14000, 16000, 12, 400, {log});"
                     "SC2.Y(14000) > SC2.Y(16000) ? 1 : 0")
    check(f"{'log' if log else 'linear'}: higher price maps to smaller y", mono == 1)
edge = js.evaljs("var SC3 = Core.makeScale(100, 100, 0, 300, 1); "
                 "isFinite(SC3.Y(100)) && isFinite(SC3.vAt(150)) ? 1 : 0")
check("log scale survives a zero-width range", edge == 1)
neg = js.evaljs("var SC4 = Core.makeScale(1e-9, 10, 0, 300, 1); isFinite(SC4.Y(0)) ? 1 : 0")
check("log scale does not produce NaN at zero", neg == 1)

print("\n--- measure tool ---")
m = js.evaljs("Core.measure(15000, 15150, 100, 160)")
check("measure: points", abs(m["pts"] - 150) < 1e-9)
check("measure: percent uses real prices", abs(m["pct"] - 1.0) < 1e-9)
check("measure: bar count", m["bars"] == 60)
m2 = js.evaljs("Core.measure(15150, 15000, 160, 100)")
check("measure: reversed drag gives a negative move", m2["pts"] < 0 and m2["pct"] < 0)
check("measure: bar count is always positive", m2["bars"] == 60)
# the log-scale trap: percent must not be computed on log values
mlog = js.evaljs("var SL = Core.makeScale(10000, 20000, 0, 400, 1);"
                 "var v0 = SL.vAt(SL.Y(15000)), v1 = SL.vAt(SL.Y(15150));"
                 "Core.measure(v0, v1, 0, 1)")
check("measure through a log scale still reports 1.00%", abs(mlog["pct"] - 1.0) < 1e-6,
      f"got {mlog['pct']}")

print("\n--- session grouping for imported files ---")
intraday = ["2023-01-03"] * 390 + ["2023-01-04"] * 390
ss = js.evaljs("Core.buildSessions(%s)" % json.dumps(intraday))
check("intraday file splits into one session per date", len(ss) == 2)
check("intraday sessions cover every bar", ss[0]["a"] == 0 and ss[1]["b"] == 779)
daily = [f"2023-{m:02d}-{d:02d}" for m in range(1, 13) for d in range(1, 21)]
sd = js.evaljs("Core.buildSessions(%s)" % json.dumps(daily))
check("daily file becomes ONE session, not one per bar", len(sd) == 1,
      f"got {len(sd)} sessions for {len(daily)} daily bars")
check("the single session spans the whole series",
      sd[0]["a"] == 0 and sd[0]["b"] == len(daily) - 1)
# and therefore aggregation actually works on daily data
js.evaljs("var DB = {n:%d, o:%s, h:%s, l:%s, c:%s, mins:%s, sessions:Core.buildSessions(%s)};" % (
    len(daily), json.dumps([100 + i for i in range(len(daily))]),
    json.dumps([101 + i for i in range(len(daily))]),
    json.dumps([99 + i for i in range(len(daily))]),
    json.dumps([100.5 + i for i in range(len(daily))]),
    json.dumps([0] * len(daily)), json.dumps(daily)))
w = js.evaljs("var DW = Core.aggregate(DB, 5); ({n:DW.n, o:DW.o[0], h:DW.h[0], c:DW.c[0]})")
check("weekly aggregation of daily bars produces fewer candles",
      w["n"] == 48, f"got {w['n']}, expected 48")
check("aggregated daily candle takes the first open", abs(w["o"] - 100) < 1e-9)
check("aggregated daily candle takes the 5-bar high", abs(w["h"] - 105) < 1e-9)
check("aggregated daily candle takes the last close", abs(w["c"] - 104.5) < 1e-9)
mixed = ["2023-01-03"] * 3 + ["2023-01-04"]
sm2 = js.evaljs("Core.buildSessions(%s)" % json.dumps(mixed))
check("a file with any repeated date is treated as intraday", len(sm2) == 2)
check("buildSessions on an empty file returns nothing",
      js.evaljs("Core.buildSessions([]).length") == 0)

print("\n--- replay cursor across a timeframe change ---")
# Duktape cannot hold several full aggregations of 315,900 bars at once, so each
# timeframe is built, exercised and released before the next one.
for tf in (1, 5, 60, 390):
    js.evaljs(f"var AR = Core.aggregate(B, {tf});")
    bad = js.evaljs(f"var bad = 0;"
                    f"var probes = [0, 500, 100000, {N - 1}];"
                    f"for (var k = 0; k < probes.length; k++){{"
                    f"  var i = probes[k];"
                    f"  var v = Core.replayToView(i, AR, {N});"
                    f"  var s = AR.src[v];"
                    f"  if (!(s <= i && i < s + {tf})) bad++;"
                    f"}} bad")
    check(f"tf={tf:>3}: a base bar maps into the candle that contains it", bad == 0)
    rt = js.evaljs(f"var bad2 = 0;"
                   f"for (var i = 0; i < {N}; i += 997){{"
                   f"  var v = Core.replayToView(i, AR, {N});"
                   f"  var back = Core.viewToReplay(v, AR, {N});"
                   f"  if (back > i || i - back >= {tf}) bad2++;"
                   f"}} bad2")
    check(f"tf={tf:>3}: cursor round-trip never leaves its own candle", rt == 0)
    oob = js.evaljs(f"[Core.replayToView(-50, AR, {N}), Core.replayToView({N + 9999}, AR, {N}),"
                    f" Core.viewToReplay(-3, AR, {N}), Core.viewToReplay(99999, AR, {N})]")
    check(f"tf={tf:>3}: out-of-range cursors clamp, never undefined",
          all(isinstance(x, (int, float)) and 0 <= x < N for x in oob), str(oob))
    js.evaljs("AR = null;")

print("\n--- account simulation ---")
# A deliberately simple series: a long that runs 20 points against you before
# recovering to a winner. Whether you survive it depends entirely on size.
js.evaljs("var AB = {n:5, o:[100,100,100,100,100], h:[101,101,101,120,120],"
          " l:[100,95,80,80,80], c:[100,96,81,119,119]};")
js.evaljs("var AT = [{side:1, entry:100, exit:119, stop_px:75}];")

small = js.evaljs("Core.simulateAccount(AB, AT, [0], [4], "
                  "{balance:10000, floor:0, contracts:1, pointValue:2,"
                  " commission:0, slippage:0})")
r = small["rows"][0]
check("small size: the stop is reachable", r["stopReachable"] is True)
check("small size: not force-liquidated", r["forced"] is False)
check("small size: exits at the recorded exit", abs(r["exit"] - 119) < 1e-9)
check("small size: MAE is the worst adverse excursion", abs(r["mae"] - 20) < 1e-9)
check("small size: MFE is the best favourable excursion", abs(r["mfe"] - 20) < 1e-9)
check("small size: P&L is points x size x point value", abs(r["pnl"] - 19 * 2) < 1e-9)
check("small size: balance updates", abs(r["bal"] - 10038) < 1e-9)

# identical trade and stop, but sized so $200 of room is gone after 10 points
big = js.evaljs("Core.simulateAccount(AB, AT, [0], [4], "
                "{balance:200, floor:0, contracts:10, pointValue:2,"
                " commission:0, slippage:0})")
rb = big["rows"][0]
check("large size: the stop is NOT reachable", rb["stopReachable"] is False)
check("large size: forced liquidation fires", rb["forced"] is True)
check("large size: liquidation distance is room / (size x point value)",
      abs(rb["liqDist"] - 200 / 20) < 1e-9)
check("large size: exits at the liquidation price, not the stop",
      abs(rb["exit"] - 90) < 1e-9)
check("large size: the account is wiped", abs(rb["bal"]) < 1e-9)
check("large size: the account is marked dead", big["summary"]["dead"] is True)
check("THE POINT: the same winning trade becomes a total loss purely from size",
      r["pnl"] > 0 and rb["pnl"] < 0)

js.evaljs("var AT2 = [{side:1,entry:100,exit:119,stop_px:75},"
          "{side:1,entry:100,exit:119,stop_px:75}];")
dead = js.evaljs("Core.simulateAccount(AB, AT2, [0,0], [4,4], "
                 "{balance:200, floor:0, contracts:10, pointValue:2})")
check("no trades are taken after the account dies",
      dead["rows"][1]["skipped"] is True and dead["summary"]["taken"] == 1)

js.evaljs("var AS = [{side:-1, entry:100, exit:81, stop_px:125}];")
rs = js.evaljs("Core.simulateAccount(AB, AS, [0], [4], "
               "{balance:10000, floor:0, contracts:1, pointValue:2})")["rows"][0]
check("short: MAE measures the move UP against the position", abs(rs["mae"] - 20) < 1e-9)
check("short: profits when price falls", rs["pnl"] > 0)

rk = js.evaljs("Core.simulateAccount(AB, AT, [0], [4], "
               "{balance:10000, floor:0, sizeMode:'risk', riskPct:1, pointValue:2})")
check("risk sizing: size = risk budget / (stop distance x point value)",
      rk["rows"][0]["size"] == int(10000 * 0.01 / (25 * 2)))
tiny = js.evaljs("Core.simulateAccount(AB, AT, [0], [4], "
                 "{balance:50, floor:0, sizeMode:'risk', riskPct:1, pointValue:2})")
check("risk sizing: a trade too small to size is skipped, not sized at zero",
      tiny["rows"][0]["skipped"] is True)

rc = js.evaljs("Core.simulateAccount(AB, AT, [0], [4], "
               "{balance:10000, floor:0, contracts:2, pointValue:2,"
               " commission:1.5, slippage:0.25})")["rows"][0]
check("costs: slippage is charged on both sides", abs(rc["pts"] - 18.5) < 1e-9)
check("costs: commission is per contract per side",
      abs(rc["pnl"] - (18.5 * 4 - 1.5 * 2 * 2)) < 1e-9)

mc = js.evaljs("Core.simulateAccount(AB, AT, [0], [4], "
               "{balance:400, floor:200, contracts:10, pointValue:2})")
check("a floor above zero liquidates earlier, like a margin call",
      abs(mc["rows"][0]["liqDist"] - 10) < 1e-9)
check("summary counts forced liquidations", mc["summary"]["forced"] == 1)
check("summary reports return as a percentage",
      abs(mc["summary"]["returnPct"] - (mc["summary"]["end"] - 400) / 400 * 100) < 1e-9)
oob = js.evaljs("Core.simulateAccount(AB, AT, [-1], [4], {balance:100}).rows[0].skipped")
check("an out-of-range trade index is skipped safely", oob is True)

# the bug this caught in the field: a $1,000 account finishing at -$4.00
costly = js.evaljs("Core.simulateAccount(AB, AT, [0], [4], "
                   "{balance:200, floor:0, contracts:10, pointValue:2,"
                   " commission:1.5, slippage:0.25})")
cr = costly["rows"][0]
check("liquidation prices the EXIT, so the balance never goes below the floor",
      cr["bal"] >= -1e-6, f"balance {cr['bal']}")
check("liquidation lands exactly on the floor", abs(cr["bal"]) < 1e-6,
      f"balance {cr['bal']}")
check("liquidation distance is reduced by the round-turn cost",
      abs(cr["liqDist"] - (200 - (2 * 0.25 * 20 + 2 * 1.5 * 10)) / 20) < 1e-9)
broke = js.evaljs("Core.simulateAccount(AB, AT, [0], [4], "
                  "{balance:20, floor:0, contracts:10, pointValue:2,"
                  " commission:1.5, slippage:0.25}).rows[0]")
check("a trade that cannot afford its own round turn is skipped",
      broke["skipped"] is True and broke["reason"] == 'costs exceed remaining equity')

print("\n--- evaluation rules (PASS / FAIL) ---")
# four sessions, each a clean +100-point long at 1 contract x $2 = +$200/day
js.evaljs("var EB = {n:8, o:[100,100,100,100,100,100,100,100],"
          " h:[210,210,210,210,210,210,210,210], l:[99,99,99,99,99,99,99,99],"
          " c:[200,200,200,200,200,200,200,200],"
          " sessions:[{day:'d1',a:0,b:1},{day:'d2',a:2,b:3},"
          "           {day:'d3',a:4,b:5},{day:'d4',a:6,b:7}]};")
js.evaljs("var ET = []; for (var q=0;q<8;q++) "
          "ET.push({side:1, entry:100, exit:200, stop_px:50});")
js.evaljs("var EI = [0,1,2,3,4,5,6,7];")

ev = js.evaljs("Core.simulateAccount(EB, ET, EI, EI, "
               "{balance:1000, contracts:1, pointValue:2, commission:0, slippage:0,"
               " evaluation:{on:true, target:1250, dailyCap:625, trailDD:1000,"
               "             freezeOffset:100}}).summary")
check("evaluation reports a verdict", ev["evaluation"]["verdict"] in ("PASS", "FAIL", "INCOMPLETE"))
check("a day cannot book more than the consistency cap",
      ev["evaluation"]["bestDay"] <= 625 + 1e-9,
      f"best day {ev['evaluation']['bestDay']}")
# at 1 contract each day books $400, under the $625 cap, so the cap never fires.
# 4 contracts makes a single trade worth $800 and forces it.
BIG = ("Core.simulateAccount(EB, ET, EI, EI, "
       "{balance:1000, contracts:4, pointValue:2, commission:0, slippage:0,"
       " evaluation:{on:true, target:1250, dailyCap:625, trailDD:1000,"
       "             freezeOffset:100}})")
big_ev = js.evaljs(BIG + ".summary")
big_rows = js.evaljs(BIG + ".rows")
check("hitting the cap is counted", big_ev["evaluation"]["capHits"] >= 1,
      f"capHits {big_ev['evaluation']['capHits']}")
check("a capped trade books exactly the cap, not its full profit",
      any(r.get("capped") and abs(r["pnl"] - 625) < 1e-9 for r in big_rows))
check("no further trade is booked once the day's cap is reached",
      any(r.get("skipped") and r.get("reason") == "daily cap reached" for r in big_rows))
check("even oversized, no day books more than the cap",
      big_ev["evaluation"]["bestDay"] <= 625 + 1e-9,
      f"best day {big_ev['evaluation']['bestDay']}")
check("a $1,250 target under a $625 cap needs at least two days",
      big_ev["evaluation"]["passedDays"] >= 2,
      f"passed in {big_ev['evaluation']['passedDays']} days")
check("passing requires at least two days at a $625 cap and a $1,250 target",
      ev["evaluation"]["passedDays"] >= 2 if ev["evaluation"]["passed"] else True,
      f"passed in {ev['evaluation']['passedDays']} days")
check("PASS is reached on this winning series", ev["evaluation"]["passed"] is True)
check("a passing run is not also reported as failed", ev["evaluation"]["failed"] is False)

# a losing series must FAIL on the trailing drawdown
js.evaljs("var LB = {n:4, o:[100,100,100,100], h:[101,101,101,101],"
          " l:[0,0,0,0], c:[1,1,1,1],"
          " sessions:[{day:'d1',a:0,b:1},{day:'d2',a:2,b:3}]};")
js.evaljs("var LT = [{side:1,entry:100,exit:1,stop_px:50},"
          "{side:1,entry:100,exit:1,stop_px:50}];")
fail = js.evaljs("Core.simulateAccount(LB, LT, [0,2], [1,3], "
                 "{balance:1000, contracts:5, pointValue:2, commission:0, slippage:0,"
                 " evaluation:{on:true, target:1250, dailyCap:625, trailDD:1000,"
                 "             freezeOffset:100}}).summary")
check("a losing run reports FAIL", fail["evaluation"]["verdict"] == "FAIL")
check("FAIL records the trade it died on", fail["evaluation"]["failedAt"] >= 0)
check("the evaluation floor starts one drawdown below the balance",
      abs(fail["evaluation"]["finalFloor"] - 0) < 1e-6 or
      fail["evaluation"]["finalFloor"] <= 1000)
noev = js.evaljs("Core.simulateAccount(EB, ET, EI, EI, "
                 "{balance:1000, contracts:1, pointValue:2}).summary.evaluation")
check("evaluation block is absent when the rules are off", noev is None)

check("a PASS is not also reported as blown up",
      big_ev["blownUp"] is False and big_ev["stopped"] is True)
check("a PASS reports dead=false so the rail cannot say BLOWN UP",
      big_ev["dead"] is False)

print("\n--- trailing drawdown: ratchets at END OF DAY only ---")
# Day 1: two winners of +$250 each at 1 contract x $2/pt (125 pts).
# Day 2: a loser. The floor must NOT have moved during day 1, only at its close.
js.evaljs("var TB = {n:6,"
          " o:[100,100,100,100,100,100],"
          " h:[225,225,225,101,101,101],"
          " l:[99,99,99,-900,-900,-900],"
          " c:[225,225,225,0,0,0],"
          " sessions:[{day:'d1',a:0,b:2},{day:'d2',a:3,b:5}]};")
js.evaljs("var TT = [{side:1,entry:100,exit:225,stop_px:50},"
          "         {side:1,entry:100,exit:225,stop_px:50},"
          "         {side:1,entry:100,exit:0,stop_px:50}];")
tr = js.evaljs("Core.simulateAccount(TB, TT, [0,1,3], [0,1,5], "
               "{balance:25000, contracts:1, pointValue:2, commission:0, slippage:0,"
               " evaluation:{on:true, target:100000, dailyCap:100000,"
               "             trailDD:1000, freezeOffset:100000}})")
rw = tr["rows"]
check("floor starts one drawdown below the opening balance",
      abs(rw[0]["floor"] - 24000) < 1e-6, f"floor {rw[0]['floor']}")
check("INTRADAY profit does NOT move the floor",
      abs(rw[1]["floor"] - 24000) < 1e-6,
      f"after a +$250 winner the floor was {rw[1]['floor']}, expected 24000")
check("the floor ratchets on the NEXT day, to EOD balance minus the drawdown",
      abs(rw[2]["floor"] - (25000 + 250 + 250 - 1000)) < 1e-6,
      f"floor {rw[2]['floor']}, expected {25000 + 500 - 1000}")
check("the ratcheted floor is above the original bust level",
      rw[2]["floor"] > 24000)

# the freeze: once the floor reaches start + freezeOffset it stops trailing
fz = js.evaljs("Core.simulateAccount(TB, TT, [0,1,3], [0,1,5], "
               "{balance:25000, contracts:1, pointValue:2, commission:0, slippage:0,"
               " evaluation:{on:true, target:100000, dailyCap:100000,"
               "             trailDD:1000, freezeOffset:100}}).rows")
# The freeze is a CEILING on the floor, not a jump to it. EOD $25,500 gives a
# floor of $24,500 -- exactly the worked example in the spec -- and the ceiling
# only binds once the balance passes start + freezeOffset + trailDD.
check("floor is EOD balance minus the drawdown, matching the worked example",
      abs(fz[2]["floor"] - 24500) < 1e-6, f"floor {fz[2]['floor']}")
check("the freeze ceiling does not bind while the floor is below it",
      fz[2]["floor"] < 25100)
# now push the EOD balance past 26,100 so the ceiling actually engages
js.evaljs("var HB = {n:4, o:[100,100,100,100], h:[1300,1300,101,101],"
          " l:[99,99,-900,-900], c:[1300,1300,0,0],"
          " sessions:[{day:'d1',a:0,b:1},{day:'d2',a:2,b:3}]};")
js.evaljs("var HT = [{side:1,entry:100,exit:1300,stop_px:50},"
          "         {side:1,entry:100,exit:0,stop_px:50}];")
hz = js.evaljs("Core.simulateAccount(HB, HT, [0,2], [1,3], "
               "{balance:25000, contracts:1, pointValue:2, commission:0, slippage:0,"
               " evaluation:{on:true, target:1000000, dailyCap:1000000,"
               "             trailDD:1000, freezeOffset:100}}).rows")
check("once the balance is high enough the floor freezes at start + offset",
      abs(hz[1]["floor"] - 25100) < 1e-6, f"floor {hz[1]['floor']}")
check("the frozen floor is capped, not equal to balance minus drawdown",
      hz[1]["floor"] < hz[0]["bal"] - 1000)

# and the consequence the user hit: stopped out well above the starting bust level
bust = js.evaljs("Core.simulateAccount(TB, TT, [0,1,3], [0,1,5], "
                 "{balance:25000, contracts:1, pointValue:2, commission:0, slippage:0,"
                 " evaluation:{on:true, target:100000, dailyCap:100000,"
                 "             trailDD:1000, freezeOffset:100000}}).summary")
check("the account can be stopped out while still above its ORIGINAL bust level",
      bust["blownUp"] is True)
check("every row carries the floor that applied to it, so it can be charted",
      all(("floor" in r) for r in rw if not r.get("skipped")))


print("\n--- the ticket lifecycle: eval -> funded -> repeated withdrawals ---")
# Twelve sessions, each offering one clean +$700 long at 1 contract x $2/pt.
# Cap 625, so every day books exactly 625. Target 1250 -> the evaluation passes
# on day 2. The account is then FUNDED, restarts at 25,000, and needs +2,100 to
# withdraw, which at 625 a day arrives four days later. The withdrawal takes
# $1,000 out (you keep 90% = $900) and the account carries on from $26,100.
js.evaljs("var RB = {n:12, o:[], h:[], l:[], c:[], sessions:[]};"
          "for (var q=0;q<12;q++){ RB.o.push(100); RB.h.push(450); RB.l.push(99);"
          " RB.c.push(450); RB.sessions.push({day:'d'+q, a:q, b:q}); }")
js.evaljs("var RT = []; for (var q=0;q<12;q++) "
          "RT.push({side:1, entry:100, exit:450, stop_px:50});")
js.evaljs("var RI = []; for (var q=0;q<12;q++) RI.push(q);")
OPT = ("{balance:25000, contracts:1, pointValue:2, commission:0, slippage:0,"
       " evaluation:{on:true, target:1250, dailyCap:625, trailDD:1000,"
       "             freezeOffset:100, cost:65, payoutAt:2100,"
       "             payoutDraw:1000, payoutSplit:0.9}}")
ser = js.evaljs("Core.simulateSeries(RB, RT, RI, RI, " + OPT + ")")
sm = ser["summary"]
accs = ser["accounts"]

check("passing promotes the ticket instead of ending it",
      all(a["funded"] for a in accs if a["draws"] > 0),
      "an account paid without ever being marked funded")
check("a funded account restarts at the opening balance",
      all(a["stage"] in ("eval", "funded") for a in accs))
check("reaching the threshold pays out", sm["payouts"] >= 1, f"payouts {sm['payouts']}")
check("you receive the draw times the split, not the whole profit",
      abs(sm["won"] - sm["payouts"] * 900) < 1e-9,
      f"won {sm['won']} for {sm['payouts']} withdrawals, expected {sm['payouts'] * 900}")
check("the reported payout value is draw x split",
      abs(sm["payoutValue"] - 900) < 1e-9, f"payoutValue {sm['payoutValue']}")
check("ONE account can pay more than once",
      any(a["draws"] > 1 for a in accs) or sm["accounts"] == 1,
      "no account paid twice, so the repeating model is not in effect")
check("a withdrawal does not retire the account",
      sm["accounts"] == 1, f"{sm['accounts']} tickets bought when one should suffice")
check("tickets are charged once each",
      abs(sm["spent"] - sm["accounts"] * 65) < 1e-9)
check("net is money received minus tickets bought",
      abs(sm["net"] - (sm["won"] - sm["spent"])) < 1e-9,
      f"net {sm['net']} vs won {sm['won']} - spent {sm['spent']}")
check("return on ticket spend is reported",
      abs(sm["roi"] - (sm["won"] - sm["spent"]) / sm["spent"]) < 1e-9)
check("net per ticket is reported",
      abs(sm["perTicket"] - (sm["won"] - sm["spent"]) / sm["accounts"]) < 1e-9)
check("withdrawals per funded account is reported",
      abs(sm["drawsPerFunded"] - sm["payouts"] / max(1, sm["passes"])) < 1e-9)
check("trading P&L is reported separately and is not the net",
      "tradingPnl" in sm and sm["tradingPnl"] != sm["net"])
check("accounts are numbered consecutively from 1",
      [a["n"] for a in accs] == list(range(1, len(accs) + 1)))
check("every row carries the account it belonged to",
      all(("acct" in r) for r in ser["rows"] if r and not r.get("skipped")))

# the user also wants the one-payout-per-account view kept
one = js.evaljs("Core.simulateSeries(RB, RT, RI, RI, "
                "{balance:25000, contracts:1, pointValue:2, commission:0, slippage:0,"
                " evaluation:{on:true, target:1250, dailyCap:625, trailDD:1000,"
                "  freezeOffset:100, cost:65, payoutAt:2100, payoutDraw:1000,"
                "  payoutSplit:0.9, retireOnPayout:true}})")
osm = one["summary"]
check("retiring on payout ends the account and buys another",
      osm["accounts"] > sm["accounts"],
      f"{osm['accounts']} tickets when retiring vs {sm['accounts']} when carrying on")
check("retiring on payout caps each account at one withdrawal",
      all(a["draws"] <= 1 for a in one["accounts"]),
      "an account paid twice with retireOnPayout on")
check("carrying on is worth more than retiring, on the same data",
      sm["net"] >= osm["net"],
      f"carry-on {sm['net']} vs retire {osm['net']}")
check("the mode is reported back so a chart cannot mislabel itself",
      osm["retireOnPayout"] is True and sm["retireOnPayout"] is False)

# the split is the single most important number: it scales every win
halfsplit = js.evaljs("Core.simulateSeries(RB, RT, RI, RI, "
                      "{balance:25000, contracts:1, pointValue:2, commission:0, slippage:0,"
                      " evaluation:{on:true, target:1250, dailyCap:625, trailDD:1000,"
                      "  freezeOffset:100, cost:65, payoutAt:2100, payoutDraw:1000,"
                      "  payoutSplit:0.5}})")
check("a worse profit split reduces what you receive, proportionally",
      abs(halfsplit["summary"]["won"] - halfsplit["summary"]["payouts"] * 500) < 1e-9,
      f"won {halfsplit['summary']['won']}")
check("a worse split lowers the net",
      halfsplit["summary"]["net"] < sm["net"] or sm["payouts"] == 0)

# the consistency cap once funded is a setting, not an assumption
nocap = js.evaljs("Core.simulateSeries(RB, RT, RI, RI, "
                  "{balance:25000, contracts:1, pointValue:2, commission:0, slippage:0,"
                  " evaluation:{on:true, target:1250, dailyCap:625, trailDD:1000,"
                  "  freezeOffset:100, cost:65, payoutAt:2100, payoutDraw:1000,"
                  "  payoutSplit:0.9, fundedCapOn:false}})")
check("lifting the cap once funded reaches the threshold sooner",
      nocap["summary"]["payouts"] >= sm["payouts"],
      f"capped {sm['payouts']} vs uncapped {nocap['summary']['payouts']}")
check("the cap setting is reported back", nocap["summary"]["fundedCapOn"] is False)

# a losing stream must produce FAILs and keep buying accounts
js.evaljs("var FB = {n:6, o:[100,100,100,100,100,100],"
          " h:[101,101,101,101,101,101], l:[-9000,-9000,-9000,-9000,-9000,-9000],"
          " c:[0,0,0,0,0,0],"
          " sessions:[{day:'d1',a:0,b:0},{day:'d2',a:1,b:1},{day:'d3',a:2,b:2},"
          "           {day:'d4',a:3,b:3},{day:'d5',a:4,b:4},{day:'d6',a:5,b:5}]};")
js.evaljs("var FT = []; for (var q=0;q<6;q++) "
          "FT.push({side:1, entry:100, exit:0, stop_px:-9000});")
fser = js.evaljs("Core.simulateSeries(FB, FT, RI, RI, " + OPT + ")")
fsm = fser["summary"]
check("a losing stream fails account after account", fsm["fails"] >= 2,
      f"fails {fsm['fails']}")
check("a losing stream passes nothing", fsm["passes"] == 0)
check("pass rate is zero when nothing passes", fsm["passRate"] == 0)
check("a failing account never ends below its floor",
      all(a["bal"] >= a["floor"] - 1e-6 for a in fser["accounts"]))

# the daily loss limit must bind before the account floor when it is tighter
dl = js.evaljs("Core.simulateSeries(FB, FT, RI, RI, "
               "{balance:25000, contracts:1, pointValue:2, commission:0, slippage:0,"
               " evaluation:{on:true, target:1250, dailyCap:625, dailyLoss:200,"
               "             trailDD:1000, freezeOffset:100, cost:65}})")
worst = min(r["pnl"] for r in dl["rows"] if r and not r.get("skipped"))
check("a daily loss limit caps the loss on a single trade",
      worst >= -200 - 1e-6, f"worst trade {worst}, limit 200")
check("a tighter daily loss limit means more trades before busting",
      dl["summary"]["trades"] >= fsm["trades"],
      f"{dl['summary']['trades']} vs {fsm['trades']}")
# the previous fixture has one trade per session, so a daily loss limit can
# never skip a LATER trade that day. This one has two trades per session.
js.evaljs("var DB = {n:4, o:[100,100,100,100], h:[101,101,101,101],"
          " l:[-9000,-9000,-9000,-9000], c:[0,0,0,0],"
          " sessions:[{day:'d1',a:0,b:1},{day:'d2',a:2,b:3}]};")
js.evaljs("var DT = []; for (var q=0;q<4;q++) "
          "DT.push({side:1, entry:100, exit:0, stop_px:-9000});")
dl2 = js.evaljs("Core.simulateSeries(DB, DT, [0,1,2,3], [0,1,2,3], "
                "{balance:25000, contracts:1, pointValue:2, commission:0, slippage:0,"
                " evaluation:{on:true, target:1250, dailyCap:625, dailyLoss:200,"
                "             trailDD:1000, freezeOffset:100, cost:65}})")
check("a later trade on a day that hit its loss limit is skipped",
      any(r and r.get("reason") == "daily loss limit reached" for r in dl2["rows"]),
      str([r.get("reason") for r in dl2["rows"] if r]))
check("the day resets, so the next session trades again",
      any(r and not r.get("skipped") and r.get("i", 0) >= 2 for r in dl2["rows"]))
check("no single day loses more than the daily loss limit",
      all(abs(r["dayPnL"]) <= 200 + 1e-6
          for r in dl2["rows"] if r and not r.get("skipped")),
      str([r.get("dayPnL") for r in dl2["rows"] if r and not r.get("skipped")]))

nolimit = js.evaljs("Core.simulateSeries(FB, FT, RI, RI, "
                    "{balance:25000, contracts:1, pointValue:2,"
                    " evaluation:{on:true, dailyLoss:0}}).summary")
check("a daily loss limit of zero means no limit", nolimit["dailyLoss"] == 0)
ser_rows = js.evaljs("Core.simulateSeries(RB, RT, RI, RI, " + OPT + ").rows")
check("simulateSeries never books an evaluation past the pass line",
      all(r["bal"] <= 25000 + 1250 + 1e-6 for r in ser_rows
          if r and not r.get("skipped") and r.get("stage") == "eval"))
# +$400 a day: three days make +$1,200, the fourth needs only $50 more, so
# that trade is trimmed to $50 at the pass line, not to the $625 cap
js.evaljs("var PB = {n:12, o:[], h:[], l:[], c:[], sessions:[]};"
          "for (var q=0;q<12;q++){ PB.o.push(100); PB.h.push(300); PB.l.push(99);"
          " PB.c.push(300); PB.sessions.push({day:'d'+q, a:q, b:q}); }")
js.evaljs("var PT = []; for (var q=0;q<12;q++) PT.push({side:1, entry:100, exit:300, stop_px:50});")
p_rows = js.evaljs("Core.simulateSeries(PB, PT, RI, RI, " + OPT + ").rows")
p4 = p_rows[3]
check("simulateSeries trims the passing trade to the line and names it",
      abs(p4["pnl"] - 50) < 1e-9 and p4["capped"] and p4["bind"] == "pass" and abs(p4["bal"] - 26250) < 1e-9,
      str({k: p4.get(k) for k in ("pnl", "capped", "bind", "bal")}))
js.evaljs("PB = null; PT = null;")
# the funded stage stops at the payout line the same way: +$625 a day from
# $25,000 reaches $26,875 in three days, and the fourth trade is trimmed to
# the $225 that reaches $27,100
f_rows = [r for r in ser_rows if r and not r.get("skipped") and r.get("stage") == "funded"]
check("no funded trade ends above the payout line",
      all(r["bal"] <= 25000 + 2100 + 1e-6 for r in f_rows),
      "worst %.2f" % max((r["bal"] for r in f_rows), default=0))
pay = [r for r in f_rows if r.get("bind") == "payout"]
check("the paying trade is trimmed to the payout line and says so",
      len(pay) > 0 and all(abs(r["bal"] - 27100) < 1e-6 and r["pnl"] < 625 for r in pay),
      "%d payout rows" % len(pay))
check("simulateSeries returns one row per trade",
      len(ser["rows"]) == 12 and len(fser["rows"]) == 6)

print("\n--- bucketed price range ---")
js.evaljs("var A1b = Core.aggregate(B, 1); var BK = Core.buildBuckets(A1b, 512);")
bk = js.evaljs("({size:BK.size, n:BK.n, nb:BK.lo.length})")
check("bucket count covers the series",
      bk["nb"] == -(-N // 512), "%d vs %d" % (bk["nb"], -(-N // 512)))
check("buckets record the series length so a stale set can be detected", bk["n"] == N)
bad = 0
for (a, b) in [(0, 0), (0, 1), (0, 389), (100, 5000), (0, 50000), (0, N - 1),
               (N - 600, N - 1), (511, 513), (512, 1024), (1023, 1025)]:
    same = js.evaljs("var x=Core.priceRange(A1b,%d,%d,0.06), "
                     "y=Core.priceRangeFast(A1b,BK,%d,%d,0.06);"
                     "(Math.abs(x.lo-y.lo)<1e-9 && Math.abs(x.hi-y.hi)<1e-9)?1:0" % (a, b, a, b))
    if same != 1:
        bad += 1
check("fast range equals the exact scan on 10 windows incl. bucket edges", bad == 0,
      "%d mismatched" % bad)
check("a stale bucket set falls back to the exact scan rather than lying",
      js.evaljs("var y=Core.priceRangeFast(A1b,{size:512,lo:[0],hi:[1],n:7},0,900,0.06);"
                "var x=Core.priceRange(A1b,0,900,0.06);"
                "(Math.abs(x.lo-y.lo)<1e-9)?1:0") == 1)
check("no buckets at all falls back too",
      js.evaljs("var y=Core.priceRangeFast(A1b,null,0,900,0.06);"
                "var x=Core.priceRange(A1b,0,900,0.06);"
                "(Math.abs(x.hi-y.hi)<1e-9)?1:0") == 1)
check("an inverted window does not return Infinity",
      js.evaljs("var r=Core.priceRangeFast(A1b,BK,900,100,0.06); "
                "(isFinite(r.lo)&&isFinite(r.hi))?1:0") == 1)
js.evaljs("A1b = null; BK = null;")

print("\n--- strategy runner ---")
js.evaljs("var SB = Core.aggregate(B, 1);")
BASE_OPT = ("{entry:{mode:'reentry', startMin:600, slotMin:30, direction:'random', seed:23},"
            " trade:{stopPts:50, rr:1.0},"
            " acct:{balance:25000, contracts:%d, pointValue:%s, commission:%s, slippage:0.25},"
            " rules:{trailDD:1000, freezeOffset:100, dailyCap:625, target:1250,"
            "        payoutAt:2100, ticket:65%s}}")
r1 = js.evaljs("Core.runStrategy(SB, %s).summary"
               % (BASE_OPT % (1, "2", "0.75", "")))
check("a run produces trades", r1["nTrades"] > 100)
check("evals = 1 + every blow-up",
      r1["evals"] == 1 + r1["evalBust"] + r1["fundBust"] + r1["payouts"],
      str(r1))
check("accounts only ever increase", r1["accounts"] >= r1["evals"])
check("cost is the ticket price times evaluations bought",
      abs(r1["cost"] - r1["evals"] * 65) < 1e-9)

# wealthCurve: payouts banked minus tickets bought, one value per session,
# rebuilt from the run's events. The Strategy panel's ensemble draws these.
cv = js.evaljs("var _r = Core.runStrategy(SB, %s);"
               " var _c = Core.wealthCurve(_r, SB.sessions.length);"
               " [_c.length, _c[0], _c[_c.length - 1], _r.summary.net, SB.sessions.length]"
               % (BASE_OPT % (1, "2", "0.75", "")))
check("wealthCurve has one value per session", cv[0] == cv[4], str(cv))
check("the first session already carries the first ticket, and only tickets",
      cv[1] <= -65 and abs(cv[1]) % 65 == 0, str(cv[1]))
check("wealthCurve ends on the run's net", abs(cv[2] - cv[3]) < 1e-9, "%s vs %s" % (cv[2], cv[3]))
steps = js.evaljs("(function(){ var d = []; for (var i = 1; i < _c.length; i++) d.push(_c[i] - _c[i-1]);"
                  " return d; })()")
legal = {900 * j - 65 * k for j in range(0, 30) for k in range(0, 30)}
check("wealth only ever moves by whole tickets and whole payouts",
      all(round(d) in legal and abs(d - round(d)) < 1e-9 for d in steps),
      str([d for d in steps if round(d) not in legal][:5]))
# a dearer ticket must show up in the curve: it reads the event, not a constant
cv80 = js.evaljs("var _r80 = Core.runStrategy(SB, %s); Core.wealthCurve(_r80, SB.sessions.length)[0]"
                 % (BASE_OPT % (1, "2", "0.75", "")).replace("ticket:65", "ticket:80"))
check("wealthCurve charges the ticket price the run was given", cv80 <= -80 and abs(cv80) % 80 == 0,
      str(cv80))
js.evaljs("_r = null; _c = null; _r80 = null;")

# The runner now also emits a row for a slot it DECLINED to trade, tagged with
# the reason, so the chart can draw it faint rather than pretend the slot never
# came up. Those rows carry no price, so every assertion below is about the
# trades that were actually taken.
def taken(res):
    return [t for t in res if not t.get("skipped")]


rows = taken(js.evaljs("Core.runStrategy(SB, %s).trades" % (BASE_OPT % (1, "2", "0.75", ""))))
check("no trade loses more than its own allowance",
      all(t["pts"] >= -t["A"] - 1e-6 for t in rows))
check("no trade gains more than its own allowance",
      all(t["pts"] <= t["F"] + 1e-6 for t in rows))
check("every exit is at or after its entry",
      all(t["exit_bar"] >= t["entry_bar"] for t in rows))
check("trades never overlap in time",
      all(rows[i + 1]["entry_bar"] > rows[i]["exit_bar"]
          for i in range(len(rows) - 1)
          if rows[i + 1]["account"] == rows[i]["account"]))
check("no eval day books more than the consistency cap",
      max((t["realized"] for t in rows if t["stage"] == "eval"), default=0) <= 625 + 1e-6)
check("a live account is never below its floor",
      all(t["bal"] > t["floor"] - 1e-6 or t is rows[-1] for t in rows[:-1]))
# An evaluation ends the moment it reaches the pass line: the balance is reset
# to the start, so profit past the line is thrown away and a trade left running
# past it risks busting an account that had already passed. The target is
# trimmed to the line exactly as it is trimmed to the daily cap.
ev_rows = [t for t in rows if t["stage"] == "eval"]
check("no evaluation trade ends above the pass line",
      all(t["bal"] <= 25000 + 1250 + 1e-6 for t in ev_rows),
      "worst %.2f" % max(t["bal"] for t in ev_rows))
passing = [t for t in ev_rows if abs(t["bal"] - 26250) < 1e-6]
check("the passing trade lands on the line and says so",
      len(passing) > 0 and all(t["capped"] and t["bind"] == "pass" for t in passing),
      "%d passing rows" % len(passing))
check("a trade the cap trims is labelled cap, not pass",
      any(t["capped"] and t["bind"] == "cap" for t in ev_rows))
check("a trade trimmed at the pass line is shorter than the cap allows",
      all(t["pnl"] <= 625 + 1e-6 for t in passing))
fd_rows = [t for t in rows if t["stage"] == "funded"]
check("no funded trade ends above the payout line (strategy run)",
      all(t["bal"] <= 25000 + 2100 + 1e-6 for t in fd_rows),
      "worst %.2f" % max((t["bal"] for t in fd_rows), default=0))
paying = [t for t in fd_rows if abs(t["bal"] - 27100) < 1e-6]
check("every paying trade lands on the payout line and says so (%d payouts in this run)" % r1["payouts"],
      len(paying) >= r1["payouts"] and all(t["capped"] and t["bind"] == "payout" for t in paying),
      "%d rows on the line" % len(paying))

# the same seed must give the same run, or nothing is reproducible
r2 = js.evaljs("Core.runStrategy(SB, %s).summary" % (BASE_OPT % (1, "2", "0.75", "")))
check("the same seed reproduces the run exactly", r1 == r2)
r3 = js.evaljs("Core.runStrategy(SB, %s).summary"
               % (BASE_OPT % (1, "2", "0.75", "")).replace("seed:23", "seed:99"))
check("a different seed gives a different run", r1 != r3)

# THE POINT of doing generation and account together: size changes the EXITS
big = taken(js.evaljs("Core.runStrategy(SB, %s).trades" % (BASE_OPT % (10, "2", "0.75", ""))))
n = min(len(rows), len(big))
diff = sum(1 for i in range(n) if abs(rows[i]["exit"] - big[i]["exit"]) > 1e-6)
check("raising size changes where trades EXIT, not just what they earn",
      diff > 0, "sizes produced identical exits, which cannot be right")
check("a bigger size reaches the daily cap in fewer points",
      big[0]["F"] < rows[0]["F"] + 1e-9)

orb = js.evaljs("Core.runStrategy(SB, %s).summary"
                % (BASE_OPT % (1, "2", "0.75", "")).replace("mode:'reentry'", "mode:'orb'")
                                                   .replace("direction:'random'", "direction:'orb'"))
check("the ORB entry rule runs and trades once per session at most",
      orb["nTrades"] <= len(SESS) + 1, "%d trades over %d sessions" % (orb["nTrades"], len(SESS)))
check("ORB is deterministic: no seed dependence",
      orb == js.evaljs("Core.runStrategy(SB, %s).summary"
                       % (BASE_OPT % (1, "2", "0.75", "")).replace("mode:'reentry'", "mode:'orb'")
                                                          .replace("direction:'random'", "direction:'orb'")
                                                          .replace("seed:23", "seed:7")))
# ---- the last-hour candle: window mode, an exit minute, and stored decisions ----
WOPT = ("{entry:{mode:'window', winMin:900, winBars:5, direction:'window', exitMin:%s, seed:%d%s},"
        " trade:{stopPts:50, rr:0.65},"
        " acct:{balance:25000, contracts:1, pointValue:20, commission:1.75, slippage:0.25},"
        " rules:{trailDD:1000, freezeOffset:100, dailyCap:625, target:1250,"
        "        payoutAt:2100, ticket:65}}")
js.evaljs("var W = Core.runStrategy(SB, %s);" % (WOPT % ("949", 23, "")))
wrows = taken(js.evaljs("W.trades"))
check("the window rule trades at most once per session",
      len(wrows) <= len(SESS), "%d trades over %d sessions" % (len(wrows), len(SESS)))
check("every window entry is at 15:05",
      all(js.evaljs("SB.mins[%d]" % t["entry_bar"]) == 905 for t in wrows[:40]))
check("no window trade runs past the 15:49 bar",
      all(js.evaljs("SB.mins[%d]" % t["exit_bar"]) <= 949 for t in wrows))
check("a window trade's side is the 15:00-15:04 candle's direction",
      all(t["side"] == (1 if js.evaljs("SB.c[%d] - SB.o[%d]" % (t["entry_bar"] - 1, t["entry_bar"] - 5)) > 0 else -1)
          for t in wrows[:40]))
check("the window rule is deterministic: no seed dependence",
      js.evaljs("W.summary") == js.evaljs("Core.runStrategy(SB, %s).summary" % (WOPT % ("949", 7, ""))))
wclose = taken(js.evaljs("Core.runStrategy(SB, %s).trades" % (WOPT % ("null", 23, ""))))
check("without an exit minute the window trade may run to the session close",
      any(js.evaljs("SB.mins[%d]" % t["exit_bar"]) > 949 for t in wclose))
skipped = [t for t in js.evaljs("W.trades") if t.get("skipped")]
check("a flat signal candle is a skipped row, never a trade",
      all(t["reason"] == "flat signal candle" for t in skipped) and
      all(js.evaljs("SB.c[%d] - SB.o[%d]" % (t["entry_bar"] - 1, t["entry_bar"] - 5)) == 0 for t in skipped))
# a stored table: all +1 is the always-long arm; zeros stand aside; a gap is a violation
days = [S["day"] for S in SESS]
T1 = "{" + ",".join("'%s':1" % d for d in days) + "}"
T0 = "{" + ",".join("'%s':%d" % (d, 0 if i % 3 == 0 else 1) for i, d in enumerate(days)) + "}"
tab = taken(js.evaljs("Core.runStrategy(SB, %s).trades" % (WOPT % ("949", 23, ", sides:" + T1)).replace("direction:'window'", "direction:'table'")))
lng = taken(js.evaljs("Core.runStrategy(SB, %s).trades" % (WOPT % ("949", 23, "")).replace("direction:'window'", "direction:'long'")))
check("a table of all +1 is the always-long rule, trade for trade",
      len(tab) == len(lng) and all(a["exit"] == b["exit"] and a["side"] == 1 for a, b in zip(tab, lng)))
r0 = js.evaljs("Core.runStrategy(SB, %s)" % (WOPT % ("949", 23, ", sides:" + T0)).replace("direction:'window'", "direction:'table'"))
check("a stored 0 stands aside: a skipped row and no trade that day",
      all(t.get("reason") == "model abstained" for t in r0["trades"] if t.get("skipped")) and
      all(days.index(t["day"]) % 3 != 0 for t in r0["trades"] if not t.get("skipped")) and
      any(t.get("skipped") for t in r0["trades"]))
Tm = "{" + ",".join("'%s':1" % d for d in days[1:]) + "}"
rm = js.evaljs("Core.runStrategy(SB, %s)" % (WOPT % ("949", 23, ", sides:" + Tm)).replace("direction:'window'", "direction:'table'"))
check("a day with no stored decision is flagged and skipped, never a coin",
      len(rm["violations"]) >= 1 and any(t.get("reason") == "no model decision" for t in rm["trades"]))
js.evaljs("W = null;")

# ---- a table that is the schedule, with a stored [side, level] per entry ----
# (the Breakout Academy systems: a stop order that filled at a known minute and
# price). The level is checked against the tape independently here: every
# entry must sit inside its bar and the fill must be the level, or the open if
# the bar opened through it, plus one tick of slippage on the trade's side.
LOPT = ("{entry:{mode:'reentry', direction:'table', slotsFromTable:true, sides:%s, exitMin:949, seed:23},"
        " trade:{stopPts:50, rr:1e9},"
        " acct:{balance:25000, contracts:1, pointValue:20, commission:1.75, slippage:0.25},"
        " rules:{trailDD:1000, freezeOffset:100, dailyCap:625, target:1250,"
        "        payoutAt:2100, ticket:65}}")
lv = {}
for i, S in enumerate(SESS[:60]):
    a, b = S["a"], S["b"]
    k = a + 40 + (i % 7)                      # some minute inside the session
    if k >= b:
        continue
    side = 1 if i % 2 == 0 else -1
    px = float(H[k]) if side > 0 else float(L[k])     # a level the bar reached
    lv[S["day"]] = {str(int(MINS[k])): [side, round(px, 4)]}
LV = json.dumps(lv)
lr = js.evaljs("Core.runStrategy(SB, %s)" % (LOPT % LV))
lrows = taken(lr["trades"])
check("the table is the schedule: one trade per stored day, none elsewhere",
      len(lrows) == len(lv) and all(r["day"] in lv for r in lrows),
      "%d trades for %d stored days" % (len(lrows), len(lv)))
ok = True
for r in lrows:
    m = str(int(MINS[r["entry_bar"]]))
    side, px = lv[r["day"]][m]
    want = (max(px, O[r["entry_bar"]]) if side > 0 else min(px, O[r["entry_bar"]])) + 0.25 * side
    if r["side"] != side or abs(r["entry"] - want) > 1e-6:
        ok = False
check("each fill is at the stored level (or the open through it) plus slippage", ok)
check("no stored level was refused on the tape it was made from",
      not any(t.get("reason") == "stop level not in this bar" for t in lr["trades"]))
# a level outside its bar is refused, never filled at the open
bad = {d: {m: [v[0], v[1] + 5000]} for d, dm in lv.items() for m, v in dm.items()}
br = js.evaljs("Core.runStrategy(SB, %s)" % (LOPT % json.dumps(bad)))
check("a level the bar never reached is skipped with a reason and no trade",
      not taken(br["trades"]) and any(t.get("reason") == "stop level not in this bar" for t in br["trades"]))
# the coin on the same bars: random direction keeps the schedule and enters at the open
cr = js.evaljs("Core.runStrategy(SB, %s)" % (LOPT % LV).replace("direction:'table'", "direction:'random'"))
crows = taken(cr["trades"])
check("the coin on the same schedule trades the same bars at the open",
      len(crows) == len(lrows) and all(a["entry_bar"] == b["entry_bar"] for a, b in zip(crows, lrows)) and
      all(abs(r["entry"] - (O[r["entry_bar"]] + 0.25 * r["side"])) < 1e-6 for r in crows))
check("with rr 1e9 no trade ends on a favourable target of its own",
      all(r["why"] != "favourable" or r["capped"] for r in lrows))

print("\n--- dowOf / daysOfWeek / newsDays / tableSkipReason (the 'custom' strategy's engine seams) ---")
# dowOf: 0=Sun..6=Sat, checked against a handful of independently-known weekdays,
# including a leap day, without going through Python's own weekday() convention
# (Mon=0) so the test can't just mirror the same off-by-rotation bug both places.
KNOWN_DOW = [("2024-01-01", 1), ("2024-01-06", 6), ("2024-01-07", 0),
             ("2016-02-29", 1), ("2000-03-01", 3), ("2011-01-07", 5)]
dow_ok = all(js.evaljs("Core.dowOf('%s')" % d) == w for d, w in KNOWN_DOW)
check("dowOf matches known weekdays, including a leap day", dow_ok, str(KNOWN_DOW))

# daysOfWeek: restrict to Mondays only (JS dowOf convention: 1) and check every
# resulting trade's day really is a Monday, via Python's own independent weekday().
DOW_OPT = ("{entry:{mode:'reentry', startMin:600, slotMin:30, direction:'random', seed:23,"
           " daysOfWeek:[1]},"
           " trade:{stopPts:50, rr:1.0},"
           " acct:{balance:25000, contracts:1, pointValue:2, commission:0.75, slippage:0.25},"
           " rules:{trailDD:1000, freezeOffset:100, dailyCap:625, target:1250,"
           "        payoutAt:2100, ticket:65}}")
dow_rows = taken(js.evaljs("Core.runStrategy(SB, %s).trades" % DOW_OPT))
check("daysOfWeek:[1] trades only fall on a Monday",
      len(dow_rows) > 0 and all(datetime.date.fromisoformat(r["day"]).weekday() == 0 for r in dow_rows),
      "%d trades" % len(dow_rows))
mon_sessions = {d for d in days if datetime.date.fromisoformat(d).weekday() == 0}
check("daysOfWeek:[1] never trades a session outside that weekday set",
      all(r["day"] in mon_sessions for r in dow_rows))

# newsDays: an explicit {day: true} allow-list, independent of weekday
news_allow = {d: True for i, d in enumerate(days) if i % 5 == 0}
NEWS_OPT = DOW_OPT.replace("daysOfWeek:[1]", "newsDays:" + json.dumps(news_allow))
news_rows = taken(js.evaljs("Core.runStrategy(SB, %s).trades" % NEWS_OPT))
check("newsDays restricts trading to exactly the given day set",
      len(news_rows) > 0 and all(r["day"] in news_allow for r in news_rows),
      "%d trades" % len(news_rows))

# tableSkipReason: scoped to an explicit opt-in flag, not a blanket slotsFromTable
# check -- a suppressed slot (position still open) is pushed as a skipped row with
# the given reason only when the flag is set; existing table strategies never set it,
# so their ledgers cannot change even though they share the same slotsFromTable path.
multi = {}
for i, S in enumerate(SESS[:30]):
    a, b = S["a"], S["b"]
    m0, m1 = MINS[a] + 5, MINS[a] + 6   # two candidate minutes one bar apart
    if a + 6 >= b:
        continue
    multi[S["day"]] = {str(int(m0)): 1, str(int(m1)): 1}
MULTI = json.dumps(multi)
TS_OPT = ("{entry:{mode:'reentry', direction:'random', slotsFromTable:true, sides:%s,"
          " tableSkipReason:'position open at next news release', exitMin:960, seed:23,"
          " holdMin:120},"
          " trade:{stopPts:50, rr:1.0},"
          " acct:{balance:25000, contracts:1, pointValue:2, commission:0.75, slippage:0.25},"
          " rules:{trailDD:1000, freezeOffset:100, dailyCap:625, target:1250,"
          "        payoutAt:2100, ticket:65}}")
ts_res = js.evaljs("Core.runStrategy(SB, %s)" % (TS_OPT % MULTI))
ts_skips = [t for t in ts_res["trades"] if t.get("skipped") and t.get("reason") == "position open at next news release"]
check("a suppressed slotsFromTable candidate is a skipped row with the given reason when tableSkipReason is set",
      len(ts_skips) > 0, "%d such rows" % len(ts_skips))
# the very same table, WITHOUT the flag (as every existing table strategy calls it):
# the suppressed candidate is still silently skipped, never that reason, never a trade
NOFLAG_OPT = TS_OPT.replace(", tableSkipReason:'position open at next news release'", "")
noflag_res = js.evaljs("Core.runStrategy(SB, %s)" % (NOFLAG_OPT % MULTI))
check("without tableSkipReason the same suppression is silent, as bo_ti4/bo_hit41/bo_hit34 always saw it",
      not any(t.get("reason") == "position open at next news release" for t in noflag_res["trades"]))

# independence: slotsFromTable only ever reads the table's KEYS. Two tables with
# identical keys but different (garbage, non-[side,level]) values, direction:'random',
# same seed, must produce byte-identical trades -- turning "values aren't read" into a
# checked invariant rather than a read-once claim.
keys_only = {d: {"600": 1} for d in days[:80]}
garbage_a = {d: {"600": "not a real value"} for d in days[:80]}
garbage_b = {d: {"600": [999, "also not real", {"nested": True}]} for d in days[:80]}
IND_OPT = ("{entry:{mode:'reentry', direction:'random', slotsFromTable:true, sides:%s, exitMin:960, seed:23},"
           " trade:{stopPts:50, rr:1.0},"
           " acct:{balance:25000, contracts:1, pointValue:2, commission:0.75, slippage:0.25},"
           " rules:{trailDD:1000, freezeOffset:100, dailyCap:625, target:1250,"
           "        payoutAt:2100, ticket:65}}")
ind_a = js.evaljs("Core.runStrategy(SB, %s).trades" % (IND_OPT % json.dumps(garbage_a)))
ind_b = js.evaljs("Core.runStrategy(SB, %s).trades" % (IND_OPT % json.dumps(garbage_b)))
check("slotsFromTable values are never read when direction isn't 'table': garbage values, same trades",
      ind_a == ind_b, "%d vs %d trades" % (len(ind_a), len(ind_b)))

# no-snap-forward: a table entry at a minute with no matching bar in its session is
# dropped, never substituted with the nearest available bar -- a real look-ahead-bias
# risk if it snapped forward, checked here rather than assumed from reading barAt().
no_bar = {}
for S in SESS[:20]:
    a = S["a"]
    m = int(MINS[a]) - 100   # well before the session opens; barAt must not find it
    if m < 0:
        continue
    no_bar[S["day"]] = {str(m): 1}
NOBAR_OPT = TS_OPT.replace(", holdMin:120", "").replace(
    ", tableSkipReason:'position open at next news release'", "")
nobar_res = js.evaljs("Core.runStrategy(SB, %s)" % (NOBAR_OPT % json.dumps(no_bar)))
check("a table minute with no matching bar produces zero trades that day, never a snapped-forward one",
      len(taken(nobar_res["trades"])) == 0 and len(no_bar) > 0, "%d candidate days" % len(no_bar))

js.evaljs("SB = null;")

print("\n--- live Breakout entries ---")
# The offline Breakout replays (bo_ti4/bo_hit41/bo_hit34) read a table
# bo_pack.py baked from one historical tape; liveBreakoutSides computes the
# same two systems fresh from whatever bars are loaded. wilderDxAdx is
# already cross-checked against an independent Python RMA above, so this
# checks the wiring around it: the window, the gate, the level, and that
# every stored fill is a real, reachable price on the actual tape.
BAR_AT = {}
for S in SESS:
    for i in range(S["a"], S["b"] + 1):
        BAR_AT[(S["day"], int(MINS[i]))] = i


def bad_fills(table):
    n = 0
    for day, slot in table.items():
        for mstr, sidelvl in slot.items():
            lvl = sidelvl[1]
            i = BAR_AT.get((day, int(mstr)))
            if i is None or not (L[i] - 1e-6 <= lvl <= H[i] + 1e-6):
                n += 1
    return n


HIT = ("{system:'hitter', side:'long', winStart:570, winEnd:930, n:41, "
       "adxPeriod:50, adxThreshold:17.5, adxDirection:'below'}")
hit = js.evaljs("Core.liveBreakoutSides(B, %s)" % HIT)
check("the live Hitter (as-published settings, on the loaded tape) fires at least once",
      len(hit) > 0, "%d days" % len(hit))
check("at most one entry a day", all(len(v) == 1 for v in hit.values()))
nfills = sum(len(v) for v in hit.values())
check("every stored Hitter fill is a real level inside its own bar (%d fills)" % nfills,
      bad_fills(hit) == 0)
hit_never = js.evaljs("Core.liveBreakoutSides(B, %s)" % HIT.replace("adxThreshold:17.5", "adxThreshold:-1"))
check("an impossible ADX gate (below -1) fires never", len(hit_never) == 0)
hit_always = js.evaljs("Core.liveBreakoutSides(B, %s)" % HIT.replace("adxThreshold:17.5", "adxThreshold:101"))
check("loosening the ADX gate only adds days, never removes them",
      len(hit_always) >= len(hit) and set(hit.keys()) <= set(hit_always.keys()))
hit_short = js.evaljs("Core.liveBreakoutSides(B, %s)" % HIT.replace("side:'long'", "side:'short'"))
diverges = any(hit[d][m][1] != hit_short[d][m][1]
               for d in hit if d in hit_short for m in hit[d] if m in hit_short[d])
check("flipping the side changes the levels it trades",
      diverges or set(hit.keys()) != set(hit_short.keys()))

TI = ("{system:'trendindi', side:'long', winStart:570, winEnd:930, "
      "fraction:4, dxPeriod:100, dxShift:20, dxThreshold:35}")
ti = js.evaljs("Core.liveBreakoutSides(B, %s)" % TI)
check("the live Trend indi 2 (as-published settings) fires at least once",
      len(ti) > 0, "%d days" % len(ti))
check("at most one entry a day", all(len(v) == 1 for v in ti.values()))
check("every stored Trend-indi-2 fill is a real level inside its own bar (%d fills)" %
      sum(len(v) for v in ti.values()), bad_fills(ti) == 0)
check("Hitter and Trend indi 2 are independent systems, not the same day set",
      set(hit.keys()) != set(ti.keys()))

print("\n--- live Breakout entries respect the trading window ---")
# The panel pins liveBreakoutSides to 09:00-15:30 New York (build_viewer3.py's
# LIVE_BO_WIN_START/END); this proves why that matters. A synthetic session,
# flat except two engineered Highest(C,1) breakouts: one overnight (bar 1,
# minute 30) and one in the published window (bar 18, minute 540 = 09:00).
# adxThreshold is left permissive so only the window decides which fires.
# With no window, the overnight bar comes first chronologically, fires, and
# "one entry a day" means the real 09:00 signal is never even reached.
TF, NBARS = 30, 20
SYN_N = NBARS * TF
so, sh, sl, sc = [100.0] * SYN_N, [100.2] * SYN_N, [99.8] * SYN_N, [100.0] * SYN_N
smins = list(range(SYN_N))


def bar_rows(idx):
    return range(idx * TF, idx * TF + TF)


r1 = list(bar_rows(1))
sc[r1[-1]] = 105.0
touch_early = list(bar_rows(2))[4]
sh[touch_early] = 105.5
r18 = list(bar_rows(18))
sc[r18[-1]] = 110.0
touch_late = list(bar_rows(19))[4]
sh[touch_late] = 110.5
SYN_B = {"n": SYN_N, "o": so, "h": sh, "l": sl, "c": sc, "mins": smins,
          "sessions": [{"day": "2024-01-01", "a": 0, "b": SYN_N - 1}]}
GATE = "n:1, adxPeriod:1, adxThreshold:1000, adxDirection:'below'"
r_open = js.evaljs("Core.liveBreakoutSides(%s, {system:'hitter', side:'long', "
                    "winStart:-1e15, winEnd:1e15, %s})" % (json.dumps(SYN_B), GATE))
r_fixed = js.evaljs("Core.liveBreakoutSides(%s, {system:'hitter', side:'long', "
                     "winStart:540, winEnd:930, %s})" % (json.dumps(SYN_B), GATE))
check("without a window the overnight bar (signal at 00:30) wins the day's one entry",
      "2024-01-01" in r_open and str(touch_early) in r_open["2024-01-01"], str(r_open))
check("with the published 09:00-15:30 window the overnight bar is skipped and "
      "the real 09:00 signal fires instead",
      "2024-01-01" in r_fixed and str(touch_late) in r_fixed["2024-01-01"], str(r_fixed))

print("\n--- magnet ---")
m = js.evaljs("var A1 = Core.aggregate(B,1); "
              "[Core.magnet(A1, 10, %f), Core.magnet(A1, 10, %f)]" % (H[10] + 3, L[10] - 3))
check("magnet snaps to the bar high", abs(m[0] - H[10]) < 1e-6)
check("magnet snaps to the bar low", abs(m[1] - L[10]) < 1e-6)

print("\n" + "=" * 62)
print(f"  {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("  FAILING:")
    for f in FAIL:
        print("    - " + f)
print("=" * 62)
