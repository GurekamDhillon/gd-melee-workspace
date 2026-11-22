#!/usr/bin/env python3
"""Skin Fitter front door: one skin at a time.

  1 Brawl source   an unpacked Brawl folder or a mod build (pf/fighter/...); a disc image is unpacked by
                   unpack_disc.unpack() when that module is present (it is wired here only if it exists)
  2 Character      the fighter folders found (brawl_root.characters)
  3 Skin           that character's Fit<Name>NN.pac/.pcs with stats read from the file
  4 Melee fighter  pre-selected by skin.detect (changeable)
  5 Slot           add as a new m-ex costume, or replace a colour
  6 Convert        skin.py build (autogroups when no slot config) -> checks -> install; "Needs review" opens the
                   advanced five-step window (ui.py) on the same files
Settings (the Melee disc image, the last folders) live in %APPDATA%/SkinFitter/settings.json, outside the repo;
paths are never written to the log.

    python frontdoor.py
    python frontdoor.py --demo DIR --shots OUT     (synthetic test tree; renders each step to OUT and exits)
"""
import json, os, subprocess, sys
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import skin, brawl_root
from ui import QSS, C, HEAD, fighters

SETTINGS = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "SkinFitter", "settings.json")
COLOURS = ["Nr", "Re", "Bu", "Gr", "Wh", "Ye", "Bk", "Pi", "Or", "La", "Aq", "Gy", "Rd", "Bl"]


def load_settings():
    try: return json.load(open(SETTINGS))
    except Exception: return {}


def save_settings(s):
    try:
        os.makedirs(os.path.dirname(SETTINGS), exist_ok=True); json.dump(s, open(SETTINGS, "w"), indent=1)
    except Exception: pass


def stats(path, work):
    """Triangles, bones, textures of one costume file (via the same reader skin.py uses)."""
    s = skin.export_source(path, work)
    tri = sum(len(o["tris"]) // 3 for o in s["objects"])
    return {"triangles": tri, "bones": len(s["bones"]), "objects": len(s["objects"]), "textures": len(s.get("textures", [])),
            "largest texture": max((max(t["w"], t["h"]) for t in s.get("textures", [])), default=0)}, s


class Front(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Skin Fitter"); self.resize(1100, 720); self.setAcceptDrops(True)
        self.set = load_settings(); self.root = None; self.chars = {}; self.src = None; self.srcpath = None
        self.work = os.path.join(skin.ROOT, "_build", "tmp", "skin-front"); os.makedirs(self.work, exist_ok=True)
        cw = QtWidgets.QWidget(); cw.setObjectName("page"); self.setCentralWidget(cw)
        L = QtWidgets.QVBoxLayout(cw); L.setContentsMargins(40, 28, 40, 24); L.setSpacing(12)
        top = QtWidgets.QHBoxLayout(); t = QtWidgets.QLabel("Skin Fitter"); t.setObjectName("h1"); top.addWidget(t); top.addStretch(1)
        self.melee = QtWidgets.QLabel(); self.melee.setObjectName("lede"); top.addWidget(self.melee)
        b = QtWidgets.QPushButton("Set Melee disc"); b.clicked.connect(self.pick_melee); top.addWidget(b)
        adv = QtWidgets.QPushButton("Advanced"); adv.clicked.connect(self.advanced); top.addWidget(adv); L.addLayout(top)
        self.show_melee()
        cols = QtWidgets.QHBoxLayout(); L.addLayout(cols, 1)
        def col(title, w):
            v = QtWidgets.QVBoxLayout(); h = QtWidgets.QLabel(title); h.setStyleSheet("font-family:'%s';font-size:12.5pt;" % HEAD); v.addWidget(h); v.addWidget(w, 1); cols.addLayout(v, 1); return v
        # 1 source
        self.drop = QtWidgets.QPushButton("Drop an unpacked Brawl folder\nor mod build here\n\nor click to browse"); self.drop.setMinimumHeight(140)
        self.drop.setStyleSheet("border:2px dashed %s;border-radius:6px;color:%s;" % (C["line"], C["dim"])); self.drop.clicked.connect(self.pick_root)
        v = col("1  Brawl source", self.drop); v.setStretch(1, 0); v.addStretch(1)
        # 2 character, 3 skin
        self.clist = QtWidgets.QListWidget(); col("2  Character", self.clist); self.clist.currentTextChanged.connect(self.pick_char)
        self.slist = QtWidgets.QListWidget(); v3 = col("3  Skin", self.slist); self.slist.currentRowChanged.connect(self.pick_skin)
        self.sinfo = QtWidgets.QLabel(""); self.sinfo.setObjectName("lede"); self.sinfo.setWordWrap(True); v3.addWidget(self.sinfo)
        # 4 fighter, 5 slot, 6 convert
        right = QtWidgets.QWidget(); R = QtWidgets.QFormLayout(right); R.setSpacing(10)
        self.fig = QtWidgets.QComboBox(); self.fig.addItems(fighters()); R.addRow("4  Melee fighter", self.fig)
        self.det = QtWidgets.QLabel(""); self.det.setObjectName("lede"); R.addRow("", self.det)
        self.slot = QtWidgets.QComboBox(); self.slot.addItems(["Add as a new m-ex costume"] + ["Replace colour %s" % c for c in COLOURS]); R.addRow("5  Slot", self.slot)
        self.name = QtWidgets.QLineEdit(); R.addRow("Name", self.name)
        self.mods = QtWidgets.QLineEdit(self.set.get("mods", os.path.join(skin.ROOT, "_build", "mods-local"))); R.addRow("Mods folder", self.mods)
        self.go = QtWidgets.QPushButton("Convert this skin"); self.go.setObjectName("go"); self.go.clicked.connect(self.convert); R.addRow(self.go)
        self.verdict = QtWidgets.QLabel(""); self.verdict.setWordWrap(True); R.addRow(self.verdict)
        un = QtWidgets.QPushButton("Uninstall what I installed"); un.clicked.connect(self.uninstall); R.addRow(un)
        col("6  Convert", right)
        self.log = QtWidgets.QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(170); L.addWidget(self.log)
        self.proc = QtCore.QProcess(self); self.proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.proc.readyRead.connect(lambda: self.log.appendPlainText(bytes(self.proc.readAll()).decode(errors="replace").rstrip()))
        self.proc.finished.connect(self.done)
        if self.set.get("brawl_root") and os.path.isdir(self.set["brawl_root"]): self.open_root(self.set["brawl_root"])

    # -- settings / melee disc
    def show_melee(self):
        ok = bool(self.set.get("melee_image") or os.environ.get("GW_ISO_VANILLA"))
        self.melee.setText("Melee disc: set" if ok else "Melee disc: not set")

    def pick_melee(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Your Melee disc image", "", "Disc images (*.iso *.gcm *.ciso *.rvz);;All files (*)")
        if p: self.set["melee_image"] = p; save_settings(self.set); self.show_melee()

    # -- 1 source
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()

    def dropEvent(self, e): self.open_root(e.mimeData().urls()[0].toLocalFile())

    def pick_root(self):
        p = QtWidgets.QFileDialog.getExistingDirectory(self, "Unpacked Brawl folder or mod build")
        if p: self.open_root(p)

    def open_root(self, p):
        if os.path.isfile(p):
            try:
                import unpack_disc                                  # optional module (disc images)
                out = os.path.join(os.path.dirname(SETTINGS), "brawl-unpacked"); self.log.appendPlainText("Unpacking the disc image once...")
                QtWidgets.QApplication.processEvents(); p = unpack_disc.unpack(p, out)
            except ImportError:
                self.log.appendPlainText("That is a file. Unpack the disc with your Brawl tools and choose the folder."); return
            except Exception as e:
                self.log.appendPlainText("Could not unpack it: %s" % e); return
        try:
            self.root = brawl_root.brawl_root(p)
        except brawl_root.NotUnpacked as e:
            self.log.appendPlainText(str(e)); return
        self.chars = brawl_root.characters(self.root); self.set["brawl_root"] = p; save_settings(self.set)
        self.drop.setText("%d characters found\n\nclick to choose another folder" % len(self.chars))
        self.clist.clear(); self.clist.addItems(list(self.chars))

    # -- 2, 3
    def pick_char(self, name):
        self.slist.clear()
        for f in self.chars.get(name, []):
            self.slist.addItem("%s   costume %02d" % (os.path.basename(f), brawl_root.costume_number(f) or 0))

    def pick_skin(self, row):
        name = self.clist.currentItem().text() if self.clist.currentItem() else None
        if name is None or row < 0: return
        self.srcpath = self.chars[name][row]
        try:
            st, self.src = stats(self.srcpath, os.path.join(self.work, "src"))
        except skin.SourceError as e:
            self.sinfo.setText("Cannot read this file: %s" % e); self.src = None; return
        self.sinfo.setText("  ".join("%s %s" % (v, k) for k, v in st.items()))
        det = skin.detect(self.src, self.srcpath)
        if det and det[0][0] >= 0.5:
            self.fig.setCurrentText(det[0][1]); self.det.setText("Detected from the skeleton (%.2f)" % det[0][0])
        else: self.det.setText("No confident match: choose the fighter")
        self.name.setText(os.path.splitext(os.path.basename(self.srcpath))[0])

    # -- 6
    def convert(self):
        if not self.src: self.log.appendPlainText("Choose a skin first (steps 1 to 3)."); return
        f = self.fig.currentText(); env = dict(os.environ)
        if self.set.get("melee_image"): env["GW_ISO_VANILLA"] = self.set["melee_image"]
        import build_melee_fighter as B
        code = B.FIGHTERS[f][1]; md = os.path.join(self.work, "melee", f)
        if not env.get("GW_ISO_VANILLA") and not os.path.exists(os.path.join(md, "Pl%sNr.dat" % code)): self.log.appendPlainText("Set your Melee disc first."); return
        if not os.path.exists(os.path.join(md, "Pl%sNr.dat" % code)):
            for cos in ("Nr", ""):
                r = subprocess.run([sys.executable, os.path.join(HERE, "skin.py"), "fetch", "--fighter", f, "--costume", cos, "--out", md], env=env, capture_output=True, text=True)
                if r.returncode: self.log.appendPlainText("Could not read the Melee disc: %s" % r.stderr.strip()[-200:]); return
        self.set["mods"] = self.mods.text(); save_settings(self.set)
        out = os.path.join(self.work, "out", "%s_%s.dat" % (code, self.name.text().replace(" ", "_")))
        os.makedirs(os.path.dirname(out), exist_ok=True); self.out = out
        args = [os.path.join(HERE, "skin.py"), "build", "--source", self.srcpath, "--fighter", f, "--retail", os.path.join(md, "Pl%sNr.dat" % code),
                ] + (["--plco", os.path.join(md, "PlCo.dat")] if os.path.exists(os.path.join(md, "PlCo.dat")) else []) + ["--fighter-dat", os.path.join(md, "Pl%s.dat" % code), "--out", out,
                "--install", self.mods.text(), "--name", self.name.text()]
        if self.slot.currentIndex() > 0: args += ["--slot", COLOURS[self.slot.currentIndex() - 1]]
        self.verdict.setText("Converting..."); self.log.appendPlainText("> converting %s onto %s" % (os.path.basename(self.srcpath), f))
        self.proc.setProcessEnvironment(QtCore.QProcessEnvironment.systemEnvironment())
        pe = QtCore.QProcessEnvironment.systemEnvironment()
        for k in ("GW_ISO_VANILLA",):
            if env.get(k): pe.insert(k, env[k])
        self.proc.setProcessEnvironment(pe); self.proc.start(sys.executable, args)

    def done(self, code, _):
        ckp = os.path.splitext(self.out)[0] + "_work/checks.json"
        ck = json.load(open(ckp)) if os.path.exists(ckp) else None
        review = code != 0 or not ck or any("NEEDS REVIEW" in s for s in ck.get("steps", [])) or ck.get("low_confidence")
        if code == 0 and ck and ck["netplay_safe"]:
            self.verdict.setText("<span style='color:%s;font-family:%s;font-size:14pt'>Installed, netplay-safe</span>%s" % (
                C["hi"], HEAD, "<br><span style='color:%s'>Needs review: open Advanced to check the bone or slot map.</span>" % C["mid"] if review else ""))
            self.remember_install()
        elif code == 2:
            self.verdict.setText("<span style='color:%s'>Over the limits; not installed. The log says which check failed.</span>" % C["lo"])
        elif code == 3:
            self.verdict.setText("<span style='color:%s'>Could not read this skin; see the log.</span>" % C["lo"])
        else:
            self.verdict.setText("<span style='color:%s'>Not installed. Needs review in Advanced.</span>" % C["lo"])

    def remember_install(self):
        import re
        mid = re.sub(r"[^a-z0-9]+", "-", (self.name.text() or "skin").lower()).strip("-")
        inst = self.set.setdefault("installed", [])
        p = os.path.join(self.mods.text(), mid)
        if p not in inst: inst.append(p)
        save_settings(self.set)

    def uninstall(self):
        import shutil
        n = 0
        for p in self.set.get("installed", []):
            if os.path.isfile(os.path.join(p, "mod.json")):
                shutil.rmtree(p, ignore_errors=True); n += 1
        self.set["installed"] = []; save_settings(self.set); self.log.appendPlainText("Removed %d installed skins." % n)

    def advanced(self):
        subprocess.Popen([sys.executable, os.path.join(HERE, "ui.py")])


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--demo"); ap.add_argument("--shots"); a = ap.parse_args()
    if a.demo:   # keep the user's real settings untouched
        global SETTINGS; SETTINGS = os.path.join(a.demo, "settings.json")
    app = QtWidgets.QApplication(sys.argv); app.setStyleSheet(QSS)
    w = Front(); w.show()
    if a.demo:
        w.work = os.path.join(a.demo, "front-work")
        w.open_root(os.path.join(a.demo, "brawltree")); w.clist.setCurrentRow(0); w.slist.setCurrentRow(0)
        w.mods.setText(os.path.join(a.demo, "mods")); w.fig.setCurrentText("luigi")
    if a.shots:
        os.makedirs(a.shots, exist_ok=True); app.processEvents(); w.grab().save(os.path.join(a.shots, "front_1_picked.png"))
        w.convert(); w.proc.waitForFinished(120000); app.processEvents(); w.grab().save(os.path.join(a.shots, "front_2_converted.png"))
        print("verdict:", w.verdict.text()); print(w.log.toPlainText()[-1500:]); return 0
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
