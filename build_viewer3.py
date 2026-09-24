import io, json

CORE = io.open(r'C:\Users\ruben\nq-backtest\viewer_core.js', encoding='utf-8').read()
D = json.load(io.open(r'C:\Users\ruben\nq-backtest\continuous2.json'))
SIZING = json.load(io.open(r'C:\Users\ruben\nq-backtest\sizing_panel.json'))
WEALTH = json.load(io.open(r'C:\Users\ruben\nq-backtest\wealth_panel.json'))
# The last-hour candle study (lh5_*.py, rf_*.py): the verdicts and the forest's stored
# out-of-sample decisions, replayed by the page rather than recomputed. Built by
# lh5_pack.viewer_payload(); the study's config hash travels with it.
import lh5_pack
LH5 = lh5_pack.viewer_payload()
# The RF2 study's verdict sentence and its stored decisions by day and slot minute,
# from rf2_pack.viewer_payload(); the forest itself never runs in the page.
import rf2_pack
import bo_pack
RF2 = rf2_pack.viewer_payload()
# The three Breakout Academy settings: fill minute, side and level per day (bo_pack.py)
BO = bo_pack.viewer_payload()
# The news calendar for the 'custom' strategy: Forex Factory reconciled against two
# Investing.com sources per-occurrence, built by build_news_calendar.py. Checked in like
# the packs above, not regenerated here.
NEWSCAL = json.load(io.open(r'C:\Users\ruben\nq-backtest\news_calendar.json'))

HTML = r"""<meta charset="utf-8">
<title>Tape Reader</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230f1115'/%3E%3Crect x='7' y='9' width='5' height='14' fill='%2326a69a'/%3E%3Crect x='9' y='5' width='1' height='22' fill='%2326a69a'/%3E%3Crect x='19' y='12' width='5' height='10' fill='%23ef5350'/%3E%3Crect x='21' y='8' width='1' height='18' fill='%23ef5350'/%3E%3C/svg%3E">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root{
  --ground:#0f1115; --panel:#161a21; --panel-2:#1b2029; --rule:#252b36;
  --rule-soft:#1e232c; --ink:#dae0ea; --ink-dim:#8e99ac; --ink-faint:#5d6779;
  --up:#4bb073; --down:#d1565a; --long:#5b9bd5; --short:#d98a55; --accent:#d8a24a;
  --i1:#6ea8dc; --i2:#c98ad4; --i3:#7fc9a8; --i4:#d4a95e;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;
  --sans:"IBM Plex Sans",-apple-system,"Segoe UI",sans-serif;
}
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);font-family:var(--sans);
     height:100vh;overflow:hidden;font-size:13px}
.app{display:grid;grid-template-rows:auto auto auto minmax(0,1fr) auto auto auto;height:100vh;overflow:hidden}
.top{display:flex;align-items:center;gap:14px;padding:7px 12px;background:var(--panel);
     border-bottom:1px solid var(--rule);flex-wrap:wrap}
.brand{font-weight:600;font-size:13px;white-space:nowrap}
.brand span{color:var(--accent)}
.sub{color:var(--ink-dim);font-family:var(--mono);font-size:10.5px;white-space:nowrap}
.spacer{flex:1}
.ohlc{font-family:var(--mono);font-size:11px;color:var(--ink-dim);display:flex;gap:9px;
      white-space:nowrap;font-variant-numeric:tabular-nums}
.ohlc b{color:var(--ink);font-weight:500}
.bar{display:flex;align-items:center;gap:5px;padding:5px 12px;background:var(--panel-2);
     border-bottom:1px solid var(--rule);flex-wrap:wrap}
.bar.b3{background:var(--panel);padding-top:4px;padding-bottom:4px}
.btn{background:var(--panel);border:1px solid var(--rule);color:var(--ink-dim);
     font-family:var(--mono);font-size:10.5px;padding:3px 8px;border-radius:3px;cursor:pointer}
/* :not(.on) so this cannot outrank .btn.on, which is more specific in
   intent but less specific to the cascade -- without it an active button
   keeps this background and .btn.on's dark text, and the label vanishes */
.bar.b3 .btn:not(.on){background:var(--panel-2)}
.btn:hover{border-color:var(--accent);color:var(--ink)}
.btn:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.btn.on{background:var(--accent);border-color:var(--accent);color:#171208;font-weight:600}
.btn:disabled{opacity:.35;cursor:not-allowed;pointer-events:none}
.seg{display:flex;gap:0}
.seg .btn{border-radius:0;margin-left:-1px}
.seg .btn:first-child{border-radius:3px 0 0 3px;margin-left:0}
.seg .btn:last-child{border-radius:0 3px 3px 0}
input,select{background:var(--panel);border:1px solid var(--rule);color:var(--ink);
     font-family:var(--mono);font-size:10.5px;padding:3px 5px;border-radius:3px}
.lbl{font-family:var(--mono);font-size:9.5px;color:var(--ink-faint);
     text-transform:uppercase;letter-spacing:.07em}
.stat{font-family:var(--mono);font-size:10.5px;color:var(--ink-dim);white-space:nowrap;
      font-variant-numeric:tabular-nums}
.pos{color:var(--up)} .neg{color:var(--down)}
.main{display:grid;grid-template-columns:1fr 244px;min-height:0}
.chartwrap{position:relative;min-width:0;min-height:0;overflow:hidden}
canvas{display:block;width:100%;height:100%}
.hint{position:absolute;left:10px;bottom:6px;font-family:var(--mono);font-size:9.5px;
      color:var(--ink-faint);pointer-events:none}
.tip{position:absolute;pointer-events:none;background:var(--panel);border:1px solid var(--rule);
     border-radius:4px;padding:7px 9px;font-family:var(--mono);font-size:10.5px;line-height:1.5;
     opacity:0;transition:opacity .1s;max-width:250px;z-index:5;box-shadow:0 6px 22px rgba(0,0,0,.6)}
.tip.on{opacity:1}
.tip .hd{font-weight:600;margin-bottom:3px}
.rail{background:var(--panel);border-left:1px solid var(--rule);overflow-y:auto;min-height:0}
.rail h3{margin:0;padding:7px 10px 5px;font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;
         color:var(--ink-faint);font-weight:600;border-bottom:1px solid var(--rule-soft);
         position:sticky;top:0;background:var(--panel);z-index:1}
.kv{display:grid;grid-template-columns:1fr auto;gap:2px 8px;padding:8px 10px;
    font-family:var(--mono);font-size:10.5px;border-bottom:1px solid var(--rule-soft)}
.kv span{color:var(--ink-faint)} .kv b{color:var(--ink);font-weight:500;text-align:right}
.srcline{font-family:var(--mono);font-size:9.5px;color:var(--ink-faint);text-align:center;
         margin:-4px 0 4px;padding:0 10px}
.trade{padding:6px 10px;border-bottom:1px solid var(--rule-soft);cursor:pointer;
       font-family:var(--mono);font-size:10px;border-left:2px solid transparent}
.trade:hover{background:var(--panel-2)}
.trade.on{background:var(--panel-2);border-left-color:var(--accent)}
.trade .r1{display:flex;justify-content:space-between;margin-bottom:2px}
.trade .r2{color:var(--ink-faint);font-size:9.5px;display:flex;justify-content:space-between}
.tag{font-size:8.5px;padding:1px 4px;border-radius:2px;font-weight:600}
.tag.L{background:rgba(91,155,213,.16);color:var(--long)}
.tag.S{background:rgba(217,138,85,.16);color:var(--short)}
/* the account stage a trade was taken in: the word carries it, the tint only helps */
.tag.E{background:var(--panel-2);color:var(--ink-dim)}
.tag.F{background:rgba(216,162,74,.16);color:var(--accent)}
.empty{padding:12px 10px;color:var(--ink-faint);font-family:var(--mono);font-size:10px}
.nav{height:50px;background:var(--panel);border-top:1px solid var(--rule);position:relative}
.nav canvas{cursor:ew-resize}
.navlbl{position:absolute;left:8px;top:4px;font-family:var(--mono);font-size:9px;
        color:var(--ink-faint);pointer-events:none}
.ledger{background:var(--panel);border-top:1px solid var(--rule);height:158px;overflow:auto;
        resize:vertical;min-height:0}
.ledger.hid{display:none}
.ledger::-webkit-scrollbar,.rail::-webkit-scrollbar{width:7px;height:7px}
.ledger::-webkit-scrollbar-thumb,.rail::-webkit-scrollbar-thumb{background:var(--rule);border-radius:3px}
table{border-collapse:collapse;width:100%;font-family:var(--mono);font-size:10px}
th{position:sticky;top:0;background:var(--panel-2);color:var(--ink-faint);font-weight:600;
   text-align:right;padding:4px 7px;border-bottom:1px solid var(--rule);white-space:nowrap;
   font-size:9px;letter-spacing:.04em;text-transform:uppercase}
th:first-child,td:first-child{text-align:left}
td{padding:3px 7px;border-bottom:1px solid var(--rule-soft);text-align:right;white-space:nowrap;
   font-variant-numeric:tabular-nums;color:var(--ink-dim)}
tr.on td{background:var(--panel-2);color:var(--ink)}
tr:hover td{background:var(--panel-2);cursor:pointer}
td b{color:var(--ink);font-weight:500}
.ok{color:var(--up)} .bad{color:var(--down)}
.errbar{position:fixed;left:12px;right:12px;bottom:12px;z-index:60;display:none;
        background:var(--panel);border:1px solid var(--down);border-left:4px solid var(--down);
        border-radius:4px;padding:10px 12px;font-family:var(--mono);font-size:11.5px;
        color:var(--ink);box-shadow:0 8px 28px rgba(0,0,0,.6);line-height:1.5}
.errbar.on{display:block}
.errbar .at{color:var(--ink-faint);font-size:10px}
.errbar .btn{margin-left:10px;vertical-align:middle}
.drop{position:fixed;inset:0;background:rgba(15,17,21,.93);z-index:20;display:none;
      align-items:center;justify-content:center;text-align:center;font-family:var(--mono);
      border:2px dashed var(--accent);color:var(--ink)}
.drop.on{display:flex}
.drop span{color:var(--ink-faint);font-size:11px}
.modal{position:fixed;inset:0;background:rgba(8,9,12,.82);z-index:30;display:none;
       align-items:center;justify-content:center;padding:20px}
.modal.on{display:flex}
.sheet{background:var(--panel);border:1px solid var(--rule);border-radius:6px;padding:20px 22px;
       max-width:640px;max-height:84vh;overflow:auto;line-height:1.6}
.sheet h2{margin:0 0 4px;font-size:15px}
.sheet h3{margin:14px 0 4px;font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;
          color:var(--accent);font-weight:600}
.sheet p{margin:5px 0;color:var(--ink-dim);font-size:12px}
.sheet code,.sheet kbd{font-family:var(--mono);color:var(--ink);font-size:11px}
.sheet kbd{background:var(--panel-2);border:1px solid var(--rule);border-radius:3px;padding:1px 5px}
.sheet pre{background:var(--ground);border:1px solid var(--rule-soft);border-radius:4px;
           padding:9px 11px;font-family:var(--mono);font-size:10.5px;overflow-x:auto;
           color:var(--ink-dim);margin:5px 0}
.sheet table{font-size:11px} .sheet td{text-align:left;color:var(--ink-dim)}
.cal{position:fixed;z-index:40;background:var(--panel);border:1px solid var(--rule);
     border-radius:6px;padding:10px;display:none;box-shadow:0 10px 34px rgba(0,0,0,.6);width:258px}
.cal.on{display:block}
.calhead{display:flex;align-items:center;gap:4px;margin-bottom:7px}
.caltitle{flex:1;text-align:center;font-family:var(--mono);font-size:11.5px;font-weight:600}
.caldow,.calgrid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px}
.caldow span{text-align:center;font-family:var(--mono);font-size:8.5px;color:var(--ink-faint);
             text-transform:uppercase}
.cell{aspect-ratio:1;display:flex;align-items:center;justify-content:center;border-radius:3px;
      font-family:var(--mono);font-size:10px;color:var(--ink-faint);border:1px solid transparent}
.cell.has{cursor:pointer;color:var(--ink);border-color:var(--rule-soft)}
.cell.has:hover{border-color:var(--accent)}
.cell.on{background:var(--accent);color:#171208;font-weight:600}
.cell.up{background:rgba(75,176,115,.22)} .cell.dn{background:rgba(209,86,90,.22)}
.calfoot{margin-top:7px;font-family:var(--mono);font-size:9.5px;color:var(--ink-faint);
         border-top:1px solid var(--rule-soft);padding-top:6px;line-height:1.5}
.bigrow{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:10px 0}
.bignum{background:var(--panel-2);border:1px solid var(--rule-soft);border-radius:4px;
        padding:9px 10px;text-align:center}
.bignum .bl{font-family:var(--mono);font-size:9px;letter-spacing:.06em;
            text-transform:uppercase;color:var(--ink-faint)}
.bignum .bv{font-family:var(--mono);font-size:21px;font-weight:600;color:var(--ink);
            margin-top:3px;font-variant-numeric:tabular-nums}
.bignum .bv.ok{color:var(--up)} .bignum .bv.bad{color:var(--down)}
.sz{max-width:none;width:min(1180px,94vw)}
/* .why, not .hint: the page already has a .hint, and it is the chart's
   absolutely-positioned overlay in the bottom-left corner */
#rptOverlay{position:fixed;inset:0;z-index:60;background:var(--ground);
  display:none;flex-direction:column}
#rptOverlay.on{display:flex}
.rptbar{display:flex;align-items:center;gap:12px;padding:8px 14px;
  background:var(--panel);border-bottom:1px solid var(--rule);flex:0 0 auto}
.rptbar span{color:var(--ink-faint);font-family:var(--mono);font-size:10.5px}
.rptbar button{margin-left:auto}
.rptbody{flex:1 1 auto;overflow:auto;padding:24px 30px 70px}
.rptbody .rpt{max-width:1020px;margin:0 auto}
.rptbody h1{font-size:25px;margin:0 0 6px}
.rptbody h2{font-size:18px;margin:34px 0 6px;padding-top:12px;
  border-top:1px solid var(--rule);color:var(--accent)}
.rptbody h3{font-size:13.5px;margin:14px 0 4px}
.rptbody p{max-width:74ch;color:var(--ink-dim);line-height:1.6}
.rptbody .dim{color:var(--ink-faint);font-size:12.5px}
.rptbody table.t{width:100%;border-collapse:collapse;font-family:var(--mono);
  font-size:12px;margin:10px 0}
.rptbody .t td,.rptbody .t th{padding:5px 9px;border-bottom:1px solid var(--rule-soft);
  text-align:left}
.rptbody .t th{color:var(--ink-dim);font-weight:500;font-size:11px}
.rptbody .t td.r,.rptbody .t th.r{text-align:right}
.rptbody .t td.n{color:var(--ink-faint);font-size:11px}
.rptbody .t tr.hi{background:rgba(216,162,74,.10)}
.rptbody .t .g{color:var(--up)}.rptbody .t .b{color:var(--down)}
.rptbody .fig{background:var(--panel);border:1px solid var(--rule);border-radius:7px;
  padding:10px;margin:8px 0;overflow-x:auto}
.rptbody svg{display:block;width:100%;height:auto}
.rptbody svg .g{stroke:var(--rule-soft)}
.rptbody svg .z{stroke:var(--rule)}
.rptbody svg .ax{fill:var(--ink-faint);font:9.5px var(--mono)}
.rptbody .g2{display:grid;grid-template-columns:1fr 1fr;gap:22px}
@media(max-width:840px){.rptbody .g2{grid-template-columns:1fr}}
.rptbody .verdict{font-family:var(--mono);font-size:14px;padding:11px 14px;
  border-radius:6px;margin:12px 0;border:1px solid}
.rptbody .verdict.ok{background:rgba(75,176,115,.12);border-color:var(--up);color:#7fd3a2}
.rptbody .verdict.bad{background:rgba(209,86,90,.12);border-color:var(--down);color:#e38f92}
.rptbody ul.as{max-width:74ch;color:var(--ink-dim);line-height:1.6}
.rptbody ul.as li{margin:7px 0}
.why{border-bottom:1px dotted var(--ink-faint);cursor:help}
.cmp{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:11px;margin-top:4px}
.cmp th,.cmp td{padding:4px 8px;border-bottom:1px solid var(--rule-soft);text-align:right}
.cmp th:first-child,.cmp td:first-child{text-align:left;font-family:var(--sans);
    color:var(--ink-dim);white-space:nowrap}
.cmp thead th{color:var(--ink-dim);font-family:var(--sans);font-size:10.5px;font-weight:500;
    border-bottom:1px solid var(--rule)}
.cmp col.on{background:rgba(216,162,74,.09)}
.cmp thead th.on{color:var(--accent)}
.cmp tr.big td{font-size:13px;padding-top:7px;padding-bottom:7px}
.cmp tr.big td:first-child{font-size:12px;color:var(--ink)}
/* the ensemble table has nine columns in a 640px sheet: smaller type, tighter
   cells, and no number may wrap onto a second line */
.cmp.ens{font-size:10px}
.cmp.ens th,.cmp.ens td{padding:3px 5px;white-space:nowrap}
.cmp.ens thead th{font-size:9.5px}
.cmp.ens tr.big td{font-size:11px;padding-top:5px;padding-bottom:5px}
.cmp.ens tr.big td:first-child{font-size:11px}
.asmp{margin-top:10px}
.asmp h4{margin:12px 0 4px;font-size:11px;color:var(--accent);text-transform:uppercase;
    letter-spacing:.07em}
.asmp ol{margin:0;padding-left:20px}
.asmp li{margin:5px 0;line-height:1.5;color:var(--ink-dim);font-size:11.5px}
.asmp li b{color:var(--ink)}
.bias{font-family:var(--mono);font-size:9px;padding:1px 5px;border-radius:8px;margin-left:5px;
    white-space:nowrap;vertical-align:1px}
.bias.opt{background:rgba(209,86,90,.16);color:#e08a8d}
.bias.con{background:rgba(75,176,115,.16);color:#6cc48d}
.bias.neu{background:rgba(142,153,172,.14);color:var(--ink-dim)}
.tagrow{display:flex;gap:4px;align-items:center;flex-wrap:wrap;padding:5px 10px;
        border-bottom:1px solid var(--rule-soft)}
.tagchip{font-family:var(--mono);font-size:9.5px;padding:2px 7px;border-radius:9px;
         cursor:pointer;border:1px solid transparent;white-space:nowrap}
.tagchip.off{opacity:.35}
.tagpick{display:flex;gap:4px;flex-wrap:wrap;margin:6px 0}
.szbar{display:flex;gap:6px;align-items:center;margin:10px 0 4px;flex-wrap:wrap}
.szgrid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:10px}
.szfig{background:var(--ground);border:1px solid var(--rule-soft);border-radius:4px;padding:8px}
.szfig h4{margin:0 0 2px;font-family:var(--mono);font-size:10.5px;font-weight:600;
          color:var(--accent);letter-spacing:.04em;text-transform:uppercase}
.szfig p{margin:0 0 6px;font-size:10.5px;color:var(--ink-faint);line-height:1.4}
.szfig svg{display:block;width:100%}
.sztab{width:100%;font-family:var(--mono);font-size:10.5px;border-collapse:collapse;margin-top:6px}
.sztab th{position:static;background:var(--panel-2);font-size:9px}
.sztab td{padding:3px 7px}
.szdot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:4px}
.verdict{font-family:var(--mono);font-weight:600;font-size:13px;letter-spacing:.08em;
         text-align:center;padding:7px;border-radius:4px;margin:8px 0}
.verdict.pass{background:rgba(75,176,115,.18);color:var(--up);border:1px solid var(--up)}
.verdict.fail{background:rgba(209,86,90,.18);color:var(--down);border:1px solid var(--down)}
.verdict.incomplete{background:var(--panel-2);color:var(--ink-dim);border:1px solid var(--rule)}
.setgrid{display:grid;grid-template-columns:1fr 1fr;gap:14px 20px;margin-top:6px}
.setrow{display:flex;align-items:center;justify-content:space-between;gap:10px;
        font-family:var(--mono);font-size:11px;color:var(--ink-dim);
        padding:3px 0;border-bottom:1px solid var(--rule-soft)}
.setrow input[type=range]{width:110px;accent-color:var(--accent)}
.setrow input[type=color]{width:34px;height:20px;padding:0;border:1px solid var(--rule);
                          background:none;cursor:pointer;border-radius:3px}
.setrow input[type=number]{width:58px}
.setrow input[type=checkbox]{accent-color:var(--accent);width:14px;height:14px;cursor:pointer}
.setrow .v{color:var(--ink);min-width:36px;text-align:right}
.setrow input[type=date]{font-family:var(--mono);font-size:11px}
/* the one number the strategy panel leads with: proportional figures in the
   body sans, never the mono, so it reads as a figure and not a table cell */
.sthero{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.sthero b{font-family:var(--sans);font-weight:600;font-size:48px;line-height:1;color:var(--ink);
          font-variant-numeric:normal;letter-spacing:-.01em}
.sthero span{font-family:var(--mono);font-size:10.5px;color:var(--ink-dim);line-height:1.5}
/* pinned to the top of the scrolling sheet so the figure stays in view while
   a field far below it is being edited; bleeds over the sheet's side padding */
.stpin{position:sticky;top:-20px;z-index:2;background:var(--panel);margin:6px -22px 0;
       padding:10px 22px 8px;border-bottom:1px solid var(--rule-soft)}
.stpair{display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
/* the per-stage strategy block; gold while the funded strategy is being edited */
.stgbox{border:1px solid var(--rule);border-radius:5px;padding:8px 12px 10px;margin-top:14px}
.stgbox.funded{border-color:var(--accent);background:rgba(216,162,74,.035)}
/* Strategy -> Custom: the news picker, its three modes and the live preview */
.nwbox{border:1px solid var(--rule);border-radius:6px;padding:4px 12px 12px;margin-top:6px;background:var(--panel-2)}
.nwstep{font-family:var(--mono);font-size:9.5px;color:var(--accent);letter-spacing:.07em;
        text-transform:uppercase;margin:12px 0 6px;display:flex;gap:7px;align-items:center}
.nwstep i{font-style:normal;display:inline-flex;width:16px;height:16px;border-radius:50%;
          border:1px solid var(--accent);align-items:center;justify-content:center;font-size:9px}
.nwhint{color:var(--ink-faint);font-size:9.5px}
.nwlab{min-width:118px}
.nwnote{font-size:10.5px !important;color:var(--ink-faint) !important;line-height:1.5;margin:6px 0 !important}
.nwchips{display:flex;flex-wrap:wrap;gap:5px;margin:8px 0 4px}
.nwchip{font-family:var(--mono);font-size:10px;padding:2px 3px 2px 9px;border-radius:10px;color:var(--ink);
        background:rgba(216,162,74,.14);border:1px solid rgba(216,162,74,.5);display:inline-flex;gap:3px;align-items:center}
.nwchip button{background:none;border:0;color:var(--ink-dim);cursor:pointer;padding:0 4px;font-size:12px;line-height:1}
.nwchip button:hover{color:var(--down)}
.nwsearch{width:100%;margin:6px 0;font-size:11.5px;padding:5px 8px}
.nwlist{max-height:320px;overflow-y:auto;border:1px solid var(--rule-soft);border-radius:5px;background:var(--panel)}
.nwlist details{border-bottom:1px solid var(--rule-soft)}
.nwlist details:last-child{border-bottom:0}
.nwlist summary{cursor:pointer;padding:6px 10px;font-family:var(--mono);font-size:9.5px;color:var(--ink-dim);
                text-transform:uppercase;letter-spacing:.05em;display:flex;justify-content:space-between;list-style:none}
.nwlist summary::-webkit-details-marker{display:none}
.nwlist summary span:first-child::before{content:'\25B8';display:inline-block;width:12px;color:var(--ink-faint)}
.nwlist details[open] summary span:first-child::before{content:'\25BE'}
.nwlist summary:hover{color:var(--ink)}
.nwrow{display:grid;grid-template-columns:16px 1fr auto 86px;gap:8px;align-items:center;padding:3px 10px 3px 22px;
       font-size:11.5px;color:var(--ink-dim);cursor:pointer}
.nwrow:hover{background:var(--panel-2);color:var(--ink)}
.nwrow.on{color:var(--ink);background:rgba(216,162,74,.07)}
.nwrow input{accent-color:var(--accent);margin:0}
.nwrow .t{font-family:var(--mono);font-size:10px;color:var(--ink-dim)}
.nwrow .n{font-family:var(--mono);font-size:9.5px;color:var(--ink-faint);text-align:right}
.nwprev{border:1px solid var(--rule);border-left:3px solid var(--accent);border-radius:5px;padding:10px 12px;
        margin-top:14px;background:var(--panel)}
.nwrule{font-size:12.5px !important;color:var(--ink) !important;line-height:1.5;margin:0 0 4px !important}
.nwstats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:10px 0 6px}
.nwstat b{display:block;font-family:var(--sans);font-size:19px;font-weight:600;color:var(--ink);line-height:1.1}
.nwstat span{font-family:var(--mono);font-size:9px;color:var(--ink-faint);text-transform:uppercase;letter-spacing:.04em}
.nwwarn{border-radius:4px;padding:7px 10px;margin:6px 0;font-size:11.5px;line-height:1.45;color:var(--ink);
        display:flex;gap:10px;align-items:center;justify-content:space-between}
.nwwarn .btn{flex:none}
.nwwarn.bad{background:rgba(209,86,90,.12);border:1px solid rgba(209,86,90,.55)}
.nwwarn.mid{background:rgba(216,162,74,.10);border:1px solid rgba(216,162,74,.5)}
.nwwarn.ok{background:rgba(75,176,115,.09);border:1px solid rgba(75,176,115,.4)}
.nwuphead{font-family:var(--mono);font-size:9px;color:var(--ink-faint);text-transform:uppercase;
          letter-spacing:.05em;margin:10px 0 3px}
.nwup{display:grid;grid-template-columns:118px 64px 1fr;gap:6px;font-family:var(--mono);font-size:10.5px;
      color:var(--ink-dim);padding:2px 0;border-top:1px solid var(--rule-soft)}
.setrow .tag{margin-right:4px;vertical-align:1px}
/* the Strategy sheet sits to the side with the chart live underneath, so the
   trade boxes can be watched moving as a number is changed; the backdrop lets
   pointer events through, the sheet itself does not */
.modal.peek{background:rgba(8,9,12,.12);justify-content:flex-end;padding-right:14px;pointer-events:none}
.modal.peek .sheet{pointer-events:auto;box-shadow:0 14px 44px rgba(0,0,0,.55)}
.swatches{display:flex;gap:5px;flex-wrap:wrap}
.sw{width:22px;height:22px;border-radius:3px;border:2px solid transparent;cursor:pointer}
.sw.on{border-color:var(--accent)}
@media(max-width:900px){.main{grid-template-columns:1fr}.rail{display:none}}
</style>

<div class="app">
  <div class="top">
    <div class="brand">TAPE <span>READER</span></div>
    <div class="sub" id="sub"></div>
    <div class="spacer"></div>
    <div class="ohlc" id="ohlc"></div>
  </div>

  <div class="bar">
    <span class="lbl">TF</span>
    <div class="seg" id="tfseg"></div>
    <span class="lbl">Type</span>
    <div class="seg" id="ctseg"></div>
    <span class="lbl">Scale</span>
    <button class="btn" id="blog">Log</button>
    <button class="btn" id="bfit">Fit</button>
    <span class="lbl">Tools</span>
    <button class="btn" id="bmag" title="Snap the crosshair to the nearest O/H/L/C">Magnet</button>
    <button class="btn" id="bfilt" title="Restrict the chart to a time-of-day window">RTH</button>
    <button class="btn" id="bmeas" title="Drag to measure points, % and bars">Measure</button>
    <button class="btn on" id="btr">Trades</button>
    <div class="spacer"></div>
    <div class="stat" id="vstat"></div>
  </div>

  <div class="bar b3">
    <span class="lbl">Data</span>
    <label class="btn" for="fbars">Bars</label><input type="file" id="fbars" accept=".csv,.json,.txt" hidden>
    <button class="btn" id="brth" title="On: a loaded bar file is converted to New York time (when its timestamps carry a UTC offset, as databento exports do) and cut to the 09:30-15:59 day session, exactly as the shipped NQ tape was built. Off: every hour in the file is kept and a session is a calendar day of the converted clock. Applies to the next file you load.">RTH</button>
    <label class="btn" for="ftrades">Trades</label><input type="file" id="ftrades" accept=".csv,.json,.txt" hidden>
    <button class="btn" id="demo">Demo</button>
    <span class="lbl">Go</span>
    <button class="btn" id="dbtn">&#128197; <span id="dbtnlbl">&mdash;</span></button>
    <button class="btn" id="tprev" title="Previous trade">&#9664;</button>
    <button class="btn" id="tnext" title="Next trade">&#9654;</button>
    <input id="tgo" size="5" placeholder="#" title="Jump to trade number">
    <span class="lbl">Replay</span>
    <button class="btn" id="rtog">&#9210;</button>
    <button class="btn" id="rstep">Step</button>
    <button class="btn" id="rplay">&#9654;</button>
    <select id="rspd"><option>1x</option><option selected>4x</option><option>10x</option><option>30x</option></select>
    <button class="btn" id="bind">Indicators <span id="bindn"></span></button>
    <div class="spacer"></div>
    <button class="btn" id="bacct" title="Simulate a real balance and a prop-firm evaluation: size, costs, liquidation on unrealised equity, and how many accounts pass or fail">Prop firm</button>
    <button class="btn" id="beq" title="Running account equity under the chart. Drag its top edge to resize.">Equity</button>
    <button class="btn on" id="ltog">Ledger</button>
    <button class="btn" id="bfull">Fullscreen</button>
    <button class="btn" id="btags" title="Tag trades by setup and compare performance between them">Setups</button>
    <button class="btn" id="bwealth" title="Does buying many evaluations with a zero-edge strategy make money? The wealth trajectory, over many runs">Wealth</button>
    <button class="btn" id="bstrat" title="Pick a strategy and run it against the loaded bars with your balance and the firm's rules">Strategy</button>
    <button class="btn" id="bsize" title="Sizing study: what every contract size does to this account, over many runs">Sizing</button>
    <button class="btn" id="bset">Settings</button>
    <button class="btn" id="bhelp">?</button>
  </div>

  <div class="main">
    <div class="chartwrap" id="wrap">
      <canvas id="cv"></canvas>
      <div class="why" id="hint"></div>
      <div class="tip" id="tip"></div>
    </div>
    <div class="rail">
      <h3>Performance</h3><div id="stats"></div>
      <h3 id="railh">Trades in view</h3><div id="rail"></div>
    </div>
  </div>

  <div class="nav" id="nav"><canvas id="navcv"></canvas><div class="navlbl" id="navlbl"></div></div>

  <div class="tagrow" id="tagrow"></div>
  <div class="ledger">
    <table><thead><tr>
      <th>#</th><th>Acct</th><th>Date</th><th>In</th><th>Out</th><th>Side</th><th>Size</th><th>Entry</th>
      <th>Stop</th><th>Target</th><th>Exit</th><th>Bind</th><th>MAE</th><th>MFE</th>
      <th>Pts</th><th>Net</th><th>From</th><th>Balance</th><th>Chk</th>
    </tr></thead><tbody id="led"></tbody></table>
  </div>
</div>

<div class="errbar" id="errbar"></div>
<div class="drop" id="drop"><div>Drop a <b>bars</b> or <b>trades</b> file<br><span>CSV or JSON &middot; detected automatically</span></div></div>
<div class="cal" id="cal">
  <div class="calhead">
    <button class="btn" id="cy0">&laquo;</button><button class="btn" id="cm0">&lsaquo;</button>
    <div class="caltitle" id="caltitle"></div>
    <button class="btn" id="cm1">&rsaquo;</button><button class="btn" id="cy1">&raquo;</button>
  </div>
  <div class="caldow"><span>Mo</span><span>Tu</span><span>We</span><span>Th</span><span>Fr</span><span>Sa</span><span>Su</span></div>
  <div class="calgrid" id="calgrid"></div>
  <div class="calfoot" id="calfoot"></div>
</div>
<div class="modal" id="modal"><div class="sheet" id="sheet"></div></div>

<script>
__CORE__

/* ================================================================
   TAPE READER -- UI layer.
   All non-trivial logic lives in Core above, which is ES5 and is
   unit-tested headlessly against the real data (74 assertions).
   This file is presentation, interaction and wiring only.
   ================================================================ */
const RAW = __DATA__;
const SIZING = __SIZING__;
const WEALTH = __WEALTH__;
const LH5 = __LH5__;
const RF2 = __RF2__;
const BO = __BO__;
const NEWSCAL = __NEWSCAL__;

function bytes(b64){
  const s = atob(b64), u = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i);
  return u;
}
function unpack(b64){ return new Int16Array(bytes(b64).buffer); }

/* The four price arrays ship as Int8 deltas plus an exception list: ~98.9% of
   one-minute moves fit in a byte, so this halves the largest part of the page.
   Verified byte-exact against the Int16 original before shipping, and read as
   a stream by chan()/chanAt() above. */
/* One channel of Int8 deltas plus its ascending exception list. Returned as
   three flat arrays rather than an object with an accessor: the decode loop
   below walks them inline, because a call per bar per channel is 1.26M calls
   and only a JIT makes those free. */
function chan(o){
  return [new Int8Array(bytes(o.d).buffer),
          new Int32Array(bytes(o.ei).buffer),
          new Int32Array(bytes(o.ev).buffer)];
}
function buildBars(raw){
  const T = raw.tick, n = raw.n;
  const v2 = !!raw.v2;
  const o = new Float64Array(n), h = new Float64Array(n),
        l = new Float64Array(n), c = new Float64Array(n);
  let acc = raw.bars.base;
  if (v2){
    /* decoded straight into o/h/l/c: four 2.5 MB temporaries and four extra
       passes fewer than materialising each delta array first */
    const O = chan(raw.bars.o), H = chan(raw.bars.h),
          L = chan(raw.bars.l), C = chan(raw.bars.c);
    const oD = O[0], oI = O[1], oV = O[2], hD = H[0], hI = H[1], hV = H[2],
          lD = L[0], lI = L[1], lV = L[2], cD = C[0], cI = C[1], cV = C[2];
    const oN = oI.length, hN = hI.length, lN = lI.length, cN = cI.length;
    let po = 0, ph = 0, pl = 0, pc = 0;
    for (let i = 0; i < n; i++){
      const dO = (po < oN && oI[po] === i) ? oV[po++] : oD[i];
      const dH = (ph < hN && hI[ph] === i) ? hV[ph++] : hD[i];
      const dL = (pl < lN && lI[pl] === i) ? lV[pl++] : lD[i];
      const dC = (pc < cN && cI[pc] === i) ? cV[pc++] : cD[i];
      acc = i === 0 ? raw.bars.base : acc + dO * T;
      o[i] = acc; h[i] = acc + dH * T; l[i] = acc + dL * T; c[i] = acc + dC * T;
    }
  } else {
    const dO = unpack(raw.bars.o), dH = unpack(raw.bars.h),
          dL = unpack(raw.bars.l), dC = unpack(raw.bars.c);
    for (let i = 0; i < n; i++){
      acc = i === 0 ? raw.bars.base : acc + dO[i] * T;
      o[i] = acc; h[i] = acc + dH[i] * T; l[i] = acc + dL[i] * T; c[i] = acc + dC[i] * T;
    }
  }
  /* volume is kept in the width it ships in rather than widened to Float64:
     identical values, a quarter of the memory, one fewer pass */
  const v = raw.bars.v ? unpack(raw.bars.v) : null;
  /* every bar sits at its session's opening minute plus its offset -- verified
     across all 315,900 bars with zero exceptions, so the array is not shipped */
  let mins;
  if (v2){
    mins = new Int16Array(n);
    raw.sessions.forEach(sn => {
      for (let i = sn.a; i <= sn.b; i++) mins[i] = sn.m0 + (i - sn.a);
    });
  } else mins = unpack(raw.mins);
  return {n, o, h, l, c, v, mins, sessions: raw.sessions};
}

/* Trades ship columnar: one array per field rather than 4,670 objects, which
   removed a megabyte of repeated key names. `day` is not shipped at all -- it
   is the day of the session owning the entry bar. */
function buildTrades(raw){
  if (!raw.v2) return raw.trades || [];
  const n = raw.ntrades, cols = raw.tcols, con = raw.tconst || {};
  const out = new Array(n);
  const sess = raw.sessions;
  let si = 0;
  for (let i = 0; i < n; i++){
    const t = {};
    for (const k in con) t[k] = con[k];
    for (const k in cols){
      const c = cols[k];
      t[k] = c.vocab ? c.vocab[c.idx[i]] : c[i];
    }
    while (si < sess.length - 1 && sess[si].b < t.entry_bar) si++;
    while (si > 0 && sess[si].a > t.entry_bar) si--;
    t.day = sess[si].day;
    out[i] = t;
  }
  return out;
}

const CSSV = getComputedStyle(document.documentElement);
const cv_ = n => CSSV.getPropertyValue(n).trim();
const money = v => (v < 0 ? '-$' : '$') + Math.abs(v).toFixed(2);
/* whole-dollar, thousands-separated -- cents are noise on five-figure wealth */
/* group digits ourselves: toLocaleString does not group under Duktape and is
   locale-dependent in a browser, and these are fixed dollar figures */
const sep = n => { const t = String(n), i = t.indexOf('.');
                   const head = i < 0 ? t : t.slice(0, i);
                   return head.replace(/\B(?=(\d{3})+(?!\d))/g, ',') +
                          (i < 0 ? '' : t.slice(i)); };
/* round halves to even, as the analysis that produced these figures does.
   With an even number of runs the median is often an exact half, and half-up
   rounding would put the page a dollar away from the numbers it reports. */
const rhe = v => { const f = Math.floor(v), d = v - f;
                   return d > 0.5 ? f + 1 : d < 0.5 ? f : (f % 2 ? f + 1 : f); };
const money0 = v => (v < 0 ? '-$' : '$') + sep(rhe(Math.abs(v)));
/* the true median: with an even count it is the average of the middle two,
   which is what the reported figures use */
const medOf = a => { const v = a.slice().sort((x, y) => x - y), n = v.length, h = n >> 1;
                     return n % 2 ? v[h] : (v[h - 1] + v[h]) / 2; };
/* Counts are discrete -- you cannot buy half an evaluation or reach half a
   payout. With an even number of runs the median can still land between two
   of them, so the cell shows the rounded count and carries the exact value in
   its hover, rather than quietly presenting a number no run produced. */
const cnt = v => sep(rhe(v));
const cntCell = (v, seeds) => v % 1
  ? '<span class="why" title="Exact median across ' + seeds + ' runs: ' + v +
    '. An even number of runs puts the median between two of them, so this is rounded.">' +
    cnt(v) + '</span>'
  : cnt(v);
/* how often the median run buys an account, stated for the size on screen
   rather than asserted once and wrong for the other two */
const pace = (evals, sessions) => {
  const g = sessions / Math.max(evals, 1e-9);
  return g <= 1.25 ? 'close to one a session'
       : g < 10 ? 'about one every ' + (g < 3 ? g.toFixed(1) : Math.round(g)) + ' sessions'
       : 'about one every ' + Math.round(g) + ' sessions';
};
/* the quote is escaped with split/join rather than /"/g on purpose: a bare
   quote inside a regex literal is invisible to simple JS scanners */
const esc = t => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;')
                          .replace(/>/g, '&gt;').split('"').join('&quot;')
                          .split("'").join('&#39;');
const hhmm = m => String(m / 60 | 0).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0');
const TFS = [['1m',1],['2m',2],['5m',5],['15m',15],['30m',30],['1H',60],['D',390]];
const CTS = [['Candle','candle'],['Hollow','hollow'],['Bar','bar'],['Line','line'],['Area','area'],['HA','ha']];
/* ---------------------------------------------------------------
   INDICATOR REGISTRY
   Add an entry and it appears in the dialog, computes, draws, saves and
   restores with no other change. `pane:'main'` overlays price; `pane:'sub'`
   gets its own stacked panel. All maths lives in Core and is unit-tested.
   --------------------------------------------------------------- */
const IND_DEFS = {
  sma:  {label:'SMA', pane:'main', params:{period:20},
         calc:(B,a,p)=>({line: Core.sma(a.c, p.period)}),
         title:p=>'SMA '+p.period},
  ema:  {label:'EMA', pane:'main', params:{period:50},
         calc:(B,a,p)=>({line: Core.ema(a.c, p.period)}),
         title:p=>'EMA '+p.period},
  vwap: {label:'VWAP (session anchored)', pane:'main', params:{},
         calc:(B,a)=>{const l=Core.vwapSession(a); return {line:l, _w:l.weighted};},
         title:function(p, out){ return out && out._w === false
           ? 'VWAP (no volume: typical price)' : 'VWAP'; }},
  volume:{label:'Volume', pane:'sub', params:{avg:20},
         calc:(B,a,p)=>{ if (!a.v) return {}; 
                         const r={volume:a.v}; const m=Core.volumeAvg(a,p.avg);
                         if (m) r.average=m; return r; },
         hist:'volume', histDir:true, title:p=>'Volume \u00b7 avg ' + p.avg},
  bb:   {label:'Bollinger Bands', pane:'main', params:{period:20, sd:2},
         calc:(B,a,p)=>{const r=Core.bollinger(a.c,p.period,p.sd);
                        return {upper:r.up, mid:r.mid, lower:r.dn};},
         title:p=>'BB '+p.period+', '+p.sd},
  donchian:{label:'Donchian Channel', pane:'main', params:{period:20},
         calc:(B,a,p)=>{const r=Core.donchian(a,p.period);
                        return {upper:r.up, mid:r.mid, lower:r.dn};},
         title:p=>'Donchian '+p.period},
  keltner:{label:'Keltner Channel', pane:'main', params:{period:20, mult:2},
         calc:(B,a,p)=>{const r=Core.keltner(a,p.period,p.mult);
                        return {upper:r.up, mid:r.mid, lower:r.dn};},
         title:p=>'Keltner '+p.period+', '+p.mult},
  rsi:  {label:'RSI', pane:'sub', params:{period:14}, range:[0,100], guides:[30,70],
         calc:(B,a,p)=>({line: Core.rsi(a.c, p.period)}),
         title:p=>'RSI '+p.period},
  stoch:{label:'Stochastic', pane:'sub', params:{k:14, d:3, smooth:1},
         range:[0,100], guides:[20,80],
         calc:(B,a,p)=>{const r=Core.stochastic(a,p.k,p.d,p.smooth);
                        return {'%K':r.k, '%D':r.d};},
         title:p=>'Stoch '+p.k+','+p.d},
  macd: {label:'MACD', pane:'sub', params:{fast:12, slow:26, signal:9}, zero:true,
         calc:(B,a,p)=>{const r=Core.macd(a.c,p.fast,p.slow,p.signal);
                        return {hist:r.hist, macd:r.macd, signal:r.signal};},
         hist:'hist', title:p=>'MACD '+p.fast+','+p.slow+','+p.signal},
  atr:  {label:'ATR', pane:'sub', params:{period:14},
         calc:(B,a,p)=>({line: Core.atr(a, p.period)}),
         title:p=>'ATR '+p.period},
  roc:  {label:'Rate of Change', pane:'sub', params:{period:12}, zero:true,
         calc:(B,a,p)=>({line: Core.roc(a.c, p.period)}),
         title:p=>'ROC '+p.period}
};
const IND_COLS = ['#6ea8dc','#c98ad4','#7fc9a8','#d4a95e','#e0797f','#8fd0e0','#b8b06a','#9d8ff0'];

/* ---------------- state ---------------- */
const THEMES = {
  midnight: {ground:'#0f1115',panel:'#161a21',panel2:'#1b2029',rule:'#252b36',ruleSoft:'#1e232c',
             ink:'#dae0ea',inkDim:'#8e99ac',inkFaint:'#5d6779'},
  graphite: {ground:'#141414',panel:'#1c1c1c',panel2:'#232323',rule:'#2e2e2e',ruleSoft:'#252525',
             ink:'#e2e2e2',inkDim:'#999',inkFaint:'#666'},
  ocean:    {ground:'#0b1622',panel:'#122031',panel2:'#17293d',rule:'#20374f',ruleSoft:'#1a2c41',
             ink:'#d5e3f0',inkDim:'#89a3bd',inkFaint:'#5b7590'},
  paper:    {ground:'#f6f4ee',panel:'#ffffff',panel2:'#f0ede4',rule:'#d8d3c6',ruleSoft:'#e6e2d8',
             ink:'#1e2118',inkDim:'#5f6455',inkFaint:'#8d9182'},
  terminal: {ground:'#05080a',panel:'#0a1013',panel2:'#0f171b',rule:'#18262c',ruleSoft:'#111c21',
             ink:'#c9e6d8',inkDim:'#6f9486',inkFaint:'#456055'}
};
const PALETTES = {
  classic:  {up:'#4bb073',down:'#d1565a',long:'#5b9bd5',short:'#d98a55',accent:'#d8a24a'},
  vivid:    {up:'#26a69a',down:'#ef5350',long:'#42a5f5',short:'#ffa726',accent:'#ffca28'},
  mono:     {up:'#cfd6e0',down:'#6b7482',long:'#9fb4cc',short:'#8a8f99',accent:'#d8a24a'},
  colorblind:{up:'#3d8fd1',down:'#e08a1e',long:'#7b68c4',short:'#c25b9e',accent:'#d8c04a'}
};
const S = {
  tf: 1, ct: 'candle', log: false, magnet: false, measure: false,
  showTrades: true, showEq: false, indicators: [],
  view: {a: 0, b: 390}, sel: -1, pmode: 'auto', PR: null,
  replay: false, rBase: 0, playing: false, speed: 4,
  /* appearance */
  theme: 'midnight', palette: 'classic',
  col: Object.assign({}, PALETTES.classic),
  bodyW: 0.7, wickW: 1, wicks: true,
  grid: true, gridOp: 1, sessLines: true, decimals: 2, fontSize: 10.5,
  /* trades */
  tBoxes: true, tMarkers: true, tLabels: true, tOpacity: 0.10,
  /* layout */
  showNav: true, showRail: true,
  eqH: 190, subH: 92, eqMode: 'both',
  /* a loaded bar file is cut to the New York day session, as the shipped
     tape was; off keeps every hour the file has */
  rthOnly: true,
  /* time-of-day rules drawn on every session, and an optional filter that
     removes bars outside a window entirely */
  marks: [{m: 570, label: 'RTH', col: '#d8a24a', on: true},
          {m: 600, label: '10:00', col: '#6ea8dc', on: false},
          {m: 960, label: 'Close', col: '#8e99ac', on: false}],
  shade: {on: false, from: 570, to: 960},
  filter: {on: false, from: 570, to: 960},
  /* account simulator: replays the loaded trades against a real balance and
     liquidates on unrealised equity, not just on the recorded exit */
  acct: {on: false, balance: 10000, floor: 0, sizeMode: 'fixed', contracts: 1,
         riskPct: 1, pointValue: 2, commission: 0.75, slippage: 0.25,
         evaluation: {on: false, repeat: false, target: 1250, dailyCap: 625,
                      dailyLoss: 0, trailDD: 1000, freezeOffset: 100,
                      cost: 65, payoutAt: 2100, payoutDraw: 1000,
                      payoutSplit: 0.9, maxDraws: 0,
                      fundedCapOn: true}}
};
/* A shallow Object.assign replaced whole sub-objects, so a state written by
   an older build -- one whose acct had no evaluation -- wiped the defaults and
   left S.acct.evaluation undefined, which threw at startup for anyone who had
   used the page before. Merge against the defaults instead: a stored value can
   only fill a key the defaults already define, and only if it is the same
   shape, so an old or corrupt state degrades to the default rather than
   deleting it. */
function mergeState(dst, src){
  if (!src || typeof src !== 'object') return dst;
  Object.keys(dst).forEach(k => {
    if (!Object.prototype.hasOwnProperty.call(src, k)) return;
    const d = dst[k], v = src[k];
    if (Array.isArray(d)){ if (Array.isArray(v)) dst[k] = v; }
    else if (d && typeof d === 'object'){ mergeState(d, v); }
    else if (v !== null && v !== undefined && typeof v === typeof d) dst[k] = v;
  });
  return dst;
}
try { mergeState(S, JSON.parse(localStorage.getItem('tape.v3') || '{}')); } catch(e){}
S.view = {a: 0, b: 390}; S.replay = false; S.playing = false; S.rBase = 0;   /* never restore transient state */
function save(){
  try { localStorage.setItem('tape.v3', JSON.stringify({
    tf: S.tf, ct: S.ct, log: S.log, magnet: S.magnet,
    showTrades: S.showTrades, showEq: S.showEq, indicators: S.indicators,
    theme: S.theme, palette: S.palette, col: S.col,
    bodyW: S.bodyW, wickW: S.wickW, wicks: S.wicks,
    grid: S.grid, gridOp: S.gridOp, sessLines: S.sessLines,
    decimals: S.decimals, fontSize: S.fontSize,
    tBoxes: S.tBoxes, tMarkers: S.tMarkers, tLabels: S.tLabels, tOpacity: S.tOpacity,
    showNav: S.showNav, showRail: S.showRail, rthOnly: S.rthOnly,
    eqH: S.eqH, subH: S.subH, eqMode: S.eqMode,
    marks: S.marks, shade: S.shade, filter: S.filter,
    acct: S.acct })); } catch(e){}
}

function applyTheme(){
  const t = THEMES[S.theme] || THEMES.midnight, r = document.documentElement.style;
  r.setProperty('--ground', t.ground); r.setProperty('--panel', t.panel);
  r.setProperty('--panel-2', t.panel2); r.setProperty('--rule', t.rule);
  r.setProperty('--rule-soft', t.ruleSoft); r.setProperty('--ink', t.ink);
  r.setProperty('--ink-dim', t.inkDim); r.setProperty('--ink-faint', t.inkFaint);
  r.setProperty('--up', S.col.up); r.setProperty('--down', S.col.down);
  r.setProperty('--long', S.col.long); r.setProperty('--short', S.col.short);
  r.setProperty('--accent', S.col.accent);
  document.documentElement.setAttribute('data-theme', S.theme === 'paper' ? 'light' : 'dark');
}
let BASE = buildBars(RAW), TRADES = buildTrades(RAW), cfg = RAW.cfg;
/* the market the loaded bars actually are, guessed from the file name when a
   new one is loaded (detectSymbol, defined with the loader); the shipped
   tape is NQ. null once a load's file name matches nothing in INSTRUMENTS,
   so the Strategy panel can say so instead of assuming the last guess */
let LOADED_SYM = 'NQ';
/* The encoded blob is ~3.3 MB of base64 that is never read again once the
   typed arrays exist. Hold the decoded originals for the Demo button and let
   the strings go, rather than keeping both alive for the life of the page. */
const BASE0 = BASE, TRADES0 = TRADES;
RAW.bars = null; RAW.trades = null; RAW.mins = null;
let BUCKETS = null;
const PR_CACHE = {sig: null, val: null};
const MK_CACHE = {};
let V = null, IND = null, ENT = null, EXT = null, MAXSPAN = 1,
    STATS = null, EQ = null, EQPEAK = null, SIM = null, SERIES = null;
/* the Strategy panel run whose trades are on the chart, if any: runAccount
   reads its books instead of re-pricing them */
let STLOADED = null;

let SRC = null, FWD = null;
/* Bumped whenever the bars themselves are replaced, which is the only thing
   that invalidates every cache below. */
let DATA_GEN = 0;
let AGG_C = {key: null}, VIEW_C = {key: null}, IND_C = {key: null};

function rebuild(){
  const fkey = DATA_GEN + '|' + (S.filter.on ? S.filter.from + '-' + S.filter.to : 'off');
  const akey = fkey + '|' + S.tf;
  const vkey = akey + '|' + S.ct;

  if (AGG_C.key !== akey){
    /* the time filter runs BEFORE aggregation, so a 5-minute candle built from
       a filtered series never spans the gap the filter removed */
    const src = S.filter.on ? Core.timeFilter(BASE, S.filter.from, S.filter.to) : BASE;
    AGG_C = {key: akey, src, agg: Core.aggregate(src, S.tf)};
  }
  SRC = AGG_C.src;
  FWD = SRC.fwd || null;
  const agg = AGG_C.agg;

  if (VIEW_C.key !== vkey){
    const view = S.ct === 'ha' ? Core.heikinAshi(agg) : agg;
    view.aggClose = agg.c;
    if (agg.v && !view.v) view.v = agg.v;
    /* block min/max for the price axis. Built with the view, not per frame. */
    VIEW_C = {key: vkey, view, buckets: Core.buildBuckets(view, 512)};
  }
  V = VIEW_C.view;
  BUCKETS = VIEW_C.buckets;
  PR_CACHE.sig = null;

  /* Every indicator is computed on the AGGREGATED REAL bars, never on
     Heikin-Ashi values, which are a display transform and not a price series.
     That is also why the candle type is absent from this key: switching to
     Heikin-Ashi must not recompute them. */
  const ikey = akey + '|' + JSON.stringify(S.indicators);
  if (IND_C.key !== ikey){
    IND_C = {key: ikey, ind: S.indicators.map((cfg, i) => {
      const def = IND_DEFS[cfg.key];
      if (!def) return null;
      try {
        return {cfg, def, out: def.calc(BASE, agg, cfg.p),
                col: cfg.col || IND_COLS[i % IND_COLS.length]};
      } catch (err){ return {cfg, def, out: {}, err: err.message,
                             col: cfg.col || IND_COLS[i % IND_COLS.length]}; }
    }).filter(Boolean)};
  }
  IND = IND_C.ind;
  reindex();
}
/* BASE bar -> filtered bar -> aggregated candle. A trade whose bar was removed
   by the filter maps to -1 and is skipped rather than sliding onto a
   neighbouring candle. */
function toView(baseIdx){
  const i = Math.min(BASE.n - 1, Math.max(0, baseIdx));
  if (!FWD) return V.map[i];
  const f = FWD[i];
  return f < 0 ? -1 : V.map[f];
}
function reindex(){
  ENT = TRADES.map(t => toView(t.entry_bar));
  EXT = TRADES.map(t => toView(t.exit_bar));
  MAXSPAN = 1;
  for (let i = 0; i < ENT.length; i++){
    if (ENT[i] < 0 || EXT[i] < 0) continue;
    const sp = EXT[i] - ENT[i];
    if (sp > MAXSPAN) MAXSPAN = sp;
  }
  STATS = Core.tradeStats(TRADES);
  EQ = STATS.equity || [];
  runAccount();
  buildPeaks();
}
/* running high-water mark of the equity series, so the tooltip can report how
   far below the peak a trade left you without rescanning on every frame */
function buildPeaks(){
  EQPEAK = new Array(EQ.length);
  let pk = -Infinity;
  for (let i = 0; i < EQ.length; i++){
    if (EQ[i] > pk) pk = EQ[i];
    EQPEAK[i] = pk;
  }
}
/* SIM is null unless the simulator is on; everything downstream checks it and
   falls back to the trades' own recorded P&L. */
/* A run from the Strategy panel arrives with its own books: every exit was
   placed by the size and rules it was generated under, and each row carries
   the balance, floor, stage and P&L that resulted. Re-pricing those rows with
   simulateSeries is a second model with its own conventions -- it charges
   slippage on both sides where runStrategy charges the exit only, it
   liquidates at the daily-loss line where runStrategy ends the day, and it
   has no notion of a skipped row -- and with the settings matched by hand the
   two still disagreed on every trade. One list, one accounting: the ledger
   reads the run's rows, reshaped to what the panels expect from a series. */
function stratSeries(r){
  const B = BASE, q = r.summary, wins = {};
  const rows = r.trades.map((t, i) => {
    if (t.skipped) return {i, skipped: true, reason: t.reason, acct: t.acct, bal: t.bal, floor: t.floor};
    /* excursions as simulateSeries reports them: the worst and best the bars
       reached between entry and exit, the adverse one pinned at the barrier
       that closed the trade */
    let mae = 0, mfe = 0;
    for (let k = t.entry_bar; k <= t.exit_bar; k++){
      const adv = t.side > 0 ? t.entry - B.l[k] : B.h[k] - t.entry;
      const fav = t.side > 0 ? B.h[k] - t.entry : t.entry - B.l[k];
      if (adv > mae) mae = adv;
      if (fav > mfe) mfe = fav;
    }
    if (t.why === 'adverse') mae = t.A;
    if (t.pnl > 0) wins[t.acct] = (wins[t.acct] || 0) + 1;
    return {i, acct: t.acct, stage: t.stage, size: t.size, side: t.side, entry: t.entry, exit: t.exit,
            exitBar: t.exit_bar, forced: t.forced, capped: t.capped, bind: t.bind, mae, mfe,
            pts: t.pts, pnl: t.pnl, bal: t.bal, dayPnL: t.realized, floor: t.floor,
            liqPrice: t.liq_px, liqDist: t.liqDist, stopDist: t.stopDist,
            stopReachable: t.stopReachable};
  });
  const accounts = r.accounts.map(a => Object.assign({}, a, {wins: wins[a.n] || 0, pnl: a.bal - q.start}));
  let fails = 0, incomplete = 0, days = 0, trades = 0, forced = 0;
  accounts.forEach(a => {
    if (a.verdict === 'FAIL') fails++; else if (a.verdict !== 'LIVE') incomplete++;
    days += a.days; trades += a.trades;
  });
  rows.forEach(x => { if (x.forced) forced++; });
  const n = accounts.length, ticket = q.tickets ? q.spent / q.tickets : 0;
  return {rows, accounts, summary: {
    start: q.start, pointValue: r.pointValue, ticket, accounts: n, passes: q.passes, fails, incomplete,
    payouts: q.draws, graduated: q.graduated, maxDraws: q.maxDraws,
    payoutValue: q.payoutValue, payoutDraw: q.payoutDraw, payoutSplit: q.payoutSplit,
    passRate: q.passRate, fundedRate: q.passRate, drawsPerFunded: q.drawsPerFunded,
    roi: q.roi, perTicket: q.perTicket,
    pnl: accounts.reduce((s, a) => s + a.pnl, 0), tradingPnl: accounts.reduce((s, a) => s + a.pnl, 0),
    ticketCost: q.spent, spent: q.spent, won: q.won, net: q.net,
    trades, forced,
    avgTradesPerAccount: n ? trades / n : 0, avgDaysPerAccount: n ? days / n : 0
  }};
}
function runAccount(){
  SIM = null; SERIES = null;
  if (!TRADES.length || !V) return;
  if (STLOADED && TRADES === STLOADED.trades){
    SERIES = stratSeries(STLOADED);
  } else if (!S.acct.on){
    return;
  } else {
    const src = SRC || BASE;
    const eIdx = TRADES.map(t => (FWD ? FWD[Math.min(src.n - 1, t.entry_bar)] : t.entry_bar));
    const xIdx = TRADES.map(t => (FWD ? FWD[Math.min(src.n - 1, t.exit_bar)] : t.exit_bar));
    if (S.acct.evaluation.on && S.acct.evaluation.repeat){
      /* buy a fresh account after every pass or bust, and count the outcomes */
      SERIES = Core.simulateSeries(src, TRADES, eIdx, xIdx, S.acct);
    } else {
      SIM = Core.simulateAccount(src, TRADES, eIdx, xIdx, S.acct);
      EQ = SIM.rows.map(r => r.bal);
      buildPeaks();
      return;
    }
  }
  SIM = {rows: SERIES.rows, summary: SERIES.summary, series: true};
  /* the equity pane plots each account's own balance, so a reset reads as a
     vertical step rather than a fake loss */
  let last = SERIES.summary.start;
  EQ = SERIES.rows.map(r => {
    if (r && !r.skipped && r.bal !== undefined){ last = r.bal; }
    return last;
  });
  buildPeaks();
}
const aggEntry = i => ENT[i];
const aggExit = i => (EXT[i] < 0 ? ENT[i] : EXT[i]);

/* ---------------- canvas ---------------- */
const cvEl = document.getElementById('cv'), wrap = document.getElementById('wrap');
const ctx = cvEl.getContext('2d'), tip = document.getElementById('tip');
let W = 0, H = 0, mouse = null, drag = null, meas = null;
const PAD = {l: 8, r: 74, t: 12, b: 30};

function subPanes(){ return IND.filter(x => x.def.pane === 'sub'); }
function plot(){
  const eq = S.showEq ? S.eqH : 0;
  const subs = subPanes().length * S.subH;
  const avail = H - PAD.t - PAD.b - eq - subs;
  /* never let the panes squeeze price out of existence */
  const h = Math.max(90, avail);
  return {x: PAD.l, y: PAD.t, w: W - PAD.l - PAD.r, h, eq, subs, subH: S.subH};
}
/* the replay cursor is stored in BASE-bar space and converted on demand, so
   a timeframe change keeps it pointing at the same moment in time */
function lastBar(){
  return S.replay ? Core.replayToView(S.rBase, V, BASE.n) : V.n - 1;
}
function priceRange(){
  if (S.pmode === 'manual' && S.PR) return S.PR;
  const b = Math.min(lastBar(), Math.ceil(S.view.b));
  /* Two costs used to land on every mouse move. First, this scanned every
     visible bar -- 47 ms across the whole series, measured. Second, scales()
     is called four or more times per frame and each one recomputed it, so a
     single mouse move cost roughly 190 ms of pure scanning.

     Buckets fix the first (71x faster at full zoom, verified identical), and
     the signature cache fixes the second: within one frame nothing that feeds
     the range has changed, so the answer is reused. */
  const sig = S.view.a + '|' + b + '|' + S.showTrades + '|' + TRADES.length + '|' + S.tf + '|' + S.ct;
  if (PR_CACHE.sig === sig) return PR_CACHE.val;
  const R = Core.priceRangeFast(V, BUCKETS, S.view.a, b, 0.06);
  if (S.showTrades) {
    Core.visibleTrades(ENT, EXT, S.view.a, b, MAXSPAN).forEach(i => {
      const t = TRADES[i];
      if (t.stop_px < R.lo) R.lo = t.stop_px;
      if (t.tgt_px  < R.lo) R.lo = t.tgt_px;
      if (t.stop_px > R.hi) R.hi = t.stop_px;
      if (t.tgt_px  > R.hi) R.hi = t.tgt_px;
    });
  }
  PR_CACHE.sig = sig; PR_CACHE.val = R;
  return R;
}
function scales(){
  const P = plot(), R = priceRange(), span = Math.max(2, S.view.b - S.view.a);
  /* Y and vAt come from Core.makeScale, which is tested to invert exactly in
     both linear and log mode -- otherwise the crosshair reads one price and
     draws at another, and the measure tool reports a percentage that is wrong. */
  const sc = Core.makeScale(R.lo, R.hi, P.y, P.h, S.log);
  return {P, R, span, Y: sc.Y, vAt: sc.vAt,
    X: i => P.x + P.w * (i - S.view.a) / span,
    iAt: px => S.view.a + (px - P.x) / P.w * span};
}
function clampView(){
  const min = 8, max = V.n - 1;
  if (S.view.b - S.view.a < min) S.view.b = S.view.a + min;
  if (S.view.a < 0){ S.view.b -= S.view.a; S.view.a = 0; }
  if (S.view.b > max){ S.view.a -= (S.view.b - max); S.view.b = max; }
  if (S.view.a < 0) S.view.a = 0;
}
function setView(a, b){ S.view = {a, b}; clampView(); render(); }
function dayAt(i){
  /* imported non-intraday files carry a date per bar; packed data derives it
     from the session that owns the bar */
  if (SRC && SRC.days && V.src) { const d = SRC.days[V.src[i]]; if (d) return d; }
  const s = V.sessions[Core.sessionOf(V.sessions, i)];
  return s ? s.day : '';
}
function stamp(i){
  if (i < 0 || i >= V.n) return '';
  const d = dayAt(i);
  return V.mins[i] ? d + ' ' + hhmm(V.mins[i]) : d;
}

function render(){
  if (!V) return;
  const sc = scales(), P = sc.P;
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = cv_('--panel');
  ctx.fillRect(P.x + P.w, 0, W - (P.x + P.w), H);
  ctx.fillRect(0, P.y + P.h + P.subs + P.eq, W, H - (P.y + P.h + P.subs + P.eq));
  ctx.strokeStyle = cv_('--rule'); ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(P.x + P.w + .5, 0);
  ctx.lineTo(P.x + P.w + .5, H); ctx.stroke();
  if (S.pmode === 'manual'){ ctx.fillStyle = cv_('--accent'); ctx.fillRect(P.x + P.w + 1, 0, 2, P.h + P.t); }
  ctx.font = S.fontSize + 'px ' + cv_('--mono'); ctx.textBaseline = 'middle';

  for (let k = 0; k <= 6; k++){
    const t = k / 6;
    const v = S.log ? Math.exp(Math.log(sc.R.lo) + (Math.log(sc.R.hi) - Math.log(sc.R.lo)) * t)
                    : sc.R.lo + (sc.R.hi - sc.R.lo) * t;
    const y = sc.Y(v);
    if (S.grid){
      ctx.globalAlpha = S.gridOp; ctx.strokeStyle = cv_('--rule-soft');
      ctx.beginPath(); ctx.moveTo(P.x, y + .5); ctx.lineTo(P.x + P.w, y + .5); ctx.stroke();
      ctx.globalAlpha = 1;
    }
    ctx.fillStyle = cv_('--ink-faint'); ctx.textAlign = 'left';
    ctx.fillText(v.toFixed(S.decimals), P.x + P.w + 7, y);
  }

  const a = Math.max(0, Math.floor(S.view.a)), b = Math.min(lastBar(), Math.ceil(S.view.b));
  const intraday = V.sessions.length > 1 || !V.sessions[0] || !V.sessions[0].spanning;
  const barsPerDay = intraday ? 390 / S.tf : 1;
  const perDay = sc.span / barsPerDay;
  ctx.textAlign = 'center';
  if (perDay >= 10){
    const step = Math.max(1, Math.round(sc.span / 10));
    for (let i = a; i <= b; i += step){
      const x = sc.X(i);
      if (S.grid){
        ctx.globalAlpha = S.gridOp; ctx.strokeStyle = cv_('--rule-soft');
        ctx.beginPath(); ctx.moveTo(x + .5, P.y); ctx.lineTo(x + .5, P.y + P.h); ctx.stroke();
        ctx.globalAlpha = 1;
      }
      ctx.fillStyle = cv_('--ink-faint');
      ctx.fillText(intraday && V.mins[i] ? hhmm(V.mins[i]) : dayAt(i),
                   x, P.y + P.h + P.subs + P.eq + 14);
    }
  } else {
    let last = '';
    V.sessions.forEach(s => {
      if (s.a < a || s.a > b) return;
      const key = perDay > 45 ? s.day.slice(0, 7) : s.day;
      if (key === last) return; last = key;
      const x = sc.X(s.a);
      if (S.sessLines){
        ctx.strokeStyle = cv_('--rule');
        ctx.beginPath(); ctx.moveTo(x + .5, P.y); ctx.lineTo(x + .5, P.y + P.h); ctx.stroke();
      }
      ctx.fillStyle = cv_('--ink-faint');
      ctx.fillText(perDay > 45 ? key : key.slice(5), x, P.y + P.h + P.subs + P.eq + 14);
    });
  }

  drawTimeMarks(sc, a, b);
  drawNewsMarks(sc, a, b);
  if (S.showTrades) drawTrades(sc, a, b);
  drawSeries(sc, a, b);
  drawIndicators(sc, a, b);
  if (S.showTrades) drawTrades(sc, a, b, true);
  if (S.showEq) drawEquity(sc, a, b);
  drawCrosshair(sc);
  onChange();
}

function drawSeries(sc, a, b){
  const P = sc.P, pxPer = P.w / sc.span;
  if (S.ct === 'line' || S.ct === 'area'){
    ctx.beginPath();
    for (let i = a; i <= b; i++){ const x = sc.X(i), y = sc.Y(V.c[i]); i === a ? ctx.moveTo(x, y) : ctx.lineTo(x, y); }
    if (S.ct === 'area'){
      ctx.lineTo(sc.X(b), P.y + P.h); ctx.lineTo(sc.X(a), P.y + P.h); ctx.closePath();
      ctx.fillStyle = 'rgba(110,168,220,.16)'; ctx.fill();
      ctx.beginPath();
      for (let i = a; i <= b; i++){ const x = sc.X(i), y = sc.Y(V.c[i]); i === a ? ctx.moveTo(x, y) : ctx.lineTo(x, y); }
    }
    ctx.strokeStyle = cv_('--i1'); ctx.lineWidth = 1.6; ctx.stroke();
    return;
  }
  if (pxPer < 1.1){
    for (let px = 0; px < Math.ceil(P.w); px++){
      const i0 = Math.max(a, Math.floor(S.view.a + px / P.w * sc.span));
      const i1 = Math.min(b, Math.floor(S.view.a + (px + 1) / P.w * sc.span));
      if (i1 < i0) continue;
      let lo = Infinity, hi = -Infinity;
      for (let i = i0; i <= i1; i++){ if (V.l[i] < lo) lo = V.l[i]; if (V.h[i] > hi) hi = V.h[i]; }
      ctx.strokeStyle = V.c[i1] >= V.o[i0] ? S.col.up : S.col.down;
      ctx.lineWidth = 1;
      const x = P.x + px + .5;
      ctx.beginPath(); ctx.moveTo(x, sc.Y(hi)); ctx.lineTo(x, sc.Y(lo)); ctx.stroke();
    }
    return;
  }
  const bw = Math.min(40, Math.max(1.2, pxPer * S.bodyW));
  for (let i = a; i <= b; i++){
    /* the fill/colour decision lives in Core so it can be unit-tested --
       an earlier build drew 'candle' and 'hollow' identically */
    const st = Core.candleStyle(V, i, S.ct);
    const x = sc.X(i), col = st.up ? S.col.up : S.col.down;
    ctx.strokeStyle = col; ctx.fillStyle = col;
    if (S.wicks){
      ctx.lineWidth = S.wickW;
      ctx.beginPath(); ctx.moveTo(x, sc.Y(V.h[i])); ctx.lineTo(x, sc.Y(V.l[i])); ctx.stroke();
    }
    if (S.ct === 'bar'){
      ctx.lineWidth = Math.max(1, S.wickW);
      ctx.beginPath();
      ctx.moveTo(x - bw / 2, sc.Y(V.o[i])); ctx.lineTo(x, sc.Y(V.o[i]));
      ctx.moveTo(x, sc.Y(V.c[i])); ctx.lineTo(x + bw / 2, sc.Y(V.c[i]));
      ctx.stroke();
      continue;
    }
    const y1 = sc.Y(Math.max(V.o[i], V.c[i])), y2 = sc.Y(Math.min(V.o[i], V.c[i]));
    const bh = Math.max(1, y2 - y1);
    if (bw < 3) ctx.fillRect(x - bw / 2, y1, bw, bh);
    else if (st.hollow){ ctx.lineWidth = 1.3; ctx.strokeRect(x - bw / 2, y1 + .5, bw, bh); }
    else ctx.fillRect(x - bw / 2, y1, bw, bh);
  }
}

function drawIndicators(sc, a, b){
  const P = sc.P;
  const line = (arr, col, w, Y) => {
    ctx.beginPath(); let started = false;
    for (let i = a; i <= b; i++){
      const v = arr[i];
      if (v === null || v === undefined || !isFinite(v)){ started = false; continue; }
      const x = sc.X(i), y = Y(v);
      started ? ctx.lineTo(x, y) : (ctx.moveTo(x, y), started = true);
    }
    ctx.strokeStyle = col; ctx.lineWidth = w || 1.4; ctx.stroke();
  };
  /* main-pane overlays */
  let row = 0;
  IND.forEach(ix => {
    if (ix.def.pane !== 'main') return;
    Object.keys(ix.out).filter(k => k.charAt(0) !== '_')
      .forEach(k => line(ix.out[k], ix.col,
      k === 'mid' ? 1 : 1.4, sc.Y));
    ctx.font = S.fontSize + 'px ' + cv_('--mono'); ctx.textAlign = 'left';
    ctx.fillStyle = ix.col;
    ctx.fillText(ix.def.title(ix.cfg.p, ix.out) + (ix.err ? '  !' : ''),
                 P.x + 8, P.y + 12 + row * 13);
    row++;
  });
  /* stacked sub-panes */
  subPanes().forEach((ix, si) => {
    const y0 = P.y + P.h + si * P.subH + 3, h = P.subH - 6;
    ctx.fillStyle = cv_('--panel-2'); ctx.fillRect(P.x, y0, P.w, h);
    ctx.strokeStyle = cv_('--rule-soft'); ctx.lineWidth = 1;
    ctx.strokeRect(P.x + .5, y0 + .5, P.w, h);
    let lo, hi;
    if (ix.def.range){ lo = ix.def.range[0]; hi = ix.def.range[1]; }
    else {
      lo = Infinity; hi = -Infinity;
      Object.keys(ix.out).forEach(k => {
        for (let i = a; i <= b; i++){
          const v = ix.out[k][i];
          if (v === null || v === undefined || !isFinite(v)) continue;
          if (v < lo) lo = v; if (v > hi) hi = v;
        }
      });
      if (!isFinite(lo)){ lo = 0; hi = 1; }
      if (ix.def.zero){ lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
      const pd = (hi - lo) * 0.12 || 1; lo -= pd; hi += pd;
    }
    const Y = v => y0 + h * (1 - (v - lo) / (hi - lo));
    (ix.def.guides || []).forEach(g => {
      if (g < lo || g > hi) return;
      ctx.setLineDash([3, 3]); ctx.strokeStyle = cv_('--rule');
      ctx.beginPath(); ctx.moveTo(P.x, Y(g) + .5); ctx.lineTo(P.x + P.w, Y(g) + .5); ctx.stroke();
      ctx.setLineDash([]);
    });
    if (ix.def.zero && lo < 0 && hi > 0){
      ctx.strokeStyle = cv_('--rule');
      ctx.beginPath(); ctx.moveTo(P.x, Y(0) + .5); ctx.lineTo(P.x + P.w, Y(0) + .5); ctx.stroke();
    }
    /* histogram series render as bars, everything else as lines */
    const bw = Math.max(1, (P.w / Math.max(2, sc.span)) * 0.6);
    Object.keys(ix.out).forEach((k, ki) => {
      if (ix.def.hist === k){
        for (let i = a; i <= b; i++){
          const v = ix.out[k][i];
          if (v === null || v === undefined || !isFinite(v)) continue;
          /* volume bars take the candle's direction; a MACD histogram takes
             its own sign */
          ctx.fillStyle = ix.def.histDir
            ? (Core.candleStyle(V, i, 'candle').up ? S.col.up : S.col.down)
            : (v >= 0 ? S.col.up : S.col.down);
          const yv = Y(v), yz = Y(Math.max(lo, Math.min(hi, 0)));
          ctx.fillRect(sc.X(i) - bw / 2, Math.min(yv, yz), bw, Math.max(1, Math.abs(yz - yv)));
        }
        return;
      }
      const shade = ki === 0 ? ix.col : (ki === 1 ? S.col.accent : cv_('--ink-dim'));
      line(ix.out[k], shade, 1.3, Y);
    });
    ctx.font = '9.5px ' + cv_('--mono'); ctx.textAlign = 'left';
    ctx.fillStyle = ix.col;
    const empty = !Object.keys(ix.out).length;
    ctx.fillText(ix.def.title(ix.cfg.p, ix.out) +
      (ix.err ? '  error: ' + ix.err : empty ? '  \u2014 no volume in this data' : ''),
      P.x + 7, y0 + 10);
    ctx.fillStyle = cv_('--ink-faint'); ctx.textAlign = 'right';
    const at = Math.min(b, Math.max(a, Math.round(mouse ? sc.iAt(mouse.x) : b)));
    const first = ix.out[Object.keys(ix.out)[0]];
    const cur = first ? first[at] : null;
    ctx.fillText(cur === null || cur === undefined || !isFinite(cur)
      ? '\u2014' : cur.toFixed(2), P.x + P.w - 8, y0 + 10);
    ctx.fillStyle = cv_('--ink-faint'); ctx.textAlign = 'left';
    ctx.fillText(lo.toFixed(1) + ' .. ' + hi.toFixed(1), P.x + 7, y0 + h - 8);
  });
}

function drawTimeMarks(sc, a, b){
  const P = sc.P;
  if (!V.mins || !V.sessions.length) return;
  /* shaded band between two times of day, per session */
  if (S.shade.on){
    ctx.globalAlpha = 0.05; ctx.fillStyle = S.col.accent;
    V.sessions.forEach(sn => {
      if (sn.b < a || sn.a > b) return;
      let x0 = -1, x1 = -1;
      for (let i = sn.a; i <= sn.b; i++){
        if (V.mins[i] >= S.shade.from && x0 < 0) x0 = i;
        if (V.mins[i] <= S.shade.to) x1 = i;
      }
      if (x0 < 0 || x1 < x0) return;
      const xa = sc.X(Math.max(a, x0)), xb = sc.X(Math.min(b, x1));
      ctx.fillRect(xa, P.y, Math.max(1, xb - xa), P.h);
    });
    ctx.globalAlpha = 1;
  }
  /* vertical rule wherever a session first reaches the marked minute */
  /* Core.timeMarks walks every visible session and scans its bars. At full
     zoom that is the whole series, once per enabled mark, per frame. The
     result only depends on the view and the timeframe, so cache it. */
  S.marks.forEach((mk, mi) => {
    if (!mk.on) return;
    const key = mi + '|' + mk.m + '|' + a + '|' + b + '|' + S.tf;
    let at;
    if (MK_CACHE[mi] && MK_CACHE[mi].key === key) at = MK_CACHE[mi].at;
    else { at = Core.timeMarks(V, mk.m, a, b); MK_CACHE[mi] = {key: key, at: at}; }
    if (!at.length) return;
    ctx.strokeStyle = mk.col; ctx.lineWidth = 1;
    ctx.setLineDash([5, 4]);
    at.forEach(i => {
      const x = sc.X(i);
      ctx.beginPath(); ctx.moveTo(x + .5, P.y); ctx.lineTo(x + .5, P.y + P.h); ctx.stroke();
    });
    ctx.setLineDash([]);
    /* label only when the marks are far enough apart to read */
    if (at.length <= 12){
      ctx.font = '9.5px ' + cv_('--mono'); ctx.fillStyle = mk.col; ctx.textAlign = 'left';
      at.forEach(i => ctx.fillText(mk.label, sc.X(i) + 3, P.y + 8));
    }
  });
}

/* The releases picked in Strategy -> Custom, as dotted lines on the bar each one
   landed in: only while that strategy is the one on the chart and 'Show on chart' is
   on. A release before the first loaded bar (08:30 data on the RTH tape) is drawn on
   that first bar and labelled "before open"; one after the last bar is not drawn.
   Cached like the time marks: it depends only on the view, the timeframe and the picks. */
let NM_CACHE = {key: null, at: []};
function newsMarks(a, b){
  const picked = ST.cuNews || {};
  if (ST.key !== 'custom' || !ST.cuShowMarks || !newsAny(ST) || !V.mins) return [];
  const key = a + '|' + b + '|' + S.tf + '|' + V.sessions.length + '|' + Object.keys(picked).join();
  if (NM_CACHE.key === key) return NM_CACHE.at;
  const at = [];
  V.sessions.forEach(sn => {
    if (sn.b < a || sn.a > b) return;
    (NEWSCAL_BY_DATE[sn.day] || []).forEach(e => {
      if (!picked[e.catId] || e.etMinute == null || e.scheduled) return;
      const label = e.eventName + ' ' + hhmm(e.etMinute);
      if (e.etMinute < V.mins[sn.a]){   /* released before the first loaded bar: mark the open */
        if (sn.a >= a && sn.a <= b) at.push([sn.a, label + ' (before open)']);
        return;
      }
      for (let i = sn.a; i <= sn.b; i++)
        if (V.mins[i] <= e.etMinute && e.etMinute < V.mins[i] + S.tf){
          if (i >= a && i <= b) at.push([i, label]);
          return;
        }
    });
  });
  NM_CACHE = {key: key, at: at};
  return at;
}
function drawNewsMarks(sc, a, b){
  const at = newsMarks(a, b), P = sc.P;
  if (!at.length) return;
  ctx.strokeStyle = cv_('--i2'); ctx.lineWidth = 1; ctx.globalAlpha = .75;
  ctx.setLineDash([2, 3]);
  at.forEach(([i]) => {
    const x = sc.X(i);
    ctx.beginPath(); ctx.moveTo(x + .5, P.y); ctx.lineTo(x + .5, P.y + P.h); ctx.stroke();
  });
  ctx.setLineDash([]); ctx.globalAlpha = 1;
  if (at.length <= 12){
    ctx.font = '9.5px ' + cv_('--mono'); ctx.fillStyle = cv_('--i2'); ctx.textAlign = 'left';
    at.forEach(([i, label], k) => ctx.fillText(label, sc.X(i) + 3, P.y + 20 + (k % 2) * 12));
  }
}

/* Two passes: the zones, lines and markers go UNDER the candles (pass 1); the
   stage badges and labels go OVER them (pass 2, `labels` true), or a wick
   runs through the text. */
function drawTrades(sc, a, b, labels){
  const vis = Core.visibleTrades(ENT, EXT, a, b, MAXSPAN);
  vis.forEach(ti => {
    /* a slot the account declined (cap reached, day over, no equity) stays
       in the rail with its reason, but draws nothing: a box on the chart
       says a position existed */
    if (!tradeTaken(ti)) return;
    const t = TRADES[ti], ea = aggEntry(ti), eb = aggExit(ti);
    const xa = sc.X(ea), xb = sc.X(eb), w = Math.max(1.5, xb - xa);
    const on = ti === S.sel;
    const ye = sc.Y(t.entry), yt = sc.Y(t.tgt_px), ys = sc.Y(t.stop_px);
    if (labels){ drawTradeLabel(sc, ti, t, xa, w, on, ye, yt, ys); return; }
    if (S.tBoxes && t.tgt_px !== t.entry){
      ctx.globalAlpha = on ? Math.min(1, S.tOpacity * 2.6) : S.tOpacity;
      ctx.fillStyle = S.col.up;
      ctx.fillRect(xa, Math.min(ye, yt), w, Math.abs(yt - ye));
      ctx.globalAlpha = 1;
    }
    if (S.tBoxes && t.stop_px !== t.entry){
      ctx.globalAlpha = on ? Math.min(1, S.tOpacity * 2.6) : S.tOpacity;
      ctx.fillStyle = S.col.down;
      ctx.fillRect(xa, Math.min(ye, ys), w, Math.abs(ys - ye));
      ctx.globalAlpha = 1;
    }
    if (S.tBoxes && (w > 3 || on)){
      ctx.setLineDash([4, 3]); ctx.lineWidth = on ? 1.6 : 1;
      ctx.strokeStyle = S.col.up;
      ctx.beginPath(); ctx.moveTo(xa, yt + .5); ctx.lineTo(xb, yt + .5); ctx.stroke();
      ctx.strokeStyle = S.col.down;
      ctx.beginPath(); ctx.moveTo(xa, ys + .5); ctx.lineTo(xb, ys + .5); ctx.stroke();
      ctx.setLineDash([]);
    }
    const tg = tagDef(tagOf(ti));
    const col = tg ? tg.col : (t.side > 0 ? S.col.long : S.col.short);
    if (w > 2){
      ctx.strokeStyle = col; ctx.lineWidth = on ? 1.6 : 1.1;
      ctx.beginPath(); ctx.moveTo(xa, ye + .5); ctx.lineTo(xb, ye + .5); ctx.stroke();
    }
    if (S.tMarkers && sc.span < 4000){
      ctx.fillStyle = col; ctx.beginPath();
      if (t.side > 0){ ctx.moveTo(xa, ye - 7); ctx.lineTo(xa - 5, ye + 2); ctx.lineTo(xa + 5, ye + 2); }
      else { ctx.moveTo(xa, ye + 7); ctx.lineTo(xa - 5, ye - 2); ctx.lineTo(xa + 5, ye - 2); }
      ctx.closePath(); ctx.fill();
      const yx = sc.Y(t.exit);
      ctx.fillStyle = t.pnl >= 0 ? S.col.up : S.col.down;
      ctx.fillRect(xb - 3.5, yx - 3.5, 7, 7);
      ctx.strokeStyle = cv_('--ground'); ctx.lineWidth = 1.3;
      ctx.strokeRect(xb - 3.5, yx - 3.5, 7, 7);
    }
  });
}
function drawTradeLabel(sc, ti, t, xa, w, on, ye, yt, ys){
    const f = tradeFacts(ti);
    const boxTop = Math.min(ye, yt, ys), boxBot = Math.max(ye, yt, ys);
    /* a stage badge in the corner of every box that has room for one, so the
       stage reads at any zoom: E for the evaluation, F once funded */
    if (S.tBoxes && f.stage && w >= 14){
      const funded = f.stage === 'funded';
      ctx.fillStyle = cv_('--panel'); ctx.fillRect(xa + 1, boxTop + 1, 12, 12);
      ctx.strokeStyle = funded ? S.col.accent : cv_('--rule'); ctx.lineWidth = 1;
      ctx.strokeRect(xa + 1.5, boxTop + 1.5, 11, 11);
      ctx.fillStyle = funded ? S.col.accent : cv_('--ink-dim');
      ctx.font = '600 9px ' + cv_('--mono'); ctx.textAlign = 'center';
      ctx.fillText(funded ? 'F' : 'E', xa + 7, boxTop + 10.5);
      ctx.textAlign = 'left';
    }
    /* Two-line label capping the box: the trade and its result, then the
       account it was taken in and the balance it started from. Always for the
       selected trade; for the others only when the box is at least as wide as
       the label, so labels can never overlap -- the next trade's box starts
       where this one ends. Opaque, so it reads over candles. */
    if (S.tLabels && f){
      const pnl = tradePnl(ti);
      const l1a = '#' + (ti + 1) + ' ' + (t.side > 0 ? 'LONG' : 'SHORT') + '  ';
      const l1b = money(pnl);
      const l2a = f.stage ? (f.stage === 'funded' ? 'FUNDED' : 'EVAL') + (f.acct ? ' #' + f.acct : '') : '';
      const l2b = f.before !== undefined ? (l2a ? '  \u00b7  ' : '') + 'from ' + money(f.before) : '';
      ctx.font = '600 10px ' + cv_('--mono');
      const w1 = ctx.measureText(l1a).width, w1b = ctx.measureText(l1b).width;
      ctx.font = '10px ' + cv_('--mono');
      const w2a = ctx.measureText(l2a).width, w2 = w2a + ctx.measureText(l2b).width;
      const bw = Math.max(w1 + w1b, w2) + 12, bh = 30;
      if (on || w >= bw){
        /* above the box unless that leaves the pane; then below it */
        let by = boxTop - 6 - bh;
        if (by < sc.P.y + 2) by = boxBot + 6;
        const bx = Math.min(xa, sc.P.x + sc.P.w - bw);
        ctx.fillStyle = cv_('--panel'); ctx.fillRect(bx, by, bw, bh);
        ctx.strokeStyle = on ? S.col.accent : cv_('--rule'); ctx.lineWidth = 1;
        ctx.strokeRect(bx + .5, by + .5, bw - 1, bh - 1);
        ctx.font = '600 10px ' + cv_('--mono');
        ctx.fillStyle = cv_('--ink'); ctx.fillText(l1a, bx + 6, by + 12);
        ctx.fillStyle = pnl >= 0 ? S.col.up : S.col.down; ctx.fillText(l1b, bx + 6 + w1, by + 12);
        ctx.font = '10px ' + cv_('--mono');
        ctx.fillStyle = f.stage === 'funded' ? S.col.accent : cv_('--ink-dim');
        ctx.fillText(l2a, bx + 6, by + 24);
        ctx.fillStyle = cv_('--ink-dim'); ctx.fillText(l2b, bx + 6 + w2a, by + 24);
      }
    }
}

function drawEquity(sc, a, b){
  /* The account's running result against the bar each trade CLOSED on, so a
     step up lines up with the trade that caused it. With a resizable pane
     there is room for a real axis and for the underwater curve, which is the
     thing a journal actually needs: not just what you made, but how far
     below the previous peak you were while making it. */
  const P = sc.P, y0 = P.y + P.h + P.subs + 3, h = P.eq - 6;
  ctx.fillStyle = cv_('--panel-2'); ctx.fillRect(P.x, y0, P.w, h);
  ctx.strokeStyle = cv_('--rule-soft'); ctx.lineWidth = 1;
  ctx.strokeRect(P.x + .5, y0 + .5, P.w, h);

  /* grip on the seam so it reads as draggable */
  ctx.fillStyle = cv_('--rule');
  for (let g = -12; g <= 12; g += 6) ctx.fillRect(P.x + P.w / 2 + g, y0 - 3, 3, 2);

  ctx.font = '9.5px ' + cv_('--mono'); ctx.textBaseline = 'middle';
  const label = txt => { ctx.fillStyle = cv_('--ink-faint'); ctx.textAlign = 'left';
                         ctx.fillText(txt, P.x + 7, y0 + 11); };
  if (!TRADES.length || !EQ.length){ label('equity \u2014 no trades loaded'); return; }
  const simOn = !!SIM;

  let lo = -1, hi = -1;
  for (let i = Math.max(0, Core.lowerBound(ENT, a - MAXSPAN)); i < TRADES.length; i++){
    if (ENT[i] < 0) continue;
    if (ENT[i] > b) break;
    const xe = aggExit(i);
    if (xe >= a && xe <= b){ if (lo < 0) lo = i; hi = i; }
  }
  if (lo < 0){ label('equity \u2014 no trades closed in this range'); return; }

  const prev = lo > 0 ? EQ[lo - 1] : 0;
  /* running peak, so the underwater curve is measured from the real high-water
     mark rather than from the left edge of whatever window you happen to view */
  const peakAt = i => { let pk = 0; for (let k = 0; k <= i; k++) if (EQ[k] > pk) pk = EQ[k]; return pk; };
  let mn = Math.min(prev, 0), mx = Math.max(prev, 0);
  for (let i = lo; i <= hi; i++){
    if (EQ[i] < mn) mn = EQ[i];
    if (EQ[i] > mx) mx = EQ[i];
  }
  let pk0 = peakAt(lo);
  if (pk0 > mx) mx = pk0;
  if (SIM){
    for (let i = lo; i <= hi; i++){
      const rr = SIM.rows[i];
      if (rr && !rr.skipped && rr.floor !== undefined && rr.floor < mn) mn = rr.floor;
    }
  }
  const pad = (mx - mn) * 0.12 || Math.max(1, Math.abs(mx) * 0.1);
  mn -= pad; mx += pad;
  const EY = v => y0 + h * (1 - (v - mn) / (mx - mn));

  const ticks = Math.max(2, Math.min(5, Math.floor(h / 34)));
  for (let k = 0; k <= ticks; k++){
    const v = mn + (mx - mn) * k / ticks, y = EY(v);
    ctx.strokeStyle = cv_('--rule-soft'); ctx.globalAlpha = 0.7;
    ctx.beginPath(); ctx.moveTo(P.x, y + .5); ctx.lineTo(P.x + P.w, y + .5); ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.fillStyle = cv_('--ink-faint'); ctx.textAlign = 'left';
    ctx.fillText(money(v), P.x + P.w + 7, y);
  }
  /* mark the starting balance when a real account is being simulated, so the
     curve reads against the number that was put in */
  const start0 = simOn ? SIM.summary.start : 0;
  if (simOn && start0 >= mn && start0 <= mx){
    ctx.setLineDash([2, 4]); ctx.strokeStyle = cv_('--ink-faint'); ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(P.x, EY(start0) + .5);
    ctx.lineTo(P.x + P.w, EY(start0) + .5); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = cv_('--ink-faint'); ctx.textAlign = 'left'; ctx.font = '9px ' + cv_('--mono');
    ctx.fillText('start ' + money(start0), P.x + 7, EY(start0) - 5);
    ctx.font = '9.5px ' + cv_('--mono');
  }
  if (mn < 0 && mx > 0){
    ctx.setLineDash([3, 3]); ctx.strokeStyle = cv_('--rule');
    ctx.beginPath(); ctx.moveTo(P.x, EY(0) + .5); ctx.lineTo(P.x + P.w, EY(0) + .5); ctx.stroke();
    ctx.setLineDash([]);
  }

  const X = i => sc.X(aggExit(i));
  const pts = [], pkPts = [];
  let run = pk0;
  if (lo > 0){ pts.push([sc.X(Math.max(a, aggExit(lo - 1))), prev]); pkPts.push([pts[0][0], run]); }
  for (let i = lo; i <= hi; i++){
    if (EQ[i] > run) run = EQ[i];
    pts.push([X(i), EQ[i]]); pkPts.push([X(i), run]);
  }

  /* underwater band: the gap between the running peak and the curve */
  if (S.eqMode !== 'curve' && pts.length > 1){
    ctx.beginPath();
    pkPts.forEach((q, k) => k ? ctx.lineTo(q[0], EY(q[1])) : ctx.moveTo(q[0], EY(q[1])));
    for (let k = pts.length - 1; k >= 0; k--) ctx.lineTo(pts[k][0], EY(pts[k][1]));
    ctx.closePath();
    ctx.globalAlpha = 0.16; ctx.fillStyle = S.col.down; ctx.fill(); ctx.globalAlpha = 1;
    ctx.beginPath();
    pkPts.forEach((q, k) => k ? ctx.lineTo(q[0], EY(q[1])) : ctx.moveTo(q[0], EY(q[1])));
    ctx.strokeStyle = cv_('--ink-faint'); ctx.setLineDash([4, 3]);
    ctx.lineWidth = 1; ctx.stroke(); ctx.setLineDash([]);
  }

  const rising = EQ[hi] >= prev, col = rising ? S.col.up : S.col.down;
  if (pts.length === 1){
    ctx.fillStyle = col;
    ctx.beginPath(); ctx.arc(pts[0][0], EY(pts[0][1]), 3.4, 0, Math.PI * 2); ctx.fill();
  } else {
    const base = EY(Math.max(mn, Math.min(mx, 0)));
    ctx.beginPath();
    pts.forEach((q, k) => k ? ctx.lineTo(q[0], EY(q[1])) : ctx.moveTo(q[0], EY(q[1])));
    ctx.lineTo(pts[pts.length - 1][0], base); ctx.lineTo(pts[0][0], base); ctx.closePath();
    ctx.globalAlpha = 0.13; ctx.fillStyle = col; ctx.fill(); ctx.globalAlpha = 1;
    ctx.beginPath();
    pts.forEach((q, k) => k ? ctx.lineTo(q[0], EY(q[1])) : ctx.moveTo(q[0], EY(q[1])));
    ctx.strokeStyle = col; ctx.lineWidth = 1.7; ctx.stroke();
  }

  /* a dot per closed trade once there is room to see them */
  if (h > 110 && pts.length < 400){
    for (let i = lo; i <= hi; i++){
      if (!tradeTaken(i)) continue;
      /* coloured by what THIS ACCOUNT made, not by the recorded trade */
      ctx.fillStyle = tradePnl(i) >= 0 ? S.col.up : S.col.down;
      ctx.beginPath(); ctx.arc(X(i), EY(EQ[i]), 2, 0, Math.PI * 2); ctx.fill();
    }
  }
  /* the trailing drawdown floor, drawn as the step function it actually is --
     it only ratchets at END OF DAY, which is why an account can be stopped out
     well above its starting bust level */
  if (SIM && SIM.rows[lo] && SIM.rows[lo].floor !== undefined){
    ctx.beginPath(); let started = false;
    for (let i = lo; i <= hi; i++){
      const rr = SIM.rows[i];
      if (!rr || rr.skipped || rr.floor === undefined) continue;
      const x = X(i), y = EY(rr.floor);
      if (!started){ ctx.moveTo(x, y); started = true; }
      else { ctx.lineTo(x, y); }
    }
    if (started){
      ctx.strokeStyle = S.col.down; ctx.lineWidth = 1.3;
      ctx.setLineDash([5, 3]); ctx.stroke(); ctx.setLineDash([]);
      const lastFloor = SIM.rows[hi] && SIM.rows[hi].floor;
      if (lastFloor !== undefined && lastFloor >= mn && lastFloor <= mx){
        ctx.fillStyle = S.col.down; ctx.font = '9px ' + cv_('--mono');
        ctx.textAlign = 'right';
        ctx.fillText('floor ' + money(lastFloor), P.x + P.w - 8, EY(lastFloor) - 5);
      }
    }
  }
  if (SIM){
    for (let i = lo; i <= hi; i++){
      const rr = SIM.rows[i];
      if (!rr || !rr.forced) continue;
      ctx.strokeStyle = S.col.down; ctx.lineWidth = 1.4;
      ctx.beginPath(); ctx.arc(X(i), EY(EQ[i]), 5, 0, Math.PI * 2); ctx.stroke();
    }
  }
  if (S.sel >= lo && S.sel <= hi){
    ctx.strokeStyle = S.col.accent; ctx.lineWidth = 1.2;
    ctx.setLineDash([2, 2]);
    ctx.beginPath(); ctx.moveTo(X(S.sel), y0); ctx.lineTo(X(S.sel), y0 + h); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = S.col.accent;
    ctx.beginPath(); ctx.arc(X(S.sel), EY(EQ[S.sel]), 3.6, 0, Math.PI * 2); ctx.fill();
  }

  const delta = EQ[hi] - prev;
  const under = run - EQ[hi];
  label((simOn ? 'account balance' : 'cumulative P&L') + ' \u00b7 ' +
        (hi - lo + 1) + ' trade' + (hi - lo ? 's' : '') + ' closed in view' +
        (simOn && SIM.summary.forced ? '  \u00b7 ' + SIM.summary.forced + ' forced liquidation' +
          (SIM.summary.forced > 1 ? 's' : '') : '') +
        (S.eqMode !== 'curve' ? '  \u00b7 shaded = drawdown from peak' : ''));
  ctx.textAlign = 'right';
  ctx.fillStyle = delta >= 0 ? S.col.up : S.col.down;
  ctx.fillText((delta >= 0 ? '+' : '') + money(delta) + ' in view', P.x + P.w - 8, y0 + 11);
  ctx.fillStyle = cv_('--ink-faint');
  ctx.fillText((simOn ? 'balance ' : 'total ') + money(EQ[hi]) +
               (under > 0 ? '   \u00b7 ' + money(-under) + ' below peak' : '   \u00b7 at peak'),
               P.x + P.w - 8, y0 + h - 9);
}

function drawCrosshair(sc){
  const P = sc.P;
  if (meas && meas.b){
    const x1 = sc.X(meas.a.i), x2 = sc.X(meas.b.i);
    const y1 = sc.Y(meas.a.v), y2 = sc.Y(meas.b.v);
    ctx.fillStyle = meas.b.v >= meas.a.v ? 'rgba(75,176,115,.16)' : 'rgba(209,86,90,.16)';
    ctx.fillRect(Math.min(x1, x2), Math.min(y1, y2), Math.abs(x2 - x1), Math.abs(y2 - y1));
    ctx.strokeStyle = cv_('--accent'); ctx.lineWidth = 1.2;
    ctx.strokeRect(Math.min(x1, x2) + .5, Math.min(y1, y2) + .5, Math.abs(x2 - x1), Math.abs(y2 - y1));
    const mm = Core.measure(meas.a.v, meas.b.v, meas.a.i, meas.b.i);
    const txt = (mm.pts >= 0 ? '+' : '') + mm.pts.toFixed(S.decimals) + ' pts   ' +
                (mm.pct >= 0 ? '+' : '') + mm.pct.toFixed(2) + '%   ' + mm.bars + ' bars';
    ctx.font = '600 10.5px ' + cv_('--mono');
    const tw = ctx.measureText(txt).width + 12;
    ctx.fillStyle = cv_('--accent');
    ctx.fillRect(Math.min(x1, x2), Math.min(y1, y2) - 20, tw, 17);
    ctx.fillStyle = '#171208'; ctx.textAlign = 'left';
    ctx.fillText(txt, Math.min(x1, x2) + 6, Math.min(y1, y2) - 11);
  }
  if (!mouse || mouse.x < P.x || mouse.x > P.x + P.w) return;
  let py = mouse.y, pv = sc.vAt(mouse.y);
  if (S.magnet){
    const bi = Math.round(sc.iAt(mouse.x));
    pv = Core.magnet(V, bi, pv); py = sc.Y(pv);
  }
  ctx.setLineDash([3, 3]); ctx.strokeStyle = cv_('--ink-faint'); ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(mouse.x + .5, P.y);
  ctx.lineTo(mouse.x + .5, P.y + P.h + P.subs + P.eq); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(P.x, py + .5); ctx.lineTo(P.x + P.w, py + .5); ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = S.magnet ? cv_('--i3') : cv_('--accent');
  ctx.fillRect(P.x + P.w + 2, py - 8, PAD.r - 4, 16);
  ctx.fillStyle = '#171208'; ctx.font = '600 10.5px ' + cv_('--mono'); ctx.textAlign = 'left';
  ctx.fillText(pv.toFixed(2), P.x + P.w + 7, py);
  const bi = Math.round(sc.iAt(mouse.x));
  if (bi >= 0 && bi < V.n){
    const lbl = stamp(bi);
    ctx.font = '10.5px ' + cv_('--mono');
    const tw = ctx.measureText(lbl).width + 10;
    const bx = Math.min(P.x + P.w - tw, Math.max(P.x, mouse.x - tw / 2));
    ctx.fillStyle = cv_('--accent');
    ctx.fillRect(bx, P.y + P.h + P.subs + P.eq + 4, tw, 15);
    ctx.fillStyle = '#171208'; ctx.textAlign = 'center';
    ctx.fillText(lbl, bx + tw / 2, P.y + P.h + P.subs + P.eq + 12);
  }
}

/* ---------------- interaction ---------------- */
function hitTrade(px){
  if (!S.showTrades) return -1;
  const sc = scales();
  const vis = Core.visibleTrades(ENT, EXT, S.view.a, S.view.b, MAXSPAN);
  for (const i of vis){
    if (px >= sc.X(aggEntry(i)) - 5 && px <= sc.X(aggExit(i)) + 5) return i;
  }
  return -1;
}
cvEl.addEventListener('mousemove', e => {
  const r = cvEl.getBoundingClientRect();
  mouse = {x: e.clientX - r.left, y: e.clientY - r.top};
  const P = plot(), sc = scales();
  if (!drag && !meas){
    const seam = P.y + P.h + P.subs;
    cvEl.style.cursor =
        (S.showEq && Math.abs(mouse.y - seam) <= 5 && mouse.x < P.x + P.w) ? 'ns-resize'
      : S.measure ? 'crosshair'
      : mouse.x > P.x + P.w ? 'ns-resize'
      : mouse.y > P.y + P.h + P.subs + P.eq ? 'ew-resize' : 'crosshair';
  }
  if (drag && drag.eq){
    S.eqH = Math.max(70, Math.min(H - 160, drag.h0 - (mouse.y - drag.y)));
    save(); render(); return;
  }
  if (meas && meas.down){
    let v = sc.vAt(mouse.y), i = sc.iAt(mouse.x);
    if (S.magnet) v = Core.magnet(V, Math.round(i), v);
    meas.b = {i, v};
  } else if (drag){
    if (drag.taxis){
      const k = Math.exp((drag.x - mouse.x) / 200);
      const mid = (drag.a + drag.b) / 2, half = (drag.b - drag.a) / 2 * k;
      S.view = {a: mid - half, b: mid + half}; clampView();
    } else if (drag.axis){
      const k = Math.exp((mouse.y - drag.y) / 160);
      const mid = (drag.lo + drag.hi) / 2, half = (drag.hi - drag.lo) / 2 * k;
      S.pmode = 'manual'; S.PR = {lo: mid - half, hi: mid + half};
      PR_CACHE.sig = null;
    } else {
      const span = drag.b - drag.a;
      const d = (drag.x - mouse.x) / P.w * span;
      S.view = {a: drag.a + d, b: drag.b + d}; clampView();
      const dy = mouse.y - drag.y;
      if (S.pmode === 'manual' || Math.abs(dy) > 3){
        const dp = dy / P.h * (drag.hi - drag.lo);
        S.pmode = 'manual'; S.PR = {lo: drag.lo + dp, hi: drag.hi + dp};
        PR_CACHE.sig = null;
      }
    }
  }
  render();
});
cvEl.addEventListener('mouseleave', () => { mouse = null; render(); });
cvEl.addEventListener('mousedown', e => {
  const r = cvEl.getBoundingClientRect();
  const px = e.clientX - r.left, py = e.clientY - r.top;
  const P = plot(), R = priceRange(), sc = scales();
  if (S.measure){
    let v = sc.vAt(py), i = sc.iAt(px);
    if (S.magnet) v = Core.magnet(V, Math.round(i), v);
    meas = {down: true, a: {i, v}, b: null};
    return;
  }
  /* the seam above the equity pane resizes it */
  const seam = P.y + P.h + P.subs;
  if (S.showEq && !onAxisArea(px, py) && Math.abs(py - seam) <= 5){
    drag = {eq: true, y: py, h0: S.eqH};
    cvEl.style.cursor = 'ns-resize';
    return;
  }
  const onPrice = px > P.x + P.w, onTime = !onPrice && py > P.y + P.h + P.subs + P.eq;
  drag = {x: px, y: py, a: S.view.a, b: S.view.b, lo: R.lo, hi: R.hi,
          axis: onPrice, taxis: onTime};
  if (!onPrice && !onTime){ const t = hitTrade(px); if (t >= 0) S.sel = t; }
  cvEl.style.cursor = onPrice ? 'ns-resize' : onTime ? 'ew-resize' : 'grabbing';
  render();
});
window.addEventListener('mouseup', () => {
  drag = null;
  if (meas) meas.down = false;
});
cvEl.addEventListener('wheel', e => {
  e.preventDefault();
  const sc = scales(), P = sc.P;
  if (mouse && mouse.x > P.x + P.w){
    const k = e.deltaY > 0 ? 1.15 : 1 / 1.15, at = sc.vAt(mouse.y);
    S.pmode = 'manual';
    S.PR = {lo: at - (at - sc.R.lo) * k, hi: at + (sc.R.hi - at) * k};
    PR_CACHE.sig = null;
    render(); return;
  }
  if (e.shiftKey){
    const d = (e.deltaY > 0 ? 1 : -1) * sc.span * 0.12;
    setView(S.view.a + d, S.view.b + d); return;
  }
  const at = sc.iAt(mouse ? mouse.x : P.x + P.w / 2), k = e.deltaY > 0 ? 1.2 : 1 / 1.2;
  setView(at - (at - S.view.a) * k, at + (S.view.b - at) * k);
}, {passive: false});
cvEl.addEventListener('dblclick', () => {
  const P = plot();
  if (mouse && mouse.x > P.x + P.w){ fitPrice(); return; }
  if (meas){ meas = null; render(); return; }
  const s = V.sessions[Core.sessionOf(V.sessions, Math.round(scales().iAt(mouse.x)))];
  fitPrice(); setView(s.a - 3, s.b + 3);
});
function fitPrice(){ S.pmode = 'auto'; S.PR = null; PR_CACHE.sig = null; render(); }
function onAxisArea(px, py){
  const P = plot();
  return px > P.x + P.w || py > P.y + P.h + P.subs + P.eq;
}

/* Resizing the canvas can itself perturb layout, so an observer that acts
   unconditionally can drive itself. Ignore a size already applied, and ignore
   a collapsed one (a hidden pane reports 0 and would blow the backing store
   away for nothing). */
let __lastW = -1, __lastH = -1, __lastDpr = -1, __resizeQueued = false;
function fitCanvas(){
  __resizeQueued = false;
  const dpr = window.devicePixelRatio || 1;
  const w = wrap.clientWidth, h = wrap.clientHeight;
  if (w <= 0 || h <= 0) return;
  if (w === __lastW && h === __lastH && dpr === __lastDpr) return;
  __lastW = w; __lastH = h; __lastDpr = dpr;
  W = w; H = h;
  cvEl.width = Math.round(w * dpr); cvEl.height = Math.round(h * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  render();
}
/* The work is deferred to the next frame. Done inside the callback it changes
   layout while the observer is still delivering, and Chrome reports
   "ResizeObserver loop completed with undelivered notifications" -- harmless,
   but the error strip showed it as an error every time a big file loaded and
   the panels reflowed. */
new ResizeObserver(() => {
  if (__resizeQueued) return;
  __resizeQueued = true;
  requestAnimationFrame(fitCanvas);
}).observe(wrap);

/* ---------------- panels ---------------- */
/* The trades carry the P&L the BACKTEST recorded (1 micro, its own costs).
   Once the account simulator is on, what matters is what YOUR account made at
   your size and your costs. Every widget goes through these two helpers so the
   ledger, the rail, the tooltip, the view total and the equity curve can never
   disagree with each other again. */
function tradePnl(i){
  if (SIM){ const r = SIM.rows[i]; return r && !r.skipped && r.pnl !== undefined ? r.pnl : 0; }
  return TRADES[i].pnl;
}
function tradeTaken(i){ return SIM ? !!(SIM.rows[i] && !SIM.rows[i].skipped) : true; }
/* The account context of one trade, the same on the chart, in the rail, in the
   tooltip and in the table: which account and stage it was taken in, and the
   balance it started from. The simulator's row wins when there is one (it is
   the accounting on screen); otherwise the trade's own fields. */
function tradeFacts(i){
  const t = TRADES[i], sr = SIM ? SIM.rows[i] : null;
  if (sr && !sr.skipped && sr.bal !== undefined)
    return {acct: sr.acct, stage: sr.stage || t.stage, before: sr.bal - sr.pnl, after: sr.bal};
  const after = t.bal, before = t.balBefore !== undefined ? t.balBefore
                            : (after !== undefined && t.pnl !== undefined ? after - t.pnl : undefined);
  return {acct: t.acct, stage: t.stage, before, after};
}
const stageTag = f => !f.stage ? '' :
  '<span class="tag ' + (f.stage === 'funded' ? 'F">FUNDED' : 'E">EVAL') + '</span>';

/* why a news-anchored trade or skip exists, for a hover title: looks up
   STLOADED.newsSides[day][minute].anchors -- the run's own news table, kept on
   STLOADED so this never recomputes against whatever the panel's settings have
   since changed to. Empty string for anything that isn't a news-anchored row. */
function newsAnchorTitle(t){
  const sides = STLOADED && STLOADED.newsSides;
  if (!sides || !t || t.entry_bar === undefined) return '';
  const day = sides[t.day];
  const slot = day && day[String(BASE.mins[t.entry_bar])];
  if (!slot || !slot.anchors || !slot.anchors.length) return '';
  return slot.anchors.map(a => a.event + ' ' + hhmm(a.releaseMinute) + ' ET (' + a.status +
    (a.offset === undefined ? '' : ', entry ' + offsetWords(a.offset)) +
    (a.moved ? '; ' + hhmm(a.plannedMinute) + ' had no bar, moved to ' + hhmm(BASE.mins[t.entry_bar]) : '') +
    ')').join(' + ');
}

function bindName(t){
  if (!t.why) return '';
  /* Strategy-panel rows say outright which barrier closed them; the shipped
     CSV's rows have to be inferred from the candidate distances */
  if (t.why === 'favourable'){
    if (t.capped !== undefined)
      return !t.capped ? 'target' : t.bind === 'pass' ? 'pass' : t.bind === 'payout' ? 'payout' : 'day tgt';
    return t.F < cfg.stop * cfg.rr - .01 ? 'day tgt' : 'target';
  }
  if (t.why === 'adverse'){
    if (t.forced !== undefined) return t.forced ? 'drawdown' : 'stop';
    return Math.abs(t.A - t.cand_stop) < .01 ? 'stop'
         : Math.abs(t.A - t.cand_dayloss) < .01 ? 'day loss' : 'drawdown';
  }
  return 'close';
}
const MAXROWS = 120;
let lastSig = '', queued = false, lastVis = [];
function onChange(){
  const sig = [Math.round(S.view.a), Math.round(S.view.b), S.sel, TRADES.length,
               S.tf, S.ct, S.showTrades, S.replay ? lastBar() : -1].join('|');
  if (sig !== lastSig){
    lastSig = sig;
    lastVis = Core.visibleTrades(ENT, EXT, S.view.a, Math.min(lastBar(), S.view.b), MAXSPAN);
    if (!queued){
      queued = true;
      requestAnimationFrame(() => {
        queued = false;
        try { paintPanels(lastVis); }
        catch (err){ document.getElementById('vstat').textContent = 'panel: ' + err.message; }
      });
    }
  }
  try { paintReadout(lastVis); }
  catch (err){ document.getElementById('vstat').textContent = 'readout: ' + err.message; }
}
function paintReadout(vis){
  const taken = vis.filter(tradeTaken);
  const net = taken.reduce((s, i) => s + tradePnl(i), 0);
  const w = taken.filter(i => tradePnl(i) > 0).length;
  document.getElementById('vstat').innerHTML =
    stamp(Math.max(0, Math.round(S.view.a))) + ' \u2192 ' +
    stamp(Math.min(V.n - 1, Math.round(S.view.b))) +
    ' &nbsp; <b>' + Math.round(S.view.b - S.view.a).toLocaleString() + '</b> bars &nbsp; ' +
    (SIM && taken.length !== vis.length
      ? taken.length + '/' + vis.length + ' taken'
      : vis.length + ' trades') +
    ' &nbsp; ' + w + 'W/' + (taken.length - w) + 'L &nbsp; <b class="' +
    (net >= 0 ? 'pos' : 'neg') + '">' + money(net) + '</b>' +
    (S.replay ? ' &nbsp; <b style="color:var(--accent)">REPLAY ' +
      (lastBar() + 1) + '/' + V.n + '</b>' : '');
  if (!mouse){ tip.classList.remove('on'); return; }
  const sc = scales(), bi = Math.round(sc.iAt(mouse.x));
  if (bi >= 0 && bi <= lastBar()){
    const up = V.c[bi] >= V.o[bi], col = up ? 'var(--up)' : 'var(--down)';
    document.getElementById('ohlc').innerHTML = '<span>' + stamp(bi) + '</span>' +
      ['O','H','L','C'].map((k, j) => '<span>' + k + ' <b style="color:' + col + '">' +
        [V.o, V.h, V.l, V.c][j][bi].toFixed(2) + '</b></span>').join('');
  }
  const hi = hitTrade(mouse.x);
  if (hi >= 0){
    const t = TRADES[hi];
    const f = tradeFacts(hi);
    tip.innerHTML = '<div class="hd" style="color:' +
      (t.side > 0 ? 'var(--long)' : 'var(--short)') + '">#' + (hi + 1) + ' \u00b7 ' +
      (t.side > 0 ? 'LONG' : 'SHORT') + '</div>' +
      (f.stage ? stageTag(f) + (f.acct ? ' account #' + f.acct : '') +
        (f.before !== undefined ? ' \u00b7 from ' + money(f.before) : '') + '<br>' : '') +
      (t.day || '') + '<br>' +
      'in&nbsp; ' + hhmm(BASE.mins[t.entry_bar]) + ' @ ' + t.entry.toFixed(2) + '<br>' +
      'stop ' + t.stop_px.toFixed(2) + ' &nbsp; tgt ' + t.tgt_px.toFixed(2) + '<br>' +
      'out ' + hhmm(BASE.mins[t.exit_bar]) + ' @ ' + t.exit.toFixed(2) +
      (t.why ? '<br><span style="color:var(--accent)">' + bindName(t) + '</span>' : '') +
      '<br><br>' + (() => {
        /* the running equity at this trade, in whichever mode is active:
           the account BALANCE when the simulator is on, the cumulative P&L of
           the loaded trades when it is off. An earlier version returned early
           in the off case and showed no running total at all. */
        const eq = EQ && EQ.length > hi ? EQ[hi] : null;
        const pk = EQPEAK && EQPEAK.length > hi ? EQPEAK[hi] : null;
        const under = (eq !== null && pk !== null && pk > eq) ? pk - eq : 0;
        const equityLines = label =>
          (eq === null ? '' :
            '<br><b>' + label + ' ' + money(eq) + '</b>' +
            (under > 0
              ? '  <span style="color:var(--down)">' + money(-under) + ' below peak</span>'
              : '  <span style="color:var(--up)">at peak</span>'));

        const sr = SIM ? SIM.rows[hi] : null;
        if (!sr) return t.pts.toFixed(2) + ' pts = ' + money(t.gross) +
          (t.slip + t.comm ? '<br>costs &minus;' + money(t.slip + t.comm).slice(1) : '') +
          '<br>net <b style="color:' + (t.pnl >= 0 ? 'var(--up)' : 'var(--down)') + '">' +
          money(t.pnl) + '</b>' +
          equityLines('running P&L') +
          '<br><span style="color:var(--ink-faint)">trade ' + (hi + 1) + ' of ' +
          TRADES.length.toLocaleString() + '</span>';
        if (sr.skipped) return '<span style="color:var(--ink-faint)" title="' + newsAnchorTitle(t) +
          '">not taken \u2014 ' + (sr.reason || 'account finished') + '</span>' + equityLines('balance');
        /* the size and start of whichever accounting produced these rows: the
           Strategy run's own, or the Prop firm settings */
        const pv = SIM.summary.pointValue !== undefined ? SIM.summary.pointValue : S.acct.pointValue;
        const start = SIM.summary.start;
        const gross = sr.pts * sr.size * pv;
        const cost = gross - sr.pnl;
        return sr.size + ' contract' + (sr.size > 1 ? 's' : '') + ' \u00d7 $' + pv + '/pt<br>' +
          sr.pts.toFixed(2) + ' pts = ' + money(gross) +
          '<br>costs &minus;' + money(cost).slice(1) +
          '<br>net <b style="color:' + (sr.pnl >= 0 ? 'var(--up)' : 'var(--down)') + '">' +
          money(sr.pnl) + '</b>' +
          '<br><b>balance ' + money(sr.bal) + '</b>' +
          '  <span style="color:' + (sr.bal >= start ? 'var(--up)' : 'var(--down)') +
          '">' + (sr.bal >= start ? '+' : '') +
          money(sr.bal - start) + ' from start</span>' +
          (under > 0 ? '<br><span style="color:var(--down)">' + money(-under) +
            ' below peak</span>' : '') +
          (sr.acct ? '<br><span style="color:var(--ink-faint)">account #' + sr.acct +
            '</span>' : '') +
          (sr.floor !== undefined ? '<br>floor ' + money(sr.floor) +
            '  <span style="color:var(--ink-faint)">(' +
            money(sr.bal - sr.floor) + ' of room)</span>' : '') +
          (sr.dayPnL !== undefined ? '<br>day so far ' + money(sr.dayPnL) : '') +
          (sr.forced ? '<br><b style="color:var(--down)">LIQUIDATED at ' +
            sr.exit.toFixed(2) + '</b>' : '') +
          (sr.capped ? '<br><b style="color:var(--accent)">' +
            (sr.bind === 'pass' ? 'closed at the pass line' : sr.bind === 'payout' ? 'closed at the payout line'
                                : 'booked at the daily cap') + '</b>' : '') +
          '<br>MAE ' + sr.mae.toFixed(1) + '  MFE ' + sr.mfe.toFixed(1);
      })();
    tip.classList.add('on');
    tip.style.left = Math.min(wrap.clientWidth - tip.offsetWidth - 8, mouse.x + 14) + 'px';
    tip.style.top = Math.min(wrap.clientHeight - tip.offsetHeight - 8, mouse.y + 14) + 'px';
  } else tip.classList.remove('on');
}
function paintPanels(vis){
  const shown = vis.slice(0, MAXROWS);
  document.getElementById('railh').textContent =
    'Trades in view (' + vis.length + (vis.length > MAXROWS ? ', showing ' + MAXROWS : '') + ')';
  if (SIM){
    const q = SIM.summary;
    const ve = q.evaluation;
    if (SERIES){
      /* NOT a return: the rail, ledger and navigator below still need painting.
         An earlier version returned here and silently froze all three. */
      const p = SERIES.summary;
      /* which list is being scored, so the number is never mistaken for the
         other one: a Strategy run keeps its own books; anything else is the
         loaded list re-priced under the Prop firm settings */
      const stratOn = STLOADED && TRADES === STLOADED.trades;
      document.getElementById('stats').innerHTML =
        '<div class="verdict ' + (p.passRate >= 0.5 ? 'pass' : 'fail') + '">' +
        p.passes + ' PASS / ' + p.fails + ' FAIL</div>' +
        '<div class="srcline">scoring ' + (stratOn ? 'the Strategy run, seed ' + STLOADED.seed
                                                : 'the loaded list under the Prop firm settings') + '</div>' +
        '<div class="kv">' +
        '<span>Accounts bought</span><b>' + p.accounts + '</b>' +
        '<span>Pass rate</span><b>' + (p.passRate * 100).toFixed(1) + '%</b>' +
        '<span>Still running</span><b>' + p.incomplete + '</b>' +
        '<span>Avg days each</span><b>' + p.avgDaysPerAccount.toFixed(1) + '</b>' +
        '<span>Avg trades each</span><b>' + p.avgTradesPerAccount.toFixed(1) + '</b>' +
        '<span>Trading P&L</span><b class="' + (p.pnl >= 0 ? 'pos' : 'neg') + '">' +
          money(p.pnl) + '</b>' +
        '<span>Fees</span><b class="neg">' + money(-p.ticketCost) + '</b>' +
        '<span>Net</span><b class="' + (p.net >= 0 ? 'pos' : 'neg') + '">' +
          money(p.net) + '</b>' +
        '</div>';
    } else {
    document.getElementById('stats').innerHTML =
      (ve ? '<div class="verdict ' + ve.verdict.toLowerCase() + '">' + ve.verdict + '</div>' +
        '<div class="kv"><span>Target</span><b>' + money(ve.target) + '</b>' +
        '<span>Best day</span><b class="' + (ve.bestDay > ve.dailyCap + 1e-6 ? 'neg' : '') +
        '">' + money(ve.bestDay) + ' / ' + money(ve.dailyCap) + '</b>' +
        '<span>Days traded</span><b>' + ve.days + '</b>' +
        '<span>Days capped</span><b>' + ve.capHits + '</b>' +
        '<span>Floor now</span><b>' + money(ve.finalFloor) + '</b></div>' : '') +
      '<div class="kv">' +
      [['Start', money(q.start)], ['Balance', money(q.end)],
       ['Return', q.returnPct.toFixed(1) + '%'],
       ['Peak', money(q.peak)], ['Max drawdown', money(-q.maxDrawdown)],
       ['Trades taken', String(q.taken)], ['Skipped', String(q.skipped)],
       ['Forced liquidations', String(q.forced)],
       ['Win rate', (q.winRate * 100).toFixed(1) + '%'],
       ['Account', q.blownUp ? 'BLOWN UP'
                  : q.stopped ? 'stopped' : 'alive']
      ].map(r => '<span>' + r[0] + '</span><b class="' +
        (r[0] === 'Return' || r[0] === 'Balance'
           ? (q.end >= q.start ? 'pos' : 'neg')
           : (r[0] === 'Account' && q.blownUp) || r[0] === 'Forced liquidations' && q.forced
             ? 'neg' : '') + '">' + r[1] + '</b>').join('') + '</div>';
    }
  } else {
  const st = STATS;
  document.getElementById('stats').innerHTML = !st || !st.n ? '<div class="empty">No trades loaded.</div>' :
    '<div class="kv">' +
    [['Trades', st.n.toLocaleString()],
     ['Win rate', (st.winRate * 100).toFixed(1) + '%'],
     ['Net P&L', money(st.net)],
     ['Profit factor', isFinite(st.profitFactor) ? st.profitFactor.toFixed(2) : '\u221e'],
     ['Expectancy', money(st.expectancy)],
     ['Avg win', money(st.avgWin)],
     ['Avg loss', money(-st.avgLoss)],
     ['Payoff', st.payoff.toFixed(2)],
     ['Max drawdown', money(-st.maxDrawdown)],
     ['Best streak', st.bestStreak + 'W'],
     ['Worst streak', Math.abs(st.worstStreak) + 'L']
    ].map(r => '<span>' + r[0] + '</span><b class="' +
      (r[0].indexOf('P&L') >= 0 || r[0] === 'Expectancy' ?
        (parseFloat(r[1].replace(/[^0-9.-]/g, '')) >= 0 ? 'pos' : 'neg') : '') + '">' +
      r[1] + '</b>').join('') + '</div>';
  }
  const rail = document.getElementById('rail');
  rail.innerHTML = !vis.length
    ? '<div class="empty">No trades in this range.<br>Zoom out, or use \u25c0 \u25b6.</div>'
    : shown.map(i => { const t = TRADES[i];
        const sr = SIM ? SIM.rows[i] : null;
        const pnl = tradePnl(i);
        const tagTxt = sr && sr.forced ? 'LIQ' : sr && sr.skipped ? 'skip' : bindName(t);
        const tg = tagDef(tagOf(i));
        return '<div class="trade' + (i === S.sel ? ' on' : '') + '" data-i="' + i + '"' +
          (tg ? ' style="border-left-color:' + tg.col + '"' : '') + '>' +
          '<div class="r1"><span>#' + (i + 1) + ' <span class="tag ' +
          (t.side > 0 ? 'L">LONG' : 'S">SHORT') + '</span></span><span class="' +
          (pnl >= 0 ? 'pos' : 'neg') + '">' + money(pnl) + '</span></div>' +
          '<div class="r2"><span>' + String(t.day || '').slice(5) + ' ' +
          hhmm(BASE.mins[t.entry_bar]) + '</span><span' +
          (sr && sr.forced ? ' style="color:var(--down)"' : '') + '>' + tagTxt +
          '</span></div>' +
          (() => {
            /* which account and stage, and the balance the trade started from
               and left behind; with no accounting on, the running P&L */
            const f = tradeFacts(i);
            if (f.stage && f.before !== undefined)
              return '<div class="r2"><span>' + stageTag(f) + (f.acct ? ' #' + f.acct : '') +
                '</span><span>' + money(f.before) + ' \u2192 ' + money(f.after) + '</span></div>';
            return EQ && EQ.length > i
              ? '<div class="r2"><span>' + (SIM ? 'balance' : 'running') + '</span><span>' +
                money(EQ[i]) + '</span></div>'
              : '';
          })() + '</div>';
      }).join('');
  document.getElementById('led').innerHTML = shown.map(i => {
    const t = TRADES[i], sr = SIM ? SIM.rows[i] : null;
    let chk = '<td>&mdash;</td>';
    if (t.why){
      const eS = +(t.entry - cfg.stop * t.side).toFixed(2);
      const eT = +(t.entry + cfg.stop * cfg.rr * t.side).toFixed(2);
      const eG = +(t.pts * cfg.dollars_per_point).toFixed(2);
      const eN = +(eG - t.slip - t.comm).toFixed(2);
      const ok = Math.abs(eS - t.stop_px) < .011 && Math.abs(eT - t.tgt_px) < .011 &&
                 Math.abs(eG - t.gross) < .011 && Math.abs(eN - t.pnl) < .011;
      chk = '<td class="' + (ok ? 'ok' : 'bad') + '">' + (ok ? '\u2713' : '\u2717') + '</td>';
    }
    /* when the simulator is running the ledger reports what the ACCOUNT did:
       its size, its real exit (which may be a liquidation), and its balance */
    const exitPx = sr && !sr.skipped ? sr.exit : t.exit;
    const pts = sr && !sr.skipped ? sr.pts : t.pts;
    const net = sr && !sr.skipped ? sr.pnl : t.pnl;
    const bal = sr && !sr.skipped ? sr.bal : t.bal;
    const bind = sr && sr.forced ? '<b style="color:var(--down)">LIQUIDATED</b>'
               : sr && sr.capped ? '<b style="color:var(--accent)">' +
                   (sr.bind === 'pass' ? 'PASS LINE' : sr.bind === 'payout' ? 'PAYOUT' : 'DAILY CAP') + '</b>'
               : sr && sr.skipped
                 ? '<span style="color:var(--ink-faint)" title="' + newsAnchorTitle(t) + '">' +
                   (sr.reason || 'skipped') + '</span>'
               : !sr && t.skipped
                 ? '<span style="color:var(--ink-faint)" title="' + newsAnchorTitle(t) + '">' +
                   (t.reason || 'skipped') + '</span>'
                 : bindName(t);
    const f = tradeFacts(i);
    return '<tr class="' + (i === S.sel ? 'on' : '') + '" data-i="' + i + '"><td>' + (i + 1) +
      '</td><td style="white-space:nowrap">' + (f.acct ? '#' + f.acct + ' ' : '') + stageTag(f) +
      (f.acct || f.stage ? '' : '\u2014') +
      '</td><td>' + (t.day || '') + '</td><td>' + hhmm(BASE.mins[t.entry_bar]) + '</td><td>' +
      hhmm(BASE.mins[t.exit_bar]) + '</td><td style="color:' +
      (t.side > 0 ? 'var(--long)' : 'var(--short)') + '">' + (t.side > 0 ? 'LONG' : 'SHORT') +
      '</td><td>' + (sr ? (sr.size || '\u2014') : '\u2014') +
      '</td><td><b>' + t.entry.toFixed(2) + '</b></td><td>' + t.stop_px.toFixed(2) + '</td><td>' +
      t.tgt_px.toFixed(2) + '</td><td><b>' + exitPx.toFixed(2) + '</b></td>' +
      '<td style="color:var(--accent)">' + bind + '</td>' +
      '<td>' + (sr && !sr.skipped ? sr.mae.toFixed(1) : '\u2014') + '</td>' +
      '<td>' + (sr && !sr.skipped ? sr.mfe.toFixed(1) : '\u2014') + '</td>' +
      '<td>' + pts.toFixed(2) + '</td>' +
      '<td class="' + (net >= 0 ? 'ok' : 'bad') + '"><b>' + money(net) + '</b></td>' +
      '<td>' + (f.before !== undefined ? money(f.before) : '\u2014') + '</td>' +
      '<td>' + money(bal) + '</td>' + chk + '</tr>';
  }).join('');
  const sn = V.sessions[Core.sessionOf(V.sessions, Math.max(0, Math.round(S.view.a)))];
  if (sn) document.getElementById('dbtnlbl').textContent = sn.day;
  drawNav();
  paintTagRow();
}
document.getElementById('rail').addEventListener('click', e => {
  const d = e.target.closest('.trade'); if (d) gotoTrade(+d.dataset.i);
});
document.getElementById('led').addEventListener('click', e => {
  const tr = e.target.closest('tr'); if (tr && tr.dataset.i) gotoTrade(+tr.dataset.i);
});
function gotoTrade(i){
  if (i < 0 || i >= TRADES.length) return;
  S.sel = i;
  const ea = aggEntry(i), eb = aggExit(i), pad = Math.max(20, (eb - ea) * 1.4);
  fitPrice(); setView(ea - pad, eb + pad);
}

/* ---------------- navigator ---------------- */
const navcv = document.getElementById('navcv'), nctx = navcv.getContext('2d');
let NAVPTS = null, navDrag = null;
function drawNav(){
  const w = navcv.clientWidth, h = navcv.clientHeight, dpr = window.devicePixelRatio || 1;
  if (navcv.width !== w * dpr || navcv.height !== h * dpr){
    navcv.width = w * dpr; navcv.height = h * dpr;
    nctx.setTransform(dpr, 0, 0, dpr, 0, 0); NAVPTS = null;
  }
  if (!NAVPTS){
    const cols = Math.max(200, Math.floor(w));
    NAVPTS = new Float64Array(cols);
    for (let px = 0; px < cols; px++)
      NAVPTS[px] = V.c[Math.min(V.n - 1, Math.floor(px / cols * V.n))];
  }
  nctx.clearRect(0, 0, w, h);
  let lo = Infinity, hi = -Infinity;
  for (const v of NAVPTS){ if (v < lo) lo = v; if (v > hi) hi = v; }
  const pad = (hi - lo) * 0.08 || 1; lo -= pad; hi += pad;
  const Y = v => 3 + (h - 6) * (1 - (v - lo) / (hi - lo));
  nctx.beginPath();
  for (let px = 0; px < NAVPTS.length; px++){
    const x = px / NAVPTS.length * w;
    px ? nctx.lineTo(x, Y(NAVPTS[px])) : nctx.moveTo(x, Y(NAVPTS[px]));
  }
  nctx.strokeStyle = cv_('--ink-faint'); nctx.lineWidth = 1; nctx.stroke();
  nctx.lineTo(w, h); nctx.lineTo(0, h); nctx.closePath();
  nctx.fillStyle = 'rgba(142,153,172,.10)'; nctx.fill();
  nctx.font = '9px ' + cv_('--mono'); nctx.textAlign = 'left';
  let lastY = '';
  V.sessions.forEach(sn => {
    const y = sn.day.slice(0, 4);
    if (y === lastY) return; lastY = y;
    const x = sn.a / V.n * w;
    nctx.strokeStyle = cv_('--rule');
    nctx.beginPath(); nctx.moveTo(x + .5, 0); nctx.lineTo(x + .5, h); nctx.stroke();
    nctx.fillStyle = cv_('--ink-faint'); nctx.fillText(y, x + 4, h - 4);
  });
  const xa = S.view.a / V.n * w, xb = S.view.b / V.n * w;
  nctx.fillStyle = 'rgba(216,162,74,.16)';
  nctx.fillRect(xa, 0, Math.max(2, xb - xa), h);
  nctx.strokeStyle = cv_('--accent'); nctx.lineWidth = 1.4;
  nctx.strokeRect(xa + .5, .5, Math.max(2, xb - xa) - 1, h - 1);
  nctx.fillStyle = cv_('--accent');
  nctx.fillRect(xa - 1, h / 2 - 7, 3, 14); nctx.fillRect(xb - 2, h / 2 - 7, 3, 14);
}
function navSet(e, mode){
  const r = navcv.getBoundingClientRect();
  const at = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * V.n;
  const span = S.view.b - S.view.a;
  if (mode === 'a') setView(Math.min(at, S.view.b - 8), S.view.b);
  else if (mode === 'b') setView(S.view.a, Math.max(at, S.view.a + 8));
  else setView(at - span / 2, at + span / 2);
}
navcv.addEventListener('mousedown', e => {
  const r = navcv.getBoundingClientRect();
  const xa = S.view.a / V.n * r.width, xb = S.view.b / V.n * r.width, px = e.clientX - r.left;
  navDrag = Math.abs(px - xa) < 6 ? 'a' : Math.abs(px - xb) < 6 ? 'b' : 'mid';
  navSet(e, navDrag);
});
window.addEventListener('mousemove', e => { if (navDrag) navSet(e, navDrag); });
window.addEventListener('mouseup', () => { navDrag = null; });
window.addEventListener('resize', () => { NAVPTS = null; drawNav(); });

/* ---------------- calendar ---------------- */
const cal = document.getElementById('cal');
let calY = 0, calM = 0, sessIdx = new Map(), DSTAT = new Map();
function reindexSessions(){
  sessIdx = new Map(); V.sessions.forEach((s, i) => sessIdx.set(s.day, i));
  DSTAT = new Map();
  TRADES.forEach(t => {
    const d = t.day || '';
    if (!DSTAT.has(d)) DSTAT.set(d, {pnl: 0, n: 0});
    const e = DSTAT.get(d); e.pnl += t.pnl; e.n++;
  });
}
const MON = ['January','February','March','April','May','June','July',
             'August','September','October','November','December'];
function openCal(){
  const cur = V.sessions[Core.sessionOf(V.sessions, Math.max(0, Math.round(S.view.a)))];
  const d = (cur ? cur.day : V.sessions[0].day).split('-');
  calY = +d[0]; calM = +d[1] - 1; drawCal();
  const r = document.getElementById('dbtn').getBoundingClientRect();
  cal.style.left = Math.min(window.innerWidth - 268, r.left) + 'px';
  cal.style.top = (r.bottom + 6) + 'px';
  cal.classList.add('on');
}
function drawCal(){
  document.getElementById('caltitle').textContent = MON[calM] + ' ' + calY;
  const startDow = (new Date(Date.UTC(calY, calM, 1)).getUTCDay() + 6) % 7;
  const ndays = new Date(Date.UTC(calY, calM + 1, 0)).getUTCDate();
  const cur = V.sessions[Core.sessionOf(V.sessions, Math.max(0, Math.round(S.view.a)))];
  const cells = [];
  for (let i = 0; i < startDow; i++) cells.push('<div class="cell"></div>');
  for (let d = 1; d <= ndays; d++){
    const key = calY + '-' + String(calM + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0');
    const has = sessIdx.has(key), st = DSTAT.get(key);
    const cls = ['cell'];
    if (has) cls.push('has');
    if (st && st.pnl > 0) cls.push('up');
    if (st && st.pnl < 0) cls.push('dn');
    if (cur && cur.day === key) cls.push('on');
    cells.push('<div class="' + cls.join(' ') + '"' + (has ? ' data-d="' + key + '"' : '') +
      (st ? ' title="' + st.n + ' trades, ' + money(st.pnl) + '"' : '') + '>' + d + '</div>');
  }
  document.getElementById('calgrid').innerHTML = cells.join('');
  [...document.querySelectorAll('.cell.has')].forEach(c => c.onclick = () => {
    const sn = V.sessions[sessIdx.get(c.dataset.d)];
    fitPrice(); setView(sn.a - 3, sn.b + 3); cal.classList.remove('on');
  });
  const pre = calY + '-' + String(calM + 1).padStart(2, '0');
  const inM = [...sessIdx.keys()].filter(k => k.indexOf(pre) === 0);
  const pnl = inM.reduce((a, k) => a + (DSTAT.get(k) ? DSTAT.get(k).pnl : 0), 0);
  const ntr = inM.reduce((a, k) => a + (DSTAT.get(k) ? DSTAT.get(k).n : 0), 0);
  document.getElementById('calfoot').innerHTML = inM.length
    ? inM.length + ' sessions &middot; ' + ntr + ' trades &middot; <b class="' +
      (pnl >= 0 ? 'pos' : 'neg') + '">' + money(pnl) + '</b><br>shading = day P&amp;L'
    : 'No sessions in this month.';
}
document.getElementById('dbtn').onclick = e => {
  e.stopPropagation();
  cal.classList.contains('on') ? cal.classList.remove('on') : openCal();
};
cal.onclick = e => e.stopPropagation();
window.addEventListener('click', () => cal.classList.remove('on'));
document.getElementById('cm0').onclick = () => { if (--calM < 0){ calM = 11; calY--; } drawCal(); };
document.getElementById('cm1').onclick = () => { if (++calM > 11){ calM = 0; calY++; } drawCal(); };
document.getElementById('cy0').onclick = () => { calY--; drawCal(); };
document.getElementById('cy1').onclick = () => { calY++; drawCal(); };

/* ---------------- toolbar ---------------- */
function seg(id, items, get, set){
  const el = document.getElementById(id);
  el.innerHTML = items.map(([lbl, val]) =>
    '<button class="btn' + (get() === val ? ' on' : '') + '" data-v="' + val + '">' + lbl + '</button>').join('');
  el.onclick = e => {
    if (e.target.tagName !== 'BUTTON') return;
    set(e.target.dataset.v);
    [...el.children].forEach(b => b.classList.toggle('on', b.dataset.v == String(get())));
  };
}
seg('tfseg', TFS, () => S.tf, v => { S.tf = +v; rebuild(); NAVPTS = null; reindexSessions();
  lastSig = ''; setView(0, Math.min(V.n - 1, 390)); save(); });
seg('ctseg', CTS, () => S.ct, v => { S.ct = v; rebuild(); lastSig = ''; render(); save(); });
function tog(id, get, set){
  const b = document.getElementById(id);
  b.classList.toggle('on', !!get());
  b.onclick = () => { set(!get()); b.classList.toggle('on', !!get()); save(); render(); };
}
tog('blog', () => S.log, v => { S.log = v; });
tog('bmag', () => S.magnet, v => { S.magnet = v; });
tog('bmeas', () => S.measure, v => { S.measure = v; if (!v) meas = null; });
tog('btr', () => S.showTrades, v => { S.showTrades = v; lastSig = ''; });
tog('brth', () => S.rthOnly, v => { S.rthOnly = v; });
tog('beq', () => S.showEq, v => { S.showEq = v; });
document.getElementById('bfit').onclick = () => fitPrice();
document.getElementById('ltog').onclick = e => {
  const L = document.querySelector('.ledger');
  L.classList.toggle('hid');
  e.target.classList.toggle('on', !L.classList.contains('hid'));
};
document.getElementById('bfull').onclick = () => {
  if (document.fullscreenElement) document.exitFullscreen();
  else document.documentElement.requestFullscreen().catch(() => {});
};
document.getElementById('tprev').onclick = () => gotoTrade(Math.max(0, S.sel - 1));
document.getElementById('tnext').onclick = () => gotoTrade(Math.min(TRADES.length - 1, S.sel + 1));
document.getElementById('tgo').onchange = e => {
  const i = parseInt(e.target.value, 10) - 1;
  if (!isNaN(i)) gotoTrade(Math.max(0, Math.min(TRADES.length - 1, i)));
};

/* ---------------- replay ---------------- */
let rTimer = null;
function setReplay(on){
  S.replay = on;
  document.getElementById('rtog').classList.toggle('on', on);
  if (on){
    const cur = lastBar();
    if (cur < S.view.a || cur > S.view.b)
      S.rBase = Core.viewToReplay(Math.round(S.view.a + (S.view.b - S.view.a) * 0.3), V, BASE.n);
  }
  if (!on) stopPlay();
  lastSig = ''; render();
}
function stopPlay(){
  S.playing = false; clearInterval(rTimer); rTimer = null;
  document.getElementById('rplay').textContent = '\u25b6';
}
document.getElementById('rtog').onclick = () => setReplay(!S.replay);
function stepReplay(){
  if (!S.replay) setReplay(true);
  const nxt = Math.min(V.n - 1, lastBar() + 1);
  S.rBase = Core.viewToReplay(nxt, V, BASE.n);
  if (nxt > S.view.b - 2) setView(S.view.a + 1, S.view.b + 1);
  else { lastSig = ''; render(); }
  return nxt < V.n - 1;
}
document.getElementById('rstep').onclick = stepReplay;
document.getElementById('rplay').onclick = () => {
  if (!S.replay) setReplay(true);
  if (S.playing){ stopPlay(); return; }
  S.playing = true;
  document.getElementById('rplay').textContent = '\u2016';
  rTimer = setInterval(() => { if (!stepReplay()) stopPlay(); }, 1000 / S.speed);
};
document.getElementById('rspd').onchange = e => {
  S.speed = parseInt(e.target.value, 10);
  if (S.playing){ stopPlay(); document.getElementById('rplay').click(); }
};

/* ---------------- keyboard ---------------- */
const HELP = [
  ['&#8592; / &#8594;', 'previous / next trade'],
  ['Shift + &#8592;/&#8594;', 'pan the chart'],
  ['+ / &minus;', 'zoom in / out'],
  ['F', 'fit price to view'],
  ['L', 'toggle log scale'],
  ['M', 'toggle magnet'],
  ['R', 'toggle measure tool'],
  ['T', 'toggle trade overlay'],
  ['E', 'toggle equity pane'],
  ['Space', 'play / pause replay'],
  ['. (period)', 'step one bar in replay'],
  ['1..5', 'tag the selected trade with a setup'],
  ['Shift + 1..7', 'timeframe 1m .. Daily'],
  ['Esc', 'close dialogs, clear measurement']
];
window.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  const k = e.key.toLowerCase();
  const hit = {
    'arrowleft': () => e.shiftKey ? setView(S.view.a - sp() * .2, S.view.b - sp() * .2)
                                  : gotoTrade(Math.max(0, S.sel - 1)),
    'arrowright': () => e.shiftKey ? setView(S.view.a + sp() * .2, S.view.b + sp() * .2)
                                   : gotoTrade(Math.min(TRADES.length - 1, S.sel + 1)),
    '+': () => zoomC(1 / 1.4), '=': () => zoomC(1 / 1.4), '-': () => zoomC(1.4),
    'f': () => fitPrice(),
    'l': () => document.getElementById('blog').click(),
    'm': () => document.getElementById('bmag').click(),
    'r': () => document.getElementById('bmeas').click(),
    't': () => document.getElementById('btr').click(),
    'e': () => document.getElementById('beq').click(),
    ' ': () => document.getElementById('rplay').click(),
    '.': () => document.getElementById('rstep').click(),
    'escape': () => { cal.classList.remove('on');
                      document.getElementById('modal').classList.remove('on', 'peek');
                      meas = null; render(); }
  }[k];
  if (hit){ e.preventDefault(); hit(); return; }
  const n = parseInt(k, 10);
  if (n >= 1 && n <= 9){
    e.preventDefault();
    /* with a trade selected the digits tag it, which is what a journal wants;
       otherwise they still switch timeframe */
    if (S.sel >= 0 && n <= TAGDEF.length && !e.shiftKey){
      setTag(S.sel, TAGDEF[n - 1].id); paintTagRow();
    } else if (n <= TFS.length){
      document.querySelector('#tfseg .btn[data-v="' + TFS[n - 1][1] + '"]').click();
    }
  }
});
const sp = () => S.view.b - S.view.a;
function zoomC(k){
  const mid = (S.view.a + S.view.b) / 2;
  setView(mid - sp() / 2 * k, mid + sp() / 2 * k);
}

/* ---------------- help / schema ---------------- */
document.getElementById('bhelp').onclick = () => {
  document.getElementById('sheet').classList.remove('sz');
  document.getElementById('sheet').innerHTML =
    '<h2>Tape Reader</h2><p>A chart and journal for inspecting backtest trades on the bars that produced them. Bars and trades are independent layers: load either on its own.</p>' +
    '<h3>Keyboard</h3><table>' + HELP.map(r =>
      '<tr><td><kbd>' + r[0] + '</kbd></td><td>' + r[1] + '</td></tr>').join('') + '</table>' +
    '<h3>Mouse</h3><table>' +
    [['drag chart', 'pan time and price together'],
     ['drag right gutter', 'scale price'],
     ['drag bottom gutter', 'scale time'],
     ['scroll', 'zoom time (shift to pan)'],
     ['scroll on price gutter', 'zoom price'],
     ['double-click', 'fit the session; on the gutter, refit price'],
     ['drag the navigator', 'move the view; drag its edges to resize']
    ].map(r => '<tr><td><kbd>' + r[0] + '</kbd></td><td>' + r[1] + '</td></tr>').join('') + '</table>' +
    '<h3>Bars &mdash; CSV</h3><pre>datetime,open,high,low,close\n2023-01-03 09:30,10990.25,10994.00,10986.50,10991.75</pre>' +
    '<p>Column names matched case-insensitively; <code>date</code>+<code>time</code>, <code>o/h/l/c</code> and <code>timestamp</code> also work. Sessions split on the date. Any instrument, any timeframe.</p>' +
    '<h3>Trades &mdash; CSV</h3><pre>entry_time,exit_time,side,entry,exit,stop,target,pnl\n2023-01-03 10:00,2023-01-03 10:18,-1,10994.00,10944.00,11044.00,10944.00,97.50</pre>' +
    '<p><code>side</code> takes <code>1</code>/<code>-1</code> or <code>long</code>/<code>short</code>. <code>stop</code>, <code>target</code> and <code>pnl</code> are optional. Times are matched to the loaded bars; <code>entry_bar</code>/<code>exit_bar</code> integer indices work too.</p>' +
    '<h3>Notes</h3><p>VWAP here is anchored to each session but this dataset carries no volume, so it is a typical-price average rather than a true volume-weighted price. Aggregated candles never span two sessions. The ledger re-derives stop, target, gross and net from first principles and marks each row \u2713 or \u2717.</p>' +
    '<button class="btn" onclick="document.getElementById(\'modal\').classList.remove(\'on\')">Close</button>';
  openSheet();
};
/* every panel but Strategy is a centred sheet over a dimmed chart; Strategy
   adds 'peek' (side sheet, chart live underneath), which must not leak into
   the next panel to open */
function openSheet(){
  const m = document.getElementById('modal');
  m.classList.remove('peek'); m.classList.add('on');
}
document.getElementById('modal').onclick = e => {
  if (e.target.id === 'modal'){
    e.target.classList.remove('on', 'peek');
    document.getElementById('sheet').classList.remove('sz');   // or the next dialog opens wide
  }
};





/* ------------------------------------------------------------------
   A tool you rely on must not fail silently. Any uncaught error, any
   rejected promise, and any error thrown inside a button handler is
   surfaced in a banner with the message and the line, instead of the
   click simply doing nothing.
   ------------------------------------------------------------------ */
function showError(where, err){
  const box = document.getElementById('errbar');
  if (!box) return;
  const msg = (err && err.message) ? err.message : String(err);
  const at = (err && err.stack)
    ? (String(err.stack).split('\n')[1] || '').trim().slice(0, 120) : '';
  box.innerHTML = '<b>' + where + ':</b> ' + msg +
    (at ? '<br><span class="at">' + at + '</span>' : '') +
    '<button class="btn" id="errclose">Dismiss</button>';
  box.classList.add('on');
  const c = document.getElementById('errclose');
  if (c) c.onclick = () => box.classList.remove('on');
}
window.addEventListener('error', e => {
  /* a browser notice, not a fault: layout settled a frame late */
  if (/ResizeObserver loop/.test(String(e.message || ''))) return;
  showError('Error', e.error || e.message);
});
window.addEventListener('unhandledrejection', e => showError('Error', e.reason));
/* wrap every toolbar handler so a throw is reported, not swallowed */
function guard(id, fn, label){
  const el = document.getElementById(id);
  if (!el) { showError('Wiring', new Error('missing element #' + id)); return; }
  el.onclick = ev => {
    try { fn(ev); }
    catch (err){ showError((label || id) + ' click', err); }
  };
}





function setupStats(){
  const by = {};
  const push = (k, i) => {
    if (!by[k]) by[k] = {n: 0, wins: 0, pnl: 0, mae: 0, mfe: 0, nx: 0};
    const b = by[k], p = tradePnl(i);
    b.n++; b.pnl += p; if (p > 0) b.wins++;
    if (SIM && SIM.rows[i] && !SIM.rows[i].skipped){
      b.mae += SIM.rows[i].mae; b.mfe += SIM.rows[i].mfe; b.nx++;
    }
  };
  for (let i = 0; i < TRADES.length; i++){
    if (!tradeTaken(i)) continue;
    push(tagOf(i) || '_', i);
  }
  return by;
}
function setupsHTML(){
  const by = setupStats();
  const rows = TAGDEF.map(d => [d, by[d.id]]).filter(x => x[1]);
  const untagged = by['_'];
  const tot = Object.values(by).reduce((a, b) => a + b.n, 0);
  const fmtRow = (name, col, b) =>
    '<tr><td><span class="tagchip" style="background:' + col + '22;color:' + col +
    ';border-color:' + col + '">' + name + '</span></td>' +
    '<td>' + b.n + '</td>' +
    '<td>' + (100 * b.wins / b.n).toFixed(1) + '%</td>' +
    '<td class="' + (b.pnl >= 0 ? 'ok' : 'bad') + '"><b>' + money(b.pnl) + '</b></td>' +
    '<td>' + money(b.pnl / b.n) + '</td>' +
    '<td>' + (b.nx ? (b.mae / b.nx).toFixed(1) : '\u2014') + '</td>' +
    '<td>' + (b.nx ? (b.mfe / b.nx).toFixed(1) : '\u2014') + '</td></tr>';
  return '<h2>Setups</h2>' +
    '<p>Tag a trade with the setup it belongs to, then compare setups against each other. ' +
    'Click a trade in the ledger or the rail to select it, then press <kbd>1</kbd>\u2013<kbd>5</kbd> ' +
    'to tag it, or use the chips under the chart. Tags are stored against the trade\'s entry bar, ' +
    'so they survive a reload and are not disturbed by filtering or re-running a strategy.</p>' +
    (tot ? '<table class="sztab"><thead><tr><th>Setup</th><th>Trades</th><th>Win rate</th>' +
      '<th>Net</th><th>Per trade</th><th>Avg MAE</th><th>Avg MFE</th></tr></thead><tbody>' +
      rows.map(x => fmtRow(x[0].name, x[0].col, x[1])).join('') +
      (untagged ? fmtRow('Untagged', cv_('--ink-faint'), untagged) : '') +
      '</tbody></table>'
     : '<p style="color:var(--ink-faint)">Nothing tagged yet.</p>') +
    (rows.length > 1 ? '<p style="margin-top:8px">The comparison only means something once ' +
      'each setup has a decent number of trades \u2014 with a handful, the difference between ' +
      'two win rates is noise.</p>' : '') +
    '<h3>Tags</h3><div class="tagpick">' +
    TAGDEF.map(d => '<span class="tagchip" style="background:' + d.col + '22;color:' + d.col +
      ';border-color:' + d.col + '">' + d.name + '</span>').join('') + '</div>' +
    '<div style="margin-top:12px;display:flex;gap:6px">' +
    '<button class="btn" id="tgClose">Close</button>' +
    '<button class="btn" id="tgClear">Clear all tags</button></div>';
}
function openSetups(){
  const sh = document.getElementById('sheet');
  sh.classList.remove('sz');
  sh.innerHTML = setupsHTML();
  openSheet();
  const c = document.getElementById('tgClose');
  if (c) c.onclick = () => document.getElementById('modal').classList.remove('on');
  const cl = document.getElementById('tgClear');
  if (cl) cl.onclick = () => {
    TAGS = {}; saveTags(); lastSig = ''; render();
    sh.innerHTML = setupsHTML(); openSetupsRebind();
  };
}
function openSetupsRebind(){
  const c = document.getElementById('tgClose');
  if (c) c.onclick = () => document.getElementById('modal').classList.remove('on');
  const cl = document.getElementById('tgClear');
  if (cl) cl.onclick = () => { TAGS = {}; saveTags(); lastSig = ''; render(); openSetups(); };
}
guard('btags', openSetups, 'Setups');

/* the chip row that tags whatever trade is selected */
function paintTagRow(){
  const el = document.getElementById('tagrow');
  if (!el) return;
  const cur = S.sel >= 0 ? tagOf(S.sel) : null;
  el.innerHTML = '<span class="lbl">Setup</span>' +
    (S.sel < 0
      ? '<span style="color:var(--ink-faint);font-family:var(--mono);font-size:10px">' +
        'select a trade to tag it</span>'
      : TAGDEF.map((d, k) => '<span class="tagchip' + (cur === d.id ? '' : ' off') +
          '" data-tag="' + d.id + '" style="background:' + d.col + '22;color:' + d.col +
          ';border-color:' + d.col + '">' + (k + 1) + ' ' + d.name + '</span>').join('') +
        '<span style="color:var(--ink-faint);font-family:var(--mono);font-size:10px;margin-left:6px">' +
        'trade #' + (S.sel + 1) + (cur ? '' : ' \u2014 untagged') + '</span>');
  el.querySelectorAll('[data-tag]').forEach(c => c.onclick = () => {
    setTag(S.sel, c.dataset.tag); paintTagRow();
  });
}


/* ================= the deep report =================
   The panel shows one configuration. The question -- how do I make the most
   money buying these things? -- needs a sweep across configurations, which is
   what this builds. Every number here is recomputed from the loaded trades;
   nothing is pre-baked. */

const RPT = {sizes: null, cache: {}};

function rptLadder(){
  /* Micros and minis overlap: 10 MNQ and 1 NQ are both $20 a point, and differ
     only in commission. Both are listed, sorted by what a point is worth, so
     the table reads as one continuous ladder from $2 to $200 a point. */
  const out = [];
  for (let n = 1; n <= 20; n++)
    out.push({label: n + ' MNQ', pv: 2 * n, comm: 0.75 * n, micro: true});
  for (let n = 1; n <= 10; n++)
    out.push({label: n + ' NQ', pv: 20 * n, comm: 1.5 * n, micro: false});
  out.sort((a, b) => a.pv - b.pv || a.comm - b.comm);
  return out;
}

/* trade -> bar maps, built once and shared by every run in the sweep */
function rptIdx(){
  const src = SRC || BASE;
  return {
    src: src,
    e: TRADES.map(t => (FWD ? FWD[Math.min(src.n - 1, t.entry_bar)] : t.entry_bar)),
    x: TRADES.map(t => (FWD ? FWD[Math.min(src.n - 1, t.exit_bar)] : t.exit_bar))
  };
}

function rptRun(ix, over){
  const a = JSON.parse(JSON.stringify(S.acct));
  a.on = true; a.sizeMode = 'fixed'; a.contracts = 1;
  a.evaluation.on = true; a.evaluation.repeat = true;
  Object.keys(over || {}).forEach(k => {
    if (k === 'pv') a.pointValue = over[k];
    else if (k === 'comm') a.commission = over[k];
    else a.evaluation[k] = over[k];
  });
  return Core.simulateSeries(ix.src, TRADES, ix.e, ix.x, a);
}

/* wealth session by session: every ticket is spent the day the account opens,
   every payout is received the day it is reached */
function rptWealth(res, ix, ticket){
  const S0 = ix.src.sessions, nS = S0.length;
  const flow = new Float64Array(nS);
  res.accounts.forEach(a => {
    const b0 = ix.e[a.from], b1 = ix.x[a.to];
    if (b0 >= 0) flow[Core.sessionOf(S0, b0)] -= ticket;
    if (a.paid && b1 >= 0) flow[Core.sessionOf(S0, b1)] += a.paid;
  });
  const cum = new Float64Array(nS);
  let run = 0;
  for (let i = 0; i < nS; i++){ run += flow[i]; cum[i] = run; }
  return cum;
}

/* --- small chart helpers, all inline SVG so the report is self-contained --- */
function rptLine(series, labels, w, h, colFor){
  const PADL = 78, PADR = 14, PADT = 12, PADB = 26;
  const pw = w - PADL - PADR, ph = h - PADT - PADB;
  let lo = Infinity, hi = -Infinity;
  series.forEach(s => s.v.forEach(v => { if (v < lo) lo = v; if (v > hi) hi = v; }));
  lo = Math.min(lo, 0); hi = Math.max(hi, 0);
  const pad = (hi - lo) * 0.08 || 1; lo -= pad; hi += pad;
  const n = Math.max(1, series[0].v.length);
  const X = i => PADL + pw * i / Math.max(1, n - 1);
  const Y = v => PADT + ph * (1 - (v - lo) / (hi - lo));
  let out = '<svg viewBox="0 0 ' + w + ' ' + h + '" role="img">';
  for (let k = 0; k <= 4; k++){
    const v = lo + (hi - lo) * k / 4, y = Y(v);
    out += '<line x1="' + PADL + '" y1="' + y + '" x2="' + (w - PADR) + '" y2="' + y +
           '" class="g"/><text x="' + (PADL - 6) + '" y="' + (y + 3) +
           '" class="ax" text-anchor="end">' + money0(v) + '</text>';
  }
  out += '<line x1="' + PADL + '" y1="' + Y(0) + '" x2="' + (w - PADR) + '" y2="' + Y(0) +
         '" class="z"/>';
  series.forEach(s => {
    let d = '';
    s.v.forEach((v, i) => { d += (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1) + ' '; });
    out += '<path d="' + d + '" fill="none" stroke="' + s.col + '" stroke-width="' +
           (s.w || 1.8) + '" opacity="' + (s.o === undefined ? 1 : s.o) + '"/>';
  });
  (labels || []).forEach(function(L){
    out += '<text x="' + X(L.i) + '" y="' + (h - 7) + '" class="ax" text-anchor="middle">' +
           esc(L.t) + '</text>';
  });
  return out + '</svg>';
}

function rptBars(rows, w, h){
  const PADL = 78, PADR = 60, PADT = 8, PADB = 8;
  const pw = w - PADL - PADR;
  const bh = Math.max(13, (h - PADT - PADB) / Math.max(1, rows.length));
  let lo = 0, hi = 0;
  rows.forEach(r => { if (r.v < lo) lo = r.v; if (r.v > hi) hi = r.v; });
  if (hi === lo) hi = lo + 1;
  const X = v => PADL + pw * (v - lo) / (hi - lo);
  let out = '<svg viewBox="0 0 ' + w + ' ' + (PADT + PADB + bh * rows.length) + '" role="img">';
  const z = X(0);
  rows.forEach((r, i) => {
    const y = PADT + i * bh, x = X(r.v);
    out += '<text x="' + (PADL - 6) + '" y="' + (y + bh / 2 + 3) +
           '" class="ax" text-anchor="end">' + esc(r.label) + '</text>' +
           '<rect x="' + Math.min(z, x) + '" y="' + (y + 2) + '" width="' +
           Math.max(1, Math.abs(x - z)) + '" height="' + (bh - 4) + '" fill="' +
           (r.v >= 0 ? '#4bb073' : '#d1565a') + '" opacity="' + (r.best ? 1 : .62) + '"/>' +
           /* a long negative bar leaves no room to the left of its end, and the
              label would print on top of the row name -- put it inside instead */
           (function(){
             const txt = money0(r.v) + (r.best ? '  \u25c0 best' : '');
             const room = x - PADL;
             const inside = r.v < 0 && room < 9 * txt.length;
             const tx = r.v >= 0 ? x + 5 : (inside ? x + 6 : x - 5);
             const anchor = (r.v >= 0 || inside) ? 'start' : 'end';
             return '<text x="' + tx + '" y="' + (y + bh / 2 + 3) +
                    '" class="ax" text-anchor="' + anchor + '">' + txt + '</text>';
           })();
  });
  out += '<line x1="' + z + '" y1="' + PADT + '" x2="' + z + '" y2="' +
         (PADT + bh * rows.length) + '" class="z"/>';
  return out + '</svg>';
}

function rptHist(vals, w, h, bins, fmt){
  if (!vals.length) return '<p class="dim">nothing to show</p>';
  const PADL = 40, PADR = 12, PADT = 10, PADB = 24;
  const pw = w - PADL - PADR, ph = h - PADT - PADB;
  let lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
  if (hi === lo) hi = lo + 1;
  const B = bins || 24, cnt = new Array(B).fill(0);
  vals.forEach(v => { let k = Math.floor((v - lo) / (hi - lo) * B); if (k >= B) k = B - 1;
                      if (k < 0) k = 0; cnt[k]++; });
  const mx = Math.max.apply(null, cnt) || 1;
  let out = '<svg viewBox="0 0 ' + w + ' ' + h + '" role="img">';
  cnt.forEach((c, i) => {
    const x = PADL + pw * i / B, bw = pw / B - 1.5;
    const bh2 = ph * c / mx;
    out += '<rect x="' + x + '" y="' + (PADT + ph - bh2) + '" width="' + bw +
           '" height="' + bh2 + '" fill="#6ea8dc" opacity=".8"/>';
  });
  out += '<text x="' + PADL + '" y="' + (h - 7) + '" class="ax">' + fmt(lo) + '</text>' +
         '<text x="' + (w - PADR) + '" y="' + (h - 7) + '" class="ax" text-anchor="end">' +
         fmt(hi) + '</text>' +
         '<text x="' + (PADL - 5) + '" y="' + (PADT + 8) + '" class="ax" text-anchor="end">' +
         mx + '</text>';
  return out + '</svg>';
}

/* -------------------------- the report itself -------------------------- */
function buildReport(){
  const ix = rptIdx();
  const ev = S.acct.evaluation;
  const ticket = ev.cost;
  const ladder = rptLadder();
  const S0 = ix.src.sessions, nS = S0.length;

  /* the configuration on screen */
  const cur = rptRun(ix, {});
  const curW = rptWealth(cur, ix, ticket);

  /* sweep: every size, both cap settings */
  const sweep = ladder.map(z => {
    const on = rptRun(ix, {pv: z.pv, comm: z.comm, fundedCapOn: true});
    const off = rptRun(ix, {pv: z.pv, comm: z.comm, fundedCapOn: false});
    return {z: z, on: on.summary, off: off.summary,
            onRes: on, offRes: off};
  });
  /* ranked by return on ticket spend: net dollars alone rewards whichever
     configuration simply churns the most accounts over the period, which is
     not the same as being the best use of a dollar */
  let best = sweep[0], bestKey = 'on';
  sweep.forEach(r => {
    ['on', 'off'].forEach(k => {
      if (r[k].spent > 0 && r[k].roi > best[bestKey].roi){ best = r; bestKey = k; }
    });
  });
  const bestRes = bestKey === 'on' ? best.onRes : best.offRes;
  const bestW = rptWealth(bestRes, ix, ticket);

  /* sensitivity to what a payout is actually worth, at the best size */
  const pvals = [];
  for (let v = 10; v <= 100; v += 10) pvals.push(v);
  const paySens = pvals.map(v => rptRun(ix, {
    pv: best.z.pv, comm: best.z.comm, fundedCapOn: bestKey === 'on', payoutSplit: v / 100
  }).summary);

  /* sensitivity to the ticket price */
  const tvals = [25, 50, 65, 80, 100, 125, 150, 200, 250];
  const tickSens = tvals.map(v => rptRun(ix, {
    pv: best.z.pv, comm: best.z.comm, fundedCapOn: bestKey === 'on', cost: v
  }).summary);

  /* lifecycle of the best configuration */
  const A = bestRes.accounts;
  const lifeTrades = A.map(a => a.trades), lifeDays = A.map(a => a.days);
  const peaks = A.map(a => a.peak - S.acct.balance);
  let worstDD = 0, peakW = -Infinity, under = 0, longestUnder = 0;
  for (let i = 0; i < bestW.length; i++){
    if (bestW[i] > peakW) peakW = bestW[i];
    const dd = peakW - bestW[i];
    if (dd > worstDD) worstDD = dd;
    if (bestW[i] < peakW - 1e-9){ under++; if (under > longestUnder) longestUnder = under; }
    else under = 0;
  }
  let minW = Infinity;
  for (let i = 0; i < bestW.length; i++) if (bestW[i] < minW) minW = bestW[i];

  const dates = [];
  for (let k = 0; k <= 5; k++){
    const i = Math.round((nS - 1) * k / 5);
    dates.push({i: i, t: (S0[i] && S0[i].day ? S0[i].day : '').slice(0, 7)});
  }

  const row = (a, b, note) => '<tr><td>' + a + '</td><td class="r">' + b + '</td>' +
    (note ? '<td class="n">' + note + '</td>' : '<td></td>') + '</tr>';
  const pct = (x, y) => y ? (100 * x / y).toFixed(1) + '%' : '\u2014';

  /* ---- the document ---- */
  let H = '<h1>Prop firm \u2014 full analysis</h1>' +
    '<p class="lede">Every figure below is recomputed from the <b>' +
    sep(TRADES.length) + ' trades currently loaded</b>, replayed across ' + sep(nS) +
    ' sessions. Nothing is pre-baked: change the settings in the panel and reopen this ' +
    'report and every number moves.</p>';

  /* the answer */
  H += '<h2>1 \u00b7 Where the money is</h2>' +
    '<div class="verdict ' + (best[bestKey].net >= 0 ? 'ok' : 'bad') + '">' +
    'Best of ' + (sweep.length * 2) + ' configurations: <b>' + esc(best.z.label) + '</b>, ' +
    'funded cap <b>' + (bestKey === 'on' ? 'on' : 'off') + '</b> \u2014 <b>' +
    (best[bestKey].roi * 100).toFixed(1) + '%</b> on ticket spend, net <b>' +
    money0(best[bestKey].net) + '</b></div>' +
    '<table class="t"><tbody>' +
    row('Tickets bought', sep(best[bestKey].accounts), money0(ticket) + ' each') +
    row('Spent on tickets', money0(-best[bestKey].spent), '') +
    row('Reached funded', sep(best[bestKey].passes),
        pct(best[bestKey].passes, best[bestKey].accounts) + ' of tickets') +
    row('Withdrawals taken', sep(best[bestKey].payouts),
        best[bestKey].drawsPerFunded.toFixed(2) + ' per funded account') +
    row('Received', money0(best[bestKey].won),
        money0(best[bestKey].payoutDraw) + ' \u00d7 ' +
        (best[bestKey].payoutSplit * 100).toFixed(0) + '% = ' +
        money0(best[bestKey].payoutValue) + ' each') +
    row('<b>Return on ticket spend</b>',
        '<b>' + (best[bestKey].roi * 100).toFixed(1) + '%</b>',
        'per dollar spent on evaluations, what came back') +
    row('Net per ticket bought', money0(best[bestKey].perTicket),
        'is one $' + Math.round(ticket) + ' evaluation worth buying, on average?') +
    row('Pass rate', (100 * best[bestKey].fundedRate).toFixed(1) + '%',
        'tickets that reached funded') +
    row('<b>NET</b>', '<b>' + money0(best[bestKey].net) + '</b>',
        'payouts received minus tickets bought') +
    row('Break-even payout value',
        best[bestKey].payouts ? money0(best[bestKey].spent / best[bestKey].payouts)
                              : 'never pays out',
        'what one payout must be worth to break even') +
    '</tbody></table>' +
    '<p class="dim">Your current settings (' + money0(S.acct.pointValue) +
    ' a point) produce <b>' + money0(cur.summary.net) + '</b> \u2014 ' +
    (Math.abs(cur.summary.net - best[bestKey].net) < 1
      ? 'which is the best available.'
      : money0(best[bestKey].net - cur.summary.net) + ' less than the best above.') + '</p>';

  /* wealth over time */
  H += '<h2>2 \u00b7 Wealth over time</h2>' +
    '<p>Cumulative payouts received minus every ticket bought, session by session. The ' +
    'amber line is the best configuration; the grey line is your current one. A ' +
    'strategy like this spends continuously and is paid in rare lumps, so the line ' +
    'should look like a slow bleed punctuated by steps.</p>' +
    '<div class="fig">' + rptLine(
      [{v: Array.from(curW), col: '#8e99ac', w: 1.4},
       {v: Array.from(bestW), col: '#d8a24a', w: 2.2}], dates, 960, 300) + '</div>' +
    '<table class="t"><tbody>' +
    row('Deepest hole before recovery', money0(-worstDD),
        'the most you would have been down from your own high-water mark') +
    row('Worst point overall', money0(minW), 'the most you were ever down in total') +
    row('Longest stretch below the high-water mark', sep(longestUnder) + ' sessions',
        (nS ? (100 * longestUnder / nS).toFixed(0) + '% of the period' : '')) +
    row('Capital you would have needed', money0(Math.max(0, -minW)),
        'to survive the ticket burn without running out of money') +
    '</tbody></table>';

  /* the sweep */
  H += '<h2>3 \u00b7 Every contract size</h2>' +
    '<p>The same trades at every size. Size is not a multiplier here: the drawdown and the ' +
    'daily cap are fixed dollar amounts, so a bigger contract does not simply earn more ' +
    '\u2014 it changes where trades are <i>closed</i>, because the account is liquidated ' +
    'sooner. That is why this is a curve with a peak rather than a straight line.</p>' +
    '<p class="dim">Bars show the net with the funded daily cap <b>' +
    (bestKey === 'on' ? 'on' : 'off') + '</b> \u2014 the setting that produced the best ' +
    'result. The table underneath gives both.</p>' +
    '<div class="fig">' + rptBars(sweep.map(r => ({
        label: r.z.label, v: r[bestKey].net,
        best: r === best})), 960, 20 * sweep.length) + '</div>' +
    '<table class="t"><thead><tr><th>Size</th><th class="r">$/point</th>' +
    '<th class="r">Tickets</th>' +
    '<th class="r">Pass rate</th><th class="r">Withdrawals</th><th class="r">Spent</th>' +
    '<th class="r">Received</th><th class="r">Net/ticket</th>' +
    '<th class="r">Return (cap on)</th><th class="r">Return (cap off)</th>' +
    '</tr></thead><tbody>' +
    sweep.map(r => '<tr' + (r === best ? ' class="hi"' : '') + '><td>' + esc(r.z.label) +
      '</td><td class="r">' + money0(r.z.pv) + '</td>' +
      '<td class="r">' + sep(r[bestKey].accounts) + '</td><td class="r">' +
      (100 * r[bestKey].fundedRate).toFixed(1) + '%</td><td class="r">' +
      sep(r[bestKey].payouts) +
      '</td><td class="r">' + money0(-r[bestKey].spent) + '</td><td class="r">' +
      money0(r[bestKey].won) + '</td><td class="r ' +
      (r[bestKey].perTicket >= 0 ? 'g' : 'b') + '">' + money0(r[bestKey].perTicket) +
      '</td><td class="r ' + (r.on.roi >= 0 ? 'g' : 'b') + '">' +
      (r.on.roi * 100).toFixed(0) + '%</td><td class="r ' +
      (r.off.roi >= 0 ? 'g' : 'b') + '">' + (r.off.roi * 100).toFixed(0) +
      '%</td></tr>').join('') +
    '</tbody></table>';

  /* the funnel */
  const f = best[bestKey];
  H += '<h2>4 \u00b7 Where the accounts go</h2>' +
    '<p>Of every hundred tickets bought, how many get funded, and of those how many are ' +
    'ever paid. This funnel is the whole business model \u2014 both for you and for the ' +
    'firm.</p>' +
    '<table class="t"><tbody>' +
    row('Tickets bought', sep(f.accounts), '100%') +
    row('\u2192 reached funded', sep(f.passes), pct(f.passes, f.accounts)) +
    row('\u2192 reached a payout', sep(f.payouts), pct(f.payouts, f.accounts) +
        ' of all tickets') +
    row('Busted', sep(f.fails), pct(f.fails, f.accounts)) +
    row('Forced liquidations', sep(f.forced),
        'closed by running out of equity, not by the stop') +
    row('Average life of a ticket', f.avgTradesPerAccount.toFixed(1) + ' trades',
        f.avgDaysPerAccount.toFixed(1) + ' sessions') +
    '</tbody></table>' +
    '<div class="g2"><div><h3>How long a ticket lasts</h3>' +
    '<p class="dim">Trades taken before it was funded, paid or busted.</p>' +
    '<div class="fig">' + rptHist(lifeTrades, 460, 170, 22, v => Math.round(v) + ' trades') +
    '</div></div><div><h3>How close accounts got</h3>' +
    '<p class="dim">Best balance each account ever reached, above the starting balance. ' +
    'If this distribution stops short of the payout line, the size cannot pay out at all ' +
    '\u2014 not unluckily, but structurally.</p>' +
    '<div class="fig">' + rptHist(peaks, 460, 170, 22, v => money0(v)) +
    '</div></div></div>';

  /* how many withdrawals one account is allowed */
  const caps = [1, 2, 3, 5, 10, 0];
  const capRuns = caps.map(m => ({m: m, s: rptRun(ix, {
    pv: best.z.pv, comm: best.z.comm, fundedCapOn: bestKey === 'on', maxDraws: m
  }).summary}));
  H += '<h2>5 \u00b7 How many withdrawals one account may take</h2>' +
    '<p>A withdrawal takes ' + money0(ev.payoutDraw) + ' out of the account, which then ' +
    'carries on from a lower balance <b>with the floor still frozen where it was</b> \u2014 ' +
    'so the second payout is earned from a thinner cushion than the first, the third from a ' +
    'thinner one again. If the firm caps withdrawals and then moves you to a live account, ' +
    'getting funded is worth at most that many payouts. This is what each cap does, at ' +
    esc(best.z.label) + '.</p>' +
    '<table class="t"><thead><tr><th>Limit per account</th><th class="r">Tickets</th>' +
    '<th class="r">Funded</th><th class="r">Withdrawals</th><th class="r">Graduated</th>' +
    '<th class="r">Received</th><th class="r">Net</th><th class="r">Return</th>' +
    '</tr></thead><tbody>' +
    capRuns.map(c => '<tr><td>' + (c.m === 0 ? 'no limit' : c.m + ' payout' +
        (c.m === 1 ? '' : 's')) + '</td><td class="r">' + sep(c.s.accounts) +
      '</td><td class="r">' + sep(c.s.passes) + '</td><td class="r">' + sep(c.s.payouts) +
      '</td><td class="r">' + sep(c.s.graduated || 0) + '</td><td class="r">' +
      money0(c.s.won) + '</td><td class="r ' + (c.s.net >= 0 ? 'g' : 'b') + '">' +
      money0(c.s.net) + '</td><td class="r ' + (c.s.roi >= 0 ? 'g' : 'b') + '">' +
      (c.s.roi * 100).toFixed(0) + '%</td></tr>').join('') +
    '</tbody></table>' +
    '<p class="dim">"Graduated" is an account that hit the limit and was passed to a live ' +
    'account \u2014 it stops being modelled here, so anything it might have earned after ' +
    'that is not counted.</p>';

  /* sensitivities */
  H += '<h2>6 \u00b7 What the answer depends on</h2>' +
    '<p>Two numbers you do not control decide almost everything. Both are shown across ' +
    'their plausible range at the best size, so you can see how much room for error ' +
    'there is.</p>' +
    '<div class="g2"><div><h3>The profit split</h3>' +
    '<div class="fig">' + rptLine([{v: paySens.map(x => x.net), col: '#d8a24a', w: 2}],
      pvals.map((v, i) => ({i: i, t: v + '%'})), 460, 210) +
    '</div><p class="dim">Left to right: you keep 10% of each withdrawal up to 100%. Yours ' +
    'is ' + (ev.payoutSplit * 100).toFixed(0) + '%, so each ' + money0(ev.payoutDraw) +
    ' withdrawal pays you ' + money0(ev.payoutDraw * ev.payoutSplit) + '. This scales every ' +
    'winning figure directly.</p></div>' +
    '<div><h3>What a ticket costs</h3>' +
    '<div class="fig">' + rptLine([{v: tickSens.map(x => x.net), col: '#6ea8dc', w: 2}],
      tvals.map((v, i) => ({i: i, t: '$' + v})), 460, 210) +
    '</div><p class="dim">Left to right: $25 to $250 a ticket. Yours is ' +
    money0(ticket) + '. Discounted tickets are the single cheapest way to improve ' +
    'this result.</p></div></div>';

  /* the honest part */
  H += '<h2>7 \u00b7 What this rests on</h2>' +
    '<p>This is one run of one trade list. It is not a forecast, and these are the ' +
    'reasons it might not survive contact with a real firm.</p>' +
    '<ul class="as">' +
    '<li><b>One realisation, not an average.</b> These are the exact trades loaded in the ' +
    'page. The Wealth panel runs the same rule 60 times with different random draws; ' +
    'expect this report to sit somewhere inside that spread, not on its median.</li>' +
    '<li><b>Unlimited tickets, instantly, with no scrutiny.</b> The best configuration ' +
    'above buys <b>' + sep(f.accounts) + '</b> accounts across ' + sep(nS) +
    ' sessions. A firm that declines to sell that many, or reviews withdrawals, removes ' +
    'the result entirely.</li>' +
    '<li><b>A payout is paid in full and immediately.</b> No delay, no split, no minimum ' +
    'trading days, no time limit on the evaluation.</li>' +
    '<li><b>The daily cap once funded is a guess.</b> It is a toggle above because the ' +
    'rules are not explicit, and column seven versus column eight of the size table shows ' +
    'how much it matters.</li>' +
    '<li><b>Ties inside a bar go against you.</b> Where one bar contains both the stop and ' +
    'the target, the stop is taken. Real intra-bar order is unknowable.</li>' +
    '<li><b>No tax, no funding delay, no slippage beyond the fixed amount set.</b></li>' +
    '</ul>';

  return H;
}

function openReport(){
  const body = buildReport();
  const CSS = 'body{margin:0;background:#0f1115;color:#dae0ea;font:15px/1.6 ' +
    '"IBM Plex Sans",-apple-system,"Segoe UI",sans-serif;padding:34px 40px 90px}' +
    '.rpt{max-width:1020px;margin:0 auto}' +
    'h1{font-size:27px;margin:0 0 6px;letter-spacing:-.01em}' +
    'h2{font-size:19px;margin:38px 0 6px;padding-top:14px;' +
    'border-top:1px solid #252b36;color:#d8a24a}' +
    'h3{font-size:14px;margin:14px 0 4px;color:#dae0ea}' +
    'p{max-width:74ch;color:#a9b3c3}.lede{font-size:16px}' +
    '.dim{color:#8e99ac;font-size:12.5px}' +
    'b{color:#dae0ea}' +
    '.verdict{font-family:"IBM Plex Mono",monospace;font-size:14px;padding:11px 14px;' +
    'border-radius:6px;margin:12px 0;border:1px solid}' +
    '.verdict.ok{background:rgba(75,176,115,.12);border-color:#4bb073;color:#7fd3a2}' +
    '.verdict.bad{background:rgba(209,86,90,.12);border-color:#d1565a;color:#e38f92}' +
    'table.t{width:100%;border-collapse:collapse;font-family:"IBM Plex Mono",monospace;' +
    'font-size:12px;margin:10px 0}' +
    '.t td,.t th{padding:5px 9px;border-bottom:1px solid #1e232c;text-align:left}' +
    '.t th{color:#8e99ac;font-weight:500;border-bottom:1px solid #252b36;font-size:11px}' +
    '.t td.r,.t th.r{text-align:right}.t td.n{color:#8e99ac;font-size:11px}' +
    '.t tr.hi{background:rgba(216,162,74,.10)}' +
    '.t .g{color:#4bb073}.t .b{color:#d1565a}' +
    '.fig{background:#161a21;border:1px solid #252b36;border-radius:7px;padding:10px;' +
    'margin:8px 0;overflow-x:auto}' +
    'svg{display:block;width:100%;height:auto}' +
    'svg .g{stroke:#1e232c}svg .z{stroke:#39414f}' +
    'svg .ax{fill:#8e99ac;font:9.5px "IBM Plex Mono",monospace}' +
    '.g2{display:grid;grid-template-columns:1fr 1fr;gap:22px}' +
    '@media(max-width:840px){.g2{grid-template-columns:1fr}}' +
    'ul.as{max-width:74ch;color:#a9b3c3}ul.as li{margin:7px 0}';
  const doc = '<!doctype html><html><head><meta charset="utf-8">' +
    '<meta name="viewport" content="width=device-width,initial-scale=1">' +
    '<title>Prop firm \u2014 full analysis</title>' +
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">' +
    '<style>' + CSS + '</style></head><body><div class="rpt">' + body +
    '</div></body></html>';
  let w = null;
  try { w = window.open('', '_blank'); } catch (e){ w = null; }
  if (w && w.document){
    w.document.open(); w.document.write(doc); w.document.close();
    return;
  }
  /* pop-ups blocked (an artifact runs in a sandboxed frame): show it here */
  let ov = document.getElementById('rptOverlay');
  if (!ov){
    ov = document.createElement('div');
    ov.id = 'rptOverlay';
    document.body.appendChild(ov);
  }
  ov.innerHTML = '<div class="rptbar"><b>Prop firm \u2014 full analysis</b>' +
    '<span>your browser blocked a new window, so it is shown here</span>' +
    '<button class="btn" id="rptClose">Close</button></div>' +
    '<div class="rptbody"><div class="rpt">' + body + '</div></div>';
  ov.classList.add('on');
  const c = document.getElementById('rptClose');
  if (c) c.onclick = () => ov.classList.remove('on');
}

/* ---------------- wealth trajectory ----------------
   The central question: with the downside capped at a $65 ticket and the upside
   a payout, does buying many evaluations with a ZERO-EDGE strategy make money?
   Each faint line is one independent run of the coin flips through the real
   bars; the bold line is the median. What separates the sizes is not skill --
   the strategy is identical -- but whether the account can physically reach the
   payout threshold at all before the drawdown ends it.                       */
/* ---------------- setups (tagging) ----------------
   The one feature every journal leads with and this had none of: label a trade
   with the setup it belongs to, then compare setups against each other. Tags
   live in localStorage keyed by the trade's entry bar, so they survive a reload
   and follow the trade rather than its row number -- reordering, filtering or
   re-running the strategy will not scramble them. */
const TAGDEF = [
  {id: 'a', name: 'A+ setup',   col: '#4bb073'},
  {id: 'b', name: 'B setup',    col: '#6ea8dc'},
  {id: 'c', name: 'Marginal',   col: '#d4a95e'},
  {id: 'x', name: 'Mistake',    col: '#d1565a'},
  {id: 'n', name: 'News',       col: '#c98ad4'}
];
let TAGS = {};
try { TAGS = JSON.parse(localStorage.getItem('tape.tags') || '{}'); } catch(e){}
function saveTags(){ try { localStorage.setItem('tape.tags', JSON.stringify(TAGS)); } catch(e){} }
function tagKey(i){ const t = TRADES[i]; return t ? String(t.entry_bar) : null; }
function tagOf(i){ const k = tagKey(i); return k === null ? null : (TAGS[k] || null); }
function setTag(i, id){
  const k = tagKey(i); if (k === null) return;
  if (!id || TAGS[k] === id) delete TAGS[k]; else TAGS[k] = id;
  saveTags(); lastSig = ''; render();
}
function tagDef(id){ for (const d of TAGDEF) if (d.id === id) return d; return null; }

const SESSIONS = (WEALTH && WEALTH.sessions) || 824;
const WL = {size: '1 NQ', cap: 'nocap', info: false};
function wlKey(){ return WL.size + '|' + WL.cap; }
function wlRun(){ return WEALTH.runs[wlKey()]; }

function wlCurves(){
  const r = wlRun(), D = WEALTH.dates;
  /* The stored curves are every 4th session, so their last point is a few
     sessions short of the end and disagreed with the Net row by up to $2,035.
     Close each one on the run's actual net. */
  const CV = r.curves.map((c, k) => c.concat([r.nets[k]]));
  const DX = D.concat([D[D.length - 1]]);
  const Wd = 700, Ht = 300, PADL = 74, PADR = 16, PADT = 14, PADB = 30;
  const pw = Wd - PADL - PADR, ph = Ht - PADT - PADB;
  let lo = Infinity, hi = -Infinity;
  CV.forEach(c => c.forEach(v => { if (v < lo) lo = v; if (v > hi) hi = v; }));
  lo = Math.min(lo, 0); hi = Math.max(hi, 0);
  const pad = (hi - lo) * 0.08 || 1; lo -= pad; hi += pad;
  const n = CV[0].length;
  const X = i => PADL + pw * i / (n - 1);
  const Y = v => PADT + ph * (1 - (v - lo) / (hi - lo));
  let out = '<svg viewBox="0 0 ' + Wd + ' ' + Ht + '" role="img">';
  for (let t = 0; t <= 4; t++){
    const v = lo + (hi - lo) * t / 4, y = Y(v);
    out += '<line x1="' + PADL + '" y1="' + y + '" x2="' + (Wd - PADR) + '" y2="' + y +
           '" stroke="' + cv_('--rule-soft') + '"/>' +
           '<text x="' + (PADL - 7) + '" y="' + (y + 3) + '" fill="' + cv_('--ink-faint') +
           '" font-size="9" font-family="' + cv_('--mono') + '" text-anchor="end">' +
           money0(v) + '</text>';
  }
  out += '<line x1="' + PADL + '" y1="' + Y(0) + '" x2="' + (Wd - PADR) + '" y2="' + Y(0) +
         '" stroke="' + cv_('--rule') + '" stroke-width="1.4"/>';
  /* every run, faint */
  CV.forEach(c => {
    let d = '';
    c.forEach((v, i) => { d += (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1) + ' '; });
    out += '<path d="' + d + '" fill="none" stroke="' +
           (c[c.length - 1] >= 0 ? S.col.up : S.col.down) + '" stroke-width="0.8" opacity="0.22"/>';
  });
  /* the median run at each point, bold */
  let med = '';
  for (let i = 0; i < n; i++){
    const col = CV.map(c => c[i]);
    const v = medOf(col);
    med += (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1) + ' ';
  }
  out += '<path d="' + med + '" fill="none" stroke="' + S.col.accent + '" stroke-width="2.2"/>';
  for (let t = 0; t <= 5; t++){
    const i = Math.round((n - 1) * t / 5);
    out += '<text x="' + X(i) + '" y="' + (Ht - 8) + '" fill="' + cv_('--ink-faint') +
           '" font-size="9" font-family="' + cv_('--mono') + '" text-anchor="middle">' +
           (DX[i] || '').slice(0, 7) + '</text>';
  }
  return out + '</svg>';
}

function wlHist(){
  const r = wlRun(), Wd = 700, Ht = 150, PADL = 74, PADR = 16, PADT = 12, PADB = 26;
  const pw = Wd - PADL - PADR, ph = Ht - PADT - PADB;
  const v = r.nets.slice().sort((a, b) => a - b);
  const lo = Math.min(v[0], 0), hi = Math.max(v[v.length - 1], 0);
  const nb = 18, w = (hi - lo) / nb || 1;
  const bins = new Array(nb).fill(0);
  v.forEach(x => bins[Math.min(nb - 1, Math.floor((x - lo) / w))]++);
  const mx = Math.max.apply(null, bins) || 1;
  const X = x => PADL + pw * (x - lo) / (hi - lo);
  let out = '<svg viewBox="0 0 ' + Wd + ' ' + Ht + '" role="img">';
  bins.forEach((c, i) => {
    if (!c) return;
    const x0 = X(lo + i * w), x1 = X(lo + (i + 1) * w);
    const h = ph * c / mx;
    out += '<rect x="' + x0 + '" y="' + (PADT + ph - h) + '" width="' + Math.max(1, x1 - x0 - 1) +
           '" height="' + h + '" fill="' + (lo + (i + 0.5) * w >= 0 ? S.col.up : S.col.down) +
           '" opacity="0.75"/>';
  });
  if (lo < 0 && hi > 0)
    out += '<line x1="' + X(0) + '" y1="' + PADT + '" x2="' + X(0) + '" y2="' + (PADT + ph) +
           '" stroke="' + cv_('--ink') + '" stroke-width="1.4"/>';
  for (let t = 0; t <= 4; t++){
    const x = lo + (hi - lo) * t / 4;
    out += '<text x="' + X(x) + '" y="' + (Ht - 8) + '" fill="' + cv_('--ink-faint') +
           '" font-size="9" font-family="' + cv_('--mono') + '" text-anchor="middle">' +
           money(x) + '</text>';
  }
  return out + '</svg>';
}


/* The comparison the question is actually about: the same size under both cap
   settings, side by side, with the live selection highlighted. Every row
   carries the assumption it depends on as a hover. */
function cmpTable(){
  const A = WEALTH.runs[WL.size + '|nocap'], B = WEALTH.runs[WL.size + '|cap'];
  if (!A || !B) return '<p style="color:var(--ink-faint)">No data for this size.</p>';
  const med = medOf;
  const wins = r => r.nets.filter(x => x > 0).length;
  const sgn = v => (v > 0 ? '+' : '') + money0(v);
  const on = WL.cap === 'cap' ? 2 : 1;
  const rows = [
    ['Evaluations bought', r => cntCell(med(r.evals), r.seeds), 0,
     'Median count of $65 tickets bought over the 824 sessions. Assumes the firm will sell '
     + 'you an unlimited number, one after another, with no review.'],
    ['Spent on tickets', r => money0(-med(r.spent)), 0,
     'Every ticket bought, at $65 each, including the one you are holding at the end. This is '
     + 'the entire downside \u2014 it is what makes the bet capped.'],
    ['Payouts reached', r => cntCell(med(r.payouts), r.seeds), 0,
     'Times a funded account reached $27,100 and withdrew $1,000. The account carries on from '
     + '$26,100, so one account can be paid several times. Any single run reaches it a whole '
     + 'number of times; the median of an even number of runs can still land between two of '
     + 'them, and is shown rounded with the exact value on hover.'],
    ['Won from payouts', r => money0(med(r.won)), 0,
     'The median run\u2019s takings: its payouts \u00d7 $900, the $1,000 withdrawn at the 90% '
     + 'split. Assumes every withdrawal is actually paid. Each row is its own median, so this '
     + 'is not the row above \u00d7 $900.'],
    ['Net', r => sgn(med(r.nets)), 1,
     'The median of each run\u2019s own won-minus-spent \u2014 the answer to the question. It '
     + 'is not the Won row minus the Spent row: every row is taken as its own median across the '
     + 'runs, and medians do not subtract.'],
    ['Runs that made money', r => wins(r) + ' of ' + r.seeds, 0,
     'How many of the independent coin-flip runs finished above zero. The median tells you the '
     + 'typical run; this tells you how often it happens at all.'],
    ['Break-even payout value', r => med(r.payouts)
        ? money0(med(r.spent) / med(r.payouts)) : 'never pays out', 0,
     'Median spend divided by median payouts, using the exact medians rather than the rounded '
     + 'counts shown. What one payout would have to be worth to break even \u2014 compare it '
     + 'against the $900 actually paid; the gap is the margin of safety.']
  ];
  return '<table class="cmp">' +
    '<colgroup><col><col class="' + (on === 1 ? 'on' : '') + '">' +
    '<col class="' + (on === 2 ? 'on' : '') + '"></colgroup>' +
    '<thead><tr><th></th><th class="' + (on === 1 ? 'on' : '') + '">No funded cap</th>' +
    '<th class="' + (on === 2 ? 'on' : '') + '">$625 funded cap</th></tr></thead><tbody>' +
    rows.map(x => '<tr' + (x[2] ? ' class="big"' : '') + '><td><span class="why" title="' +
      esc(x[3]) + '">' + x[0] + '</span></td><td>' + x[1](A) + '</td><td>' + x[1](B) +
      '</td></tr>').join('') +
    '</tbody></table>' +
    '<p style="color:var(--ink-faint);font-size:10.5px;margin-top:6px"><b>Every row is its ' +
    'own median across the ' + A.seeds + ' runs, so the rows do not add up.</b> The run with ' +
    'the median net is not the run with the median spend, and with an even number of runs the ' +
    'median falls between two of them. Read each row as the typical value of that quantity, ' +
    'never as arithmetic on the rows above it.</p>';
}

/* "explain all the hidden assumptions the code contains from start to finish"
   -- grouped in the order the model actually applies them, each tagged with
   which way it bends the answer. */
const ASSUMPTIONS = [
 ['The data', [
  ['Real NQ 1-minute bars, Jan 2023 \u2013 2026: <b>824 sessions, 315,900 bars</b>. Prices are '
   + 'never simulated or resampled \u2014 the run walks the actual tape in order.', 'neu'],
  ['Regular session only, <b>09:30\u201316:00 ET</b>. No overnight or Globex trading, so gap '
   + 'risk across the close never touches the account.', 'con'],
  ['A bar gives open, high, low and close but <b>not the path between them</b>. When a bar '
   + 'contains both the target and the stop, the model takes <b>the stop</b>. Real intrabar '
   + 'order is unknowable, so ties are always resolved against you.', 'con']]],
 ['The strategy', [
  ['A coin flip at <b>10:00 ET, re-entering every 30 minutes</b> to 15:30 \u2014 twelve slots a '
   + 'session. Direction is the only random element.', 'neu'],
  ['The flip is genuinely fair: <b>2,334 longs against 2,336 shorts</b> measured, lag-1 '
   + 'autocorrelation +0.017. There is <b>no edge hiding in the entries</b> \u2014 that is the '
   + 'whole point of the test.', 'neu'],
  ['Fixed <b>50-point stop, 1:1 target</b>. Both are cut down when the account cannot afford '
   + 'the full distance, which is what makes small accounts behave differently from large ones.',
   'neu'],
  ['One position at a time. A slot is skipped if the previous trade is still open, and anything '
   + 'open at 16:00 is <b>closed at the close</b>.', 'neu']]],
 ['Execution and costs', [
  ['<b>0.25 points of slippage per side</b>, charged on entry and on exit.', 'neu'],
  ['Commission <b>$1.50 per side for 1 NQ</b>, $0.75 for 1 MNQ \u2014 $3.00 and $1.50 round '
   + 'turn. Both are charged on every trade.', 'neu'],
  ['A fill is <b>always available</b> at the stop or target once the bar trades through it. No '
   + 'gapping past a stop, no partial fills, no rejected orders.', 'opt'],
  ['Liquidation is <b>cost-aware</b>: the forced exit is priced so the account lands exactly on '
   + 'the floor after slippage and commission, never below it.', 'neu']]],
 ['The firm\u2019s rules', [
  ['<b>$25,000</b> start, with a <b>$1,000 trailing drawdown measured end of day</b>. The '
   + 'floor stops ratcheting once <b>the floor itself reaches $25,100</b> \u2014 which happens '
   + 'when the balance reaches $26,100, not $25,100 \u2014 locking in $100 above the start.',
   'neu'],
  ['Evaluation passes at <b>+$1,250</b>. Daily profit is capped at <b>$625</b> (the 50% '
   + 'consistency rule), and the account stops trading for the day once it is hit.', 'neu'],
  ['Funded accounts carry the <b>same trailing drawdown</b>, and a payout is reached at '
   + '<b>$27,100</b>. Whether the $625 cap still applies once funded is the toggle above \u2014 '
   + 'it was never confirmed, so both answers are shown.', 'neu'],
  ['Equity is tracked <b>unrealised</b>. The account is force-closed the moment live equity '
   + 'touches the floor, even with the stop still far away.', 'con']]],
 ['Payout accounting', [
  ['A payout is a <b>$1,000 withdrawal at a 90% split</b>, so $900 reaches you. The balance '
   + 'drops to $26,100 and the floor stays where it froze, so the next payout is earned from a '
   + 'thinner cushion than the first.', 'neu'],
  ['The account <b>carries on</b> after a payout and may withdraw again each time it is back at '
   + '$27,100, with no limit on the count. A firm that caps withdrawals, or moves the account to '
   + 'live capital after a few, cuts off that tail.', 'opt'],
  ['Tickets are <b>$65, unlimited, instant</b>, with no discount, no queue and no scrutiny. The '
   + 'median run buys <b>hundreds of accounts</b> across the period; the exact pace for the '
   + 'size on screen is in the note above.', 'opt'],
  ['No taxes, no funding delays, no minimum trading days, no time limit on the evaluation.',
   'opt']]],
 ['The statistics', [
  ['<b>60 independent runs</b> per setting, each a different seed through the same real bars. '
   + 'One path of a random strategy is an anecdote; the question asked about the average.',
   'neu'],
  ['Figures are <b>medians, not means</b>. The distribution is skewed by rare very good runs, '
   + 'so the mean flatters it \u2014 the median is the typical outcome.', 'con'],
  ['824 sessions is a little over three years, and one market regime. The result is <b>not a '
   + 'forecast</b>; it is what this rule set did on this tape.', 'neu']]]
];

function assumptionsHTML(){
  return '<div class="asmp">' + ASSUMPTIONS.map(g =>
    '<h4>' + g[0] + '</h4><ol>' + g[1].map(a =>
      '<li>' + a[0] + '<span class="bias ' + a[1] + '">' +
      (a[1] === 'opt' ? 'flatters it' : a[1] === 'con' ? 'conservative' : 'neutral') +
      '</span></li>').join('') + '</ol>').join('') +
    '<p style="margin-top:12px;color:var(--ink-dim);font-size:11.5px">Read the red tags first. '
    + 'The result survives the conservative ones comfortably; it depends entirely on the '
    + 'optimistic ones. <b>Unlimited $65 tickets and unlimited withdrawals are what carry '
    + 'it</b> \u2014 remove either and the arithmetic changes shape.</p></div>';
}

function wealthHTML(){
  const r = wlRun();
  const med = medOf;
  const mean = a => a.reduce((x, y) => x + y, 0) / a.length;
  const wins = r.nets.filter(x => x > 0).length;
  /* the smallest and largest size under the same cap setting, for the closing
     sentence: it must follow the data, not a number typed in from an old run */
  const small = WEALTH.runs[WEALTH.sizes[0] + '|' + WL.cap];
  const large = WEALTH.runs[WEALTH.sizes[WEALTH.sizes.length - 1] + '|' + WL.cap];
  const never = small.payouts.filter(v => v === 0).length;
  return '<h2>Does a zero-edge strategy pay?</h2>' +
    '<p>Buy an evaluation for <b>$' + 65 + '</b>. Trade it with a strategy that has <b>no edge ' +
    'at all</b> \u2014 a coin flip every 30 minutes from 10:00. Lose it and buy another. The ' +
    'downside is the ticket; the upside is a payout. Does that pay on average?</p>' +
    '<p style="color:var(--ink-dim);font-size:11.5px">Every line below is one independent run of ' +
    'the coin flips through the <b>real NQ bars</b>, 2023-2026. Nothing about the price is ' +
    'simulated; only the entry direction is random, which is why one path is not an answer and ' +
    r.seeds + ' are.</p>' +
    '<div class="szbar"><span class="lbl">Size</span>' +
    WEALTH.sizes.map(z => '<button class="btn' + (WL.size === z ? ' on' : '') +
      '" data-wz="' + esc(z) + '">' + esc(z) + '</button>').join('') +
    '<span class="lbl" style="margin-left:12px">Funded daily cap</span>' +
    '<button class="btn' + (WL.cap === 'nocap' ? ' on' : '') + '" data-wc="nocap">None</button>' +
    '<button class="btn' + (WL.cap === 'cap' ? ' on' : '') + '" data-wc="cap">$625</button></div>' +
    '<div class="verdict ' + (mean(r.nets) >= 0 ? 'pass' : 'fail') + '">' +
    (mean(r.nets) >= 0 ? 'PROFITABLE ON AVERAGE' : 'LOSES MONEY ON AVERAGE') +
    '  \u00b7  median ' + money0(med(r.nets)) + '  \u00b7  ' + wins + ' of ' + r.seeds +
    ' runs made money</div>' +
    '<div class="szfig"><h4>Wealth over time</h4>' +
    '<p>Cumulative payouts banked minus every ticket bought. Faint lines are the ' + r.seeds +
    ' runs; the amber line is the median across them.</p>' + wlCurves() + '</div>' +
    '<div class="szgrid"><div class="szfig"><h4>Where the runs finish</h4>' +
    '<p>Distribution of final wealth across all ' + r.seeds + ' runs.</p>' + wlHist() + '</div>' +
    '<div class="szfig"><h4>The arithmetic \u2014 ' + esc(WL.size) + '</h4>' +
    '<p>Median across ' + r.seeds + ' runs, both cap settings. Hover any row for what it ' +
    'rests on.</p>' + cmpTable() + '</div></div>' +
    '<p style="margin-top:10px"><b>What decides it is size, not skill.</b> The strategy is ' +
    'identical at every setting above. What changes is how often the account reaches the ' +
    '$27,100 a payout needs before the $1,000 trailing drawdown ends it. At ' + esc(small.size) +
    ', ' + never + ' of ' + small.seeds + ' runs were never paid and the median run was paid ' +
    cnt(med(small.payouts)) + (med(small.payouts) === 1 ? ' time' : ' times') + '; at ' +
    esc(large.size) + ' the median run was paid ' + cnt(med(large.payouts)) + ' times.</p>' +
    '<div class="note warn" style="margin-top:10px"><b>What this rests on.</b> Unlimited ' +
    'evaluations at $65 with no scrutiny, and every $1,000 withdrawal paid at the 90% split, ' +
    money0(r.pv) + ' each, for as long as the account keeps earning them. The median run here ' +
    'buys <b>' + cnt(med(r.evals)) + '</b> accounts over ' + SESSIONS + ' sessions \u2014 ' +
    pace(med(r.evals), SESSIONS) + '. A firm that reviews withdrawals, or that ' +
    'declines to sell that many tickets, removes the result entirely.</div>' +
    '<div style="margin-top:12px;display:flex;gap:6px">' +
    '<button class="btn" id="wlClose">Close</button>' +
    '<button class="btn' + (WL.info ? ' on' : '') + '" id="wlInfo">' +
    (WL.info ? '\u25be Hide the assumptions' : '\u25b8 More info \u2014 what this assumes') +
    '</button></div>' +
    (WL.info ? assumptionsHTML() : '');
}
function openWealth(){
  const sh = document.getElementById('sheet');
  sh.classList.add('sz');
  sh.innerHTML = wealthHTML();
  openSheet();
  bindWealth();
}
function bindWealth(){
  const sh = document.getElementById('sheet');
  const redraw = () => { sh.innerHTML = wealthHTML(); bindWealth(); };
  const inf = document.getElementById('wlInfo');
  /* redraw() rather than openWealth(): re-opening reset the sheet's scroll, so
     the assumptions the reader just asked for appeared off-screen below */
  if (inf) inf.onclick = () => {
    WL.info = !WL.info; redraw();
    const b = document.getElementById('wlInfo');
    if (b && b.scrollIntoView) b.scrollIntoView({block: 'nearest'});
  };
  sh.querySelectorAll('button[data-wz]').forEach(b => b.onclick = () => { WL.size = b.dataset.wz; redraw(); });
  sh.querySelectorAll('button[data-wc]').forEach(b => b.onclick = () => { WL.cap = b.dataset.wc; redraw(); });
  const c = document.getElementById('wlClose');
  if (c) c.onclick = () => {
    WL.info = false;            /* otherwise the panel reopens expanded */
    document.getElementById('modal').classList.remove('on');
    sh.classList.remove('sz');
  };
}
guard('bwealth', openWealth, 'Wealth');

/* ---------------- strategy runner ----------------
   The piece that was missing: choose a strategy, give it a balance and the
   firm's rules, and it REGENERATES every trade from the loaded bars. It does
   not re-price an existing trade list, because it cannot: the daily cap and
   the drawdown are fixed in dollars, so changing size changes where each trade
   EXITS. Generating and accounting have to happen together, and Core.runStrategy
   does exactly that in one pass.                                            */
/* Each note states the ENTRY rule only: when a trade is placed and how its
   direction is chosen. The exits and the account rules are the same for all
   four and are spelled out once in the panel, under the buttons. */
/* Four things a live recompute cannot resolve on its own, common to both
   live Breakout entries; kept in one place so they read the same way twice
   rather than drifting. None of these are new to the live entries -- every
   strategy on any market shares the first, third and fourth -- but ADX and
   Highest(C,N) are unusually exposed to a single bad bar, so they are
   spelled out here rather than left to the general Instrument-row hint. */
const LIVE_BO_CAVEATS =
  ' <b>What this cannot check for you:</b> it assumes the loaded bars are a ' +
  'roll-adjusted continuous series \u2014 one unadjusted contract roll can read as ' +
  'a giant breakout and a giant stop-out on the same day. Its 30-minute bars are ' +
  'built by counting 30 rows of whatever is loaded, not by the clock, so a gap ' +
  'in the 1-minute data quietly shifts every later bar off true half-hour ' +
  'boundaries. A single 1-minute bar that both fills the stop order and swings ' +
  'hard cannot be split into before-the-fill and after-the-fill from OHLC alone; ' +
  'the ledger\'s rule (adverse wins a tie) is the conservative reading, not a fact ' +
  'about what happened. And the Instrument row only sets $ per point, commission ' +
  'and slippage \u2014 it does not check that the bars you loaded are actually that ' +
  'market, so a NQ tape priced as ES runs without complaint; match them yourself. ' +
  'With RTH off you gain the pre-market bars ADX wants, but sessions are still ' +
  'grouped by calendar day here, not the exchange\'s own overnight trading ' +
  'session, so a day\'s worth of account rules and this rule\'s \u201cone entry a ' +
  'day\u201d can span the wrong hours \u2014 it is not simply closer to how this was studied.';
const STRATS = {
  reentry:  {label: '10:00 to 16:00, coin every 30 minute periods as long as trade is not opened.',
             mode: 'reentry', direction: 'random',
             note: '<b>Entry:</b> every 30 minutes from 10:00 to 15:30 (10:00, 10:30, ' +
                   '\u2026 15:30). At each of those minutes, if no trade is open, a coin is ' +
                   'flipped: heads buys, tails sells, at the open of that minute. Up to 12 ' +
                   'trades a day. No signal at all, by design: it measures what the account ' +
                   'rules are worth on their own. This is what the supplied CSV contains.'},
  reentry1: {label: '10:00 to 16:00, coin every 60 minute periods as long as trade is not opened.',
             mode: 'reentry', direction: 'random', slotMin: 60,
             note: '<b>Entry:</b> the same coin flip, but only at 10:00, 11:00, \u2026 15:00. ' +
                   'Up to 6 trades a day, so less commission but fewer chances in a day.'},
  orb:      {label: 'Zarattini\u2019s ORB at 09:56', mode: 'orb', direction: 'orb',
             note: '<b>Entry:</b> one trade a day at 9:56, 26 minutes after the 9:30 open. ' +
                   'Buys if the 9:55 close is above the day\u2019s opening price, sells if ' +
                   'below \u2014 the direction the first 26 minutes broke. No randomness, so ' +
                   'the seed does nothing and there is one path, not a distribution.'},
  lh5:      {label: '15:05 entry in unison with 5-min candle, close at 15:49', mode: 'window', direction: 'window',
             winMin: 900, winBars: 5, exitMin: 949,
             note: '<b>Entry:</b> one trade a day. Read the candle from 15:00 to 15:04: if it ' +
                   'closed up, buy at the 15:05 open; if down, sell; if flat, no trade. Out at ' +
                   'the 15:49 close unless the stop or target is hit first (set Flat by to 16:00 ' +
                   'to hold to the close). The 15:49 exit is deliberate: the exchanges publish ' +
                   'closing-auction imbalances at 15:50 and the last ten minutes belong to those ' +
                   'orders. <b>Tested:</b> ' + LH5.edge.sentence + ' <a href="../lh5/" target="_blank" rel="noopener">The write-up</a>.'},
  lh5coin:  {label: '15:05 coin flip entry, close at 15:49', mode: 'reentry', direction: 'random',
             startMin: 905, endMin: 905, exitMin: 949,
             note: '<b>Entry:</b> one trade a day at the 15:05 open, heads buys and tails ' +
                   'sells, out at 15:49. The control for the last-hour candle: same bar, same ' +
                   'exit, same stop and target, no signal. What the candle rule is measured ' +
                   'against.'},
  long1505: {label: '15:05 long entry, close at 15:49', mode: 'reentry', direction: 'long',
             startMin: 905, endMin: 905, exitMin: 949,
             note: '<b>Entry:</b> buy at the 15:05 open every day, out at 15:49. The drift ' +
                   'baseline: what a rising market hands to anyone who is simply long into ' +
                   'the last hour. No randomness, so the seed does nothing.'},
  lh5rf:    {label: 'Candle, forest-filtered', mode: 'window', direction: 'table', sides: 'f50',
             winMin: 900, winBars: 5, exitMin: 949, markets: ['NQ'],
             note: '<b>Entry:</b> the last-hour candle rule, but only on the days a random ' +
                   'forest (46 inputs known by 15:04: the candle, the day so far, the morning, ' +
                   'the gap, the regime, VIX, ES/RTY/CL/GC, rates, positioning, the calendar) ' +
                   'gave the trade better than even odds. <b>The forest does not run here:</b> ' +
                   'the page replays decisions it made out of sample, each month\'s from a ' +
                   'model fitted only on the months before it, from ' + LH5.rf.firstMonth + '. ' +
                   'Days before that stand aside. <b>Tested:</b> ' + LH5.rf.sentence},
  lh5rfdir: {label: 'Forest picks the side', mode: 'reentry', direction: 'table', sides: 'dir',
             startMin: 905, endMin: 905, exitMin: 949, markets: ['NQ'],
             note: '<b>Entry:</b> at 15:05 the same forest predicts whether price will be ' +
                   'higher at 15:49; long above 55%, short below 45%, stand aside in between. ' +
                   'Out at 15:49. Replayed out-of-sample decisions from ' + LH5.rf.firstMonth +
                   '; earlier days stand aside. <b>Tested:</b> ' + LH5.rf.dirSentence},
  rf2:      {label: 'Forest, 30-minute trades', mode: 'reentry', direction: 'table', sides: 'rf2',
             holdMin: 30, markets: ['NQ'],
             note: '<b>The answer first:</b> ' + RF2.plain + ' <b>Entry:</b> every 30 minutes from 10:00 to 15:30 a random forest says long, ' +
                   'short or stand aside for the next 30 minutes: long when it puts the odds of a ' +
                   'rise above 52%, short below 48%. Its ' + RF2.nFactors + ' inputs are known at ' +
                   'the decision minute: the last bars, the day so far, the regime, VIX, what ' +
                   'ES/RTY/CL/GC have done, rates, positioning, the calendar and a set of technical ' +
                   'indicators. Out at the close of the 30th minute unless the stop or target is hit ' +
                   'first. <b>The forest does not run here:</b> the page replays decisions it made ' +
                   'out of sample, each month\'s from a model fitted only on the months before it ' +
                   '(training from 2017-07), on every day of this tape. <b>Tested:</b> ' + RF2.sentence +
                   ' <a href="../rf2/" target="_blank" rel="noopener">The write-up</a>.'},
  coin30:   {label: '10:00 to 16:00, coin every 30 minute periods', mode: 'reentry', direction: 'random', holdMin: 30,
             note: '<b>Entry:</b> the 10:00 re-entry coin, but every trade is closed at the end of ' +
                   'its own 30 minutes, so up to 12 trades a day are taken whatever happens. The ' +
                   'control for the forest: same slots, same exit, same stop and target, no signal.'},
  orbrand:  {label: '09:56 coin-flip entry', mode: 'orb', direction: 'random',
             note: '<b>Entry:</b> one trade a day at 9:56, the same minute as the breakout, ' +
                   'but heads buys and tails sells. The control for the breakout: same ' +
                   'time, same exits, no signal. Note it passes less often than the ' +
                   're-entry coin flips at the same settings \u2014 not because the coin is ' +
                   'worse, but because one trade a day meets the drawdown ratchet and the ' +
                   'daily cap after every single trade, where a re-entry day can lose and ' +
                   'recover before the floor is reassessed.'},
  bo_ti4:   {label: 'Breakout: Trend indi 2, f=4', mode: 'reentry', direction: 'table', sides: 'bo:ti4',
             slotsFromTable: true, exitMin: 1019, noTarget: true, markets: ['NQ', 'ES', 'YM'],
             note: '<b>Entry:</b> Breakout Trading Academy\'s "Trend indi 2" on 30-minute bars of the full ' +
                   'session, fraction 4. At each 30-minute close between 09:00 and 15:30 New York a buy stop goes in ' +
                   'at that bar\'s open plus 4 times its open-to-low distance (a sell stop at the open minus it), ' +
                   'if the close is still on the near side of it; longs need DMI(100) twenty bars earlier below 35, ' +
                   'shorts above 35 (which almost never happens). One entry a day, filled at the level the minute ' +
                   'price reaches it.' + ' <b>Exit:</b> the 16:59 close (the CME session close at 16:00 Chicago), the stop, or the account. No profit target: the daily cap is the only ceiling. <b>Tape:</b> the entries are the fills this system took on the databento 1-minute file for the market picked in the Instrument row (NQ for the micros), 2010-2026, replayed here; a fill before 09:30 or after the tape ends is simply not on the tape. Load the databento file with RTH off for the exact rules. <a href="../breakout/" target="_blank" rel="noopener">The write-up</a>.'},
  bo_hit41: {label: 'Breakout: Hitter, N=41', mode: 'reentry', direction: 'table', sides: 'bo:hit41',
             slotsFromTable: true, exitMin: 1019, noTarget: true, markets: ['NQ', 'ES', 'YM'],
             note: '<b>Entry:</b> the "NASDAQ Hitter" with a 41-bar lookback, the best of its neighbours. At each ' +
                   '30-minute close between 09:00 and 15:30 New York, if ADX(50) on the full-session 30-minute bars ' +
                   'is below 17.5, a buy stop goes in at the highest close of the last 41 bars. Long only, one entry ' +
                   'a day, filled at the level the minute price reaches it.' + ' <b>Exit:</b> the 16:59 close (the CME session close at 16:00 Chicago), the stop, or the account. No profit target: the daily cap is the only ceiling. <b>Tape:</b> the entries are the fills this system took on the databento 1-minute file for the market picked in the Instrument row (NQ for the micros), 2010-2026, replayed here; a fill before 09:30 or after the tape ends is simply not on the tape. Load the databento file with RTH off for the exact rules. <a href="../breakout/" target="_blank" rel="noopener">The write-up</a>.'},
  bo_hit34: {label: 'Breakout: Hitter, N=34 as published', mode: 'reentry', direction: 'table', sides: 'bo:hit34',
             slotsFromTable: true, exitMin: 1019, noTarget: true, markets: ['NQ', 'ES', 'YM'],
             note: '<b>Entry:</b> the "NASDAQ Hitter" exactly as its EasyLanguage reads: Highest(C, 34), ' +
                   'ADX(50) < 17.5, Time 800-1500 Chicago, one entry a day, SetStopLoss(1000), SetExitOnClose. ' +
                   'The reference the other two are measured against.' + ' <b>Exit:</b> the 16:59 close (the CME session close at 16:00 Chicago), the stop, or the account. No profit target: the daily cap is the only ceiling. <b>Tape:</b> the entries are the fills this system took on the databento 1-minute file for the market picked in the Instrument row (NQ for the micros), 2010-2026, replayed here; a fill before 09:30 or after the tape ends is simply not on the tape. Load the databento file with RTH off for the exact rules. <a href="../breakout/" target="_blank" rel="noopener">The write-up</a>.'},
  bo_live_hit: {label: 'Breakout: Hitter, live (tunable)', mode: 'reentry', direction: 'table',
             slotsFromTable: true, noTarget: true, live: 'hitter', exitMin: 1019,
             note: '<b>Entry:</b> Highest(C, N) of the last N 30-minute closes sets a buy-stop ' +
                   '(or Lowest(C, N) sells, pick the side below), one entry a day, only on signal ' +
                   'bars between 09:00 and 15:30 New York where ADX(period) is below (or above) the ' +
                   'threshold below \u2014 same rule as the Hitter replay, but N, the ADX period, its ' +
                   'threshold and direction are computed fresh, live, on whichever bars you loaded, ' +
                   'instead of read from a table. The published NASDAQ Hitter is N=34; this defaults ' +
                   'to that. N=41 (its own replay is in the group above) was a better-performing ' +
                   'neighbour the later sweep found, not the published figure \u2014 type 41 here to ' +
                   'try it live. Trades one side at a time; the published system is long only.' +
                   ' <b>Exit:</b> the 16:59 New York close, the stop, or the account; no profit ' +
                   'target, the daily cap is the only ceiling.' + LIVE_BO_CAVEATS},
  bo_live_ti: {label: 'Breakout: Trend indi 2, live (tunable)', mode: 'reentry', direction: 'table',
             slotsFromTable: true, noTarget: true, live: 'trendindi', exitMin: 1019,
             note: '<b>Entry:</b> a buy-stop at the open plus a fraction of |open - low| (the sell ' +
                   'side mirrors it), placed only when the close is still on the near side of that ' +
                   'level and DMI(period), read shift bars back, sits below (or above, for the sell ' +
                   'side) the threshold below, on signal bars between 09:00 and 15:30 New York \u2014 ' +
                   'same rule as the Trend indi 2 replay, but the fraction, DMI period, shift and ' +
                   'threshold are computed fresh, live, on whichever bars you loaded. Trades one ' +
                   'side at a time; the published system runs long and short together.' +
                   ' <b>Exit:</b> the 16:59 New York close, the stop, or the account; no profit ' +
                   'target, the daily cap is the only ceiling.' + LIVE_BO_CAVEATS},
  custom: {label: 'Custom \u2014 day / time / news (tunable)',
           note: '<b>Entry:</b> built from the controls below \u2014 which weekdays, a fixed ' +
                 'time of day (or an offset before a news release), and long / short / a coin. ' +
                 '<b>Exit:</b> the Flat by minute below, same as every other entry rule (16:00 ' +
                 'unless set). Works on any market; the news calendar is USD-only, so a news ' +
                 'filter on a non-USD tape will simply never fire.'}
};
/* The list mixes five different kinds of thing: a coin flip with no signal
   at all (the control every other row is measured against), a rule computed
   live from whatever bars are loaded, a family of stored, offline-fitted
   forest decisions that only mean anything on the market they were fitted
   on, the Breakout Academy systems replayed exactly as studied, and the
   same two systems recomputed live with every input tunable. Grouped so the
   panel says which is which instead of leaving them all in one flat row. */
const STRAT_GROUPS = [
  {label: 'Coin flip \u2014 no signal, by design', keys: ['coin30', 'reentry', 'reentry1', 'orbrand', 'lh5coin']},
  {label: 'Rule, computed live \u2014 any market', keys: ['orb', 'lh5', 'long1505']},
  {label: 'Forest replay \u2014 fitted on NQ only', keys: ['lh5rf', 'lh5rfdir', 'rf2']},
  {label: 'Breakout replay \u2014 fitted on NQ/ES/YM only', keys: ['bo_ti4', 'bo_hit41', 'bo_hit34']},
  {label: 'Breakout, live \u2014 tunable, any market', keys: ['bo_live_hit', 'bo_live_ti']},
  {label: 'Build your own \u2014 day, time, news (any market)', keys: ['custom']}
];
/* What one point of each contract is worth, its tick, Lucid Trading's
   per-side commission (their published table, 2026-09-18), and three
   slippage assumptions in points per side: generous / normal / conservative.
   The slippage figures are judgment, stated in ticks so they can be argued
   with: ES 0/1/2 ticks because one ES tick is already half a percent of a
   median day; the rest 1/2/4 ticks. Picking an instrument sets $ per point
   and commission for the stage being edited and the account's slippage to
   the normal figure; the buttons under the slippage box switch it. VX is
   not on Lucid's list and its files carry no timestamps, so it is not here. */
const INSTRUMENTS = [
  {key: 'NQ',  root: 'NQ',  pv: 20,   comm: 1.75, tick: 0.25, slip: [0.25, 0.50, 1.00], note: 'Nasdaq 100'},
  {key: 'MNQ', root: 'NQ',  pv: 2,    comm: 0.50, tick: 0.25, slip: [0.25, 0.50, 1.00], note: 'micro Nasdaq'},
  {key: 'ES',  root: 'ES',  pv: 50,   comm: 1.75, tick: 0.25, slip: [0.00, 0.25, 0.50], note: 'S&P 500'},
  {key: 'MES', root: 'ES',  pv: 5,    comm: 0.50, tick: 0.25, slip: [0.00, 0.25, 0.50], note: 'micro S&P'},
  {key: 'RTY', root: 'RTY', pv: 50,   comm: 1.75, tick: 0.10, slip: [0.10, 0.20, 0.40], note: 'Russell 2000'},
  {key: 'M2K', root: 'RTY', pv: 5,    comm: 0.50, tick: 0.10, slip: [0.10, 0.20, 0.40], note: 'micro Russell'},
  {key: 'CL',  root: 'CL',  pv: 1000, comm: 2.00, tick: 0.01, slip: [0.01, 0.02, 0.04], note: 'crude oil'},
  {key: 'MCL', root: 'CL',  pv: 100,  comm: 0.50, tick: 0.01, slip: [0.01, 0.02, 0.04], note: 'micro crude'},
  {key: 'GC',  root: 'GC',  pv: 100,  comm: 2.30, tick: 0.10, slip: [0.10, 0.20, 0.40], note: 'gold'},
  {key: 'MGC', root: 'GC',  pv: 10,   comm: 0.80, tick: 0.10, slip: [0.10, 0.20, 0.40], note: 'micro gold'},
  {key: 'YM',  root: 'YM',  pv: 5,    comm: 1.75, tick: 1,    slip: [1, 2, 4],          note: 'Dow'},
  {key: 'MYM', root: 'YM',  pv: 0.5,  comm: 0.50, tick: 1,    slip: [1, 2, 4],          note: 'micro Dow'},
  {key: 'SI',  root: 'SI',  pv: 5000, comm: 2.30, tick: 0.005, slip: [0.005, 0.01, 0.02], note: 'silver, 5,000 oz'},
  {key: 'SIL', root: 'SI',  pv: 1000, comm: 1.60, tick: 0.005, slip: [0.005, 0.01, 0.02], note: 'micro silver, 1,000 oz'},
  {key: 'HG',  root: 'HG',  pv: 25000, comm: 2.30, tick: 0.0005, slip: [0.0005, 0.001, 0.002], note: 'copper, 25,000 lb'},
  {key: 'HE',  root: 'HE',  pv: 400,  comm: 2.80, tick: 0.025, slip: [0.025, 0.05, 0.10], note: 'lean hogs, cents a lb'},
  {key: 'NKD', root: 'NKD', pv: 5,    comm: 1.75, tick: 5,    slip: [5, 10, 20],        note: 'Nikkei 225 in dollars, thin book'}
];
const SLIP_NAMES = ['Generous', 'Normal', 'Conservative'];
/* the preset a stage is on, by $ per point and commission; null after a hand edit */
function instOf(C){
  for (const z of INSTRUMENTS) if (C.pointValue === z.pv && C.commission === z.comm) return z;
  return null;
}
const CONTRACTS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
/* LucidFlex tiers. Target and max-loss (trailDD) are the firm's own eval table;
   dailyCap is the stated 50% consistency rule (half the target); payoutDraw is
   the firm's per-tier payout cap; payoutAt is trailDD + payoutDraw + freezeOffset,
   the balance a funded account must reach for that cap to be exactly 50% of its
   locked-in profit (verified against the 25k tier: 1000 + 1000 + 100 = 2100, a
   funded balance of $27,100 - the number the firm itself quotes). The 90% split
   and $100 freeze offset are carried over from the 25k tier and assumed constant
   across tiers; ticket prices are Lucid's listed one-time-payment price. */
const LUCID_PRESETS = {
  '25k':  {label: 'LucidFlex 25k',  balance: 25000,  target: 1250, dailyCap: 625,
           trailDD: 1000, freezeOffset: 100, payoutAt: 2100, payoutDraw: 1000,
           payoutSplit: 0.9, ticket: 65,     pointValue: 20, commission: 1.5, slippage: 0.25},
  '50k':  {label: 'LucidFlex 50k',  balance: 50000,  target: 3000, dailyCap: 1500,
           trailDD: 2000, freezeOffset: 100, payoutAt: 4100, payoutDraw: 2000,
           payoutSplit: 0.9, ticket: 105.2,  pointValue: 20, commission: 1.5, slippage: 0.25},
  '100k': {label: 'LucidFlex 100k', balance: 100000, target: 6000, dailyCap: 3000,
           trailDD: 3000, freezeOffset: 100, payoutAt: 5600, payoutDraw: 2500,
           payoutSplit: 0.9, ticket: 215.6,  pointValue: 20, commission: 1.5, slippage: 0.25},
  '150k': {label: 'LucidFlex 150k', balance: 150000, target: 9000, dailyCap: 4500,
           trailDD: 4500, freezeOffset: 100, payoutAt: 7600, payoutDraw: 3000,
           payoutSplit: 0.9, ticket: 295.4,  pointValue: 20, commission: 1.5, slippage: 0.25}
};
/* true only when every field the preset sets still matches; a hand edit to any
   one of them (including on the funded stage, since presets set both) drops it */
function lucidPresetOn(key){
  const p = LUCID_PRESETS[key];
  return ST.balance === p.balance && ST.target === p.target && ST.dailyCap === p.dailyCap &&
    ST.trailDD === p.trailDD && ST.freezeOffset === p.freezeOffset &&
    ST.payoutAt === p.payoutAt && ST.payoutDraw === p.payoutDraw &&
    ST.payoutSplit === p.payoutSplit && ST.ticket === p.ticket &&
    ST.pointValue === p.pointValue && ST.commission === p.commission;
}
function applyLucidPreset(key){
  const p = LUCID_PRESETS[key];
  Object.assign(ST, {balance: p.balance, target: p.target, dailyCap: p.dailyCap,
    trailDD: p.trailDD, freezeOffset: p.freezeOffset, payoutAt: p.payoutAt,
    payoutDraw: p.payoutDraw, payoutSplit: p.payoutSplit, ticket: p.ticket,
    pointValue: p.pointValue, commission: p.commission, slippage: p.slippage});
}
const ST = {
  key: 'reentry', seed: 23,
  /* one unit is live at a time. 'pts' drives the engine with stopPts + rr,
     'usd' with riskUSD + targetUSD (the sweeps' own units, and exact: the
     engine takes the dollar target as given rather than via rr x stop x $/pt,
     which lands 625 at 625.0000000000001 and misses trades that touch it). */
  riskMode: 'pts', stopPts: 50, rr: 1.0, riskUSD: 100, targetUSD: 100,
  balance: 25000, contracts: 1, pointValue: 2, commission: 0.5, slippage: 0.25,
  trailDD: 1000, freezeOffset: 100, dailyCap: 625, dailyLoss: 0, target: 1250,
  payoutAt: 2100, payoutDraw: 1000, payoutSplit: 0.9, ticket: 65, fundedCap: null,
  from: '', to: '',                /* ISO days; '' = the end of the tape */
  exitMin: 960,                    /* "Flat by": minute of day; 960 (16:00) = the strategy's own exit or the close */
  ensN: 25,                        /* seeds the Ensemble block runs at once */
  /* the two live Breakout entries: every input Core.liveBreakoutSides takes,
     defaulted to the settings the offline study published (the Hitter is
     N=34; N=41 was a later sweep's better neighbour, not the published one) */
  boSide: 'long', boN: 34, boAdxPeriod: 50, boAdxThreshold: 17.5, boAdxDir: 'below',
  boFraction: 4, boDxPeriod: 100, boDxShift: 20, boDxThreshold: 35,
  /* the 'custom' strategy: day-of-week, a fixed entry time (or a news-release offset),
     direction, and which news categories/same-day rule/offset drive that news anchor */
  cuDow: {mon: true, tue: true, wed: true, thu: true, fri: true},
  cuEntryMin: 600,                 /* 10:00; used when cuNewsOffset is null */
  cuDir: 'random',                 /* 'random' | 'long' | 'short' */
  cuNews: {},                      /* {catId: bool}; {} = no news filter, every day eligible */
  cuNewsMode: 'important',         /* 'important' | 'first' | 'last' | 'every' */
  cuNewsOffset: null,              /* null | 60 | 30 | 10 | 1 | 'custom' */
  cuNewsOffsetCustom: 30,          /* minutes; used when cuNewsOffset === 'custom' */
  cuNewsCustomAfter: false,        /* the custom offset counts after the release, not before */
  cuNewsSkip: false,               /* day mode: true = trade every day EXCEPT release days */
  cuNewsQuality: 'any',            /* 'any' | 'verified' | 'cross': which timed rows may anchor */
  /* an entry time with no bar that day (08:30 data on the 09:30-16:00 tape): 'next' enters at
     the next bar that day, 'skip' skips the day. Was cuNoBar, default 'skip', which made
     every pre-open release silently vanish; renamed so that saved default does not return. */
  cuNoBar: 'next',
  cuHold: null,                    /* minutes each trade is held; null = until the Flat by time */
  cuShowMarks: true,               /* draw the evaluation's picked releases on the chart */
  /* what the FUNDED account trades, once it differs from the evaluation:
     its own entry, size, units, risk/target and loss limit. `same` (the
     default) means it trades exactly as the evaluation does. */
  funded: {same: true, key: 'reentry', contracts: 1, pointValue: 2, commission: 0.5,
           riskMode: 'pts', stopPts: 50, rr: 1.0, riskUSD: 100, targetUSD: 100, dailyLoss: 0,
           boSide: 'long', boN: 34, boAdxPeriod: 50, boAdxThreshold: 17.5, boAdxDir: 'below',
           boFraction: 4, boDxPeriod: 100, boDxShift: 20, boDxThreshold: 35,
           cuDow: {mon: true, tue: true, wed: true, thu: true, fri: true}, cuEntryMin: 600,
           cuDir: 'random', cuNews: {}, cuNewsMode: 'important', cuNewsOffset: null,
           cuNewsOffsetCustom: 30, cuNewsCustomAfter: false, cuNewsSkip: false,
           cuNewsQuality: 'any', cuNoBar: 'next', cuHold: null},
  stageView: 'eval'                /* which stage the stage-specific inputs edit */
};
/* the object the stage-specific inputs read and write */
function stageObj(){ return ST.stageView === 'funded' && !ST.funded.same ? ST.funded : ST; }
const STAGE_KEYS = ['key', 'contracts', 'pointValue', 'commission', 'riskMode',
                    'stopPts', 'rr', 'riskUSD', 'targetUSD', 'dailyLoss',
                    'boSide', 'boN', 'boAdxPeriod', 'boAdxThreshold', 'boAdxDir',
                    'boFraction', 'boDxPeriod', 'boDxShift', 'boDxThreshold',
                    'cuDow', 'cuEntryMin', 'cuDir', 'cuNews', 'cuNewsMode',
                    'cuNewsOffset', 'cuNewsOffsetCustom', 'cuNewsCustomAfter', 'cuNewsSkip',
                    'cuNewsQuality', 'cuNoBar', 'cuHold'];
try { mergeState(ST, JSON.parse(localStorage.getItem('tape.strat') || '{}')); } catch(e){}
/* mergeState only copies keys the default already has, of the same type: cuNews ({})
   has no keys and cuNewsOffset / cuHold default to null, so a saved news selection,
   timing preset or hold was silently dropped on every reload. Restore those three by
   hand, checking each value's shape. */
function restoreCustom(dst, src){
  if (!src || typeof src !== 'object') return;
  if (src.cuNews && typeof src.cuNews === 'object'){
    const known = {}; NEWSCAL.categories.forEach(c => { known[c.id] = 1; });
    dst.cuNews = {};
    /* the two Powell-named categories became the chair-neutral Fed Chair ones */
    const renamed = {fed_chair_powell_speaks: 'fed_chair_speaks', fed_chair_powell_testifies: 'fed_chair_testifies'};
    Object.keys(src.cuNews).forEach(k => {
      const id = renamed[k] || k;
      if (src.cuNews[k] === true && known[id]) dst.cuNews[id] = true;
    });
  }
  const off = src.cuNewsOffset;
  if (off === null || off === 'custom' || (typeof off === 'number' && Math.abs(off) < 1440)) dst.cuNewsOffset = off;
  const hold = src.cuHold;
  if (hold === null || (typeof hold === 'number' && hold >= 1)) dst.cuHold = hold;
}
try {
  const saved = JSON.parse(localStorage.getItem('tape.strat') || '{}');
  restoreCustom(ST, saved); restoreCustom(ST.funded, saved.funded);
} catch(e){}
/* If the stage is priced for a market the entry rule was never fitted on,
   snap it onto the first market that rule does cover, so a stored, offline
   decision (a fill level, a long/short call) is never read against a $/pt
   it was not built for. Used both here (a save from before this check
   existed, or a hand-edited key) and when the entry rule is switched live. */
function snapMarket(C, d, alsoSlippage){
  if (!d || !d.markets || instAllowed(instOf(C) || {root: null}, d)) return false;
  const fb = firstAllowed(d);
  if (!fb) return false;
  C.pointValue = fb.pv; C.commission = fb.comm;
  if (alsoSlippage) ST.slippage = fb.slip[1];
  return true;
}
[ST, ST.funded].forEach(C => snapMarket(C, STRATS[C.key], false));
let STRES = null;       /* the run for the CURRENT settings, recomputed live;
                           STLOADED (declared with the chart state) is the one
                           on the chart */

/* Converts once, at the moment of the switch, and never keeps the two forms
   in sync: a live two-way binding rounds on every keystroke and drifts. */
function setRiskMode(m, C){
  if (m === C.riskMode) return;
  const dv = C.contracts * C.pointValue;
  if (m === 'usd'){ C.riskUSD = C.stopPts * dv; C.targetUSD = C.riskUSD * C.rr; }
  else { C.stopPts = C.riskUSD / dv; C.rr = C.targetUSD / C.riskUSD; }
  C.riskMode = m;
}
/* the Breakout Academy tables are per market; the micros share their parent's.
   BO.sides only has NQ/ES/YM, so a root outside that set (no table exists,
   and the panel's own markets check keeps this unreachable) falls back to
   NQ rather than reading undefined out of the table. */
function boRoot(C){
  const z = instOf(C), r = z ? z.root : 'NQ';
  return (r === 'NQ' || r === 'ES' || r === 'YM') ? r : 'NQ';
}
/* a strategy with no `markets` list runs on whatever bars are loaded, at
   any $/pt; one WITH a list was fitted on that market's own tape (a stored
   decision per day, or per day and level) and reading it against another
   market's price action is not a rescale, it is a different question. */
function instAllowed(z, d){ return !d.markets || d.markets.indexOf(z.root) !== -1; }
/* the first instrument a restricted strategy may fall back onto, so
   switching entry rules never leaves the account priced off a market the
   strategy was never fitted for */
function firstAllowed(d){ return INSTRUMENTS.filter(z => instAllowed(z, d))[0]; }
/* live == a Breakout system computed fresh from BASE (Core.liveBreakoutSides)
   instead of read from a table baked on one historical tape. The signal
   window is pinned to the published 09:00-15:30 New York clock, the same
   as the replay above, even with RTH off: leaving it open let a bar at
   02:00 or midnight take the day's one entry before the real 09:00-15:30
   signal was ever reached. */
const LIVE_BO_WIN_START = 540, LIVE_BO_WIN_END = 930;   /* 09:00 / 15:30 New York */
function liveBoParams(system, C){
  const common = {system: system, side: C.boSide,
                  winStart: LIVE_BO_WIN_START, winEnd: LIVE_BO_WIN_END};
  return system === 'hitter'
    ? Object.assign(common, {n: C.boN, adxPeriod: C.boAdxPeriod,
        adxThreshold: C.boAdxThreshold, adxDirection: C.boAdxDir})
    : Object.assign(common, {fraction: C.boFraction, dxPeriod: C.boDxPeriod,
        dxShift: C.boDxShift, dxThreshold: C.boDxThreshold});
}
function sidesOf(d, C){
  if (d.live) return Core.liveBreakoutSides(BASE, liveBoParams(d.live, C));
  if (!d.sides) return undefined;
  if (d.sides === 'rf2') return RF2.sides;
  if (d.sides.slice(0, 3) === 'bo:') return BO.sides[d.sides.slice(3)][boRoot(C)];
  return LH5.rf.sides[d.sides];
}
/* ---------------- the 'custom' strategy: day / time / news, built live ----------------
   Everything here reads NEWSCAL (build_news_calendar.py's per-occurrence output, never
   a category-level constant -- see the plan) and the stage's own cu* fields. Isolated
   from sidesOf()/d.sides, the mechanism the 5 stored-table strategies above use. */
const NEWSCAL_BY_DATE = (() => {
  const idx = {};
  for (const e of NEWSCAL.events) (idx[e.date] || (idx[e.date] = [])).push(e);
  return idx;
})();
/* which timed rows a timing preset may anchor on, by the Source quality picked in the
   panel. 'any' is what every earlier build used. DISAGREE / INVESTING_INTERNAL_CONFLICT /
   UNMATCHED / AMBIGUOUS / DAY_ONLY never anchor, whichever is picked. */
const NEWS_QUALITY = {
  any:      {CROSS_VERIFIED: 1, SINGLE_SOURCE_FF: 1, SINGLE_SOURCE_INVESTING: 1,
             OFFICIAL_VERIFIED: 1, OFFICIAL_STANDARD: 1},
  verified: {CROSS_VERIFIED: 1, OFFICIAL_VERIFIED: 1, OFFICIAL_STANDARD: 1},
  cross:    {CROSS_VERIFIED: 1, OFFICIAL_VERIFIED: 1}
};
const NEWS_QUALITY_LABEL = {any: 'Any source', verified: 'Verified or official time',
                            cross: 'Two sources agree only'};
const NEWS_PRIORITY_RANK = (() => {
  const r = {}; NEWSCAL.categories.forEach(c => { r[c.name] = c.priorityRank; }); return r;
})();
const DOW_NAMES = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
/* pure calendar-date arithmetic: Date.UTC construction, getUTC/setUTC reads only --
   never the local-time variants, whose "previous day" depends on the viewer's own
   browser/OS timezone (this page runs on whoever's machine has it open) */
function shiftIsoDay(day, n){
  const dt = new Date(Date.UTC(+day.slice(0, 4), +day.slice(5, 7) - 1, +day.slice(8, 10)));
  dt.setUTCDate(dt.getUTCDate() + n);
  return dt.getUTCFullYear() + '-' + String(dt.getUTCMonth() + 1).padStart(2, '0') +
    '-' + String(dt.getUTCDate()).padStart(2, '0');
}
function prevIsoDay(day){ return shiftIsoDay(day, -1); }
function newsAny(C){ const c = C.cuNews || {}; return Object.keys(c).some(k => c[k]); }
/* timed around the release only when something is ticked; with nothing ticked the
   custom entry is the plain fixed-time rule, whatever the Timing buttons last said */
function newsAround(C){ return newsAny(C) && C.cuNewsOffset !== null; }
/* the entry's distance from the release in minutes: positive = before it, negative = after */
function newsOffsetMin(C){
  const o = C.cuNewsOffset === 'custom'
    ? (C.cuNewsCustomAfter ? -1 : 1) * C.cuNewsOffsetCustom : C.cuNewsOffset;
  return Math.max(-1439, Math.min(1439, o));
}
const offsetWords = o => o === 0 ? 'at the release' : Math.abs(o) + ' min ' + (o > 0 ? 'before' : 'after');
function newsEligibleForDay(date, checked, quality){
  const ok = NEWS_QUALITY[quality] || NEWS_QUALITY.any;
  return (NEWSCAL_BY_DATE[date] || []).filter(e =>
    checked[e.catId] && ok[e.status] && e.etMinute != null && !e.scheduled);
}
/* one day's checked, eligible events -> the anchor event(s) 'cuNewsMode' picks.
   'important': lowest NEWS_PRIORITY rank (unranked categories sort last, deterministic,
   never by what price did afterward). 'first'/'last': earliest/latest etMinute.
   'every': all of them (same-minute events collapse naturally when they land on the
   same anchor key downstream, in buildNewsSides). */
function reduceNewsEvents(evs, mode){
  if (!evs.length) return [];
  if (mode === 'every') return evs;
  if (mode === 'first') return [evs.reduce((a, b) => (b.etMinute < a.etMinute ? b : a))];
  if (mode === 'last') return [evs.reduce((a, b) => (b.etMinute > a.etMinute ? b : a))];
  return [evs.reduce((a, b) => {
    const ra = NEWS_PRIORITY_RANK[a.eventName], rb = NEWS_PRIORITY_RANK[b.eventName];
    return (rb === undefined ? Infinity : rb) < (ra === undefined ? Infinity : ra) ? b : a;
  })];
}
/* day -> its session in the loaded bars, rebuilt only when the tape changes */
let _sessByDay = null, _sessByDayBase = null;
function sessionByDay(){
  if (_sessByDayBase !== BASE){
    _sessByDay = {};
    BASE.sessions.forEach(S => { _sessByDay[S.day] = S; });
    _sessByDayBase = BASE;
  }
  return _sessByDay;
}
/* the bar an entry at `minute` lands on in session S: the bar at exactly that minute (as
   Core's barAt finds it), else with 'next' the earliest bar after it that day -- 08:00 on
   an RTH tape becomes the 09:30 open; a 24-hour session that starts the evening before
   still picks 08:00, not 18:00. -1 = no bar. */
function anchorBar(S, minute, outside){
  let next = -1, gap = Infinity;
  for (let i = S.a; i <= S.b; i++){
    const m = BASE.mins[i];
    if (m === minute) return i;
    if (m > minute && m - minute < gap){ gap = m - minute; next = i; }
  }
  return outside === 'next' ? next : -1;
}
/* the per-day slotsFromTable schedule for a news-anchored custom stage. Values are a
   structured {anchors:[...]} record, explicitly merged (pushed onto), never
   overwritten -- two different releases can legitimately share one anchor minute with
   different underlying status/sourceTimes. The engine itself only ever reads this
   table's KEYS when direction isn't 'table' (verified, see the plan); the anchors
   array is inert to it and exists purely for the ledger's UI-layer lookup and the
   panel's preview. The key is the bar minute the entry will actually use: the planned
   minute, or with cuNoBar 'next' the next bar that day (the anchor then records
   plannedMinute and moved). `stats`, when given, counts what happened to each anchor
   inside the run's span, for the preview. */
function buildNewsSides(C, stats){
  const checked = C.cuNews || {};
  if (!newsAny(C)) return {};
  const offsetMin = newsOffsetMin(C), outside = C.cuNoBar || 'next';
  const sess = sessionByDay(), [lo, hi] = newsSpan();
  const sides = {};
  for (const date in NEWSCAL_BY_DATE){
    if (!C.cuDow[DOW_NAMES[Core.dowOf(date)]]) continue;   // release-day weekday filter
    const chosen = reduceNewsEvents(newsEligibleForDay(date, checked, C.cuNewsQuality), C.cuNewsMode);
    for (const e of chosen){
      let plan = e.etMinute - offsetMin, anchorDate = date;
      if (plan < 0){ anchorDate = shiftIsoDay(date, -1); plan += 1440; }
      else if (plan >= 1440){ anchorDate = shiftIsoDay(date, 1); plan -= 1440; }
      const S = sess[anchorDate];
      const i = S ? anchorBar(S, plan, outside) : -1;
      const key = i >= 0 ? BASE.mins[i] : plan, moved = i >= 0 && key !== plan;
      if (stats && anchorDate >= lo && anchorDate <= hi){
        stats.anchors++; stats.timedDays[date] = 1;
        if (!S || i < 0){
          stats.none++; if (stats.outEx === undefined) stats.outEx = plan;
          if (!S){ stats.noDay++; if (!stats.noDayEx) stats.noDayEx = anchorDate; }
        }
        else {
          stats.slots[anchorDate + '|' + key] = 1;   /* two releases on one bar are one trade */
          if (moved){ stats.moved++; if (!stats.moveEx) stats.moveEx = [plan, key]; }
        }
      }
      if (!sides[anchorDate]) sides[anchorDate] = {};
      const k = String(key);
      if (!sides[anchorDate][k]) sides[anchorDate][k] = {anchors: []};
      sides[anchorDate][k].anchors.push({event: e.eventName, catId: e.catId,
        releaseMinute: e.etMinute, offset: offsetMin, status: e.status,
        sourceTimes: e.sourceTimes, plannedMinute: plan, moved: moved});
    }
  }
  return sides;
}
/* the plain (no timing preset) day filter: the days any checked category released
   (status-agnostic: the day is known even when the time is not), or with cuNewsSkip
   every loaded session EXCEPT those days */
function newsReleaseDays(C){
  const checked = C.cuNews || {}, days = {};
  for (const date in NEWSCAL_BY_DATE)
    if (NEWSCAL_BY_DATE[date].some(e => checked[e.catId] && !e.scheduled)) days[date] = true;
  return days;
}
function buildNewsDays(C){
  if (!newsAny(C)) return null;
  const hit = newsReleaseDays(C);
  if (!C.cuNewsSkip) return hit;
  const days = {};
  BASE.sessions.forEach(S => { if (!hit[S.day]) days[S.day] = true; });
  return days;
}
/* the run's span of days, as the panel's From/To and the tape's own ends give it */
function newsSpan(){
  const [a, b] = tapeEnds();
  return [ST.from && ST.from > a ? ST.from : a, ST.to && ST.to < b ? ST.to : b];
}
function customStageOpts(C){
  const dow = C.cuDow || {};
  const daysOfWeek = [0, 1, 2, 3, 4, 5, 6].filter(n => dow[DOW_NAMES[n]]);
  const exitMin = ST.exitMin < 960 ? ST.exitMin : null;
  const holdMin = C.cuHold === null || C.cuHold === undefined ? null : C.cuHold;
  const entry = !newsAround(C)
    ? {mode: 'reentry', startMin: C.cuEntryMin, endMin: C.cuEntryMin, slotMin: 30,
       direction: C.cuDir, exitMin: exitMin, holdMin: holdMin, daysOfWeek: daysOfWeek,
       newsDays: buildNewsDays(C), seed: ST.seed}
    : {mode: 'reentry', slotsFromTable: true, sides: buildNewsSides(C),
       tableSkipReason: 'position open at next news release', direction: C.cuDir,
       exitMin: exitMin, holdMin: holdMin, daysOfWeek: daysOfWeek,
       /* kept on entry itself, outside .sides, so ensSig() -- which strips .sides
          from its staleness fingerprint -- still detects a settings or calendar change */
       cuNews: C.cuNews, cuNewsMode: C.cuNewsMode, cuNewsOffset: C.cuNewsOffset,
       cuNewsOffsetCustom: C.cuNewsOffsetCustom, cuNewsCustomAfter: C.cuNewsCustomAfter,
       cuNewsQuality: C.cuNewsQuality, cuNoBar: C.cuNoBar,
       newsCalVersion: NEWSCAL.builtFrom, seed: ST.seed};
  return {
    entry: entry,
    trade: C.riskMode === 'usd' ? {riskUSD: C.riskUSD, targetUSD: C.targetUSD}
                                 : {stopPts: C.stopPts, rr: C.rr},
    acct: {balance: ST.balance, contracts: C.contracts, pointValue: C.pointValue,
           commission: C.commission, slippage: ST.slippage}
  };
}

/* one stage's entry / trade / acct blocks, from ST (the evaluation) or ST.funded */
function stageOpts(C){
  if (C.key === 'custom') return customStageOpts(C);
  const d = STRATS[C.key];
  /* "Flat by" set in the panel overrides the strategy's own exit minute; 16:00
     (null) is the session close, which every earlier strategy had */
  const exitMin = ST.exitMin < 960 ? ST.exitMin : (d.exitMin === undefined ? null : d.exitMin);
  return {
    entry: {mode: d.mode, startMin: d.startMin || 600, endMin: d.endMin,
            slotMin: d.slotMin || 30, orbBars: 26,
            winMin: d.winMin, winBars: d.winBars, exitMin: exitMin,
            /* each trade ends holdMin minutes after its own entry (the 30-minute arms) */
            holdMin: d.holdMin === undefined ? null : d.holdMin,
            /* a stored table per day (LH5) or per day and slot minute (RF2) */
            sides: sidesOf(d, C),
            sidesId: d.sides || null,
            /* the table names its own entry minutes (a stop-order system) */
            slotsFromTable: !!d.slotsFromTable,
            direction: d.direction, seed: ST.seed},
    /* a system with no profit target: only the stop and the account close a trade */
    trade: d.noTarget ? (C.riskMode === 'usd' ? {riskUSD: C.riskUSD, targetUSD: 1e12} : {stopPts: C.stopPts, rr: 1e9})
         : (C.riskMode === 'usd' ? {riskUSD: C.riskUSD, targetUSD: C.targetUSD} : {stopPts: C.stopPts, rr: C.rr}),
    acct: {balance: ST.balance, contracts: C.contracts, pointValue: C.pointValue,
           commission: C.commission, slippage: ST.slippage}
  };
}
function stratOpts(){
  const F = ST.funded;
  return Object.assign(stageOpts(ST), {
    rules: {trailDD: ST.trailDD, freezeOffset: ST.freezeOffset, dailyCap: ST.dailyCap,
            dailyLoss: ST.dailyLoss, fundedDailyLoss: F.same ? null : F.dailyLoss,
            target: ST.target, payoutAt: ST.payoutAt,
            payoutDraw: ST.payoutDraw, payoutSplit: ST.payoutSplit, ticket: ST.ticket,
            /* follows the cap as it is edited, rather than the value it had
               when the box was ticked */
            fundedCap: ST.fundedCap !== null ? ST.dailyCap : null},
    span: {from: ST.from, to: ST.to},
    funded: F.same ? undefined : stageOpts(F)
  });
}
/* Every run goes straight onto the chart: the candles, trade boxes, equity
   curve and ledger behind the panel always show the settings as they stand.
   The view is left where it is, so the same candles can be watched while a
   number is changed. */
function runStrat(){
  try {
    STRES = Core.runStrategy(BASE, stratOpts());
  } catch (err){ showError('Strategy', err); STRES = null; }
  const r = STRES;
  if (!r) return null;
  STLOADED = r; r.seed = ST.seed; r.pointValue = ST.pointValue;   /* named on the ledger; sizes the tooltip */
  /* the news-anchor table this run used, if any -- kept so the ledger tooltip can look
     up why a news-anchored trade or skip exists without recomputing stageOpts() against
     whatever the panel's settings have since changed to. A second stratOpts() call
     (cheap and pure) rather than restructuring the line above, which a lint check
     matches verbatim. */
  const _opts = stratOpts();
  r.newsSides = (_opts.entry && _opts.entry.slotsFromTable) ? _opts.entry.sides : null;
  TRADES = r.trades;
  reindex(); reindexSessions(); lastSig = '';
  document.getElementById('sub').textContent =
    STRATS[ST.key].label + ' \u00b7 ' + ST.contracts + ' contract' + (ST.contracts > 1 ? 's' : '') +
    (ST.funded.same ? '' : ' \u00b7 funded: ' + STRATS[ST.funded.key].label + ' \u00b7 ' +
      ST.funded.contracts + ' contract' + (ST.funded.contracts > 1 ? 's' : '')) +
    ' \u00b7 ' + r.trades.filter(t => !t.skipped).length.toLocaleString() + ' trades' +
    /* a rule that stands aside leaves skipped rows in the list; they are not trades */
    (r.trades.some(t => t.skipped) ? ' \u00b7 ' + r.trades.filter(t => t.skipped).length.toLocaleString() + ' stood aside' : '');
  try { localStorage.setItem('tape.strat', JSON.stringify(ST)); } catch(e){}
  render();
  return r;
}
/* Recompute after a pause in typing and refresh ONLY the two result blocks,
   so the field being edited keeps its focus and caret. */
let stTimer = null;
function stLive(){
  STRES = null;
  clearTimeout(stTimer);
  stTimer = setTimeout(() => {
    const h = document.getElementById('stHero'), el = document.getElementById('stResult');
    if (h) h.innerHTML = heroHTML();
    if (el) el.innerHTML = resultHTML();
    paintEnsemble();   /* no computation: re-reads the stored runs, flags them stale */
  }, 200);
}
/* "last N months" measured back from the tape's final session. Jan 31 minus a
   month is the end of February, not March 3, which is what setUTCMonth alone
   would give. */
function monthsBack(iso, n){
  const d = new Date(iso + 'T00:00:00Z'), m = d.getUTCMonth() - n;
  d.setUTCMonth(m);
  if (d.getUTCMonth() !== ((m % 12) + 12) % 12) d.setUTCDate(0);
  return d.toISOString().slice(0, 10);
}
const SPANS = [['All', 0], ['3 mo', 3], ['6 mo', 6], ['12 mo', 12], ['24 mo', 24]];
function tapeEnds(){
  const s = BASE.sessions;
  return s.length ? [s[0].day, s[s.length - 1].day] : ['', ''];
}
function spanFrom(n){ return n ? monthsBack(tapeEnds()[1], n) : ''; }

const stRow = (l, c, note) => '<div class="setrow"><span>' + l +
  (note ? '<br><span style="color:var(--ink-faint);font-size:9.5px">' + note + '</span>' : '') +
  '</span>' + c + '</div>';

/* The two result blocks, kept apart from the inputs so a keystroke can refresh
   them without rebuilding the field being typed in. Each runs the engine if
   nothing is cached; the second call finds the first one's result. */
function stNet(q){ return q.net; }
function heroHTML(){
  const r = STRES || runStrat();
  if (!r) return '';
  const q = r.summary;
  const pct = q.evals ? (q.passRate * 100).toFixed(1) + '%' : '\u2014';
  return '<div class="sthero"><b>' + pct + '</b><span>pass rate \u00b7 ' + q.passes + ' of ' +
    q.evals + ' evaluations reached the profit target<br>' +
    'net ' + money0(stNet(q)) + ' \u00b7 ' + q.payouts + ' payout' + (q.payouts === 1 ? '' : 's') +
    ' \u00b7 ' + q.sessions.toLocaleString() + ' sessions, ' + (q.firstDay || '\u2014') +
    ' to ' + (q.lastDay || '\u2014') + ' \u00b7 seed ' + ST.seed + '</span></div>';
}
function resultHTML(){
  const r = STRES || runStrat();
  if (!r) return '';
  const q = r.summary, row = stRow;
  const payValue = q.payoutValue;
  const net = stNet(q);
  const pct = q.evals ? (q.passRate * 100).toFixed(1) + '%' : '\u2014';
  /* Accounts that were paid at least once. Total payouts over passes is a
     count per funded account and can exceed 100% (one account may withdraw
     several times), so it must not be read as a probability. */
  const paid = r.accounts.filter(a => a.draws > 0).length;
  const pc = (n, d) => d ? (100 * n / d).toFixed(1) + '%' : '\u2014';
  return '<h3>Result</h3>' +
    '<div class="verdict ' + (net >= 0 ? 'pass' : 'fail') + '">' +
    'NET ' + money(net) +
    '  \u00b7  ' + q.payouts + ' payout' + (q.payouts === 1 ? '' : 's') +
    ' from ' + q.evals + ' evaluations</div>' +
    '<div class="setgrid"><div>' +
    row('Evaluations bought', String(q.evals)) +
    row('Passed to funded', q.passes + '  (' + pct + ')') +
    row('Evaluations blown', String(q.evalBust)) +
    row('Funded accounts blown', String(q.fundBust)) +
    row('Best funded balance', money(q.bestFunded)) +
    '</div><div>' +
    row('One ticket ends in a payout', pc(paid, q.evals),
        paid + ' of ' + q.evals + ' evaluations bought were paid at least once') +
    row('A funded account is paid at least once', pc(paid, q.passes),
        paid + ' of ' + q.passes + ' funded') +
    row('Payouts per funded account', q.passes ? (q.payouts / q.passes).toFixed(2) : '\u2014',
        q.payouts + ' payouts in all; one account can withdraw more than once') +
    row('Won from payouts', money(q.won),
        q.payouts + ' \u00d7 ' + money(payValue) + ' \u2014 the gross, before tickets') +
    row('Spent on evaluations', money(-q.cost)) +
    '</div></div>' +
    '<p style="color:var(--ink-faint);font-size:11px">Net values a payout at ' +
    money(payValue) + ' \u2014 ' + money(q.payoutDraw) + ' withdrawn \u00d7 ' +
    (q.payoutSplit * 100).toFixed(0) + '%, not the full profit reached \u2014 and nets off ' +
    'every evaluation ticket bought. One seed is one draw of the coin, not an average: the ' +
    'same settings land a few points either side of this figure from one seed to the next, ' +
    'and the Ensemble block below runs many seeds at once to show that spread. ' +
    'These ' + q.nTrades.toLocaleString() + ' trades are on the chart behind this panel.</p>';
}

/* ---------------- the ensemble ----------------
   One seed is one sequence of coin flips. Running the same settings under
   many seeds shows the spread the rule produces and where the seed on the
   chart sits inside it. The runs stay OFF the chart -- only each run's
   account totals and its wealth curve are kept -- and go in 40 ms slices,
   so the page keeps painting while a thousand full-tape runs go by.
   Every press draws a fresh base seed and runs base, base + 1, ... so the
   batch is independent of the seed on the chart; that seed is compared
   AGAINST the batch instead -- its own curve and rank are drawn from the
   run already on the chart (STRES), as long as the settings still match. */
const ENS = {res: null, busy: false, done: 0, total: 0};
const ENS_SIZES = [10, 25, 50, 100, 1000];
/* the settings with the seed removed: an ensemble is stale once anything
   else has changed, but not when the chart merely moves to another seed */
function ensSig(opt){
  const o = JSON.parse(JSON.stringify(opt));
  delete o.entry.seed; delete o.entry.sides;
  if (o.funded && o.funded.entry){ delete o.funded.entry.seed; delete o.funded.entry.sides; }
  return JSON.stringify(o);
}
/* a strategy with no coin in either stage gives the same path for every seed */
function ensRandom(opt){
  return opt.entry.direction === 'random' ||
         !!(opt.funded && opt.funded.entry && opt.funded.entry.direction === 'random');
}
/* linear-interpolated percentile of an unsorted array. Infinity is a legal
   value here (a break-even that a run never reached), and interpolating
   towards it gives NaN, so a percentile that falls on it is returned as is. */
function pctOf(a, p){
  const v = a.slice().sort((x, y) => x - y), i = (v.length - 1) * p;
  const lo = Math.floor(i), hi = Math.ceil(i), t = i - lo;
  if (hi === lo || t === 0) return v[lo];
  if (!isFinite(v[lo]) || !isFinite(v[hi])) return v[hi];
  return v[lo] + (v[hi] - v[lo]) * t;
}
function runEnsemble(){
  if (ENS.busy) return;
  const opt = stratOpts(), n = ST.ensN, nS = BASE.sessions.length;
  /* a rule with no coin in it has nothing for a seed to change: every account
     on the tape would be byte-identical, so there is nothing to multiply into
     a sample, and the panel that calls this is not shown for one */
  if (!ensRandom(opt)) return;
  const optRun = JSON.parse(JSON.stringify(opt));
  if (opt.entry.sides){
    optRun.entry.sides = opt.entry.sides;      /* keep the reference, not a copy */
  }
  /* a fresh base every press, drawn the way the dice button draws a seed;
     the range is printed under the figures so a batch can be named */
  const seed0 = (Date.now() ^ (Math.random() * 0xFFFFFFFF)) >>> 0;
  const seeds = [];
  for (let k = 0; k < n; k++) seeds.push((seed0 + k) >>> 0);
  /* the span's session indices, so the curves are drawn over the sessions
     that were traded rather than a flat tail on either side */
  let a = -1, b = -1;
  for (let i = 0; i < nS; i++){
    const d = BASE.sessions[i].day;
    if ((!ST.from || d >= ST.from) && (!ST.to || d <= ST.to)){ if (a < 0) a = i; b = i; }
  }
  const R = {sig: ensSig(opt), seeds: seeds, seed0: seed0, n: n, a: a, b: b,
             nets: [], evals: [], passes: [], payouts: [], won: [], spent: [], curves: [],
             sessions: 0, firstDay: null, lastDay: null};
  ENS.busy = true; ENS.done = 0; ENS.total = n;
  let k = 0;
  const gen = DATA_GEN;   /* the tape this batch belongs to */
  const step = () => {
    /* a tape loaded mid-batch: the runs so far are on other bars, drop them */
    if (DATA_GEN !== gen){ ENS.busy = false; ENS.res = null; paintEnsemble(); return; }
    const t0 = performance.now();
    while (k < n && performance.now() - t0 < 40){
      const o = Object.assign({}, optRun, {entry: Object.assign({}, optRun.entry, {seed: seeds[k]})});
      let r;
      try { r = Core.runStrategy(BASE, o); }
      catch (err){ ENS.busy = false; paintEnsemble(); showError('Ensemble', err); return; }
      const q = r.summary;
      R.nets.push(q.net); R.evals.push(q.evals); R.passes.push(q.passes);
      R.payouts.push(q.payouts); R.won.push(q.won); R.spent.push(q.spent);
      R.curves.push(Core.wealthCurve(r, nS));
      R.sessions = q.sessions; R.firstDay = q.firstDay; R.lastDay = q.lastDay;
      k++;
    }
    ENS.done = k;
    if (k < n){ paintEnsemble(); setTimeout(step, 0); return; }
    ENS.busy = false; ENS.res = R;
    paintEnsemble();
  };
  paintEnsemble();
  setTimeout(step, 0);
}
function paintEnsemble(){
  const el = document.getElementById('stEns');
  if (!el) return;
  el.innerHTML = ensembleHTML();
  bindEnsemble();
}
function bindEnsemble(){
  const el = document.getElementById('stEns');
  if (!el) return;
  el.querySelectorAll('button[data-ens]').forEach(b => b.onclick = () => {
    ST.ensN = +b.dataset.ens; paintEnsemble();
  });
  const run = document.getElementById('stEnsRun');
  if (run) run.onclick = runEnsemble;
}

/* The ensemble's wealth over the span. Up to 100 runs each run is a faint
   line, green if it finished ahead; past that the lines merge into a blob, so
   the fan is drawn as the middle 50% and 90% of runs at each session instead.
   The median across runs is amber; `mine` (the run on the chart, when its
   settings match the batch) is ink. Curves are thinned to ~200 points. */
const ENS_LINES_MAX = 100;
function ensCurves(R, mine){
  const n = R.b - R.a + 1;
  if (n < 2 || !R.curves.length || R.b >= BASE.sessions.length) return '';
  const stride = Math.max(1, Math.ceil(n / 200));
  const pick = c => {
    const o = [];
    for (let i = R.a; i <= R.b; i += stride) o.push(c[i]);
    if ((n - 1) % stride) o.push(c[R.b]);
    return o;
  };
  const CV = R.curves.map(pick), m = CV[0].length;
  const MY = mine ? pick(mine.curve) : null;
  const bands = R.n > ENS_LINES_MAX;
  const Wd = 600, Ht = 250, PADL = 70, PADR = 66, PADT = 12, PADB = 28;
  const pw = Wd - PADL - PADR, ph = Ht - PADT - PADB;
  /* per-session quantiles across the runs: the median always, the band
     edges when there are too many runs to draw one by one */
  const Q = {};
  const want = bands ? [0.05, 0.25, 0.5, 0.75, 0.95] : [0.5];
  want.forEach(p => { Q[p] = []; });
  for (let i = 0; i < m; i++){
    const col = CV.map(c => c[i]);
    want.forEach(p => Q[p].push(pctOf(col, p)));
  }
  const med = Q[0.5];
  let lo = 0, hi = 0;
  const span = c => c.forEach(v => { if (v < lo) lo = v; if (v > hi) hi = v; });
  if (bands){ span(Q[0.05]); span(Q[0.95]); } else CV.forEach(span);
  if (MY) span(MY);
  const pad = (hi - lo) * 0.08 || 1; lo -= pad; hi += pad;
  const X = i => PADL + pw * i / (m - 1);
  const Y = v => PADT + ph * (1 - (v - lo) / (hi - lo));
  const path = c => c.map((v, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1)).join(' ');
  let out = '<svg viewBox="0 0 ' + Wd + ' ' + Ht + '" role="img">';
  for (let t = 0; t <= 4; t++){
    const v = lo + (hi - lo) * t / 4, y = Y(v);
    out += '<line x1="' + PADL + '" y1="' + y + '" x2="' + (Wd - PADR) + '" y2="' + y +
           '" stroke="' + cv_('--rule-soft') + '"/>' +
           '<text x="' + (PADL - 7) + '" y="' + (y + 3) + '" fill="' + cv_('--ink-faint') +
           '" font-size="9" font-family="' + cv_('--mono') + '" text-anchor="end">' +
           money0(v) + '</text>';
  }
  out += '<line x1="' + PADL + '" y1="' + Y(0) + '" x2="' + (Wd - PADR) + '" y2="' + Y(0) +
         '" stroke="' + cv_('--rule') + '" stroke-width="1.4"/>';
  if (bands){
    /* a band is the upper edge forwards and the lower edge back */
    const band = (up, dn, op) => {
      let d = path(up);
      for (let i = m - 1; i >= 0; i--) d += ' L' + X(i).toFixed(1) + ' ' + Y(dn[i]).toFixed(1);
      return '<path d="' + d + ' Z" fill="' + S.col.accent + '" opacity="' + op +
             '" stroke="none"/>';
    };
    out += band(Q[0.95], Q[0.05], 0.13) + band(Q[0.75], Q[0.25], 0.22);
  } else {
    CV.forEach((c, k) => {
      out += '<path d="' + path(c) + '" fill="none" stroke="' +
             (R.nets[k] >= 0 ? S.col.up : S.col.down) + '" stroke-width="0.8" opacity="0.22">' +
             '<title>seed ' + R.seeds[k] + ' \u00b7 net ' + money0(R.nets[k]) + '</title></path>';
    });
  }
  const label = (y, txt, col) =>
    '<text x="' + (Wd - PADR + 5) + '" y="' + (y + 3) + '" fill="' + col +
    '" font-size="9" font-family="' + cv_('--mono') + '">' + txt + '</text>';
  const yMed = Y(med[m - 1]);
  out += '<path d="' + path(med) + '" fill="none" stroke="' + S.col.accent +
         '" stroke-width="2.2"/>' + label(yMed, 'median', S.col.accent);
  if (MY){
    /* the two end labels collide when the chart's seed finishes near the
       median, which a typical seed does; push its label clear */
    let yS = Y(MY[m - 1]);
    if (Math.abs(yS - yMed) < 10) yS = yMed + (yS >= yMed ? 10 : -10);
    out += '<path d="' + path(MY) + '" fill="none" stroke="' + cv_('--ink') +
           '" stroke-width="1.6" data-seed="' + mine.seed + '"><title>' + mine.label +
           ' \u00b7 on the chart \u00b7 net ' + money0(mine.net) + '</title></path>' +
           label(yS, mine.label, cv_('--ink'));
  }
  for (let t = 0; t <= 4; t++){
    const i = Math.round((m - 1) * t / 4), si = Math.min(R.b, R.a + i * stride);
    out += '<text x="' + X(i) + '" y="' + (Ht - 8) + '" fill="' + cv_('--ink-faint') +
           '" font-size="9" font-family="' + cv_('--mono') + '" text-anchor="middle">' +
           BASE.sessions[si].day.slice(0, 7) + '</text>';
  }
  return out + '</svg>';
}
/* where the runs finish, with the seed on the chart marked */
function ensHist(R, mine){
  /* PADT leaves room for the chart-seed marker and its label above the bars */
  const Wd = 600, Ht = 140, PADL = 70, PADR = 66, PADT = 26, PADB = 26;
  const pw = Wd - PADL - PADR, ph = Ht - PADT - PADB;
  const v = R.nets.slice().sort((a, b) => a - b);
  let lo = Math.min(v[0], 0), hi = Math.max(v[v.length - 1], 0);
  if (mine){ lo = Math.min(lo, mine.net); hi = Math.max(hi, mine.net); }
  const nb = R.n >= 500 ? 36 : 18, w = (hi - lo) / nb || 1;
  const bins = new Array(nb).fill(0);
  v.forEach(x => bins[Math.min(nb - 1, Math.floor((x - lo) / w))]++);
  const mx = Math.max.apply(null, bins) || 1;
  const X = x => PADL + pw * (x - lo) / ((hi - lo) || 1);
  let out = '<svg viewBox="0 0 ' + Wd + ' ' + Ht + '" role="img">';
  bins.forEach((c, i) => {
    if (!c) return;
    const x0 = X(lo + i * w), x1 = X(lo + (i + 1) * w), h = ph * c / mx;
    out += '<rect x="' + x0 + '" y="' + (PADT + ph - h) + '" width="' + Math.max(1, x1 - x0 - 1) +
           '" height="' + h + '" fill="' + (lo + (i + 0.5) * w >= 0 ? S.col.up : S.col.down) +
           '" opacity="0.75"><title>' + c + ' run' + (c === 1 ? '' : 's') + ' finished between ' +
           money0(lo + i * w) + ' and ' + money0(lo + (i + 1) * w) + '</title></rect>';
  });
  if (lo < 0 && hi > 0)
    out += '<line x1="' + X(0) + '" y1="' + PADT + '" x2="' + X(0) + '" y2="' + (PADT + ph) +
           '" stroke="' + cv_('--ink') + '" stroke-width="1.4"/>';
  if (mine){
    const x = X(mine.net);
    out += '<path d="M' + x + ' ' + (PADT - 2) + ' l-5 -8 l10 0 z" fill="' + cv_('--ink') + '"/>' +
           '<text x="' + x + '" y="' + (PADT - 12) + '" fill="' + cv_('--ink') +
           '" font-size="9" font-family="' + cv_('--mono') + '" text-anchor="middle">' +
           mine.label + '</text>';
  }
  for (let t = 0; t <= 4; t++){
    const x = lo + (hi - lo) * t / 4;
    out += '<text x="' + X(x) + '" y="' + (Ht - 8) + '" fill="' + cv_('--ink-faint') +
           '" font-size="9" font-family="' + cv_('--mono') + '" text-anchor="middle">' +
           money0(x) + '</text>';
  }
  return out + '</svg>';
}
function ensembleHTML(){
  const opt = stratOpts(), R = ENS.res;
  const fixedRule = !ensRandom(opt);
  if (fixedRule){
    /* nothing here has a coin in it, so every seed replays the same trades on
       the same accounts -- there is no bigger sample size to buy by pressing
       this again. Multiplying seeds is only meaningful for a rule that still
       has a random decision left in it somewhere (entry direction, in either
       stage); this one has none, so the control does not appear at all. */
    return '<h3>Ensemble</h3>' +
      '<p>' + esc(STRATS[ST.key].label) + ' takes no random decision, so every seed replays the ' +
      'exact same trades on the exact same accounts. There is nothing here for more seeds to ' +
      'change, so this panel only appears for strategies with a coin flip still in them.</p>';
  }
  let out = '<h3>Ensemble</h3>' +
    '<p>One seed is one sequence of coin flips. The same settings run under many seeds ' +
    'show the spread the rule produces, and where the seed on the chart sits inside it. ' +
    'These runs stay off the chart; only each run\u2019s account totals and its wealth ' +
    'curve are kept.</p>';
  out += '<div class="szbar"><span class="lbl">Seeds</span>' +
    ENS_SIZES.map(v => '<button class="btn' + (ST.ensN === v ? ' on' : '') +
      '" data-ens="' + v + '">' + v + '</button>').join('') +
    '<span class="stpair"><button class="btn on" id="stEnsRun"' + (ENS.busy ? ' disabled' : '') +
    '>' + (ENS.busy ? 'Running\u2026 ' + ENS.done + ' of ' + ENS.total
                    : 'Run ' + ST.ensN + ' seeds') +
    '</button></span>' +
    '<span style="color:var(--ink-faint);font-size:9.5px">a fresh batch of seeds every press</span></div>';
  if (!R) return out;
  const stale = R.sig !== ensSig(opt);
  const med = medOf, mean = a => a.reduce((x, y) => x + y, 0) / a.length;
  const wins = R.nets.filter(x => x > 0).length;
  /* the run on the chart, measured against the batch: its own curve and its
     totals, valid only while the batch was run under the same settings */
  let mine = null;
  const my = stale ? null : (STRES || runStrat());
  if (my){
    const q = my.summary;
    mine = {seed: ST.seed, label: 'seed ' + ST.seed,
            net: q.net, evals: q.evals, passes: q.passes, payouts: q.payouts,
            won: q.won, spent: q.spent, rate: q.evals ? q.passes / q.evals : 0,
            be: q.payouts ? q.spent / q.payouts : Infinity,
            curve: Core.wealthCurve(my, BASE.sessions.length)};
  }
  const ahead = mine ? R.nets.filter(x => x < mine.net).length : 0;
  const pr = (p, e) => e ? p / e : 0;
  const rates = R.passes.map((p, k) => pr(p, R.evals[k]));
  const be = R.spent.map((s, k) => R.payouts[k] ? s / R.payouts[k] : Infinity);
  const pctS = v => (100 * v).toFixed(1) + '%';
  const sd = a => {
    const m = mean(a);
    return Math.sqrt(a.reduce((s, x) => s + (x - m) * (x - m), 0) / Math.max(1, a.length - 1));
  };
  /* one row: the run on the chart, the five percentiles the band chart draws,
     then the mean and the sample standard deviation. A mean or SD that is
     not finite (a break-even some runs never reached) is a dash, not a
     number; a percentile that lands on such a run says "never paid". */
  const PCTS = [0.05, 0.25, 0.5, 0.75, 0.95];
  const fin = (v, f) => isFinite(v) ? f(v) : '\u2014';
  const cell = (a, f, mv, fsd) => '<td>' + (mine ? f(mv) : '\u2014') + '</td>' +
    PCTS.map(p => '<td>' + f(pctOf(a, p)) + '</td>').join('') +
    '<td>' + fin(mean(a), f) + '</td><td>' + fin(sd(a), fsd || f) + '</td>';
  const one = v => v.toFixed(1);        /* an SD of a count is not a count */
  const bands = R.n > ENS_LINES_MAX;
  if (stale)
    out += '<div class="note warn" style="margin:6px 0"><b>Settings have changed</b> since these ' +
      R.n + ' seeds ran. Run again to refresh them; the figures below are for the old settings.</div>';
  out += '<div class="verdict ' + (mean(R.nets) >= 0 ? 'pass' : 'fail') + '">' +
    (mean(R.nets) >= 0 ? 'PROFITABLE ON AVERAGE' : 'LOSES MONEY ON AVERAGE') +
    '  \u00b7  median net ' + money0(med(R.nets)) + '  \u00b7  ' + wins + ' of ' + R.n +
    ' seeds made money</div>' +
    (mine ? '<p style="font-size:11.5px">Seed <b>' + mine.seed + '</b>, the one on the chart, ' +
        'finishes ahead of <b>' + ahead + ' of these ' + R.n + '</b> runs at ' +
        money0(mine.net) + '.</p>' : '') +
    '<div class="szfig"><h4>Wealth over time \u00b7 ' + R.n + ' seeds</h4>' +
    '<p>Payouts banked minus every ticket bought, session by session. ' +
    (bands ? 'The dark band holds the middle half of the runs at each session, the light band ' +
             'the middle 90%; amber is the median. '
           : 'Faint lines are the runs, green if they finished ahead; amber is the median across ' +
             'them at each session. Hover a line for its seed. ') +
    (mine ? 'White is the seed on the chart.' : '') +
    '</p>' + ensCurves(R, mine) + '</div>' +
    '<div class="szfig" style="margin-top:8px"><h4>Where the runs finish</h4>' +
    '<p>Final net of each of the ' + R.n + ' runs.</p>' + ensHist(R, mine) + '</div>' +
    '<table class="cmp ens" style="margin-top:8px"><thead><tr><th></th><th>This seed</th>' +
    '<th>5th</th><th>25th</th><th>Median</th><th>75th</th><th>95th</th><th>Mean</th><th>SD</th>' +
    '</tr></thead><tbody>' +
    '<tr class="big"><td>Net</td>' + cell(R.nets, money0, mine && mine.net) + '</tr>' +
    /* the two halves of the net sit right under it; for one run they subtract
       exactly, for the column statistics they do not, as the footnote says */
    '<tr><td>Won from payouts</td>' + cell(R.won, money0, mine && mine.won) + '</tr>' +
    '<tr><td>Spent on tickets</td>' + cell(R.spent, money0, mine && mine.spent) + '</tr>' +
    '<tr><td>Evaluations bought</td>' + cell(R.evals, cnt, mine && mine.evals, one) + '</tr>' +
    '<tr><td>Passed to funded</td>' + cell(R.passes, cnt, mine && mine.passes, one) + '</tr>' +
    '<tr><td>Pass rate</td>' + cell(rates, pctS, mine && mine.rate) + '</tr>' +
    '<tr><td>Payouts</td>' + cell(R.payouts, cnt, mine && mine.payouts, one) + '</tr>' +
    '<tr><td>Break-even payout</td>' +
    cell(be, v => isFinite(v) ? money0(v) : 'never paid', mine && mine.be) +
    '</tr></tbody></table>' +
    '<p style="color:var(--ink-faint);font-size:10.5px;margin-top:6px">Each cell is its own ' +
    'statistic across the ' + R.n + ' runs, so the rows do not add up; only the run on the ' +
    'chart has Won minus Spent equal to Net. The five percentile columns are the levels the ' +
    'band chart draws. SD is the sample standard deviation. ' + R.n + ' seeds are ' +
    R.n + ' draws of the coin over the same ' + R.sessions.toLocaleString() + ' sessions' +
    (R.firstDay ? ', ' + R.firstDay + ' to ' + R.lastDay : '') + ': the spread is coin-flip ' +
    'variance on one stretch of tape, not a forecast for a different one. This batch is seeds ' +
    R.seeds[0] + ' to ' + R.seeds[R.n - 1] + '; type any one of them into the Seed box to put ' +
    'that run on the chart.</p>';
  return out;
}

/* thematic grouping for the ~50-category news checklist -- a judgment call, trivially
   editable, not load-bearing (every category is still individually checkable) */
function newsCatGroup(name){
  if (/decision day|Federal Funds|FOMC Statement|FOMC Press|FOMC Meeting|FOMC Economic|Fed Announcement/i.test(name))
    return 'Fed decisions';
  if (/Speaks|Testifies/i.test(name)) return 'Speeches';
  if (/Inflation Expectations|CPI|PCE|PPI/i.test(name)) return 'Inflation';
  if (/Payroll|Non-Farm|Employment|Unemployment|Claims|JOLTS|Hourly Earnings/i.test(name)) return 'Jobs';
  if (/GDP|Retail Sales|Durable Goods/i.test(name)) return 'Growth & spending';
  if (/ISM|PMI|Empire|Philly|Confidence|Sentiment/i.test(name)) return 'Surveys & PMIs';
  if (/Housing|Home Sales|HPI/i.test(name)) return 'Housing';
  return 'Auctions, politics & other';
}
const NEWS_GROUP_ORDER = ['Fed decisions', 'Jobs', 'Inflation', 'Growth & spending',
                          'Surveys & PMIs', 'Housing', 'Speeches', 'Auctions, politics & other'];
/* one click replaces the selection; ids that are not in this calendar are dropped */
const NEWS_PRESETS = [
  ['big3', 'Big 3', 'The Fed rate decision, the jobs report and CPI',
   ['federal_funds_rate', 'non_farm_employment_change', 'cpi_m_m']],
  ['fed', 'Fed days', 'Rate decision, statement, press conference and minutes',
   ['federal_funds_rate', 'fomc_statement', 'fomc_press_conference', 'fomc_meeting_minutes']],
  ['jobs', 'Jobs', 'Payrolls, unemployment, earnings, ADP, claims, JOLTS',
   ['non_farm_employment_change', 'unemployment_rate', 'average_hourly_earnings_m_m',
    'adp_non_farm_employment_change', 'unemployment_claims', 'jolts_job_openings']],
  ['infl', 'Inflation', 'CPI, core CPI, PPI, core PPI and core PCE',
   ['cpi_m_m', 'cpi_y_y', 'core_cpi_m_m', 'ppi_m_m', 'core_ppi_m_m', 'core_pce_price_index_m_m']],
  ['830', '08:30 data', 'Every release that usually lands at 08:30 ET',
   () => NEWSCAL.categories.filter(c => c.typicalEtMinute === 510).map(c => c.id)],
  ['top10', 'Top 10', 'The ten highest-priority releases',
   () => NEWSCAL.categories.slice().sort((a, b) => a.priorityRank - b.priorityRank).slice(0, 10).map(c => c.id)]
];
function newsPresetIds(p){
  return typeof p[3] === 'function' ? p[3]() : p[3].filter(id => NEWS_CAT[id]);
}
/* UI-only state that is not worth saving: the search text and which groups are open */
const NEWS_UI = {q: '', open: {}, lastOffset: 30};
const NEWS_CAT = (() => { const m = {}; NEWSCAL.categories.forEach(c => { m[c.id] = c; }); return m; })();
/* per category, over the run's span: releases, and releases with a time the chosen
   Source quality accepts */
function newsCounts(C){
  const [lo, hi] = newsSpan(), ok = NEWS_QUALITY[C.cuNewsQuality] || NEWS_QUALITY.any;
  const n = {}, timed = {};
  for (const e of NEWSCAL.events){
    if (e.scheduled || e.date < lo || e.date > hi) continue;
    n[e.catId] = (n[e.catId] || 0) + 1;
    if (e.etMinute != null && ok[e.status]) timed[e.catId] = (timed[e.catId] || 0) + 1;
  }
  return {n, timed};
}
function newsNames(ids){
  const names = ids.map(id => (NEWS_CAT[id] || {name: id}).name);
  return names.length <= 3 ? names.join(', ').replace(/, ([^,]*)$/, ' and $1')
                           : names.slice(0, 2).join(', ') + ' and ' + (names.length - 2) + ' more';
}
const DOW_WORD = {mon: 'Mon', tue: 'Tue', wed: 'Wed', thu: 'Thu', fri: 'Fri'};
function newsDaysWord(C){
  const on = Object.keys(DOW_WORD).filter(k => (C.cuDow || {})[k]);
  if (on.length === 5) return 'any weekday';
  if (!on.length) return 'no weekday (tick at least one)';
  return on.map(k => DOW_WORD[k]).join(', ');
}
/* the rule in one plain sentence, so what the settings add up to is never a guess */
function newsRuleSentence(C){
  const dir = {random: 'A coin picks long or short', long: 'Go long', short: 'Go short'}[C.cuDir];
  const ids = Object.keys(C.cuNews || {}).filter(k => C.cuNews[k]);
  const hold = C.cuHold ? 'hold ' + C.cuHold + ' min' : 'hold to the Flat by time (' + hhmm(ST.exitMin) + ')';
  const mode = {important: 'the most important', first: 'the first', last: 'the last',
                every: 'every one'}[C.cuNewsMode];
  let what;
  if (!ids.length) what = 'at ' + hhmm(C.cuEntryMin) + ' ET';
  else if (newsAround(C)) what = offsetWords(newsOffsetMin(C)) + ' of ' + newsNames(ids) +
    (ids.length > 1 ? ' (' + mode + ' of them on a day with several)' : '');
  else what = 'at ' + hhmm(C.cuEntryMin) + ' ET, ' + (C.cuNewsSkip ? 'except' : 'only') +
    ' on days with ' + newsNames(ids);
  return dir + ' ' + what + ', on ' + newsDaysWord(C) + '; stop and target from Trade below; ' + hold + '.';
}
function newsUpcoming(C, n){
  const ids = C.cuNews || {}, out = [];
  for (const e of NEWSCAL.events) if (e.scheduled && ids[e.catId]) out.push(e);
  out.sort((a, b) => a.date < b.date ? -1 : a.date > b.date ? 1 : (a.etMinute || 0) - (b.etMinute || 0));
  return out.slice(0, n);
}
const nwStat = (v, l) => '<div class="nwstat"><b>' + v + '</b><span>' + l + '</span></div>';
/* the live preview under the news controls: the rule in words, what it adds up to over
   the run's span, anything that will silently stop it trading, and what is coming up */
function newsStats(C){
  const st = {anchors: 0, moved: 0, none: 0, noDay: 0, slots: {}, timedDays: {}};
  buildNewsSides(C, st);
  return st;
}
/* the loaded hours, from the longest session in the span (the first one may be a short day) */
function newsHours(){
  const [lo, hi] = newsSpan();
  const full = BASE.sessions.filter(S => S.day >= lo && S.day <= hi)
    .reduce((x, y) => (!x || y.b - y.a > x.b - x.a ? y : x), null);
  return full ? hhmm(BASE.mins[full.a]) + '\u2013' + hhmm(BASE.mins[full.b]) : 'none';
}
/* what the No-bar choice did, right under it: the reason a release traded at the open, or
   did not trade at all, is never left for the reader to find at the bottom of the panel */
function newsNoBarHTML(C, st){
  const hours = newsHours(), trade = Object.keys(st.slots).length, skipped = st.none - st.noDay;
  /* a release on a day the tape has no session for (closed, or not in the file) has no
     next bar either: said as such, never offered a fix that cannot help */
  const noDay = !st.noDay ? '' : '<p class="nwnote">' + st.noDay.toLocaleString() +
    ' release day' + (st.noDay > 1 ? 's have' : ' has') + ' no bars at all in the loaded tape (e.g. ' +
    st.noDayEx + '), so ' + (st.noDay > 1 ? 'they do' : 'it does') + ' not trade.</p>';
  if (skipped && !trade)
    return '<div class="nwwarn bad"><span><b>Nothing can trade.</b> Every entry time (e.g. ' +
      hhmm(st.outEx) + ') falls where the loaded bars have none: they run ' + hours +
      ' ET. Enter at the next bar that day, or load a file with those hours and turn RTH ' +
      'off in the Data bar.</span><button class="btn" data-cu-nobar="next">Enter at the next bar</button></div>' + noDay;
  if (skipped)
    return '<div class="nwwarn mid"><span>' + skipped.toLocaleString() + ' of ' + st.anchors.toLocaleString() +
      ' entry times fall where the loaded bars (' + hours + ' ET) have none and are skipped.</span>' +
      '<button class="btn" data-cu-nobar="next">Enter at the next bar</button></div>' + noDay;
  if (st.moved)
    return '<div class="nwwarn ok"><span>' + st.moved.toLocaleString() + ' of ' + st.anchors.toLocaleString() +
      ' entries have no bar at their time (e.g. ' + hhmm(st.moveEx[0]) + ') and are taken at the next bar ' +
      'that day (' + hhmm(st.moveEx[1]) + '): the loaded bars run ' + hours + ' ET, so price has already ' +
      'reacted. For the release itself, load a file with those hours and turn RTH off.</span>' +
      '<button class="btn" data-cu-nobar="skip">Skip them instead</button></div>' + noDay;
  return noDay;
}
function newsPreviewHTML(C){
  const [lo, hi] = newsSpan();
  const any = newsAny(C);
  let out = '<div class="nwprev"><p class="nwrule">' + newsRuleSentence(C) + '</p>';
  if (!any){
    return out + '<p style="font-size:11px;color:var(--ink-faint);margin:0">Tick a release above ' +
      'to trade only on release days, skip them, or time the entry to the release.</p></div>';
  }
  const sess = BASE.sessions.filter(S => S.day >= lo && S.day <= hi);
  const hours = newsHours();
  const dowOk = d => (C.cuDow || {})[DOW_NAMES[Core.dowOf(d)]];
  if (newsAround(C)){
    const st = newsStats(C);
    const rel = newsReleaseDays(C);
    const relDays = Object.keys(rel).filter(d => d >= lo && d <= hi && dowOk(d));
    const trade = Object.keys(st.slots).length, off = st.none;
    const untimed = relDays.filter(d => !st.timedDays[d]).length;
    out += '<div class="nwstats">' + nwStat(relDays.length.toLocaleString(), 'release days in span') +
      nwStat(st.anchors.toLocaleString(), 'entry times') +
      nwStat(trade.toLocaleString(), 'can trade') +
      nwStat(off.toLocaleString(), 'no bar there') + '</div>';
    if (untimed)
      out += '<p class="nwnote">' + untimed.toLocaleString() +
        ' release days have no time the chosen source quality (' +
        NEWS_QUALITY_LABEL[C.cuNewsQuality] + ') accepts, and are left out.</p>';
  } else {
    const rel = newsReleaseDays(C);
    const inSpan = sess.filter(S => dowOk(S.day));
    const hit = inSpan.filter(S => rel[S.day]).length;
    const trades = C.cuNewsSkip ? inSpan.length - hit : hit;
    out += '<div class="nwstats">' + nwStat(inSpan.length.toLocaleString(), 'sessions in span') +
      nwStat(hit.toLocaleString(), 'with a release') +
      nwStat(trades.toLocaleString(), 'days it trades') +
      nwStat(hhmm(C.cuEntryMin), 'entry, ET') + '</div>';
    if (inSpan.length && !inSpan.some(S => anchorBar(S, C.cuEntryMin, 'skip') >= 0))
      out += '<div class="nwwarn bad"><span><b>Nothing can trade.</b> The entry time ' + hhmm(C.cuEntryMin) +
        ' is outside the loaded bars (' + hours + ' ET).</span></div>';
  }
  if (C === ST)
      out += '<div class="szbar"><span class="lbl">Chart</span>' +
        '<button class="btn' + (ST.cuShowMarks ? ' on' : '') + '" data-cu-marks>Show releases on the chart</button>' +
        '<span class="nwhint">dotted lines on the bar each release landed in</span></div>';
  const up = newsUpcoming(C, 5);
  if (up.length){
    const offMin = newsAround(C) ? newsOffsetMin(C) : null;
    out += '<div class="nwuphead">Coming up (published schedule)</div>' + up.map(e => {
      const wd = DOW_WORD[DOW_NAMES[Core.dowOf(e.date)]] || '';
      const t = e.etMinute == null ? 'time tba' : hhmm(e.etMinute);
      const entry = offMin === null || e.etMinute == null ? '' :
        ' <span style="color:var(--accent)">\u2192 entry ' + hhmm(((e.etMinute - offMin) % 1440 + 1440) % 1440) +
        (C.cuNoBar === 'next' ? ' (or the next bar)' : '') + '</span>';
      return '<div class="nwup"><span>' + wd + ' ' + e.date + '</span><span>' + t + '</span><span>' +
        e.eventName + entry + '</span></div>';
    }).join('');
  }
  return out + '</div>';
}
function customEntryHTML(C){
  const dow = C.cuDow || {};
  const dowLabels = [['mon', 'Mon'], ['tue', 'Tue'], ['wed', 'Wed'], ['thu', 'Thu'], ['fri', 'Fri']];
  const checked = C.cuNews || {};
  const ids = Object.keys(checked).filter(k => checked[k]);
  const any = ids.length > 0, around = newsAround(C);
  const cnt = newsCounts(C);
  const cats = NEWSCAL.categories.slice().sort((a, b) => a.priorityRank - b.priorityRank);
  const grouped = {};
  cats.forEach(c => { const g = newsCatGroup(c.name); (grouped[g] || (grouped[g] = [])).push(c); });
  const btn = (on, attr, label, title) => '<button class="btn' + (on ? ' on' : '') + '" ' + attr +
    (title ? ' title="' + title + '"' : '') + '>' + label + '</button>';
  const off = C.cuNewsOffset;
  const hint = t => '<span class="nwhint">' + t + '</span>';
  let out = '<h3>Custom entry</h3>' +
    '<div class="szbar"><span class="lbl">Days</span><span class="seg">' +
    dowLabels.map(([k, l]) => btn(dow[k], 'data-cu-dow="' + k + '"', l)).join('') + '</span></div>' +
    '<div class="szbar"><span class="lbl">Direction</span><span class="seg">' +
    [['random', 'Coin'], ['long', 'Long'], ['short', 'Short']].map(([v, l]) =>
      btn(C.cuDir === v, 'data-cu-dir="' + v + '"', l)).join('') + '</span></div>' +
    (around ? '' :
      '<div class="szbar"><span class="lbl">Entry time</span>' +
      '<input type="time" id="cuEntryMin" value="' + hhmm(C.cuEntryMin) + '" step="60" style="width:92px">' +
      hint(any ? 'ET, on the days the news choice below allows' : 'ET, every chosen weekday') + '</div>') +
    '<div class="szbar"><span class="lbl">Hold</span><span class="seg">' +
    btn(C.cuHold === null, 'data-cu-hold=""', 'To Flat by') +
    [5, 15, 30, 60].map(m => btn(C.cuHold === m, 'data-cu-hold="' + m + '"', m + 'm')).join('') + '</span>' +
    '<input type="number" id="cuHoldMin" min="1" step="1" placeholder="min" value="' +
    (C.cuHold && [5, 15, 30, 60].indexOf(C.cuHold) < 0 ? C.cuHold : '') + '" style="width:58px">' +
    hint('each trade closes this long after its own entry, or at the stop, target or Flat by first') + '</div>' +
    '<h3>News filter &amp; timing</h3><div class="nwbox">' +
    '<div class="nwstep"><i>1</i>Which releases</div>' +
    '<div class="szbar" style="margin-top:0"><span class="lbl">Quick pick</span>' +
    NEWS_PRESETS.map(p => btn(false, 'data-cu-preset="' + p[0] + '"', p[1], p[2])).join('') +
    (any ? btn(false, 'data-cu-preset="clear"', 'Clear') : '') + '</div>' +
    (any ? '<div class="nwchips">' + ids.map(id => '<span class="nwchip">' + (NEWS_CAT[id] || {name: id}).name +
      '<button data-cu-unpick="' + id + '" title="remove">\u00d7</button></span>').join('') + '</div>'
         : '<p class="nwnote">No release picked: the entry above trades every chosen weekday.</p>') +
    '<input type="search" id="cuNewsQ" class="nwsearch" placeholder="Search releases (CPI, claims, ISM\u2026)" value="' +
    NEWS_UI.q.replace(/"/g, '&quot;') + '">' +
    '<div class="nwlist">' +
    NEWS_GROUP_ORDER.filter(g => grouped[g]).map(g => {
      const inG = grouped[g], picked = inG.filter(c => checked[c.id]).length;
      const q = NEWS_UI.q.toLowerCase(), hit = c => !q || c.name.toLowerCase().indexOf(q) >= 0;
      const open = q || picked || NEWS_UI.open[g];
      return '<details data-cu-group="' + g + '"' + (open ? ' open' : '') +
        (inG.some(hit) ? '' : ' style="display:none"') + '><summary><span>' + g +
        '</span><span>' + (picked ? picked + ' of ' : '') + inG.length + '</span></summary>' +
        inG.map(c => {
          const n = cnt.n[c.id] || 0, t = cnt.timed[c.id] || 0;
          return '<label class="nwrow' + (checked[c.id] ? ' on' : '') + '" data-cu-name="' +
            c.name.toLowerCase().replace(/"/g, '') + '"' + (hit(c) ? '' : ' style="display:none"') +
            ' title="' + (c.note ? c.note.replace(/"/g, '') : '') + '">' +
            '<input type="checkbox" data-cu-news="' + c.id + '"' + (checked[c.id] ? ' checked' : '') + '>' +
            '<span>' + c.name + (c.note ? ' <span style="color:var(--accent)" title="' +
              c.note.replace(/"/g, '') + '">\u24d8</span>' : '') + '</span>' +
            '<span class="t">' + (c.typicalEtMinute == null ? 'no time' : hhmm(c.typicalEtMinute)) + '</span>' +
            '<span class="n" title="releases in the span; with a usable time">' + n +
              (n && t < n ? ' \u00b7 ' + t + ' timed' : '') + '</span></label>';
        }).join('') + '</details>';
    }).join('') + '</div>' +
    '<div class="nwstep"><i>2</i>How to use them</div>' +
    '<div class="szbar" style="margin-top:0"><span class="seg">' +
    btn(any && !around && !C.cuNewsSkip, 'data-cu-use="only"' + (any ? '' : ' disabled'), 'Only release days') +
    btn(any && !around && C.cuNewsSkip, 'data-cu-use="skip"' + (any ? '' : ' disabled'), 'Skip release days') +
    btn(around, 'data-cu-use="around"' + (any ? '' : ' disabled'), 'Time the entry to the release') +
    '</span></div>' +
    (!around ? (any ? '<p class="nwnote">' + (C.cuNewsSkip ? 'Trades at the entry time on every ' +
        'chosen weekday except the days one of these was released.' : 'Trades at the entry time, ' +
        'only on days one of these was released (the day is enough; the time is not needed).') + '</p>' : '')
     : '<div class="szbar"><span class="lbl nwlab">Enter before</span>' +
      '<span class="seg">' + [60, 30, 15, 10, 5, 1].map(m => btn(off === m, 'data-cu-news-offset="' + m + '"', m + 'm')).join('') +
      '</span>' + btn(off === 0, 'data-cu-news-offset="0"', 'At the release') + '</div>' +
      '<div class="szbar"><span class="lbl nwlab">Enter after</span>' +
      '<span class="seg">' + [1, 5, 15, 30].map(m => btn(off === -m, 'data-cu-news-offset="-' + m + '"', m + 'm')).join('') +
      '</span>' + btn(off === 'custom', 'data-cu-news-offset="custom"', 'Custom\u2026') + '</div>' +
      (off !== 'custom' ? '' :
        '<div class="szbar"><span class="lbl nwlab">Custom</span><input type="number" id="cuNewsOffsetCustom" value="' +
        C.cuNewsOffsetCustom + '" min="0" step="1" style="width:60px"><span class="lbl">min</span><span class="seg">' +
        btn(!C.cuNewsCustomAfter, 'data-cu-custom-dir="before"', 'before') +
        btn(C.cuNewsCustomAfter, 'data-cu-custom-dir="after"', 'after') + '</span></div>') +
      '<div class="szbar"><span class="lbl nwlab">Several that day</span><select id="cuNewsMode" style="font-size:11px">' +
      [['important', 'Most important one'], ['first', 'First one'], ['last', 'Last one'],
       ['every', 'Every one (one trade each)']].map(([v, l]) =>
        '<option value="' + v + '"' + (C.cuNewsMode === v ? ' selected' : '') + '>' + l + '</option>').join('') +
      '</select></div><div class="szbar"><span class="lbl nwlab">Source quality</span>' +
      '<select id="cuNewsQuality" style="font-size:11px">' +
      ['any', 'verified', 'cross'].map(v => '<option value="' + v + '"' + (C.cuNewsQuality === v ? ' selected' : '') +
        '>' + NEWS_QUALITY_LABEL[v] + '</option>').join('') + '</select></div>' +
      '<div class="szbar"><span class="lbl nwlab">No bar at that time</span><span class="seg">' +
      btn(C.cuNoBar !== 'next', 'data-cu-nobar="skip"', 'Skip the day') +
      btn(C.cuNoBar === 'next', 'data-cu-nobar="next"', 'Enter at the next bar') + '</span>' +
      hint('e.g. 08:30 data on a 09:30\u201316:00 tape') + '</div>' + newsNoBarHTML(C, newsStats(C)) +
      '<p class="nwnote">Times are New York. Only an occurrence whose time the chosen source quality ' +
      'accepts is used: \u201cany source\u201d takes one source\u2019s time, \u201cverified\u201d needs ' +
      'two sources to agree or the agency\u2019s own schedule. A day whose sources disagree is never ' +
      'timed. An entry skipped because the last trade is still open shows in the ledger as ' +
      '\u201cnot taken \u2014 position open at next news release\u201d. Calendar: ' +
      NEWSCAL.ffCoverage.join(' to ') + ' (Forex Factory), Investing.com ' +
      NEWSCAL.investingCoverage.join(' to ') + '; published schedule to ' +
      ((NEWSCAL.ffLive || {}).scheduledTo || '\u2014') + '.</p>') +
    newsPreviewHTML(C) + '</div>';
  return out;
}

function strategyHTML(){
  const C = stageObj(), d = STRATS[C.key], fundedView = C === ST.funded;
  const num = (id, v, st) => '<input type="number" id="' + id + '" value="' + v +
    '" step="' + (st || 1) + '" style="width:92px">';
  const row = stRow;
  const usd = C.riskMode === 'usd';
  const ends = tapeEnds();
  /* the preset lights up while $ per point and commission still stand */
  const onInst = z => C.pointValue === z.pv && C.commission === z.comm;
  const inst = instOf(C);
  const date = (id, v) => '<input type="date" id="' + id + '" value="' + v + '" min="' + ends[0] +
    '" max="' + ends[1] + '" style="width:130px">';
  let out = '<h2>Strategy</h2>' +
    '<p>Pick a strategy and it is <b>regenerated from the loaded bars</b> under your ' +
    'balance and the firm\'s rules. It is not a rescaled copy of an existing trade list: ' +
    'the daily cap and the drawdown are fixed in dollars, so changing size changes where ' +
    'each trade <em>exits</em>, not just what it earns. Every change you make here goes ' +
    'straight onto the chart behind this panel \u2014 the trade boxes, the equity curve and ' +
    'the ledger \u2014 and the chart still scrolls and zooms while it is open. The seed stays ' +
    'put until you ask for a new one, so what moves is the rule, not the coin.</p>' +
    '<div id="stHero" class="stpin">' + heroHTML() + '</div>' +
    /* ---- the account: shared by both stages ---- */
    '<h3>The account \u00b7 both stages</h3>' +
    '<div class="szbar"><span class="lbl">Preset</span>' +
    Object.keys(LUCID_PRESETS).map(k => {
      const p = LUCID_PRESETS[k];
      return '<button class="btn' + (lucidPresetOn(k) ? ' on' : '') + '" data-lucid="' + k +
        '" title="Fill balance, target, daily cap, drawdown, payout and ticket with the ' +
        p.label + ' rules: ' + money0(p.balance) + ' start, ' + money0(p.target) +
        ' to pass, ' + money0(p.dailyCap) + ' a day, ' + money0(p.trailDD) +
        ' trailing drawdown, ' + money0(p.payoutDraw) + ' a payout, ' + money0(p.ticket) +
        ' a ticket">' + p.label + '</button>';
    }).join('') +
    '<span style="color:var(--ink-faint);font-size:9.5px">sets the account block below; the ' +
    'strategy itself (entry, size, stop) is untouched</span></div>' +
    '<div class="szbar"><span class="lbl">Span</span>' +
    SPANS.map(s => '<button class="btn" data-span="' + s[1] + '">' + s[0] + '</button>').join('') +
    '<span class="stpair"><span class="lbl">from</span>' + date('stFrom', ST.from) +
    '<span class="lbl">to</span>' + date('stTo', ST.to) + '</span></div>' +
    '<div class="szbar"><span class="lbl">Seed</span><span class="stpair">' + num('stSeed', ST.seed) +
    '<button class="btn" id="stDice" title="draw a fresh, unpredictable seed">' +
    '\ud83c\udfb2 New seed</button></span>' +
    '<span style="color:var(--ink-faint);font-size:9.5px">the coin flips are seeded so a run ' +
    'is reproducible; deterministic strategies ignore it</span></div>' +
    '<div class="setgrid"><div>' +
    row('Starting balance', num('stBal', ST.balance, 100),
        'what a ticket buys; a passed account is reset to it when it becomes funded') +
    row('Slippage (points per side)', num('stSlip', ST.slippage, 0.05),
        'charged on the fill and again on the exit, both stages') +
    (inst
      ? '<div class="szbar" style="margin:0 0 6px"><span class="lbl">' + inst.key + '</span>' +
        inst.slip.map((v, i) => '<button class="btn' + (ST.slippage === v ? ' on' : '') +
          '" data-slip="' + v + '" title="' + (v / inst.tick).toFixed(1).replace('.0', '') + ' tick' +
          (v === inst.tick ? '' : 's') + ' a side">' + SLIP_NAMES[i] + ' ' + v + '</button>').join('') +
        '<span style="color:var(--ink-faint);font-size:9.5px">assumptions, in ticks: hover a ' +
        'button; the box takes any figure</span></div>'
      : '<div class="szbar" style="margin:0 0 6px"><span style="color:var(--ink-faint);font-size:9.5px">' +
        'pick an instrument below to see its three slippage defaults</span></div>') +
    row('Cost of one evaluation', num('stTick', ST.ticket, 5), 'the ticket, paid once per account bought') +
    row('Flat by', '<input type="time" id="stFlat" value="' + hhmm(ST.exitMin) +
        '" step="60" style="width:92px">',
        'every trade is closed at this minute; 16:00 is the session close. The last-hour ' +
        'strategies set 15:49 themselves; this box overrides it') +
    row('Trailing drawdown', num('stDD', ST.trailDD, 50),
        'both stages: trails the best END-OF-DAY balance; intraday profit does not move it') +
    row('Freeze the floor this far above the start', num('stFrz', ST.freezeOffset, 25),
        'both stages: once the floor gets here it stops rising') +
    '</div><div>' +
    row('<span class="tag E">EVAL</span> Max per day', num('stCap', ST.dailyCap, 25),
        'the consistency cap: an evaluation day is over once it has booked this') +
    row('<span class="tag E">EVAL</span> Profit to pass', num('stTgt', ST.target, 50),
        'reach the starting balance plus this and the account is funded; it means nothing once funded') +
    row('<span class="tag F">FUNDED</span> Profit to withdraw', num('stPay', ST.payoutAt, 100),
        'measured from the reset starting balance. Each withdrawal takes ' +
        money0(ST.payoutDraw) + ' out, and the next one needs the balance back up here') +
    row('<span class="tag F">FUNDED</span> Withdrawn each time ($)', num('stPayD', ST.payoutDraw, 100),
        'this LEAVES the account balance every payout \u2014 it is not what you are paid, ' +
        'see the split below') +
    row('<span class="tag F">FUNDED</span> Your share of it (%)',
        '<input type="number" id="stPayS" value="' + (ST.payoutSplit * 100) +
        '" step="5" min="0" max="100" style="width:92px">',
        'the profit split. At ' + (ST.payoutSplit * 100) + '% a ' + money0(ST.payoutDraw) +
        ' withdrawal pays you ' + money0(ST.payoutDraw * ST.payoutSplit)) +
    row('<span class="tag F">FUNDED</span> Keep the daily cap',
        '<input type="checkbox" id="stFC"' + (ST.fundedCap !== null ? ' checked' : '') + '>',
        'off, a funded day may run all the way to a withdrawal') +
    '</div></div>' +
    /* ---- the strategy: one stage at a time ---- */
    '<div class="stgbox' + (fundedView ? ' funded' : '') + '">' +
    '<div class="szbar" style="margin-top:0"><span class="lbl">Strategy for</span>' +
    '<button class="btn' + (fundedView ? '' : ' on') + '" data-stage="eval">Evaluation</button>' +
    (ST.funded.same ? '' :
      '<button class="btn' + (fundedView ? ' on' : '') + '" data-stage="funded">Funded</button>') +
    '<label class="stpair" style="margin-left:10px;font-family:var(--mono);font-size:10.5px;' +
    'color:var(--ink-dim);cursor:pointer"><input type="checkbox" id="stDiff"' +
    (ST.funded.same ? '' : ' checked') + '> the funded account trades differently</label></div>' +
    '<p style="color:var(--ink-faint);font-size:11px;margin-top:2px">' +
    (ST.funded.same
      ? 'Everything in this box runs in both stages. Tick the box to give the funded account ' +
        'its own entry, size, risk and target, and loss limit.'
      : (fundedView
          ? '<b style="color:var(--accent)">The funded strategy.</b> It starts the day after an ' +
            'evaluation passes, from the reset starting balance, and runs until the account is lost.'
          : '<b>The evaluation strategy.</b> It runs from the day a ticket is bought until the ' +
            'account passes or is lost.')) + '</p>' +
    '<h3>Entry</h3>' +
    STRAT_GROUPS.map(g => '<div class="szbar"><span class="lbl">' + g.label + '</span>' +
      g.keys.map(k => '<button class="btn' + (C.key === k ? ' on' : '') +
        '" data-st="' + k + '">' + STRATS[k].label + '</button>').join('') + '</div>').join('') +
    '<p style="color:var(--ink-dim);font-size:11.5px">' + d.note + '</p>' +
    '<p style="color:var(--ink-faint);font-size:11px"><b>Exits, the same for every entry rule:</b> a ' +
    'trade is filled at the open of its minute plus your slippage (' + ST.slippage + ' pt) against ' +
    'you, and closes at whichever comes first \u2014 the stop (the points set below, or nearer ' +
    'if the account cannot afford them: then the drawdown floor closes it), the target (the ' +
    'points set below, or nearer if it would carry the day past the daily cap), or the Flat by ' +
    'minute (16:00 unless set, 15:49 for the last-hour strategies). After each trade: a day that ' +
    'has booked the cap is over; a day that has lost the ' +
    'loss limit is over; a balance that touches the floor is a lost account, and a new ' +
    'evaluation is bought that carries on from the next slot. Reaching the profit target ' +
    'passes: the account is funded and trades on from the starting balance.</p>' +
    '<div class="szbar"><span class="lbl">Loaded</span>' +
    '<span class="stat">' + (LOADED_SYM || 'not recognised from the file name') + '</span>' +
    (inst && LOADED_SYM && inst.key !== LOADED_SYM
      ? '<b style="color:var(--down)">MISMATCH \u2014 priced as ' + inst.key + ', the loaded bars ' +
        'look like ' + LOADED_SYM + '</b>'
      : '<span style="color:var(--ink-faint);font-size:9.5px">guessed from the file name when it ' +
        'was loaded; the Instrument row below was set to match automatically</span>') + '</div>' +
    '<div class="szbar"><span class="lbl">Instrument</span>' +
    INSTRUMENTS.map((z, i) => {
      const allowed = instAllowed(z, d);
      const why = allowed ? (z.note + ': $' + z.pv + ' a point, tick ' + z.tick +
        ', Lucid $' + z.comm.toFixed(2) + ' a side, normal slippage ' + z.slip[1] + ' pt')
        : 'this system\u2019s entries were fitted on ' + d.markets.join('/') + ' only \u2014 ' +
          'picking ' + z.key + ' would price its stored decisions off a market it never saw';
      return '<button class="btn' + (onInst(z) ? ' on' : '') + '" data-inst="' + i + '"' +
        (allowed ? '' : ' disabled') + ' title="' + why + '">' + z.key + '</button>';
    }).join('') +
    (d.markets
      ? '<span style="color:var(--ink-faint);font-size:9.5px">this entry rule is a stored replay ' +
        'fitted on ' + d.markets.join('/') + ' (and their micros); the rest are dimmed, not deleted' +
        '</span>'
      : '<span style="color:var(--ink-faint);font-size:9.5px">sets $ per point, Lucid\u2019s commission ' +
        'and normal slippage; match it to the bars you loaded</span>') + '</div>' +
    '<div class="szbar"><span class="lbl">Contracts</span>' +
    CONTRACTS.map(n => '<button class="btn' + (C.contracts === n ? ' on' : '') +
      '" data-con="' + n + '">' + n + '</button>').join('') + '</div>' +
    (!d.live ? '' :
      '<h3>Model inputs, live</h3>' +
      '<div class="szbar"><span class="lbl">Side</span>' +
      '<button class="btn' + (C.boSide === 'long' ? ' on' : '') + '" data-bo-side="long">Long</button>' +
      '<button class="btn' + (C.boSide === 'short' ? ' on' : '') + '" data-bo-side="short">Short</button>' +
      '<span style="color:var(--ink-faint);font-size:9.5px">one side at a time; the published ' +
      'system is ' + (d.live === 'hitter' ? 'long only' : 'long and short together') + '</span></div>' +
      (d.live === 'hitter'
        ? '<div class="setgrid"><div>' +
          row('Lookback N (30-min closes)', num('stBoN', C.boN, 1),
              'the buy-stop (or sell-stop) sits at the highest (lowest) close of the last N bars') +
          row('ADX period', num('stBoAdxP', C.boAdxPeriod, 1), '30-minute bars, RMA-smoothed') +
          '</div><div>' +
          row('ADX threshold', num('stBoAdxT', C.boAdxThreshold, 0.5)) +
          '<div class="szbar" style="margin-top:2px"><span class="lbl">Direction</span>' +
          '<button class="btn' + (C.boAdxDir === 'below' ? ' on' : '') + '" data-bo-adxdir="below">Below</button>' +
          '<button class="btn' + (C.boAdxDir === 'above' ? ' on' : '') + '" data-bo-adxdir="above">Above</button>' +
          '<span style="color:var(--ink-faint);font-size:9.5px">below: only after a quiet market; ' +
          'above: only into one already trending</span></div>' +
          '</div></div>'
        : '<div class="setgrid"><div>' +
          row('Range fraction', num('stBoFrac', C.boFraction, 0.5),
              'stop = open plus-or-minus fraction x |open - low|') +
          row('DMI period', num('stBoDxP', C.boDxPeriod, 1), '30-minute bars, unsmoothed DX') +
          '</div><div>' +
          row('DMI shift (bars back)', num('stBoDxS', C.boDxShift, 1),
              'reads the DMI reading from this many 30-minute bars before the signal bar') +
          row('DMI threshold', num('stBoDxT', C.boDxThreshold, 1)) +
          '</div></div>')) +
    (C.key !== 'custom' ? '' : customEntryHTML(C)) +
    '<div class="setgrid"><div>' +
    '<h3>Trade</h3>' +
    '<div class="szbar" style="margin-top:2px"><span class="lbl">Units</span>' +
    '<button class="btn' + (usd ? '' : ' on') + '" data-rm="pts">Points</button>' +
    '<button class="btn' + (usd ? ' on' : '') + '" data-rm="usd">Dollars</button></div>' +
    (usd
      ? row('Risk per trade ($)', num('stRisk', C.riskUSD, 25),
            'stop = risk / (contracts x $ per point)') +
        (d.noTarget ? row('Target per trade ($)', '<span class="lbl">none</span>',
                          'this system has no profit target; only the stop, the close and the account end a trade')
                    : row('Target per trade ($)', num('stTarget', C.targetUSD, 25),
                          'capped by whatever the day still allows'))
      : row('Stop (points)', num('stStop', C.stopPts)) +
        (d.noTarget ? row('Reward to risk', '<span class="lbl">none</span>',
                          'this system has no profit target; only the stop, the close and the account end a trade')
                    : row('Reward to risk', num('stRR', C.rr, 0.1),
                          'target = R:R x stop, capped by whatever the day still allows'))) +
    row('Stop trading for the day after losing', num('stLoss', C.dailyLoss, 25),
        '0 = no limit. Ends the day; it does not blow the account') +
    '</div><div>' +
    '<h3>Size and costs</h3>' +
    row('Contracts', num('stCon', C.contracts)) +
    row('$ per point', num('stPV', C.pointValue, 0.5),
        'NQ 20, MNQ 2, ES 50, MES 5, RTY 50, M2K 5, CL 1000, MCL 100, GC 100, MGC 10, YM 5, MYM 0.5, SI 5000, SIL 1000, HG 25000, HE 400, NKD 5') +
    row('Commission per contract per side', num('stComm', C.commission, 0.05),
        'presets carry Lucid Trading\u2019s table; put your firm\u2019s figure here') +
    '</div></div>' +
    '</div>' +
    '<div id="stResult">' + resultHTML() + '</div>' +
    '<div id="stEns">' + ensembleHTML() + '</div>';
  return out + '<div style="margin-top:12px;display:flex;gap:6px">' +
    '<button class="btn on" id="stRun">Close and go to the first trade</button>' +
    '<button class="btn" id="stClose">Close</button></div>';
}
function openStrategy(){
  const sh = document.getElementById('sheet');
  sh.classList.remove('sz');
  sh.innerHTML = strategyHTML();
  document.getElementById('modal').classList.add('on', 'peek');
  bindStrategy();
}
function closeStrategy(){
  document.getElementById('modal').classList.remove('on', 'peek');
}
function bindStrategy(){
  const sh = document.getElementById('sheet');
  const $ = id => document.getElementById(id);
  const redraw = () => { sh.innerHTML = strategyHTML(); bindStrategy(); };
  /* A full redraw rebuilds every input, so it is reserved for changes that
     alter which inputs exist or what several of them say. Typing into one
     field goes through stLive() and touches only the result block. */
  const C = stageObj();
  sh.querySelectorAll('button[data-stage]').forEach(b => b.onclick = () => {
    ST.stageView = b.dataset.stage; redraw();
  });
  sh.querySelectorAll('button[data-lucid]').forEach(b => b.onclick = () => {
    applyLucidPreset(b.dataset.lucid);
    STRES = null; redraw();
  });
  const diff = $('stDiff');
  if (diff) diff.onchange = () => {
    ST.funded.same = !diff.checked;
    /* start the funded strategy from a copy of the evaluation's, then diverge */
    if (diff.checked) STAGE_KEYS.forEach(k => { ST.funded[k] = ST[k]; });
    ST.stageView = diff.checked ? 'funded' : 'eval';
    STRES = null; redraw();
  };
  sh.querySelectorAll('button[data-st]').forEach(b => b.onclick = () => {
    C.key = b.dataset.st;
    snapMarket(C, STRATS[C.key], true);
    STRES = null; redraw();
  });
  sh.querySelectorAll('button[data-inst]').forEach(b => b.onclick = () => {
    const z = INSTRUMENTS[+b.dataset.inst];
    C.pointValue = z.pv; C.commission = z.comm;
    ST.slippage = z.slip[1];   /* the account's, shared by both stages: one tape */
    STRES = null; redraw();
  });
  sh.querySelectorAll('button[data-slip]').forEach(b => b.onclick = () => {
    ST.slippage = +b.dataset.slip; STRES = null; redraw();
  });
  sh.querySelectorAll('button[data-con]').forEach(b => b.onclick = () => {
    C.contracts = +b.dataset.con; STRES = null; redraw();
  });
  sh.querySelectorAll('button[data-rm]').forEach(b => b.onclick = () => {
    setRiskMode(b.dataset.rm, C); STRES = null; redraw();
  });
  /* the preset that matches the dates lights up; none does after a hand edit */
  const syncSpan = () => sh.querySelectorAll('button[data-span]').forEach(b => {
    b.classList.toggle('on', ST.from === spanFrom(+b.dataset.span) && !ST.to);
  });
  syncSpan();
  sh.querySelectorAll('button[data-span]').forEach(b => b.onclick = () => {
    ST.from = spanFrom(+b.dataset.span); ST.to = '';
    $('stFrom').value = ST.from; $('stTo').value = ST.to;
    syncSpan(); stLive();
  });
  ['stFrom', 'stTo'].forEach((id, i) => {
    const el = $(id); if (!el) return;
    el.onchange = () => { ST[i ? 'to' : 'from'] = el.value; syncSpan(); stLive(); };
  });
  /* stage-specific fields write to the stage being edited; the rest to ST */
  const bindNum = (id, key, min, obj) => {
    const el = $(id); if (!el) return;
    const O = obj || ST;
    el.oninput = () => {
      const v = parseFloat(el.value);
      if (!isFinite(v) || v < min) return;
      O[key] = v; stLive();
    };
    el.onchange = () => {
      const v = parseFloat(el.value);
      if (!isFinite(v) || v < min) el.value = O[key];
    };
  };
  bindNum('stStop', 'stopPts', 0.25, C); bindNum('stRR', 'rr', 0.01, C);
  bindNum('stRisk', 'riskUSD', 1, C); bindNum('stTarget', 'targetUSD', 1, C);
  bindNum('stSeed', 'seed', 0); bindNum('stBal', 'balance', 1);
  bindNum('stCon', 'contracts', 1, C); bindNum('stPV', 'pointValue', 0.01, C);
  bindNum('stComm', 'commission', 0, C); bindNum('stSlip', 'slippage', 0);
  bindNum('stDD', 'trailDD', 1); bindNum('stFrz', 'freezeOffset', 0);
  bindNum('stCap', 'dailyCap', 1); bindNum('stLoss', 'dailyLoss', 0, C);
  bindNum('stTgt', 'target', 1);
  bindNum('stPay', 'payoutAt', 1); bindNum('stTick', 'ticket', 0);
  bindNum('stPayD', 'payoutDraw', 1);
  bindNum('stBoN', 'boN', 1, C); bindNum('stBoAdxP', 'boAdxPeriod', 2, C);
  bindNum('stBoAdxT', 'boAdxThreshold', 0, C);
  bindNum('stBoFrac', 'boFraction', 0.01, C); bindNum('stBoDxP', 'boDxPeriod', 2, C);
  bindNum('stBoDxS', 'boDxShift', 0, C); bindNum('stBoDxT', 'boDxThreshold', 0, C);
  sh.querySelectorAll('button[data-bo-side]').forEach(b => b.onclick = () => {
    C.boSide = b.dataset.boSide; STRES = null; redraw();
  });
  sh.querySelectorAll('button[data-bo-adxdir]').forEach(b => b.onclick = () => {
    C.boAdxDir = b.dataset.boAdxdir; STRES = null; redraw();
  });
  sh.querySelectorAll('button[data-cu-dow]').forEach(b => b.onclick = () => {
    C.cuDow[b.dataset.cuDow] = !C.cuDow[b.dataset.cuDow]; STRES = null; redraw();
  });
  sh.querySelectorAll('button[data-cu-dir]').forEach(b => b.onclick = () => {
    C.cuDir = b.dataset.cuDir; STRES = null; redraw();
  });
  const cuEntryMin = $('cuEntryMin');
  if (cuEntryMin) cuEntryMin.onchange = () => {
    const m = cuEntryMin.value.match(/^(\d{1,2}):(\d{2})$/);
    if (!m) return;
    C.cuEntryMin = +m[1] * 60 + +m[2]; STRES = null; redraw();
  };
  sh.querySelectorAll('button[data-cu-hold]').forEach(b => b.onclick = () => {
    C.cuHold = b.dataset.cuHold === '' ? null : +b.dataset.cuHold; STRES = null; redraw();
  });
  const cuHoldMin = $('cuHoldMin');
  if (cuHoldMin) cuHoldMin.onchange = () => {
    const v = parseInt(cuHoldMin.value, 10);
    C.cuHold = isFinite(v) && v >= 1 ? v : null; STRES = null; redraw();
  };
  sh.querySelectorAll('input[data-cu-news]').forEach(el => el.onchange = () => {
    if (el.checked) C.cuNews[el.dataset.cuNews] = true; else delete C.cuNews[el.dataset.cuNews];
    STRES = null; redraw();
  });
  sh.querySelectorAll('button[data-cu-unpick]').forEach(b => b.onclick = () => {
    delete C.cuNews[b.dataset.cuUnpick]; STRES = null; redraw();
  });
  sh.querySelectorAll('button[data-cu-preset]').forEach(b => b.onclick = () => {
    const p = NEWS_PRESETS.filter(x => x[0] === b.dataset.cuPreset)[0];
    C.cuNews = {};
    if (p) newsPresetIds(p).forEach(id => { C.cuNews[id] = true; });
    STRES = null; redraw();
  });
  /* the search filters the rows in place -- no redraw, so the box keeps its focus */
  const cuNewsQ = $('cuNewsQ');
  if (cuNewsQ) cuNewsQ.oninput = () => {
    NEWS_UI.q = cuNewsQ.value.trim();
    const q = NEWS_UI.q.toLowerCase();
    sh.querySelectorAll('details[data-cu-group]').forEach(d => {
      let shown = 0;
      d.querySelectorAll('label[data-cu-name]').forEach(l => {
        const hit = !q || l.dataset.cuName.indexOf(q) >= 0;
        l.style.display = hit ? '' : 'none'; if (hit) shown++;
      });
      d.style.display = shown ? '' : 'none';
      if (q) d.open = true;
    });
  };
  /* remembered only on a real click (a toggle event also fires when a redraw opens a
     group because it holds a pick or matches the search) */
  sh.querySelectorAll('details[data-cu-group] > summary').forEach(sm => sm.onclick = () => {
    const d = sm.parentNode; NEWS_UI.open[d.dataset.cuGroup] = !d.open;
  });
  sh.querySelectorAll('button[data-cu-use]').forEach(b => b.onclick = () => {
    const u = b.dataset.cuUse;
    if (u === 'around'){ if (C.cuNewsOffset === null) C.cuNewsOffset = NEWS_UI.lastOffset; }
    else {
      if (C.cuNewsOffset !== null) NEWS_UI.lastOffset = C.cuNewsOffset;
      C.cuNewsOffset = null; C.cuNewsSkip = u === 'skip';
    }
    STRES = null; redraw();
  });
  const cuNewsMode = $('cuNewsMode');
  if (cuNewsMode) cuNewsMode.onchange = () => { C.cuNewsMode = cuNewsMode.value; STRES = null; redraw(); };
  const cuNewsQuality = $('cuNewsQuality');
  if (cuNewsQuality) cuNewsQuality.onchange = () => {
    C.cuNewsQuality = NEWS_QUALITY[cuNewsQuality.value] ? cuNewsQuality.value : 'any'; STRES = null; redraw();
  };
  sh.querySelectorAll('button[data-cu-news-offset]').forEach(b => b.onclick = () => {
    const v = b.dataset.cuNewsOffset;
    C.cuNewsOffset = v === '' ? null : (v === 'custom' ? 'custom' : +v);
    STRES = null; redraw();
  });
  sh.querySelectorAll('button[data-cu-custom-dir]').forEach(b => b.onclick = () => {
    C.cuNewsCustomAfter = b.dataset.cuCustomDir === 'after'; STRES = null; redraw();
  });
  sh.querySelectorAll('button[data-cu-marks]').forEach(b => b.onclick = () => {
    ST.cuShowMarks = !ST.cuShowMarks; redraw(); render();
  });
  sh.querySelectorAll('button[data-cu-nobar]').forEach(b => b.onclick = () => {
    C.cuNoBar = b.dataset.cuNobar === 'next' ? 'next' : 'skip'; STRES = null; redraw();
  });
  const cuNewsOffsetCustom = $('cuNewsOffsetCustom');
  if (cuNewsOffsetCustom) cuNewsOffsetCustom.onchange = () => {
    const v = parseInt(cuNewsOffsetCustom.value, 10);
    if (isFinite(v) && v >= 0 && v < 1440){ C.cuNewsOffsetCustom = v; STRES = null; redraw(); }
    else cuNewsOffsetCustom.value = C.cuNewsOffsetCustom;
  };
  const stPayS = $('stPayS');
  if (stPayS) stPayS.onchange = () => {
    const v = parseFloat(stPayS.value);
    if (!isFinite(v) || v < 0 || v > 100){ stPayS.value = ST.payoutSplit * 100; return; }
    ST.payoutSplit = v / 100; stLive();
  };
  const flat = $('stFlat');
  if (flat) flat.onchange = () => {
    const m = flat.value.match(/^(\d{1,2}):(\d{2})$/);
    if (!m) return;
    const v = +m[1] * 60 + +m[2];
    /* 16:00 or later is the close; before 09:31 makes no sense and is ignored */
    if (v < 571) { flat.value = hhmm(ST.exitMin); return; }
    ST.exitMin = v >= 960 ? 960 : v;
    stLive();
  };
  const fc = $('stFC');
  if (fc) fc.onchange = () => { ST.fundedCap = fc.checked ? ST.dailyCap : null; stLive(); };
  const dice = $('stDice');
  if (dice) dice.onclick = () => {
    ST.seed = (Date.now() ^ (Math.random() * 0xFFFFFFFF)) >>> 0;
    $('stSeed').value = ST.seed; stLive();
  };
  const run = $('stRun');
  if (run) run.onclick = () => {
    closeStrategy();
    if (!STRES) runStrat();
    if (STRES && STRES.trades.length) gotoTrade(0);
  };
  const cl = $('stClose');
  if (cl) cl.onclick = closeStrategy;
  bindEnsemble();
}
guard('bstrat', openStrategy, 'Strategy');

/* ---------------- sizing study ---------------- */
const SZ = {cap: 'nocap', payout: 900};
function szRows(){ return SIZING[SZ.cap]; }
function szSvg(w, h){
  return '<svg viewBox="0 0 ' + w + ' ' + h + '" role="img">';
}
function szEsc(v){ return String(v); }

/* every seed's DISCRETE outcome, drawn as one dot per run. A mean of "0.55
   payouts" cannot happen on any single run; this shows what actually can. */
function szStrip(rows, key, title, note, fmt){
  const W = 560, rowH = 26, PADL = 62, PADR = 14, PADT = 22;
  const H = PADT + rows.length * rowH + 22;
  let lo = Infinity, hi = -Infinity;
  rows.forEach(r => r[key].forEach(v => { if (v < lo) lo = v; if (v > hi) hi = v; }));
  if (!isFinite(lo)) { lo = 0; hi = 1; }
  if (hi === lo) hi = lo + 1;
  const X = v => PADL + (W - PADL - PADR) * (v - lo) / (hi - lo);
  let out = szSvg(W, H);
  for (let t = 0; t <= 4; t++){
    const v = lo + (hi - lo) * t / 4, x = X(v);
    out += '<line x1="' + x + '" y1="' + PADT + '" x2="' + x + '" y2="' + (H - 20) +
           '" stroke="' + cv_('--rule-soft') + '"/>' +
           '<text x="' + x + '" y="' + (H - 7) + '" fill="' + cv_('--ink-faint') +
           '" font-size="9" font-family="' + cv_('--mono') + '" text-anchor="middle">' +
           fmt(v) + '</text>';
  }
  rows.forEach((r, i) => {
    const y = PADT + i * rowH + rowH / 2;
    out += '<text x="' + (PADL - 8) + '" y="' + (y + 3) + '" fill="' + cv_('--ink-dim') +
           '" font-size="9.5" font-family="' + cv_('--mono') + '" text-anchor="end">' +
           r.label + '</text>';
    const vals = r[key].slice().sort((a, b) => a - b);
    const med = medOf(vals);
    out += '<line x1="' + X(vals[0]) + '" y1="' + y + '" x2="' + X(vals[vals.length - 1]) +
           '" y2="' + y + '" stroke="' + cv_('--rule') + '" stroke-width="1"/>';
    /* Group first, then draw EVERY run. Jittering into a handful of fixed
       offsets silently hid most of the distribution: 1 MNQ has 24 runs at zero
       and only 5 dots appeared. Small groups stack in full; a group too tall
       for the row becomes a column carrying its own count, so no run is lost. */
    const counts = {};
    vals.forEach(v => { counts[v] = (counts[v] || 0) + 1; });
    Object.keys(counts).forEach(k => {
      const v = +k, cnt = counts[k], x = X(v);
      const col = v > 0 ? S.col.up : S.col.down;
      if (cnt <= 7){
        for (let j = 0; j < cnt; j++){
          const off = (j - (cnt - 1) / 2) * 2.6;
          out += '<circle cx="' + x + '" cy="' + (y + off) + '" r="2.1" fill="' +
                 col + '" opacity="0.8"/>';
        }
      } else {
        out += '<rect x="' + (x - 1.8) + '" y="' + (y - 8) + '" width="3.6" height="16" rx="1.6"' +
               ' fill="' + col + '" opacity="0.8"/>' +
               '<text x="' + x + '" y="' + (y - 10) + '" fill="' + col +
               '" font-size="8.5" font-family="' + cv_('--mono') +
               '" text-anchor="middle">' + cnt + '</text>';
      }
    });
    out += '<line x1="' + X(med) + '" y1="' + (y - 8) + '" x2="' + X(med) + '" y2="' +
           (y + 8) + '" stroke="' + S.col.accent + '" stroke-width="2"/>';
  });
  return '<div class="szfig"><h4>' + title + '</h4><p>' + note + '</p>' + out + '</svg></div>';
}

/* break-even payout: what one payout must be worth for a size to clear its
   own evaluation fees. Lower is better, and it is the one metric that is not
   swamped by run-to-run noise. */
function szBars(rows, vals, title, note, fmt, colorFn){
  const W = 560, rowH = 22, PADL = 62, PADR = 60, PADT = 16;
  const H = PADT + rows.length * rowH + 8;
  const plotW = W - PADL - PADR;
  const hiV = Math.max.apply(null, vals.concat([0]));
  const loV = Math.min.apply(null, vals.concat([0]));
  const span = (hiV - loV) || 1;
  const zero = PADL + plotW * (-loV / span);   // zero sits where it actually falls
  const scale = plotW / span;
  let out = szSvg(W, H);
  if (vals.some(v => v < 0))
    out += '<line x1="' + zero + '" y1="' + PADT + '" x2="' + zero + '" y2="' + (H - 4) +
           '" stroke="' + cv_('--rule') + '"/>';
  rows.forEach((r, i) => {
    const v = vals[i], y = PADT + i * rowH;
    const w = Math.abs(v) * scale;
    const x = v >= 0 ? zero : zero - w;
    /* a negative bar's label goes to its left only if it fits there; when one
       large positive value puts the zero line near the edge, the small losses
       have no room on that side and the label collided with the row label */
    const leftOK = v < 0 && (x - PADL) > 72;
    const lx = v >= 0 ? Math.min(x + w + 6, W - 4) : (leftOK ? x - 6 : zero + 6);
    out += '<text x="' + (PADL - 8) + '" y="' + (y + 13) + '" fill="' + cv_('--ink-dim') +
           '" font-size="9.5" font-family="' + cv_('--mono') + '" text-anchor="end">' +
           r.label + '</text>' +
           '<rect x="' + x + '" y="' + (y + 4) + '" width="' + Math.max(1, w) +
           '" height="13" rx="2" fill="' + colorFn(v, i) + '" opacity="0.85"/>' +
           '<text x="' + lx +
           '" y="' + (y + 14) + '" fill="' + cv_('--ink') + '" font-size="9.5" font-family="' +
           cv_('--mono') + '" text-anchor="' + (leftOK ? 'end' : 'start') + '">' +
           fmt(v) + '</text>';
  });
  return '<div class="szfig"><h4>' + title + '</h4><p>' + note + '</p>' + out + '</svg></div>';
}

/* Both datasets come from regen_payout_panels.py, which drives Core.runStrategy
   itself: a payout is a $1,000 withdrawal at a 90% split ($900) and the account
   carries on, the same rule the Strategy panel runs live. The earlier files,
   which credited $2,100 and retired the account, are kept as *_2100retire.json. */

function sizingHTML(){
  const rows = szRows(), N = SIZING.seeds, T = SIZING.ticket;
  const med = medOf;
  const mean = a => a.reduce((x, y) => x + y, 0) / a.length;
  const be = rows.map(r => { const p = mean(r.po);
    return p > 0 ? mean(r.ev) * T / p : Infinity; });
  const net = rows.map(r => mean(r.po) * SZ.payout - mean(r.ev) * T);

  let tab = '<table class="sztab"><thead><tr>' +
    ['size', '$/pt', 'comm/side', 'runs with 0 payouts', 'median payouts',
     'best run', 'median evals', 'break-even payout', 'net @ $' + SZ.payout]
      .map(h => '<th>' + h + '</th>').join('') + '</tr></thead><tbody>';
  rows.forEach((r, i) => {
    const zero = r.po.filter(v => v === 0).length;
    tab += '<tr><td><b>' + r.label + '</b></td><td>' + r.dv + '</td><td>' +
      r.comm.toFixed(2) + '</td>' +
      '<td class="' + (zero > N / 2 ? 'bad' : '') + '">' + zero + ' / ' + N + '</td>' +
      '<td><b>' + cntCell(med(r.po), N) + '</b></td><td>' +
      Math.max.apply(null, r.po) + '</td>' +
      '<td>' + cntCell(med(r.ev), N) + '</td>' +
      '<td>' + (isFinite(be[i]) ? money(be[i]) : 'never pays out') + '</td>' +
      '<td class="' + (net[i] >= 0 ? 'ok' : 'bad') + '"><b>' + money(net[i]) + '</b></td></tr>';
  });
  tab += '</tbody></table>';

  /* the spread of one size's own runs, for the sentence about why there are N
     of them; the 5 MNQ row is the middle of the ladder */
  const mid = rows[Math.min(4, rows.length - 1)];
  const evLo = Math.min.apply(null, mid.ev), evHi = Math.max.apply(null, mid.ev);
  const first = rows[0], last = rows[rows.length - 1];
  const firstNever = first.po.filter(v => v === 0).length;

  return '<h2>Sizing study</h2>' +
    '<p>What every contract size does to a 25k evaluation, run against the <b>real NQ ' +
    '1-minute bars</b>. Nothing about the price path is simulated.</p>' +
    '<div class="note warn" style="margin:8px 0"><b>Why there are ' + N + ' runs and not one.</b> ' +
    'The strategy in your file takes a <b>random direction</b> at each entry \u2014 50.0% long, ' +
    '50.0% short, no serial correlation. The market data is real, but the strategy is not ' +
    'deterministic, so there is no single &ldquo;what happened&rdquo;: your CSV is one particular ' +
    'sequence of coin flips. At ' + mid.label + ' alone, one run bought ' + evLo + ' accounts and ' +
    'another ' + evHi + ' \u2014 same bars, same rules, different flips. Each row below is ' +
    'therefore ' + N + ' independent runs, and <b>every dot is one whole run with a whole ' +
    'number of payouts</b>.</div>' +
    '<div class="szbar"><span class="lbl">Funded daily cap</span>' +
    '<button class="btn' + (SZ.cap === 'nocap' ? ' on' : '') + '" data-cap="nocap">None (your rules)</button>' +
    '<button class="btn' + (SZ.cap === 'cap' ? ' on' : '') + '" data-cap="cap">$625</button>' +
    '<span class="lbl" style="margin-left:12px">Cash per payout</span>' +
    [900, 1000, 1500, 2100].map(v => '<button class="btn' + (SZ.payout === v ? ' on' : '') +
      '" data-pay="' + v + '">$' + v + '</button>').join('') + '</div>' +
    '<p style="color:var(--ink-faint);font-size:10.5px;margin:2px 0 8px">$900 is the rule: ' +
    '$1,000 withdrawn at a 90% split. The other values show what a different split would pay; ' +
    'the account gives up $1,000 either way, so the payout counts do not change.</p>' +
    '<div class="szgrid">' +
    szStrip(rows, 'po', 'Payouts per run',
      'One dot per run. Amber tick is the median. A payout is a whole event \u2014 there is no such thing as 0.55 of one.',
      v => v.toFixed(0)) +
    szStrip(rows, 'ev', 'Evaluations bought per run',
      'Each costs $65. This is the cost side, and it grows with size just as the payouts do.',
      v => v.toFixed(0)) +
    szBars(rows, be.map(v => isFinite(v) ? v : 0), 'Break-even payout',
      'What one payout must be worth for that size to clear its own eval fees. Lower is better \u2014 the one measure not swamped by run-to-run noise.',
      (v, i) => (v === 0 && !isFinite(be[i])) ? 'never' : money(v),
      (v, i) => (v === 0 && !isFinite(be[i])) ? cv_('--ink-faint')
                : v <= SZ.payout ? S.col.up : S.col.down) +
    szBars(rows, net, 'Net result at $' + SZ.payout + ' per payout',
      'Mean across all ' + N + ' runs. Switch the payout value above \u2014 it changes the answer completely.',
      v => money(v), v => v >= 0 ? S.col.up : S.col.down) +
    '</div>' + tab +
    '<p style="margin-top:10px"><b>' + first.label + ' barely pays out.</b> ' + firstNever +
    ' of ' + N + ' runs never reached the $27,100 a payout requires, and the median run was paid ' +
    cnt(med(first.po)) + (med(first.po) === 1 ? ' time' : ' times') + ', against ' +
    cnt(med(last.po)) + ' at ' + last.label + '. ' +
    'And note <b>1 NQ against 10 MNQ</b>: identical $20 per point, but $1.50 a side against $7.50. ' +
    'Same exposure, five times the commission.</p>' +
    '<div style="margin-top:12px"><button class="btn" id="szClose">Close</button></div>';
}
function openSizing(){
  const sheet = document.getElementById('sheet');
  sheet.classList.add('sz');
  sheet.innerHTML = sizingHTML();
  openSheet();
  bindSizing();
}
function bindSizing(){
  const sheet = document.getElementById('sheet');
  sheet.querySelectorAll('button[data-cap]').forEach(b => b.onclick = () => {
    SZ.cap = b.dataset.cap; sheet.innerHTML = sizingHTML(); bindSizing();
  });
  sheet.querySelectorAll('button[data-pay]').forEach(b => b.onclick = () => {
    SZ.payout = +b.dataset.pay; sheet.innerHTML = sizingHTML(); bindSizing();
  });
  const c = document.getElementById('szClose');
  if (c) c.onclick = () => {
    document.getElementById('modal').classList.remove('on');
    sheet.classList.remove('sz');
  };
}
document.getElementById('bsize').onclick = openSizing;

/* ---------------- account simulator ---------------- */
function accountHTML(){
  const a = S.acct;
  const num = (id, v, step) => '<input type="number" id="' + id + '" value="' + v +
    '" step="' + (step || 1) + '" style="width:88px">';
  const row = (l, c, note) => '<div class="setrow"><span>' + l +
    (note ? '<br><span style="color:var(--ink-faint);font-size:9.5px">' + note + '</span>' : '') +
    '</span>' + c + '</div>';
  const q = SIM ? SIM.summary : null;
  /* what the current numbers actually imply, stated in points and dollars */
  const size = a.sizeMode === 'fixed' ? a.contracts : 1;
  const rt = 2 * a.commission * size + 2 * a.slippage * a.pointValue * size;
  const dd = a.evaluation.on ? a.evaluation.trailDD : Math.max(a.balance - a.floor, 0);
  const ppp = a.pointValue * size;
  const toFloor = ppp > 0 ? (dd - rt) / ppp : Infinity;
  const dayCap = a.evaluation.on && a.evaluation.dailyCap > 0
    ? a.evaluation.dailyCap / ppp : Infinity;
  const fmtPts = v => isFinite(v) ? v.toFixed(1) + ' pts' : 'no limit';

  const stratOn = STLOADED && TRADES === STLOADED.trades;
  return '<h2>Prop firm account</h2>' +
    (stratOn
      ? '<div class="note" style="margin-bottom:8px"><b>The trades on the chart came from the ' +
        'Strategy panel</b> and carry their own accounting: every exit was placed by the size ' +
        'and rules set there, so the ledger shows those books and the settings below do not ' +
        'apply to them. To change the size or the rules for this run, use Strategy. These ' +
        'settings take effect on the shipped list (Data \u25b8 Demo) and on imported trades.</div>'
      : '') +
    '<p>Replays the loaded trades against a real balance under a firm\u2019s rules. It tracks ' +
    '<b>unrealised</b> equity bar by bar: if the account runs out of money before price ' +
    'reaches your stop, the position is closed there instead. A stop is a price; ' +
    'liquidation is an equity level, and with enough size the second one binds first.</p>' +

    (stratOn ? '' : '<div class="szbar" style="margin-bottom:6px">' +
    '<button class="btn on" id="acReport" title="Re-runs the loaded trades across every ' +
    'contract size from $2 to $200 a point, both cap settings, every withdrawal limit, and ' +
    'a range of profit splits and ticket prices \u2014 then reports which settings return ' +
    'the most per dollar spent">\u25b8 Full analysis \u2014 find the best settings</button>' +
    '<span class="lbl">every size, ranked by return on ticket spend \u00b7 opens in a new ' +
    'tab</span></div>') +
    '<div class="szbar"><span class="lbl">Preset</span>' +
    '<button class="btn" id="apLucid" title="Fill every field below with the LucidFlex 25k ' +
    'rules: $25,000 start, $1,250 to pass, $625 a day, $1,000 trailing drawdown freezing at ' +
    '$25,100, $65 a ticket">LucidFlex 25k</button>' +
    '<button class="btn" id="apOff" title="Turn the simulator off and show the backtest\u2019s ' +
    'own P&amp;L again">Turn it all off</button></div>' +

    row('<b>Simulate an account</b>',
        '<input type="checkbox" id="aOn"' + (a.on ? ' checked' : '') + '>',
        'off, the ledger shows the backtest\u2019s own P&amp;L at 1 micro; on, it shows what ' +
        'YOUR account made at your size and your costs') +

    '<h3>1 \u00b7 The account you bought</h3>' +
    row('Starting balance ($)', num('aBal', a.balance, 100),
        'what the firm credits the account with \u2014 $25,000 on a LucidFlex 25k') +
    row('Price of one evaluation ($)', num('eCost', a.evaluation.cost, 5),
        'the ticket, charged once per account bought \u2014 $65. This is your entire downside') +
    row('Liquidate at ($)', num('aFloor', a.floor, 100),
        'the balance at which the position is force-closed, whatever your stop says. Used ' +
        'when the firm rules below are off; with them on, the trailing drawdown sets it') +

    '<h3>2 \u00b7 What you trade</h3>' +
    row('How the size is decided', '<select id="aMode">' +
        '<option value="fixed"' + (a.sizeMode === 'fixed' ? ' selected' : '') +
        '>A fixed number of contracts</option>' +
        '<option value="risk"' + (a.sizeMode === 'risk' ? ' selected' : '') +
        '>A fixed % of the balance at risk</option></select>') +
    (a.sizeMode === 'fixed'
      ? row('Contracts per trade', num('aCon', a.contracts, 1),
            'the same size on every trade, whatever the balance has done')
      : row('Risk per trade (%)', num('aRisk', a.riskPct, 0.1),
            'size = (balance \u00d7 this %) \u00f7 (stop distance \u00d7 $ per point), so the ' +
            'size falls as the account does')) +
    row('Dollars per point ($)', num('aPV', a.pointValue, 0.5),
        'what one point of movement is worth: NQ 20 \u00b7 MNQ 2 \u00b7 ES 50 \u00b7 MES 5 \u00b7 ' +
        'RTY 50 \u00b7 M2K 5 \u00b7 CL 1000 \u00b7 MCL 100 \u00b7 GC 100 \u00b7 MGC 10 \u00b7 VX 1000') +
    row('Commission, per contract per side ($)', num('aComm', a.commission, 0.05),
        '$1.50 a side on 1 NQ, so $3.00 the round turn') +
    row('Slippage, points per side', num('aSlip', a.slippage, 0.05),
        'charged on the way in and the way out') +

    '<h3>3 \u00b7 The rules you are held to</h3>' +
    '<p style="margin:4px 0;color:var(--ink-dim);font-size:11.5px">' +
    '<b>PASS</b> is reaching the profit target without any single day booking more than the ' +
    'consistency cap. <b>FAIL</b> is touching the trailing drawdown, which ratchets up behind ' +
    'your best end-of-day balance and then freezes.</p>' +
    row('<b>Apply the firm\u2019s rules</b>',
        '<input type="checkbox" id="eOn"' + (a.evaluation.on ? ' checked' : '') + '>',
        'off, only the balance and the floor above apply') +
    row('Buy another when one ends',
        '<input type="checkbox" id="eRep"' + (a.evaluation.repeat ? ' checked' : '') + '>',
        'when an account passes or busts, buy the next and carry on \u2014 this is what turns ' +
        'a single outcome into a pass RATE, and it is the whole basis of the Wealth study') +
    row('Profit needed to pass ($)', num('eTgt', a.evaluation.target, 50),
        '$1,250 on a LucidFlex 25k, so the account passes at $26,250') +
    row('Most you may bank in one day ($)', num('eCap', a.evaluation.dailyCap, 25),
        'the 50% consistency rule \u2014 $625. A day that reaches it stops trading, and the ' +
        'profit is booked at the cap') +
    row('Stop trading for the day after losing ($)', num('eLoss', a.evaluation.dailyLoss, 25),
        '0 means no daily loss limit, and the drawdown alone decides') +
    row('Trailing drawdown ($)', num('eDD', a.evaluation.trailDD, 50),
        '$1,000, measured end of day. The bust level follows your best end-of-day balance up, ' +
        'and never comes back down') +
    row('Stop the drawdown trailing at (+$)', num('eFrz', a.evaluation.freezeOffset, 25),
        'once the floor is this far above the start it freezes. +$100 means the floor stops ' +
        'at $25,100 \u2014 which happens when the balance reaches $26,100, locking in $100') +

    '<h3>4 \u00b7 Getting paid</h3>' +
    '<p style="margin:4px 0;color:var(--ink-dim);font-size:11.5px">Passing does not end the ' +
    'account \u2014 it makes it <b>funded</b>. A funded account starts again at the opening ' +
    'balance under the same trailing drawdown, and this is the only stage that can actually ' +
    'pay you. <b>The account balance is never yours.</b> The only money that reaches you is a ' +
    'payout; the only money that leaves you is a ticket.</p>' +
    row('Profit needed to withdraw (+$)', num('ePay', a.evaluation.payoutAt, 100),
        'measured from the opening balance once funded. $2,100 means the account may withdraw ' +
        'once it reaches $27,100') +
    row('Amount withdrawn each time ($)', num('ePayD', a.evaluation.payoutDraw, 100),
        'this LEAVES the account. Withdraw $1,000 at $27,100 and the account carries on from ' +
        '$26,100 \u2014 with the floor still frozen at $25,100, so the next withdrawal is ' +
        'earned from a thinner cushion than the first') +
    row('Your share of it (%)',
        '<input type="number" id="ePayS" value="' + (a.evaluation.payoutSplit * 100) +
        '" step="5" min="0" max="100" style="width:88px">',
        'the profit split. At 90% a $1,000 withdrawal pays you <b>$900</b>. Every winning ' +
        'figure scales directly with this, so it is the single most important number here') +
    row('Withdrawals allowed per account',
        num('ePayN', a.evaluation.maxDraws, 1),
        '0 means no limit. Set 5 and an account graduates to a live account after its fifth ' +
        'withdrawal and leaves this model \u2014 so getting funded is worth at most five ' +
        'payouts, not an indefinite income') +
    row('The daily cap still applies once funded',
        '<input type="checkbox" id="eFCap"' + (a.evaluation.fundedCapOn ? ' checked' : '') + '>',
        'the firm\u2019s rules are not explicit about this, so it is a setting rather than an ' +
        'assumption \u2014 turning it off reaches payouts faster and flatters the result') +

    '<div class="note" style="margin-top:10px"><b>What these settings mean.</b> ' +
    'At ' + (a.sizeMode === 'fixed' ? size + ' contract' + (size === 1 ? '' : 's') : '1 contract') +
    ' and $' + a.pointValue + ' a point, one point is <b>' + money(ppp) + '</b> and the round ' +
    'turn costs <b>' + money(rt) + '</b>. With ' + money(dd) + ' of room, price can move ' +
    '<b>' + fmtPts(toFloor) + '</b> against you before the account is liquidated' +
    (isFinite(dayCap) ? ', and <b>' + fmtPts(dayCap) + '</b> in your favour before the day\u2019s ' +
      'cap stops you' : '') + '. ' +
    (toFloor < 50
      ? '<b>That is less than a 50-point stop</b>, so at this size the account dies before the ' +
        'stop is ever reached \u2014 the position is closed by the floor, not by your order.'
      : 'A 50-point stop is reached before the floor, so the stop is what closes the trade.') +
    '</div>' +

    (q && q.evaluation ? '<div class="verdict ' + q.evaluation.verdict.toLowerCase() + '">' +
      q.evaluation.verdict +
      (q.evaluation.passed ? ' \u00b7 target reached on day ' + q.evaluation.passedDays
       : q.evaluation.failed ? ' \u00b7 drawdown hit at trade ' + (q.evaluation.failedAt + 1)
       : ' \u00b7 ran out of data before either outcome') + '</div>' +
      '<div class="setgrid"><div>' +
      row('Target', money(q.evaluation.target)) +
      row('Daily cap', money(q.evaluation.dailyCap)) +
      row('Best day', money(q.evaluation.bestDay)) +
      '</div><div>' +
      row('Days traded', String(q.evaluation.days)) +
      row('Days capped out', String(q.evaluation.capHits)) +
      row('Final floor', money(q.evaluation.finalFloor),
          'the bust level now \u2014 it ratchets to (best end-of-day balance ' +
          '\u2212 drawdown) and then freezes, so it can sit well above where it started') +
      '</div></div>' : '') +
    (SERIES ? (() => {
      const p = SERIES.summary;
      const accs = SERIES.accounts;
      const rowsHtml = accs.slice(0, 60).map(x =>
        '<tr><td>' + x.n + '</td><td class="' +
        (x.verdict === 'PAYOUT' ? 'ok' : x.verdict === 'FAIL' ? 'bad' : '') + '"><b>' +
        x.verdict + '</b></td><td>' + (x.funded ? 'yes' : '\u2014') + '</td><td>' +
        (x.paid ? money(x.paid) : '\u2014') + '</td><td>' + x.days + '</td><td>' +
        x.trades + '</td><td>' + x.wins + '/' + (x.trades - x.wins) + '</td><td class="' +
        (x.pnl >= 0 ? 'ok' : 'bad') + '">' + money(x.pnl) + '</td><td>' +
        money(x.bal) + '</td></tr>').join('');
      return '<h3>The answer</h3>' +
        '<div class="verdict ' + (p.net >= 0 ? 'pass' : 'fail') + '">' +
        (p.net >= 0 ? 'MADE ' : 'LOST ') + money(Math.abs(p.net)) +
        '  \u00b7  ' + p.payouts + ' withdrawal' + (p.payouts === 1 ? '' : 's') +
        ' \u00d7 ' + money(p.payoutValue) + ' from ' + p.accounts + ' tickets</div>' +
        '<div class="setgrid"><div>' +
        row('Tickets bought', String(p.accounts),
            'one per account, at ' + money(p.ticket) + ' each') +
        row('Spent on tickets', '<b class="bad">' + money(-p.spent) + '</b>') +
        row('Reached funded', String(p.passes) +
            '  (' + (100 * p.fundedRate).toFixed(1) + '% of tickets)') +
        row('Withdrawals taken', '<b class="' + (p.payouts ? 'ok' : '') + '">' +
            String(p.payouts) + '</b>',
            p.passes ? p.drawsPerFunded.toFixed(2) + ' per funded account' : '') +
        row('Graduated to live', String(p.graduated || 0),
            p.maxDraws ? 'hit the ' + p.maxDraws + '-withdrawal limit' : 'no limit set') +
        '</div><div>' +
        row('Received', '<b class="ok">' + money(p.won) + '</b>',
            money(p.payoutDraw) + ' withdrawn \u00d7 ' +
            (p.payoutSplit * 100).toFixed(0) + '% = ' + money(p.payoutValue) + ' each') +
        row('Return on ticket spend',
            '<b class="' + (p.roi >= 0 ? 'ok' : 'bad') + '">' +
            (p.roi * 100).toFixed(1) + '%</b>',
            'per dollar spent on evaluations, what came back') +
        row('Net per ticket', money(p.perTicket),
            'is buying one evaluation worth it, on average?') +
        row('<b>NET</b>', '<b class="' + (p.net >= 0 ? 'ok' : 'bad') + '">' +
            money(p.net) + '</b>', 'payouts received minus tickets bought \u2014 the ' +
            'only two flows that are actually yours') +
        row('Break-even payout value', p.payouts
            ? money(p.spent / p.payouts) : 'never paid out',
            'what one payout would have to be worth for this to break even') +
        row('Trading P&L (not yours)', money(p.pnl),
            'what the accounts made on paper. You do not keep it \u2014 it is shown only ' +
            'to explain why the accounts ended where they did') +
        '</div></div>' +
        '<h3>Accounts</h3>' +
        '<div class="bigrow">' +
        '<div class="bignum"><div class="bl">Accounts</div><div class="bv">' +
          p.accounts + '</div></div>' +
        '<div class="bignum"><div class="bl">Passed</div><div class="bv ok">' +
          p.passes + '</div></div>' +
        '<div class="bignum"><div class="bl">Failed</div><div class="bv bad">' +
          p.fails + '</div></div>' +
        '<div class="bignum"><div class="bl">Pass rate</div><div class="bv">' +
          (p.passRate * 100).toFixed(1) + '%</div></div>' +
        '</div>' +
        '<div class="setgrid"><div>' +
        row('Still running', String(p.incomplete)) +
        row('Trades taken', String(p.trades)) +
        row('Avg trades per account', p.avgTradesPerAccount.toFixed(1)) +
        '</div><div>' +
        row('Avg days per account', p.avgDaysPerAccount.toFixed(1)) +
        row('Forced liquidations', String(p.forced),
            'closed by running out of equity rather than by the stop') +
        row('Busted', String(p.fails)) +
        '</div></div>' +
        '<div class="tablewrap" style="max-height:220px;margin-top:8px"><table><thead><tr>' +
        '<th>#</th><th>Result</th><th>Funded</th><th>Paid</th><th>Days</th>' +
        '<th>Trades</th><th>W/L</th><th>P&L</th><th>Final</th></tr></thead><tbody>' +
        rowsHtml +
        '</tbody></table></div>' +
        (accs.length > 60 ? '<p>Showing the first 60 of ' + accs.length + '.</p>' : '') +
        '<div class="note" style="margin-top:12px"><b>How this relates to the Wealth ' +
        'panel.</b> This panel is <b>one run</b>: the exact trade list loaded in the page, ' +
        'played through account after account, and you can inspect every trade of it in the ' +
        'ledger. The Wealth panel is <b>60 runs</b> \u2014 the same coin-flip rule and the ' +
        'same real bars, but re-drawn 60 times with 60 different random seeds, so the long/' +
        'short decisions differ each time while the prices never do. One run of a random ' +
        'strategy tells you what happened once; 60 tell you what happens on average, which ' +
        'is the question. Expect this panel to land somewhere inside the spread the Wealth ' +
        'panel shows \u2014 not on its median.</div>';
    })() : '') +
    (q && !SERIES ? '<h3>Result</h3><div class="setgrid"><div>' +
      row('Final balance', '<b class="' + (q.end >= q.start ? 'pos' : 'neg') + '">' +
          money(q.end) + '</b>') +
      row('Return', '<b class="' + (q.returnPct >= 0 ? 'pos' : 'neg') + '">' +
          q.returnPct.toFixed(1) + '%</b>') +
      row('Peak', money(q.peak)) +
      row('Max drawdown', '<b class="neg">' + money(-q.maxDrawdown) + '</b>') +
      '</div><div>' +
      row('Trades taken', String(q.taken)) +
      row('Skipped', String(q.skipped)) +
      row('Forced liquidations', '<b class="' + (q.forced ? 'neg' : '') + '">' +
          q.forced + '</b>') +
      row('Account', q.blownUp
            ? '<b class="neg">blown up at trade ' + (q.deadAt + 1) + '</b>'
            : q.stopped ? '<b class="pos">stopped \u2014 target reached</b>'
                        : '<b class="pos">alive</b>') +
      '</div></div>' +
      (q.forced ? '<p><b>' + q.forced + '</b> position' + (q.forced > 1 ? 's were' : ' was') +
        ' closed by running out of equity rather than by the stop. The ledger marks ' +
        'them LIQUIDATED and the equity pane rings them.</p>' : '')
     : '<p>Turn the simulator on to see the result.</p>') +
    '<div style="margin-top:12px;display:flex;gap:6px">' +
    '<button class="btn" id="aClose">Close</button></div>';
}
function openAccount(){
  document.getElementById('sheet').classList.remove('sz');
  document.getElementById('sheet').innerHTML = accountHTML();
  openSheet();
  bindAccount();
}
function bindAccount(){
  const $ = id => document.getElementById(id);
  const refresh = () => {
    runAccount(); save(); lastSig = ''; render();
    $('bacct').classList.toggle('on', S.acct.on);
    document.getElementById('sheet').innerHTML = accountHTML();
    bindAccount();
  };
  const on = $('aOn');
  if (on) on.onchange = () => { S.acct.on = on.checked; refresh(); };
  /* the preset exists so the panel is usable without decoding every field
     first; the numbers are the LucidFlex 25k rules as stated by the firm */
  const rep = $('acReport');
  if (rep) rep.onclick = () => {
    try {
      /* the report needs a running series; switch on whatever is missing rather
         than leaving the button dead on a panel that has not been set up yet */
      if (!S.acct.on || !S.acct.evaluation.on || !S.acct.evaluation.repeat){
        S.acct.on = true;
        S.acct.evaluation.on = true;
        S.acct.evaluation.repeat = true;
        runAccount(); save(); lastSig = ''; render();
      }
      openReport();
    } catch (err){ showError('Report', err); }
  };
  const lucid = $('apLucid');
  if (lucid) lucid.onclick = () => {
    Object.assign(S.acct, {on: true, balance: 25000, floor: 24000,
                           sizeMode: 'fixed', contracts: 1, pointValue: 20,
                           commission: 1.5, slippage: 0.25});
    Object.assign(S.acct.evaluation, {on: true, repeat: true, target: 1250,
                                      dailyCap: 625, dailyLoss: 0, trailDD: 1000,
                                      cost: 65, freezeOffset: 100,
                                      payoutAt: 2100, payoutDraw: 1000,
                                      payoutSplit: 0.9, maxDraws: 0,
                                      fundedCapOn: true});
    refresh();
  };
  const off = $('apOff');
  if (off) off.onclick = () => {
    S.acct.on = false; S.acct.evaluation.on = false; refresh();
  };
  const bindNum = (id, key, min) => {
    const el = $(id); if (!el) return;
    el.onchange = () => {
      const v = parseFloat(el.value);
      if (!isFinite(v) || v < (min === undefined ? 0 : min)){ el.value = S.acct[key]; return; }
      S.acct[key] = v; refresh();
    };
  };
  bindNum('aBal', 'balance', 1); bindNum('aFloor', 'floor', 0);
  bindNum('aCon', 'contracts', 1); bindNum('aRisk', 'riskPct', 0.01);
  bindNum('aPV', 'pointValue', 0.01); bindNum('aComm', 'commission', 0);
  bindNum('aSlip', 'slippage', 0);
  const eOn = $('eOn');
  if (eOn) eOn.onchange = () => { S.acct.evaluation.on = eOn.checked; refresh(); };
  const bindEv = (id, key, min) => {
    const el = $(id); if (!el) return;
    el.onchange = () => {
      const v = parseFloat(el.value);
      if (!isFinite(v) || v < min){ el.value = S.acct.evaluation[key]; return; }
      S.acct.evaluation[key] = v; refresh();
    };
  };
  const eRep = $('eRep');
  if (eRep) eRep.onchange = () => { S.acct.evaluation.repeat = eRep.checked; refresh(); };
  bindEv('eTgt', 'target', 1); bindEv('eCap', 'dailyCap', 1);
  bindEv('eLoss', 'dailyLoss', 0); bindEv('eCost', 'cost', 0);
  bindEv('eDD', 'trailDD', 1); bindEv('eFrz', 'freezeOffset', 0);
  bindEv('ePay', 'payoutAt', 1); bindEv('ePayD', 'payoutDraw', 1);
  bindEv('ePayN', 'maxDraws', 0);
  const ps = $('ePayS');
  if (ps) ps.onchange = () => {
    const v = parseFloat(ps.value);
    if (!isFinite(v) || v < 0 || v > 100){ ps.value = S.acct.evaluation.payoutSplit * 100; return; }
    S.acct.evaluation.payoutSplit = v / 100; refresh();
  };
  const fc = $('eFCap');
  if (fc) fc.onchange = () => { S.acct.evaluation.fundedCapOn = fc.checked; refresh(); };
  const md = $('aMode');
  if (md) md.onchange = () => { S.acct.sizeMode = md.value; refresh(); };
  const cl = $('aClose');
  if (cl) cl.onclick = () => document.getElementById('modal').classList.remove('on');
}
guard('bacct', openAccount, 'Prop firm');

/* ---------------- indicator manager ---------------- */
function indBadge(){
  const el = document.getElementById('bindn');
  if (el) el.textContent = S.indicators.length ? '(' + S.indicators.length + ')' : '';
}
function indicatorsHTML(){
  const opts = Object.keys(IND_DEFS).map(k =>
    '<option value="' + k + '">' + IND_DEFS[k].label + '</option>').join('');
  const rows = !S.indicators.length
    ? '<p>Nothing added yet. Pick one below \u2014 overlays draw on the price chart, oscillators get their own panel.</p>'
    : S.indicators.map((cfg, i) => {
        const def = IND_DEFS[cfg.key];
        const ps = Object.keys(def.params).map(k =>
          '<label style="display:inline-flex;gap:4px;align-items:center;margin-right:8px">' + k +
          '<input type="number" data-i="' + i + '" data-p="' + k + '" value="' + cfg.p[k] +
          '" step="' + (k === 'sd' || k === 'mult' ? '0.1' : '1') +
          '" min="0.1" style="width:56px"></label>').join('');
        return '<div class="setrow" style="align-items:flex-start">' +
          '<span style="flex:1"><b style="color:' + (cfg.col || IND_COLS[i % IND_COLS.length]) +
          '">' + def.label + '</b>' +
          '<span style="color:var(--ink-faint);font-size:9.5px"> \u00b7 ' +
          (def.pane === 'main' ? 'overlay' : 'panel') + '</span><br>' + (ps || '\u2014') + '</span>' +
          '<span style="display:flex;gap:5px;align-items:center">' +
          '<input type="color" data-ci="' + i + '" value="' +
          (cfg.col || IND_COLS[i % IND_COLS.length]) + '">' +
          '<button class="btn" data-up="' + i + '" title="Move up">\u25b2</button>' +
          '<button class="btn" data-rm="' + i + '">Remove</button></span></div>';
      }).join('');
  return '<h2>Indicators</h2>' +
    '<p>Computed on the aggregated real bars for the current timeframe \u2014 never on ' +
    'Heikin-Ashi values, which are a display transform rather than a price series. ' +
    'All the maths is unit-tested against independent implementations.</p>' +
    rows +
    '<h3>Add</h3><div class="setrow"><select id="indAdd">' + opts + '</select>' +
    '<button class="btn" id="indAddBtn">Add to chart</button></div>' +
    '<div style="margin-top:12px;display:flex;gap:6px">' +
    '<button class="btn" id="indClose">Close</button>' +
    '<button class="btn" id="indClear">Remove all</button></div>';
}
function openIndicators(){
  document.getElementById('sheet').classList.remove('sz');
  document.getElementById('sheet').innerHTML = indicatorsHTML();
  openSheet();
  const refresh = () => {
    rebuild(); save(); indBadge(); render();
    document.getElementById('sheet').innerHTML = indicatorsHTML();
    bindIndicators();
  };
  window.__indRefresh = refresh;
  bindIndicators();
}
function bindIndicators(){
  const sheet = document.getElementById('sheet');
  const refresh = window.__indRefresh;
  sheet.querySelectorAll('input[type=number][data-p]').forEach(el => {
    el.onchange = () => {
      const v = parseFloat(el.value);
      if (!isFinite(v) || v <= 0) return;
      const k = el.dataset.p;
      S.indicators[+el.dataset.i].p[k] = (k === 'sd' || k === 'mult') ? v : Math.round(v);
      rebuild(); save(); render();
    };
  });
  sheet.querySelectorAll('input[type=color][data-ci]').forEach(el => {
    el.oninput = () => { S.indicators[+el.dataset.ci].col = el.value; rebuild(); save(); render(); };
  });
  sheet.querySelectorAll('button[data-rm]').forEach(el => {
    el.onclick = () => { S.indicators.splice(+el.dataset.rm, 1); refresh(); };
  });
  sheet.querySelectorAll('button[data-up]').forEach(el => {
    el.onclick = () => {
      const i = +el.dataset.up; if (i === 0) return;
      const t = S.indicators[i]; S.indicators[i] = S.indicators[i - 1]; S.indicators[i - 1] = t;
      refresh();
    };
  });
  const add = document.getElementById('indAddBtn');
  if (add) add.onclick = () => {
    const sel = document.getElementById('indAdd');
    const key = sel && sel.value;
    const def = key && IND_DEFS[key];
    if (!def) return;              /* nothing selected: do nothing, quietly */
    S.indicators.push({key, p: Object.assign({}, def.params),
                       col: IND_COLS[S.indicators.length % IND_COLS.length]});
    refresh();
  };
  const cl = document.getElementById('indClear');
  if (cl) cl.onclick = () => { S.indicators = []; refresh(); };
  const cls = document.getElementById('indClose');
  if (cls) cls.onclick = () => document.getElementById('modal').classList.remove('on');
}
guard('bind', openIndicators, 'Indicators');

/* ---------------- settings ---------------- */
function settingsHTML(){
  const row = (lbl, ctrl) => '<div class="setrow"><span>' + lbl + '</span>' + ctrl + '</div>';
  const rng = (id, v, mn, mx, st, suffix) =>
    '<span><input type="range" id="' + id + '" min="' + mn + '" max="' + mx + '" step="' + st +
    '" value="' + v + '"><span class="v" id="' + id + 'v">' + v + (suffix || '') + '</span></span>';
  const chk = (id, v) => '<input type="checkbox" id="' + id + '"' + (v ? ' checked' : '') + '>';
  const col = (id, v) => '<input type="color" id="' + id + '" value="' + v + '">';
  const num = (id, v, mn, mx) => '<input type="number" id="' + id + '" value="' + v +
    '" min="' + mn + '" max="' + mx + '">';
  return '<h2>Settings</h2>' +
  '<h3>Theme</h3><div class="swatches" id="themesw">' +
    Object.keys(THEMES).map(k => '<div class="sw' + (S.theme === k ? ' on' : '') +
      '" data-t="' + k + '" title="' + k + '" style="background:' + THEMES[k].panel +
      ';box-shadow:inset 0 0 0 6px ' + THEMES[k].ground + '"></div>').join('') + '</div>' +
  '<h3>Palette</h3><div class="swatches" id="palsw">' +
    Object.keys(PALETTES).map(k => '<div class="sw' + (S.palette === k ? ' on' : '') +
      '" data-p="' + k + '" title="' + k + '" style="background:linear-gradient(90deg,' +
      PALETTES[k].up + ' 50%,' + PALETTES[k].down + ' 50%)"></div>').join('') + '</div>' +
  '<div class="setgrid"><div>' +
    '<h3>Colours</h3>' +
    row('Up', col('cUp', S.col.up)) + row('Down', col('cDown', S.col.down)) +
    row('Long', col('cLong', S.col.long)) + row('Short', col('cShort', S.col.short)) +
    row('Accent', col('cAcc', S.col.accent)) +
    '<h3>Candles</h3>' +
    row('Body width', rng('sBody', S.bodyW, 0.2, 0.98, 0.02)) +
    row('Wick width', rng('sWick', S.wickW, 0.5, 3, 0.1)) +
    row('Show wicks', chk('sWicks', S.wicks)) +
  '</div><div>' +
    '<h3>Grid &amp; axes</h3>' +
    row('Show grid', chk('sGrid', S.grid)) +
    row('Grid opacity', rng('sGridOp', S.gridOp, 0.1, 1, 0.05)) +
    row('Session lines', chk('sSess', S.sessLines)) +
    row('Price decimals', num('sDec', S.decimals, 0, 5)) +
    row('Font size', rng('sFont', S.fontSize, 8, 15, 0.5, 'px')) +
    '<h3>Trades</h3>' +
    row('Risk boxes', chk('sBoxes', S.tBoxes)) +
    row('Entry/exit markers', chk('sMark', S.tMarkers)) +
    row('Selected label', chk('sLab', S.tLabels)) +
    row('Box opacity', rng('sTop', S.tOpacity, 0.02, 0.5, 0.01)) +
    '<h3>Session marks</h3>' +
    S.marks.map((mk, i) =>
      '<div class="setrow"><span><input type="checkbox" data-mk="' + i + '"' +
      (mk.on ? ' checked' : '') + '> ' + mk.label + '</span>' +
      '<span><input type="text" data-mkt="' + i + '" value="' + hhmm(mk.m) +
      '" size="5" style="width:52px"> <input type="color" data-mkc="' + i +
      '" value="' + mk.col + '"></span></div>').join('') +
    row('Shade a time band', chk('sShade', S.shade.on)) +
    '<div class="setrow"><span>Band from / to</span><span>' +
    '<input type="text" id="sShadeA" value="' + hhmm(S.shade.from) + '" style="width:52px"> ' +
    '<input type="text" id="sShadeB" value="' + hhmm(S.shade.to) + '" style="width:52px"></span></div>' +
    '<h3>Time filter</h3>' +
    row('Keep only this window', chk('sFilt', S.filter.on)) +
    '<div class="setrow"><span>Filter from / to</span><span>' +
    '<input type="text" id="sFiltA" value="' + hhmm(S.filter.from) + '" style="width:52px"> ' +
    '<input type="text" id="sFiltB" value="' + hhmm(S.filter.to) + '" style="width:52px"></span></div>' +
    '<h3>Layout</h3>' +
    row('Navigator strip', chk('sNav', S.showNav)) +
    row('Side rail', chk('sRail', S.showRail)) +
    row('Equity pane height', rng('sEqH', S.eqH, 70, 420, 10, 'px')) +
    row('Indicator pane height', rng('sSubH', S.subH, 60, 240, 4, 'px')) +
    row('Drawdown shading', chk('sEqDD', S.eqMode !== 'curve')) +
  '</div></div>' +
  '<div style="margin-top:14px;display:flex;gap:6px">' +
  '<button class="btn" id="setClose">Close</button>' +
  '<button class="btn" id="setReset">Reset to defaults</button></div>';
}
function bindSettings(){
  const $ = id => document.getElementById(id);
  const live = (id, fn, fmt) => {
    const el = $(id); if (!el) return;
    el.oninput = () => {
      fn(el.type === 'checkbox' ? el.checked : el.value);
      const v = $(id + 'v'); if (v) v.textContent = fmt ? fmt(el.value) : el.value;
      save(); applyTheme(); applyLayout(); render();
    };
  };
  [...document.querySelectorAll('#themesw .sw')].forEach(d => d.onclick = () => {
    S.theme = d.dataset.t; applyTheme(); save();
    [...document.querySelectorAll('#themesw .sw')].forEach(x => x.classList.toggle('on', x === d));
    render();
  });
  [...document.querySelectorAll('#palsw .sw')].forEach(d => d.onclick = () => {
    S.palette = d.dataset.p; S.col = Object.assign({}, PALETTES[S.palette]);
    applyTheme(); save();
    $('sheet').innerHTML = settingsHTML(); bindSettings();
    render();
  });
  live('cUp', v => S.col.up = v); live('cDown', v => S.col.down = v);
  live('cLong', v => S.col.long = v); live('cShort', v => S.col.short = v);
  live('cAcc', v => S.col.accent = v);
  live('sBody', v => S.bodyW = +v); live('sWick', v => S.wickW = +v);
  live('sWicks', v => S.wicks = v);
  live('sGrid', v => S.grid = v); live('sGridOp', v => S.gridOp = +v);
  live('sSess', v => S.sessLines = v);
  live('sDec', v => S.decimals = Math.max(0, Math.min(5, +v)));
  live('sFont', v => S.fontSize = +v);
  live('sBoxes', v => S.tBoxes = v); live('sMark', v => S.tMarkers = v);
  live('sLab', v => S.tLabels = v); live('sTop', v => S.tOpacity = +v);
  live('sNav', v => S.showNav = v); live('sRail', v => S.showRail = v);
  const toMin = t => {
    const m = /^(\d{1,2}):(\d{2})$/.exec(String(t).trim());
    return m ? Math.max(0, Math.min(1439, +m[1] * 60 + +m[2])) : null;
  };
  document.querySelectorAll('input[data-mk]').forEach(el => {
    el.onchange = () => { S.marks[+el.dataset.mk].on = el.checked; save(); render(); };
  });
  document.querySelectorAll('input[data-mkt]').forEach(el => {
    el.onchange = () => {
      const v = toMin(el.value);
      if (v === null){ el.value = hhmm(S.marks[+el.dataset.mkt].m); return; }
      S.marks[+el.dataset.mkt].m = v; save(); render();
    };
  });
  document.querySelectorAll('input[data-mkc]').forEach(el => {
    el.oninput = () => { S.marks[+el.dataset.mkc].col = el.value; save(); render(); };
  });
  live('sShade', v => S.shade.on = v);
  ['sShadeA', 'sShadeB'].forEach((id, k) => {
    const el = $(id); if (!el) return;
    el.onchange = () => {
      const v = toMin(el.value);
      if (v === null){ el.value = hhmm(k ? S.shade.to : S.shade.from); return; }
      if (k) S.shade.to = v; else S.shade.from = v;
      save(); render();
    };
  });
  live('sFilt', v => { S.filter.on = v; applyFilter(); });
  ['sFiltA', 'sFiltB'].forEach((id, k) => {
    const el = $(id); if (!el) return;
    el.onchange = () => {
      const v = toMin(el.value);
      if (v === null){ el.value = hhmm(k ? S.filter.to : S.filter.from); return; }
      if (k) S.filter.to = v; else S.filter.from = v;
      if (S.filter.on) applyFilter(); else save();
    };
  });
  live('sEqH', v => S.eqH = +v); live('sSubH', v => S.subH = +v);
  live('sEqDD', v => S.eqMode = v ? 'both' : 'curve');
  $('setClose').onclick = () => $('modal').classList.remove('on');
  $('setReset').onclick = () => {
    try { localStorage.removeItem('tape.v3'); } catch(e){}
    S.theme = 'midnight'; S.palette = 'classic';
    S.col = Object.assign({}, PALETTES.classic);
    S.bodyW = 0.7; S.wickW = 1; S.wicks = true;
    S.grid = true; S.gridOp = 1; S.sessLines = true; S.decimals = 2; S.fontSize = 10.5;
    S.tBoxes = true; S.tMarkers = true; S.tLabels = true; S.tOpacity = 0.10;
    S.showNav = true; S.showRail = true;
    S.eqH = 190; S.subH = 92; S.eqMode = 'both';
    S.marks = [{m:570,label:'RTH',col:'#d8a24a',on:true},
               {m:600,label:'10:00',col:'#6ea8dc',on:false},
               {m:960,label:'Close',col:'#8e99ac',on:false}];
    S.shade = {on:false, from:570, to:960};
    S.filter = {on:false, from:570, to:960};
    S.acct = {on:false, balance:10000, floor:0, sizeMode:'fixed',
              contracts:1, riskPct:1, pointValue:2,
              commission:0.75, slippage:0.25,
              evaluation:{on:false, repeat:false, target:1250, dailyCap:625,
                          dailyLoss:0, trailDD:1000, freezeOffset:100,
                          cost:65}};
    applyTheme(); applyLayout(); rebuild(); save();
    $('sheet').innerHTML = settingsHTML(); bindSettings();
    render();
  };
}
function applyFilter(){
  const keepBase = SRC && SRC.back ? SRC.back[Math.round((S.view.a + S.view.b) / 2)]
                                   : Math.round((S.view.a + S.view.b) / 2);
  rebuild(); NAVPTS = null; reindexSessions(); lastSig = '';
  const btn = document.getElementById('bfilt');
  if (btn) btn.classList.toggle('on', S.filter.on);
  const anchor = FWD ? Math.max(0, FWD[Math.min(BASE.n - 1, keepBase || 0)]) : (keepBase || 0);
  const span = Math.min(V.n - 1, Math.max(20, S.view.b - S.view.a));
  const mid = V.map[Math.max(0, Math.min((SRC.n || V.n) - 1, anchor))] || 0;
  fitPrice(); setView(mid - span / 2, mid + span / 2);
  save(); indBadge();
}
document.getElementById('bfilt').onclick = () => {
  S.filter.on = !S.filter.on;
  applyFilter();
};
function applyLayout(){
  document.getElementById('nav').style.display = S.showNav ? '' : 'none';
  const fb = document.getElementById('bfilt');
  if (fb) fb.classList.toggle('on', S.filter.on);
  const ab = document.getElementById('bacct');
  if (ab) ab.classList.toggle('on', S.acct.on);
  const rail = document.querySelector('.rail');
  rail.style.display = S.showRail ? '' : 'none';
  document.querySelector('.main').style.gridTemplateColumns = S.showRail ? '1fr 244px' : '1fr';
}
guard('bset', () => {
  document.getElementById('sheet').innerHTML = settingsHTML();
  openSheet();
  bindSettings();
}, 'Settings');

/* ---------------- data loading ---------------- */
function parseCSV(text){
  const lines = text.trim().split(/\r?\n/);
  const sep = (lines[0].match(/\t/g) || []).length > (lines[0].match(/,/g) || []).length ? '\t' : ',';
  const strip = s => s.replace(/^\uFEFF/, '').trim().replace(/^["']|["']$/g, '');
  const head = lines[0].split(sep).map(s => strip(s).toLowerCase());
  const rows = [];
  for (let i = 1; i < lines.length; i++){
    if (lines[i].trim()) rows.push(lines[i].split(sep).map(strip));
  }
  return {head, rows};
}
const findCol = (h, names) => { for (const n of names){ const i = h.indexOf(n); if (i >= 0) return i; } return -1; };
/* The UTC offset a timestamp carries, in minutes: "2024-03-13 14:30:00+00:00"
   and "2024-03-13T14:30:00Z" give 0, "...09:30:00-04:00" gives -240. null
   means there is none and the clock is taken as written, which is what a
   datetime_et export wants. */
function tzOffsetMin(s){
  const m = /(Z|[+-]\d\d:?\d\d)\s*$/.exec(s);
  if (!m) return null;
  if (m[1] === 'Z') return 0;
  return (m[1].charAt(0) === '-' ? -1 : 1) * (+m[1].slice(1, 3) * 60 + +m[1].slice(-2));
}
/* New York's offset from UTC at a UTC instant: EDT (-4h) from the second
   Sunday of March at 07:00 UTC to the first Sunday of November at 06:00 UTC,
   EST (-5h) otherwise -- the rule since 2007, so every file this will see. */
const NY_DST = {};
function nyOffsetMs(ms){
  const y = new Date(ms).getUTCFullYear();
  let r = NY_DST[y];
  if (!r){
    const DAY = 86400000, mar = Date.UTC(y, 2, 1), nov = Date.UTC(y, 10, 1);
    const toSunday = t => ((7 - new Date(t).getUTCDay()) % 7) * DAY;
    r = NY_DST[y] = [mar + toSunday(mar) + 7 * DAY + 7 * 3600000, nov + toSunday(nov) + 6 * 3600000];
  }
  return (ms >= r[0] && ms < r[1] ? -4 : -5) * 3600000;
}
/* A bar file the way the shipped tape was built: timestamps that carry a UTC
   offset (databento's "+00:00") are converted to New York time, and with RTH
   on the bars are cut to 09:30-15:59 so a session is the day session. Taking
   the clock as written, as this once did, put a databento "10:00" at 06:00
   New York and ran the "16:00 close" at 16:59 -- the coin looked different on
   ES for no reason to do with ES. Read line by line rather than through
   parseCSV: a 16-year 1-minute file is 5.5 million rows, and holding every
   field of every row as a string is what runs the tab out of memory. */
function barsFromCSV(text){
  const lines = text.split(/\r?\n/);
  let first = 0;
  while (first < lines.length && !lines[first].trim()) first++;
  if (first >= lines.length) throw new Error('empty file');
  const sep = (lines[first].match(/\t/g) || []).length > (lines[first].match(/,/g) || []).length ? '\t' : ',';
  const strip = s => (s || '').replace(/^\uFEFF/, '').trim().replace(/^["']|["']$/g, '');
  const head = lines[first].split(sep).map(s => strip(s).toLowerCase());
  const iDT = findCol(head, ['datetime','timestamp','date_time','datetime_et','ts_event']);
  const iD = findCol(head, ['date']), iT = findCol(head, ['time','clock']);
  const iO = findCol(head, ['open','o']), iH = findCol(head, ['high','h']);
  const iL = findCol(head, ['low','l']), iC = findCol(head, ['close','c','last']);
  const iV = findCol(head, ['volume','vol','v','qty','size']);
  if (iO < 0 || iH < 0 || iL < 0 || iC < 0) throw new Error('need open/high/low/close');
  const stampOf = r => iDT >= 0 ? strip(r[iDT])
                     : iD >= 0 ? strip(r[iD]) + (iT >= 0 ? ' ' + strip(r[iT]) : '') : '';
  /* the first data row decides whether the file carries an offset */
  let off = null;
  for (let k = first + 1; k < lines.length; k++){
    if (lines[k].trim()){ off = tzOffsetMin(stampOf(lines[k].split(sep))); break; }
  }
  const N = lines.length - first - 1;
  let o = new Float64Array(N), h = new Float64Array(N), l = new Float64Array(N),
      c = new Float64Array(N), mins = new Int16Array(N);
  let v = iV >= 0 ? new Float64Array(N) : null;
  let days = new Array(N);
  let n = 0, dayNum = null, dayStr = '', firstM = null, intraday = false;
  for (let k = first + 1; k < lines.length; k++){
    if (!lines[k].trim()) continue;
    const r = lines[k].split(sep);
    o[n] = +r[iO]; h[n] = +r[iH]; l[n] = +r[iL]; c[n] = +r[iC];
    if (v) v[n] = +r[iV] || 0;
    const st = stampOf(r);
    let m;
    if (off !== null){
      const rowOff = tzOffsetMin(st);
      const ms = Date.UTC(+st.slice(0, 4), +st.slice(5, 7) - 1, +st.slice(8, 10),
                          +st.slice(11, 13) || 0, +st.slice(14, 16) || 0, +st.slice(17, 19) || 0)
                 - (rowOff === null ? off : rowOff) * 60000;
      const local = ms + nyOffsetMs(ms);
      const dn = Math.floor(local / 86400000);
      if (dn !== dayNum){ dayNum = dn; dayStr = new Date(dn * 86400000).toISOString().slice(0, 10); }
      days[n] = dayStr;
      m = Math.floor((local - dn * 86400000) / 60000);
    } else {
      const s2 = st.replace('T', ' ');
      const hm = s2.slice(11, 16);
      days[n] = s2.slice(0, 10) || 'series';
      m = hm ? (+hm.slice(0, 2)) * 60 + (+hm.slice(3, 5)) : 0;
    }
    mins[n] = m;
    /* A daily or weekly file has one bar per date and one clock value; it is
       never cut, and splitting it on the date would make every bar its own
       session and turn aggregation into a no-op. */
    if (firstM === null) firstM = m; else if (m !== firstM) intraday = true;
    n++;
  }
  let cut = false;
  if (S.rthOnly && intraday){
    let w = 0;
    for (let i = 0; i < n; i++){
      const m = mins[i];
      if (m < 570 || m > 959) continue;
      if (w !== i){ o[w] = o[i]; h[w] = h[i]; l[w] = l[i]; c[w] = c[i]; mins[w] = m; days[w] = days[i]; if (v) v[w] = v[i]; }
      w++;
    }
    if (!w) throw new Error('no bars between 09:30 and 15:59 New York time \u2014 turn RTH off to keep every hour');
    n = w; cut = true;
  }
  o = o.slice(0, n); h = h.slice(0, n); l = l.slice(0, n); c = c.slice(0, n); mins = mins.slice(0, n);
  if (v) v = v.slice(0, n);
  days.length = n;
  const sessions = Core.buildSessions(days);
  return {n, o, h, l, c, v, mins, sessions, days,
          clock: {converted: off !== null, rth: cut, intraday}};
}
/* what the subtitle says about a loaded file's clock, so a mis-sessioned
   tape is visible rather than silent */
function clockNote(b){
  const k = b.clock;
  if (!k || !k.intraday) return '';
  return ' \u00b7 ' + (k.rth ? '09:30\u201315:59' : 'all hours') +
    (k.converted ? ' New York time' : ', clock as in the file');
}
function tradesFromCSV(text, bars){
  const {head, rows} = parseCSV(text);
  const iEn = findCol(head, ['entry_time','entry_bar','entrytime','in_time']);
  const iEx = findCol(head, ['exit_time','exit_bar','exittime','out_time']);
  const iSd = findCol(head, ['side','dir','direction','long_short']);
  const iEp = findCol(head, ['entry_price','entry_px','entry']);
  const iXp = findCol(head, ['exit_price','exit_px','exit']);
  const iSt = findCol(head, ['stop','stop_px','stop_price','sl']);
  const iTg = findCol(head, ['target','tgt_px','target_price','tp']);
  const iPn = findCol(head, ['pnl','net','profit']);
  if (iEn < 0 || iEx < 0) throw new Error('need entry_time/exit_time or entry_bar/exit_bar');
  const map = new Map();
  bars.sessions.forEach(s => {
    for (let i = s.a; i <= s.b; i++) map.set(s.day + ' ' + hhmm(bars.mins[i]), i);
  });
  const idx = v => {
    if (/^\d+$/.test(v)) return Math.min(bars.n - 1, +v);
    const k = String(v).replace('T',' ').slice(0,16);
    return map.has(k) ? map.get(k) : -1;
  };
  const dayOf = i => { const s = bars.sessions.find(s => i >= s.a && i <= s.b); return s ? s.day : ''; };
  const out = [];
  rows.forEach(r => {
    const a = idx(r[iEn]), b = idx(r[iEx]);
    if (a < 0 || b < 0) return;
    const raw = iSd >= 0 ? String(r[iSd]).toLowerCase() : '1';
    const side = (raw.charAt(0) === 's' || raw.charAt(0) === '-') ? -1 : 1;
    const ep = iEp >= 0 ? +r[iEp] : bars.o[a], xp = iXp >= 0 ? +r[iXp] : bars.c[b];
    const pnl = iPn >= 0 ? +r[iPn] : (xp - ep) * side;
    out.push({entry_bar: a, exit_bar: b, side, entry: ep, exit: xp,
      stop_px: iSt >= 0 ? +r[iSt] : ep, tgt_px: iTg >= 0 ? +r[iTg] : ep,
      A: 0, F: 0, cand_stop: 0, cand_dayloss: 0, cand_bust: 0, cand_tgt: 0, cand_daytgt: 0,
      pts: (xp - ep) * side, gross: pnl, slip: 0, comm: 0, pnl,
      realized: pnl, bal: 0, floor: 0, stage: '', why: '', day: dayOf(a)});
  });
  return out;
}
/* A new tape invalidates every result computed on the old one: the cached
   Strategy run (or the panel would open on the old tape's numbers) and the
   ensemble batch (its session indices no longer exist -- ensCurves threw
   "reading 'day'" on a shorter tape). */
function dropTapeResults(){ STRES = null; ENS.res = null; }
/* Guesses the instrument from the file name so the account is priced for
   what was actually loaded rather than whatever Instrument button was
   clicked for the previous file. \b keeps 'NQ' from matching inside 'MNQ'
   (M and N are both word characters, so there is no boundary between them)
   regardless of check order; longest keys first is extra insurance. null
   when nothing in the name matches a known symbol. */
function detectSymbol(filename){
  const keys = INSTRUMENTS.map(z => z.key).sort((a, b) => b.length - a.length);
  /* \b treats '_' as a word character, so \bNQ\b misses 'NQ_1min...csv' --
     exactly the underscore-separated names these files actually have.
     A boundary here means anything that is not a letter or digit (or the
     start/end of the name), so '_', '-', '.' and spaces all count. */
  const nonAlnum = '[^A-Za-z0-9]';
  for (const k of keys){
    const re = new RegExp('(?:^|' + nonAlnum + ')' + k + '(?:' + nonAlnum + '|$)', 'i');
    if (re.test(filename)) return k;
  }
  return null;
}
function applyBars(b, keepTrades, sym){
  BASE = b;  DATA_GEN++;   /* every cached view is now stale */
  dropTapeResults();
  if (sym !== undefined) LOADED_SYM = sym;
  /* auto-price for the market just detected, both stages: a new tape is a
     bigger event than clicking Instrument, and funded starts as a copy of
     eval's pricing anyway until the two are told to differ */
  if (sym){
    const z = INSTRUMENTS.filter(w => w.key === sym)[0];
    if (z){
      [ST, ST.funded].forEach(C => { C.pointValue = z.pv; C.commission = z.comm; });
      ST.slippage = z.slip[1];
    }
  }
  if (!keepTrades) TRADES = [];
  rebuild(); NAVPTS = null; reindexSessions(); lastSig = '';
  document.getElementById('sub').textContent =
    b.n.toLocaleString() + ' bars \u00b7 ' + b.sessions.length + ' sessions \u00b7 ' +
    TRADES.length.toLocaleString() + ' trades' + clockNote(b);
  setView(0, Math.min(V.n - 1, 390));
}
function applyTrades(t){
  TRADES = t; reindex(); reindexSessions(); lastSig = '';
  document.getElementById('sub').textContent =
    BASE.n.toLocaleString() + ' bars \u00b7 ' + BASE.sessions.length + ' sessions \u00b7 ' +
    t.length.toLocaleString() + ' trades';
  t.length ? gotoTrade(0) : render();
}
function loadFile(file, kind){
  const fr = new FileReader();
  fr.onload = () => {
    try {
      const txt = fr.result;
      const sym = detectSymbol(file.name);
      if (file.name.toLowerCase().endsWith('.json')){
        const j = JSON.parse(txt);
        if (j.bars && j.n){ applyBars(buildBars(j), false, sym);
          const jt = buildTrades(j); if (jt.length) applyTrades(jt); }
        else if (Array.isArray(j)) applyTrades(j);
        else if (j.trades) applyTrades(j.trades);
        else throw new Error('unrecognised JSON shape');
      } else {
        /* the header alone decides what the file is; parsing all of a
           300 MB bar file into strings just to read its first line is what
           used to exhaust the tab */
        const {head} = parseCSV(txt.slice(0, 4096));
        const isTrades = kind === 'trades' || head.some(x =>
          ['entry_time','entry_bar','exit_time','exit_bar','pnl'].indexOf(x) >= 0);
        isTrades ? applyTrades(tradesFromCSV(txt, BASE)) : applyBars(barsFromCSV(txt), false, sym);
      }
    } catch (err){
      document.getElementById('sub').textContent = 'Could not load ' + file.name + ' \u2014 ' + err.message;
    }
  };
  fr.readAsText(file);
}
document.getElementById('fbars').onchange = e => e.target.files[0] && loadFile(e.target.files[0], 'bars');
document.getElementById('ftrades').onchange = e => e.target.files[0] && loadFile(e.target.files[0], 'trades');
document.getElementById('demo').onclick = () => {
  BASE = BASE0; TRADES = TRADES0;  DATA_GEN++;   /* every cached view is now stale */
  dropTapeResults();
  /* the shipped tape is always NQ; without this, Demo after loading a
     different market left LOADED_SYM and the pricing pointed at it */
  LOADED_SYM = 'NQ';
  const nq = INSTRUMENTS.filter(z => z.key === 'NQ')[0];
  [ST, ST.funded].forEach(C => { C.pointValue = nq.pv; C.commission = nq.comm; });
  ST.slippage = nq.slip[1];
  rebuild(); NAVPTS = null; reindexSessions(); lastSig = '';
  document.getElementById('sub').textContent = RAW.subtitle;
  gotoTrade(0);
};
const dropEl = document.getElementById('drop');
let dragDepth = 0;
window.addEventListener('dragenter', e => { e.preventDefault(); dragDepth++; dropEl.classList.add('on'); });
window.addEventListener('dragover', e => e.preventDefault());
window.addEventListener('dragleave', () => { if (--dragDepth <= 0){ dragDepth = 0; dropEl.classList.remove('on'); } });
window.addEventListener('drop', e => {
  e.preventDefault(); dragDepth = 0; dropEl.classList.remove('on');
  Array.prototype.slice.call(e.dataTransfer.files).forEach(f => loadFile(f, null));
});

/* ---------------- go ---------------- */
document.getElementById('sub').textContent = RAW.subtitle;
document.getElementById('hint').textContent =
  'drag = pan  \u00b7  scroll = zoom  \u00b7  gutters scale each axis  \u00b7  ? for all shortcuts';
document.getElementById('navlbl').textContent = '';
function boot(){
  applyTheme(); applyLayout();
  rebuild(); reindexSessions(); indBadge();
  gotoTrade(0);
}
try {
  boot();
} catch (err){
  /* Almost the only way boot fails is a saved state this build cannot read.
     Throw it away and start clean rather than leaving the page unusable. */
  try { localStorage.removeItem('tape.v3'); localStorage.removeItem('tape.strat'); } catch(e){}
  try {
    boot();
    document.getElementById('sub').textContent =
      'Saved settings were from an older version and have been reset.';
  } catch (err2){
    showError('Startup', err2);
  }
}
</script>
"""

out = (HTML.replace('__CORE__', CORE)
           .replace('__DATA__', json.dumps(D, separators=(',', ':')))
           .replace('__SIZING__', json.dumps(SIZING, separators=(',', ':')))
           .replace('__WEALTH__', json.dumps(WEALTH, separators=(',', ':')))
           .replace('__LH5__', json.dumps(LH5, separators=(',', ':')))
           .replace('__RF2__', json.dumps(RF2, separators=(',', ':')))
           .replace('__BO__', json.dumps(BO, separators=(',', ':')))
           .replace('__NEWSCAL__', json.dumps(NEWSCAL, separators=(',', ':'))))
p = r'C:\Users\ruben\nq-backtest\tape_reader.html'
io.open(p, 'w', encoding='utf-8').write(out)
print(f'{p}  {len(out)/1e6:.2f} MB')
