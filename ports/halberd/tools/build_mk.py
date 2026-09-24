"""Meta Knight Phase 1 scripts + numbers, built for MK's OWN skeleton and clips (Phases 2/3: model/, anim/).

    python tools/build_mk.py [--preset tuning.json] [--out build/stage]

Outputs
  <out>/files/PlKb.dat    stage A: the fighter file as built (scripts, attributes). experiment/brawl-kirby/tools/
                          verify_mod.py checks THIS one (every untouched row byte-identical to vanilla Kirby).
  <out>/final/PlBm.dat    stage B = stage A + the MK-skeleton pass over the scripts this build does not write
                          (Kirby-authored bone numbers -> MK joints, ModelVis from anim/vis_events.json). This is the
                          file the slot ships; tools/verify_mk.py checks it (bones, hurtbox joints, vis, extras).
  <out>/CHANGES.json      Brawl Kirby schema (+ MK fields), <out>/geno.json (Geno profile: multi-jump + v1 overlays),
  analysis/mk_moves.json  per-move coverage, analysis/v1_stubs.json (what is still not expressible).

Method = the Brawl Kirby Phase 1 build (brawl-kirby/tools/build_mod.py): vanilla Melee Kirby is the base file (the
behaviour host: Kirby's clone code runs MK), scripts are rebuilt APPEND-ONLY, attributes come from the cast scaling
(tools/mk_scaling.py), every value goes through brawl-kirby/tools/tuning.py. Frame convention (both games): a hitbox
created at counter c is active from frame c+1; terminated at counter e = last active frame e.

Skeleton contract (model_anim_ready.md): 105 joints, 0-76 = Brawl FitMetaknight00 bone ids, no insert slots, so a
hitbox's bone field (a PART slot = joint index for MK) IS the Brawl bone id, with the Brawl offset and size unscaled
(model_scaling = MK's Brawl Size). Clip lengths are Brawl's (anim/out/motion_rows.json + CLIP_OVERRIDES below, applied
after install by build_mk_slot.py). Kirby-authored events kept in a rebuilt script (GFX, SFX, flags) are moved with the
first hit (brawl-kirby retime rule) and their Kirby part-slot bones are remapped to MK joints (install_mk.kirby_spaces).

Geno v1 (geno_v1_encodings.md): the Pl file stays plain Melee ftcmd (runs on every exe). Everything that needs an
escape goes into geno.json "subactions" overlays (full scripts with the escapes inline), used only by the Geno exe."""
import sys, os, json, struct, collections, copy, math, argparse, fnmatch, shutil, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(HERE); EXP = os.path.join(os.path.dirname(os.path.dirname(MK)), "experiment")
BK = os.path.join(EXP, "brawl-kirby"); BKT = os.path.join(BK, "tools")
ap = argparse.ArgumentParser()
ap.add_argument("--preset", default=os.path.join(MK, "tuning.json"))
ap.add_argument("--out", default=os.path.join(MK, "build", "stage"))
A = ap.parse_args()
os.makedirs(os.path.join(MK, "analysis"), exist_ok=True)
os.environ["MD_OUT"] = os.path.join(MK, "analysis", "_host_kirby_vanilla.json")   # melee_dump writes its decode on import
os.environ.pop("MD_IN", None)
sys.path.insert(0, BKT); sys.path.insert(0, os.path.join(MK, "model", "tools"))
import melee_dump as MD
import tuning as TUN
import install_mk as IM                      # Phase 2/3's installer: skeleton, Kirby part-slot map, apply_vis, Writer

# ------------------------------------------------------------------ tuning: Meta Knight move keys
MOVE_KEYS = ["jab", "rapid_jab_start", "rapid_jab", "rapid_jab_end", "dash_attack", "ftilt", "ftilt2", "ftilt3", "utilt", "dtilt",
             "fsmash", "usmash", "dsmash", "nair", "fair", "bair", "uair", "dair",
             "nair_land", "fair_land", "bair_land", "uair_land", "dair_land",
             "grab", "dash_grab", "pummel", "throwf", "throwb", "throwhi", "throwlw",
             "ledge_attack_fast", "ledge_attack_slow", "getup_attack_up", "getup_attack_down",
             "tornado_start", "tornado", "tornado_end", "drill_rush", "drill_rush_air",
             "shuttle_loop_rise", "shuttle_loop_loop", "shuttle_loop_fall", "shuttle_loop_land",
             "cape_start", "cape_vanish", "cape_attack", "cape_end", "cape_end_air", "jumpaerial",
             "glide", "glide_attack", "drill_start", "taunt", "wait3"]          # Geno v2 rows (the exe with geno.json)
TUN.MOVE_KEYS = MOVE_KEYS
TUN.ALIASES = {"fthrow": "throwf", "bthrow": "throwb", "uthrow": "throwhi", "dthrow": "throwlw", "mach_tornado": "tornado",
               "neutral_b": "tornado", "side_b": "drill_rush", "up_b": "shuttle_loop_rise", "down_b": "cape_attack"}
MK_KNOBS = {"hitbox_scale": 1.0, "autolink_angle": 80, "tornado_rehit": 10, "drill_rehit": None, "model_scaling": 0.95,
            "geno_v1": True, "geno_v2": True, "upb_glide": "Glide", "taunt_stick": 0.5, "wait3_chance": 3}
raw_cfg = json.load(open(A.preset, encoding="utf-8"))
knobs = dict(MK_KNOBS); knobs.update({k: v for k, v in (raw_cfg.get("mk") or {}).items() if not k.startswith("_")})
cfg = {k: v for k, v in raw_cfg.items() if k != "mk"}
TUN.Tuning(cfg, A.preset)
TUN.ACTIVE, TUN.PRESET, TUN.OUT_DIR = cfg, os.path.relpath(A.preset, MK), A.out
TT = TUN.current()

ar = MD.ar
data = bytearray(ar.data)
new_relocs = []
def u32(o): return struct.unpack(">I", data[o:o+4])[0]
def put32(o, v): data[o:o+4] = struct.pack(">I", v & 0xFFFFFFFF)
def putf(o, v): data[o:o+4] = struct.pack(">f", v)
def getf(o): return struct.unpack(">f", data[o:o+4])[0]

B = json.load(open(MK + "/analysis/brawl_metaknight.json"))
S = {int(s["hex"], 16): s for s in B["subactions"]["list"]}
def SUB(h): return S[int(h, 16)]
SC = json.load(open(MK + "/analysis/scaling_mk.json"))
MROWS = {r["index"]: r for r in MD.rows}
MROWS_BY_NAME = {}
for r in MD.rows:
    if r["category"] != "copy_ability" and r["name"] not in MROWS_BY_NAME: MROWS_BY_NAME[r["name"]] = r["index"]
changes = {"fighter": "Brawl Meta Knight (Phase 1 scripts on MK's own skeleton and clips, Kirby behaviour host)",
           "attributes": [], "special_attributes": [], "moves": [], "untouched": [], "notes": [], "knobs": knobs, "tuning": TT.summary()}
moves_report = []; stubs = []; overlays = []

# ================================================================== skeleton / clips (Phases 2 and 3)
SKEL = IM.skeleton(); JIDX = {j["name"]: i for i, j in enumerate(SKEL)}
MR = json.load(open(os.path.join(MK, "anim", "out", "motion_rows.json")))
CLIPS = {c["brawl_clip"]: c for c in MR["clips"] + MR["extras"]}
ROWCLIP = {r: c["brawl_clip"] for c in MR["clips"] for r in c["rows"]}
# Rows whose clip this build chooses (the scripts and the clips must agree); build_mk_slot.py applies them after install:
CLIP_OVERRIDES = {
    47: "AttackS3S2",        # ftilt 2 on the unreachable Attack12 motion (entered by the Geno v1 chain only)
    48: "AttackS3S3",        # ftilt 3 on the unreachable Attack13 motion (row had no clip / script)
    322: "SpecialSDrill",    # Drill Rush: one row on Kirby's hammer code -> the drill clip (the 22-frame start clip has no hits)
    323: "SpecialSDrill",
    328: "SpecialHi",        # air Shuttle Loop rises with the slash too (8-frame SpecialAirHiStart has no hitbox)
    333: "SpecialLwEnd",     # Dimensional Cape: stone HOLD = the vanish (MK hidden; clip frozen, never seen)
    334: "SpecialLw",        #   stone END = the reappear attack (was SpecialLwEnd, the no-attack reappear)
    336: "SpecialAirLwEnd",
    337: "SpecialAirLw",
}
# Geno v2 (geno_v2_encodings.md): MK's extra clips (no Kirby motion has them) get rows of their own, on Kirby COPY-ABILITY
# rows (338-478: unreachable for MK - his neutral B has no catch box, so he never copies). The row count stays Kirby's
# (the port rewrites the kind bits of exactly ftData_Table_Unk0[kind].count rows; an appended row would take the cross-kind
# animation path). The Geno v2 states name these rows as their "subaction"; the Pl scripts are plain ftcmd (the main exe
# never reaches them), the v1/v2 escapes go into geno.json overlays of the same rows.
V2ROWS = collections.OrderedDict([
    ("GlideStart", (338, "GlideStart")), ("Glide", (339, "GlideDirection")), ("GlideAttack", (340, "GlideAttack")),
    ("GlideLanding", (341, "GlideLanding")), ("GlideEnd", (342, "GlideEnd")),
    ("DrillStart", (343, "SpecialSStart")), ("DrillStartAir", (344, "SpecialAirSStart")), ("Drill", (345, "SpecialSDrill")),
    ("DrillEnd", (346, "SpecialAirSEnd")), ("DrillEndGround", (347, "SpecialSEnd")), ("TornadoEnd", (348, "SpecialAirNEnd")),
    ("AppealHi", (349, "AppealHi")), ("AppealS", (350, "AppealS")), ("Wait3", (351, "Wait3")),
    # Geno v3 Shuttle Loop (geno.anim_motion: the clips' TransN moves MK in the air and on the ground)
    ("UpB", (352, "SpecialHi")), ("UpBAir", (353, "SpecialAirHiStart")), ("UpBLoop", (354, "SpecialHiLoop")),
    ("UpBLand", (355, "SpecialHiEnd")),
    # Geno v3 Dimensional Cape (geno.cape / geno.cape.attack / geno.cape.end; order = the engine's pairing)
    ("CapeStart", (356, "SpecialLwStart")), ("CapeStartAir", (357, "SpecialAirLwStart")),
    ("CapeN", (358, "SpecialLw")), ("CapeNAir", (359, "SpecialAirLw")), ("CapeF", (360, "SpecialLwF")),
    ("CapeFAir", (361, "SpecialAirLwF")), ("CapeB", (362, "SpecialLwB")), ("CapeBAir", (363, "SpecialAirLwB")),
    ("CapeEnd", (364, "SpecialLwEnd")), ("CapeEndAir", (365, "SpecialAirLwEnd"))])
CLIP_OVERRIDES.update({r: c for r, c in V2ROWS.values()})
ROW_FLAGS = {r: 0x00000004 for r, _ in V2ROWS.values()}      # plain rows (kind bits are rewritten by the port anyway)
ROW_FLAGS[V2ROWS["Drill"][0]] = 0x80000004                    # animation-driven: TransN -> fp->x6A4_transNOffset (the drill's speed)
for _n in ("UpB", "UpBAir", "UpBLoop", "CapeN", "CapeNAir", "CapeF", "CapeFAir", "CapeB", "CapeBAir"):
    ROW_FLAGS[V2ROWS[_n][0]] = 0x80000004                    # root motion (TransN) moves MK: Shuttle Loop, the cape's reappears
ROWCLIP.update(CLIP_OVERRIDES)
def clip_frames(row): return int(CLIPS[ROWCLIP[row]]["frames"])
VIS = {c["brawl_clip"]: c for c in json.load(open(os.path.join(MK, "anim", "vis_events.json")))["clips"]}
MV = lambda i, v: (31 << 26) | ((i & 0x7F) << 19) | (v & 0x7FFFF)
BODY_STATE = {0: 0, 1: 1, 2: 0, 3: 0}
def vis_events(row, hexid=None):
    """ModelVis for the row's clip: anim/vis_events.json, else the Brawl subaction's Model Changer events."""
    c = VIS.get(ROWCLIP[row])
    if c is not None:
        ev = [(e["frame"], e["index"], e["value"]) for e in c["melee_modelvis_suggested"]]
    else:
        ev = []
        if hexid:
            for ch, evs in SUB(hexid)["channels_raw"].items():
                f = 0
                for e in evs:
                    n = e.get("name"); a = e.get("args")
                    if n == "Synchronous Timer": f += a[0]
                    elif n == "Asynchronous Timer": f = max(f, a[0])
                    elif n == "Model Changer 2" and a[0] == 2: ev.append((int(f), 0, a[1]))
                    elif n == "Model Changer 1" and a[0] == 1: ev.append((int(f), 1, BODY_STATE.get(a[1], 0)))
    ev = sorted({(min(f, clip_frames(row) - 1), i, v) for f, i, v in ev})
    return [(f, [MV(i, v)], f"ModelVis({i},{v})") for f, i, v in ev]
SLOT, _JOINT = IM.kirby_spaces()          # Kirby part slot -> MK joint (Kirby-authored GFX / hurtbox / wind bones)
HURT = {h["bone"] for h in B["hurtboxes"]}
def to_hurt(j):
    while j not in HURT and j > 0: j = SKEL[j]["parent_index"]
    return j if j in HURT else 6
def remap_host_words(words):
    """A Kirby-authored command (list of words) -> the same command with MK joints."""
    w = list(words); op = w[0] >> 26
    if op == 10 and not (w[0] >> 17) & 1 and not (w[0] >> 15) & 1:
        b = (w[0] >> 18) & 0xFF; w[0] = (w[0] & ~(0xFF << 18)) | (SLOT.get(b, 0) << 18)
    elif op == 28:
        b = (w[0] >> 18) & 0xFF; w[0] = (w[0] & ~(0xFF << 18)) | (to_hurt(SLOT.get(b, 6)) << 18)
    elif op == 58:
        b = w[0] & 0xFF; w[0] = (w[0] & ~0xFF) | SLOT.get(b, 0)
    elif op == 11 and not (w[0] >> 10) & 1:
        b = (w[0] >> 11) & 0xFF; w[0] = (w[0] & ~(0xFF << 11)) | (SLOT.get(b, 0) << 11)
    return w

# ================================================================== 1. common attributes (cast-scaled)
root = MD.root; ca = MD.P(root)
moff = {a["name"]: (int(a["offset"], 16), a["type"]) for a in MD.common}
def write_attr(nm, brawl_val, entry=None, brawl_raw=None, note=None):
    off, ty = moff[nm]
    before = MD.i32(ca + off) if ty == "int" else getf(ca + off)
    v, tpol = TT.attr(nm, brawl_val, before, entry, brawl_raw=brawl_raw, is_int=(ty == "int"))
    if ty == "int": put32(ca + off, int(v))
    else: putf(ca + off, float(v))
    rec = {"name": nm, "offset": f"0x{off:03X}", "melee_before": round(before, 5), "brawl_metaknight": brawl_raw if entry is None else entry["brawl_kirby"],
           "written": v, "variant": entry["recommended_variant"] if entry else "synthesized", "tuning": tpol}
    if note: rec["note"] = note
    changes["attributes"].append(rec)
    return v
for e in SC["attributes"]:
    write_attr(e["melee_attr"], e["recommended_value"], e)
write_attr("rapid_jab_window", 0, brawl_raw=0,
           note="MK's jab is rapid-only (no Attack11-13 in Brawl): Attack11 arms the rapid jab at counter 2 and window 0 enters "
                "Attack100Start on the next frame; the loop continues while A is pressed/released between checkpoints")
write_attr("model_scaling", knobs["model_scaling"], brawl_raw=0.95,
           note="MK's Brawl Size (0x0B4); MK's own model, hitbox sizes and offsets are all in Brawl units")

# ================================================================== 1b. host special attributes (Kirby's ftKb_DatAttrs)
sa = MD.P(root + 4)
soff = {s["name"]: int(s["offset"], 16) for s in MD.special}
def write_special(nm, brawl_val, note, is_int=False, brawl_raw=None):
    off = soff[nm]
    before = MD.i32(sa + off) if is_int else getf(sa + off)
    v, tpol = TT.attr(nm, brawl_val, before, brawl_raw=brawl_raw, is_int=is_int)
    if is_int: put32(sa + off, int(v))
    else: putf(sa + off, float(v))
    changes["special_attributes"].append({"name": nm, "offset": f"0x{off:03X}", "melee_before": round(before, 5) if not is_int else before,
                                          "brawl_metaknight": brawl_raw, "written": v, "variant": note, "tuning": tpol})
    return v
jv = [e for e in SC["attributes"] if e["key"] == "jump_v_initial"][0]
kjump = jv["recommended_value"] / jv["brawl_kirby"]
HOPS = [2.2, 2.1, 2.0, 1.88, 1.75]        # Brawl MK Misc MultiJump hop velocities (IR multijump.hop_velocities)
air_vy = [write_special(f"jumpaerial_jump{i+1}_vertical_momentum", round(h * kjump, 4), f"brawl hop x {kjump:.4f} (jump_v_initial scale)", brawl_raw=h)
          for i, h in enumerate(HOPS)]
write_special("speciallw_max_time_in_stone", 8, "Dimensional Cape: vanish frames (stone hold reused; min = max so it is fixed)", is_int=True)
write_special("speciallw_min_time_in_stone", 8, "Dimensional Cape: vanish frames", is_int=True)
write_special("speciallw_gravity", 0.4, "Dimensional Cape (air): sink speed while vanished (Kirby's stone drop 4.5)")
write_special("speciallw_freefall_toggle", 20.0, "Dimensional Cape: != 0 -> the end row enters FallSpecial with this landing lag")
changes["notes"].append("Multi-jump: 6 jumps (1 ground + 5 air) = Kirby's own 5-state table; hop velocities are Brawl MK's x the jump "
                        "scale. geno.json carries the same jumps.max / air_vy for the Geno exe.")

# ================================================================== 2. script building blocks
ELEM = {"Normal": 0, "Fire": 1, "Electric": 2, "Slash": 3, "Coin": 4, "Ice": 5, "Sleep": 6, "Grounded": 8, "Cape": 10, "Darkness": 13, "Flower": 15}
SFXKIND = {"Punch": 1, "Kick": 2, "Slash": 3}
SFXLVL = {"Weak": 0, "Medium": 1, "Strong": 2}
HB_OPS = {"Hitbox", "ClearHitboxes", "RemoveHitbox", "HitboxDamage", "HitboxSize", "IASA"}
FLOW = {"SyncWait", "AsyncWait", "End", "Goto", "Subroutine", "Return", "SetLoop", "ExecLoop", "SetTimerAnim"}
def s16(v): return int(round(v * 256)) & 0xFFFF
def pack_hitbox(slot, joint, dmg, size, off, ang, kbg, wdsk, bkb, elem, shield, lvl, kind, gnd, air, flags5, group=0, grabbed=0):
    w0 = (11 << 26) | (slot << 23) | (group << 20) | (grabbed << 19) | (joint << 11) | (min(int(round(dmg)), 1023))
    w1 = (min(int(round(size * 256)), 0xFFFF) << 16) | s16(off[0])
    w2 = (s16(off[1]) << 16) | s16(off[2])
    w3 = (ang << 23) | (kbg << 14) | (wdsk << 5) | flags5
    w4 = (bkb << 23) | (elem << 18) | ((shield & 0xFF) << 10) | (lvl << 7) | (kind << 2) | (int(gnd) << 1) | int(air)
    return [w0, w1, w2, w3, w4]
FLAGN = ["hits_items", "ignore_thrown", "ignore_scale", "clank", "rebound"]
def flags5_of(t): return sum(1 << (4 - i) for i, n in enumerate(FLAGN) if n in t["flags"])

# ---- Geno v1 escapes (geno_v1_encodings.md; opcode 59)
def G(sub, ln, lo=0): return (59 << 26) | (sub << 20) | (ln << 16) | (lo & 0xFFFF)
def fbits(x): return struct.unpack(">I", struct.pack(">f", x))[0]
V_AIR, V_FACING, V_VEL_Y, V_FWD_VEL = 0x00, 0x01, 0x03, 0x05
def PUT(vid, val, is_float=True): return [G(0x09, 3), vid, fbits(val) if is_float else int(val) & 0xFFFFFFFF]
C_ALWAYS, C_ANIM_END, C_GROUND, C_AIR, C_PRESSED = 0, 1, 2, 3, 4
BTN_ATTACK = 1 << 0
def TGT_MOTION(mid, raw=False): return (0 << 28) | ((1 << 27) if raw else 0) | mid
def CHG(cond, target, args=(), once=False): return [G(0x30, 2 + len(args), (cond << 8) | ((1 << 2) if once else 0)), target, *args]
def LINK(mask, mode=1): return [G(0x39, 2, mask << 8), mode]
# v1 CHGAND / RAND / ORIG and the v2 GENO target (geno_v2_encodings.md section 3)
C_VAR, C_VALUE = 7, 9
CMP_EQ, CMP_LT, CMP_GT = 0, 2, 4
def CHGAND(cond, args=(), cmp=0): return [G(0x31, 1 + len(args), (cond << 8) | (cmp << 4)), *args]
def CHGV(cond, target, args=(), cmp=0, once=False): return [G(0x30, 2 + len(args), (cond << 8) | (cmp << 4) | ((1 << 2) if once else 0)), target, *args]
def RAND(var, n): return [G(0x0A, 2, var << 8), n]
ORIG = [G(0x13, 1)]
RA_INT0 = (1 << 6) | 0
V_STICK_X, V_STICK_Y = 0x08, 0x09
def TGT_GENO(n, keep_frame=False): return (2 << 28) | ((1 << 26) if keep_frame else 0) | n
# Geno v2 state list (index n = Melee motion 0x400 + n = script target GENO(n)); the order is part of the contract, keep it.
STATE_ORDER = ["GlideStart", "Glide", "GlideAttack", "GlideLanding", "GlideEnd", "Tornado", "TornadoEnd", "TornadoEndGround",
               "DrillStart", "DrillStartAir", "Drill", "DrillEndGround", "DrillEnd", "AppealHi", "AppealS", "Wait3",
               "UpB", "UpBAir", "UpBLoop", "UpBLand",
               "CapeStart", "CapeStartAir", "CapeN", "CapeNAir", "CapeF", "CapeFAir", "CapeB", "CapeBAir", "CapeEnd", "CapeEndAir"]
SI = {n: i for i, n in enumerate(STATE_ORDER)}
V2 = bool(knobs["geno_v2"]) and bool(knobs["geno_v1"])
MS_FALLSPECIAL, MS_ATTACK12, MS_ATTACK13 = 35, 45, 46
MS_FALL = 29
V_LEDGE, V_HIDDEN, V_MOTION_GRAVITY = 0x30, 0x31, 0x34   # Geno v3 engine values (geno_v2_encodings.md section 7)
BODYCOLL = lambda st: [(26 << 26) | st]

def term_counters(s):
    f = 0; t = set()
    for e in s["channels_raw"]["main"]:
        n = e.get("name"); a = e.get("args")
        if n == "Synchronous Timer": f += a[0]
        elif n == "Asynchronous Timer": f = max(f, a[0])
        elif n == "Terminate Collisions": t.add(int(f))
    return t

def host_templates(row):
    src = int(MROWS[row]["script"], 16) if MROWS[row]["script"] else None
    if src is None: return []
    flat, static, reason = MD.flatten(src)
    sets = collections.OrderedDict()
    for f, ev in flat:
        if ev["name"] == "Hitbox": sets.setdefault(f, []).append(ev["hitbox"])
    return list(sets.values())

def mk_windows(hexid, offset=0, until=None, rehit=None, clip_from=None, clip_to=None, angle_fix=None):
    """Brawl hitboxes -> [{slot, start, end, h, new_hit, win}] (counters + offset). until: end for hitboxes with none.
    rehit: re-create every N frames. clip_from/clip_to: only that part of the Brawl timeline (before offset)."""
    s = SUB(hexid); term = term_counters(s); log = []
    hbs = [h for h in s["hitboxes"] if h["kind"] in ("hitbox", "special_hitbox")]
    groups = collections.OrderedDict()
    for h in hbs: groups.setdefault(h["start"], []).append(h)
    out = []
    for wi, (st, grp) in enumerate(groups.items()):
        grp = sorted(grp, key=lambda h: h["id"])
        if len(grp) > 4:
            drop = sorted(grp, key=lambda h: h["size"])[:len(grp) - 4]
            log.append(f"Brawl window @{st:g} has {len(grp)} hitboxes; Melee has 4 slots -> dropped the smallest: " + ", ".join(f"id{h['id']} size {h['size']}" for h in drop))
            grp = [h for h in grp if h not in drop]
        for j, h in enumerate(grp):
            h = dict(h); a0 = h["start"]; e0 = h["end"]
            if clip_from is not None and (e0 is not None and e0 <= clip_from): continue
            if clip_to is not None and a0 >= clip_to: continue
            if clip_from is not None and a0 < clip_from: a0 = clip_from
            if clip_to is not None and (e0 is None or e0 > clip_to): e0 = clip_to
            base = -(clip_from or 0) + offset
            if angle_fix and h["angle"] in angle_fix:
                log.append(f"id{h['id']} angle {h['angle']} (autolink) -> {angle_fix[h['angle']]} in the Pl file; the Geno overlay adds LINK")
                h["angle"] = angle_fix[h["angle"]]; h["autolink"] = True
            start = int(a0) + base; end = None if e0 is None else int(e0) + base
            if end is None and until is not None: end = until
            rr = rehit or (h.get("rehit_rate") or 0)
            new_hit = int(h["start"]) in term
            if rr and end is not None and end - start > rr:
                k = 0; c = start
                while c < end:
                    out.append({"slot": j, "start": c, "end": min(c + rr, end), "h": h, "new_hit": k > 0 or new_hit, "win": wi + 1, "rehit": rr})
                    c += rr; k += 1
            else:
                out.append({"slot": j, "start": start, "end": end, "h": h, "new_hit": new_hit, "win": wi + 1})
    return out, log

def mk_body(hexid, offset=0, clip_from=None, clip_to=None):
    """Brawl Body Collision (0 normal, 1 invincible, 2+ intangible) and Visibility -> BodyCollState / FighterVis."""
    s = SUB(hexid); out = []
    for ch in ("main", "other"):
        f = 0
        for e in s["channels_raw"][ch]:
            n = e.get("name"); a = e.get("args")
            if n == "Synchronous Timer": f += a[0]; continue
            if n == "Asynchronous Timer": f = max(f, a[0]); continue
            if clip_from is not None and f < clip_from: continue
            if clip_to is not None and f >= clip_to: continue
            c = int(f) - (clip_from or 0) + offset
            if n == "Body Collision":
                st = a[0] if isinstance(a, list) else a.get("State")
                out.append((c, [(26 << 26) | min(int(st), 2)], f"BodyCollState {min(int(st), 2)} (Brawl Body Collision {st})"))
            elif n == "Visibility":
                vis = a[0] if isinstance(a, list) else True
                out.append((c, [(37 << 26) | (0 if vis else 1)], f"FighterVis {'shown' if vis else 'hidden'} (Brawl Visibility)"))
    return out

placed = []                  # (rows, words, looping)
TUNED_IASA = {}

def host_events(row, keep, frame_offset=0, first_hit=None, clip=None, mode="shift"):
    """Kirby's own events of the host row, filtered, retimed onto the MK clip and remapped to MK joints.
    mode shift: events from 2 frames before Kirby's first hitbox move with the hit (+ MK first hit - Kirby first hit);
    SmashCharge goes to the MK charge frame (frame_offset). mode scale: counters scaled by clip / Kirby clip.
    Kirby-bank sounds (id >= 10000: voice / Kirby SFX) and ModelVis (MK's come from vis_events) are dropped."""
    r = MROWS[row]
    if not r["script"]: return [], []
    flat, static, reason = MD.flatten(int(r["script"], 16))
    if not (static or reason == "goto loop"): return [], []
    mh = [f for f, ev in flat if ev["name"] == "Hitbox"]; m0 = min(mh) if mh else None
    d = (first_hit - m0) if (first_hit is not None and m0 is not None) else 0
    kan = r["anim_frames"] or 1
    out = []; moved = []
    for f, ev in flat:
        n = ev["name"]
        if n in HB_OPS or n in FLOW or n in ("ModelVis", "RandomSmashSFX"): continue
        if n == "SFX" and ev["args"]["sfx_id"] >= 10000: continue
        if not keep(ev): continue
        nf = f
        if n == "SmashCharge": nf = frame_offset
        elif mode == "scale": nf = int(round(f * (clip or kan) / kan))
        elif m0 is not None and f >= m0 - 2 and d: nf = f + d
        if clip and nf >= clip: nf = clip - 1
        if nf < 0: nf = 0
        if nf != f: moved.append(f"{n}@{f}->{nf}")
        out.append((nf, remap_host_words([int(x, 16) for x in ev["raw"]["words"]]), n))
    return out, moved

def emit(key, rows, windows, *, extra=(), host=(), iasa=None, iasa_how=None, looping=False, loop_len=None, end_at=None,
         catch=False, log=(), brawl=None, note=None, geno_extra=None, geno_hit=None, dry=False, record=True, tmpl_row=None):
    """Assemble a Melee script. windows: mk_windows output; extra: [(counter, words, label)] MK-side commands (before the
    hitboxes of that frame); host: host_events output. geno_extra: v1 escapes [(counter, words, label)] -> a geno.json
    overlay variant of the same script (only for non-looping scripts); geno_hit(rec) -> escape words after a hitbox."""
    log = list(log)
    anim = clip_frames(rows[0])
    templates = host_templates(rows[0] if tmpl_row is None else tmpl_row)
    creates = collections.defaultdict(list); ends = collections.defaultdict(set); info = []
    for w in sorted(windows, key=lambda w: (w["start"], w["slot"])):
        h = dict(w["h"]); slot = w["slot"]
        t = None
        if templates:
            ms = templates[min(len(templates) - 1, w["win"] - 1)]
            cand = [x for x in ms if x["slot"] == slot] or [ms[min(len(ms) - 1, slot)]]
            t = cand[0]
        k = knobs["hitbox_scale"]
        joint = int(h.get("bone", 0)); offs = [o * k for o in h["offset"]]; h["size"] = round(h["size"] * k, 4)
        if catch:
            tt = t
            words = pack_hitbox(slot, joint, tt["damage"], h["size"], offs, tt["angle"], tt["knockback_growth"], tt["weight_dependent_set_knockback"],
                                tt["base_knockback"], tt["element_raw"], tt["shield_damage"], tt["hit_sfx"]["level"], tt["hit_sfx"]["kind"],
                                tt["targets"]["ground"], tt["targets"]["air"], flags5_of(tt))
            rec = {"slot": slot, "damage": tt["damage"], "angle": tt["angle"], "kbg": tt["knockback_growth"], "wdsk": tt["weight_dependent_set_knockback"],
                   "bkb": tt["base_knockback"], "size": h["size"], "element": "Grounded", "joint": joint, "brawl_bone": h.get("bone_name"),
                   "joint_from": "grab box: Melee catch template (element catch), MK bone/size/offset/timing", "active": [w["start"] + 1, w["end"]]}
        else:
            h2, tr = TT.hitbox(key, w["win"], h, t)
            flags5 = flags5_of(t) if t else 0b10011
            if not h2.get("clang", True): flags5 &= ~0b00011
            snd = h.get("sfx") or ""
            lvl = next((v for kname, v in SFXLVL.items() if snd.startswith(kname)), 1)
            kind = next((v for kname, v in SFXKIND.items() if snd.endswith(kname)), (t["hit_sfx"]["kind"] if t else 1))
            el = ELEM.get(h2["element"], 0)
            gb = 1 if (h.get("special_flags") or {}).get("HittingGrippedCharacter") else 0
            words = pack_hitbox(slot, joint, h2["damage"], h2["size"], offs, h2["angle"], h2["kbg"], h2["wdsk"], h2["bkb"], el,
                                int(h2.get("shield_damage") or 0), lvl, kind, h2.get("ground", True), h2.get("air", True), flags5, grabbed=gb)
            rec = {"slot": slot, "damage": h2["damage"], "angle": h2["angle"], "kbg": h2["kbg"], "wdsk": h2["wdsk"], "bkb": h2["bkb"],
                   "size": h2["size"], "element": h2["element"], "joint": joint, "joint_from": f"Brawl bone {h.get('bone_name')} = MK joint {joint}",
                   "brawl_bone": h.get("bone_name"), "offset": [round(o, 3) for o in offs], "active": [w["start"] + 1, w["end"]],
                   "shield": h2.get("shield_damage"), "hit_sfx": [lvl, kind], "clank": bool(flags5 & 2), "only_hit_grabbed": gb, "tuning": tr}
            if w.get("rehit"): rec["rehit"] = w["rehit"]
            if h.get("autolink"): rec["autolink"] = True
        creates[w["start"]].append((slot, words, rec, w["new_hit"]))
        if w["end"] is not None: ends[w["end"]].add(slot)
    iasa_c = iasa
    if iasa_c is not None and anim and iasa_c >= anim:
        log.append(f"IASA {iasa_c + 1} ({iasa_how}) >= clip length {anim}: dropped (interruptible at clip end)"); iasa_c = None
    if not looping:
        late = sorted({w["start"] for w in windows if w["start"] >= anim})
        if late: log.append(f"MK hitboxes created at counters {late} are past the {anim}-frame clip: never active")
    host_len = end_at if end_at is not None else anim
    def assemble(gx):
        frames = sorted(set([f for f, _, _ in host] + list(creates) + list(ends) + [c for c, _, _ in extra] + [c for c, _, _ in gx]
                            + ([iasa_c] if iasa_c is not None else [])))
        out = []; cur = 0; active = set(); inf = []
        def wait(f):
            out.append(((1 << 26) | (f - cur)) if looping == "sync" else ((2 << 26) | f))
        for f in frames:
            if f > cur: wait(f); cur = f
            e = ends.get(f, set()); cr = creates.get(f, [])
            renew = {s for s, _, _, nh in cr if nh and s in active}
            closing = (e | renew) & active
            if closing:
                if closing == active: out.append(16 << 26); active.clear()
                else:
                    for s in sorted(closing): out.append((15 << 26) | s); active.discard(s)
            for c, words, label in extra:
                if c == f: out += words
            for c, words, label in gx:
                if c == f: out += words
            for ff, words, n in host:
                if ff == f: out += words
            for s, words, rec, nh in cr:
                out += words; active.add(s); inf.append(rec)
                if gx is not NOGX and geno_hit: out += geno_hit(rec)
            if iasa_c is not None and f == iasa_c: out.append(23 << 26)
        if looping == "sync":
            if loop_len and loop_len > cur: wait(loop_len)
            out += [7 << 26, 0]
        elif looping:
            out += [8 << 26, 7 << 26, 0]
        else:
            if host_len > cur: out.append((2 << 26) | host_len)
            out.append(0)
        return out, inf
    out, info = assemble(NOGX)
    if (geno_extra or geno_hit) and not looping and knobs["geno_v1"]:
        gout, _ = assemble(list(geno_extra or []))
        for r in rows: overlays.append({"index": r, "move": key, "words": gout, "escapes": [l for _, _, l in (geno_extra or [])] + (["LINK after autolink hitboxes"] if geno_hit else [])})
    if dry: return out, info
    placed.append((rows, out, looping))
    iasa_rec = None if iasa_c is None else iasa_c + 1
    if record:
        for rr in rows:
            mr = MROWS[rr]; orig = MD.scripts[int(mr["script"], 16)]["timeline"] if mr["script"] else {"hit_windows": []}
            m = {"move": key, "melee_row": rr, "melee_name": mr["name"], "clip": ROWCLIP[rr], "brawl_subaction": brawl,
                 "melee_before": {"windows": [[x["start"], x["end"], x["damage"]] for x in orig["hit_windows"]], "iasa": orig.get("interruptible_from")},
                 "written_hitboxes": info, "written_iasa": iasa_rec, "melee_anim_frames": anim, "tuning": TT.label(key),
                 "tuning_iasa": TUNED_IASA.get(key), "iasa_how": iasa_how, "extra_events": [(c, l) for c, _, l in extra],
                 "host_events": sorted({n for _, _, n in host}), "notes": log + ([note] if note else [])}
            if catch: m["written_catch_boxes"] = m.pop("written_hitboxes")
            changes["moves"].append(m)
    return info, iasa_rec, log
NOGX = []

def iasa_for(key, hexid, offset=0, host_row=None, policy="auto"):
    """IASA through the tuning hook: Brawl Allow Interrupt (MK's clips end the move at Brawl's length by themselves)."""
    melee = (MD.scripts[int(MROWS[host_row]["script"], 16)]["timeline"].get("interruptible_from")
             if host_row is not None and MROWS[host_row]["script"] else None)
    s = SUB(hexid)
    c = int(s["iasa_frame"]) + offset if (policy == "auto" and s.get("iasa_frame") is not None) else None
    how = "brawl Allow Interrupt" if c is not None else "none (clip end)"
    c2, rec = TT.iasa(key, c, melee)
    TUNED_IASA[key] = rec
    return c2, (how if TT.move(key)["iasa"] is None and TT.move(key)["base"] == "brawl" else f"tuned ({rec['how']})")

def verdict(hexid, host_row, windows):
    """The Kirby mapping tool's legend: direct = same window count as the Melee host move, restructure = not."""
    mw = MD.scripts[int(MROWS[host_row]["script"], 16)]["timeline"]["hit_windows"] if MROWS[host_row]["script"] else []
    bw = sorted({w["start"] for w in windows})
    return ("direct", f"{len(bw)} window(s) in both") if len(mw) == len(bw) else ("restructure", f"Brawl {len(bw)} window(s) vs Melee Kirby {len(mw)}")

def cover(key, brawl, rows, status, verdict_, what, approx=(), stub_=()):
    moves_report.append({"move": key, "brawl_subaction": brawl, "melee_rows": [f"{r} {MROWS[r]['name']} ({ROWCLIP.get(r)})" for r in rows],
                         "status": status, "verdict": verdict_, "what": what, "approximated": list(approx), "stubbed": list(stub_)})

def stub(ver, where, brawl_event, need, frame=None):
    stubs.append({"geno": ver, "where": where, "frame": frame, "brawl_event": brawl_event, "needs": need})

V1_DONE = set()          # Brawl event names this build expresses with a v1 overlay (per move)
def unported_events(hexid, where, done=()):
    s = SUB(hexid)
    V1 = {"Change Action": "change-action escape", "Change Action Status": "change-action escape (status transition groups)",
          "Set Air/Ground": "PUT AIR", "Set/Add Momentum": "PUT FWD_VEL / VEL_Y", "Disable Horizontal Gravity": "no v1 value (gravity)",
          "Enable Horizontal Gravity?": "no v1 value (gravity)", "Disallow Vertical Movement": "no v1 value", "Reverse Direction": "PUT FACING 0",
          "Allow/Disallow Ledgegrab": "no v1 value (ledge grab flag)", "Frame Speed Modifier": "no v1 write (anim rate is read-only)"}
    LATER = {"Article Visibility": "cape article: merged into MK's model, shown by ModelVis(0,2) (vis_events)",
             "Sword Glow": "sword trail (m-ex trail data / Geno)", "Terminate Sword Glow": "sword trail",
             "Graphic Effect": "MK effect bank (EfMk) not ported", "External Graphic Effect": "effect bank not ported",
             "Sound Effect": "MK sound bank not extracted (BRSAR)", "Character Specific 17": "MK native"}
    seen = set()
    for ch in ("main", "other", "gfx", "sfx"):
        for e in s["channels_raw"].get(ch, []):
            n = e.get("name")
            if n in done or (n, ch) in seen: continue
            if n in V1: seen.add((n, ch)); stub("v1" if not V1[n].startswith("no v1") else "later", where, n, V1[n], e.get("frame"))
            elif n in LATER and n not in {x[0] for x in seen}: seen.add((n, ch)); stub("later", where, n, LATER[n], e.get("frame"))

def generic(key, host_names, hexid, offset=0, iasa_policy="auto", keep=lambda ev: True, note=None, extra=(), geno_extra=None):
    rows = [MROWS_BY_NAME[n] for n in host_names if MROWS[MROWS_BY_NAME[n]]["script"]]
    wins, log = mk_windows(hexid, offset, angle_fix={365: knobs["autolink_angle"]})
    body = mk_body(hexid, offset)
    k2 = keep if not body else (lambda ev, k=keep: ev["name"] not in ("BodyCollState", "FighterVis") and k(ev))
    first = min([w["start"] for w in wins], default=None)
    host, moved = host_events(rows[0], k2, frame_offset=offset, first_hit=first, clip=clip_frames(rows[0]))
    ic, how = iasa_for(key, hexid, offset, rows[0], iasa_policy)
    info, iasa_rec, log2 = emit(key, rows, wins, extra=list(body) + vis_events(rows[0], hexid) + list(extra), host=host, iasa=ic, iasa_how=how,
                                log=log + ([f"Kirby events retimed onto the MK clip: {', '.join(moved)}"] if moved else []),
                                brawl=f"{hexid} {SUB(hexid)['name']}", note=note, geno_extra=geno_extra)
    v, vwhy = verdict(hexid, rows[0], wins)
    approx = [x for x in log2 if "past the" in x or "dropped the smallest" in x or "autolink" in x]
    cover(key, f"{hexid} {SUB(hexid)['name']}", rows, "approximated" if approx else "translated",
          f"{v}: {vwhy}", f"{len(info)} hitbox events on MK's {clip_frames(rows[0])}-frame clip, IASA {iasa_rec} ({how})", approx)
    unported_events(hexid, key)
    return info

# ================================================================== 3. normals
r11 = MROWS_BY_NAME["Attack11"]
emit("jab", [r11], [], extra=[(2, [(30 << 26) | 1], "RapidJab flag on (x2218_b2) at counter 2: the entry frame runs counters 0-1 and "
                                                      "checkAttack11 clears the flag after it (measured); window 0 -> Attack100Start next frame")]
     + vis_events(r11, "0x4B"), host=[], iasa=None, iasa_how="none", brawl="0x4B Attack100Start (entry)",
     note="MK has no Attack11-13: Attack11 (MK's Attack100Start clip) only arms the rapid jab.")
TUNED_IASA["jab"] = None
cover("jab", "- (no Attack11 in Brawl)", [r11], "translated", "restructure: Melee jab 1 -> rapid-jab entry",
      "Attack11 = rapid-jab entry (RapidJab flag @2, rapid_jab_window 0): every A press starts the rapid jab")
generic("rapid_jab_start", ["Attack100Start"], "0x4B", iasa_policy="none")
rl = MROWS_BY_NAME["Attack100Loop"]
wins, log = mk_windows("0x4C", 0)
host, _ = host_events(rl, lambda ev: ev["name"] == "GFX", clip=clip_frames(rl), mode="scale")
emit("rapid_jab", [rl], wins, extra=[(9, [20 << 26], "loop checkpoint (Brawl RA.Bit[25] @9)"), (19, [20 << 26], "loop checkpoint (Brawl RA.Bit[25] @19)")]
     + vis_events(rl, "0x4C"), host=host, iasa=None, iasa_how="none", looping="anim", log=log, brawl="0x4C Attack100",
     note="loops with MK's Attack100 clip (SetTimerAnim + goto, like Kirby's own); Melee ends it at a checkpoint without an A press/release since the last")
TUNED_IASA["rapid_jab"] = None
cover("rapid_jab", "0x4C Attack100", [rl], "translated", "direct: 5 rehit windows per loop", "MK's 5 windows (2%/1%), checkpoints at MK's RA.Bit[25] frames")
generic("rapid_jab_end", ["Attack100End"], "0x4D")
generic("dash_attack", ["AttackDash"], "0x4E")
# ftilt: 3-hit chain. Hit 1 on the three ftilt rows; hits 2 and 3 on Attack12 / Attack13 (unreachable in plain Melee: MK's
# Attack11 never sets JabCombo), entered by the v1 change action on A inside Brawl's RA.Bit[16] window.
chain2 = [(4, CHG(C_PRESSED, TGT_MOTION(MS_ATTACK12, raw=True), (BTN_ATTACK,)), "CHG PRESSED(A) -> Attack12 motion = ftilt 2 (Brawl RA.Bit[16] @4)")]
generic("ftilt", ["AttackS3Hi", "AttackS3S", "AttackS3Lw"], "0x50", geno_extra=chain2,
        note="all three Melee angles play ftilt 1 (Brawl MK has no angled ftilt); the chain needs the Geno exe (v1 CHG overlay)")
for key, row, hx, nxt in (("ftilt2", MROWS_BY_NAME["Attack12"], "0x51", MS_ATTACK13), ("ftilt3", 48, "0x52", None)):
    wins, log = mk_windows(hx, 0)
    gate = [int(f) for f, n, a_ in SUB(hx)["main_timeline"] if n == "Bit Variable Set"]
    gx = [(gate[0], CHG(C_PRESSED, TGT_MOTION(nxt, raw=True), (BTN_ATTACK,)), f"CHG PRESSED(A) -> Attack13 motion = ftilt 3 (Brawl RA.Bit[16] @{gate[0]})")] if nxt and gate else None
    body = mk_body(hx, 0)
    emit(key, [row], wins, extra=[(0, [(30 << 26) | 0], "RapidJab flag off (the Attack12/13 motions check the rapid jab)")] + body + vis_events(row, hx),
         host=[], iasa=None, iasa_how="none", log=log, brawl=f"{hx} {SUB(hx)['name']}", geno_extra=gx,
         note=f"host motion {'Attack12' if nxt else 'Attack13'} (reached only by the v1 chain); clip {ROWCLIP[row]}")
    TUNED_IASA[key] = None
    cover(key, f"{hx} {SUB(hx)['name']}", [row], "translated (Geno exe)", "unsupported in plain Melee: no ftilt chain state",
          f"{len(wins)} hitboxes on row {row}; reached by v1 CHG PRESSED(A) from the previous hit", ["plain exe: unreachable (ftilt 1 only)"])
generic("utilt", ["AttackHi3"], "0x54")
generic("dtilt", ["AttackLw3"], "0x55")
S4 = int(SUB("0x56")["anim_frames"]); HI4 = int(SUB("0x5C")["anim_frames"]); LW4 = int(SUB("0x5F")["anim_frames"])
generic("fsmash", ["AttackS4Hi", "AttackS4S", "AttackS4Lw"], "0x58", offset=S4,
        note=f"Start ({S4}) + AttackS4S joined in MK's clip; SmashCharge at {S4}. No angled fsmash in Brawl MK.")
generic("usmash", ["AttackHi4"], "0x5D", offset=HI4, note=f"Start ({HI4}) + AttackHi4 joined; SmashCharge at {HI4}")
generic("dsmash", ["AttackLw4"], "0x60", offset=LW4, note=f"Start ({LW4}) + AttackLw4 joined; SmashCharge at {LW4}")
for k_, n_, hx in (("nair", "AttackAirN", "0x62"), ("fair", "AttackAirF", "0x63"), ("bair", "AttackAirB", "0x64"), ("uair", "AttackAirHi", "0x65"), ("dair", "AttackAirLw", "0x66")):
    generic(k_, [n_], hx)
for k_, n_, hx in (("nair_land", "LandingAirN", "0x67"), ("fair_land", "LandingAirF", "0x68"), ("bair_land", "LandingAirB", "0x69"),
                   ("uair_land", "LandingAirHi", "0x6A"), ("dair_land", "LandingAirLw", "0x6B")):
    generic(k_, [n_], hx, iasa_policy="none", note="MK has no landing hitboxes (Kirby's landing hits removed); lag = landingair*_lag attributes")
generic("pummel", ["CatchAttack"], "0x70")
generic("ledge_attack_fast", ["CliffAttackQuick"], "0x0D7")
generic("ledge_attack_slow", ["CliffAttackSlow"], "0x0DC")
generic("getup_attack_up", ["DownAttackU"], "0x0B0")
generic("getup_attack_down", ["DownAttackD"], "0x0B9")
# multi-jump gate: Kirby allows the next air jump at 28 (SetCmdVar 0 = 1, read by ftCo_800D72A0); MK sets RA.Bit[17]/[19] at 24
for i in range(1, 5):
    hx = f"0x{0x1A + i:X}"
    gate = [int(fr) for fr, n, a_ in SUB(hx)["main_timeline"] if n == "Bit Variable Set"][0]
    rows = [MROWS_BY_NAME[f"JumpAerialF{i}"], MROWS_BY_NAME[f"JumpAerialF{i}Met"]]
    host, _ = host_events(rows[0], lambda ev: ev["name"] != "SetCmdVar", clip=clip_frames(rows[0]), mode="scale")
    emit("jumpaerial", rows, [], extra=[(gate, [(19 << 26) | 1], f"multi-jump gate: SetCmdVar 0 = 1 at Brawl's RA.Bit[17]/[19] counter {gate} (Kirby: 28)")]
         + vis_events(rows[0], hx), host=host, iasa=None, iasa_how="none", brawl=f"{hx} {SUB(hx)['name']}", note="next air jump from MK's frame")
TUNED_IASA["jumpaerial"] = None
cover("jumpaerial", "0x1B-0x1E JumpAerialF1-F4", [MROWS_BY_NAME[f"JumpAerialF{i}"] for i in range(1, 5)], "translated",
      "direct: one gate event", "next air jump allowed at MK's counter 24; wings ModelVis; hop impulses in special attrs / geno.json")

def grab(key, name, hexid):
    s = SUB(hexid); row = MROWS_BY_NAME[name]
    tend = [int(f) for f, n, _ in s["main_timeline"] if n == "Terminate Catch Collisions"]
    wins = []
    for j, g in enumerate(sorted(s["grabs"], key=lambda g: g["args"]["ID"])[:4]):
        a = g["args"]; bone = a["Bone"] - 400 if a["Bone"] >= 400 else a["Bone"]
        wins.append({"slot": j, "start": int(g["frame"]), "end": tend[0] if tend else None, "win": 1, "new_hit": False,
                     "h": {"bone": bone, "bone_name": SKEL[bone]["name"], "offset": [a["X offset"], a["Y Offset"], a["Z Offset"]], "size": a["Scale"]}})
    host, moved = host_events(row, lambda ev: True, first_hit=wins[0]["start"], clip=clip_frames(row))
    emit(key, [row], wins, extra=vis_events(row, hexid), host=host, iasa=None, iasa_how="none", catch=True, brawl=f"{hexid} {s['name']}",
         note="grab boxes: Melee Kirby's catch hitboxes (element catch, flags) with MK's bone, timing, size and offset")
    TUNED_IASA[key] = None
    cover(key, f"{hexid} {s['name']}", [row], "translated", "direct: one grab window", f"{len(wins)} catch boxes, active {wins[0]['start']+1}-{wins[0]['end']}")
grab("grab", "Catch", "0x6C"); grab("dash_grab", "CatchDash", "0x6D")
cover("pivot_grab", "0x6E CatchTurn", [], "stubbed-for-v2", "unsupported", "Brawl pivot grab: no Melee motion (Melee turns, then grabs)", stub_=["a Geno state"])

def throw(key, name, hexid):
    s = SUB(hexid); row = MROWS_BY_NAME[name]
    spec = {t["args"]["ID"]: t["args"] for t in s["throws"] if t["name"] == "Throw Specifier"}
    app = [int(t["frame"]) for t in s["throws"] if t["name"] == "Throw Applier"]
    wins, log = mk_windows(hexid, 0)
    body = mk_body(hexid, 0)
    keep = lambda ev: ev["name"] not in ("ThrowFlagB3/B4", "BodyCollState", "FighterVis") and not (ev["name"] == "SetAirState" and name != "ThrowHi")
    host, moved = host_events(row, keep, clip=clip_frames(row), mode="scale")
    extra = body + vis_events(row, hexid) + [(app[0], [20 << 26], f"throw release at Brawl's Throw Applier (counter {app[0]})")]
    ic, how = iasa_for(key, hexid, 0, row)
    info, ia, log2 = emit(key, [row], wins, extra=extra, host=host, iasa=ic, iasa_how=how, log=log, brawl=f"{hexid} {s['name']}",
                          note="MK's throw clip, release at the Throw Applier; Kirby's throw commands scaled to the clip")
    words = placed[-1][1]; o = 0; done = []
    while o < len(words):
        w = words[o]; op = w >> 26
        if op == 34:
            typ = (w >> 23) & 7; a = spec.get(typ)
            if a:
                w1, w2 = words[o + 1], words[o + 2]
                before = {"damage": w & 0x7FFFFF, "angle": w1 >> 23, "kbg": (w1 >> 14) & 0x1FF, "wdsk": (w1 >> 5) & 0x1FF, "bkb": w2 >> 23}
                a2, trec = TT.throw(key, a, before)
                words[o] = (w & ~0x7FFFFF) | a2["Damage"]
                words[o + 1] = (a2["Trajectory"] << 23) | (a2["Knockback Growth"] << 14) | (a2["Weight Knockback"] << 5) | (w1 & 0x1F)
                words[o + 2] = (a2["Base Knockback"] << 23) | (w2 & 0x7FFFFF)
                done.append({"type": "throw" if typ == 0 else "release", "melee_before": before,
                             "written": {"damage": a2["Damage"], "angle": a2["Trajectory"], "kbg": a2["Knockback Growth"], "wdsk": a2["Weight Knockback"], "bkb": a2["Base Knockback"]},
                             "tuning": trec})
        if op in (5, 7): o += 2; continue
        if op == 0: break
        o += MD.LEN[op]
    changes["moves"][-1]["throw_hitboxes"] = done
    cover(key, f"{hexid} {s['name']}", [row], "translated", "direct: ThrowHitbox values map 1:1 (Throw Specifier)",
          f"throw {done[0]['written'] if done else '?'}, release @{app[0]}, {len(info)} MK hitboxes", ["Kirby's throw code (victim attach) on MK's clip"])
    unported_events(hexid, key)
for k_, n_, hx in (("throwf", "ThrowF", "0x73"), ("throwb", "ThrowB", "0x72"), ("throwhi", "ThrowHi", "0x74"), ("throwlw", "ThrowLw", "0x75")):
    throw(k_, n_, hx)

# ================================================================== 4. specials on Kirby's special rows + code
KEEP_NONE = lambda ev: False
# --- Neutral B: Mach Tornado on inhale (hitboxes are Slash, not Catch: nothing is swallowed)
for row, hx in ((MROWS_BY_NAME["SpecialN"], "0x1CE"), (MROWS_BY_NAME["SpecialAirN"], "0x1CF")):
    host, _ = host_events(row, lambda ev: ev["name"] == "SetCmdVar", clip=clip_frames(row), mode="scale")
    emit("tornado_start", [row], [], extra=vis_events(row, hx), host=host, iasa=None, iasa_how="none", brawl=f"{hx} {SUB(hx)['name']}",
         note="inhale start: Kirby's catch box / ThrowHitbox / GFX dropped; SetCmdVar kept (inhale state machine)")
TUNED_IASA["tornado_start"] = None
cover("tornado_start", "0x1CE/0x1CF SpecialNStart", [MROWS_BY_NAME["SpecialN"], MROWS_BY_NAME["SpecialAirN"]], "translated",
      "direct: no hitbox in either", "MK start clip; Kirby's inhale code runs it")
rt = [MROWS_BY_NAME["SpecialNLoop"], MROWS_BY_NAME["SpecialAirNLoop"]]
wins, log = mk_windows("0x1D0", 0, until=knobs["tornado_rehit"])
for w in wins: w["new_hit"] = True
emit("tornado", rt, wins, extra=vis_events(rt[0], "0x1D0"), host=[], iasa=None, iasa_how="none", looping="sync", loop_len=knobs["tornado_rehit"],
     log=log + [f"rehit every {knobs['tornado_rehit']} frames (paramSpecialN[11] = 10, param id 24000 read by the native execStatus; inferred)"],
     brawl="0x1D0 SpecialNSpin", note="loops while B is held (Kirby's inhale loop code); 4 x 1% set-knockback hitboxes re-created every loop")
TUNED_IASA["tornado"] = None
cover("tornado", "0x1D0 SpecialNSpin", rt, "approximated", "unsupported: native tornado physics (sora_melee execStatus)",
      f"4 hitboxes x 1% rehit every {knobs['tornado_rehit']} frames while B held (MK spin clip, 361 frames)",
      ["placeholder physics: Kirby's inhale loop (stands still, no rise/drift, no tap-to-rise); lasts while B is held"],
      ["Phase 4: tornado phys/input callbacks (tap to rise, params 4012-4015)"])
stub("v2", "tornado", "ftMetaknightStatusUniqProcessSpecialNSpin::execStatus", "native physics callback (rise on B taps, drift, fixed duration)", None)
rn = [MROWS_BY_NAME["SpecialNEnd"]]
wins, log = mk_windows("0x1D1", 0)
emit("tornado_end", rn, wins, extra=vis_events(rn[0], "0x1D1"), host=[], iasa=None, iasa_how="none", log=log, brawl="0x1D1 SpecialNEnd",
     note="Kirby's SpecialNEnd row also serves the air end (no own row)")
TUNED_IASA["tornado_end"] = None
cover("tornado_end", "0x1D1 SpecialNEnd (+0x1D2 air)", rn, "translated", "direct", "3% finisher 0-3", ["air end shares the ground row and clip"])

# --- Side B: Drill Rush on the hammer rows, MK's drill clip (45): drill rehit from 4, End hitboxes in the last frames
for key, name, endhx in (("drill_rush", "SpecialS", "0x1D6"), ("drill_rush_air", "SpecialAirS", "0x1D7")):
    row = MROWS_BY_NAME[name]; cl = clip_frames(row)
    end_len = max(int(h["end"]) for h in SUB(endhx)["hitboxes"]) + 1
    end_at = cl - end_len - 1
    rr = knobs["drill_rehit"] or 6
    w1, l1 = mk_windows("0x1D5", 0, until=end_at, rehit=rr, angle_fix={365: knobs["autolink_angle"]})
    w2, l2 = mk_windows(endhx, end_at)
    for w in w2: w["win"] += max(x["win"] for x in w1); w["new_hit"] = True
    gx = []
    if key == "drill_rush_air" and not V2:     # Brawl SpecialAirSEnd: Set/Add Momentum (H -1, V 2.1) on its first frame
        gx = [(end_at, PUT(V_FWD_VEL, -1.0) + PUT(V_VEL_Y, 2.1), "PUT FWD_VEL -1, VEL_Y 2.1 (Brawl Set/Add Momentum on SpecialAirSEnd)")]
    link_done = set()
    def link_hit(rec, _d=link_done):
        if V2: return []            # the Geno exe runs Drill Rush as Geno states (4b); rows 322/323 are the main exe's fallback
        if rec.get("autolink") and rec["slot"] not in _d:
            _d.add(rec["slot"]); return LINK(1 << rec["slot"], 1)
        return []
    emit(key, [row], w1 + w2, extra=vis_events(row, "0x1D5"), host=[], iasa=None, iasa_how="none", log=l1 + l2,
         brawl=f"0x1D5 SpecialSDrill + {endhx} {SUB(endhx)['name']}", geno_extra=gx or None, geno_hit=None if V2 else link_hit,
         note=f"drill clip ({cl}); drill hits from counter 4, rehit {rr}, until {end_at}; End hitboxes at {end_at}; hammer item never spawned")
    TUNED_IASA[key] = None
    cover(key, f"0x1D5/{endhx}", [row], "approximated", "unsupported: native drill steering (SpecialSRush::execStatus)",
          f"drill 3 hitboxes rehit {rr} from frame 5, end hit at {end_at + 1}; Geno exe: LINK (autolink 365)" + (", end momentum" if gx else ""),
          [f"no 22-frame start (the row plays the drill clip; SpecialSStart is unused)", f"Pl file: autolink 365 -> fixed {knobs['autolink_angle']}",
           "placeholder physics: Kirby's hammer code (ground: in place; air: 1.5 hop, fall-special landing)"],
          ["Phase 4: steering/bounce phys (param 4020), start phase"])
unported_events("0x1D5", "drill_rush"); unported_events("0x1D7", "drill_rush_air", done={"Set/Add Momentum"})

# --- Up B: Shuttle Loop on Final Cutter: Hi1 / AirHi1 = SpecialHi, Hi2 / AirHi2 = SpecialHiLoop (+ v1: -> FallSpecial at its end)
for key, rows_, hx in (("shuttle_loop_rise", ["SpecialHi1", "SpecialAirHi1"], "0x1E2"), ("shuttle_loop_loop", ["SpecialHi2", "SpecialAirHi2"], "0x1E4")):
    rows = [MROWS_BY_NAME[n] for n in rows_]
    wins, log = mk_windows(hx, 0, until=clip_frames(rows[0]))
    body = mk_body(hx, 0)
    keep = lambda ev: ev["name"] in ("ftCommon_8007F5CC", "SetAirState") or (ev["name"] == "SetCmdVar" and ev["args"]["var"] == 3)
    host, _ = host_events(rows[0], keep, clip=clip_frames(rows[0]), mode="scale")
    gx = None
    if key == "shuttle_loop_loop":
        gx = [(0, CHG(C_ANIM_END, TGT_MOTION(MS_FALLSPECIAL)), "CHG ANIM_END -> FallSpecial (Brawl: Glide / FallSpecial at the loop end)")]
        if V2:      # the Geno exe binds specials.hi / air_hi to the UpB states (4c): these Kirby rows are the main exe's fallback only
            gx = None
    emit(key, rows, wins, extra=body + vis_events(rows[0], hx), host=host, iasa=None, iasa_how="none", log=log, brawl=f"{hx} {SUB(hx)['name']}", geno_extra=gx,
         note=("Kirby's Final Cutter code: rise -> loop row; " + ("plain exe: then Kirby's plunge; Geno exe: FallSpecial" if gx else "MK SpecialHi clip for ground and air")))
    TUNED_IASA[key] = None
    cover(key, f"{hx} {SUB(hx)['name']}", rows, "approximated", "restructure: Brawl subactions -> Kirby Hi1/Hi2 rows",
          f"{len(wins)} hitbox events on MK's clip" + ("; Geno exe: FallSpecial at the loop end" if gx else ""),
          ["path/physics = Kirby's Final Cutter code (rise, then the plunge on the plain exe), not MK's loop"],
          ["v2 glide hand-off at the loop end"] + (["v1 Allow/Disallow Ledgegrab (no v1 value)"] if gx else []))
unported_events("0x1E2", "shuttle_loop_rise"); unported_events("0x1E4", "shuttle_loop_loop", done={"Change Action"})
for key, rows_ in (("shuttle_loop_fall", ["SpecialHi3", "SpecialAirHi3"]), ("shuttle_loop_land", ["SpecialHi4", "SpecialAirHiEnd"])):
    rows = [MROWS_BY_NAME[n] for n in rows_]
    host, _ = host_events(rows[0], lambda ev: ev["name"] == "ftCommon_8007F5CC", clip=clip_frames(rows[0]), mode="scale")
    emit(key, rows, [], extra=vis_events(rows[0], "0x1E5"), host=host, iasa=None, iasa_how="none", brawl="0x1E5 SpecialHiEnd",
         note="no hitbox, no cutter wave (SetCmdVar 2 dropped)")
    TUNED_IASA[key] = None
    cover(key, "0x1E5 SpecialHiEnd", rows, "approximated", "unsupported: Brawl ends in Glide or FallSpecial",
          "plain exe: Kirby's straight-down plunge / landing (MK SpecialHiEnd clip)", ["plunge instead of FallSpecial on the plain exe"], ["v2 glide"])
stub("v2", "shuttle_loop_loop", "Change Action 133 (Glide) on Animation End + In Air (actions 0x114 / 0x11D)", "Geno glide state; v1 overlay sends it to FallSpecial", 31)

# --- Down B: Dimensional Cape on Stone: start -> vanish (hold) -> reappear attack (end row, SpecialLw clip) -> FallSpecial
for row, hx in ((MROWS_BY_NAME["SpecialLw1"], "0x1D8"), (MROWS_BY_NAME["SpecialAirLwStart"], "0x1D9")):
    emit("cape_start", [row], [], extra=mk_body(hx, 0) + vis_events(row, hx), host=[], iasa=None, iasa_how="none", brawl=f"{hx} {SUB(hx)['name']}",
         note="no stone transform (SetCmdVar 0 dropped): cape article shown, intangible @17, hidden @12 (MK frames)")
    unported_events(hx, "cape_start")
TUNED_IASA["cape_start"] = None
cover("cape_start", "0x1D8/0x1D9 SpecialLwStart", [MROWS_BY_NAME["SpecialLw1"], MROWS_BY_NAME["SpecialAirLwStart"]], "translated",
      "direct: no hitbox", "cape article (ModelVis 0,2), intangible @17, hidden @12", [], ["v1 Set Air/Ground @12 (not needed on Kirby's stone code)"])
rows = [MROWS_BY_NAME["SpecialLw"], MROWS_BY_NAME["SpecialAirLw"]]
emit("cape_vanish", rows, [], extra=[(0, [(26 << 26) | 2], "BodyCollState intangible"), (0, [(37 << 26) | 1], "FighterVis hidden")],
     host=[], iasa=None, iasa_how="none", brawl="(vanished: between SpecialLwStart and SpecialLw)",
     note="Kirby's stone hold (anim rate 0) as the vanish: intangible + hidden, speciallw_max/min_time_in_stone frames; Kirby's 18% stone-drop hitbox removed")
TUNED_IASA["cape_vanish"] = None
cover("cape_vanish", "(vanish)", rows, "approximated", "unsupported: host = Kirby stone hold",
      "intangible + invisible for speciallw_max_time_in_stone frames; air sink speciallw_gravity", ["no stick-steered teleport (Brawl moves MK N/F/B)"],
      ["Phase 4: teleport distance/direction from the stick (v1 has the stick values, not a position write)"])
for row, hx in ((MROWS_BY_NAME["SpecialLwEnd"], "0x1DA"), (MROWS_BY_NAME["SpecialAirLwEnd"], "0x1DB")):
    wins, log = mk_windows(hx, 0)
    emit("cape_attack", [row], wins, extra=mk_body(hx, 0) + vis_events(row, hx), host=[], iasa=None, iasa_how="none", log=log,
         brawl=f"{hx} {SUB(hx)['name']} (neutral)", geno_extra=[(1, PUT(V_FACING, 0.0), "PUT FACING 0 (Brawl Reverse Direction @1)")],
         note="reappear attack 14% on MK's neutral clip (hits behind MK's facing, as the clip swings); Geno exe turns MK around first, "
              "as Brawl does; then FallSpecial (speciallw_freefall_toggle = landing lag)")
    unported_events(hx, "cape_attack", done={"Reverse Direction"})
TUNED_IASA["cape_attack"] = None
cover("cape_attack", "0x1DA/0x1DB SpecialLw (neutral)", [MROWS_BY_NAME["SpecialLwEnd"], MROWS_BY_NAME["SpecialAirLwEnd"]], "approximated",
      "direct: one 2-hitbox window", "14% f6-7 on MK's clip; Geno exe: Reverse Direction @1; then FallSpecial",
      ["F/B variants (stick) not chosen: neutral only", "plain exe: MK does not turn around (the hit lands behind him, matching the clip)",
       "ground reappear also ends in FallSpecial -> LandingFallSpecial"],
      ["v1 CHG to F/B variants needs host rows for SpecialLwF/B (extras exist, no free Kirby row wired)"])
cover("glide_attack", "0x3C GlideAttack", [], "stubbed-for-v2", "unsupported: glide is a Geno v2 state", "12% f5-7 once the glide states exist", stub_=["Geno v2 action states"])
cover("final_smash", "0x1E6.. Final*", [], "not ported", "Brawl global mechanic", "no Smash Ball in Melee")
cover("trip_attack", "0xE7 SlipAttack", [], "not ported", "Brawl global mechanic", "tripping")

# ================================================================== 4b. Geno v2 rows (MK's extra clips on Kirby copy-ability rows)
# Plain ftcmd scripts (hitboxes, ModelVis, BodyColl) for the rows the Geno v2 states play; the escapes (LINK, the ground
# variant switch) go into overlays of the same rows. The main exe never enters these rows.
def v2row(state, key, hexid=None, wins=(), log=(), extra=(), geno_extra=None, geno_hit=None, tmpl=None, note=""):
    row, clip = V2ROWS[state]
    ex = vis_events(row, hexid) + list(extra)
    if hexid: ex += mk_body(hexid, 0)
    info, _, log2 = emit(key, [row], list(wins), extra=ex, host=[], iasa=None, iasa_how="none", log=list(log),
                         brawl=f"{hexid} {SUB(hexid)['name']}" if hexid else f"({clip})", geno_extra=geno_extra, geno_hit=geno_hit,
                         tmpl_row=tmpl, note=f"Geno v2 state {state} (row {row}, a Kirby copy-ability row; clip {clip}). " + note)
    return info
CLOSE_CAPE = lambda row, why: [(clip_frames(row) - 1, [MV(0, 0)], f"ModelVis(0,0) closed cape at the last frame ({why})")]
for st_, hx in (("GlideStart", "0x39"), ("Glide", "0x3A"), ("GlideLanding", "0x3E"), ("GlideEnd", "0x3D")):
    v2row(st_, "glide", hx, note="no hitbox; the behaviour moves MK")
TUNED_IASA["glide"] = None
wins, log = mk_windows("0x3C", 0)
v2row("GlideAttack", "glide_attack", "0x3C", wins, log, extra=CLOSE_CAPE(V2ROWS["GlideAttack"][0], "GlideAttack goes to Fall, which has no ModelVis"),
      tmpl=MROWS_BY_NAME["AttackAirN"], note="12% f5-7 (3 boxes on TopN); Kirby's nair hitbox flags as the template")
TUNED_IASA["glide_attack"] = None
cover("glide_attack", "0x3C GlideAttack", [V2ROWS["GlideAttack"][0]], "translated (Geno exe)", "unsupported in plain Melee: Geno v2 state",
      f"{len(wins)} hitboxes on MK's GlideAttack clip; entered from the glide on A (geno.glide)")
cover("glide", "0x39-0x3E Glide*", [V2ROWS[n][0] for n in ("GlideStart", "Glide", "GlideLanding", "GlideEnd")], "translated (Geno exe)",
      "unsupported in plain Melee: Geno v2 states", "GlideStart / Glide (posed by angle, pose_center 90) / GlideLanding / GlideEnd rows")
v2row("DrillStart", "drill_start", "0x1D3", note="no hitbox (Brawl SpecialSStart)")
v2row("DrillStartAir", "drill_start", "0x1D4", note="no hitbox (Brawl SpecialAirSStart)")
TUNED_IASA["drill_start"] = None
rr = knobs["drill_rehit"] or 6
drow = V2ROWS["Drill"][0]
w1, l1 = mk_windows("0x1D5", 0, until=clip_frames(drow), rehit=rr, angle_fix={365: knobs["autolink_angle"]})
ndw = max(x["win"] for x in w1)
v2link = set()
def v2_link_hit(rec, _d=v2link):
    if rec.get("autolink") and rec["slot"] not in _d:
        _d.add(rec["slot"]); return LINK(1 << rec["slot"], 1)
    return []
v2row("Drill", "drill_rush", "0x1D5", w1, l1, geno_hit=v2_link_hit, tmpl=MROWS_BY_NAME["SpecialS"],
      geno_extra=[(20, PUT(V_LEDGE, 1, is_float=False), "PUT LEDGE 1 (Brawl Allow/Disallow Ledgegrab 1 @20)")],
      note=f"drill hits from counter 4, re-created every {rr} (Brawl rehit), to the clip end; row flag 0x80000000: the clip's TransN "
           "is the rush speed (geno.drill reads fp->x6A4_transNOffset); overlay adds LINK (Brawl 365)")
TUNED_IASA["drill_rush"] = None
for st_, hx, key, air in (("DrillEnd", "0x1D7", "drill_rush_air", True), ("DrillEndGround", "0x1D6", "drill_rush", False)):
    w2, l2 = mk_windows(hx, 0)
    for w in w2: w["win"] += ndw; w["new_hit"] = True
    v2row(st_, key, hx, w2, l2, tmpl=MROWS_BY_NAME["SpecialAirS" if air else "SpecialS"],
          note="end hits; the engine picks the ground / air end by the situation at the rush's end (Brawl SpecialSEnd If On Ground); "
               + ("air: Brawl's Set Momentum (-1, +2.1), FallSpecial at the end, LandingFallSpecial on landing, ledge grab (both)"
                  if air else "ground: Wait at the end, off an edge -> Fall"))
cover("drill_rush_v2", "0x1D3-0x1D7 SpecialS*", [V2ROWS[n][0] for n in ("DrillStart", "DrillStartAir", "Drill", "DrillEnd", "DrillEndGround")],
      "translated (Geno exe)", "native steering: geno.drill.start / geno.drill / geno.drill.end",
      "22-frame start, the rush steered by the stick at the clip's TransN speed (LINK = 365), end hits; plain exe: rows 322/323 (Kirby's hammer code)")
w2, l2 = mk_windows("0x1D2", 0)
v2row("TornadoEnd", "tornado_end", "0x1D2", w2, l2, tmpl=MROWS_BY_NAME["SpecialNEnd"],
      geno_extra=[(0, CHGV(C_GROUND, TGT_GENO(SI["TornadoEndGround"], keep_frame=True), once=True), "CHG GROUND ONCE -> GENO(TornadoEndGround) KEEP_FRAME (row 307)")],
      note="the air finisher 3% f1-2")
cover("tornado_v2", "0x1D0-0x1D2 SpecialN*", [306, V2ROWS["TornadoEnd"][0], 307], "translated (Geno exe)", "native physics: geno.tornado",
      "spin on row 306 (4 x 1% re-created every 10), rise on B taps, drift; ends when the spin rate runs down -> TornadoEnd (air row) / row 307")
for st_, hx in (("AppealHi", "0x1BC"), ("AppealS", "0x1BE")):
    v2row(st_, "taunt", hx, note="entered from the Melee taunt with the stick held up / sideways (geno.json overlay on rows 239/240)")
TUNED_IASA["taunt"] = None
v2row("Wait3", "wait3", "0x2", extra=CLOSE_CAPE(V2ROWS["Wait3"][0], "the idle ends in Wait"),
      note="Brawl's second idle: entered from Wait at the end of a Wait1 cycle, 1 in wait3_chance (game RNG, rollback-safe)")
TUNED_IASA["wait3"] = None
# ================================================================== 4c. Geno v3: Shuttle Loop as root-motion states (no Kirby code)
# Brawl (IR actions 0x114 / 0x11D / 0x11E, PSA): ground SpecialHi (32f: rise + loop in one clip; Set Air/Ground @5, ledge grab
# allowed @7, anim end + in air -> Glide); air SpecialAirHiStart (8f, no hitbox) -> SpecialHiLoop (31f; ledge @7; anim end + in air
# -> Glide, else Fall); landing -> SpecialHiEnd (32f, no interrupt) -> Wait. No MK code: the path is the clips' TransN.
upb_log = []
def upb(state, key, hx, geno_extra=None, tmpl=None, note=""):
    row = V2ROWS[state][0]; cl = clip_frames(row)
    wins, log = mk_windows(hx, 0, until=cl) if SUB(hx)["hitboxes"] else ([], [])
    info = v2row(state, key, hx, wins, log, geno_extra=geno_extra, tmpl=tmpl, note=note)
    upb_log.append((state, row, ROWCLIP[row], len(info)))
    return info
to_glide = lambda c: [(c, CHG(C_ANIM_END, TGT_GENO(SI["Glide"])) + CHGAND(C_AIR), "CHG ANIM_END & AIR -> GENO(Glide) (Brawl Change Action 0x85)"),
                      (c, CHG(C_ANIM_END, TGT_MOTION(MS_FALL)), "CHG ANIM_END -> Fall (Brawl Change Action 0xE on the ground)")]
ledge7 = [(7, PUT(V_LEDGE, 2, is_float=False), "PUT LEDGE 2 (Brawl Allow/Disallow Ledgegrab 2 @7)")]
if V2:
    upb("UpB", "shuttle_loop_rise", "0x1E2", tmpl=MROWS_BY_NAME["SpecialHi1"],
        geno_extra=to_glide(0) + ledge7,
        note="ground Shuttle Loop: rise + loop in one clip, moved by its TransN (geno.anim_motion, origin); intangible 4-8")
    upb("UpBAir", "shuttle_loop_rise", "0x1E3", note="air start: 8 frames, no hitbox, holds still (the clip has no root motion)")
    upb("UpBLoop", "shuttle_loop_loop", "0x1E4", tmpl=MROWS_BY_NAME["SpecialHi2"], geno_extra=to_glide(0) + ledge7,
        note="air loop, moved by its TransN (origin: the clip starts one frame into the rise)")
    upb("UpBLand", "shuttle_loop_land", "0x1E5", note="landing out of the loop: 32 frames (Brawl SpecialHiEnd has no interrupt), then Wait")
    cover("shuttle_loop_v3", "0x1E2-0x1E5 SpecialHi*", [V2ROWS[n][0] for n in ("UpB", "UpBAir", "UpBLoop", "UpBLand")], "translated (Geno exe)",
          "Geno v3 states: geno.anim_motion (no Kirby Up-B code)",
          "ground: SpecialHi (rise+loop, TransN) -> Glide in the air; air: SpecialAirHiStart -> SpecialHiLoop -> Glide (helpless after); "
          "landing -> SpecialHiEnd (32f); ledge grab from frame 7 (front and back); plain exe: Kirby's Final Cutter rows 324-331")
    changes["gfx_hooks"] = {"_note": "Brawl effect events of the Geno rows, for the effects pass (not emitted by this build)",
                            "UpB": {"row": V2ROWS["UpB"][0], "brawl": "0x1E2 SpecialHi gfx", "events": [
                                [6, "Graphic Effect 40 (sword)"], [6, "Sword Glow (RHaveN, len 40) to 20"], [7, "Meta Knight ef 24"],
                                [8, "Common ef 17 at (0,0,20) rot 15"]]},
                            "UpBAir": {"row": V2ROWS["UpBAir"][0], "brawl": "0x1E3 gfx", "events": [[6, "Common ef 40"]]},
                            "UpBLoop": {"row": V2ROWS["UpBLoop"][0], "brawl": "0x1E4 gfx", "events": [
                                [0, "Sword Glow to 29"], [1, "Meta Knight ef 24"], [1, "Common ef 17 at (0,0,20) rot 18"]]}}
# ================================================================== 4d. Geno v3: Dimensional Cape (no Kirby stone code)
# Brawl (IR actions 0x115 / 0x11B / 0x11C, subactions 472-481; MK kinetic 0x69 / 0x6A): start (20f clip, script to 26) keeps half
# the momentum, vanishes at 12 (steered by the stick), intangible from 17; at 26 B or A held -> the slash reappear (N / "F" / "B" by
# the stick x vs facing), else the plain reappear. Reappears: 56f (slash f5-6, 14%), visible and tangible from f1 (N and B turn
# around at f1); plain end 36f (ledge grab, ground IASA 28). Ground -> Wait, air -> FallSpecial.
if V2:
    hide12 = [(12, PUT(V_HIDDEN, 1, is_float=False), "PUT HIDDEN 1 (Brawl Visibility off @12, kept across the Geno states)")]
    for st_, hx in (("CapeStart", "0x1D8"), ("CapeStartAir", "0x1D9")):
        v2row(st_, "cape_start", hx, geno_extra=hide12, note="start + vanish (geno.cape): hidden @12, intangible @17, decision @26")
    TUNED_IASA["cape_start"] = None
    for st_, hx, turn in (("CapeN", "0x1DA", True), ("CapeNAir", "0x1DB", True), ("CapeF", "0x1DC", False), ("CapeFAir", "0x1DD", False),
                          ("CapeB", "0x1DE", True), ("CapeBAir", "0x1DF", True)):
        row = V2ROWS[st_][0]
        wins, log = mk_windows(hx, 0)
        gx = [(1, PUT(V_HIDDEN, 0, is_float=False), "PUT HIDDEN 0 (Brawl Visibility on @1)")]
        if turn: gx.append((1, PUT(V_FACING, 0.0), "PUT FACING 0 (Brawl Reverse Direction @1)"))
        v2row(st_, "cape_attack", hx, wins, log, geno_extra=gx, tmpl=MROWS_BY_NAME["SpecialLwEnd"],
              extra=[(0, BODYCOLL(2), "BodyCollState intangible @0 (the vanish's intangibility lasts to f1)")] + CLOSE_CAPE(row, "ends in Wait / FallSpecial"),
              note=f"slash reappear ({'turns around @1, ' if turn else ''}root motion in the entry facing): 14% f6-7; visible and tangible @1")
    for st_, hx, air in (("CapeEnd", "0x1E0", False), ("CapeEndAir", "0x1E1", True)):
        row = V2ROWS[st_][0]
        gx = [(0, PUT(V_HIDDEN, 0, is_float=False), "PUT HIDDEN 0 (Brawl Visibility on @0)"),
              (0, PUT(V_LEDGE, 2, is_float=False), "PUT LEDGE 2 (Brawl Allow/Disallow Ledgegrab 2 @0)")]
        if air: gx += [(0, PUT(V_MOTION_GRAVITY, 0.0), "PUT MOTION_GRAVITY 0 (no gravity yet)"),
                       (10, PUT(V_MOTION_GRAVITY, 1.0), "PUT MOTION_GRAVITY 1 (Brawl Enable Horizontal Gravity? @10: falls from here)")]
        ekey = "cape_end_air" if air else "cape_end"
        ic, how = iasa_for(ekey, hx, 0, None) if not air else (None, "none")
        if air: TUNED_IASA[ekey] = None
        info, _, _ = emit(ekey, [row], [], extra=vis_events(row, hx) + mk_body(hx, 0) + CLOSE_CAPE(row, "ends in Wait / FallSpecial"),
                          host=[], iasa=ic, iasa_how=how, brawl=f"{hx} {SUB(hx)['name']}", geno_extra=gx,
                          note=f"Geno v3 state {st_} (row {row}; clip {V2ROWS[st_][1]}): plain reappear, visible @0, ledge grab"
                               + (", IASA 28 (iasa 'interrupt')" if not air else ", falls from @10"))
    TUNED_IASA["cape_attack"] = None
    cover("cape_v3", "0x1D8-0x1E1 SpecialLw*", [V2ROWS[n][0] for n in STATE_ORDER if n.startswith("Cape")], "translated (Geno exe)",
          "Geno v3 states: geno.cape (vanish, stick-steered), geno.cape.attack x6, geno.cape.end x2 (no Kirby stone code)",
          "start: momentum kept at 0.5 / 0.4, hidden @12, intangible @17, stick-steered vanish (0.5 accel, 2.5 max per axis); @26 B/A held "
          "-> slash (N / back=F / forward=B clips, root motion), else plain reappear; ground -> Wait, air -> FallSpecial; "
          "plain exe: Kirby's stone rows 332-337")
    changes["gfx_hooks"].update({
        "CapeStart": {"rows": [V2ROWS["CapeStart"][0], V2ROWS["CapeStartAir"][0]], "brawl": "0x1D8/0x1D9 gfx",
                      "events": [[5, "Meta Knight ef 22 + gfx 15 (cape swirl)"], [12, "vanish"]]},
        "CapeAttack": {"rows": [V2ROWS[n][0] for n in ("CapeN", "CapeNAir", "CapeF", "CapeFAir", "CapeB", "CapeBAir")],
                       "brawl": "0x1DA-0x1DF gfx", "events": [[0, "Common ef 125 (y 12) + MK ef 25/26/27/28 (N / N air / F / B) + ef 23 + gfx 14 (reappear)"],
                                                               [4, "Sword Glow to 30"]]},
        "CapeEnd": {"rows": [V2ROWS["CapeEnd"][0], V2ROWS["CapeEndAir"][0]], "brawl": "0x1E0/0x1E1 gfx", "events": [[0, "reappear flash (no slash)"]]}})
cover("taunts_idle", "0x1BC/0x1BE AppealHi/S, 0x2 Wait3", [V2ROWS[n][0] for n in ("AppealHi", "AppealS", "Wait3")], "translated (Geno exe)",
      "Geno v2 states", "up / side taunt by stick at the taunt press; Wait3 idle; the down taunt (AppealLw) is Melee's own taunt row")

# ================================================================== 5. place new scripts, repoint rows (stage A)
base = (len(data) + 0x1F) & ~0x1F
data += b"\0" * (base - len(data))
mt = MD.P(root + 0xC)
placed_at = {}
for rows, words, looping in placed:
    at = len(data)
    if looping:
        words = list(words); words[-1] = at; new_relocs.append(at + 4 * (len(words) - 1))
    data += b"".join(struct.pack(">I", w) for w in words)
    for r in rows:
        po = mt + r * 0x18 + 0xC
        if po not in ar.reloc_set: new_relocs.append(po)        # row 48 (Attack13) had no script
        put32(po, at); placed_at[r] = (at, 4 * len(words))
for r, fl in ROW_FLAGS.items():                    # Geno v2 rows: plain, or animation-driven (Drill)
    put32(mt + r * 0x18 + 0x10, fl)
changes["row_flags"] = {str(r): f"0x{fl:08X}" for r, fl in ROW_FLAGS.items()}
changes["untouched"] += ["inhale capture / Eat* / swallow / spit rows (unreachable: MK's neutral B has no catch boxes)",
                         "copy-ability rows (Kirby hats): Kirby clones keep Kirby's copy code",
                         "movement, defensive and common rows: Kirby's scripts (bones remapped to MK, ModelVis from vis_events) on MK's clips"]
relocs = sorted(set(ar.reloc_offsets) | set(new_relocs))
tail = ar.raw[ar.o_public:]
hdr = struct.pack(">5I", 0x20 + len(data) + 4 * len(relocs) + len(tail), len(data), len(relocs), ar.nb_public, ar.nb_extern) + ar.raw[0x14:0x20]
outA = hdr + bytes(data) + b"".join(struct.pack(">I", r) for r in relocs) + tail
os.makedirs(A.out + "/files", exist_ok=True); os.makedirs(A.out + "/final", exist_ok=True)
open(A.out + "/files/PlKb.dat", "wb").write(outA)

# ================================================================== 6. stage B: the MK-skeleton pass over the scripts not written here
w = IM.Writer(outA)
fd = w.ar.public([s for s, _ in w.ar.publics if s.startswith("ftData")][0])
mine = set()
for at, n in placed_at.values(): mine |= set(range(at, at + n, 4))
nrows = len(MD.rows)
starts = [w.u32(mt + r * 0x18 + 0xC) for r in range(nrows) if (mt + r * 0x18 + 0xC) in w.relocs]
FL = IM.FLOW_LEN; OL = IM.OP_LEN
done = set(); stats = collections.Counter()
def walk(o):
    while o not in done and o not in mine and o + 4 <= len(w.data):
        done.add(o); word = w.u32(o); op = word >> 26
        if op < 10:
            if op in (0, 6): return
            if op in (5, 7):
                t = w.u32(o + 4) if (o + 4) in w.relocs else 0
                if t: walk(t)
                if op == 7: return
            o += 4 * FL[op]; continue
        if op - 10 >= len(OL): return
        ln = OL[op - 10]
        new = remap_host_words([w.u32(o + 4 * k) for k in range(ln)])
        if new[0] != w.u32(o): stats[op] += 1; w.put(o, new[0])
        o += 4 * ln
for s_ in starts: walk(s_)
changes["notes"].append(f"stage B: Kirby-authored bones remapped to MK joints in the scripts not written here: {dict(stats)} "
                        "(10 GFX, 11 hitbox, 28 hurtbox state, 58 wind)")
# ModelVis for the rows not written here: install_mk.apply_vis on a vis file without this build's rows
vis_all = json.load(open(os.path.join(MK, "anim", "vis_events.json")))
tmpd = tempfile.mkdtemp()
vis_all["clips"] = [dict(c, rows=[r for r in c["rows"] if r not in placed_at]) for c in vis_all["clips"]]
json.dump(vis_all, open(os.path.join(tmpd, "vis_events.json"), "w"))
anim_saved = IM.ANIM; IM.ANIM = tmpd
visrep = {}
try: IM.apply_vis(w, fd, visrep)
finally: IM.ANIM = anim_saved; shutil.rmtree(tmpd, ignore_errors=True)
changes["notes"].append(f"stage B: ModelVis inserted (install_mk.apply_vis) into {visrep['modelvis']['rows']} rows this build does not write; "
                        f"approximate (loops) {len(visrep['modelvis']['approx_rows'])}")
w.save(A.out + "/final/PlBm.dat")
changes["stageB"] = {"remapped_commands": dict(stats), "modelvis": visrep.get("modelvis")}
changes["clip_overrides"] = {str(r): {"clip": c, "symbol": CLIPS[c]["symbol"], "offset": CLIPS[c]["offset"], "size": CLIPS[c]["size"], "frames": CLIPS[c]["frames"]}
                             for r, c in CLIP_OVERRIDES.items()}

# ================================================================== 7. geno.json: multi-jump + v1 overlays (+ MK's special params, inactive)
IR = json.load(open(os.path.join(MK, "ir", "metaknight.brawl.ir.json")))
blocks = collections.OrderedDict()
for f in IR["behavior"]["attributes"]["special"]["fields"]:
    grp = f["key"].split(".")[0]
    if grp in ("special_n", "special_s", "special_lw", "multijump", "glide"):
        blocks.setdefault(grp, collections.OrderedDict())[f["key"].split(".", 1)[1]] = f["value"]
def wmap(d): return collections.OrderedDict((k, v) for k, v in d.items())
mk_params, word = [], 0
for grp in ("special_n", "special_s", "special_lw"):
    for k_, v in blocks[grp].items():
        mk_params.append({"index": word, "name": f"{grp}.{k_}", ("int" if isinstance(v, int) else "float"): v}); word += 1
fighter = {"attach": "PlBm.dat", "name": "Meta Knight (Brawl)",
           "jumps": {"max": 6, "air_vy": air_vy}}
v1_overlays = [{"index": o["index"], "words": ["0x%08X" % x for x in o["words"]]} for o in overlays]
if V2:
    # Overlays on rows this build does not write: the escapes, then ORIG (the row's own shipped script).
    stick = float(knobs["taunt_stick"])
    taunt = (CHGV(C_VALUE, TGT_GENO(SI["AppealHi"]), (V_STICK_Y, fbits(stick)), cmp=CMP_GT, once=True)
             + CHGV(C_VALUE, TGT_GENO(SI["AppealS"]), (V_STICK_X, fbits(stick)), cmp=CMP_GT, once=True)
             + CHGV(C_VALUE, TGT_GENO(SI["AppealS"]), (V_STICK_X, fbits(-stick)), cmp=CMP_LT, once=True))
    idle = (RAND(RA_INT0, int(knobs["wait3_chance"])) + CHG(C_ANIM_END, TGT_GENO(SI["Wait3"]))
            + CHGAND(C_VAR, (RA_INT0, 0), cmp=CMP_EQ))
    orig_ov = [(r, taunt, "taunt: stick up -> AppealHi, sideways -> AppealS (Brawl's up / side taunts)") for r in (MROWS_BY_NAME["AppealR"], MROWS_BY_NAME["AppealL"])]
    orig_ov += [(MROWS_BY_NAME["Wait1"], idle, f"idle: 1 in {knobs['wait3_chance']} Wait1 cycles ends in Wait3 (Brawl's idle variation)")]
    for r, ws, why in orig_ov:
        v1_overlays.append({"index": r, "words": ["0x%08X" % x for x in ws + ORIG]})
        changes.setdefault("geno_orig_overlays", []).append({"row": r, "escapes": why})
    SUBA = {n: V2ROWS[n][0] for n in V2ROWS}
    SUBA.update({"Tornado": MROWS_BY_NAME["SpecialNLoop"], "TornadoEndGround": MROWS_BY_NAME["SpecialNEnd"]})
    ST = {
        "GlideStart":       {"behavior": "geno.glide.start"},
        "Glide":            {"behavior": "geno.glide"},
        "GlideAttack":      {"behavior": "geno.glide.attack", "like": "motion:65", "move_id": 48},
        "GlideLanding":     {"behavior": "geno.glide.landing"},
        "GlideEnd":         {"behavior": "geno.glide.end", "next": "auto"},
        "Tornado":          {"behavior": "geno.tornado", "move_id": 18, "next": "geno:TornadoEnd"},
        "TornadoEnd":       {"behavior": "geno.air", "phys": "auto", "coll": "both", "next": "helpless", "move_id": 18},
        "TornadoEndGround": {"behavior": "geno.air", "phys": "auto", "coll": "both", "next": "helpless", "move_id": 18},
        "DrillStart":       {"behavior": "geno.drill.start", "move_id": 19},
        "DrillStartAir":    {"behavior": "geno.drill.start", "move_id": 19},
        "Drill":            {"behavior": "geno.drill", "move_id": 19},
        # v3 (Brawl SpecialSEnd): ground end -> Wait, off an edge -> Fall; air end -> FallSpecial, landing -> LandingFallSpecial
        "DrillEndGround":   {"behavior": "geno.drill.end", "move_id": 19, "coll": "ground", "next": "auto"},
        "DrillEnd":         {"behavior": "geno.drill.end", "move_id": 19, "coll": "anim_motion", "ledge": "both",
                             "land": "motion:43", "next": "helpless"},
        "AppealHi":         {"behavior": "geno.ground", "like": "motion:264"},
        "AppealS":          {"behavior": "geno.ground", "like": "motion:264"},
        "Wait3":            {"behavior": "geno.ground", "like": "motion:14", "iasa": "like", "phys": "like", "coll": "like"},
        # v3 Shuttle Loop: like = Kirby's SpecialHi1 / SpecialHi2 / SpecialAirHi1 rows (flags, move id, camera only)
        # Brawl sets the air situation at 5 (Set Air/Ground 17) while the clip still sits on the floor (its rise starts at 7): in
        # Melee an airborne fighter at floor height lands at once, so the state lifts off when the clip starts rising ("liftoff")
        "UpB":              {"behavior": "geno.anim_motion", "like": "motion:385", "liftoff": True, "origin": True, "ledge": "none",
                             "land": "geno:UpBLand", "next": "auto"},
        "UpBAir":           {"behavior": "geno.anim_motion", "like": "motion:389", "ledge": "none", "land": "geno:UpBLand",
                             "next": "geno:UpBLoop"},
        "UpBLoop":          {"behavior": "geno.anim_motion", "like": "motion:386", "origin": True, "ledge": "none",
                             "land": "geno:UpBLand", "next": "auto"},
        "UpBLand":          {"behavior": "geno.ground", "like": "motion:43", "next": "auto"},
        # v3 Dimensional Cape: like = Kirby's SpecialLw rows 393-398 (flags, move id, camera only). The ground reappears keep
        # to the floor ("liftoff": false: the clips' TransN y pops 17.5 up at frame 1; on the ground Brawl ignores it)
        "CapeStart":        {"behavior": "geno.cape", "like": "motion:393"},
        "CapeStartAir":     {"behavior": "geno.cape", "like": "motion:396"},
        "CapeN":            {"behavior": "geno.cape.attack", "like": "motion:394", "facing": "entry", "liftoff": False},
        "CapeNAir":         {"behavior": "geno.cape.attack", "like": "motion:397", "facing": "entry"},
        "CapeF":            {"behavior": "geno.cape.attack", "like": "motion:394", "facing": "entry", "liftoff": False},
        "CapeFAir":         {"behavior": "geno.cape.attack", "like": "motion:397", "facing": "entry"},
        "CapeB":            {"behavior": "geno.cape.attack", "like": "motion:394", "facing": "entry", "liftoff": False},
        "CapeBAir":         {"behavior": "geno.cape.attack", "like": "motion:397", "facing": "entry"},
        "CapeEnd":          {"behavior": "geno.cape.end", "like": "motion:395", "ledge": "both", "liftoff": False},
        "CapeEndAir":       {"behavior": "geno.cape.end", "like": "motion:398", "ledge": "both"},
    }
    assert list(ST) == STATE_ORDER
    states = [dict({"name": n, "subaction": SUBA[n]}, **ST[n]) for n in STATE_ORDER]
    glide = wmap(blocks["glide"]); glide.update({"hold_frames": 16, "pose_center": 90})
    tornado = wmap(blocks["special_n"]); drill = wmap(blocks["special_s"]); drill["bounce"] = 0     # Brawl: nothing ends the rush early
    # Geno v4: Brawl plays SpecialNSpin (361 frames, YRotN = frame degrees) at the spin rate (Frame Speed Modifier = w02,
    # execStatus get/setRate), so the body turns `rate` deg a frame; the clip loops at 360 (frame 360 = frame 0).
    # The drill turns the model with the rush pitch (posture rot.x, SpecialSRush / SpecialSEnd): Geno's default, explicit.
    tornado.update({"spin_anim": 1, "spin_period": 360}); drill["pitch_model"] = 1
    cape = wmap(blocks["special_lw"])
    fighter.update({"geno_v2_note": "Geno v2 (geno_v2_encodings.md): glide / Mach Tornado / Drill Rush as Geno states on MK's own clips; "
                                    "glide/tornado/drill blocks are MK's Brawl words (Misc Glide, paramSpecialN, paramSpecialS) from the IR. "
                                    "drill.speed is not set: the Drill row is animation-driven, its SpecialSDrill TransN is the speed.",
                    "subactions": v1_overlays, "states": states,
                    "specials": {"n": "geno:Tornado", "s": "geno:DrillStart", "air_s": "geno:DrillStartAir",
                                 "hi": "geno:UpB", "air_hi": "geno:UpBAir", "lw": "geno:CapeStart", "air_lw": "geno:CapeStartAir"},
                    "glide": glide, "tornado": tornado, "drill": drill, "cape": cape})
else:
    fighter["subactions"] = v1_overlays
fighter["mk_special_attributes"] = {
    "_status": ("INACTIVE on purpose: v1 'special_attributes' would overwrite the host's (Kirby's) dat_attrs, which Kirby's code reads. "
                + ("paramSpecialN / paramSpecialS and the Misc Glide block now live in the v2 'tornado' / 'drill' / 'glide' blocks above "
                   "(the Geno behaviours own those specials). What remains here has no MK-native reader yet: paramSpecialLw (Dimensional "
                   "Cape runs on Kirby's stone code, tuned through the host knobs speciallw_*) and Misc MultiJump (Kirby's multi-jump table "
                   "+ jumps.air_vy carry the hops)." if V2 else "These are MK's own paramSpecialN/S/Lw words in v1 format, for MK-native "
                   "special code (Phase 4). Rename to special_attributes only when the attach target reads MK's layout.")),
    "words": [m for m in mk_params if not V2 or m["name"].startswith("special_lw")],
    "multijump": blocks["multijump"]}
if not V2: fighter["mk_special_attributes"]["glide"] = blocks["glide"]
fighter["hooks"] = {"on_init": [], "on_frame": [], "on_action": []}
geno = {"geno": 3 if V2 else 1, "fighters": [fighter]}
json.dump(geno, open(A.out + "/geno.json", "w"), indent=1)
changes["geno"] = {"version": geno["geno"], "jumps.max": 6, "air_vy": air_vy,
                   "overlays": [{"row": o["index"], "move": o["move"], "escapes": o["escapes"]} for o in overlays] + changes.get("geno_orig_overlays", []),
                   "states": [{"n": i, "motion": hex(0x400 + i), "name": st["name"], "behavior": st["behavior"], "subaction": st["subaction"],
                               "clip": ROWCLIP.get(st["subaction"])} for i, st in enumerate(fighter.get("states", []))],
                   "specials": fighter.get("specials")}
json.dump(changes, open(A.out + "/CHANGES.json", "w"), indent=1)
json.dump({"moves": moves_report}, open(MK + "/analysis/mk_moves.json", "w"), indent=1)
json.dump({"v1_encodings": "geno_v1_encodings.md (used: CHG, PUT, LINK; overlays in geno.json 'subactions')",
           "overlays": changes["geno"]["overlays"],
           "note": "the Pl file stays plain Melee ftcmd; these entries still have no v1 expression", "stubs": stubs},
          open(MK + "/analysis/v1_stubs.json", "w"), indent=1)
print("stage A", len(outA), "bytes; scripts", len(placed), "moves", len(changes["moves"]), "coverage", len(moves_report),
      "overlays", len(overlays), "stubs", len(stubs), "| stage B remap", dict(stats), "vis rows", visrep["modelvis"]["rows"])
