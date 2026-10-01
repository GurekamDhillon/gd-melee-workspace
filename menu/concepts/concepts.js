/* concepts.js - five live navigation prototypes, drawn the way the kit draws.
 *
 * Everything is a quad list in UNSHEARED 640x480 coords. The shear is applied once, as
 * the outermost transform, which is the order hubs_layout.json documents: shear LAST,
 * after layout and motion. Toggle SHEAR off to see the raw rects the engine would store.
 * Motion runs on the frame counts in each concept's spec, at 60fps. */

const K = {
  ink:'#0a0e18', bone:'#f2efe4', muted:'#b8c2dc', gold:'#f0b429', goldLt:'#ffd766',
  goldDk:'#a9761a', dis:'#7d88a6', ok:'#27b88a', danger:'#e5483b',
};
const SEC = {
  versus:    {face:'#1e3a8c', bg:'#032568', band:'#012d7b', hi:'#9da2f8'},
  solo:      {face:'#6a4308', bg:'#4c2e01', band:'#583601', hi:'#dead77'},
  collection:{face:'#5a2a6e', bg:'#411255', band:'#4b1c5f', hi:'#c795d9'},
  options:   {face:'#2e3640', bg:'#19212a', band:'#212933', hi:'#959da7'},
  data:      {face:'#1c5a4a', bg:'#004234', band:'#084c3c', hi:'#90c7b5'},
};
const ROLE = {caption:12, body:14, row:16, label:20, title:24, heading:32, hero:44, display:56};
const SAFE = [32, 24, 608, 456];
const MS = 1000 / 60;
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
const TAU = Math.PI * 2;

/* the real menu tree, from gmfrontend_menus.inc */
const NAMES = ['MELEE','ONLINE','TOURNAMENT','SPECIAL MELEE','RULES','NAME ENTRY'];
const MAIN = [
  {t:'VERSUS',  sec:'versus',     d:'Up to four players. Your rules, your stage.'},
  {t:'SOLO',    sec:'solo',       d:'One player against the machine.'},
  {t:'TOY',     sec:'collection', d:'Trophies, figures and the lottery.'},
  {t:'EXTRA',   sec:'collection', d:'Melee with a twist.'},
  {t:'OPTIONS', sec:'options',    d:'The game, set to your taste.'},
  {t:'DATA',    sec:'data',       d:'Records, replays and messages.'},
  {t:'ONLINE',  sec:'versus',     d:'Host a room or join one.'},
];
const CHILD = [
  NAMES.map(n => ({t:n})),
  [{t:'TARGET TEST'},{t:'HOMERUN'},{t:'MULTI-MAN'}],
  [{t:'TROPHIES'},{t:'FIGURES'},{t:'LOTTERY'}],
  [{t:'SLO-MO MELEE'},{t:'KOSMOS'},{t:'INTRO'}],
  [{t:'CONTROLLERS'},{t:'RUMBLE'},{t:'DISPLAY'},{t:'SOUND'},{t:'LANGUAGE'},{t:'ERASE DATA'}],
  [{t:'MOVIES'},{t:'SNAPSHOTS'},{t:'SOUND TEST'},{t:'RECORDS'},{t:'SPECIAL MESSAGES'}],
  [{t:'HOST A ROOM'},{t:'JOIN BY CODE'},{t:'DIRECT'}],
];
const ROMAN = ['01','02','03','04','05','06','07','08','09','10','11','12','13'];

/* ---- primitives ----------------------------------------------------------------------------- */
function G(ctx) {
  const a = {};
  a.ctx = ctx;
  a.shear = on => {
    ctx.translate(0, 240);
    if (on) ctx.transform(1, 0, -0.25, 1, 0, 0);
    ctx.translate(0, -240);
  };
  /* scale about a point, unsheared - the joint pivot in the player */
  a.xf = (cx, cy, s, fn) => {
    if (s === 1) { fn(); return; }
    ctx.save(); ctx.translate(cx, cy); ctx.scale(s, s); ctx.translate(-cx, -cy);
    fn(); ctx.restore();
  };
  a.rect = (x, y, w, h, fill, al) => {
    ctx.globalAlpha = al === undefined ? 1 : al;
    ctx.fillStyle = fill; ctx.fillRect(x, y, w, h); ctx.globalAlpha = 1;
  };
  a.ring = (cx, cy, r, fill, lw) => {
    ctx.strokeStyle = fill; ctx.lineWidth = lw || 1;
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, TAU); ctx.stroke();
  };
  a.circle = (cx, cy, r, fill, al) => {
    ctx.globalAlpha = al === undefined ? 1 : al;
    ctx.fillStyle = fill; ctx.beginPath(); ctx.arc(cx, cy, r, 0, TAU); ctx.fill();
    ctx.globalAlpha = 1;
  };
  /* the icon bodies are placeholders - a plate with a hard-edged chevron */
  a.icon = (x, y, s, fill, al) => {
    a.rect(x, y, s, s, fill, al);
    ctx.globalAlpha = (al === undefined ? 1 : al);
    ctx.fillStyle = K.ink;
    ctx.beginPath();
    ctx.moveTo(x + s * .20, y + s * .30); ctx.lineTo(x + s * .80, y + s * .30);
    ctx.lineTo(x + s * .50, y + s * .76); ctx.closePath(); ctx.fill();
    ctx.globalAlpha = 1;
  };
  a.text = (s, x, y, role, fill, align, maxW, al) => {
    ctx.globalAlpha = al === undefined ? 1 : al;
    ctx.fillStyle = fill;
    ctx.font = '900 ' + ROLE[role] + 'px SS3, sans-serif';
    ctx.textAlign = align || 'left'; ctx.textBaseline = 'alphabetic';
    if (maxW) ctx.fillText(s, x, y, maxW); else ctx.fillText(s, x, y);
    ctx.globalAlpha = 1;
  };
  a.mono = (s, x, y, role, fill, align, al) => {
    ctx.globalAlpha = al === undefined ? 1 : al;
    ctx.fillStyle = fill;
    ctx.font = '900 ' + ROLE[role] + 'px Hask, monospace';
    ctx.textAlign = align || 'left';
    ctx.fillText(s, x, y); ctx.globalAlpha = 1;
  };
  a.meas = (s, role) => {
    ctx.font = '900 ' + ROLE[role] + 'px SS3, sans-serif';
    return ctx.measureText(s).width;
  };
  /* SECTION1.md's fit rule: step down the role chain, then truncate with an ellipsis */
  a.fit = (s, role, maxW, chain) => {
    let r = role;
    for (const nx of chain) { if (a.meas(s, r) <= maxW) return {s, r};
                              r = nx; if (a.meas(s, r) <= maxW) return {s, r}; }
    let t = s;
    while (t.length > 1 && a.meas(t + '…', role) > maxW) t = t.slice(0, -1);
    return {s: t + '…', r: role};
  };
  a.dash = (x0, y0, x1, y1, fill) => {
    ctx.save(); ctx.strokeStyle = fill; ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1);
    ctx.stroke(); ctx.restore();
  };
  a.outline = (x, y, w, h, fill, lw) => {
    ctx.strokeStyle = fill; ctx.lineWidth = lw || 1;
    ctx.strokeRect(x + .5, y + .5, w - 1, h - 1);
  };
  return a;
}

/* ---- shared kit chrome ---------------------------------------------------------------------- */
function bands(g, sec) {
  const B = {versus:[[18, 22], [572, 40]], solo:[[0, 64]],
             collection:[[560, 8], [576, 8], [592, 8]], options:[],
             data:[[16, 6], [30, 6], [44, 6], [586, 22]]}[sec] || [];
  for (const [x, w] of B) g.rect(x, -40, w, 560, SEC[sec].band);
}
function header(g, title, role, fill) {
  const w = g.meas(title, role);
  g.rect(84, 24, w + 60, 44, K.gold);
  g.text(title, 104, 58, role, K.ink);
  g.rect(84 + w + 56, 40, 100, 2, K.ink);
}
function descStrip(g, s, hint) {
  g.rect(90, 398, 506, 24, K.ink);
  if (s) g.text(s, 100, 415, 'body', K.bone, 'left', 486);
  g.rect(90, 430, 506, 26, K.ink);
  g.rect(100, 438, 6, 12, K.gold);
  g.text(hint, 114, 448, 'body', K.muted);
}
function crumb(g, sec, here) {
  g.icon(96, 62, 16, SEC[sec].hi);
  g.text('MAIN', 120, 74, 'body', K.muted);
  const x = 120 + g.meas('MAIN', 'body');
  g.rect(x + 6, 64, 2, 10, K.gold);
  g.text(here, x + 22, 74, 'body', K.bone);
}
function safeBox(g) {
  g.dash(SAFE[0], SAFE[1], SAFE[2], SAFE[1], 'rgba(240,180,41,.45)');
  g.dash(SAFE[0], SAFE[3], SAFE[2], SAFE[3], 'rgba(240,180,41,.45)');
  g.dash(SAFE[0], SAFE[1], SAFE[0], SAFE[3], 'rgba(240,180,41,.45)');
  g.dash(SAFE[2], SAFE[1], SAFE[2], SAFE[3], 'rgba(240,180,41,.45)');
}
const inside = (x, y, w, h) => x >= SAFE[0] && y >= SAFE[1] && x + w <= SAFE[2] && y + h <= SAFE[3];

/* ---- the shared child screen: the kit's list_layout.json -------------------------------------
 * Not one of the five concepts. This is the screen every one of them hands off to, and it is
 * why the long lists do not constrain the choice above it. */
function childScreen(g, C, t) {
  const sec = 'versus';
  const rows = C.childRows();
  C.csel = clamp(C.csel, 0, rows.length - 1);
  bands(g, sec);
  header(g, C.parentTitle(), 'heading');
  crumb(g, sec, C.parentTitle());
  const X0 = 96, X1 = 540, TOP = 84, PITCH = 34, RH = 30, VIS = 9;
  const first = clamp(C.csel - 4, 0, Math.max(0, rows.length - VIS));
  for (let i = 0; i < VIS; i++) {
    const k = first + i;
    if (k >= rows.length) break;
    const y = TOP + i * PITCH, on = k === C.csel;
    if (on) g.rect(X0 - 3, y - 3, X1 - X0 + 6, RH + 6, K.goldDk);   /* the plate */
    g.rect(X0, y, X1 - X0, RH, on ? K.gold : SEC[sec].face);
    g.text(rows[k].t, X0 + 16, y + 21, 'row', on ? K.ink : K.bone, 'left', 320);
    if (on) g.rect(X1 - 8, y + 12, 8, 6, K.ink);                     /* a second cue */
  }
  if (rows.length > VIS) {
    g.rect(548, 96, 6, 284, SEC[sec].bg);
    const th = Math.max(16, 284 * VIS / rows.length);
    const ty = 96 + (284 - th) * (C.csel / Math.max(1, rows.length - 1));
    g.rect(548, clamp(ty, 96, 96 + 284 - th), 6, th, SEC[sec].hi);
  }
  descStrip(g, C.parentDesc(), '▲▼ move   A select   B back to ' + C.name);
  g.mono(rows.length + ' rows', 596, 356, 'caption', K.muted, 'right');
  if (C.view.geo) { safeBox(g); g.outline(X0, TOP, X1 - X0, VIS * PITCH - 4, '#8fdef6');
    g.text('list_layout: x0 96 x1 540 pitch 34 row_h 30 visible 9', 96, 372, 'caption', '#8fdef6'); }
}

/* ---- concepts ------------------------------------------------------------------------------- */
const C = {};

/* ---- A · ORBIT ------------------------------------------------------------------------------ */
C.a = {
  key:'a', name:'A · Orbit', n:6, sel:0, csel:0, child:0, parent:0, anim:0,
  view:{shear:1, geo:0, fit:0}, note:'',
  items(n) { return Array.from({length:n}, (_, i) => MAIN[i % MAIN.length]); },
  childRows() { return CHILD[this.parent % CHILD.length]; },
  parentTitle() { return this.items(this.n)[this.parent].t; },
  parentDesc() { return this.items(this.n)[this.parent].d; },

  /* The ring rule, executable. The selected card is PULLED OUT of the ring and parks in
   * the reading slot below it, so the arc never has to route around it and no two cards
   * can collide at any n. Ring: centre (320, 268), R = 148, arc +/-78deg, card 76x100. */
  layout(sel, n) {
    const out = [];
    for (let r = 0; r < n; r++) {
      const d = ((r - sel) % n + n) % n;                /* 0 = the reading slot */
      if (d === 0) {
        out.push({d, x:262, y:250, w:116, h:150, a:1, role:'hero'});
      } else {
        const ang = (-78 + (d / n) * 156) * Math.PI / 180;
        out.push({d,
          x: 320 + 148 * Math.sin(ang) - 38,
          y: 268 - 148 * Math.cos(ang) - 50,
          w: 76, h: 100,
          a: [0, .62, .44, .32, .24, .19, .16, .14, .13][d],
          role: d === 1 ? 'heading' : d === 2 ? 'label' : null});
      }
    }
    return out;
  },
  move(d) { this.sel = (this.sel + d + this.n) % this.n; this.anim = performance.now(); },

  draw(g, t) {
    if (this.child) return childScreen(g, this, t);
    const items = this.items(this.n), cur = items[this.sel], sec = 'versus';
    const L = this.layout(this.sel, this.n);
    /* 10f travel with the 1.3x overshoot at f4 that row_select ships */
    const e = clamp((t - this.anim) / (10 * MS), 0, 1);
    const pop = e < .4 ? (e / .4) * 1.30 : 1.30 - .30 * ((e - .4) / .6);
    bands(g, sec);
    g.ring(320, 268, 148, 'rgba(157,162,248,.22)', 2);
    g.rect(84, 60, 478, 340, SEC[sec].bg);
    let out = 0;
    for (const c of L) {
      const it = items[(this.sel + c.d) % this.n];
      if (!inside(c.x, c.y, c.w, c.h)) out++;
      const cx = c.x + c.w / 2, cy = c.y + c.h / 2;
      g.xf(cx, cy, c.d === 0 ? (0.88 + 0.12 * pop) : 1, () => {
        if (c.d === 0) g.rect(c.x - 5, c.y - 5, c.w + 5, c.h + 5, K.goldDk);
        g.rect(c.x, c.y, c.w, c.h, c.d === 0 ? K.gold : SEC[sec].face, c.a);
        if (c.d === 0) g.rect(c.x - 8, c.y, 8, c.h, K.goldDk);
        const isz = c.d === 0 ? 44 : 34;
        g.icon(cx - isz / 2, c.y + (c.d === 0 ? 18 : 14), isz, K.ink, c.a);
        if (c.role) {
          const fit = g.fit(c.d === 0 ? it.t.toUpperCase() : it.t, c.role, c.w - 16,
                            ['heading', 'title', 'label', 'row', 'body']);
          g.text(fit.s, cx, c.y + c.h - (c.d === 0 ? 20 : 7), fit.r,
                 c.d === 0 ? K.ink : K.bone, 'center', c.w - 16, c.a);
        }
      });
      if (this.view.geo) {
        g.dash(c.x, c.y, c.x + c.w, c.y, 'rgba(143,222,246,.65)');
        g.text('rank ' + c.d + '  a=' + c.a.toFixed(2) + (c.role ? '  ' + c.role : '  icon only'),
               c.x, c.y - 4, 'caption', '#8fdef6');
      }
    }
    header(g, 'MAIN MENU', 'heading');
    descStrip(g, cur.d, '◄ ► turn the ring   A enter   B back');
    if (this.view.geo) { safeBox(g);
      g.text('ring centre (320,268) R=148 arc ±78° · card 76×100', 90, 350, 'caption', '#8fdef6');
      g.text('reading slot 262,250 116×150 — the card is pulled OUT of the arc', 90, 364,
             'caption', '#8fdef6'); }
    if (this.view.fit) { safeBox(g);
      g.text(out ? out + ' card(s) leave title-safe at n=' + this.n
                 : 'all ' + this.n + ' cards inside title-safe, including the 1.3× overshoot',
             90, 364, 'caption', out ? K.danger : K.ok); }
    this.note = this.n <= 6 ? 'every card keeps a label at n=' + this.n
      : 'at n=' + this.n + ' only ranks 0-2 are named; ' + (this.n - 3) + ' cards are icon-only';
  },
};

/* ---- B · FILMSTRIP ------------------------------------------------------------------------- */
C.b = {
  key:'b', name:'B · Filmstrip', n:6, sel:0, csel:0, child:0, parent:0, anim:0,
  view:{shear:1, geo:0, fit:0}, note:'',
  items(n) { return Array.from({length:n}, (_, i) => MAIN[(i + 1) % MAIN.length]); },
  childRows() { return CHILD[(this.parent + 1) % CHILD.length]; },
  parentTitle() { return this.items(this.n)[this.parent].t; },
  parentDesc() { return this.items(this.n)[this.parent].d; },
  move(d) { this.sel = clamp(this.sel + d, 0, this.n - 1); this.anim = performance.now(); },

  draw(g, t) {
    if (this.child) return childScreen(g, this, t);
    const items = this.items(this.n), cur = items[this.sel], s = SEC[cur.sec];
    const e = clamp((t - this.anim) / (7 * MS), 0, 1);          /* scroll is 7f */
    bands(g, cur.sec);
    g.rect(90, 24, 566, 2, K.gold);
    g.text(cur.sec.toUpperCase(), 90, 52, 'title', K.bone);
    /* the strip: cards ahead of the selection, decaying in scale AND contrast */
    for (let k = 3; k >= 1; k--) {
      const i = this.sel + k;
      if (i >= this.n) continue;
      const sc = Math.pow(.86, k);
      const x = 372 + (i - this.sel) * 64 * e, y = 168 + k * 10;
      const w = 64 * sc, h = 88 * sc;
      g.rect(x, y, w, h, s.face);
      g.rect(x, y, w, 3, s.hi);                              /* a bright cap edge */
      g.rect(x + 6, y + 8, w - 12, (h - 16) * .55, s.bg);   /* the artwork well */
      g.text(items[i].t, x + w / 2, y + h - 6, 'caption', K.bone, 'center', w - 4);
    }
    /* the reading slot: the chosen card flies in over 10f */
    const fe = clamp((t - this.anim) / (10 * MS), 0, 1);
    g.xf(188, 230, .86 + .14 * fe, () => {
      g.rect(58, 100, 260, 260, s.face);
      g.rect(58, 100, 8, 260, K.gold);
      g.rect(94, 124, 92, 92, s.bg);                         /* artwork well */
      g.icon(106, 136, 68, K.ink);
      g.text(cur.t, 94, 256, 'heading', K.bone, 'left', 210);
      g.rect(94, 272, 56, 2, s.hi);
      g.text(cur.d, 94, 300, 'body', K.bone, 'left', 210);
    });
    g.mono((this.sel + 1) + ' / ' + this.n, 596, 424, 'caption', K.muted, 'right');
    descStrip(g, null, '◄ ► scroll the strip   A enter   B back');
    if (this.view.geo) { safeBox(g);
      g.outline(58, 100, 260, 260, '#8fdef6');
      g.text('reading slot 58,100 260×260', 58, 94, 'caption', '#8fdef6');
      g.dash(372, 168, 602, 168, 'rgba(143,222,246,.7)');
      g.text('strip origin x=372 pitch 64, decay ×0.86', 372, 160, 'caption', '#8fdef6'); }
    if (this.view.fit) { safeBox(g);
      g.text('reading card + 3 strip cards inside 640 — but the strip is 1-D, so there is no hub',
             90, 364, 'caption', K.ok); }
    this.note = 'the strip never wraps — the ends are dead stops, which is the concept\'s whole weakness';
  },
};

/* ---- C · INDEX ----------------------------------------------------------------------------- */
C.c = {
  key:'c', name:'C · Index', n:6, sel:0, csel:0, child:0, parent:0, anim:0,
  view:{shear:1, geo:0, fit:0}, note:'',
  items(n) { return Array.from({length:n}, (_, i) => MAIN[i % MAIN.length]); },
  childRows() { return CHILD[this.parent % CHILD.length]; },
  parentTitle() { return this.items(this.n)[this.parent].t; },
  parentDesc() { return this.items(this.n)[this.parent].d; },
  move(d) { this.sel = (this.sel + d + this.n) % this.n; this.anim = performance.now(); },

  draw(g, t) {
    if (this.child) return childScreen(g, this, t);
    const items = this.items(this.n), cur = items[this.sel], s = SEC.data;
    const e = clamp((t - this.anim) / (6 * MS), 0, 1);           /* label TRA_X is 6f */
    /* the rule that actually holds: pitch shrinks to fit, but never below 30px,
       because a label role is 20px and anything tighter collides. */
    const TOP = 124, BOTTOM = 386, MINP = 30, MAXP = 44;
    const pitch = this.n > 1 ? Math.min(MAXP, (BOTTOM - TOP) / (this.n - 1)) : MAXP;
    const lastY = TOP + (this.n - 1) * pitch;
    bands(g, 'data');
    header(g, 'VERSUS', 'heading');
    g.text('02', 596, 76, 'display', s.hi, 'right');            /* the section numeral */
    g.rect(88, TOP - 24, 2, lastY - TOP + 30, s.hi);            /* the margin rule */
    for (let i = 0; i < this.n; i++) {
      const y = TOP + i * pitch, on = i === this.sel;
      g.rect(104, y, 436, 1, '#0d3b31');
      if (on) { g.rect(76, y + 8, 14, 14, K.gold); g.rect(104, y + pitch - 4, 436, 2, K.gold); }
      g.text(items[i].t, 104 + (on ? 10 * e : 0), y + 30, 'label', on ? K.gold : K.bone,
             'left', 300);
      g.mono(ROMAN[i], 540, y + 30, 'row', on ? K.goldDk : K.muted, 'right');
    }
    g.rect(90, 400, 4, 44, K.gold);
    g.text(cur.d, 106, 418, 'body', K.bone, 'left', 420);
    g.text('▲▼ move   A enter   B back', 106, 444, 'caption', K.muted);
    if (this.view.geo) { safeBox(g);
      g.text('margin rule x=88 · label x=104 · numeral x=540 · pitch ' + pitch.toFixed(0) + 'px',
             104, 372, 'caption', '#8fdef6'); }
    if (this.view.fit) { safeBox(g);
      const ok2 = pitch >= MINP;
      g.text(ok2 ? 'pitch ' + pitch.toFixed(0) + 'px at n=' + this.n +
                  ' — fits, last row ends y=' + lastY.toFixed(0)
                 : 'pitch would be ' + pitch.toFixed(0) + 'px, under the 30px floor — ' +
                   'this is the concept\'s real ceiling',
             104, 372, 'caption', ok2 ? K.ok : K.danger); }
    this.note = 'pitch ' + pitch.toFixed(0) + 'px at n=' + this.n +
      (pitch < 30 ? ' — UNDER the 30px floor, so this is where C breaks'
                  : ' · the 30px floor is the ceiling: C tops out at 9, same as the kit list');
  },
};

/* ---- D · DASHBOARD ------------------------------------------------------------------------- */
const ANCHORS = [
  {k:'A', x:436, y:126, r:22}, {k:'X', x:500, y:162, r:22},
  {k:'B', x:436, y:198, r:22}, {k:'Y', x:372, y:198, r:22},
  {k:'L', x:168, y:107, r:26}, {k:'R', x:324, y:107, r:26},
  {k:'U', x:214, y:118, r:22}, {k:'D', x:214, y:198, r:22},
  {k:'STICK', x:144, y:242, r:26}, {k:'HOME', x:344, y:233, r:20},
];
C.d = {
  key:'d', name:'D · Dashboard', n:6, sel:1, csel:0, child:0, parent:0, anim:0,
  view:{shear:1, geo:0, fit:0}, note:'',
  items(n) { return Array.from({length:Math.min(n, ANCHORS.length)}, (_, i) => MAIN[i % MAIN.length]); },
  childRows() { return CHILD[this.parent % CHILD.length]; },
  parentTitle() { return this.items(this.n)[this.parent].t; },
  parentDesc() { return this.items(this.n)[this.parent].d; },
  move(d) { this.sel = (this.sel + d + this.n) % this.n; this.anim = performance.now(); },
  pick(px, py) {
    let best = -1, bd = 1e9;
    for (let i = 0; i < Math.min(this.n, ANCHORS.length); i++) {
      const a = ANCHORS[i], d = Math.hypot(px - a.x, py - a.y);
      if (d < a.r + 6 && d < bd) { bd = d; best = i; }
    }
    return best;
  },
  draw(g, t) {
    if (this.child) return childScreen(g, this, t);
    const items = this.items(this.n), cur = items[this.sel];
    const e = clamp((t - this.anim) / (6 * MS), 0, 1);
    const sc = 1 + .15 * e;                                       /* 6f, about the centre */
    g.rect(32, 24, 212, 40, K.gold);
    g.text(cur.t, 50, 50, 'title', K.ink);
    g.text(cur.d.toUpperCase().slice(0, 34), 264, 50, 'caption', K.muted);
    /* the pad body: one I4 mask in the engine, flat rects here */
    g.rect(96, 104, 236, 150, '#39424f');
    g.rect(96, 104, 236, 14, '#4a5468');
    g.rect(150, 130, 128, 24, '#2a3140');
    g.rect(202, 78, 24, 128, '#2a3140');
    const au = ANCHORS[6];
    g.circle(au.x, au.y, 13 * (this.sel === 6 ? sc : 1),
             this.sel === 6 ? K.gold : '#2a3140');
    g.text('↑', au.x, au.y + 6, 'body', this.sel === 6 ? K.ink : '#5c6675', 'center');
    for (let i = 0; i < 4; i++) {
      const a = ANCHORS[i], on = i === this.sel;
      g.circle(a.x, a.y, a.r * (on ? sc : 1), on ? K.gold : '#4a5468');
      g.text(a.k, a.x, a.y + 6, 'body', on ? K.ink : K.bone, 'center');
    }
    for (const i of [4, 5, 7, 8, 9]) {
      if (i >= this.n) continue;
      const a = ANCHORS[i], on = i === this.sel;
      if (i === 8) g.circle(a.x, a.y, a.r * (on ? sc : 1), on ? K.gold : '#4a5468');
      else g.rect(a.x - a.r, a.y - 11, a.r * 2, 22, on ? K.gold : '#2a3140');
      g.text(a.k, a.x, a.y + (i === 8 ? 5 : 4), 'caption', on ? K.ink : K.dis, 'center');
    }
    g.rect(96, 296, 404, 1, SEC.options.hi);
    g.text('ROOMS OPEN', 96, 318, 'caption', K.muted);
    g.mono('003', 500, 318, 'row', K.bone, 'right');
    g.text('Press ' + ANCHORS[this.sel].k + ' to open ' + cur.t + '.', 96, 344, 'body', K.bone);
    descStrip(g, null, 'Click a button   A enter   B back');
    if (this.view.geo) { safeBox(g);
      for (let i = 0; i < Math.min(this.n, ANCHORS.length); i++) {
        const a = ANCHORS[i];
        g.ring(a.x, a.y, a.r, 'rgba(143,222,246,.75)');
        g.text(a.k + ' r' + a.r, a.x - 12, a.y - a.r - 3, 'caption', '#8fdef6');
      } }
    if (this.view.fit) { safeBox(g);
      g.text(this.n + ' anchors bound; a real pad offers 10, so this ceiling is the pad, not the screen',
             96, 372, 'caption', this.n <= 8 ? K.ok : K.danger); }
    this.note = 'the ceiling is the hardware — 10 anchors, and the pad has no room for 10 named modes';
  },
};

/* ---- E · DECK ------------------------------------------------------------------------------ */
C.e = {
  key:'e', name:'E · Deck', n:6, sel:0, csel:0, child:0, parent:0, anim:0,
  view:{shear:1, geo:0, fit:0}, note:'',
  items(n) { return Array.from({length:n}, (_, i) => MAIN[(i + 2) % MAIN.length]); },
  childRows() { return CHILD[(this.parent + 2) % CHILD.length]; },
  parentTitle() { return this.items(this.n)[this.parent].t; },
  parentDesc() { return this.items(this.n)[this.parent].d; },
  move(d) { this.sel = (this.sel + d + this.n) % this.n; this.anim = performance.now(); },

  draw(g, t) {
    if (this.child) return childScreen(g, this, t);
    const items = this.items(this.n), cur = items[this.sel];
    const e = clamp((t - this.anim) / (10 * MS), 0, 1);
    const pop = e < .4 ? (e / .4) * 1.30 : 1.30 - .30 * ((e - .4) / .6);
    bands(g, cur.sec);
    g.rect(84, 24, 150, 44, K.gold);
    g.text('MAIN', 104, 58, 'heading', K.ink);
    for (let k = 3; k >= 1; k--) {                       /* the fan, back to front */
      const x = 268 + (k - 1) * 52, y = 214 - (k - 1) * 8;
      g.rect(x, y, 96, 130, ['#4a2c05', '#543105', '#5e3705', '#683d04'][k - 1]);
    }
    const more = Math.max(0, this.n - 4);
    if (more) g.text(more + ' MORE', 524, 336, 'caption', K.muted, 'right');
    g.xf(161, 232, .88 + .12 * pop, () => {
      g.rect(92, 140, 150, 200, K.goldDk);
      g.rect(86, 132, 150, 200, K.gold);
      g.icon(131, 158, 60, K.ink);
      g.text(cur.t, 161, 258, 'title', K.ink, 'center', 130);
      g.text(CHILD[this.sel % CHILD.length].length + ' MODES', 161, 288, 'caption', '#6b4a12',
             'center');
    });
    g.rect(268, 96, 320, 1, SEC.solo.hi);
    g.text(cur.t, 268, 130, 'heading', SEC.solo.hi);
    g.text(cur.d, 268, 160, 'body', K.bone, 'left', 300);
    descStrip(g, cur.d, '◄ ► through the fan   A enter   B back');
    if (this.view.geo) { safeBox(g);
      g.outline(86, 132, 150, 200, '#8fdef6');
      g.text('selected 86,132 150×200', 86, 126, 'caption', '#8fdef6');
      g.outline(268, 214, 96, 130, 'rgba(143,222,246,.6)');
      g.text('fan origin 268,214 pitch −52,−8', 268, 206, 'caption', '#8fdef6'); }
    if (this.view.fit) { safeBox(g);
      const ok2 = 214 + 130 <= 396;
      g.text(ok2 ? 'fan and selected card both clear of the pull-quote'
                 : 'the fan runs into the description strip', 268, 372, 'caption',
             ok2 ? K.ok : K.danger); }
    this.note = 'four cards fit in the fan; the rest collapse to an "n MORE" counter — occlusion by design';
  },
};

/* ---- wiring --------------------------------------------------------------------------------- */
const KEYS = ['a', 'b', 'c', 'd', 'e'];
const cv = {}, G2 = {}, HUD = {}, FIND = {}, CTX = {};
let active = 'a';

for (const k of KEYS) {
  cv[k] = document.getElementById('cv-' + k);
  CTX[k] = cv[k].getContext('2d');
  G2[k] = G(CTX[k]);
  HUD[k] = document.getElementById('hud-' + k);
  FIND[k] = document.getElementById(k + '-find');
  cv[k].tabIndex = 0;
  const K2 = C[k];
  const nEl = document.getElementById('n-' + k), nv = document.getElementById('nv-' + k);
  nEl.addEventListener('input', () => {
    K2.n = +nEl.value; nv.textContent = nEl.value;
    K2.sel = clamp(K2.sel, 0, K2.n - 1);
    K2.anim = performance.now();
  });
  for (const id of ['shear', 'geo', 'fit']) {
    const b = document.getElementById(k + '-' + id);
    b.addEventListener('click', () => {
      K2.view[id] = K2.view[id] ? 0 : 1;
      b.setAttribute('aria-pressed', String(!!K2.view[id]));
    });
  }
  const toStage = ev => {
    const r = cv[k].getBoundingClientRect();
    let x = (ev.clientX - r.left) / (r.width / 640);
    let y = (ev.clientY - r.top) / (r.height / 480);
    if (K2.view.shear) x -= (240 - y) * 0.25;          /* invert the shear */
    return [x, y];
  };
  cv[k].addEventListener('click', ev => {
    active = k; const [x, y] = toStage(ev);
    if (K2.child) { K2.csel = clamp(Math.floor((y - 84) / 34) + K2.csel - 4, 0,
                                     K2.childRows().length - 1); return; }
    if (k === 'd') { const i = C.d.pick(x, y); if (i >= 0) { C.d.sel = i; C.d.anim = performance.now(); } return; }
    const i = hit(k, x, y);
    if (i >= 0) { K2.sel = i; K2.anim = performance.now(); }
  });
  cv[k].addEventListener('focus', () => { active = k; });
  cv[k].addEventListener('mousedown', () => { active = k; });
}

function hit(k, x, y) {
  const K2 = C[k];
  if (k === 'a') {
    for (const c of K2.layout(K2.sel, K2.n))
      if (x >= c.x && x <= c.x + c.w && y >= c.y && y <= c.y + c.h)
        return (K2.sel + c.d) % K2.n;
  }
  if (k === 'b') { if (x >= 58 && x <= 318 && y >= 100 && y <= 360) return K2.sel; }
  if (k === 'c') { const p = Math.min(44, 262 / Math.max(1, K2.n - 1));
    for (let i = 0; i < K2.n; i++) if (y >= 124 + i * p && y < 124 + (i + 1) * p) return i; }
  if (k === 'e') { if (x >= 86 && x <= 236 && y >= 132 && y <= 332) return K2.sel; }
  return -1;
}

function step(k, d) {
  const K2 = C[k];
  if (K2.child) {
    K2.csel = (K2.csel + d + K2.childRows().length) % K2.childRows().length;
    return;
  }
  K2.move(d);
}

function enter(k) {
  const K2 = C[k];
  if (K2.child) return;
  K2.parent = K2.sel; K2.csel = 0; K2.child = 1;
}
function back(k) {
  const K2 = C[k];
  if (!K2.child) return;
  K2.child = 0; K2.sel = K2.parent;
}

addEventListener('keydown', ev => {
  const k = active, kk = ev.key;
  if (kk === 'ArrowLeft')  { step(k, -1); ev.preventDefault(); }
  if (kk === 'ArrowRight') { step(k,  1); ev.preventDefault(); }
  if (kk === 'ArrowUp')    { step(k, active === 'c' || active === 'd' ? -1 : -1); ev.preventDefault(); }
  if (kk === 'ArrowDown')  { step(k,  1); ev.preventDefault(); }
  if (kk === 'a' || kk === 'A' || kk === 'Enter') { enter(k); ev.preventDefault(); }
  if (kk === 'b' || kk === 'B' || kk === 'Escape') { back(k); ev.preventDefault(); }
});

function drawOne(k) {
  const c = CTX[k], g = G2[k], K2 = C[k];
  c.clearRect(0, 0, 960, 720);
  c.save();
  c.scale(1.5, 1.5);
  g.shear(K2.view.shear);
  K2.draw(g, performance.now());
  c.restore();
  const it = K2.items(K2.n)[K2.sel];
  HUD[k].innerHTML = K2.name + ' · tiles <b>' + K2.n + '</b> · sel <b>' + (it ? it.t : '—') +
    '</b> · screen <b>' + (K2.child ? 'CHILD (list_layout)' : 'concept') + '</b>';
  FIND[k].textContent = K2.note;
}
function frame() { for (const k of KEYS) drawOne(k); requestAnimationFrame(frame); }
requestAnimationFrame(frame);