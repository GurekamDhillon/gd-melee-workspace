#!/usr/bin/env python3
"""Skin Fitter: a desktop front-end over skin.py (the CLI stays the source of truth; this window only drives it).

    python ui.py                       open the window
    python ui.py --demo DIR            open on the synthetic test model built by test_synthetic.py into DIR
    python ui.py --demo DIR --shots OUT   render each step of the flow to OUT/*.png (grabs this window only) and exit

Flow: 1 Source  2 Bone map  3 Preview  4 Checks  5 Build. Keyboard: Ctrl+1..5 or Alt+Left/Right switch steps,
Ctrl+O opens a source, Ctrl+S saves the map. Drop a folder or .pac/.json anywhere to load it as the source.
"""
import html, json, math, os, subprocess, sys
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import skin

# ---- tokens: a drafting-table look (blueprint slate, chalk lines, one ochre for "selected") ------------------------
C = {"bg": "#1d2831", "panel": "#243340", "line": "#3a4d5c", "chalk": "#dde6ec", "dim": "#8fa3b1",
     "sel": "#e3b23c", "hi": "#3fb5a3", "mid": "#e3b23c", "lo": "#e0645a"}
HEAD = "Bahnschrift"; BODY = "Segoe UI"
QSS = f"""
* {{ color: {C['chalk']}; font-family: '{BODY}'; font-size: 10.5pt; }}
QMainWindow, #page {{ background: {C['bg']}; }}
#rail {{ background: {C['panel']}; border-right: 1px solid {C['line']}; }}
#rail QPushButton {{ text-align: left; padding: 12px 18px; border: none; border-left: 3px solid transparent; color: {C['dim']}; font-family: '{HEAD}'; font-size: 12pt; }}
#rail QPushButton:checked {{ color: {C['chalk']}; border-left: 3px solid {C['sel']}; background: {C['bg']}; }}
#rail QPushButton:focus {{ outline: none; border-left: 3px solid {C['hi']}; }}
QLabel#h1 {{ font-family: '{HEAD}'; font-size: 20pt; }}
QLabel#lede {{ color: {C['dim']}; }}
QLineEdit, QComboBox, QPlainTextEdit, QTreeWidget, QListWidget {{ background: {C['panel']}; border: 1px solid {C['line']}; border-radius: 3px; padding: 4px; selection-background-color: {C['sel']}; selection-color: {C['bg']}; }}
QLineEdit:focus, QComboBox:focus, QTreeWidget:focus {{ border: 1px solid {C['sel']}; }}
QPushButton {{ background: {C['panel']}; border: 1px solid {C['line']}; border-radius: 3px; padding: 6px 14px; }}
QPushButton:hover {{ border-color: {C['dim']}; }} QPushButton:focus {{ border-color: {C['sel']}; }}
QPushButton#go {{ background: {C['sel']}; color: {C['bg']}; border: none; font-family: '{HEAD}'; font-size: 12pt; padding: 9px 22px; }}
QHeaderView::section {{ background: {C['panel']}; color: {C['dim']}; border: none; padding: 4px; }}
"""



def fighters():
    sys.path.insert(0, os.path.join(skin.ROOT, "ports", "ir", "tools"))
    import build_melee_fighter as B
    return sorted(k for k in B.FIGHTERS if k != "captain")


def conf_color(c):
    return QtGui.QColor(C["hi"] if c >= 0.8 else C["mid"] if c >= 0.5 else C["lo"])


class State(QtCore.QObject):
    changed = QtCore.Signal()

    def __init__(self):
        super().__init__(); self.source = None; self.src = None; self.retail = None; self.tgt = None; self.plco = None
        self.fighter = "luigi"; self.slot = "Nr"; self.mp = None; self.groups = None; self.sk = None; self.checks = None
        self.mods = os.path.join(skin.ROOT, "_build", "mods-local"); self.out = None; self.names_override = None


# ---- step 1: source -----------------------------------------------------------------------------------------------
class SourcePage(QtWidgets.QWidget):
    def __init__(self, st, win):
        super().__init__(); self.st, self.win = st, win
        L = QtWidgets.QVBoxLayout(self); L.setContentsMargins(40, 32, 40, 32); L.setSpacing(14)
        h = QtWidgets.QLabel("Pick what to fit, and onto whom"); h.setObjectName("h1"); L.addWidget(h)
        p = QtWidgets.QLabel("Drop a source fighter folder, a .pac or an exported .json anywhere in this window. "
                             "The target is a retail costume file; its skeleton is kept exactly."); p.setObjectName("lede"); p.setWordWrap(True); L.addWidget(p)
        f = QtWidgets.QFormLayout(); f.setSpacing(10)
        self.src = QtWidgets.QLineEdit(); self.src.setPlaceholderText("Source folder, .pac or .json")
        b1 = QtWidgets.QPushButton("Browse"); b1.clicked.connect(self.pick_src)
        r1 = QtWidgets.QHBoxLayout(); r1.addWidget(self.src); r1.addWidget(b1); f.addRow("Source", r1)
        self.fig = QtWidgets.QComboBox(); self.fig.addItems(fighters()); self.fig.setCurrentText(st.fighter); f.addRow("Target fighter", self.fig)
        self.slot = QtWidgets.QComboBox(); self.slot.addItems(["Nr", "Re", "Bu", "Gr", "Wh", "Ye", "Bk", "Pi", "Or", "La", "Aq", "new m-ex costume"]); f.addRow("Costume slot", self.slot)
        self.ret = QtWidgets.QLineEdit(); self.ret.setPlaceholderText("Retail costume .dat (Pl<code>Nr.dat)")
        b2 = QtWidgets.QPushButton("Browse"); b2.clicked.connect(lambda: self._file(self.ret, "Costume (*.dat)"))
        r2 = QtWidgets.QHBoxLayout(); r2.addWidget(self.ret); r2.addWidget(b2); f.addRow("Retail costume", r2)
        self.plco = QtWidgets.QLineEdit(); self.plco.setPlaceholderText("PlCo.dat, for joint names (optional)")
        b3 = QtWidgets.QPushButton("Browse"); b3.clicked.connect(lambda: self._file(self.plco, "PlCo (*.dat)"))
        r3 = QtWidgets.QHBoxLayout(); r3.addWidget(self.plco); r3.addWidget(b3); f.addRow("Fighter names", r3)
        self.grp = QtWidgets.QLineEdit(); self.grp.setPlaceholderText("Object slot config (groups.json)")
        b4 = QtWidgets.QPushButton("Browse"); b4.clicked.connect(lambda: self._file(self.grp, "JSON (*.json)"))
        r4 = QtWidgets.QHBoxLayout(); r4.addWidget(self.grp); r4.addWidget(b4); f.addRow("Object slots", r4)
        L.addLayout(f)
        self.msg = QtWidgets.QLabel(""); self.msg.setObjectName("lede"); L.addWidget(self.msg)
        go = QtWidgets.QPushButton("Load and auto-map"); go.setObjectName("go"); go.clicked.connect(self.load)
        L.addWidget(go, 0, Qt.AlignLeft); L.addStretch(1)

    def _file(self, edit, filt):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose", "", filt)
        if p: edit.setText(p)

    def pick_src(self):
        p = QtWidgets.QFileDialog.getExistingDirectory(self, "Source fighter folder")
        if p: self.src.setText(p)

    def load(self):
        st = self.st
        try:
            sp = self.src.text().strip()
            if sp.endswith(".pac") or os.path.isdir(sp):
                work = os.path.join(skin.ROOT, "_build", "tmp", "skin-ui"); os.makedirs(work, exist_ok=True)
                if os.path.isdir(sp):
                    pac = sorted(f for f in os.listdir(sp) if f.endswith("00.pac"))[0]; sp = os.path.join(sp, pac)
                js = os.path.join(work, "source.json"); subprocess.run([skin.MODEL_EXPORT, sp, js], check=True, capture_output=True); sp = js
            st.source = sp; st.src = skin.load_source(sp)
            st.retail = self.ret.text().strip(); st.fighter = self.fig.currentText(); st.slot = self.slot.currentText()
            st.plco = self.plco.text().strip() or None
            st.tgt = skin.read_target(st.retail, st.fighter if st.plco else None, st.plco)
            if st.names_override: [j.__setitem__("name", n) for j, n in zip(st.tgt["joints"], st.names_override)]
            start = None; tm = os.path.join(HERE, "maps", st.fighter + ".bones.json")
            if os.path.exists(tm) and st.plco: start = json.load(open(tm))["source_to_target"]
            st.mp = skin.automap(st.src, st.tgt, start)
            st.groups = json.load(open(self.grp.text().strip())) if self.grp.text().strip() else {"dobjs": {}}
            st.sk = skin.retarget(st.src, st.tgt, st.mp, st.groups) if st.groups["dobjs"] else None
            low = sum(1 for v in st.mp["source_to_target"].values() if v["confidence"] < 0.5)
            self.msg.setText("Loaded %d source bones onto %d target joints. %d mappings need a look." % (len(st.src["bones"]), len(st.tgt["joints"]), low))
            st.changed.emit(); self.win.go(1)
        except Exception as e:
            self.msg.setText("Could not load: %s" % e)


# ---- step 2: bone map (two trees, links drawn between) ------------------------------------------------------------
class MapPage(QtWidgets.QWidget):
    def __init__(self, st, win):
        super().__init__(); self.st, self.win = st, win; self.sel = None
        L = QtWidgets.QVBoxLayout(self); L.setContentsMargins(40, 32, 40, 24)
        h = QtWidgets.QLabel("Bone map"); h.setObjectName("h1"); L.addWidget(h)
        p = QtWidgets.QLabel("Every source bone lands on one target joint. Teal is certain, ochre is a guess by name, "
                             "coral is a guess by position. Click a source bone, then a target joint, to remap it."); p.setObjectName("lede"); p.setWordWrap(True); L.addWidget(p)
        row = QtWidgets.QHBoxLayout(); L.addLayout(row, 1)
        self.a = QtWidgets.QTreeWidget(); self.a.setHeaderLabels(["Source bone", "conf."]); self.b = QtWidgets.QTreeWidget(); self.b.setHeaderLabels(["Target joint", "#"])
        self.links = Links(self); row.addWidget(self.a, 5); row.addWidget(self.links, 2); row.addWidget(self.b, 5)
        for t in (self.a, self.b):
            t.setColumnWidth(0, 230); t.itemExpanded.connect(self.links.update); t.itemCollapsed.connect(self.links.update)
            t.verticalScrollBar().valueChanged.connect(self.links.update)
        self.a.itemClicked.connect(self.pick_a); self.b.itemClicked.connect(self.pick_b)
        bar = QtWidgets.QHBoxLayout(); L.addLayout(bar)
        for txt, fn in (("Load map", self.load_map), ("Save map", self.save_map)):
            b = QtWidgets.QPushButton(txt); b.clicked.connect(fn); bar.addWidget(b)
        bar.addStretch(1); self.info = QtWidgets.QLabel(""); self.info.setObjectName("lede"); bar.addWidget(self.info)
        st.changed.connect(self.fill)

    def fill(self):
        st = self.st
        if not st.mp: return
        self.a.clear(); self.b.clear(); self.ia, self.ib = {}, {}
        for bn in st.src["bones"]:
            m = st.mp["source_to_target"][bn["name"]]
            it = QtWidgets.QTreeWidgetItem([bn["name"], "%.2f" % m["confidence"]]); it.setForeground(1, conf_color(m["confidence"]))
            it.setToolTip(0, "%s -> %s (%s)" % (bn["name"], m["target"], m["rule"]))
            (self.ia[bn["parent"]].addChild(it) if bn["parent"] in self.ia else self.a.addTopLevelItem(it)); self.ia[bn["name"]] = it
        for j in st.tgt["joints"]:
            it = QtWidgets.QTreeWidgetItem([j["name"], str(j["index"])])
            par = st.tgt["joints"][j["parent"]]["name"] if j["parent"] is not None else None
            (self.ib[par].addChild(it) if par in self.ib else self.b.addTopLevelItem(it)); self.ib[j["name"]] = it
        self.a.expandAll(); self.b.expandAll()
        n = len(st.mp["source_to_target"]); hi = sum(1 for v in st.mp["source_to_target"].values() if v["confidence"] >= 0.8)
        self.info.setText("%d of %d bones mapped with high confidence" % (hi, n)); self.links.update()

    def pick_a(self, it, _):
        self.sel = it.text(0); self.links.update()
        self.b.setCurrentItem(self.ib.get(self.st.mp["source_to_target"][self.sel]["target"]))

    def pick_b(self, it, _):
        if self.sel:
            self.st.mp["source_to_target"][self.sel] = {"target": it.text(0), "confidence": 1.0, "rule": "picked by hand"}
            self.ia[self.sel].setText(1, "1.00"); self.ia[self.sel].setForeground(1, conf_color(1.0))
            if self.st.groups and self.st.groups["dobjs"]: self.st.sk = skin.retarget(self.st.src, self.st.tgt, self.st.mp, self.st.groups)
            self.links.update(); self.win.pages[2].view.update()

    def save_map(self):
        p, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save map", "", "JSON (*.json)")
        if p: json.dump({"source_to_target": {k: v["target"] for k, v in self.st.mp["source_to_target"].items()}}, open(p, "w"), indent=1)

    def load_map(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load map", "", "JSON (*.json)")
        if p:
            m = json.load(open(p))["source_to_target"]; self.st.mp = skin.automap(self.st.src, self.st.tgt, m); self.fill()


class Links(QtWidgets.QWidget):
    def __init__(self, page): super().__init__(); self.p = page; self.setMinimumWidth(80)

    def paintEvent(self, e):
        p = self.p; st = p.st
        if not st.mp or not hasattr(p, "ia"): return
        g = QtGui.QPainter(self); g.setRenderHint(QtGui.QPainter.Antialiasing)
        off = self.mapFromGlobal(QtCore.QPoint(0, 0))
        for name, m in st.mp["source_to_target"].items():
            ia, ib = p.ia.get(name), p.ib.get(m["target"])
            if ia is None or ib is None: continue
            ra, rb = p.a.visualItemRect(ia), p.b.visualItemRect(ib)
            if ra.height() == 0 or rb.height() == 0: continue
            ya = p.a.viewport().mapToGlobal(ra.center()).y() + off.y(); yb = p.b.viewport().mapToGlobal(rb.center()).y() + off.y()
            col = QtGui.QColor(C["sel"]) if name == p.sel else conf_color(m["confidence"])
            col.setAlpha(255 if name == p.sel else 120)
            g.setPen(QtGui.QPen(col, 2.4 if name == p.sel else 1.2))
            path = QtGui.QPainterPath(QtCore.QPointF(0, ya)); w = self.width()
            path.cubicTo(w * 0.5, ya, w * 0.5, yb, w, yb); g.drawPath(path)


# ---- step 3: preview (software renderer: flat-shaded triangles, painter's order) ---------------------------------
POSES = {"Bind pose": {}, "Arms raised": {"LShoulderJ": (0, 0, 1.2), "RShoulderJ": (0, 0, -1.2), "LArmJ": (0, 0, 0.9), "RArmJ": (0, 0, -0.9)},
         "Crouch": {"LLegJ": (0, 0, -1.1), "RLegJ": (0, 0, -1.1), "LKneeJ": (0, 0, 1.6), "RKneeJ": (0, 0, 1.6), "BustN": (0, 0, 0.35)},
         "Run frame": {"LLegJ": (0, 0, -0.8), "RLegJ": (0, 0, 0.6), "LKneeJ": (0, 0, 0.9), "LShoulderJ": (0, 0, 0.7), "RShoulderJ": (0, 0, -0.5), "BustN": (0, 0, 0.2)}}


class View(QtWidgets.QWidget):
    def __init__(self, st):
        super().__init__(); self.st = st; self.yaw = 0.6; self.pitch = 0.15; self.pose = "Bind pose"; self.paint_bone = None
        self.setMinimumSize(420, 420); self.setFocusPolicy(Qt.StrongFocus); self.last = None; self.anim = 0.0

    def mousePressEvent(self, e): self.last = e.position()

    def mouseMoveEvent(self, e):
        if self.last is not None:
            d = e.position() - self.last; self.yaw += d.x() * 0.01; self.pitch = max(-1.2, min(1.2, self.pitch + d.y() * 0.01)); self.last = e.position(); self.update()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Left: self.yaw -= 0.15
        elif e.key() == Qt.Key_Right: self.yaw += 0.15
        else: return super().keyPressEvent(e)
        self.update()

    def posed(self):
        """Target joint matrices for the pose (bind * delta) and the skinning matrices (posed * inverse bind)."""
        T = self.st.tgt["joints"]; names = {j["name"]: j["index"] for j in T}
        delta = POSES[self.pose]; t = self.anim
        P = []
        for j in T:
            L = np.eye(4); L[:3, :3] = skin.euler_mat(j["rot"]) @ np.diag(j["scale"]); L[:3, 3] = j["trans"]
            if j["name"] in delta: L[:3, :3] = L[:3, :3] @ skin.euler_mat([a * t for a in delta[j["name"]]])
            P.append(L if j["parent"] is None else P[j["parent"]] @ L)
        B = [np.array(j["world"]) for j in T]
        return P, B

    def paintEvent(self, e):
        g = QtGui.QPainter(self); g.setRenderHint(QtGui.QPainter.Antialiasing); g.fillRect(self.rect(), QtGui.QColor(C["bg"]))
        st = self.st
        # floor grid: drafting paper
        g.setPen(QtGui.QPen(QtGui.QColor(C["line"]), 1))
        for i in range(0, self.width(), 24): g.drawLine(i, 0, i, self.height())
        for i in range(0, self.height(), 24): g.drawLine(0, i, self.width(), i)
        if not st.tgt: g.setPen(QtGui.QColor(C["dim"])); g.drawText(self.rect(), Qt.AlignCenter, "Load a source to see it fitted"); return
        P, B = self.posed()
        S = [p @ np.linalg.inv(b) for p, b in zip(P, B)]
        cy, sy, cp, sp = math.cos(self.yaw), math.sin(self.yaw), math.cos(self.pitch), math.sin(self.pitch)
        R = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]); R = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]]) @ R
        pts = np.array([b[:3, 3] for b in B]); ctr = pts.mean(0); ext = max(1e-3, np.ptp(pts[:, 1]) * 0.75)
        sc = min(self.width(), self.height()) / (2.4 * ext)
        def proj(v): q = R @ (v - ctr); return QtCore.QPointF(self.width() / 2 + q[0] * sc, self.height() / 2 - q[1] * sc), q[2]
        tris = []
        if st.sk:
            light = np.array([0.3, 0.6, 0.75]); light /= np.linalg.norm(light)
            sel = {j["name"]: j["index"] for j in st.tgt["joints"]}.get(self.paint_bone)
            for d in st.sk["dobjs"]:
                for t in d.get("tris", []):
                    vs, wsel = [], 0
                    for v in t:
                        p = np.array(v["p"] + [1.0])
                        if len(v["w"]) == 1 and st.tgt["joints"][v["w"][0][0]]["ibm"]: p = B[v["w"][0][0]] @ p     # joint-local -> bind world
                        w = sum(wt * (S[j] @ p) for j, wt in v["w"])[:3]; vs.append(w)
                        if sel is not None: wsel += sum(wt for j, wt in v["w"] if j == sel) / 3
                    n = np.cross(vs[1] - vs[0], vs[2] - vs[0]); nn = np.linalg.norm(n)
                    shade = abs(np.dot(R @ (n / nn), light)) if nn > 0 else 0.5
                    pp = [proj(v) for v in vs]
                    tris.append((sum(z for _, z in pp) / 3, [q for q, _ in pp], shade, wsel if sel is not None else None))
        tris.sort(key=lambda x: x[0])
        base = QtGui.QColor(C["chalk"]); g.setPen(Qt.NoPen)
        for _, poly, sh, ws in tris:
            if ws is None: col = QtGui.QColor.fromRgbF(base.redF() * (0.35 + 0.65 * sh), base.greenF() * (0.35 + 0.65 * sh), base.blueF() * (0.35 + 0.65 * sh))
            else: a = min(1, ws); col = QtGui.QColor.fromRgbF(0.15 + 0.75 * a, 0.25 + 0.45 * a * (1 - a) * 4 * 0.5, 0.45 * (1 - a))
            g.setBrush(col); g.drawPolygon(QtGui.QPolygonF(poly))
        # skeleton on top
        g.setPen(QtGui.QPen(QtGui.QColor(C["sel"]), 2))
        for j in st.tgt["joints"]:
            if j["parent"] is not None:
                a, _ = proj(P[j["parent"]][:3, 3]); b, _ = proj(P[j["index"]][:3, 3]); g.drawLine(a, b)
        g.setBrush(QtGui.QColor(C["bg"]))
        for j in st.tgt["joints"]:
            a, _ = proj(P[j["index"]][:3, 3]); g.drawEllipse(a, 3.5, 3.5)


class PreviewPage(QtWidgets.QWidget):
    def __init__(self, st, win):
        super().__init__(); self.st = st
        L = QtWidgets.QVBoxLayout(self); L.setContentsMargins(40, 32, 40, 24)
        h = QtWidgets.QLabel("Preview on the target skeleton"); h.setObjectName("h1"); L.addWidget(h)
        p = QtWidgets.QLabel("Drag or use the arrow keys to turn it. Test poses show stretching at shoulders, hips and hands before you install."); p.setObjectName("lede"); p.setWordWrap(True); L.addWidget(p)
        row = QtWidgets.QHBoxLayout(); L.addLayout(row, 1)
        self.view = View(st); row.addWidget(self.view, 1)
        side = QtWidgets.QVBoxLayout(); row.addLayout(side)
        self.poses = QtWidgets.QButtonGroup(self)
        for i, n in enumerate(POSES):
            b = QtWidgets.QPushButton(n); b.setCheckable(True); b.setChecked(i == 0); self.poses.addButton(b); side.addWidget(b)
            b.clicked.connect(lambda _=False, n=n: self.set_pose(n))
        side.addSpacing(16); side.addWidget(QtWidgets.QLabel("Weight paint"))
        self.bones = QtWidgets.QListWidget(); self.bones.setMaximumWidth(200); side.addWidget(self.bones, 1)
        self.bones.currentTextChanged.connect(self.paint)
        st.changed.connect(self.fill)
        self.tl = QtCore.QVariantAnimation(self); self.tl.setDuration(420); self.tl.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.tl.valueChanged.connect(lambda v: (setattr(self.view, "anim", float(v)), self.view.update()))

    def fill(self):
        self.bones.clear(); self.bones.addItem("(none)")
        if self.st.tgt: self.bones.addItems([j["name"] for j in self.st.tgt["joints"]])

    def paint(self, n): self.view.paint_bone = None if n in ("", "(none)") else n; self.view.update()

    def set_pose(self, n, animate=True):
        self.view.pose = n
        if animate: self.tl.stop(); self.tl.setStartValue(0.0); self.tl.setEndValue(1.0); self.tl.start()
        else: self.view.anim = 1.0; self.view.update()


# ---- step 4: checks ----------------------------------------------------------------------------------------------
class ChecksPage(QtWidgets.QWidget):
    def __init__(self, st, win):
        super().__init__(); self.st, self.win = st, win
        L = QtWidgets.QVBoxLayout(self); L.setContentsMargins(40, 32, 40, 24); L.setSpacing(10)
        h = QtWidgets.QLabel("Checks"); h.setObjectName("h1"); L.addWidget(h)
        self.verdict = QtWidgets.QLabel(""); self.verdict.setMinimumHeight(64); L.addWidget(self.verdict)
        self.list = QtWidgets.QVBoxLayout(); L.addLayout(self.list); L.addStretch(1)
        b = QtWidgets.QPushButton("Run checks"); b.clicked.connect(self.run); L.addWidget(b, 0, Qt.AlignLeft)

    def run(self):
        st = self.st
        if not st.sk: return
        work = os.path.join(skin.ROOT, "_build", "tmp", "skin-ui"); os.makedirs(work, exist_ok=True)
        sj = os.path.join(work, "skin.json"); json.dump(st.sk, open(sj, "w")); out = os.path.join(work, "preview.dat")
        r = [subprocess.run([skin.CB, "build", st.retail, sj, out, os.path.join(work, "rep.json")], capture_output=True, text=True)]
        for f, o in ((st.retail, "ir.json"), (out, "io.json")): subprocess.run([skin.CB, "inspect", f, os.path.join(work, o)], capture_output=True)
        d = subprocess.run([sys.executable, os.path.join(HERE, "jointdiff.py"), st.retail, out], capture_output=True, text=True)
        st.checks = skin.checks(json.load(open(os.path.join(work, "rep.json"))), json.load(open(os.path.join(work, "ir.json"))),
                                json.load(open(os.path.join(work, "io.json"))), d.returncode, st.sk["stats"])
        st.checks["diff"] = d.stdout.strip(); st.out = out; self.show_checks()

    def show_checks(self):
        while self.list.count(): w = self.list.takeAt(0).widget(); w and w.deleteLater()
        ck = self.st.checks
        for x in ck["checks"]:
            row = QtWidgets.QLabel("<span style='background:%s;color:%s;padding:2px 8px;border-radius:3px;font-family:%s'>&nbsp;%s&nbsp;</span>"
                                   "&nbsp;&nbsp;<b>%s</b><br><span style='color:%s'>%s</span>" % (C["hi"] if x["pass"] else C["lo"], C["bg"], HEAD,
                                   "Pass" if x["pass"] else "Fail", html.escape(x["check"][0].upper() + x["check"][1:]), C["dim"], html.escape(x["detail"])))
            row.setTextFormat(Qt.RichText); self.list.addWidget(row)
        ok = ck["netplay_safe"]
        self.verdict.setText("<span style='font-family:%s;font-size:17pt;color:%s'>%s</span><br><span style='color:%s'>%s</span>" % (
            HEAD, C["hi"] if ok else C["lo"], "Netplay-safe" if ok else "Not netplay-safe", C["dim"],
            "The skeleton and object slots match the retail costume field for field." if ok else "The skeleton or object slots differ from retail. Players with and without this skin would desync."))


# ---- step 5: build & install ----------------------------------------------------------------------------------------
class BuildPage(QtWidgets.QWidget):
    def __init__(self, st, win):
        super().__init__(); self.st = st
        L = QtWidgets.QVBoxLayout(self); L.setContentsMargins(40, 32, 40, 24); L.setSpacing(10)
        h = QtWidgets.QLabel("Build and install"); h.setObjectName("h1"); L.addWidget(h)
        p = QtWidgets.QLabel("Writes the costume and copies it into a local mods folder with a mod.json. Nothing is uploaded."); p.setObjectName("lede"); L.addWidget(p)
        f = QtWidgets.QFormLayout(); self.name = QtWidgets.QLineEdit("My skin"); f.addRow("Name", self.name)
        self.mods = QtWidgets.QLineEdit(st.mods); f.addRow("Mods folder", self.mods); L.addLayout(f)
        b = QtWidgets.QPushButton("Build and install"); b.setObjectName("go"); b.clicked.connect(self.go); L.addWidget(b, 0, Qt.AlignLeft)
        q = QtWidgets.QHBoxLayout(); L.addLayout(q)
        self.queue = QtWidgets.QListWidget(); self.queue.setMaximumHeight(110); q.addWidget(self.queue, 1)
        qb = QtWidgets.QVBoxLayout(); q.addLayout(qb)
        b2 = QtWidgets.QPushButton("Queue a folder of skins"); b2.clicked.connect(self.add_folder); qb.addWidget(b2)
        b3 = QtWidgets.QPushButton("Run the queue"); b3.clicked.connect(self.run_queue); qb.addWidget(b3); qb.addStretch(1)
        self.log = QtWidgets.QPlainTextEdit(); self.log.setReadOnly(True); L.addWidget(self.log, 1)
        self.proc = QtCore.QProcess(self); self.proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.proc.readyRead.connect(lambda: self.log.appendPlainText(bytes(self.proc.readAll()).decode(errors="replace").rstrip()))
        self.proc.finished.connect(lambda c, _: self.log.appendPlainText("Finished (exit %d)." % c))

    def add_folder(self, d=None):
        d = d or QtWidgets.QFileDialog.getExistingDirectory(self, "Folder of skins (.pac / .pcs)")
        if d:
            for f in sorted(os.listdir(d)):
                if f.lower().endswith((".pac", ".pcs", ".json")): self.queue.addItem(os.path.join(d, f))

    def run_queue(self):
        st = self.st
        if not self.queue.count() or not st.retail: self.log.appendPlainText("Queue skins and load a target first."); return
        d = os.path.join(skin.ROOT, "_build", "tmp", "skin-ui", "queue"); os.makedirs(d, exist_ok=True)
        for i in range(self.queue.count()):
            f = self.queue.item(i).text(); dst = os.path.join(d, os.path.basename(f))
            if os.path.abspath(f) != os.path.abspath(dst): open(dst, "wb").write(open(f, "rb").read())
        gp = os.path.join(skin.ROOT, "_build", "tmp", "skin-ui", "groups.json"); json.dump(st.groups, open(gp, "w"))
        args = [os.path.join(HERE, "skin.py"), "batch", "--in-dir", d, "--out-dir", os.path.join(skin.ROOT, "_build", "tmp", "skin-ui", "costumes"),
                "--fighter", st.fighter, "--retail", st.retail, "--groups", gp, "--install", self.mods.text()]
        if st.plco: args += ["--plco", st.plco]
        self.log.appendPlainText("> skin.py batch: %d skins" % self.queue.count()); self.proc.start(sys.executable, args)

    def go(self):
        st = self.st
        if not st.source: self.log.appendPlainText("Load a source first (step 1)."); return
        gp = os.path.join(skin.ROOT, "_build", "tmp", "skin-ui", "groups.json"); json.dump(st.groups, open(gp, "w"))
        mp = os.path.join(skin.ROOT, "_build", "tmp", "skin-ui", "map.json"); json.dump(st.mp, open(mp, "w"))
        out = os.path.join(skin.ROOT, "_build", "tmp", "skin-ui", "skin_out.dat")
        args = [os.path.join(HERE, "skin.py"), "build", "--source", st.source, "--fighter", st.fighter, "--retail", st.retail,
                "--groups", gp, "--map", mp, "--out", out, "--install", self.mods.text(), "--name", self.name.text()]
        if st.plco: args += ["--plco", st.plco]
        if st.slot and st.slot != "new m-ex costume": args += ["--slot", st.slot]
        self.log.appendPlainText("> skin.py " + " ".join(os.path.basename(a) if os.sep in a or "/" in a else a for a in args[1:]))
        self.proc.start(sys.executable, args)


class Win(QtWidgets.QMainWindow):
    def __init__(self, st):
        super().__init__(); self.st = st; self.setWindowTitle("Skin Fitter"); self.resize(1180, 760); self.setAcceptDrops(True)
        cw = QtWidgets.QWidget(); cw.setObjectName("page"); self.setCentralWidget(cw)
        H = QtWidgets.QHBoxLayout(cw); H.setContentsMargins(0, 0, 0, 0); H.setSpacing(0)
        rail = QtWidgets.QWidget(); rail.setObjectName("rail"); rail.setFixedWidth(210); R = QtWidgets.QVBoxLayout(rail); R.setContentsMargins(0, 24, 0, 24); R.setSpacing(2)
        t = QtWidgets.QLabel("Skin Fitter"); t.setStyleSheet("font-family:'%s';font-size:15pt;padding:0 18px 18px 18px;" % HEAD); R.addWidget(t)
        self.stack = QtWidgets.QStackedWidget()
        self.pages = [SourcePage(st, self), MapPage(st, self), PreviewPage(st, self), ChecksPage(st, self), BuildPage(st, self)]
        self.btns = QtWidgets.QButtonGroup(self)
        for i, (n, pg) in enumerate(zip(["1  Source", "2  Bone map", "3  Preview", "4  Checks", "5  Build"], self.pages)):
            b = QtWidgets.QPushButton(n); b.setCheckable(True); self.btns.addButton(b, i); R.addWidget(b); self.stack.addWidget(pg)
            b.clicked.connect(lambda _=False, i=i: self.go(i))
            QtGui.QShortcut(QtGui.QKeySequence("Ctrl+%d" % (i + 1)), self, activated=lambda i=i: self.go(i))
        QtGui.QShortcut(QtGui.QKeySequence("Alt+Right"), self, activated=lambda: self.go(min(4, self.stack.currentIndex() + 1)))
        QtGui.QShortcut(QtGui.QKeySequence("Alt+Left"), self, activated=lambda: self.go(max(0, self.stack.currentIndex() - 1)))
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+O"), self, activated=lambda: (self.go(0), self.pages[0].pick_src()))
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, activated=lambda: self.pages[1].save_map())
        R.addStretch(1); H.addWidget(rail); H.addWidget(self.stack, 1)
        self.fx = QtWidgets.QGraphicsOpacityEffect(self.stack); self.stack.setGraphicsEffect(self.fx)
        self.fade = QtCore.QPropertyAnimation(self.fx, b"opacity", self); self.fade.setDuration(180)
        self.go(0, animate=False)

    def go(self, i, animate=True):
        self.btns.button(i).setChecked(True); self.stack.setCurrentIndex(i)
        if animate: self.fade.stop(); self.fade.setStartValue(0.2); self.fade.setEndValue(1.0); self.fade.start()
        else: self.fx.setOpacity(1.0)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()

    def dropEvent(self, e):
        p = e.mimeData().urls()[0].toLocalFile(); self.go(0); self.pages[0].src.setText(p)


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--demo"); ap.add_argument("--shots"); a = ap.parse_args()
    app = QtWidgets.QApplication(sys.argv); app.setStyleSheet(QSS)
    st = State(); st.names_override = None
    w = Win(st); w.show()
    if a.demo:
        d = a.demo; sp = w.pages[0]
        sp.src.setText(os.path.join(d, "source.json")); sp.ret.setText(os.path.join(d, "synth_retail.dat")); sp.grp.setText(os.path.join(d, "groups.json"))
        st.names_override = ["TopN", "HipN", "BustN", "LShoulderJ", "RShoulderJ", "HeadN"]
        sp.load()
    if a.shots:
        os.makedirs(a.shots, exist_ok=True)
        def snap(name): app.processEvents(); QtCore.QThread.msleep(60); app.processEvents(); w.grab().save(os.path.join(a.shots, name))
        w.go(0, False); snap("1_source.png")
        w.go(1, False); w.pages[1].pick_a(w.pages[1].ia["LArmTwist"], 0); snap("2_bonemap.png")
        w.go(2, False); pv = w.pages[2]; pv.set_pose("Bind pose", False); snap("3_preview_bind.png")
        pv.set_pose("Arms raised", False); snap("3_preview_arms.png")
        pv.bones.setCurrentRow(4); snap("3_preview_weights.png"); pv.bones.setCurrentRow(0)
        w.go(3, False); w.pages[3].run(); snap("4_checks.png")
        w.go(4, False); snap("5_build.png")
        return 0
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
