"""Shared m-ex files for the metaknight-slot mod: MxDt.dat, PlCo.dat, MnSlChr.usd, IfAll.usd.

    python tools/mk_slot_files.py --out mods-slot/metaknight-slot/files

WHY A SUPERSET. m-ex keeps one table per boot (MxDt.dat) plus menu/stock atlases indexed by fighter id, and the mods
overlay lets the LATER mod win a disc path both provide (mount order: fighter mods by id, so "metaknight-slot" mounts
after "brawl-kirby-slot"). So this mod ships those four files built ON TOP OF brawl-kirby-slot's copies (when present,
else the ACE disc's): Brawl Kirby's row (internal 34 / external 33, PlBk.dat) stays, and Meta Knight's row is added.
The port's filtered-base rule (docs/mods-packaging.md 2.4) gives a row a fighter slot only when its Pl file resolves,
so with this mod alone Brawl Kirby's row is simply skipped, and with both mods both fighters are there.
Rebuild this mod after brawl-kirby-slot's shared files change (build_mk_slot.py does it every run).

WHICH ROW. ACE has exactly one empty row (34/33), and brawl-kirby-slot uses it. The port has 31 m-ex fighter slots
(GW_MEX_SLOTS; the 6-bit x597 kind field) and ACE already fills 31 of the 32 rows 27..58, so every added fighter
displaces one ACE fighter whatever row it takes (with Brawl Kirby on, ACE's row 58 "Giga Bowser" already falls off
the end). Meta Knight therefore REPLACES ACE's duplicate Wolf: internal 52 / external 51 ("Wolf SSBU", PlWfU.dat).
Growing the tables to 66 rows would not help (the slot cap) and would shift the boss rows.

Row 52/51 becomes a clone of Kirby (internal 4 / external 4) exactly the way mxdt_clone.py made Brawl Kirby's (that
tool is run unchanged, with its disc read redirected to the base file): pl PlBm.dat, name "Brawl Meta Knight",
Kirby's costumes, animation file (PlKbAJ.dat), sound bank, effects and m-ex callbacks.
CSS: the existing ext-51 icon keeps its cell and gets a new icon joint that is a copy of Kirby's (PLACEHOLDER art);
its door portrait (CSP) frames become Kirby's. Stock icons (IfAll) for internal 52 become Kirby's. PlCo.dat's
per-internal-kind tables [4] and [5] get Kirby's entry at 52."""
import sys, os, struct, json, argparse, runpy, io, contextlib
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(HERE)
BKT = os.path.join(os.path.dirname(os.path.dirname(MK)), "experiment", "brawl-kirby", "tools")
BKSLOT = os.path.join(os.path.dirname(os.path.dirname(MK)), "experiment", "brawl-kirby", "mods-slot", "brawl-kirby-slot", "files")
ROOT = r"C:/Users/Gurek/Desktop/GD's Melee"
sys.path.insert(0, ROOT + "/tools/mex_port"); sys.path.insert(0, BKT)
import mex_hsd, texanim_keys
ISO = "C:/iso/SSBM ACE Build v2.0.0.iso"

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--base", default=BKSLOT, help="folder with the base MxDt/PlCo/MnSlChr/IfAll (default brawl-kirby-slot's; missing files come from the disc)")
ap.add_argument("--pl", default="PlBm.dat")
ap.add_argument("--name", default="Brawl Meta Knight")
ap.add_argument("--dst-k", type=int, default=52); ap.add_argument("--dst-e", type=int, default=51)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
SRC_K = SRC_E = 4
log = {"row": {"internal": a.dst_k, "external": a.dst_e, "replaces": None}, "base": {}}

def base_bytes(name):
    p = os.path.join(a.base, name)
    if a.base and os.path.exists(p):
        log["base"][name] = p; return open(p, "rb").read()
    log["base"][name] = "disc"; return mex_hsd.Gcm(ISO).read(name)

def write_archive(path, ar, data, relocs):
    rel = sorted(relocs); tail = ar.raw[ar.o_public:]
    while len(data) % 4: data.append(0)
    body = bytes(data) + b"".join(struct.pack(">I", x) for x in rel) + tail
    open(path, "wb").write(struct.pack(">5I", 0x20 + len(body), len(data), len(rel), ar.nb_public, ar.nb_extern) + ar.raw[0x14:0x20] + body)

# ------------------------------------------------------------------ MxDt.dat: run mxdt_clone.py on the base file
mx_base = base_bytes("MxDt.dat")
_ar = mex_hsd.Archive(mx_base); _d = _ar.data
_u = lambda o: struct.unpack(">I", _d[o:o+4])[0]
_ft = _u(_ar.public("mexData") + 8)
_cs = lambda o: _d[o:_d.index(b"\0", o)].decode("latin1") if o else ""
log["row"]["replaces"] = {"name": _cs(_u(_u(_ft) + 4*a.dst_e)), "pl": _cs(_u(_u(_ft + 4) + 8*a.dst_k))}
class _Gcm:                         # mxdt_clone.py reads the disc's MxDt.dat; hand it the base file instead
    def __init__(self, iso): pass
    def read(self, name): return mx_base if name == "MxDt.dat" else mex_hsd.Gcm(ISO).read(name)
_real = mex_hsd.Gcm; mex_hsd.Gcm = _Gcm
argv = sys.argv
sys.argv = ["mxdt_clone.py", "--out", os.path.join(a.out, "MxDt.dat"), "--pl", a.pl, "--name", a.name,
            "--src-k", str(SRC_K), "--src-e", str(SRC_E), "--dst-k", str(a.dst_k), "--dst-e", str(a.dst_e)]
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    runpy.run_path(os.path.join(BKT, "mxdt_clone.py"), run_name="__main__")
sys.argv = argv; mex_hsd.Gcm = _real
log["mxdt_clone"] = json.loads(buf.getvalue())

# CSS icon of external dst_e: its joint -> the new icon joint appended to MnSlChr (below)
raw = open(os.path.join(a.out, "MxDt.dat"), "rb").read(); ar = mex_hsd.Archive(raw)
data = bytearray(ar.data); relocs = set(ar.reloc_offsets)
u32 = lambda o: struct.unpack(">I", data[o:o+4])[0]
base = ar.public("mexData"); meta = u32(base); menu = u32(base + 4); css = u32(menu + 4)
n_icons = struct.unpack(">i", data[meta+12:meta+16])[0]
icon = [i for i in range(n_icons) if data[css+0xDC+i*0x1C+1] == a.dst_e]
assert len(icon) == 1, icon

# ------------------------------------------------------------------ MnSlChr.usd: new icon joint (copy of Kirby's) + CSP
raw_m = base_bytes("MnSlChr.usd"); am = mex_hsd.Archive(raw_m)
md = bytearray(am.data); mrel = set(am.reloc_offsets)
mu = lambda o: struct.unpack(">I", md[o:o+4])[0]
def mput(o, v): md[o:o+4] = struct.pack(">I", v)
msc = am.public("mexSelectChr")
def chain(root, ch, nx):
    kids = []; o = mu(root + ch)
    while o: kids.append(o); o = mu(o + nx)
    return kids
def clone(node, size, nx):
    while len(md) % 0x20: md.append(0)
    at = len(md); md.extend(md[node:node+size])
    for i in range(0, size, 4):
        if node + i in mrel: mrel.add(at + i)
    mput(at + nx, 0); mrel.discard(at + nx)
    return at
KIRBY_ICON = 20
new_joint = None
for field, ch, nx, size in ((0, 8, 0xC, 0x40), (4, 0, 4, 0x14), (8, 0, 4, 0xC)):
    root = mu(msc + field); kids = chain(root, ch, nx)
    new = clone(kids[KIRBY_ICON - 1], size, nx)
    mput(kids[-1] + nx, new); mrel.add(kids[-1] + nx)
    j = len(kids) + 1
    assert new_joint in (None, j); new_joint = j
cspj = mu(msc + 0x0C); cstride = mu(msc + 0x10); ctex = mu(cspj + 8)
end = struct.unpack(">f", md[mu(ctex + 8) + 4:mu(ctex + 8) + 8])[0]
csp = texanim_keys.copy_frames(md, ctex, [(a.dst_e + c * cstride, SRC_E + c * cstride) for c in range(8) if a.dst_e + c * cstride < end])
write_archive(os.path.join(a.out, "MnSlChr.usd"), am, md, mrel)
row = css + 0xDC + icon[0] * 0x1C
log["css"] = {"icon_index": icon[0], "old_joint": data[row + 4], "new_joint": new_joint, "copied_from_icon_joint": KIRBY_ICON,
              "placeholder": "Kirby's icon art (Meta Knight icon/CSP art not made yet)", "csp_frames": len(csp)}
data[row + 4] = data[row + 5] = new_joint
write_archive(os.path.join(a.out, "MxDt.dat"), ar, data, relocs)

# ------------------------------------------------------------------ PlCo.dat: per-internal-kind tables [4], [5]
raw_p = base_bytes("PlCo.dat"); ap_ = mex_hsd.Archive(raw_p)
pd = bytearray(ap_.data); prel = set(ap_.reloc_offsets)
r = ap_.public("ftLoadCommonData"); log["plco"] = []
for t in (4, 5):
    tb = ap_.u32(r + 4*t); so, do = tb + 4*SRC_K, tb + 4*a.dst_k
    log["plco"].append(f"table {t}: [{a.dst_k}] 0x{ap_.u32(do):X} -> 0x{ap_.u32(so):X}")
    pd[do:do+4] = pd[so:so+4]
    (prel.add if so in prel else prel.discard)(do)
write_archive(os.path.join(a.out, "PlCo.dat"), ap_, pd, prel)

# ------------------------------------------------------------------ IfAll.usd: stock icons of internal dst_k = Kirby's
raw_i = base_bytes("IfAll.usd"); ai = mex_hsd.Archive(raw_i)
idata = bytearray(ai.data); iu = lambda o: struct.unpack(">I", idata[o:o+4])[0]
stc = ai.public("Stc_icns"); reserved, stride = struct.unpack(">HH", idata[stc:stc+4])
tex = iu(iu(iu(stc + 4) + 8) + 8)
stock = texanim_keys.copy_frames(idata, tex, [(reserved + c*stride + a.dst_k, reserved + c*stride + SRC_K) for c in range(8)])
while len(idata) % 4: idata.append(0)
tail = raw_i[ai.o_reloc:]
open(os.path.join(a.out, "IfAll.usd"), "wb").write(struct.pack(">II", 0x20 + len(idata) + len(tail), len(idata)) + raw_i[8:0x20] + bytes(idata) + tail)
log["stock_frames"] = len(stock)
print(json.dumps(log, indent=1))
