#!/usr/bin/env python3
"""Envoy UI, step 1: visual direction + entry point. One review spread.

Writes spread.html beside this file and renders preview/spread.png (1600 px wide) with headless
Chromium, the same way the menu pipeline renders its studies. Original vector art only; fonts are
OFL (Source Sans 3, Barlow Condensed, Hasklug from the menu folder; Unbounded and Bricolage
Grotesque in fonts/).
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent

FLAME = "M0,-44 C16,-26 32,-10 32,14 C32,36 16,50 0,50 C-16,50 -32,36 -32,14 C-32,0 -22,-10 -17,-24 C-12,-14 -6,-14 0,-44Z"
FLAME_IN = "M0,-6 C8,4 14,12 14,24 C14,36 7,42 0,42 C-7,42 -14,36 -14,24 C-14,14 -6,8 0,-6Z"
RULE = "Every 4th hit: a fire burst, 6% and Burning."
NEXT = "Level 3 hits every foe near the target."

CSS = r"""
@font-face{font-family:"SS3";src:url("../SourceSans3/SourceSans3-Semibold.otf");font-weight:600}
@font-face{font-family:"SS3";src:url("../SourceSans3/SourceSans3-Bold.otf");font-weight:700}
@font-face{font-family:"SS3";src:url("../SourceSans3/SourceSans3-Black.otf");font-weight:900}
@font-face{font-family:"BarlowC";src:url("../Barlow/BarlowCondensed-SemiBold.ttf");font-weight:600}
@font-face{font-family:"BarlowC";src:url("../Barlow/BarlowCondensed-Bold.ttf");font-weight:700}
@font-face{font-family:"Hask";src:url("../Hasklug/HasklugNerdFontMono-SemiBold.otf");font-weight:600}
@font-face{font-family:"Unbounded";src:url("fonts/Unbounded.ttf");font-weight:200 900}
@font-face{font-family:"Brico";src:url("fonts/BricolageGrotesque.ttf");font-weight:200 800}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:#E6E5EC}
body{width:1600px;font-family:"SS3";font-weight:600;color:#1A1830;-webkit-font-smoothing:antialiased}
#c{width:1600px;padding:44px 40px 40px}
.top{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:34px}
.top h1{font-weight:900;font-size:54px;line-height:1;letter-spacing:-1px}
.top p{font-size:19px;line-height:1.35;max-width:640px;color:#45425E;text-align:right}
h2{font-weight:900;font-size:30px;line-height:1.1;margin-bottom:6px}
.lede{font-size:17px;color:#45425E;margin-bottom:18px;max-width:1100px;line-height:1.35}
.sec{margin-bottom:44px}

/* ---------- directions ---------- */
.dirs{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
.dir{border-radius:18px;padding:28px 28px 30px}
.dir .head{display:flex;align-items:baseline;gap:16px;margin-bottom:8px}
.dir .letter{font-size:76px;line-height:.9}
.dir .name{font-size:34px;line-height:1}
.dir .idea{font-size:17px;line-height:1.35;min-height:70px;margin-bottom:18px}
.dir h3{font-family:"SS3";font-weight:700;font-size:14px;margin:0 0 8px;opacity:.78}
.sw{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:8px}
.sw i{display:block;height:38px;border-radius:6px;margin-bottom:5px}
.sw b{display:block;font-weight:700;font-size:13px;line-height:1.15}
.sw span{font-family:"Hask";font-size:11px;opacity:.8}
.fam{font-size:13.5px;line-height:1.3;margin-bottom:20px;opacity:.9}
.spec{margin-bottom:22px}
.spec .big{font-size:42px;line-height:1.05;white-space:nowrap}
.spec .roles{font-size:13.5px;line-height:1.3;margin-top:6px;opacity:.9}
.samples{display:grid;grid-template-columns:184px 1fr;gap:18px;align-items:start}
.samples .lab{font-family:"SS3";font-weight:700;font-size:14px;margin-bottom:10px;opacity:.78}

/* A: Orrery */
.A{background:#0E1230;color:#F3EEDC}
.A .letter,.A .name,.A .spec .big{font-family:"Unbounded";font-weight:700}
.A .name{font-weight:600}
.A .sw i{box-shadow:inset 0 0 0 1px rgba(243,238,220,.25)}
.a-card{width:184px;padding-bottom:18px;background:#1B2052;border-radius:92px 92px 16px 16px;box-shadow:inset 0 0 0 1.5px rgba(243,238,220,.28);overflow:hidden}
.a-card svg{display:block}
.a-card .t{padding:0 16px}
.a-card .nm{font-family:"Unbounded";font-weight:600;font-size:22px;line-height:1.1}
.a-card .lv{font-size:13px;color:#FFC83D;margin:3px 0 9px}
.a-card .rule{font-size:15px;line-height:1.28}
.a-card .nx{font-size:12.5px;line-height:1.25;color:#B9B6CF;margin-top:9px;padding-top:8px;border-top:1px solid rgba(243,238,220,.2)}
.a-hud{width:227px;height:230px;background:#171B45;border-radius:16px}

/* B: Overdrive */
.B{background:#1C5A4A;color:#EDE4D0}
.B .letter,.B .name,.B .spec .big{font-family:"BarlowC";font-weight:700;text-transform:uppercase;letter-spacing:.5px}
.B .sw i{box-shadow:inset 0 0 0 1.5px rgba(237,228,208,.45)}
.B .letter{font-size:92px}.B .name{font-size:44px}.B .spec .big{font-size:54px}
.b-card{width:184px;position:relative;padding-bottom:16px}
.b-card .body{background:#EDE4D0;color:#10201B;border-radius:6px;border:3px solid #10201B;overflow:hidden}
.b-card .plate{background:#10201B;color:#EDE4D0;padding:9px 12px 7px;display:flex;justify-content:space-between;align-items:flex-end}
.b-card .plate b{font-family:"BarlowC";font-weight:700;font-size:40px;line-height:.9;text-transform:uppercase;letter-spacing:1px}
.b-card .plate span{font-family:"Hask";font-size:11px;color:#FF8A3D}
.b-card .win{margin:12px 12px 0;background:#10201B;border-radius:4px;padding:9px 10px;color:#EDE4D0}
.b-card .win .k{font-family:"Hask";font-size:10.5px;display:flex;justify-content:space-between;margin-bottom:6px}
.seg{display:flex;gap:4px}
.seg i{flex:1;height:16px;background:#2C4A41;border-radius:2px}
.seg i.on{background:#FF6A13}
.lamps{display:flex;align-items:center;gap:7px;margin:10px 12px 0;font-family:"Hask";font-size:11px}
.lamps i{width:15px;height:15px;border-radius:50%;border:2.5px solid #10201B;background:#CFC6B2}
.lamps i.on{background:#FFD02A}
.b-card .rule{padding:10px 12px 0;font-size:15px;line-height:1.28;font-weight:700}
.b-card .nx{padding:7px 12px 13px;font-size:12.5px;line-height:1.25;color:#3F5049}
.b-card .pins{position:absolute;left:22px;right:22px;bottom:0;height:16px;display:flex;gap:6px}
.b-card .pins i{flex:1;background:#FFD02A;border:3px solid #10201B;border-top:0;border-radius:0 0 3px 3px}
.b-hud{width:227px;background:#10201B;border-radius:6px;padding:12px;color:#EDE4D0}
.b-hud .row1{display:flex;align-items:flex-end;gap:10px}
.b-hud .p{background:#FF6A13;color:#10201B;font-family:"BarlowC";font-weight:700;font-size:22px;padding:1px 8px;border-radius:3px;margin-bottom:9px}
.b-hud .pct{font-family:"BarlowC";font-weight:700;font-size:70px;line-height:.85}
.b-hud .pct small{font-size:34px}
.b-hud .fuses{margin-left:auto;text-align:right;font-family:"Hask";font-size:10px;color:#A9C2B8}
.b-hud .fuses div{display:flex;gap:3px;margin-top:5px}
.b-hud .fuses i{width:10px;height:24px;background:#FFD02A;border-radius:2px}
.b-hud .fuses i.off{background:none;box-shadow:inset 0 0 0 2px #46675C}
.bays{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:12px}
.bay{background:#1C3B33;border-radius:4px;padding:7px 7px 8px}
.bay b{display:block;font-family:"BarlowC";font-weight:700;font-size:17px;text-transform:uppercase;letter-spacing:.6px;line-height:1}
.bay .seg{margin:6px 0 6px}.bay .seg i{height:11px}
.bay .seg.v i.on{background:#B79CFF}
.bay .dots{display:flex;gap:4px}
.bay .dots i{width:8px;height:8px;border-radius:50%;background:#35564C}
.bay .dots i.on{background:#FFD02A}
.bay.empty{background:repeating-linear-gradient(135deg,#1C3B33 0 6px,#17302A 6px 12px)}
.bay.empty b{color:#7FA296}
.keysw{margin-top:8px;border:2px solid #FFD02A;border-radius:4px;padding:6px 8px;display:flex;align-items:center;gap:8px;font-family:"BarlowC";font-weight:700;font-size:17px;text-transform:uppercase;letter-spacing:.6px}
.keysw i{width:12px;height:12px;border-radius:50%;background:#FFD02A}
.keysw span{font-family:"Hask";font-size:10px;color:#A9C2B8;margin-left:auto;text-transform:none;letter-spacing:0}

/* C: Party pack */
.C{background:#FFD84A;color:#2A1A6E}
.C .letter,.C .name,.C .spec .big{font-family:"Brico";font-weight:800;letter-spacing:-1px}
.C .name{font-size:38px}
.C .sw i{box-shadow:inset 0 0 0 2.5px #2A1A6E}
.c-card{width:176px;margin:6px 0 0 6px;background:#fff;border:4px solid #2A1A6E;border-radius:20px;box-shadow:7px 8px 0 #2A1A6E;transform:rotate(-2.2deg);position:relative}
.c-card .art{background:#FF4D6D;border-radius:14px 14px 0 0;border-bottom:4px solid #2A1A6E;height:122px}
.c-card .burst{position:absolute;right:-12px;top:128px}
.c-card .t{padding:10px 13px 13px}
.c-card .nm{font-family:"Brico";font-weight:800;font-size:31px;line-height:1;letter-spacing:-.5px}
.c-card .stars{display:flex;gap:3px;margin:5px 0 7px}
.c-card .rule{font-size:15px;line-height:1.28;font-weight:700}
.c-card .nx{font-size:12.5px;line-height:1.25;margin-top:7px;color:#5A4C99}
.c-hud{width:227px;height:262px;position:relative}
.c-hud .blob{position:absolute;left:4px;top:14px;background:#fff;border:4px solid #2A1A6E;border-radius:26px 26px 26px 8px;box-shadow:5px 6px 0 #2A1A6E;padding:2px 16px 4px;font-family:"Brico";font-weight:800;font-size:58px;line-height:1.05;letter-spacing:-2px}
.c-hud .blob small{font-size:30px;letter-spacing:0}
.c-hud .p{position:absolute;left:-2px;top:0;background:#FF4D6D;color:#fff;border:3px solid #2A1A6E;border-radius:9px;font-family:"Brico";font-weight:800;font-size:16px;padding:0 8px;transform:rotate(-7deg);z-index:2}
.c-hud .stk{position:absolute;right:0;top:16px;text-align:right;font-family:"Brico";font-weight:800;font-size:14px;line-height:1.1}
.c-hud .stk div{display:flex;gap:3px;justify-content:flex-end;margin-top:5px}
.c-hud .stk i{width:13px;height:13px;border-radius:50%;background:#FF4D6D;border:2.5px solid #2A1A6E}
.c-hud .stk i.off{background:none}
.pogs{position:absolute;left:0;top:112px;display:flex;gap:9px}
.pog{width:66px;text-align:center;font-family:"Brico";font-weight:800;font-size:14px;line-height:1.1}
.pog svg{display:block;margin:0 auto 3px}
.pog small{display:block;font-family:"SS3";font-weight:700;font-size:11.5px}
.c-hud .key{position:absolute;left:0;top:214px;background:#2A1A6E;color:#FFD84A;border-radius:12px;padding:6px 12px 7px;font-family:"Brico";font-weight:800;font-size:16px;transform:rotate(1.5deg);display:flex;gap:8px;align-items:center}

/* ---------- entry ---------- */
.opt{display:grid;grid-template-columns:232px 1fr 262px;gap:22px;background:#F6F5FA;border-radius:18px;padding:22px 22px 20px;margin-bottom:16px;align-items:start}
.opt .num{font-weight:900;font-size:66px;line-height:.9}
.opt .nm{font-weight:900;font-size:25px;line-height:1.1;margin:8px 0 8px}
.opt .way{font-size:15.5px;line-height:1.35;color:#45425E;margin-bottom:10px}
.opt .trade{font-size:15.5px;line-height:1.35;font-weight:700;border-left:4px solid #1A1830;padding-left:10px}
.flow{display:flex;align-items:flex-start}
.step{width:240px}
.step .cap{font-size:14px;line-height:1.25;margin-top:8px;color:#45425E}
.step .cap b{color:#1A1830;font-weight:700}
.arr{width:34px;height:180px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#45425E;gap:3px}
.miss{border-left:2px dashed #B9B6CF;padding-left:20px}
.miss .tag{font-weight:700;font-size:14px;margin-bottom:8px;color:#8A4B00}
.miss .step{margin-top:0}
.scr{width:240px;height:180px;background:#262B3A;border-radius:8px;position:relative;overflow:hidden;color:#E9EBF2;font-size:11.5px;font-weight:700}
.scr .ttl{position:absolute;left:12px;top:9px;font-size:11.5px;color:#9AA1B5}
.rows{position:absolute;left:12px;top:30px;width:106px}
.rows div{height:17px;line-height:17px;padding-left:8px;background:#353C52;margin-bottom:3px;border-radius:2px;white-space:nowrap}
.rows .on{background:#5CF0B4;color:#0F2A22}
.rows .lock{background:#3A3524;color:#FFC247}
.pv{position:absolute;left:128px;top:30px;width:100px;height:117px;border-radius:4px;background:repeating-linear-gradient(135deg,#30374B 0 7px,#2B3144 7px 14px);display:flex;align-items:center;justify-content:center;text-align:center;color:#9AA1B5;font-size:10.5px;line-height:1.25;padding:6px}
.pv.env{background:#1E3A36;color:#DFFBEF;box-shadow:inset 0 0 0 2px #5CF0B4;flex-direction:column;gap:5px}
.pv.env b{font-weight:900;font-size:19px;color:#5CF0B4}
.pv.warn{background:#3A3524;color:#FFE2A6;box-shadow:inset 0 0 0 2px #FFC247;flex-direction:column;gap:4px}
.pv.warn b{font-weight:900;font-size:14px;color:#FFC247}
.desc{position:absolute;left:12px;right:12px;bottom:8px;height:20px;line-height:20px;background:#1B1F2B;border-radius:2px;padding-left:8px;font-size:10.5px;color:#C7CCDA;white-space:nowrap;overflow:hidden}
.desc.warn{color:#FFC247}
.ph{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px}
.ph .box{width:150px;height:62px;border-radius:4px;background:repeating-linear-gradient(135deg,#30374B 0 7px,#2B3144 7px 14px);display:flex;align-items:center;justify-content:center;color:#9AA1B5;font-size:11px}
.ph .ps{font-size:13px}
.fork{position:absolute;left:12px;right:12px;top:30px;bottom:34px;display:grid;grid-template-columns:1fr 1fr;gap:8px}
.fork div{border-radius:5px;background:#353C52;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:4px;padding:6px;font-size:10.5px;line-height:1.25;color:#C7CCDA}
.fork b{font-weight:900;font-size:21px;color:#E9EBF2}
.fork .on{background:#1E3A36;box-shadow:inset 0 0 0 2px #5CF0B4}.fork .on b{color:#5CF0B4}
.fork .lock{background:#3A3524;box-shadow:inset 0 0 0 2px #FFC247;color:#FFE2A6}.fork .lock b{color:#FFC247}
.dlg{position:absolute;left:26px;right:26px;top:36px;background:#3A3524;box-shadow:0 0 0 2px #FFC247,0 0 0 200px rgba(20,22,30,.62);border-radius:5px;padding:11px 12px 10px;font-size:12px;line-height:1.3;color:#FFE2A6}
.dlg b{display:block;font-weight:900;font-size:14.5px;color:#FFC247;margin-bottom:4px}
.dlg u{display:inline-block;text-decoration:none;background:#FFC247;color:#2A2410;border-radius:2px;padding:1px 10px;margin-top:8px}
.camp{position:absolute;inset:0}
.camp .menu{position:absolute;right:10px;top:28px;width:104px}
.camp .menu div{height:17px;line-height:17px;padding-left:7px;background:#353C52;margin-bottom:3px;border-radius:2px;font-size:10.5px;white-space:nowrap}
.camp .menu .on{background:#5CF0B4;color:#0F2A22}

/* ---------- recommendation ---------- */
.rec{background:#1A1830;color:#F6F5FA;border-radius:18px;padding:26px 30px;display:grid;grid-template-columns:150px 1fr 1fr;gap:30px;align-items:start}
.rec h2{font-size:24px;margin:0}
.rec p{font-size:18px;line-height:1.38}
.rec b{font-weight:900;color:#5CF0B4}
.foot{margin-top:14px;font-size:13.5px;color:#5A5775;line-height:1.35}
"""


def swatches(items):
    return '<div class="sw">' + "".join(
        f'<div><i style="background:{h}"></i><b>{n}</b><span>{h}</span></div>' for n, h in items) + "</div>"


# ---------------------------------------------------------------- A: Orrery
def a_card():
    art = f"""
<svg width="184" height="158" viewBox="0 0 184 158">
  <ellipse cx="92" cy="92" rx="74" ry="26" fill="none" stroke="#F3EEDC" stroke-opacity=".3" stroke-width="1.5"/>
  <ellipse cx="92" cy="92" rx="50" ry="17" fill="none" stroke="#F3EEDC" stroke-opacity=".2" stroke-width="1.5"/>
  <circle cx="92" cy="86" r="40" fill="#FF5A3C" opacity=".16"/>
  <g transform="translate(92 84) scale(.62)">
    <path d="{FLAME}" fill="#FF5A3C"/><path d="{FLAME_IN}" fill="#FFC83D"/>
  </g>
  <path d="M18,92 A74,26 0 0 0 166,92" fill="none" stroke="#F3EEDC" stroke-opacity=".75" stroke-width="1.5"/>
  <circle cx="44" cy="112" r="7" fill="#FFC83D"/>
  <circle cx="118" cy="116.5" r="7" fill="#FFC83D"/>
  <circle cx="160" cy="102" r="6" fill="#1B2052" stroke="#F3EEDC" stroke-opacity=".7" stroke-width="1.5" stroke-dasharray="3 3"/>
</svg>"""
    return f"""<div class="a-card">{art}<div class="t">
  <div class="nm">Ember</div><div class="lv">Level 2 of 3: two moons lit</div>
  <div class="rule">{RULE}</div><div class="nx">{NEXT}</div></div></div>"""


def a_hud():
    return """
<svg class="a-hud" width="227" height="230" viewBox="0 0 227 230" font-family="SS3">
  <circle cx="84" cy="116" r="64" fill="none" stroke="#F3EEDC" stroke-opacity=".32" stroke-width="1.5"/>
  <text x="84" y="128" text-anchor="middle" font-family="Unbounded" font-weight="700" font-size="34" fill="#F3EEDC">47<tspan font-size="18">%</tspan></text>
  <rect x="12" y="12" width="34" height="22" rx="11" fill="#F3EEDC"/>
  <text x="29" y="28" text-anchor="middle" font-family="Unbounded" font-weight="700" font-size="12" fill="#0E1230">P1</text>
  <!-- keystone: a crown point on top of the orbit -->
  <path d="M84,38 L93,52 L84,66 L75,52Z" fill="#FFC83D"/>
  <text x="100" y="42" font-weight="700" font-size="12" fill="#FFC83D">Plague Bearer</text>
  <!-- Ember: charge 3 of 4, level 2 -->
  <circle cx="137" cy="80" r="19" fill="#171B45"/>
  <circle cx="137" cy="80" r="19" fill="none" stroke="#F3EEDC" stroke-opacity=".25" stroke-width="4"/>
  <circle cx="137" cy="80" r="19" fill="none" stroke="#FFC83D" stroke-width="4" stroke-dasharray="89.5 119.4" transform="rotate(-90 137 80)"/>
  <circle cx="137" cy="80" r="12" fill="#FF5A3C"/>
  <circle cx="163" cy="68" r="3.5" fill="#FFC83D"/><circle cx="166" cy="79" r="3.5" fill="#FFC83D"/>
  <text x="166" y="100" font-weight="700" font-size="13" fill="#F3EEDC">Ember</text>
  <text x="166" y="115" font-weight="600" font-size="12" fill="#B9B6CF">3 of 4 hits</text>
  <!-- Frost: charge 1 of 4, level 1 -->
  <circle cx="24" cy="138" r="16" fill="#171B45"/>
  <circle cx="24" cy="138" r="16" fill="none" stroke="#F3EEDC" stroke-opacity=".25" stroke-width="4"/>
  <circle cx="24" cy="138" r="16" fill="none" stroke="#FFC83D" stroke-width="4" stroke-dasharray="25.1 100.5" transform="rotate(-90 24 138)"/>
  <circle cx="24" cy="138" r="9.5" fill="#9B7CFF"/>
  <circle cx="45" cy="127" r="3.5" fill="#FFC83D"/>
  <text x="8" y="172" font-weight="700" font-size="13" fill="#F3EEDC">Frost</text>
  <!-- empty slot -->
  <circle cx="96" cy="179" r="11" fill="#171B45" stroke="#F3EEDC" stroke-opacity=".6" stroke-width="1.5" stroke-dasharray="3 3"/>
  <!-- shared pool -->
  <text x="215" y="176" text-anchor="end" font-weight="700" font-size="12" fill="#B9B6CF">Shared stocks</text>
  <g fill="#F3EEDC"><circle cx="153" cy="194" r="5.5"/><circle cx="168" cy="194" r="5.5"/><circle cx="183" cy="194" r="5.5"/><circle cx="198" cy="194" r="5.5"/></g>
  <circle cx="211" cy="194" r="4.5" fill="none" stroke="#F3EEDC" stroke-opacity=".5" stroke-width="1.5"/>
</svg>"""


# ---------------------------------------------------------------- B: Overdrive
def b_card():
    return f"""<div class="b-card"><div class="body">
  <div class="plate"><b>Ember</b><span>RED 01</span></div>
  <div class="win"><div class="k"><span>charge</span><span>4 hits</span></div>
    <div class="seg"><i class="on"></i><i class="on"></i><i class="on"></i><i></i></div></div>
  <div class="lamps"><i class="on"></i><i class="on"></i><i></i><span>level 2 of 3</span></div>
  <div class="rule">{RULE}</div><div class="nx">{NEXT}</div>
</div><div class="pins"><i></i><i></i><i></i><i></i><i></i><i></i></div></div>"""


def b_hud():
    return """<div class="b-hud">
  <div class="row1"><span class="p">P1</span><span class="pct">47<small>%</small></span>
    <span class="fuses">shared stocks<div><i></i><i></i><i></i><i></i><i class="off"></i></div></span></div>
  <div class="bays">
    <div class="bay"><b>Ember</b><div class="seg"><i class="on"></i><i class="on"></i><i class="on"></i><i></i></div><div class="dots"><i class="on"></i><i class="on"></i><i></i></div></div>
    <div class="bay"><b>Frost</b><div class="seg v"><i class="on"></i><i></i><i></i><i></i></div><div class="dots"><i class="on"></i><i></i><i></i></div></div>
    <div class="bay empty"><b>Open bay</b></div>
  </div>
  <div class="keysw"><i></i>Plague Bearer<span>keystone</span></div>
</div>"""


# ---------------------------------------------------------------- C: Party pack
STAR = "M0,-10 L3,-3.2 L10.2,-3 L4.6,1.6 L6.4,8.8 L0,4.8 L-6.4,8.8 L-4.6,1.6 L-10.2,-3 L-3,-3.2Z"


def star(on):
    fill, extra = ("#FFD84A", "") if on else ("#fff", ' stroke-opacity=".35" stroke-dasharray="2.5 2.5"')
    return f'<svg width="24" height="24" viewBox="-12 -12 24 24"><path d="{STAR}" fill="{fill}" stroke="#2A1A6E" stroke-width="2.4" stroke-linejoin="round"{extra}/></svg>'


def c_card():
    art = f"""<svg width="168" height="118" viewBox="0 0 168 118">
  <g fill="#fff" opacity=".35"><circle cx="24" cy="26" r="5"/><circle cx="48" cy="92" r="4"/><circle cx="142" cy="34" r="6"/><circle cx="128" cy="96" r="4"/></g>
  <g transform="translate(84 60) scale(.98)">
    <path d="{FLAME}" fill="#FFD84A" stroke="#2A1A6E" stroke-width="5" stroke-linejoin="round"/>
    <path d="{FLAME_IN}" fill="#fff" stroke="#2A1A6E" stroke-width="4" stroke-linejoin="round"/>
  </g></svg>"""
    burst = """<svg class="burst" width="58" height="58" viewBox="-29 -29 58 58">
  <path d="M0,-27 L7,-17 L19,-19 L17,-7 L27,0 L17,7 L19,19 L7,17 L0,27 L-7,17 L-19,19 L-17,7 L-27,0 L-17,-7 L-19,-19 L-7,-17Z" fill="#00A99D" stroke="#2A1A6E" stroke-width="3.5" stroke-linejoin="round"/>
  <text x="0" y="6" text-anchor="middle" font-family="Brico" font-weight="800" font-size="17" fill="#fff">Lv 2</text></svg>"""
    return f"""<div class="c-card"><div class="art">{art}</div>{burst}<div class="t">
  <div class="nm">Ember</div><div class="stars">{star(1)}{star(1)}{star(0)}</div>
  <div class="rule">{RULE}</div><div class="nx">{NEXT}</div></div></div>"""


def pog(fill, frac, icon, name, sub):
    c = 2 * 3.14159 * 25
    ring = f'<circle cx="0" cy="0" r="25" fill="none" stroke="#2A1A6E" stroke-width="7" stroke-dasharray="{c*frac:.1f} {c:.1f}" transform="rotate(-90)"/>' if frac else ""
    return f"""<div class="pog"><svg width="62" height="62" viewBox="-31 -31 62 62">
  <circle r="25" fill="#fff" stroke="#2A1A6E" stroke-opacity=".28" stroke-width="7"/>{ring}
  <circle r="19" fill="{fill}" stroke="#2A1A6E" stroke-width="3"/>{icon}</svg>{name}<small>{sub}</small></div>"""


def c_hud():
    flame = f'<g transform="scale(.3)"><path d="{FLAME}" fill="#FFD84A" stroke="#2A1A6E" stroke-width="9" stroke-linejoin="round"/></g>'
    flake = '<g stroke="#fff" stroke-width="3.6" stroke-linecap="round"><path d="M0,-11V11M-9.5,-5.5L9.5,5.5M-9.5,5.5L9.5,-5.5"/></g>'
    empty = """<div class="pog"><svg width="62" height="62" viewBox="-31 -31 62 62">
  <circle r="22" fill="none" stroke="#2A1A6E" stroke-width="3" stroke-dasharray="6 6"/>
  <path d="M0,-8V8M-8,0H8" stroke="#2A1A6E" stroke-width="3.5" stroke-linecap="round"/></svg>Free<small>slot</small></div>"""
    return f"""<div class="c-hud">
  <span class="p">P1</span><div class="blob">47<small>%</small></div>
  <div class="stk">Team<br>stocks<div><i></i><i></i><i></i><i></i><i class="off"></i></div></div>
  <div class="pogs">{pog('#FF4D6D', .75, flame, 'Ember', '3 of 4 hits')}{pog('#00A99D', .25, flake, 'Frost', '1 of 4 hits')}{empty}</div>
  <div class="key"><svg width="20" height="20" viewBox="-12 -12 24 24"><path d="{STAR}" fill="#FFD84A"/></svg>Plague Bearer</div>
</div>"""


def direction(cls, letter, name, idea, pal, fam, big, roles, card, hud):
    return f"""<div class="dir {cls}">
  <div class="head"><span class="letter">{letter}</span><span class="name">{name}</span></div>
  <p class="idea">{idea}</p>
  <h3>Palette</h3>{swatches(pal)}<p class="fam">{fam}</p>
  <h3>Type</h3><div class="spec"><div class="big">{big}</div><p class="roles">{roles}</p></div>
  <div class="samples"><div><div class="lab">Drive card</div>{card}</div>
  <div><div class="lab">In-fight HUD, one player</div>{hud}</div></div>
</div>"""


# ---------------------------------------------------------------- entry mocks
def scr(inner):
    return f'<div class="scr">{inner}</div>'


def step(screen, cap):
    return f'<div class="step">{screen}<p class="cap">{cap}</p></div>'


def arrow(label):
    return f"""<div class="arr"><span>{label}</span><svg width="26" height="14" viewBox="0 0 26 14"><path d="M1,7H22M16,1.5L23,7L16,12.5" fill="none" stroke="#45425E" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg></div>"""


def rows(items):
    out = ""
    for it in items:
        cls, txt = ("", it) if isinstance(it, str) else it
        out += f'<div class="{cls}">{txt}</div>'
    return f'<div class="rows">{out}</div>'


TITLE = scr('<div class="ph"><div class="box">title screen (retail)</div><div class="ps">Press Start</div></div>')
PV_RETAIL = '<div class="pv">retail 3D panel</div>'
PV_ENVOY = '<div class="pv env"><b>Envoy</b>Continue run<br>act 2, fight 3</div>'
MSG = "Add it in the launcher, then restart the game."

CAMP = scr("""<div class="camp"><span class="ttl">Envoy camp</span>
<svg width="240" height="180" viewBox="0 0 240 180" style="position:absolute;inset:0">
  <rect x="0" y="146" width="240" height="34" fill="#1B1F2B"/>
  <path d="M14,146 L50,84 L86,146Z" fill="#353C52"/><path d="M50,84 L50,146 L66,146Z" fill="#262B3A"/>
  <g fill="#4A536E"><rect x="86" y="108" width="15" height="38" rx="7.5"/><circle cx="93.5" cy="98" r="8"/>
  <rect x="108" y="114" width="14" height="32" rx="7"/><circle cx="115" cy="105" r="7.5"/></g>
  <path d="M98,160 C98,152 104,150 104,143 C109,148 112,152 112,160Z" fill="#5CF0B4"/>
</svg>
<div class="menu"><div class="on">Start run</div><div>Fighters</div><div>Team attack: off</div><div>NG+ level 0</div><div>Unlocks</div><div>Back</div></div>
<div class="desc" style="left:10px;right:10px">Shared stocks: 5. Two players.</div></div>""")
CAMP_CAP = "<b>Camp.</b> Set up the run, then start."


def option(num, name, way, trade, flow, miss, miss_cap):
    return f"""<div class="opt">
  <div><div class="num">{num}</div><div class="nm">{name}</div><p class="way">{way}</p><p class="trade">{trade}</p></div>
  <div class="flow">{flow}</div>
  <div class="miss"><div class="tag">Without the Brawl disc</div>{step(miss, miss_cap)}</div>
</div>"""


def entry():
    main6 = ["1-P Mode", "Vs. Mode", ("on", "Envoy"), "Trophies", "Options", "Data"]
    o1 = option(
        1, "A row on the main menu",
        "Envoy sits between Vs. Mode and Trophies, with its own panel on the right showing the saved run.",
        "One press from the main menu and always in view; the retail main menu has to grow from five rows to six.",
        step(scr('<span class="ttl">Main menu</span>' + rows(main6) + PV_ENVOY
                   + '<div class="desc">A co-op run for 1 or 2 players.</div>'),
               "<b>Main menu</b>, straight after Press Start. Envoy is a mode like the others.") + arrow("A")
        + step(CAMP, CAMP_CAP),
        scr('<span class="ttl">Main menu</span>' + rows(["1-P Mode", "Vs. Mode", ("lock", "Envoy"), "Trophies", "Options", "Data"])
            + PV_RETAIL + f'<div class="dlg"><b>Envoy needs your Brawl disc</b>{MSG}<br><u>Back</u></div>'),
        "The row stays and is marked. A opens this message; the camp never loads.")

    one_p = ["Regular Match", "Event Match", "Stadium", "Training", ("on", "Envoy")]
    o2 = option(
        2, "A real row inside 1-P Mode",
        "Same place as today, but built as a retail row: same panel, same cursor, same description bar. The mod browser row goes away.",
        "Changes the least and follows Melee's own menus; two menus deep, and a co-op mode sits under the name 1-P.",
        step(scr('<span class="ttl">Main menu</span>' + rows([("on", "1-P Mode"), "Vs. Mode", "Trophies", "Options", "Data"])
                   + PV_RETAIL + '<div class="desc">Play alone.</div>'), "<b>Main menu</b>, straight after Press Start. Unchanged.") + arrow("A")
        + step(scr('<span class="ttl">1-P Mode</span>' + rows(one_p) + PV_ENVOY
                   + '<div class="desc">A co-op run for 1 or 2 players.</div>'),
               "<b>1-P Mode.</b> Envoy is the fifth row.") + arrow("A")
        + step(CAMP, CAMP_CAP),
        scr('<span class="ttl">1-P Mode</span>' + rows(["Regular Match", "Event Match", "Stadium", "Training", ("lock", "Envoy")])
            + '<div class="pv warn"><b>Brawl disc needed</b>Add it in the launcher</div>'
            + '<div class="desc warn">Envoy needs your Brawl disc.</div>'),
        "The row is marked and cannot be entered; the panel and the bar say why.")

    o3 = option(
        3, "Its own door after the title",
        "Press Start, then choose Melee or Envoy. Envoy opens straight into the camp, which is its whole menu: run, fighters, unlocks, records.",
        "The strongest identity and the most room to grow; every boot gains one more choice, even for players who only want Vs.",
        step(TITLE, "<b>Title.</b> Unchanged.") + arrow("Start")
        + step(scr('<span class="ttl">Choose a game</span><div class="fork"><div><b>Melee</b>1-P, Vs., Trophies, Options, Data</div>'
                   '<div class="on"><b>Envoy</b>Continue run<br>act 2, fight 3</div></div>'
                   '<div class="desc">A co-op run for 1 or 2 players.</div>'),
               "<b>Fork.</b> Two halves of one game.") + arrow("A")
        + step(CAMP, CAMP_CAP),
        scr('<span class="ttl">Choose a game</span><div class="fork"><div><b>Melee</b>1-P, Vs., Trophies, Options, Data</div>'
            '<div class="lock"><b>Envoy</b>Brawl disc needed. Add it in the launcher.</div></div>'
            '<div class="desc warn">Envoy needs your Brawl disc.</div>'),
        "The Envoy half is marked and explains itself; Melee still opens.")
    return o1 + o2 + o3


def html():
    A = direction(
        "A", "A", "Orrery",
        "Drives already circle the fighter as 3D models. Draw every screen with that same picture: the fighter is the sun, a build is a sky that fills up.",
        [("Night", "#0E1230"), ("Dusk", "#2B3176"), ("Starlight", "#F3EEDC"), ("Sun", "#FFC83D"), ("Haze", "#B9B6CF")],
        "Each drive family brings its own colour as a body: red Ember, violet Frost. Gold is only ever charge and level.",
        "Ember 47%", "Unbounded for names and numbers; Source Sans 3 for rules.",
        a_card(), a_hud())
    B = direction(
        "B", "B", "Overdrive",
        "A drive is a part you plug into a machine. Cards are cartridges, the HUD is a rack of bays, and charge is a gauge that fills until it fires.",
        [("Enamel", "#1C5A4A"), ("Ink", "#10201B"), ("Bone", "#EDE4D0"), ("Signal", "#FF6A13"), ("Lamp", "#FFD02A")],
        "Family colour is the gauge colour: orange Ember, violet Frost. Yellow lamps count levels and stocks.",
        "Ember 47%", "Barlow Condensed for names and numbers; Hasklug for readouts; Source Sans 3 for rules.",
        b_card(), b_hud())
    C = direction(
        "C", "C", "Party pack",
        "A couch co-op toy box. Drives are stickers you collect and slap on your fighter; everything is die-cut, outlined in grape ink and a bit crooked.",
        [("Sunny", "#FFD84A"), ("Grape", "#2A1A6E"), ("Sticker", "#FFFFFF"), ("Coral", "#FF4D6D"), ("Lagoon", "#00A99D")],
        "Family colour fills the sticker: coral Ember, lagoon Frost. The grape outline carries charge.",
        "Ember 47%", "Bricolage Grotesque for names and numbers; Source Sans 3 for rules.",
        c_card(), c_hud())
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Envoy UI step 1</title><style>{CSS}</style></head>
<body><div id="c">
<div class="top"><h1>Envoy: the look and the way in</h1>
<p>Step 1 of the UI design. Two choices: a visual direction (A, B or C) and where Envoy lives in the menus (1, 2 or 3). Nothing else is designed yet.</p></div>

<div class="sec"><h2>Visual direction</h2>
<p class="lede">Each column shows the same two things: the Ember drive at level 2, and one player's HUD mid-fight (47%, Ember three hits into its four-hit charge, Frost, one free slot, the Plague Bearer keystone, four of five shared stocks).</p>
<div class="dirs">{A}{B}{C}</div></div>

<div class="sec"><h2>The way in</h2>
<p class="lede">Today Envoy is an extra row drawn under the 1-P menu by a mod, plus a line in the mod browser. Each option below replaces both. Screens are neutral placeholders in the shape of the retail menus; green marks what Envoy adds, amber marks the missing-disc state.</p>
{entry()}</div>

<div class="rec"><h2>Recommended</h2>
<p><b>Direction A, Orrery.</b> The game already shows power as things in orbit, so cards, HUD and menus reuse a picture the player has learned, and a stronger build is visibly a fuller sky.</p>
<p><b>Entry 1, a row on the main menu.</b> It is the only option that puts Envoy in view on every boot without adding a step for players who came for Vs.</p></div>
<p class="foot">Original vector art. Fonts: Source Sans 3, Barlow Condensed, Hasklug, Unbounded, Bricolage Grotesque (all SIL OFL). Fighter and menu shapes are neutral placeholders.</p>
</div></body></html>"""


def main():
    src = HERE / "spread.html"
    src.write_text(html(), encoding="utf-8")
    (HERE / "preview").mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1)
        page.goto(src.as_uri())
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(300)
        # report text that overflows its box
        bad = page.evaluate("""() => [...document.querySelectorAll('.scr *, .dir *, .opt *')].filter(e => e.children.length === 0 && (e.scrollWidth > e.clientWidth + 1) && getComputedStyle(e).display !== 'inline').map(e => e.className + ': ' + e.textContent.slice(0, 40))""")
        for b in bad:
            print("overflow:", b)
        page.locator("#c").screenshot(path=str(HERE / "preview" / "spread.png"), type="png")
        print(page.evaluate("document.getElementById('c').offsetHeight"))
        browser.close()


if __name__ == "__main__":
    main()
