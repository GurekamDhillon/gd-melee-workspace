"""Meta Knight Phase 1: Brawl Meta Knight's numbers and scripts on a Melee Kirby host -> PlBm.dat (+ CHANGES.json,
geno.json, v1 stubs, move coverage).

    python tools/build_mk.py [--preset tuning.json] [--out build/stage]

Writes <out>/files/PlKb.dat (the Meta Knight fighter file; build_mk_slot.py ships it as PlBm.dat), <out>/CHANGES.json
(the Brawl Kirby schema, so experiment/brawl-kirby/tools/verify_mod.py checks it unchanged), <out>/geno.json,
analysis/mk_moves.json (per-subaction coverage) and analysis/v1_stubs.json (what needs a Geno v1 escape).

Method = the Brawl Kirby Phase 1 build (brawl-kirby/tools/build_mod.py), reused: the vanilla Melee Kirby file is the
base (melee_dump.py decodes it), scripts are rebuilt APPEND-ONLY (new scripts after the data, rows repointed,
relocation table re-emitted), common attributes come from the cast scaling (tools/mk_scaling.py = the Kirby scaling
method), and every value goes through the Kirby tuning layer (brawl-kirby/tools/tuning.py; move keys swapped for
Meta Knight's). Frame convention (both games): a hitbox created at counter c is active from frame c+1, one terminated
at counter e was last active on frame e.

What differs from Kirby's build, and why:
- The host clips are KIRBY's (Phase 1 has no Meta Knight animation), so the host script's non-hitbox events (GFX, SFX,
  smash charge, throw release, flags) stay on Kirby's frames, and Meta Knight's hitboxes/IASA go on Meta Knight's.
  When MK's move is shorter than Kirby's clip and has no Allow Interrupt, an IASA is placed at MK's clip end
  (knob mk.synth_iasa), so the move lasts as long as it does in Brawl. Longer MK moves are cut at Kirby's clip end.
- Hitbox bones: TopN keeps the Brawl offset; other bones use the same-named Melee Kirby joint (brawl-kirby/phase2/
  bone_map.json; SwordM -> RHaveN through SwordM's local transform). Sizes and offsets are scaled by
  mk.hitbox_scale (MK Size 0.95 / Melee Kirby model scale 0.92). Hit SFX from Brawl's sound class
  (Weak/Medium/Strong x Slash/Kick/Punch); element Slash stays Slash.
- Rehit-rate hitboxes compile to ClearHitboxes + re-create every N frames (Melee's own multi-hit idiom).
- Specials sit on Kirby's special rows and code: Mach Tornado on inhale (hitboxes are not Catch-element, so nothing
  is swallowed), Drill Rush on the hammer rows (the hammer item is never spawned), Shuttle Loop on Final Cutter
  (no cutter wave), Dimensional Cape on Stone (Kirby never turns to stone; the stone hold becomes the vanish, the end
  row the reappear attack, then helpless fall via speciallw_freefall_toggle)."""
import sys, os, json, struct, collections, copy, math, argparse, fnmatch
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(HERE); EXP = os.path.join(os.path.dirname(os.path.dirname(MK)), "experiment")
BK = os.path.join(EXP, "brawl-kirby"); BKT = os.path.join(BK, "tools")
ap = argparse.ArgumentParser()
ap.add_argument("--preset", default=os.path.join(MK, "tuning.json"))
ap.add_argument("--out", default=os.path.join(MK, "build", "stage"))
ap.add_argument("--geno-v1", default=os.path.join(MK, "geno_v1_encodings.md"), help="emit v1 escapes when this file exists (not implemented until it does)")
A = ap.parse_args()
os.makedirs(os.path.join(MK, "analysis"), exist_ok=True)
os.environ["MD_OUT"] = os.path.join(MK, "analysis", "_host_kirby_vanilla.json")   # melee_dump writes its decode on import
os.environ.pop("MD_IN", None)
sys.path.insert(0, BKT)
import melee_dump as MD
import tuning as TUN

# ------------------------------------------------------------------ tuning: Meta Knight move keys
MOVE_KEYS = ["jab", "rapid_jab_start", "rapid_jab", "rapid_jab_end", "dash_attack", "ftilt", "utilt", "dtilt",
             "fsmash", "usmash", "dsmash", "nair", "fair", "bair", "uair", "dair",
             "nair_land", "fair_land", "bair_land", "uair_land", "dair_land",
             "grab", "dash_grab", "pummel", "throwf", "throwb", "throwhi", "throwlw",
             "ledge_attack_fast", "ledge_attack_slow", "getup_attack_up", "getup_attack_down",
             "tornado_start", "tornado", "tornado_end", "drill_rush", "drill_rush_air",
             "shuttle_loop_rise", "shuttle_loop_loop", "shuttle_loop_fall", "shuttle_loop_land",
             "cape_start", "cape_vanish", "cape_attack", "jumpaerial"]
TUN.MOVE_KEYS = MOVE_KEYS
TUN.ALIASES = {"fthrow": "throwf", "bthrow": "throwb", "uthrow": "throwhi", "dthrow": "throwlw", "mach_tornado": "tornado",
               "neutral_b": "tornado", "side_b": "drill_rush", "up_b": "shuttle_loop_rise", "down_b": "cape_attack"}
MK_KNOBS = {"hitbox_scale": round(0.95 / 0.92, 4), "synth_iasa": True, "autolink_angle": 80, "tornado_rehit": 10,
            "drill_rehit": None, "clear_iasa_on_landing": True}
raw_cfg = json.load(open(A.preset, encoding="utf-8"))
knobs = dict(MK_KNOBS); knobs.update({k: v for k, v in (raw_cfg.get("mk") or {}).items() if not k.startswith("_")})
cfg = {k: v for k, v in raw_cfg.items() if k != "mk"}
TUN.Tuning(cfg, A.preset)                            # validate
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
changes = {"fighter": "Brawl Meta Knight (Phase 1, Kirby host)", "attributes": [], "special_attributes": [], "moves": [],
           "untouched": [], "notes": [], "knobs": knobs, "tuning": TT.summary()}
moves_report = []      # coverage table rows
stubs = []             # Geno v1/v2 needs

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
write_attr("rapid_jab_window", 1, brawl_raw=1,
           note="MK's jab is rapid-only (no Attack11-13 in Brawl): Attack11 arms the rapid jab at once and the first A release "
                "(count 1) enters Attack100Start. Melee Kirby needs 4 presses/releases.")

# ================================================================== 1b. host special attributes (Kirby's ftKb_DatAttrs)
sa = MD.P(root + 4)
sname = {int(s["offset"], 16): s["name"] for s in MD.special}
soff = {v: k for k, v in sname.items()}
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
air_vy = []
for i, h in enumerate(HOPS):
    air_vy.append(write_special(f"jumpaerial_jump{i+1}_vertical_momentum", round(h * kjump, 4), f"brawl hop x {kjump:.4f} (jump_v_initial scale)", brawl_raw=h))
# Kirby-host placeholders for MK specials (Kirby's special code runs them)
write_special("speciallw_max_time_in_stone", 8, "Dimensional Cape: vanish frames (stone hold reused; min = max so it is fixed)", is_int=True)
write_special("speciallw_min_time_in_stone", 8, "Dimensional Cape: vanish frames", is_int=True)
write_special("speciallw_gravity", 0.4, "Dimensional Cape (air): sink speed while vanished (Kirby's stone drop 4.5)")
write_special("speciallw_freefall_toggle", 20.0, "Dimensional Cape: != 0 -> the end row enters FallSpecial with this landing lag (Brawl: fall special)")
changes["notes"].append("Multi-jump: 6 jumps (1 ground + 5 air) = Kirby's own 5-state table; hop velocities are Brawl MK's x the jump scale. "
                        "geno.json carries the same jumps.max / air_vy for the Geno exe.")

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

BONEMAP = {m["brawl_bone"]: m["melee_joint"] for m in json.load(open(BK + "/phase2/bone_map.json"))["map"]}
MKB = {b["name"]: b for b in json.load(open(MK + "/dump/mk_bones.json"))}
def _vec(s): return [float(x) for x in s.strip("()").split(",")]
def _rot(deg):
    rx, ry, rz = [math.radians(d) for d in deg]
    cx, sx_, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    # HSD / BrawlLib bone order: R = Rz * Ry * Rx
    return [[cz*cy, cz*sy*sx_ - sz*cx, cz*sy*cx + sz*sx_], [sz*cy, sz*sy*sx_ + cz*cx, sz*sy*cx - cz*sx_], [-sy, cy*sx_, cy*cx]]
def bone_joint(bone, off):
    """Brawl MK bone + offset -> (Melee Kirby joint, offset in that joint's frame, how)."""
    if bone == "TopN": return 0, list(off), "TopN (joint 0)"
    if bone in BONEMAP: return BONEMAP[bone], list(off), f"{bone} -> Melee joint {BONEMAP[bone]} (same name)"
    b = MKB.get(bone)
    if b and b["parent"] in BONEMAP:
        R = _rot(_vec(b["rotation"])); t = _vec(b["translation"])
        p = [sum(R[i][j] * off[j] for j in range(3)) + t[i] for i in range(3)]
        return BONEMAP[b["parent"]], p, f"{bone} -> parent {b['parent']} (local transform) -> Melee joint {BONEMAP[b['parent']]}"
    return 0, list(off), f"{bone}: no Melee joint -> TopN"

def term_counters(s):
    f = 0; t = set()
    for e in s["channels_raw"]["main"]:
        n = e.get("name"); a = e.get("args")
        if n == "Synchronous Timer": f += a[0]
        elif n == "Asynchronous Timer": f = max(f, a[0])
        elif n in ("Terminate Collisions",): t.add(int(f))
    return t

def host_templates(row):
    """Melee Kirby hitboxes of the host row, as hitbox sets in script order (for flags / sfx fallback / 'melee' tuning base)."""
    src = int(MROWS[row]["script"], 16)
    flat, static, reason = MD.flatten(src)
    sets = collections.OrderedDict()
    for f, ev in flat:
        if ev["name"] == "Hitbox": sets.setdefault(f, []).append(ev["hitbox"])
    return list(sets.values())

def mk_windows(hexid, offset=0, until=None, rehit=None, only=None, clip_from=None, clip_to=None, angle_fix=None):
    """Brawl hitboxes of subaction hexid -> window list [{slot, start, end, h, new_hit, win}] with counters + offset.
    until: counter where hitboxes with no end stop (segment end). rehit: re-create every N frames (new hit).
    clip_from/clip_to: keep only the part of the Brawl timeline in [clip_from, clip_to) (counters before offset)."""
    s = SUB(hexid); term = term_counters(s); log = []
    hbs = [h for h in s["hitboxes"] if h["kind"] in ("hitbox", "special_hitbox")]
    if only is not None: hbs = [h for h in hbs if only(h)]
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
                log.append(f"id{h['id']} angle {h['angle']} (autolink) -> {angle_fix[h['angle']]} (fixed-angle approximation; Geno v1 autolink)")
                h["angle"] = angle_fix[h["angle"]]
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
    """Brawl Body Collision (0 normal, 1 invincible, 2+ intangible) and Visibility -> Melee BodyCollState / FighterVis words."""
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

def mk_iasa(hexid, offset=0):
    s = SUB(hexid)
    if s.get("iasa_frame") is not None: return int(s["iasa_frame"]) + offset, "brawl Allow Interrupt"
    return int(s["anim_frames"]) + offset, "synthesized: Brawl clip end (no Allow Interrupt)"

placed = []                  # (rows, words, looping)
placed_meta = []

def emit(key, rows, windows, *, extra=(), keep=None, iasa=None, iasa_how=None, looping=False, loop_len=None, host_end=None,
         catch=False, grabbed=False, log=(), brawl=None, note=None, host_row=None):
    """Assemble a Melee script. windows: mk_windows output. extra: [(counter, words, label)] (placed before hitboxes).
    keep: predicate on host events (flattened host script) to keep them on their counters (None = default)."""
    log = list(log)
    host_row = host_row if host_row is not None else rows[0]
    r = MROWS[host_row]; src = int(r["script"], 16)
    anim = r["anim_frames"] or 0
    flat, static, reason = MD.flatten(src)
    templates = host_templates(host_row) if static or reason == "goto loop" else []
    if keep is None: keep = lambda ev: True
    kept = [(f, ev) for f, ev in flat if ev["name"] not in HB_OPS and ev["name"] not in FLOW and keep(ev)] if (static or reason == "goto loop") else []
    mend = [f for f, ev in flat if ev["name"] == "End"]
    host_len = host_end if host_end is not None else (mend[0] if mend else (flat[-1][0] if flat else 0))
    # ---- hitbox create words
    creates = collections.defaultdict(list); ends = collections.defaultdict(set); info = []
    for w in sorted(windows, key=lambda w: (w["start"], w["slot"])):
        h = dict(w["h"]); slot = w["slot"]
        t = None
        if templates:
            ms = templates[min(len(templates) - 1, w["win"] - 1)]
            cand = [x for x in ms if x["slot"] == slot] or [ms[min(len(ms) - 1, slot)]]
            t = cand[0]
        joint, offs, jhow = bone_joint(h.get("bone_name") or "TopN", h["offset"])
        k = knobs["hitbox_scale"]
        offs = [o * k for o in offs]
        h["size"] = round(h["size"] * k, 4)
        if catch:
            tt = t; tr = None
            words = pack_hitbox(slot, 0, tt["damage"], h["size"], offs, tt["angle"], tt["knockback_growth"], tt["weight_dependent_set_knockback"],
                                tt["base_knockback"], tt["element_raw"], tt["shield_damage"], tt["hit_sfx"]["level"], tt["hit_sfx"]["kind"],
                                tt["targets"]["ground"], tt["targets"]["air"], flags5_of(tt))
            rec = {"slot": slot, "damage": tt["damage"], "angle": tt["angle"], "kbg": tt["knockback_growth"], "wdsk": tt["weight_dependent_set_knockback"],
                   "bkb": tt["base_knockback"], "size": h["size"], "element": "Grounded", "joint": 0, "joint_from": "grab box: Melee catch template (element catch), MK size/offset/timing",
                   "brawl_bone": h.get("bone_name"), "active": [w["start"] + 1, w["end"]]}
        else:
            h2, tr = TT.hitbox(key, w["win"], h, t)
            flags5 = flags5_of(t) if t else 0b10011
            if not h2.get("clang", True): flags5 &= ~0b00011
            snd = h.get("sfx") or ""
            lvl = next((v for kname, v in SFXLVL.items() if snd.startswith(kname)), 1)
            kind = next((v for kname, v in SFXKIND.items() if snd.endswith(kname)), (t["hit_sfx"]["kind"] if t else 1))
            el = ELEM.get(h2["element"], 0)
            gb = 1 if (grabbed or (h.get("special_flags") or {}).get("HittingGrippedCharacter")) else 0
            words = pack_hitbox(slot, joint, h2["damage"], h2["size"], offs, h2["angle"], h2["kbg"], h2["wdsk"], h2["bkb"], el,
                                int(h2.get("shield_damage") or 0), lvl, kind, h2.get("ground", True), h2.get("air", True), flags5, grabbed=gb)
            rec = {"slot": slot, "damage": h2["damage"], "angle": h2["angle"], "kbg": h2["kbg"], "wdsk": h2["wdsk"], "bkb": h2["bkb"],
                   "size": h2["size"], "element": h2["element"], "joint": joint, "joint_from": jhow, "brawl_bone": h.get("bone_name"),
                   "offset": [round(o, 3) for o in offs], "active": [w["start"] + 1, w["end"]], "shield": h2.get("shield_damage"),
                   "hit_sfx": [lvl, kind], "clank": bool(flags5 & 2), "only_hit_grabbed": gb, "tuning": tr}
            if w.get("rehit"): rec["rehit"] = w["rehit"]
        creates[w["start"]].append((slot, words, rec, w["new_hit"]))
        if w["end"] is not None: ends[w["end"]].add(slot)
    iasa_c = iasa
    if iasa_c is not None and anim and iasa_c >= anim:
        log.append(f"IASA {iasa_c + 1} ({iasa_how}) >= Kirby clip length {anim:g}: dropped (interruptible at clip end)"); iasa_c = None
    last = max([host_len] + list(creates) + [e for e in ends] + [c for c, _, _ in extra] + ([iasa_c] if iasa_c is not None else []))
    if anim and not looping:
        late = sorted({w["start"] for w in windows if w["start"] >= anim})
        if late: log.append(f"MK hitboxes created at counters {late} are past Kirby's {anim:g}-frame clip: never active (state ends at clip end)")
    # ---- emit
    frames = sorted(set([f for f, _ in kept] + list(creates) + list(ends) + [c for c, _, _ in extra] + ([iasa_c] if iasa_c is not None else [])))
    out = []; cur = 0; active = set()
    def wait(f):   # AsyncWait counts the ANIMATION frame (ftAction_80073240); a "sync" loop is anim-independent
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
        for ff, ev in kept:
            if ff == f: out += [int(x, 16) for x in ev["raw"]["words"]]
        for s, words, rec, nh in cr:
            out += words; active.add(s); info.append(rec)
        if iasa_c is not None and f == iasa_c: out.append(23 << 26)
    if looping == "sync":
        if loop_len and loop_len > cur: wait(loop_len)
        out.append(7 << 26); out.append(0)
    elif looping:                       # "anim": wait for the clip to loop (SetTimerAnim), as Kirby's own rapid jab does
        out.append(8 << 26); out.append(7 << 26); out.append(0)
    else:
        if host_len > cur: out.append((2 << 26) | host_len)
        out.append(0)
    placed.append((rows, out, looping))
    tiasa = None
    iasa_rec = None if iasa_c is None else iasa_c + 1
    for rr in rows:
        mr = MROWS[rr]; orig = MD.scripts[int(mr["script"], 16)]["timeline"]
        m = {"move": key, "melee_row": rr, "melee_name": mr["name"], "brawl_subaction": brawl,
             "melee_before": {"windows": [[x["start"], x["end"], x["damage"]] for x in orig["hit_windows"]], "iasa": orig.get("interruptible_from")},
             "written_hitboxes": info, "written_iasa": iasa_rec, "melee_anim_frames": anim, "tuning": TT.label(key),
             "tuning_iasa": TUNED_IASA.get(key), "iasa_how": iasa_how, "extra_events": [(c, l) for c, _, l in extra],
             "kept_host_events": sorted({ev["name"] for _, ev in kept}), "notes": log + ([note] if note else [])}
        if catch:     # verify_mod.py knows no catch element; tools/verify_mk.py checks these
            m["written_catch_boxes"] = m.pop("written_hitboxes")
        changes["moves"].append(m)
    return info, iasa_rec, log

TUNED_IASA = {}
def iasa_for(key, hexid, offset=0, host_row=None, policy="auto"):
    """IASA counter through the tuning hook. policy: auto (Allow Interrupt, else synthesized clip end if knob) | none."""
    melee = MD.scripts[int(MROWS[host_row]["script"], 16)]["timeline"].get("interruptible_from") if host_row is not None else None
    if policy == "none":
        c, how = None, "none (landing lag / code-driven)"
    else:
        c, how = mk_iasa(hexid, offset)
        if how.startswith("synth") and not knobs["synth_iasa"]: c, how = None, "none (mk.synth_iasa off)"
    c2, rec = TT.iasa(key, c, melee)
    TUNED_IASA[key] = rec
    return c2, (how if TT.move(key)["iasa"] is None and TT.move(key)["base"] == "brawl" else f"tuned ({rec['how']})")

def verdict(hexid, host_row, windows):
    """The Kirby mapping tool's legend: direct = same window structure (count, hitboxes per window), restructure = not."""
    mw = [x for x in MD.scripts[int(MROWS[host_row]["script"], 16)]["timeline"]["hit_windows"]]
    bw = sorted({(w["start"]) for w in windows})
    if len(mw) == len(bw): return "direct", f"{len(bw)} window(s) in both"
    return "restructure", f"Brawl {len(bw)} window(s) vs Melee Kirby {len(mw)}"

def cover(key, brawl, rows, status, verdict_, what, approx=(), stub=()):
    moves_report.append({"move": key, "brawl_subaction": brawl, "melee_rows": [f"{r} {MROWS[r]['name']}" for r in rows] if rows else [],
                         "status": status, "verdict": verdict_, "what": what, "approximated": list(approx), "stubbed": list(stub)})

def stub(ver, where, brawl_event, need, frame=None):
    stubs.append({"geno": ver, "where": where, "frame": frame, "brawl_event": brawl_event, "needs": need})

def unported_events(hexid, where):
    """Brawl events a Melee script cannot express -> stub list (translated ones are skipped)."""
    s = SUB(hexid)
    V1 = {"Change Action": "change-action escape", "Change Action Status": "change-action escape (status transition groups)",
          "Additional Change Action Requirement": "change-action escape", "Set Air/Ground": "engine-value write (ground/air)",
          "Set/Add Momentum": "engine-value write (velocity)", "Disable Horizontal Gravity": "engine-value write (gravity)",
          "Enable Horizontal Gravity?": "engine-value write (gravity)", "Disallow Vertical Movement": "engine-value write (velocity)",
          "Reverse Direction": "engine-value write (facing)", "Allow/Disallow Ledgegrab": "engine-value write (ledge grab flag)",
          "Frame Speed Modifier": "engine-value write (anim rate)", "If Comparison": "v0 IF + engine-value read", "If Value": "v0 IF + engine-value read",
          "If": "v0 IF + engine-value read"}
    V2 = {"Article Visibility": "cape article (Phase 3 merges it into the model: ModelVis)", "Set Anchored Article SubAction": "cape article",
          "Model Changer 2": "model parts (Phase 3: ModelVis on MK's own model)", "Sword Glow": "sword trail (m-ex trail data / Geno)",
          "Terminate Sword Glow": "sword trail", "Graphic Effect": "MK effect bank (EfMk) not ported", "External Graphic Effect": "effect bank",
          "Sound Effect": "MK sound bank not extracted (BRSAR)", "Character Specific 17": "MK native"}
    seen = set()
    for ch in ("main", "other", "gfx", "sfx"):
        for e in s["channels_raw"].get(ch, []):
            n = e.get("name")
            if n in V1 and (n, ch) not in seen: seen.add((n, ch)); stub("v1", where, n, V1[n], e.get("frame"))
            elif n in V2 and n not in seen: seen.add(n); stub("later", where, n, V2[n], e.get("frame"))

# ================================================================== 3. normals
def generic(key, host_names, hexid, offset=0, iasa_policy="auto", keep=None, note=None, grabbed=False, extra=()):
    rows = [MROWS_BY_NAME[n] for n in host_names if MROWS[MROWS_BY_NAME[n]]["script"]]
    wins, log = mk_windows(hexid, offset, angle_fix={365: knobs["autolink_angle"]})
    body = mk_body(hexid, offset)
    if body:
        k0 = keep
        keep = (lambda ev: ev["name"] not in ("BodyCollState", "FighterVis") and (k0 is None or k0(ev)))
    ic, how = iasa_for(key, hexid, offset, rows[0], iasa_policy)
    info, iasa_rec, log2 = emit(key, rows, wins, extra=list(body) + list(extra), keep=keep, iasa=ic, iasa_how=how, log=log,
                                 brawl=f"{hexid} {SUB(hexid)['name']}", note=note, grabbed=grabbed)
    v, vwhy = verdict(hexid, rows[0], wins)
    approx = [x for x in log2 if "past Kirby" in x or "dropped" in x or "autolink" in x]
    anim_b = SUB(hexid)["anim_frames"]; anim_m = MROWS[rows[0]]["anim_frames"]
    if anim_b and anim_m and anim_b + offset > anim_m: approx.append(f"Brawl clip {anim_b + offset:g} frames > Kirby clip {anim_m:g}: the move ends at Kirby's clip end")
    approx.append("host events (GFX/SFX/flags) on Kirby's frames; hitbox positions provisional until MK's skeleton (Phase 3)")
    cover(key, f"{hexid} {SUB(hexid)['name']}", rows, "approximated" if any("past" in a or "ends at" in a for a in approx) else "translated",
          f"{v}: {vwhy}", f"{len(info)} hitbox events, IASA {iasa_rec} ({how})", approx)
    unported_events(hexid, key)
    return info

MROWS_BY_NAME = {}
for r in MD.rows:
    if r["category"] != "copy_ability" and r["name"] not in MROWS_BY_NAME: MROWS_BY_NAME[r["name"]] = r["index"]

# --- jab: rapid only
r11 = MROWS_BY_NAME["Attack11"]
emit("jab", [r11], [], extra=[(2, [(30 << 26) | 1], "RapidJab flag on (x2218_b2) at counter 2 (the entry frame runs counters 0-1 and checkAttack11 clears the flag after it; measured in game): first A release -> Attack100Start")],
     keep=lambda ev: ev["name"] in ("ft_8008A1B8",), iasa=None, iasa_how="none", brawl="0x4B Attack100Start (entry)",
     note="MK has no Attack11-13: Attack11 only arms the rapid jab (Melee checks presses+releases >= rapid_jab_window = 1). "
          "No JabCombo, so Attack12/13 are unreachable.")
TUNED_IASA["jab"] = None
cover("jab", "- (no Attack11 in Brawl)", [r11], "translated", "restructure: Melee jab 1 -> rapid-jab entry",
      "Attack11 = rapid-jab entry (RapidJab flag, no hitbox); rapid_jab_window 1")
generic("rapid_jab_start", ["Attack100Start"], "0x4B", iasa_policy="none")
# rapid jab loop: MK hitboxes on MK counters, Melee's loop checkpoints (ThrowFlag b3) at MK's RA.Bit[25] counters, 20-frame loop
rl = MROWS_BY_NAME["Attack100Loop"]
wins, log = mk_windows("0x4C", 0)
emit("rapid_jab", [rl], wins, extra=[(9, [20 << 26], "loop checkpoint (Brawl RA.Bit[25] @9)"), (19, [20 << 26], "loop checkpoint (Brawl RA.Bit[25] @19)")],
     keep=lambda ev: ev["name"] == "GFX", iasa=None, iasa_how="none", looping="anim", log=log, brawl="0x4C Attack100",
     note="20-frame loop (Brawl Attack100 goto at 20 = Kirby's 20-frame clip); Melee ends the loop at a checkpoint with no A press/release since the last")
TUNED_IASA["rapid_jab"] = None
cover("rapid_jab", "0x4C Attack100", [rl], "translated", "direct: 5 rehit windows per loop",
      "loop body = MK's 5 windows (2%/1% mix), checkpoints at MK's RA.Bit[25] frames")
generic("rapid_jab_end", ["Attack100End"], "0x4D", iasa_policy="auto")
generic("dash_attack", ["AttackDash"], "0x4E")
generic("ftilt", ["AttackS3Hi", "AttackS3S", "AttackS3Lw"], "0x50",
        note="Brawl MK has no angled ftilt: all three Melee angles play ftilt 1. The 3-hit chain (AttackS3S2/S3S3) needs the v1 change-action escape.")
for hx, nm in (("0x51", "AttackS3S2"), ("0x52", "AttackS3S3")):
    w_, l_ = mk_windows(hx, 0)
    cover(f"ftilt{hx[-1]}", f"{hx} {nm}", [], "stubbed-for-v1", "unsupported (no Melee state)",
          f"{len(w_)} hitbox windows translated in mk_moves.json, no host row: Brawl chains S3S -> S3S2 -> S3S3 on A inside RA.Bit[16] "
          f"(set @4 / @3); needs change-action escape + a host motion", stub=["change-action escape (A pressed, RA.Bit[16]) -> " + nm])
    stub("v1", "ftilt", f"Bit Variable Set RA.Bit[16] -> chain to {nm}", "change-action escape (A in window) + host motion for the next hit", 4 if hx == "0x51" else 3)
generic("utilt", ["AttackHi3"], "0x54")
generic("dtilt", ["AttackLw3"], "0x55")
S4 = int(SUB("0x56")["anim_frames"]); HI4 = int(SUB("0x5C")["anim_frames"]); LW4 = int(SUB("0x5F")["anim_frames"])
generic("fsmash", ["AttackS4Hi", "AttackS4S", "AttackS4Lw"], "0x58", offset=S4,
        note=f"Brawl AttackS4Start ({S4} frames) + AttackS4S; Melee charges inside the script (Kirby's SmashCharge kept on Kirby's frame). No angled fsmash in Brawl MK.")
generic("usmash", ["AttackHi4"], "0x5D", offset=HI4, note=f"Brawl AttackHi4Start ({HI4}) + AttackHi4")
generic("dsmash", ["AttackLw4"], "0x60", offset=LW4, note=f"Brawl AttackLw4Start ({LW4}) + AttackLw4")
for k_, n_, hx in (("nair", "AttackAirN", "0x62"), ("fair", "AttackAirF", "0x63"), ("bair", "AttackAirB", "0x64"), ("uair", "AttackAirHi", "0x65"), ("dair", "AttackAirLw", "0x66")):
    generic(k_, [n_], hx)
    stub("v1", k_, "Bit Variable Set/Clear RA.Bit[30] (auto-cancel window)", "none needed in Melee (L-cancel rules) - listed for completeness", None)
for k_, n_, hx in (("nair_land", "LandingAirN", "0x67"), ("fair_land", "LandingAirF", "0x68"), ("bair_land", "LandingAirB", "0x69"),
                   ("uair_land", "LandingAirHi", "0x6A"), ("dair_land", "LandingAirLw", "0x6B")):
    generic(k_, [n_], hx, iasa_policy="none", note="MK has no landing hitboxes (Kirby's landing hits removed); lag = landingair*_lag attributes")
generic("pummel", ["CatchAttack"], "0x70")
generic("ledge_attack_fast", ["CliffAttackQuick"], "0x0D7")
generic("ledge_attack_slow", ["CliffAttackSlow"], "0x0DC")
generic("getup_attack_up", ["DownAttackU"], "0x0B0")
generic("getup_attack_down", ["DownAttackD"], "0x0B9")

# --- multi-jump gate: Kirby's JumpAerialF1-4 allow the next air jump at counter 28 (SetCmdVar 0 = 1, read by
#     ftCo_800D72A0); Brawl MK's JumpAerialF sets RA.Bit[17]/[19] at 24 -> the gate moves to MK's 24. F5 is the last jump.
for i in range(1, 5):
    hx = f"0x{0x1A + i:X}"
    gate = [int(fr) for fr, n, a_ in SUB(hx)["main_timeline"] if n == "Bit Variable Set"][0]
    rows = [MROWS_BY_NAME[f"JumpAerialF{i}"], MROWS_BY_NAME[f"JumpAerialF{i}Met"]]
    emit("jumpaerial", rows, [], extra=[(gate, [(19 << 26) | 1], f"multi-jump gate: SetCmdVar 0 = 1 at Brawl's RA.Bit[17]/[19] counter {gate} (Kirby: 28)")],
         keep=lambda ev: ev["name"] != "SetCmdVar", iasa=None, iasa_how="none", brawl=f"{hx} {SUB(hx)['name']}",
         note="air jump i+1 allowed from MK's frame (Kirby's clip, ModelVis and SFX kept)")
TUNED_IASA["jumpaerial"] = None
cover("jumpaerial", "0x1B-0x1E JumpAerialF1-F4", [MROWS_BY_NAME[f"JumpAerialF{i}"] for i in range(1, 5)], "translated",
      "direct: one gate event", "next air jump allowed at MK's counter 24 (Kirby's 28); hop impulses in special attrs / geno.json",
      ["Kirby's 50-frame jump clips (MK 34)"])

# --- grabs: MK Catch Collision timing/size on Kirby's catch template (element catch)
def grab(key, name, hexid):
    s = SUB(hexid); row = MROWS_BY_NAME[name]
    tend = [int(f) for f, n, _ in s["main_timeline"] if n == "Terminate Catch Collisions"]
    wins = []
    for j, g in enumerate(sorted(s["grabs"], key=lambda g: g["args"]["ID"])[:4]):
        a = g["args"]
        bone = "TopN" if a["Bone"] in (0, 400) else MKB_BY_INDEX.get(a["Bone"], "TopN")
        wins.append({"slot": j, "start": int(g["frame"]), "end": tend[0] if tend else None, "win": 1, "new_hit": False,
                     "h": {"bone_name": bone, "offset": [a["X offset"], a["Y Offset"], a["Z Offset"]], "size": a["Scale"]}})
    emit(key, [row], wins, keep=None, iasa=None, iasa_how="none", catch=True, brawl=f"{hexid} {s['name']}",
         note="grab boxes: Melee Kirby's catch hitboxes (element catch, flags) with MK's timing, size and offset")
    TUNED_IASA[key] = None
    cover(key, f"{hexid} {s['name']}", [row], "translated", "direct: one grab window", f"{len(wins)} catch boxes, active {wins[0]['start']+1}-{wins[0]['end']}")
MKB_BY_INDEX = {b["index"]: b["name"] for b in MKB.values()}
grab("grab", "Catch", "0x6C"); grab("dash_grab", "CatchDash", "0x6D")
cover("pivot_grab", "0x6E CatchTurn", [], "stubbed-for-v2", "unsupported", "Brawl pivot grab: no Melee motion (Melee turns then grabs)", stub=["Geno action state"])

# --- throws: MK throw values patched into the host's ThrowHitbox commands; MK bystander hitboxes; release timing
def throw(key, name, hexid, move_release):
    s = SUB(hexid); row = MROWS_BY_NAME[name]
    spec = {t["args"]["ID"]: t["args"] for t in s["throws"] if t["name"] == "Throw Specifier"}
    app = [int(t["frame"]) for t in s["throws"] if t["name"] == "Throw Applier"]
    keep = None; extra = []
    if move_release and app:
        keep = lambda ev: ev["name"] != "ThrowFlagB3/B4"
        extra = [(app[0], [20 << 26], f"throw release at Brawl's Throw Applier (counter {app[0]})")]
    wins, log = mk_windows(hexid, 0)
    body = mk_body(hexid, 0)
    if body:
        k0 = keep; keep = (lambda ev: ev["name"] not in ("BodyCollState", "FighterVis") and (k0 is None or k0(ev)))
    ic, how = iasa_for(key, hexid, 0, row, "auto" if move_release else "none")
    info, ia, log2 = emit(key, [row], wins, extra=body + extra, keep=keep, iasa=ic, iasa_how=how, log=log, brawl=f"{hexid} {s['name']}",
                          note=("release moved to MK's Throw Applier" if move_release else "release/motion stay Kirby's (Kirby's throw clip carries the victim); MK's throw values"))
    # patch the (copied) ThrowHitbox commands in the new words
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
    approx = ["host clip/motion (Kirby's throw) with MK's numbers"] + ([] if move_release else ["release timing = Kirby's"])
    if len(info): approx.append(f"{len(info)} MK hitboxes on MK counters (bystander/grabbed hits) over Kirby's motion")
    cover(key, f"{hexid} {s['name']}", [row], "approximated", "direct: ThrowHitbox values map 1:1 (Throw Specifier)",
          f"throw {done[0]['written'] if done else '?'}; IASA {ia}", approx)
    unported_events(hexid, key)
throw("throwf", "ThrowF", "0x73", False)
throw("throwb", "ThrowB", "0x72", False)
throw("throwhi", "ThrowHi", "0x74", False)
throw("throwlw", "ThrowLw", "0x75", True)

# ================================================================== 4. specials on Kirby's special rows
NOFX = lambda ev: ev["name"] not in ("GFX", "SFX", "RandomSmashSFX", "ModelVis", "ThrowHitbox")
# --- Neutral B: Mach Tornado on inhale (SpecialN / SpecialNLoop / SpecialNEnd, air rows too)
for key, names, hx in (("tornado_start", ["SpecialN", "SpecialAirN"], "0x1CE"),):
    rows = [MROWS_BY_NAME[n] for n in names]
    emit(key, rows, [], keep=lambda ev: NOFX(ev), iasa=None, iasa_how="none", brawl=f"{hx} SpecialNStart",
         note="inhale start: Kirby's catch box, mouth ModelVis, GFX/SFX removed; SetCmdVar kept (inhale state machine)")
    TUNED_IASA[key] = None
    cover(key, f"{hx} SpecialNStart", rows, "approximated", "unsupported: host = Kirby inhale start (code)", "no hitbox (Brawl start has none)",
          ["Kirby's inhale start clip/physics (placeholder)"])
rt = [MROWS_BY_NAME["SpecialNLoop"], MROWS_BY_NAME["SpecialAirNLoop"]]
wins, log = mk_windows("0x1D0", 0, until=knobs["tornado_rehit"], rehit=None)
for w in wins: w["new_hit"] = True
emit("tornado", rt, wins, keep=lambda ev: ev["name"] == "Rumble", iasa=None, iasa_how="none", looping="sync", loop_len=knobs["tornado_rehit"],
     log=log + [f"rehit every {knobs['tornado_rehit']} frames (paramSpecialN[11] = 10, param id 24000 read by the native execStatus; inferred)"],
     brawl="0x1D0 SpecialNSpin", note="loops while B is held (Kirby's inhale loop code); 4 x 1% set-knockback hitboxes re-created every loop")
TUNED_IASA["tornado"] = None
cover("tornado", "0x1D0 SpecialNSpin", rt, "approximated", "unsupported: native tornado physics (sora_melee execStatus)",
      f"4 hitboxes x 1% rehit every {knobs['tornado_rehit']} frames while B held",
      ["placeholder physics: Kirby's inhale loop (no rise/drift, no tap-to-rise); duration = while B held"],
      ["Phase 4: tornado phys/input callbacks (tap to rise, 4012-4015)", "v1 rehit escape optional (compiled to Clear+recreate)"])
stub("v2", "tornado", "ftMetaknightStatusUniqProcessSpecialNSpin::execStatus", "native physics callback (rise on B taps, drift, fixed duration)", None)
rn = [MROWS_BY_NAME["SpecialNEnd"]]
wins, log = mk_windows("0x1D1", 0)
emit("tornado_end", rn, wins, keep=lambda ev: NOFX(ev), iasa=None, iasa_how="none", log=log, brawl="0x1D1 SpecialNEnd",
     note="Kirby's SpecialNEnd row also serves the air end (no own row)")
TUNED_IASA["tornado_end"] = None
cover("tornado_end", "0x1D1 SpecialNEnd (+0x1D2 air)", rn, "translated", "direct", "3% finisher 0-3", ["air end shares the ground row"])

# --- Side B: Drill Rush on the hammer rows (Start 22 + drill rehit + End, squeezed into Kirby's 60/70-frame clips)
for key, name, endhx, host_len in (("drill_rush", "SpecialS", "0x1D6", 60), ("drill_rush_air", "SpecialAirS", "0x1D7", 70)):
    row = MROWS_BY_NAME[name]
    st = int(SUB("0x1D3")["anim_frames"])                  # 22
    end_len = max(int(h["end"]) for h in SUB(endhx)["hitboxes"]) + 1
    end_at = host_len - 10                                  # End segment placed so its hitboxes fit the clip
    rr = knobs["drill_rehit"] or 6
    w1, l1 = mk_windows("0x1D5", st, until=end_at, rehit=rr, angle_fix={365: knobs["autolink_angle"]})
    w2, l2 = mk_windows(endhx, end_at)
    for w in w2: w["win"] += max(x["win"] for x in w1)
    for w in w2: w["new_hit"] = True
    emit(key, [row], w1 + w2, keep=lambda ev: ev["name"] in ("Rumble", "ftCommon_8007F5CC"), iasa=None, iasa_how="none", log=l1 + l2,
         brawl=f"0x1D3 SpecialSStart + 0x1D5 SpecialSDrill + {endhx} {SUB(endhx)['name']}",
         note=f"Start {st} frames, drill from {st + 4} rehit {rr} until {end_at}, End hitboxes at {end_at}; hammer item never spawned (no SetCmdVar 0)")
    TUNED_IASA[key] = None
    cover(key, f"0x1D3/0x1D5/{endhx}", [row], "approximated", "unsupported: native drill steering (SpecialSRush::execStatus)",
          f"drill 3 hitboxes rehit {rr} ({end_at - st - 4} frames), end hit at {end_at + 1}",
          [f"drill phase shortened to fit Kirby's {host_len}-frame hammer clip (Brawl: 45-frame drill, steerable, until wall/timeout)",
           f"autolink 365 -> fixed {knobs['autolink_angle']}", "placeholder physics: Kirby's hammer (ground: none; air: 1.5 hop, fall-special landing)"],
          ["Phase 4: steering/bounce phys (param 4020)", "v1 autolink 365", "v1 Set/Add Momentum on the air end"])
unported_events("0x1D5", "drill_rush"); unported_events("0x1D7", "drill_rush_air")
stub("v1", "drill_rush", "angle 365 autolink", "autolink hitbox extension (or keep the fixed angle)", 4)

# --- Up B: Shuttle Loop on Final Cutter (Hi1 rise <- SpecialHi, Hi2 <- SpecialHi tail + SpecialHiLoop, plunge/landing no hitbox)
hi = SUB("0x1E2"); hi_len = int(hi["anim_frames"])      # 32
for key, rows_, part in (("shuttle_loop_rise", ["SpecialHi1", "SpecialAirHi1"], 1), ("shuttle_loop_loop", ["SpecialHi2", "SpecialAirHi2"], 2)):
    rows = [MROWS_BY_NAME[n] for n in rows_]
    rlen = int(MROWS[rows[0]]["anim_frames"])            # Kirby Hi1 23, Hi2 35
    if part == 1:
        wins, log = mk_windows("0x1E2", 0, clip_to=rlen)
        body = mk_body("0x1E2", 0, clip_to=rlen)
        note = f"MK SpecialHi counters 0-{rlen - 1} on Kirby's {rlen}-frame rise"
    else:
        tail = hi_len - int(MROWS[MROWS_BY_NAME['SpecialHi1']]["anim_frames"])     # 9 frames of SpecialHi left
        w1, l1 = mk_windows("0x1E2", 0, clip_from=hi_len - tail, clip_to=hi_len)
        w2, l2 = mk_windows("0x1E4", tail, until=rlen)
        for w in w2: w["win"] += max([x["win"] for x in w1] or [0]); w["new_hit"] = True
        wins, log = w1 + w2, l1 + l2
        body = mk_body("0x1E2", 0, clip_from=hi_len - tail, clip_to=hi_len) + mk_body("0x1E4", tail)
        note = f"MK SpecialHi counters {hi_len - tail}-{hi_len - 1}, then SpecialHiLoop from counter {tail}"
    keep = lambda ev: ev["name"] in ("ftCommon_8007F5CC", "SetAirState", "Rumble") or (ev["name"] == "SetCmdVar" and ev["args"]["var"] == 3)
    emit(key, rows, wins, extra=body, keep=keep, iasa=None, iasa_how="none", log=log, brawl="0x1E2 SpecialHi" + ("" if part == 1 else " + 0x1E4 SpecialHiLoop"), note=note)
    TUNED_IASA[key] = None
    cover(key, "0x1E2 SpecialHi" + ("" if part == 1 else " + 0x1E4 SpecialHiLoop"), rows, "approximated", "restructure: Brawl 2 subactions -> Kirby Hi1/Hi2",
          note, ["path = Kirby's Final Cutter rise (root motion/code), not MK's loop", "hitboxes at MK counters"],
          ["v1 Set Air/Ground @5", "v1 Allow/Disallow Ledgegrab", "v2 glide hand-off at the loop end"])
unported_events("0x1E2", "shuttle_loop_rise"); unported_events("0x1E4", "shuttle_loop_loop")
for key, rows_, note in (("shuttle_loop_fall", ["SpecialHi3", "SpecialAirHi3"], "Kirby's plunge, no hitbox: stands in for Brawl's FallSpecial (helpless until landing / ledge)"),
                         ("shuttle_loop_land", ["SpecialHi4", "SpecialAirHiEnd"], "landing: no cutter wave (SetCmdVar 2 dropped), no GFX/SFX")):
    rows = [MROWS_BY_NAME[n] for n in rows_]
    emit(key, rows, [], keep=lambda ev: ev["name"] in ("ftCommon_8007F5CC", "Rumble"), iasa=None, iasa_how="none", brawl="0x1E5 SpecialHiEnd / FallSpecial", note=note)
    TUNED_IASA[key] = None
    cover(key, "0x1E5 SpecialHiEnd / FallSpecial", rows, "approximated", "unsupported: Brawl ends in Glide (PSA Change Action 0x85) or FallSpecial",
          note, ["fall-special ending approximated by Kirby's straight-down plunge (fast); can grab ledges"],
          ["v1 change-action escape: SpecialHiLoop end -> FallSpecial", "v2 glide (Geno action states)"])
stub("v1", "shuttle_loop_loop", "Change Action 133 (Glide) on Animation End + In Air (actions 0x114 / 0x11D)", "change-action escape -> FallSpecial now, Glide with v2", 31)
stub("v2", "shuttle_loop_loop", "Glide", "Geno action states (GlideStart/Glide/GlideAttack/GlideLanding/GlideEnd)", None)

# --- Down B: Dimensional Cape on Stone (start -> vanish (hold) -> reappear attack (end row) -> FallSpecial)
for key, rows_, hx in (("cape_start", ["SpecialLw1", "SpecialAirLwStart"], "0x1D8"),):
    rows = [MROWS_BY_NAME[n] for n in rows_]
    body = mk_body(hx, 0)
    emit(key, rows, [], extra=body, keep=lambda ev: ev["name"] == "Rumble", iasa=None, iasa_how="none", brawl=f"{hx} SpecialLwStart",
         note="no stone transform (SetCmdVar 0 dropped): Kirby wraps (Kirby's stone-start clip), intangible and hidden on MK's frames")
    TUNED_IASA[key] = None
    cover(key, f"{hx} SpecialLwStart (+0x1D9 air)", rows, "approximated", "unsupported: host = Kirby stone start",
          "BodyCollState intangible @17, FighterVis hidden @12 (MK frames)", ["Kirby's clip (29 frames vs MK 20): vanish starts at Kirby's clip end"],
          ["cape article visibility (Phase 3: cape meshes in MK's model)", "v1 Set Air/Ground @12"])
    unported_events(hx, key)
rows = [MROWS_BY_NAME["SpecialLw"], MROWS_BY_NAME["SpecialAirLw"]]
emit("cape_vanish", rows, [], extra=[(0, [(26 << 26) | 2], "BodyCollState intangible"), (0, [(37 << 26) | 1], "FighterVis hidden")],
     keep=lambda ev: False, iasa=None, iasa_how="none", brawl="(vanished: between SpecialLwStart and SpecialLw)",
     note="Kirby's stone hold (anim rate 0) reused as the vanish: intangible + hidden, fixed length = speciallw_max/min_time_in_stone; Kirby's 18% stone-drop hitbox removed")
TUNED_IASA["cape_vanish"] = None
cover("cape_vanish", "(vanish)", rows, "approximated", "unsupported: host = Kirby stone hold",
      "intangible + invisible for speciallw_max_time_in_stone frames; air sink speciallw_gravity", ["no stick-steered teleport (MK moves N/F/B)"],
      ["v1 engine-value write: position/velocity from the stick (teleport distance)", "v1 change-action: N/F/B variant from the stick"])
rows = [MROWS_BY_NAME["SpecialLwEnd"], MROWS_BY_NAME["SpecialAirLwEnd"]]
wins, log = mk_windows("0x1DC", 0)
body = mk_body("0x1DC", 0)
emit("cape_attack", rows, wins, extra=body, keep=lambda ev: ev["name"] == "Rumble", iasa=None, iasa_how="none", log=log,
     brawl="0x1DC SpecialLwF (N/B share the numbers)",
     note="reappear attack 14% on MK's frames; the end row then enters FallSpecial (speciallw_freefall_toggle = landing lag)")
TUNED_IASA["cape_attack"] = None
cover("cape_attack", "0x1DA/0x1DC/0x1DE SpecialLw N/F/B (+air)", rows, "approximated", "direct: one 2-hitbox window",
      "2 hitboxes 14% f6-7, visible + tangible again, then FallSpecial", ["neutral/back variants use the forward offsets (Brawl reverses direction first)",
      "Kirby's 31-frame stone-end clip (MK 56)", "ground reappear also ends in FallSpecial -> LandingFallSpecial"],
      ["v1 Reverse Direction (N/B variants)", "v1 SpecialLwEnd no-attack variant (Brawl: attack only if A/B held)"])
unported_events("0x1DA", "cape_attack")
cover("glide_attack", "0x3C GlideAttack", [], "stubbed-for-v2", "unsupported: glide is a Brawl-only state", "12% f5-7 translated once the Geno glide states exist",
      stub=["Geno v2 action states"])
cover("final_smash", "0x1E6.. Final*", [], "not ported", "Brawl global mechanic", "no Smash Ball in Melee")
cover("trip_attack", "0xE7 SlipAttack", [], "not ported", "Brawl global mechanic", "tripping")

# ================================================================== 5. place new scripts, repoint rows
base = (len(data) + 0x1F) & ~0x1F
data += b"\0" * (base - len(data))
mt = MD.P(root + 0xC)
for rows, words, looping in placed:
    at = len(data)
    if looping:
        words = list(words); words[-1] = at; new_relocs.append(at + 4 * (len(words) - 1))
    data += b"".join(struct.pack(">I", w) for w in words)
    for r in rows:
        po = mt + r * 0x18 + 0xC
        assert po in ar.reloc_set, (r, MROWS[r]["name"])
        put32(po, at)
changes["untouched"] += ["Attack12 / Attack13 (unreachable: no JabCombo)", "inhale capture / Eat* / swallow / spit rows (unreachable: MK hitboxes are not catch boxes)",
                         "copy-ability rows (Kirby hats): Kirby clones keep Kirby's copy code", "movement, defensive and common rows: Kirby's scripts"]

# ================================================================== 6. write HSD archive + side files
relocs = sorted(set(ar.reloc_offsets) | set(new_relocs))
tail = ar.raw[ar.o_public:]
hdr = struct.pack(">5I", 0x20 + len(data) + 4 * len(relocs) + len(tail), len(data), len(relocs), ar.nb_public, ar.nb_extern) + ar.raw[0x14:0x20]
outb = hdr + bytes(data) + b"".join(struct.pack(">I", r) for r in relocs) + tail
os.makedirs(A.out + "/files", exist_ok=True)
open(A.out + "/files/PlKb.dat", "wb").write(outb)

# geno.json: multi-jump (Geno v0) + MK special params as the v1 special-attribute override block
IR = json.load(open(os.path.join(MK, "ir", "metaknight.brawl.ir.json")))
spec_fields = IR["behavior"]["attributes"]["special"]["fields"]
blocks = collections.OrderedDict()
for f in spec_fields:
    grp = f["key"].split(".")[0]
    if grp in ("special_n", "special_s", "special_lw", "multijump", "glide"):
        blocks.setdefault(grp, collections.OrderedDict())[f["key"].split(".", 1)[1]] = f["value"]
geno = {"geno": 1, "fighters": [{
    "attach": "PlBm.dat", "name": "Meta Knight (Brawl, Phase 1)",
    "jumps": {"max": 6, "air_vy": air_vy},
    "special_attrs": {"_status": "v1 input: ignored by Geno v0 (unknown keys are hashed into the id, so peers must match). Names follow the IR "
                                 "(metaknight.brawl.ir.json); param ids are inferred (floats-then-ints numbering).",
                      "target": "meta_knight", **blocks},
    "hooks": {"on_init": [], "on_frame": [], "on_action": []}}]}
json.dump(geno, open(A.out + "/geno.json", "w"), indent=1)
changes["geno"] = {"jumps.max": 6, "air_vy": air_vy, "special_attrs": sorted(blocks)}
json.dump(changes, open(A.out + "/CHANGES.json", "w"), indent=1)
json.dump({"moves": moves_report}, open(MK + "/analysis/mk_moves.json", "w"), indent=1)
json.dump({"v1_encodings_file": A.geno_v1, "present": os.path.exists(A.geno_v1),
           "note": "Stubs are NOT in the scripts (opcode 59 would crash a non-Geno exe). When geno_v1_encodings.md exists, emit them "
                   "inline for the Geno exe build.", "stubs": stubs}, open(MK + "/analysis/v1_stubs.json", "w"), indent=1)
print("wrote", len(outb), "bytes; new scripts", len(placed), "moves", len(changes["moves"]), "coverage rows", len(moves_report), "stubs", len(stubs))
