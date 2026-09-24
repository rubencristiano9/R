/* =====================================================================
   TAPE READER -- CORE
   Every piece of logic that can be wrong in a way you would not see.
   Deliberately ES5 so it runs unchanged in the browser AND in a headless
   engine, which is how test_core.py exercises it against real NQ data.
   No DOM, no canvas, no globals: pure functions only.
   ===================================================================== */
var Core = (function () {

  /* ---------- binary search: first index with arr[i] >= v ---------- */
  function lowerBound(arr, v, len) {
    var lo = 0, hi = (len === undefined ? arr.length : len);
    while (lo < hi) { var m = (lo + hi) >> 1; if (arr[m] < v) lo = m + 1; else hi = m; }
    return lo;
  }

  /* ---------- session lookup: which session contains this bar ---------- */
  function sessionOf(sessions, i) {
    var lo = 0, hi = sessions.length - 1;
    while (lo < hi) { var m = (lo + hi) >> 1; if (sessions[m].b < i) lo = m + 1; else hi = m; }
    return lo;
  }

  /* ---------- timeframe aggregation ----------
     tf is a count of base bars. Aggregation NEVER crosses a session
     boundary: a 60-minute bar cannot span two trading days. Returns the
     aggregated series plus map[], the base->aggregated index, so trades
     recorded on 1-minute bars still land on the right candle.            */
  /* At 1m the map is the identity, and rebuilding a 315,900-element array for
     it on every rebuild() was pure waste -- an allocation and a full pass to
     produce map[j] === j. Build it once per length and hand out the same one.
     Int32Array rather than Array: a quarter of the memory, and every consumer
     only ever indexes it. */
  var IDENT = null;
  function identity(n) {
    if (!IDENT || IDENT.length !== n) {
      IDENT = new Int32Array(n);
      for (var q = 0; q < n; q++) IDENT[q] = q;
    }
    return IDENT;
  }

  function aggregate(B, tf) {
    if (tf <= 1) {
      var idn = identity(B.n);
      return { n: B.n, o: B.o, h: B.h, l: B.l, c: B.c, v: B.v, mins: B.mins,
               sessions: B.sessions, map: idn, src: idn, tf: 1 };
    }
    var o = [], h = [], l = [], c = [], v = [], mins = [], src = [], sess = [];
    var hasV = !!B.v;
    var map = new Array(B.n);
    var k = 0;
    for (var s = 0; s < B.sessions.length; s++) {
      var S = B.sessions[s], start = k;
      for (var i = S.a; i <= S.b; i += tf) {
        var e = Math.min(S.b, i + tf - 1);
        var hi = B.h[i], lo = B.l[i], vol = 0;
        for (var j = i; j <= e; j++) {
          if (B.h[j] > hi) hi = B.h[j];
          if (B.l[j] < lo) lo = B.l[j];
          if (hasV) vol += B.v[j];      /* volume SUMS across the candle */
          map[j] = k;
        }
        o.push(B.o[i]); h.push(hi); l.push(lo); c.push(B.c[e]);
        if (hasV) v.push(vol);
        mins.push(B.mins[i]); src.push(i);
        k++;
      }
      sess.push({ day: S.day, a: start, b: k - 1 });
    }
    return { n: k, o: o, h: h, l: l, c: c, v: hasV ? v : undefined,
             mins: mins, sessions: sess, map: map, src: src, tf: tf };
  }

  /* ---------- Heikin-Ashi ----------
     haC = (o+h+l+c)/4 ; haO = previous (haO+haC)/2, seeded with (o+c)/2 */
  function heikinAshi(B) {
    var n = B.n, o = new Array(n), h = new Array(n), l = new Array(n), c = new Array(n);
    for (var i = 0; i < n; i++) {
      c[i] = (B.o[i] + B.h[i] + B.l[i] + B.c[i]) / 4;
      o[i] = i === 0 ? (B.o[0] + B.c[0]) / 2 : (o[i - 1] + c[i - 1]) / 2;
      h[i] = Math.max(B.h[i], o[i], c[i]);
      l[i] = Math.min(B.l[i], o[i], c[i]);
    }
    return { n: n, o: o, h: h, l: l, c: c, mins: B.mins, sessions: B.sessions,
             map: B.map, src: B.src, tf: B.tf, ha: true };
  }

  /* ---------- moving averages ---------- */
  function sma(src, p) {
    var n = src.length, out = new Array(n), sum = 0;
    for (var i = 0; i < n; i++) {
      sum += src[i];
      if (i >= p) sum -= src[i - p];
      out[i] = i >= p - 1 ? sum / p : null;
    }
    return out;
  }
  function ema(src, p) {
    var n = src.length, out = new Array(n), k = 2 / (p + 1), prev = null, sum = 0;
    for (var i = 0; i < n; i++) {
      if (i < p - 1) { sum += src[i]; out[i] = null; continue; }
      if (i === p - 1) { sum += src[i]; prev = sum / p; out[i] = prev; continue; }
      prev = src[i] * k + prev * (1 - k);
      out[i] = prev;
    }
    return out;
  }
  /* Session-anchored VWAP: sum(typical x volume) / sum(volume), re-anchored at
     each session open. When the loaded data carries no volume column it falls
     back to an unweighted typical-price average, and says so through .weighted
     rather than passing itself off as a true VWAP. */
  function vwapSession(B) {
    var n = B.n, out = new Array(n), hasV = !!B.v;
    for (var s = 0; s < B.sessions.length; s++) {
      var S = B.sessions[s], num = 0, den = 0;
      for (var i = S.a; i <= S.b; i++) {
        var tp = (B.h[i] + B.l[i] + B.c[i]) / 3;
        var w = hasV ? B.v[i] : 1;
        num += tp * w; den += w;
        out[i] = den > 0 ? num / den : tp;
      }
    }
    out.weighted = hasV;
    return out;
  }

  /* Rolling average volume, for the reference line on the volume pane. */
  function volumeAvg(B, p) {
    if (!B.v) return null;
    return sma(B.v, p);
  }
  function bollinger(src, p, k) {
    var mid = sma(src, p), n = src.length;
    var up = new Array(n), dn = new Array(n);
    for (var i = 0; i < n; i++) {
      if (mid[i] === null) { up[i] = dn[i] = null; continue; }
      var v = 0;
      for (var j = i - p + 1; j <= i; j++) { var d = src[j] - mid[i]; v += d * d; }
      var sd = Math.sqrt(v / p);
      up[i] = mid[i] + k * sd; dn[i] = mid[i] - k * sd;
    }
    return { mid: mid, up: up, dn: dn };
  }
  function atr(B, p) {
    var n = B.n, tr = new Array(n);
    for (var i = 0; i < n; i++) {
      tr[i] = i === 0 ? B.h[0] - B.l[0]
        : Math.max(B.h[i] - B.l[i],
                   Math.abs(B.h[i] - B.c[i - 1]),
                   Math.abs(B.l[i] - B.c[i - 1]));
    }
    return sma(tr, p);
  }

  /* Wilder's DX and ADX (his RMA-smoothed DM/TR give DI+/DI-, DX =
     100|DI+-DI-|/(DI++DI-), ADX = RMA of DX) -- byte-for-byte the same
     recursion as bo_data.py's wilder_dx_adx, checked against it in
     test_core.py so the live Breakout entries below read the same trend
     strength the offline study did. h/l/c are one series with no session
     gaps (30-minute bars here; the caller builds them per session). */
  function wilderDxAdx(h, l, c, period) {
    var n = h.length, i;
    var dx = new Array(n), adx = new Array(n);
    for (i = 0; i < n; i++) { dx[i] = null; adx[i] = null; }
    if (n < period) return { dx: dx, adx: adx };
    var pdm = new Array(n), mdm = new Array(n), tr = new Array(n);
    for (i = 0; i < n; i++) {
      var up = i === 0 ? 0 : h[i] - h[i - 1];
      var dn = i === 0 ? 0 : l[i - 1] - l[i];
      pdm[i] = (up > dn && up > 0) ? up : 0;
      mdm[i] = (dn > up && dn > 0) ? dn : 0;
      var pc = i === 0 ? c[0] : c[i - 1];
      tr[i] = Math.max(h[i] - l[i], Math.abs(h[i] - pc), Math.abs(l[i] - pc));
    }
    function rma(x) {
      var out = new Array(n), j, sum = 0;
      for (j = 0; j < n; j++) out[j] = null;
      for (j = 0; j < period; j++) sum += x[j];
      out[period - 1] = sum / period;
      var a = 1 / period;
      for (j = period; j < n; j++) out[j] = out[j - 1] + a * (x[j] - out[j - 1]);
      return out;
    }
    var atrR = rma(tr), spdm = rma(pdm), smdm = rma(mdm);
    for (i = 0; i < n; i++) {
      if (atrR[i] === null) continue;
      var pdi = 100 * spdm[i] / atrR[i], mdi = 100 * smdm[i] / atrR[i];
      var v = 100 * Math.abs(pdi - mdi) / (pdi + mdi);
      dx[i] = isFinite(v) ? v : 0;         /* matches np.nan_to_num(dx, nan=0) */
    }
    for (i = 0; i < period; i++) dx[i] = null;   /* matches dx[:period] = nan */
    var start = 2 * period - 1;
    if (n > start) {
      var s = 0;
      for (i = period; i <= start; i++) s += dx[i];
      adx[start] = s / period;
      var a2 = 1 / period;
      for (i = start + 1; i < n; i++) adx[i] = adx[i - 1] + a2 * (dx[i] - adx[i - 1]);
    }
    return { dx: dx, adx: adx };
  }

  /* ---------- oscillators and channels ----------
     Wilder's RSI: the average gain and loss are smoothed with his own
     1/period recursion, not a simple mean, which is why RSI(14) here matches
     a platform and a naive rolling average would not. */
  function rsi(src, p) {
    var n = src.length, out = new Array(n), i, g = 0, l = 0;
    for (i = 0; i < n; i++) out[i] = null;
    if (n <= p) return out;
    for (i = 1; i <= p; i++) {
      var d = src[i] - src[i - 1];
      if (d >= 0) g += d; else l -= d;
    }
    g /= p; l /= p;
    out[p] = l === 0 ? 100 : 100 - 100 / (1 + g / l);
    for (i = p + 1; i < n; i++) {
      var ch = src[i] - src[i - 1];
      g = (g * (p - 1) + (ch > 0 ? ch : 0)) / p;
      l = (l * (p - 1) + (ch < 0 ? -ch : 0)) / p;
      out[i] = l === 0 ? 100 : 100 - 100 / (1 + g / l);
    }
    return out;
  }

  function macd(src, fast, slow, sig) {
    var f = ema(src, fast), sl = ema(src, slow), n = src.length;
    var line = new Array(n), i;
    for (i = 0; i < n; i++)
      line[i] = (f[i] === null || sl[i] === null) ? null : f[i] - sl[i];
    var firstIdx = -1;
    for (i = 0; i < n; i++) if (line[i] !== null) { firstIdx = i; break; }
    var sigOut = new Array(n), hist = new Array(n);
    for (i = 0; i < n; i++) { sigOut[i] = null; hist[i] = null; }
    if (firstIdx >= 0) {
      var dense = line.slice(firstIdx);
      var se = ema(dense, sig);
      for (i = 0; i < se.length; i++) {
        sigOut[firstIdx + i] = se[i];
        hist[firstIdx + i] = se[i] === null ? null : dense[i] - se[i];
      }
    }
    return { macd: line, signal: sigOut, hist: hist };
  }

  /* Stochastic %K over the high/low range, %D as an SMA of %K. */
  function stochastic(B, kP, dP, smooth) {
    var n = B.n, raw = new Array(n), i, j;
    for (i = 0; i < n; i++) {
      if (i < kP - 1) { raw[i] = null; continue; }
      var hh = -Infinity, ll = Infinity;
      for (j = i - kP + 1; j <= i; j++) {
        if (B.h[j] > hh) hh = B.h[j];
        if (B.l[j] < ll) ll = B.l[j];
      }
      raw[i] = hh === ll ? 50 : (B.c[i] - ll) / (hh - ll) * 100;
    }
    var k = smooth > 1 ? smaNull(raw, smooth) : raw;
    return { k: k, d: smaNull(k, dP) };
  }

  /* SMA that tolerates leading nulls -- the plain sma() would poison its
     running sum with them. */
  function smaNull(src, p) {
    var n = src.length, out = new Array(n), i, j;
    for (i = 0; i < n; i++) {
      if (i < p - 1) { out[i] = null; continue; }
      var sum = 0, ok = true;
      for (j = i - p + 1; j <= i; j++) {
        if (src[j] === null || src[j] === undefined) { ok = false; break; }
        sum += src[j];
      }
      out[i] = ok ? sum / p : null;
    }
    return out;
  }

  function donchian(B, p) {
    var n = B.n, up = new Array(n), dn = new Array(n), mid = new Array(n), i, j;
    for (i = 0; i < n; i++) {
      if (i < p - 1) { up[i] = dn[i] = mid[i] = null; continue; }
      var hh = -Infinity, ll = Infinity;
      for (j = i - p + 1; j <= i; j++) {
        if (B.h[j] > hh) hh = B.h[j];
        if (B.l[j] < ll) ll = B.l[j];
      }
      up[i] = hh; dn[i] = ll; mid[i] = (hh + ll) / 2;
    }
    return { up: up, mid: mid, dn: dn };
  }

  function keltner(B, p, mult) {
    var mid = ema(B.c, p), a = atr(B, p), n = B.n;
    var up = new Array(n), dn = new Array(n);
    for (var i = 0; i < n; i++) {
      if (mid[i] === null || a[i] === null) { up[i] = dn[i] = null; continue; }
      up[i] = mid[i] + mult * a[i];
      dn[i] = mid[i] - mult * a[i];
    }
    return { up: up, mid: mid, dn: dn };
  }

  /* Rate of change, in percent. */
  function roc(src, p) {
    var n = src.length, out = new Array(n);
    for (var i = 0; i < n; i++)
      out[i] = i < p || src[i - p] === 0 ? null : (src[i] - src[i - p]) / Math.abs(src[i - p]) * 100;
    return out;
  }

  /* ---------- price range over a visible window ---------- */
  function priceRange(B, a, b, pad) {
    a = Math.max(0, Math.floor(a)); b = Math.min(B.n - 1, Math.ceil(b));
    var lo = Infinity, hi = -Infinity;
    for (var i = a; i <= b; i++) { if (B.l[i] < lo) lo = B.l[i]; if (B.h[i] > hi) hi = B.h[i]; }
    if (!isFinite(lo)) return { lo: 0, hi: 1 };
    /* `span * pad || 1` was wrong: a legitimate pad of 0 is falsy, so it
       silently became 1. Only a genuinely flat window needs the fallback. */
    var span = hi - lo;
    var p = span * (pad === undefined ? 0.06 : pad);
    if (span === 0) p = 1;
    return { lo: lo - p, hi: hi + p };
  }

  /* ---------- bucketed price range ----------
     priceRange() scans every visible bar, which is fine for a day and ruinous
     for the whole series: measured at 47 ms for 315,900 bars, and the render
     path asks for it several times per mouse move. Precomputing the min/max of
     fixed-size blocks lets a wide view read whole blocks and scan only the two
     partial ends, turning O(bars) into O(bars/size + 2*size).                */
  function buildBuckets(B, size) {
    size = size || 512;
    var nb = Math.ceil(B.n / size);
    var lo = new Array(nb), hi = new Array(nb), k, i, e, a, b;
    for (k = 0; k < nb; k++) {
      a = Infinity; b = -Infinity;
      e = Math.min(B.n, (k + 1) * size);
      for (i = k * size; i < e; i++) {
        if (B.l[i] < a) a = B.l[i];
        if (B.h[i] > b) b = B.h[i];
      }
      lo[k] = a; hi[k] = b;
    }
    return { size: size, lo: lo, hi: hi, n: B.n };
  }

  function priceRangeFast(B, bk, a, b, pad) {
    if (!bk || bk.n !== B.n) return priceRange(B, a, b, pad);
    a = Math.max(0, Math.floor(a));
    b = Math.min(B.n - 1, Math.ceil(b));
    if (b < a) return priceRange(B, a, b, pad);
    var sz = bk.size, ka = Math.floor(a / sz), kb = Math.floor(b / sz);
    var lo = Infinity, hi = -Infinity, i;
    if (kb - ka < 2) {
      for (i = a; i <= b; i++) { if (B.l[i] < lo) lo = B.l[i]; if (B.h[i] > hi) hi = B.h[i]; }
    } else {
      for (var k = ka + 1; k < kb; k++) {
        if (bk.lo[k] < lo) lo = bk.lo[k];
        if (bk.hi[k] > hi) hi = bk.hi[k];
      }
      for (i = a; i < (ka + 1) * sz; i++) { if (B.l[i] < lo) lo = B.l[i]; if (B.h[i] > hi) hi = B.h[i]; }
      for (i = kb * sz; i <= b; i++) { if (B.l[i] < lo) lo = B.l[i]; if (B.h[i] > hi) hi = B.h[i]; }
    }
    if (!isFinite(lo)) return { lo: 0, hi: 1 };
    var span = hi - lo;
    var p = span * (pad === undefined ? 0.06 : pad);
    if (span === 0) p = 1;
    return { lo: lo - p, hi: hi + p };
  }

  /* ---------- trades visible in a window ----------
     BOTH arrays must already be in the same index space as a and b, i.e. the
     aggregated view. An earlier version took the trade objects and read
     t.entry_bar / t.exit_bar off them, which are BASE indices: at 1-minute the
     two spaces coincide and it worked, but at 1-hour the base indices are ~60x
     larger than the view window, the loop broke on its first iteration and
     almost every trade vanished from the chart.

     An entry of -1 means the trade was removed by a filter and is skipped.   */
  function visibleTrades(entries, exits, a, b, maxspan) {
    var out = [], n = entries.length;
    if (!n) return out;
    var i = lowerBound(entries, a - maxspan);
    if (i > 0) i--;
    for (; i < n; i++) {
      if (entries[i] < 0) continue;
      if (entries[i] > b) break;
      if (exits[i] >= a) out.push(i);
    }
    return out;
  }

  /* ---------- restrict the series to a time-of-day window ----------
     Keeps bars with from <= minute-of-day <= to, so you can strip overnight or
     look only at the RTH session. Returns the filtered series PLUS:
       fwd[i]  base index -> filtered index, or -1 if the bar was dropped
       back[j] filtered index -> base index
     Trades are remapped through fwd; one whose entry bar was dropped is
     marked -1 and simply stops being drawn, rather than silently sliding onto
     the wrong candle.                                                        */
  function timeFilter(B, from, to) {
    var n = B.n, o = [], h = [], l = [], c = [], v = [], mins = [], back = [];
    var fwd = new Array(n), hasV = !!B.v, i;
    var days = B.days ? [] : null;
    for (i = 0; i < n; i++) {
      var m = B.mins[i];
      if (m < from || m > to) { fwd[i] = -1; continue; }
      fwd[i] = back.length;
      back.push(i);
      o.push(B.o[i]); h.push(B.h[i]); l.push(B.l[i]); c.push(B.c[i]);
      if (hasV) v.push(B.v[i]);
      mins.push(m);
      if (days) days.push(B.days[i]);
    }
    /* rebuild sessions over the surviving bars */
    var sess = [], cur = null;
    for (var j = 0; j < back.length; j++) {
      var si = sessionOf(B.sessions, back[j]);
      var day = B.sessions[si].day;
      if (!cur || cur.day !== day) { cur = { day: day, a: j, b: j }; sess.push(cur); }
      else cur.b = j;
    }
    return { n: back.length, o: o, h: h, l: l, c: c, v: hasV ? v : undefined,
             mins: mins, sessions: sess, days: days, fwd: fwd, back: back,
             filtered: true };
  }

  /* ---------- where a time-of-day mark falls inside each session ----------
     Returns the first bar of every session at or after the given minute, so a
     vertical rule can be drawn at, say, the 09:30 RTH open on every day.     */
  function timeMarks(B, minute, a, b) {
    var out = [];
    for (var s = 0; s < B.sessions.length; s++) {
      var S = B.sessions[s];
      if (S.b < a || S.a > b) continue;
      for (var i = S.a; i <= S.b; i++) {
        if (B.mins[i] >= minute) { out.push(i); break; }
      }
    }
    return out;
  }

  /* ---------- backtest statistics ---------- */
  function tradeStats(trades) {
    var n = trades.length;
    if (!n) return { n: 0 };
    var wins = 0, losses = 0, gp = 0, gl = 0, net = 0;
    var peak = 0, dd = 0, cum = 0, eq = new Array(n);
    var run = 0, bestRun = 0, worstRun = 0;
    for (var i = 0; i < n; i++) {
      var p = trades[i].pnl;
      net += p; cum += p; eq[i] = cum;
      if (p > 0) { wins++; gp += p; run = run > 0 ? run + 1 : 1; }
      else if (p < 0) { losses++; gl -= p; run = run < 0 ? run - 1 : -1; }
      if (run > bestRun) bestRun = run;
      if (run < worstRun) worstRun = run;
      if (cum > peak) peak = cum;
      if (peak - cum > dd) dd = peak - cum;
    }
    var avgW = wins ? gp / wins : 0, avgL = losses ? gl / losses : 0;
    return {
      n: n, wins: wins, losses: losses,
      winRate: wins / n,
      net: net,
      grossProfit: gp, grossLoss: gl,
      profitFactor: gl > 0 ? gp / gl : (gp > 0 ? Infinity : 0),
      expectancy: net / n,
      avgWin: avgW, avgLoss: avgL,
      payoff: avgL > 0 ? avgW / avgL : 0,
      maxDrawdown: dd,
      bestStreak: bestRun, worstStreak: worstRun,
      equity: eq
    };
  }

  /* ---------- account simulation ----------
     Replays the loaded trades against a starting balance, tracking UNREALISED
     equity bar by bar rather than only booking the result at the exit.

     The reason to do it this way: a stop loss is a price, but liquidation is an
     equity level, and the two are not the same thing. If the account runs out
     of money before price reaches the stop, the position closes THERE. So the
     effective adverse distance is

         min(the trade's own stop, the move that takes equity to the floor)

     and with enough size the second term is the binding one. That case is
     invisible if you only book P&L at the exit, which is why an equity curve
     built from closed trades can look survivable when the account was not.

     opts: {balance, floor, sizeMode:'fixed'|'risk', contracts, riskPct,
            pointValue, commission, slippage}
     Rows also carry MAE and MFE in points -- how far each trade ran against and
     for you -- which the entry/exit pair alone cannot tell you.              */
  function simulateAccount(B, trades, entryIdx, exitIdx, opts) {
    var o = opts || {};
    var start = o.balance === undefined ? 25000 : o.balance;
    var bal = start;
    var floor = o.floor === undefined ? 0 : o.floor;
    var pv = o.pointValue === undefined ? 2 : o.pointValue;
    var comm = o.commission === undefined ? 0 : o.commission;
    var slip = o.slippage === undefined ? 0 : o.slippage;
    var rows = [], i;
    var peak = bal, maxDD = 0, forced = 0, skipped = 0, wins = 0, losses = 0;
    var stopped = false, deadAt = -1;   /* finished trading, for any reason */
    var blownUp = false;                /* specifically: the floor was breached */

    /* ---- evaluation rules (a prop-firm style assessment) ----
       PASS  reach +target while never booking more than dailyCap in one day
       FAIL  balance touches the drawdown floor
       The floor trails the highest END-OF-DAY balance by trailDD and freezes
       once it has risen freezeOffset above the start, which is what makes the
       early days of an evaluation the dangerous ones.                        */
    var ev = o.evaluation || { on: false };
    var floorNow = floor;
    var freezeLevel = start + (ev.freezeOffset === undefined ? 100 : ev.freezeOffset);
    if (ev.on) floorNow = start - (ev.trailDD === undefined ? 1000 : ev.trailDD);
    var curDay = -1, dayPnL = 0, dayCount = 0, capHits = 0, bestDay = -Infinity;
    var passed = false, passedAt = -1, passedDays = 0;

    for (i = 0; i < trades.length; i++) {
      var t = trades[i], a = entryIdx[i], b = exitIdx[i];
      if (stopped || a < 0 || b < 0 || a >= B.n || b >= B.n) {
        skipped++;
        rows.push({ i: i, skipped: true, bal: bal, size: 0 });
        continue;
      }
      /* day boundaries drive both the consistency cap and the trailing floor */
      if (ev.on) {
        var sIdx = sessionOf(B.sessions, a);
        if (sIdx !== curDay) {
          if (curDay >= 0) {
            if (dayPnL > bestDay) bestDay = dayPnL;
            /* the floor ratchets on the END-OF-DAY balance, then freezes */
            var lifted = bal - (ev.trailDD === undefined ? 1000 : ev.trailDD);
            if (lifted > floorNow) floorNow = lifted;
            if (floorNow > freezeLevel) floorNow = freezeLevel;
          }
          curDay = sIdx; dayPnL = 0; dayCount++;
        }
        if (dayPnL >= (ev.dailyCap === undefined ? 625 : ev.dailyCap) - 1e-9) {
          skipped++;
          rows.push({ i: i, skipped: true, reason: 'daily cap reached',
                      bal: bal, size: 0, day: sIdx });
          continue;
        }
      }

      var side = t.side >= 0 ? 1 : -1;
      var entry = t.entry;
      var stopDist = Math.abs(t.stop_px - entry);

      var size;
      if (o.sizeMode === 'risk' && stopDist > 0) {
        size = Math.floor((bal - floor) * (o.riskPct || 1) / 100 / (stopDist * pv));
      } else {
        size = o.contracts === undefined ? 1 : o.contracts;
      }
      if (!(size >= 1)) {
        skipped++;
        rows.push({ i: i, skipped: true, reason: 'size 0', bal: bal, size: 0 });
        continue;
      }

      var perPoint = size * pv;
      var room = bal - floorNow;
      /* Liquidation has to leave room for the cost of GETTING OUT. Solving
             -room = (-d - 2*slip) * perPoint - 2*comm*size
         for d gives the distance at which the balance lands exactly on the
         floor once the exit is paid for. Pricing only the move, as an earlier
         version did, closed the position a few dollars late and left the
         balance BELOW the floor -- a $1,000 account finishing at -$4.00
         instead of at 0. */
      var exitCost = 2 * slip * perPoint + 2 * comm * size;
      var liqDist = perPoint > 0 ? (room - exitCost) / perPoint : Infinity;
      if (!(liqDist > 0)) {
        skipped++;
        rows.push({ i: i, skipped: true, reason: 'costs exceed remaining equity',
                    bal: bal, size: 0 });
        continue;
      }

      var mae = 0, mfe = 0, exitPx = t.exit, forcedHere = false, exitBar = b;
      for (var k = a; k <= b; k++) {
        var adv = side > 0 ? (entry - B.l[k]) : (B.h[k] - entry);
        var fav = side > 0 ? (B.h[k] - entry) : (entry - B.l[k]);
        if (adv > mae) mae = adv;
        if (fav > mfe) mfe = fav;
        if (adv >= liqDist) {
          exitPx = side > 0 ? entry - liqDist : entry + liqDist;
          forcedHere = true; exitBar = k; mae = liqDist;
          break;
        }
      }

      var pts = (exitPx - entry) * side - 2 * slip;
      var pnl = pts * perPoint - comm * size * 2;
      var capped = false;
      if (ev.on) {
        /* the consistency rule caps what a single day may BOOK; you close at
           the cap rather than being penalised for exceeding it */
        var cap = ev.dailyCap === undefined ? 625 : ev.dailyCap;
        if (dayPnL + pnl > cap) { pnl = cap - dayPnL; capped = true; capHits++; }
        /* ...and at the pass line: reaching the target ends the evaluation,
           so nothing past it is ever booked or left at risk */
        var passLine = start + (ev.target === undefined ? 1250 : ev.target);
        if (!passed && bal + pnl > passLine) { pnl = passLine - bal; capped = true; }
        dayPnL += pnl;
      }
      bal += pnl;
      if (bal > peak) peak = bal;
      if (peak - bal > maxDD) maxDD = peak - bal;
      if (pnl > 0) wins++; else if (pnl < 0) losses++;
      if (forcedHere) forced++;

      rows.push({
        i: i, size: size, side: side, entry: entry, exit: exitPx,
        exitBar: exitBar, forced: forcedHere, capped: capped,
        mae: mae, mfe: mfe, pts: pts, pnl: pnl, bal: bal,
        dayPnL: ev.on ? dayPnL : undefined, floor: floorNow,
        liqPrice: side > 0 ? entry - liqDist : entry + liqDist,
        liqDist: liqDist, stopDist: stopDist,
        stopReachable: liqDist >= stopDist
      });

      if (ev.on && !passed && bal >= start + (ev.target === undefined ? 1250 : ev.target)) {
        passed = true; passedAt = i; passedDays = dayCount;
      }
      if (bal <= floorNow + 1e-9) { stopped = true; blownUp = true; deadAt = i; }
      if (passed && ev.stopAtPass !== false) { stopped = true; }
    }

    var taken = 0;
    for (i = 0; i < rows.length; i++) if (!rows[i].skipped) taken++;
    return {
      rows: rows,
      summary: {
        start: start, end: bal, peak: peak, maxDrawdown: maxDD,
        pnl: bal - start,
        returnPct: start ? (bal - start) / start * 100 : 0,
        taken: taken, skipped: skipped, forced: forced,
        wins: wins, losses: losses,
        winRate: taken ? wins / taken : 0,
        dead: blownUp, blownUp: blownUp, stopped: stopped, deadAt: deadAt,
        evaluation: ev.on ? {
          passed: passed, passedAt: passedAt, passedDays: passedDays,
          failed: blownUp && !passed, failedAt: blownUp && !passed ? deadAt : -1,
          verdict: passed ? 'PASS' : (blownUp ? 'FAIL' : 'INCOMPLETE'),
          target: ev.target === undefined ? 1250 : ev.target,
          dailyCap: ev.dailyCap === undefined ? 625 : ev.dailyCap,
          days: dayCount, capHits: capHits,
          bestDay: bestDay === -Infinity ? 0 : bestDay,
          finalFloor: floorNow
        } : null
      }
    };
  }


  /* ---------- repeated evaluations ----------
     simulateAccount() models ONE account and stops the moment it passes or
     busts. That answers "did this account survive", not "how often does this
     strategy pass", which is the question that matters when evaluations are
     cheap and repeatable.

     This runs the same trade stream through account after account: when one
     passes or busts it is recorded, a fresh one is bought, and the stream
     continues from the very next trade. Every account faces the same rules
     from the same starting balance, so the pass rate is a like-for-like count
     rather than one lucky or unlucky path.

     Adds a DAILY LOSS LIMIT alongside the daily profit cap: reaching either
     ends that account's trading day. The adverse allowance on any trade is the
     nearest of the stop, what the daily loss limit still permits, and what the
     account has left before it busts.                                        */
  function simulateSeries(B, trades, entryIdx, exitIdx, opts) {
    var o = opts || {};
    var ev = o.evaluation || {};
    var start = o.balance === undefined ? 25000 : o.balance;
    var pv = o.pointValue === undefined ? 2 : o.pointValue;
    var comm = o.commission === undefined ? 0 : o.commission;
    var slip = o.slippage === undefined ? 0 : o.slippage;
    var target = ev.target === undefined ? 1250 : ev.target;
    var dailyCap = ev.dailyCap === undefined ? 625 : ev.dailyCap;
    var dailyLoss = ev.dailyLoss === undefined ? 0 : ev.dailyLoss;
    var trailDD = ev.trailDD === undefined ? 1000 : ev.trailDD;
    var freezeLevel = start + (ev.freezeOffset === undefined ? 100 : ev.freezeOffset);
    var ticket = ev.cost === undefined ? 0 : ev.cost;
    /* the funded stage: what a passed account must reach to pay, what that
       payout is actually worth to you, and whether the consistency cap still
       applies once funded (the firm's rules are not explicit, so it is a
       setting rather than an assumption baked into the answer) */
    var payoutAt = ev.payoutAt === undefined ? 2100 : ev.payoutAt;
    /* what leaves the account on a withdrawal, and the share of it you keep.
       LucidFlex 25k: reach $27,100, withdraw $1,000, receive 90% of it. */
    var payoutDraw = ev.payoutDraw === undefined ? 1000 : ev.payoutDraw;
    var payoutSplit = ev.payoutSplit === undefined ? 0.9 : ev.payoutSplit;
    /* a withdrawal does not end the account: the money comes out and it keeps
       trading, so a funded account pays repeatedly until the drawdown ends it */
    var retireOnPayout = ev.retireOnPayout === undefined ? false : !!ev.retireOnPayout;
    /* ...unless the firm caps how many times one account may withdraw. After
       the cap the account graduates to live and leaves this model, so it is
       neither a bust nor still running: it is counted separately. 0 = no cap. */
    var maxDraws = ev.maxDraws === undefined ? 0 : ev.maxDraws;
    if (retireOnPayout && !(maxDraws > 0)) maxDraws = 1;
    var fundedCapOn = ev.fundedCapOn === undefined ? true : !!ev.fundedCapOn;

    var rows = new Array(trades.length);
    var accounts = [], i;
    var acct = null;

    function open(atTrade) {
      acct = {
        n: accounts.length + 1, from: atTrade, to: atTrade,
        bal: start, floor: start - trailDD, peak: start,
        curDay: -1, dayPnL: 0, days: 0, trades: 0, wins: 0,
        forced: 0, capped: 0, verdict: 'INCOMPLETE', pnl: 0,
        stage: 'eval', funded: false, paid: 0, draws: 0, stopDay: false
      };
    }
    function close(verdict, atTrade) {
      acct.verdict = verdict;
      acct.to = atTrade;
      acct.pnl = acct.bal - start;
      accounts.push(acct);
      acct = null;
    }
    open(0);

    for (i = 0; i < trades.length; i++) {
      var t = trades[i], a = entryIdx[i], b = exitIdx[i];
      if (a < 0 || b < 0 || a >= B.n || b >= B.n) {
        rows[i] = { i: i, skipped: true, reason: 'outside the loaded bars' };
        continue;
      }
      /* One retry per trade: an account retired for want of equity is replaced
         and the replacement attempts this same trade, rather than the signal
         being lost with the account that could not afford it. */
      var attempt = 0, placed = false;
      while (attempt < 2 && !placed) {
      attempt++;
      if (!acct) open(i);

      var sIdx = sessionOf(B.sessions, a);
      if (sIdx !== acct.curDay) {
        if (acct.curDay >= 0) {
          /* the floor ratchets on the END-OF-DAY balance, then freezes */
          var lifted = acct.bal - trailDD;
          if (lifted > acct.floor) acct.floor = lifted;
          if (acct.floor > freezeLevel) acct.floor = freezeLevel;
        }
        acct.curDay = sIdx; acct.dayPnL = 0; acct.days++; acct.stopDay = false;
      }
      /* passing, or being paid, ends that account's trading day */
      if (acct.stopDay) {
        rows[i] = { i: i, skipped: true, reason: 'done for the day',
                    acct: acct.n, bal: acct.bal, floor: acct.floor };
        break;
      }
      var capNow = (acct.stage === 'funded' && !fundedCapOn) ? Infinity : dailyCap;
      if (acct.dayPnL >= capNow - 1e-9) {
        rows[i] = { i: i, skipped: true, reason: 'daily cap reached',
                    acct: acct.n, bal: acct.bal, floor: acct.floor };
        break;
      }
      if (dailyLoss > 0 && acct.dayPnL <= -dailyLoss + 1e-9) {
        rows[i] = { i: i, skipped: true, reason: 'daily loss limit reached',
                    acct: acct.n, bal: acct.bal, floor: acct.floor };
        break;
      }

      var side = t.side >= 0 ? 1 : -1;
      var entry = t.entry;
      var stopDist = Math.abs(t.stop_px - entry);
      var size;
      if (o.sizeMode === 'risk' && stopDist > 0) {
        size = Math.floor((acct.bal - acct.floor) * (o.riskPct || 1) / 100 / (stopDist * pv));
      } else {
        size = o.contracts === undefined ? 1 : o.contracts;
      }
      if (!(size >= 1)) {
        rows[i] = { i: i, skipped: true, reason: 'too little equity to size a trade',
                    acct: acct.n, bal: acct.bal, floor: acct.floor };
        /* Risk sizing has rounded to nothing. The balance cannot change without
           a trade and the floor never falls, so this account can never size a
           trade again -- retire it rather than let it skip the rest of the
           file. A fresh account that cannot size one is a settings problem, not
           a dead account, so leave that one alone. */
        if (acct.trades > 0) { close('FAIL', i); continue; }
        break;
      }

      var perPoint = size * pv;
      var exitCost = 2 * slip * perPoint + 2 * comm * size;
      var roomAcct = acct.bal - acct.floor;
      var roomDay = dailyLoss > 0 ? dailyLoss + acct.dayPnL : Infinity;
      var room = Math.min(roomAcct, roomDay);
      var liq = (room - exitCost) / perPoint;
      if (!(liq > 0)) {
        rows[i] = { i: i, skipped: true, reason: 'not enough equity left to cover costs',
                    acct: acct.n, bal: acct.bal, floor: acct.floor };
        /* The remaining room will not even cover the round turn, so no trade
           can be placed. Without a trade the balance is frozen and the floor
           only ratchets up: this account can never trade again. Leaving it open
           made it skip every remaining trade in the file. It is finished. */
        if (acct.trades > 0) { close('FAIL', i); continue; }
        break;
      }
      var allow = Math.min(liq, stopDist > 0 ? stopDist : Infinity);

      var mae = 0, mfe = 0, exitPx = t.exit, forcedHere = false, exitBar = b;
      for (var k = a; k <= b; k++) {
        var adv = side > 0 ? (entry - B.l[k]) : (B.h[k] - entry);
        var fav = side > 0 ? (B.h[k] - entry) : (entry - B.l[k]);
        if (adv > mae) mae = adv;
        if (fav > mfe) mfe = fav;
        if (adv >= allow) {
          exitPx = side > 0 ? entry - allow : entry + allow;
          forcedHere = liq <= stopDist;
          exitBar = k; mae = allow;
          break;
        }
      }

      var pts = (exitPx - entry) * side - 2 * slip;
      var pnl = pts * perPoint - comm * size * 2;
      var capped = false, bind = null;
      if (acct.dayPnL + pnl > capNow) {
        pnl = capNow - acct.dayPnL; capped = true; bind = 'cap';
      }
      /* an evaluation also closes at the pass line: the account is promoted
         and reset the moment it gets there, so nothing past it is booked */
      if (acct.stage === 'eval' && acct.bal + pnl > start + target) {
        pnl = start + target - acct.bal; capped = true; bind = 'pass';
      }
      /* and a funded account at the payout line: the withdrawal is taken
         the moment the balance gets there, not after the trade runs on */
      if (acct.stage === 'funded' && acct.bal + pnl > start + payoutAt) {
        pnl = start + payoutAt - acct.bal; capped = true; bind = 'payout';
      }
      if (capped) acct.capped++;
      acct.dayPnL += pnl;
      acct.bal += pnl;
      acct.trades++;
      if (pnl > 0) acct.wins++;
      if (forcedHere) acct.forced++;
      if (acct.bal > acct.peak) acct.peak = acct.bal;

      rows[i] = {
        i: i, acct: acct.n, stage: acct.stage, size: size, side: side, entry: entry, exit: exitPx,
        exitBar: exitBar, forced: forcedHere, capped: capped, bind: bind,
        mae: mae, mfe: mfe, pts: pts, pnl: pnl, bal: acct.bal,
        dayPnL: acct.dayPnL, floor: acct.floor,
        liqPrice: side > 0 ? entry - liq : entry + liq,
        liqDist: liq, stopDist: stopDist, stopReachable: liq >= stopDist
      };

      placed = true;
      if (acct.bal <= acct.floor + 1e-9) {
        close('FAIL', i);
      } else if (acct.stage === 'eval' && acct.bal >= start + target - 1e-9) {
        /* Passing does not end the ticket -- it promotes it. The funded
           account starts again at the opening balance with the same trailing
           drawdown, and now has something to aim at that actually pays. */
        acct.stage = 'funded'; acct.funded = true;
        acct.bal = start; acct.floor = start - trailDD;
        acct.peak = start; acct.stopDay = true;
      } else if (acct.stage === 'funded' && acct.bal >= start + payoutAt - 1e-9) {
        /* Withdraw. The draw leaves the account; you keep your share of it.
           The account carries on from the reduced balance -- the floor is
           already frozen by this point, so there is still room to trade. */
        acct.paid += payoutDraw * payoutSplit;
        acct.draws++;
        acct.bal -= payoutDraw;
        acct.stopDay = true;
        /* The next withdrawal needs the balance back at the same threshold,
           and the floor stays frozen where it is -- so each further payout is
           earned from a smaller cushion than the first. */
        if (maxDraws > 0 && acct.draws >= maxDraws) close('LIVE', i);
      }
      }   /* end retry */
    }
    if (acct && acct.trades > 0)
      close(acct.draws > 0 ? 'PAYING' : 'INCOMPLETE', trades.length - 1);

    var passes = 0, fails = 0, incomplete = 0, pnlTot = 0, tradesTot = 0;
    var forcedTot = 0, daysTot = 0, payouts = 0, wonTot = 0, graduated = 0;
    for (i = 0; i < accounts.length; i++) {
      if (accounts[i].funded) passes++;
      payouts += accounts[i].draws;
      wonTot += accounts[i].paid;
      if (accounts[i].verdict === 'FAIL') fails++;
      else if (accounts[i].verdict === 'LIVE') graduated++;
      else incomplete++;
      pnlTot += accounts[i].pnl;
      tradesTot += accounts[i].trades;
      forcedTot += accounts[i].forced;
      daysTot += accounts[i].days;
    }
    var decided = payouts + fails;
    var spentTot = accounts.length * ticket;
    return {
      rows: rows, accounts: accounts,
      summary: {
        start: start, target: target, dailyCap: dailyCap, dailyLoss: dailyLoss,
        trailDD: trailDD, ticket: ticket,
        accounts: accounts.length, passes: passes, fails: fails,
        incomplete: incomplete, payouts: payouts,
        payoutAt: payoutAt, payoutDraw: payoutDraw, payoutSplit: payoutSplit,
        payoutValue: payoutDraw * payoutSplit,
        retireOnPayout: retireOnPayout, fundedCapOn: fundedCapOn,
        maxDraws: maxDraws, graduated: graduated,
        passRate: accounts.length ? passes / accounts.length : 0,
        fundedRate: accounts.length ? passes / accounts.length : 0,
        /* the figure that compares configurations buying very different
           numbers of accounts: per dollar spent on tickets, what came back */
        roi: spentTot ? (wonTot - spentTot) / spentTot : 0,
        perTicket: accounts.length ? (wonTot - spentTot) / accounts.length : 0,
        drawsPerFunded: passes ? payouts / passes : 0,
        /* Trading P&L is a diagnostic, NOT money you keep: a prop account's
           balance is never yours. The only cash that reaches you is a payout,
           and the only cash that leaves you is a ticket. */
        pnl: pnlTot, ticketCost: spentTot,
        spent: spentTot, won: wonTot,
        net: wonTot - spentTot,
        tradingPnl: pnlTot,
        trades: tradesTot, forced: forcedTot,
        avgTradesPerAccount: accounts.length ? tradesTot / accounts.length : 0,
        avgDaysPerAccount: accounts.length ? daysTot / accounts.length : 0
      }
    };
  }

  /* ---------- how a single candle should be drawn ----------
     Pulled out of the render loop so it can actually be tested. The two
     styles are genuinely different conventions, not a colour tweak:

       "candle"  solid body; colour from close vs OPEN (this bar's own range)
       "hollow"  colour from close vs PREVIOUS CLOSE (direction of the move),
                 body hollow when the bar closed up on its own open

     An earlier build had `(type === 'hollow' || type === 'candle') && up`,
     which made both styles render identically.                              */
  function candleStyle(B, i, type) {
    if (type === 'hollow') {
      return {
        up: i === 0 ? B.c[i] >= B.o[i] : B.c[i] >= B.c[i - 1],
        hollow: B.c[i] >= B.o[i]
      };
    }
    return { up: B.c[i] >= B.o[i], hollow: false };
  }

  /* ---------- magnet: nearest OHLC level on a bar ---------- */
  function magnet(B, i, price) {
    if (i < 0 || i >= B.n) return price;
    var cand = [B.o[i], B.h[i], B.l[i], B.c[i]];
    var best = cand[0], bd = Math.abs(price - cand[0]);
    for (var k = 1; k < 4; k++) {
      var d = Math.abs(price - cand[k]);
      if (d < bd) { bd = d; best = cand[k]; }
    }
    return best;
  }

  /* ---------- price scale, linear or logarithmic ----------
     Y and vAt must be exact inverses in BOTH modes, or the crosshair reads a
     different price from the one it is drawn at, and the measure tool lies.  */
  function makeScale(lo, hi, y0, h, log) {
    var f = log ? function (v) { return Math.log(v > 0 ? v : 1e-9); }
                : function (v) { return v; };
    var g = log ? Math.exp : function (v) { return v; };
    var a = f(lo), b = f(hi), d = (b - a) || 1;
    return {
      Y: function (v) { return y0 + h * (1 - (f(v) - a) / d); },
      vAt: function (py) { return g(a + (1 - (py - y0) / h) * d); }
    };
  }

  /* ---------- measurement between two chart points ----------
     Percentage is always computed on REAL prices, never on the log of them. */
  function measure(v0, v1, i0, i1) {
    return {
      pts: v1 - v0,
      pct: v0 !== 0 ? (v1 - v0) / Math.abs(v0) * 100 : 0,
      bars: Math.abs(Math.round(i1 - i0))
    };
  }

  /* ---------- session grouping for imported data ----------
     Splitting purely on the date breaks non-intraday files: with one bar per
     date every bar becomes its own "session", so timeframe aggregation turns
     into a no-op and a 5-day candle is impossible. If no date carries more
     than one bar the series is not intraday, so it becomes ONE session and
     aggregation works normally.                                              */
  function buildSessions(days) {
    var n = days.length, i;
    if (!n) return [];
    var counts = {}, maxPer = 0;
    for (i = 0; i < n; i++) {
      counts[days[i]] = (counts[days[i]] || 0) + 1;
      if (counts[days[i]] > maxPer) maxPer = counts[days[i]];
    }
    if (maxPer <= 1) {
      return [{ day: days[0], a: 0, b: n - 1, spanning: true }];
    }
    var out = [], cur = null;
    for (i = 0; i < n; i++) {
      if (!cur || cur.day !== days[i]) { cur = { day: days[i], a: i, b: i }; out.push(cur); }
      else cur.b = i;
    }
    return out;
  }

  /* ---------- keep a replay cursor meaningful across a timeframe change ----------
     The cursor is held in BASE-bar space; a view index is only ever derived
     from it. Storing it in view space meant switching timeframe silently
     teleported the replay to an unrelated moment.                            */
  function replayToView(baseIdx, V, baseN) {
    if (!V || !V.map) return 0;
    var i = baseIdx < 0 ? 0 : (baseIdx > baseN - 1 ? baseN - 1 : baseIdx);
    var v = V.map[i];
    return v === undefined ? 0 : v;
  }
  function viewToReplay(viewIdx, V, baseN) {
    if (!V || !V.src) return 0;
    var i = viewIdx < 0 ? 0 : (viewIdx > V.n - 1 ? V.n - 1 : viewIdx);
    var b = V.src[i];
    return b === undefined ? 0 : (b > baseN - 1 ? baseN - 1 : b);
  }

  /* ================= LIVE BREAKOUT ENTRIES =================
     The Breakout Academy replays (bo_ti4/bo_hit41/bo_hit34 in STRATS) read a
     table baked offline by bo_pack.py from one specific historical tape.
     This computes the same two systems' entries FRESH from whatever bars
     are loaded, with the lookback/ADX/DMI settings as live parameters,
     producing a table in the exact shape slotsFromTable already replays --
     the account rules, stop, costs and size still come from the panel.

     p = {system: 'hitter'|'trendindi', side: 'long'|'short',
          winStart, winEnd,                    minute-of-day trading window
          n, adxPeriod, adxThreshold, adxDirection: 'below'|'above',   Hitter
          fraction, dxPeriod, dxShift, dxThreshold}                Trend indi 2

     Wilder's ADX/DX need session-spanning history to mean anything, so they
     are computed on 30-minute bars built from the WHOLE loaded series (never
     reset per day), exactly as bo_data.py builds them from its 24-hour tape.
     Loaded with RTH on, the tradeable window and the day's bar count are
     both narrower than the original 24-hour, 09:00-start study used, so this
     is a live approximation on your own tape, not a replay of that study --
     turn RTH off to match its setup more closely. */
  function liveBreakoutSides(B, p) {
    var agg = aggregate(B, 30);
    var period = p.system === 'hitter' ? p.adxPeriod : p.dxPeriod;
    var dxadx = wilderDxAdx(agg.h, agg.l, agg.c, period);
    var trend = p.system === 'hitter' ? dxadx.adx : dxadx.dx;
    var side = p.side === 'short' ? -1 : 1;
    var out = {}, s, j, k;
    for (s = 0; s < agg.sessions.length; s++) {
      var S = agg.sessions[s];
      for (j = S.a; j < S.b; j++) {          /* j+1 must stay in this session */
        var m = agg.mins[j];
        if (m < p.winStart || m > p.winEnd) continue;
        var lvl = null;
        if (p.system === 'hitter') {
          if (trend[j] === null) continue;
          var gate = p.adxDirection === 'above' ? trend[j] > p.adxThreshold : trend[j] < p.adxThreshold;
          if (!gate || j - p.n + 1 < 0) continue;
          var ext = side > 0 ? -Infinity : Infinity;
          for (k = j - p.n + 1; k <= j; k++) {
            if (side > 0 ? agg.c[k] > ext : agg.c[k] < ext) ext = agg.c[k];
          }
          lvl = ext;
        } else {
          var shifted = j - p.dxShift;
          if (shifted < 0 || trend[shifted] === null) continue;
          var dv = trend[shifted];
          var rng = p.fraction * Math.abs(agg.o[j] - agg.l[j]);
          var cand = agg.o[j] + side * rng;
          var gateOk = side > 0 ? dv < p.dxThreshold : dv > p.dxThreshold;
          var nearSide = side > 0 ? agg.c[j] < cand : agg.c[j] > cand;
          if (!gateOk || !nearSide) continue;
          lvl = cand;
        }
        /* the level is a stop order live during the NEXT 30-minute bar only;
           scan its 1-minute bars in order for the first touch */
        /* j1 is an aggregated-bar index; its own session may be shorter than
           tf on the last chunk, so the upper bound comes from B's own
           session boundary, not a fixed 30-bar span past agg.src[j1] */
        var j1 = j + 1, i0 = agg.src[j1];
        var i1 = (j1 + 1 <= S.b) ? agg.src[j1 + 1] - 1 : B.sessions[s].b;
        var fillAt = -1;
        for (k = i0; k <= i1; k++) {
          if (side > 0 ? B.h[k] >= lvl : B.l[k] <= lvl) { fillAt = k; break; }
        }
        if (fillAt < 0) continue;
        /* a bar that opened through the level fills at the open, not the
           stale level (bo_engine.py's own rule); an open sits inside its
           own bar's [l,h] by construction, so this keeps the stored level
           reachable in exactly the bar it is stored against */
        var op = B.o[fillAt];
        if (side > 0 ? op > lvl : op < lvl) lvl = op;
        out[S.day] = {};
        out[S.day][String(B.mins[fillAt])] = [side, lvl];
        break;   /* one entry a day: this session is decided */
      }
    }
    return out;
  }

  /* ================= STRATEGY RUNNER =================
     Generates the trades AND walks the account in a single pass, because the
     two cannot be separated: the daily profit cap and the drawdown floor are
     fixed in DOLLARS, so changing position size changes where a trade exits,
     not merely what it earns. Any design that generates a trade list first and
     re-sizes it afterwards is wrong -- that is precisely the bug that made a
     naively doubled CSV keep trades that would never have happened.

     entry   {mode:'reentry'|'orb'|'window', startMin, endMin, slotMin, orbBars,
              winMin, winBars, exitMin, holdMin, direction, sides, seed,
              daysOfWeek, newsDays, tableSkipReason}
             direction: 'random' (the coin) | 'orb' | 'window' (follow the signal
             candle) | 'long' | 'short' | 'table' (sides[day] = 1|-1|0, 0 stands aside;
             or sides[day] = {minute: 1|-1|0}, a decision per slot)
             holdMin: each trade ends holdMin minutes after its own entry (or at
             exitMin / the close, whichever is first); null = as before
             slotsFromTable: the per-slot table names the entry minutes itself
             (a stop-order system that fills at an arbitrary minute); a stored
             value may be [side, level], and the trade then fills at the level
             (or the open, if the bar opened through it) instead of the open
             daysOfWeek: array of allowed weekday ints (0=Sun..6=Sat), or null/absent
             = every day. newsDays: {day: true} map of allowed ISO days, or null/absent
             = every day. Both gate BEFORE slot generation for the session; neither
             field is set by any existing STRATS entry, so this is purely additive.
             tableSkipReason: when set (only the 'custom' strategy sets it), a
             slotsFromTable candidate suppressed because the previous trade is still
             open is pushed as a `skipped: true` row with this reason instead of a
             silent `continue` -- scoped to this explicit flag, not a blanket
             `slotsFromTable` check, so no other strategy's ledger can be affected
     trade   {stopPts, rr}  or, in the sweeps' own units, {riskUSD, targetUSD}
     acct    {balance, contracts, pointValue, commission, slippage}
     rules   {trailDD, freezeOffset, dailyCap, dailyLoss, fundedDailyLoss,
              target, payoutAt, payoutDraw, payoutSplit, maxDraws, ticket}
     span    {from, to}   ISO days, inclusive; sessions outside are not traded
     funded  {entry, trade, acct}  what the FUNDED stage trades, when it differs
             from the evaluation; each block given replaces the evaluation's
             as a whole (balance, slippage and the coin stream stay shared)
     ================================================== */

  /* A seeded generator, so the same strategy replays identically. Math.random
     cannot be seeded, and an unseeded run would give a different answer on
     every click. */
  function lcg(seed) {
    var s = (seed >>> 0) || 1;
    return function () {
      s = (s * 1664525 + 1013904223) >>> 0;
      return s / 4294967296;
    };
  }

  /* Weekday of a 'YYYY-MM-DD' string via Zeller's congruence, 0=Sun..6=Sat, proleptic
     Gregorian -- no Date object, matching this file's existing style (no Date anywhere
     else in it), so it stays immune to whatever timezone the host machine runs in. */
  function dowOf(day) {
    var y = +day.slice(0, 4), m = +day.slice(5, 7), d = +day.slice(8, 10);
    if (m < 3) { y -= 1; m += 12; }
    var k = y % 100, j = (y / 100) | 0;
    var h = (d + (((13 * (m + 1)) / 5) | 0) + k + ((k / 4) | 0) + ((j / 4) | 0) + 5 * j) % 7;
    return (h + 6) % 7;   /* Zeller: 0=Sat..6=Fri; rotate to 0=Sun..6=Sat */
  }

  function runStrategy(B, opt) {
    var e = opt.entry || {}, t = opt.trade || {}, a = opt.acct || {}, r = opt.rules || {};
    var rnd = lcg(e.seed === undefined ? 23 : e.seed);

    var START = a.balance === undefined ? 25000 : a.balance;
    var slip = a.slippage === undefined ? 0.25 : a.slippage;

    /* What one stage trades: its entry schedule, its size and its stop and
       target. The funded stage may have its own (opt.funded = {entry, trade,
       acct}, each block replacing the evaluation's as a whole when given),
       exactly as pf_stage carries an evalcfg and a fundcfg. Balance, slippage
       and the coin stream are the account's, shared by both. */
    function stageParams(e, t, a) {
      var p = {};
      p.mode = e.mode || 'reentry';
      p.startMin = e.startMin === undefined ? 600 : e.startMin;
      p.endMin = e.endMin === undefined ? 930 : e.endMin;
      p.slotMin = e.slotMin === undefined ? 30 : e.slotMin;
      p.orbBars = e.orbBars === undefined ? 26 : e.orbBars;
      /* 'window' mode: a signal candle of winBars bars starting at minute winMin,
         entered at the bar after it (the last-hour candle rule: 900 = 15:00, 5). */
      p.winMin = e.winMin === undefined ? 900 : e.winMin;
      p.winBars = e.winBars === undefined ? 5 : e.winBars;
      /* the trade may run only to the bar at this minute (949 = 15:49); null = the
         session close, which is what every earlier strategy had */
      p.exitMin = (e.exitMin === undefined || e.exitMin === null) ? null : e.exitMin;
      /* each trade may run only holdMin minutes from its own entry (30 = a
         half-hour trade); null = to exitMin or the close */
      p.holdMin = (e.holdMin === undefined || e.holdMin === null) ? null : e.holdMin;
      /* direction 'table': a stored decision per day, {day: 1|-1|0}, or per slot,
         {day: {minute: 1|-1|0}}; 0 stands aside */
      p.sides = e.sides || null;
      p.slotsFromTable = !!e.slotsFromTable;
      /* narrowly-scoped opt-in: only the 'custom' strategy sets this, so only it can
         ever produce this skipped-row reason -- see the skip-row push below */
      p.tableSkipReason = e.tableSkipReason || null;
      /* daysOfWeek: array of allowed weekday ints (0=Sun..6=Sat), or null = every day.
         newsDays: {day: true} map of allowed ISO days, or null = every day. Both are
         pure additive filters -- no existing STRATS entry sets either, so today's
         strategies are unaffected. */
      p.daysOfWeek = e.daysOfWeek || null;
      p.newsDays = e.newsDays || null;
      p.dir = e.direction || 'random';
      p.size = a.contracts === undefined ? 1 : a.contracts;
      p.pv = a.pointValue === undefined ? 2 : a.pointValue;
      p.comm = a.commission === undefined ? 0.75 : a.commission;
      p.dv = p.size * p.pv;
      p.cost = slip * p.dv + 2 * p.comm * p.size;   /* exit slippage; entry is in the fill */
      p.stopPts = t.stopPts === undefined ? 50 : t.stopPts;
      var rr = t.rr === undefined ? 1 : t.rr;
      /* The dollar form is taken as given, not routed through rr * stopPts * dv:
         625/950 * 47.5 * 20 is 625.0000000000001, and because NQ excursions
         land on exact quarter points that last ulp decides every trade that
         touches the target precisely. pf_stage documents the same trap. */
      if (t.riskUSD !== undefined) p.stopPts = t.riskUSD / p.dv;
      p.tgtCap = t.targetUSD !== undefined ? t.targetUSD : rr * p.stopPts * p.dv;
      return p;
    }
    var fo = opt.funded || {};
    var PE = stageParams(e, t, a);
    var PF = (fo.entry || fo.trade || fo.acct)
      ? stageParams(fo.entry || e, fo.trade || t, fo.acct || a) : PE;

    var DD = r.trailDD === undefined ? 1000 : r.trailDD;
    var FRZ = START + (r.freezeOffset === undefined ? 100 : r.freezeOffset);
    var CAP = r.dailyCap === undefined ? 625 : r.dailyCap;
    /* 0 = no loss limit. Reaching it ENDS THE DAY, it does not bust the
       account, exactly as pf_stage's loss_lim does. null for the funded stage
       means the same limit as the evaluation, mirroring fundedCap below. */
    var LOSS = r.dailyLoss === undefined ? 0 : r.dailyLoss;
    var fundedLoss = (r.fundedDailyLoss === undefined || r.fundedDailyLoss === null)
      ? LOSS : r.fundedDailyLoss;
    var TGT = r.target === undefined ? 1250 : r.target;
    var PAY = r.payoutAt === undefined ? 2100 : r.payoutAt;
    var TICKET = r.ticket === undefined ? 65 : r.ticket;
    /* LucidFlex 25k: reach $27,100, withdraw $1,000, keep 90% of it = $900.
       The account is NOT retired -- the money comes out and it keeps trading
       from $26,100 with the floor left frozen where it was, so every further
       payout is earned from a thinner cushion than the one before it. */
    var DRAW = r.payoutDraw === undefined ? 1000 : r.payoutDraw;
    var SPLIT = r.payoutSplit === undefined ? 0.9 : r.payoutSplit;
    /* 0 = the account may withdraw for ever. Otherwise it graduates to a live
       account after this many withdrawals and leaves the model: neither a bust
       nor still running, and a fresh evaluation is bought. */
    var MAXD = r.maxDraws === undefined ? 0 : r.maxDraws;
    /* null = the consistency cap applies during the evaluation ONLY, so a
       funded account may run all the way to the payout in a single session. */
    var fundedCap = r.fundedCap === undefined ? null : r.fundedCap;

    var EPS = 1e-6;
    var CASH = DRAW * SPLIT;
    var from = (opt.span && opt.span.from) || null, to = (opt.span && opt.span.to) || null;
    var lastS = -1, nSess = 0, firstDay = null, lastDay = null;

    var bal = START, floor = START - DD, stage = 'eval';
    var tickets = 1, passes = 0, evalBust = 0, fundBust = 0;
    var draws = 0, graduated = 0, won = 0;
    var acctN = 1, peak = bal, bestFunded = bal;
    var out = [], events = [], accounts = [], bad = [];
    var A0 = null;

    function openAcct(bar, si) {
      A0 = {
        n: acctN, stage: 'eval', funded: false, verdict: null,
        from_bar: bar, to_bar: bar, from_session: si, to_session: si,
        trades: 0, days: 0, draws: 0, paid: 0,
        bal: START, floor: START - DD, peak: START
      };
      events.push({ kind: 'ticket', bar: bar, session: si, acct: acctN,
                    stage: 'eval', from: 0, to: TICKET, bal: START, floor: START - DD });
    }
    function closeAcct(verdict, bar, si) {
      if (!A0) return;
      A0.verdict = verdict; A0.to_bar = bar; A0.to_session = si;
      A0.bal = bal; A0.floor = floor;
      accounts.push(A0); A0 = null;
    }
    function flag(msg, row) { if (bad.length < 50) bad.push({ msg: msg, row: row }); }
    /* the bar at a minute of the day inside a session, or -1 */
    function barAt(S, m) {
      var g = S.a + (m - B.mins[S.a]);
      if (g >= S.a && g <= S.b && B.mins[g] === m) return g;
      for (var i = S.a; i <= S.b; i++) if (B.mins[i] === m) return i;
      return -1;
    }
    /* the last bar a trade may run to in this session */
    function exitEnd(p, S) {
      if (p.exitMin === null) return S.b;
      var x = barAt(S, p.exitMin);
      return x < 0 ? S.b : x;
    }
    /* the last bar a trade entered at i0 may run to: within holdMin minutes of its
       own entry (a 10:00 entry held 30 exits at the 10:29 close), never past xEnd */
    function holdEnd(p, i0, xEnd) {
      if (p.holdMin === null) return xEnd;
      var end = B.mins[i0] + p.holdMin - 1, j = i0;
      while (j + 1 <= xEnd && B.mins[j + 1] <= end) j++;
      return j;
    }
    /* candidate entry bars for a session under one stage's schedule */
    function slotsFor(p, S) {
      var out = [];
      /* the table is the schedule: one candidate bar per stored minute that
         exists in this session, whatever the direction (the coin on the same
         bar keeps the schedule and only draws the side) */
      if (p.slotsFromTable && p.sides) {
        var sd0 = p.sides[S.day];
        if (sd0 && typeof sd0 === 'object') {
          for (var mk in sd0) {
            var gb = barAt(S, +mk);
            if (gb >= 0) out.push(gb);
          }
          out.sort(function (x, y) { return x - y; });
        }
        return out;
      }
      if (p.mode === 'orb') {
        if (S.a + p.orbBars <= S.b) out.push(S.a + p.orbBars);
      } else if (p.mode === 'window') {
        var w = barAt(S, p.winMin);
        if (w >= 0 && w + p.winBars < exitEnd(p, S)) out.push(w + p.winBars);
      } else {
        for (var i = S.a; i <= S.b; i++) {
          var m = B.mins[i];
          if (m >= p.startMin && m <= p.endMin && (m - p.startMin) % p.slotMin === 0) out.push(i);
        }
      }
      return out;
    }

    for (var s = 0; s < B.sessions.length; s++) {
      var S = B.sessions[s];
      /* outside the span the tape might as well not exist: no entries, no
         account-day, no floor ratchet */
      if ((from && S.day < from) || (to && S.day > to)) continue;
      lastS = s; nSess++;
      if (firstDay === null) firstDay = S.day;
      lastDay = S.day;
      var realized = 0, lastExit = -1, stopDay = false;
      if (!A0) openAcct(S.a, s);
      A0.days++;

      var p = stage === 'eval' ? PE : PF;
      /* daysOfWeek/newsDays gate BEFORE slot generation, not after -- a session that
         fails either is simply not scheduled at all, exactly like a mode/startMin
         combination that produces no candidates today. Neither field is set by any
         existing STRATS entry, so this changes nothing for them. */
      var eligible = (!p.daysOfWeek || p.daysOfWeek.indexOf(dowOf(S.day)) !== -1) &&
                     (!p.newsDays || !!p.newsDays[S.day]);
      var slots = eligible ? slotsFor(p, S) : [];

      var xEnd = exitEnd(p, S);
      for (var k = 0; k < slots.length && !stopDay; k++) {
        var i0 = slots[k];
        if (i0 >= xEnd) continue;
        if (i0 <= lastExit) {
          if (p.slotsFromTable && p.tableSkipReason) {
            out.push({ skipped: true, entry_bar: i0, exit_bar: i0, session: s, day: S.day,
                       acct: A0.n, stage: stage, bal: bal, floor: floor, realized: realized,
                       reason: p.tableSkipReason });
          }
          continue;
        }
        var dv = p.dv, cost = p.cost, size = p.size, stopPts = p.stopPts, tgtCap = p.tgtCap;

        /* A rule that has decided in advance decides HERE, before the account is
           consulted: a day it stands aside on must not become a bust-for-no-room
           on the account, because the Python engines omit that day's entry
           altogether and the two must land on the same days. The coin keeps
           drawing after the room checks, as it always has. */
        var preSide = null, preLevel = null;
        if (p.dir === 'window') {
          var w0 = barAt(S, p.winMin);
          var refW = w0 < 0 ? 0 : B.c[w0 + p.winBars - 1] - B.o[w0];
          if (refW === 0) {
            out.push({ skipped: true, entry_bar: i0, exit_bar: i0, session: s, day: S.day,
                       acct: A0.n, stage: stage, bal: bal, floor: floor, realized: realized,
                       reason: 'flat signal candle' });
            continue;
          }
          preSide = refW > 0 ? 1 : -1;
        } else if (p.dir === 'table') {
          var sd = p.sides ? p.sides[S.day] : undefined;
          /* a per-slot table: the day's entry is keyed by the entry minute */
          if (sd !== undefined && sd !== null && typeof sd === 'object' && sd.length === undefined) sd = sd[String(B.mins[i0])];
          /* a stored [side, level]: a stop order that filled at that price */
          if (sd !== undefined && sd !== null && typeof sd === 'object' && sd.length === 2) {
            preLevel = +sd[1]; sd = +sd[0];
          }
          if (sd === undefined || sd === null) {
            flag('no stored decision for ' + S.day, out.length);
            out.push({ skipped: true, entry_bar: i0, exit_bar: i0, session: s, day: S.day,
                       acct: A0.n, stage: stage, bal: bal, floor: floor, realized: realized,
                       reason: 'no model decision' });
            continue;
          }
          if (sd === 0) {
            out.push({ skipped: true, entry_bar: i0, exit_bar: i0, session: s, day: S.day,
                       acct: A0.n, stage: stage, bal: bal, floor: floor, realized: realized,
                       reason: 'model abstained' });
            continue;
          }
          preSide = sd > 0 ? 1 : -1;
        } else if (p.dir === 'long') {
          preSide = 1;
        } else if (p.dir === 'short') {
          preSide = -1;
        }

        /* dollars of room before each barrier. When funded with no cap the
           gain room is CUMULATIVE to the payout threshold, not a daily figure:
           that is what the rule actually says.

           An evaluation trade also stops at the PASS LINE. The moment the
           balance reaches START + TGT the account is funded and reset, so
           any profit past the line is thrown away -- and, worse, a trade
           left running past it can turn round and bust an account that had
           already passed. An earlier version trimmed the target to the daily
           cap only: an account at +$1,061.50 ran its last trade on to +$625
           and "passed" at +$1,686.50, having risked $1,000 for nothing.
           bindKind names which line trimmed the target, for the ledger. */
        var gainRoom, dayTgt, bindKind;
        if (stage === 'eval') {
          dayTgt = CAP;
          var passRoom = START + TGT - bal, capRoom = CAP - realized;
          gainRoom = Math.min(capRoom, passRoom);
          bindKind = passRoom < capRoom - EPS ? 'pass' : 'cap';
        }
        else {
          /* the funded stage stops at the PAYOUT LINE the same way: the
             withdrawal is taken the moment the balance gets there */
          var payRoom = (START + PAY) - bal;
          if (fundedCap !== null) {
            dayTgt = fundedCap;
            gainRoom = Math.min(fundedCap - realized, payRoom);
            bindKind = payRoom < fundedCap - realized - EPS ? 'payout' : 'cap';
          } else { dayTgt = payRoom; gainRoom = payRoom; bindKind = 'payout'; }
        }
        var bustRoom = bal - floor;

        if (gainRoom <= EPS) {
          out.push({ skipped: true, entry_bar: i0, exit_bar: i0, session: s, day: S.day,
                     acct: A0.n, stage: stage, bal: bal, floor: floor, realized: realized,
                     reason: stage === 'eval' ? 'daily cap reached' : 'payout target reached' });
          break;
        }
        /* The adverse barrier must leave enough to PAY for the exit, or the
           balance lands below the floor. */
        var adverseRoom = bustRoom - cost;
        if (bustRoom <= EPS || adverseRoom <= EPS) {
          out.push({ skipped: true, entry_bar: i0, exit_bar: i0, session: s, day: S.day,
                     acct: A0.n, stage: stage, bal: bal, floor: floor, realized: realized,
                     reason: 'costs exceed remaining equity' });
          /* An account that cannot afford the round turn can never trade again.
             Leaving it alive freezes the run: it skips every remaining slot for
             ever and quietly swallows the rest of the file. It is finished, so
             book it as a bust and buy the next ticket. A brand-new account that
             cannot size a trade is a settings problem, not a dead account, so
             that one is left alone. */
          if (A0.trades > 0) {
            if (stage === 'eval') evalBust++; else fundBust++;
            events.push({ kind: 'bust', bar: i0, session: s, acct: A0.n, stage: stage,
                          trade: out.length - 1, from: bal, to: bal, bal: bal, floor: floor,
                          note: 'could not afford a round turn' });
            closeAcct('FAIL', i0, s);
            tickets++; acctN++;
            bal = START; floor = START - DD; stage = 'eval'; realized = 0;
            openAcct(i0, s);
            /* the replacement starts at the NEXT slot, as pf_fast does, so the
               rebuilt schedule must not offer it this one again */
            if (PF !== PE) { p = PE; slots = slotsFor(p, S); k = -1; if (i0 > lastExit) lastExit = i0; }
            continue;
          }
          break;
        }

        var side;
        if (preSide !== null) {
          side = preSide;
        } else if (p.dir === 'orb') {
          var ref = B.c[Math.min(S.a + p.orbBars - 1, S.b)] - B.o[S.a];
          side = ref >= 0 ? 1 : -1;
        } else {
          side = rnd() < 0.5 ? 1 : -1;
        }

        /* A stop is a PRICE. Liquidation is an EQUITY LEVEL. Whichever is
           nearer closes the trade, and with enough size it is the second. */
        var liqDist = adverseRoom / dv;
        var stopDist = stopPts;
        var reachable = liqDist >= stopDist - EPS;
        var A = Math.min(stopDist, liqDist);
        var F = Math.min(tgtCap, gainRoom + cost) / dv;
        if (A <= EPS || F <= EPS) break;

        /* intrabar walk: whichever barrier the bar's range reaches first, with
           adverse winning a tie because 1-minute OHLC cannot order them */
        var entry;
        if (preLevel !== null) {
          /* the level must be inside this bar on THIS tape; a table made on
             other data is refused, not silently filled at the open */
          if (preLevel < B.l[i0] - EPS || preLevel > B.h[i0] + EPS) {
            out.push({ skipped: true, entry_bar: i0, exit_bar: i0, session: s, day: S.day,
                       acct: A0.n, stage: stage, bal: bal, floor: floor, realized: realized,
                       reason: 'stop level not in this bar' });
            continue;
          }
          entry = (side > 0 ? Math.max(preLevel, B.o[i0]) : Math.min(preLevel, B.o[i0])) + slip * side;
        } else {
          entry = B.o[i0] + slip * side;
        }
        var xE = holdEnd(p, i0, xEnd);
        var pts = null, xb = xE, why = 'close';
        for (var j = i0; j <= xE; j++) {
          var adv = side > 0 ? (entry - B.l[j]) : (B.h[j] - entry);
          var fav = side > 0 ? (B.h[j] - entry) : (entry - B.l[j]);
          if (adv >= A) { pts = -A; xb = j; why = 'adverse'; break; }
          if (fav >= F) { pts = F; xb = j; why = 'favourable'; break; }
        }
        if (pts === null) pts = (B.c[xE] - entry) * side;

        var pnl = pts * dv - cost;
        var forced = why === 'adverse' && !reachable;
        var capped = why === 'favourable' && (gainRoom + cost) < tgtCap - EPS;
        var balBefore = bal;
        bal += pnl; realized += pnl; lastExit = xb;
        if (bal > peak) peak = bal;
        if (bal > A0.peak) A0.peak = bal;
        if (stage === 'funded' && bal > bestFunded) bestFunded = bal;
        A0.trades++;

        var row = {
          entry_bar: i0, exit_bar: xb, side: side, session: s, day: S.day,
          entry: entry, exit: entry + pts * side,
          stop_px: entry - stopDist * side,
          liq_px: entry - liqDist * side,
          tgt_px: entry + F * side,
          A: A, F: F, liqDist: liqDist, stopDist: stopDist,
          stopReachable: reachable, forced: forced, capped: capped,
          bind: capped ? bindKind : null,
          cand_bust: bustRoom / dv, cand_daytgt: gainRoom / dv,
          pts: pts, gross: pts * dv, slip: slip * dv, comm: 2 * p.comm * size,
          pnl: pnl, realized: realized, balBefore: balBefore, bal: bal, floor: floor,
          stage: stage, why: why, acct: A0.n, account: A0.n, size: size,
          skipped: false
        };
        out.push(row);

        /* invariants -- surfaced, never silent */
        if (pts < -A - 1e-6) flag('trade lost more than its allowance', out.length - 1);
        if (pts > F + 1e-6) flag('trade beat its target', out.length - 1);
        if (stage === 'eval' && bal > START + TGT + 0.01) flag('evaluation ran past the pass line', out.length - 1);
        if (stage === 'funded' && bal > START + PAY + 0.01) flag('funded account ran past the payout line', out.length - 1);

        if (bal <= floor + EPS) {
          if (bal < floor - 0.01) flag('busted BELOW the floor', out.length - 1);
          if (stage === 'eval') evalBust++; else fundBust++;
          events.push({ kind: 'bust', bar: xb, session: s, acct: A0.n, stage: stage,
                        trade: out.length - 1, from: balBefore, to: bal, bal: bal, floor: floor });
          closeAcct('FAIL', xb, s);
          tickets++; acctN++;
          bal = START; floor = START - DD; stage = 'eval'; realized = 0;
          openAcct(xb, s);
          if (PF !== PE) { p = PE; slots = slotsFor(p, S); k = -1; }
          continue;
        }
        if (bal < floor - EPS) flag('live account below its floor', out.length - 1);

        if (stage === 'eval' && bal >= START + TGT - EPS) {
          passes++;
          events.push({ kind: 'pass', bar: xb, session: s, acct: A0.n, stage: 'eval',
                        trade: out.length - 1, from: bal, to: START, bal: START, floor: START - DD });
          stage = 'funded'; A0.stage = 'funded'; A0.funded = true;
          bal = START; floor = START - DD;
          stopDay = true;
          continue;
        }
        if (stage === 'funded' && bal >= START + PAY - EPS) {
          won += CASH; draws++; A0.draws++; A0.paid += CASH;
          events.push({ kind: 'payout', bar: xb, session: s, acct: A0.n, stage: 'funded',
                        trade: out.length - 1, from: bal, to: bal - DRAW,
                        amount: CASH, bal: bal - DRAW, floor: floor });
          bal -= DRAW;                       /* the floor is deliberately NOT reset */
          stopDay = true;
          if (MAXD > 0 && A0.draws >= MAXD) {
            graduated++;
            events.push({ kind: 'graduate', bar: xb, session: s, acct: A0.n, stage: 'funded',
                          trade: out.length - 1, from: bal, to: START, bal: START, floor: START - DD });
            closeAcct('LIVE', xb, s);
            tickets++; acctN++;
            bal = START; floor = START - DD; stage = 'eval'; realized = 0;
            openAcct(xb, s);
            if (PF !== PE) { p = PE; slots = slotsFor(p, S); k = -1; }
          }
          continue;
        }
        if (realized >= dayTgt - EPS) stopDay = true;
        var lossLim = stage === 'eval' ? LOSS : fundedLoss;
        if (lossLim > 0 && realized <= -lossLim + EPS) stopDay = true;
      }

      /* the floor ratchets on the END-OF-DAY balance only, then freezes */
      var was = floor;
      floor = Math.min(FRZ, Math.max(floor, bal - DD));
      if (A0) A0.floor = floor;
      if (floor > was + 1e-9) {
        events.push({ kind: 'ratchet', bar: S.b, session: s, acct: A0 ? A0.n : acctN,
                      stage: stage, from: was, to: floor, bal: bal, floor: floor });
      }
    }
    closeAcct(A0 && A0.draws > 0 ? 'PAYING' : 'INCOMPLETE',
              lastS >= 0 ? B.sessions[lastS].b : 0, lastS);

    var spent = tickets * TICKET;
    var taken = 0;
    for (var q = 0; q < out.length; q++) if (!out[q].skipped) taken++;

    return {
      trades: out,
      events: events,
      accounts: accounts,
      violations: bad,
      summary: {
        start: START, end: bal, peak: peak, bestFunded: bestFunded,
        evals: tickets, tickets: tickets, passes: passes,
        evalBust: evalBust, fundBust: fundBust, busts: evalBust + fundBust,
        payouts: draws, draws: draws, graduated: graduated,
        won: won, spent: spent, net: won - spent,
        roi: spent > 0 ? (won - spent) / spent : 0,
        perTicket: tickets ? (won - spent) / tickets : 0,
        payoutValue: CASH, payoutDraw: DRAW, payoutSplit: SPLIT, maxDraws: MAXD,
        accounts: acctN, nTrades: taken, nRows: out.length,
        sessions: nSess, firstDay: firstDay, lastDay: lastDay,
        skipped: out.length - taken,
        cost: tickets * TICKET,
        passRate: tickets ? passes / tickets : 0,
        conversion: passes ? draws / passes : 0,
        drawsPerFunded: passes ? draws / passes : 0,
        breakEvenPayout: draws ? spent / draws : null,
        ok: bad.length === 0
      }
    };
  }

  /* ---------- wealth after every session of a run ----------
     Payouts banked minus tickets bought, cumulative, one value per session
     of the tape. Rebuilt from the run's events rather than by a second walk,
     so it costs nothing and cannot drift from the run itself: the last value
     is summary.net by construction, and the ensemble view asserts that. A
     session outside the run's span has no events and repeats the value
     before it, which is what "nothing happened" should look like.         */
  function wealthCurve(res, nSessions) {
    var d = new Array(nSessions), i, e;
    for (i = 0; i < nSessions; i++) d[i] = 0;
    for (i = 0; i < res.events.length; i++) {
      e = res.events[i];
      if (e.kind === 'ticket') d[e.session] -= e.to;          /* the ticket price */
      else if (e.kind === 'payout') d[e.session] += e.amount;  /* the cash paid */
    }
    var acc = 0;
    for (i = 0; i < nSessions; i++) { acc += d[i]; d[i] = acc; }
    return d;
  }

  /* ---------- log-scale helpers ---------- */
  function toLog(v) { return v > 0 ? Math.log(v) : 0; }
  function fromLog(v) { return Math.exp(v); }

  return {
    lowerBound: lowerBound, sessionOf: sessionOf, aggregate: aggregate,
    heikinAshi: heikinAshi, sma: sma, ema: ema, vwapSession: vwapSession,
    bollinger: bollinger, atr: atr, wilderDxAdx: wilderDxAdx, priceRange: priceRange,
    volumeAvg: volumeAvg,
    rsi: rsi, macd: macd, stochastic: stochastic, smaNull: smaNull,
    donchian: donchian, keltner: keltner, roc: roc,
    visibleTrades: visibleTrades, tradeStats: tradeStats, magnet: magnet,
    timeFilter: timeFilter, timeMarks: timeMarks,
    buildBuckets: buildBuckets, priceRangeFast: priceRangeFast,
    runStrategy: runStrategy, liveBreakoutSides: liveBreakoutSides, lcg: lcg, wealthCurve: wealthCurve,
    dowOf: dowOf,
    simulateAccount: simulateAccount, simulateSeries: simulateSeries,
    candleStyle: candleStyle, makeScale: makeScale, measure: measure,
    buildSessions: buildSessions, replayToView: replayToView, viewToReplay: viewToReplay,
    toLog: toLog, fromLog: fromLog
  };
})();
