"""Meta Knight's model visuals on the finished metaknight-slot: the eye animation (Brawl's SRT0 eye clips as Melee
SetTexAnim commands). Run by build_mk_slot.py after the effects pass (it rewrites the same scripts, append-only).

    python tools/build_mk_visuals.py [--mod mods-slot/metaknight-slot] [--dry]

Eyes: the costume files (model/tools/mkbuild) carry, per eye TObj, a matanim whose frame k is eye state k
(anim/out/eye_states.json, anim/tools/mk_eyes.py); ftData x8 lists the two eye TObjs (install_mk.py). Here every motion
row whose clip has a Brawl eye clip gets SetTexAnim(tex-anim 0 and 1, frame = state) at each frame the state changes
(op 40, ftAction_800726F4: [31:26] 40, [25] both, [24:18] idx, [17:11] idx2, [10:0] frame), merged into the row's script
without moving any existing command (effects/tools/ftscript.py insert, the effects pass's merger), and the same into the
row's Geno overlay (geno.json: overlays replace the Pl script on the Geno exe). Any old SetTexAnim (Kirby's eye frames,
inherited by Kirby-authored scripts) is dropped from a rewritten script. The engine resets both to frame 0 (state 0 =
open eyes) at every motion change (fighter.c -> ftAnim_80070654), so a clip with no events keeps open eyes.
Rows are matched by clip (their AJ offset/size -> anim/out/motion_rows.json), as the effects pass does.
Report: model/work/visuals_report.json."""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(MK, "effects", "tools")); sys.path.insert(0, os.path.join(MK, "model", "tools"))
import ftscript as FS
import install_mk as IM

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=os.path.join(MK, "mods-slot", "metaknight-slot"))
ap.add_argument("--dry", action="store_true")
A = ap.parse_args()
SETTEXANIM = 40
REP = {"eyes": {"rows": {}, "overlays": {}, "notes": []}}


def tex_word(state):
    assert 0 <= state < 1024
    return (SETTEXANIM << 26) | (1 << 25) | (0 << 18) | (1 << 11) | state


def eye_events(clip, eyes):
    """'AttackS4Start+AttackS4S' -> [(frame, state)] over the joined clip (each part's Brawl frames)."""
    out = []; off = 0; parts = clip.split("+")
    for i, n in enumerate(parts):
        c = eyes["clips"].get(n)
        if c is None:
            return None if len(parts) == 1 else out
        ev = list(c["events"])
        if i > 0 and (not ev or ev[0][0] != 0):
            # a later part starts at its own frame-0 state, which the engine does not reset between joined parts
            first = next((s for f, s in [(0, 0)] + ev if f == 0), 0)
            ev = [[0, first]] + ev
        out += [(f + off, s) for f, s in ev]
        off += c["frames"]
    return out


def inline_timed_subs(u32, cmds, rep):
    """A Subroutine whose body waits runs its waits INSIDE the caller's timeline (Kirby's blink subroutine: SetTexAnim +
    SyncWait 7 frames, called at 20 / 40 / 100 of the Wait script), but ftscript.timeline counts the call as 0 frames, so
    every event after it would be placed late. Such calls are inlined (the body's commands up to its Return, first one
    keeping the call's offset for Goto relocation); their SetTexAnim then go with the row's other old eye commands."""
    out = []
    for c in cmds:
        if c[0] == FS.SUB:
            body = FS.parse_at(u32, c[1][1])
            ops = [b[0] for b in body]
            if ops and ops[-1] == FS.RET and any(o in (FS.SYNC, FS.ASYNC) for o in ops) and                     not any(o in (FS.END, FS.SETLOOP, FS.EXECLOOP, FS.SUB, FS.GOTO) for o in ops[:-1]):
                for k, b in enumerate(body[:-1]): out.append((b[0], list(b[1]), c[2] if k == 0 else None))
                rep["inlined"] = rep.get("inlined", 0) + 1
                continue
        out.append(c)
    return out


def write_script(w, sc, new, cmds):
    """new: FS.insert output -> appended copy, Goto/Subroutine targets relocated (as build_mk_effects.rewrite_pl)."""
    pos = []; p = 0
    for cc in new: pos.append(p); p += 4 * len(cc[1])
    at = w.alloc(bytes(p), 4)
    old_off = {i: cmds[i][2] for i in range(len(cmds))}
    new_of_old = {cc[2]: at + pos[j] for j, cc in enumerate(new) if cc[2] is not None}
    first_orig = next((at + pos[j] for j, cc in enumerate(new) if cc[2] == 0), at)
    for j, cc in enumerate(new):
        for k2, word in enumerate(cc[1]): w.put(at + pos[j] + 4 * k2, word)
        if cc[0] in (FS.GOTO, FS.SUB) and cc[2] is not None:
            t = w.u32(old_off[cc[2]] + 4)
            oi = next((i for i in old_off if old_off[i] == t), None)
            if cc[0] == FS.GOTO and t == sc: nt = first_orig
            elif oi is not None: nt = new_of_old.get(oi, t)
            else: nt = t
            w.ptr(at + pos[j] + 4, nt)
    return at


def eyes(pl_path, geno_path, write):
    E = json.load(open(os.path.join(MK, "anim", "out", "eye_states.json")))
    MR = json.load(open(os.path.join(MK, "anim", "out", "motion_rows.json")))
    by_off = {(c["offset"], c["size"]): c for c in MR["clips"] + MR["extras"]}
    w = IM.Writer(open(pl_path, "rb").read())
    fd = w.ar.public([s for s, _ in w.ar.publics if s.startswith("ftData")][0]); mt = w.u32(fd + 0xC)
    G = json.load(open(geno_path)) if os.path.exists(geno_path) else None
    ovl = {s["index"]: s for s in (G["fighters"][0].get("subactions", []) if G else [])}
    done = {}; r = 0; R = REP["eyes"]
    while True:
        o = mt + r * 0x18
        if o + 0x18 > len(w.data) or r > 600: break
        sc = w.u32(o + 0xC) if (o + 0xC) in w.relocs else 0
        c = by_off.get((w.u32(o + 4), w.u32(o + 8)))
        if w.u32(o) == 0 and sc == 0 and c is None and r > 480: break
        if c is not None:
            clip = c["brawl_clip"]; frames = int(c["frames"])
            ev = eye_events(clip, E)
            if ev:
                enc = [(f, [tex_word(s)], "eye %d" % s) for f, s in ev if f < frames]
                if not sc:
                    # a row with no script: one made of the events alone (timers between them)
                    words = []; cur = 0
                    for f, ws, _ in enc:
                        if f > cur: words.append((FS.ASYNC << 26) | f); cur = f
                        words += ws
                    at = w.alloc(b"".join(x.to_bytes(4, "big") for x in words + [0]), 4)
                    w.ptr(o + 0xC, at)
                    R["rows"][r] = {"clip": clip, "frames": frames, "script": [None, hex(at)], "placed": len(enc), "dropped": []}
                else:
                    cmds = FS.parse_at(w.u32, sc)
                    key = (sc, clip)
                    if key not in done:
                        pre = {}
                        cmds = inline_timed_subs(w.u32, cmds, pre)
                        new, rep = FS.insert(cmds, enc, strip={SETTEXANIM}, clip=frames)
                        rep["inlined_subroutines"] = pre.get("inlined", 0)
                        done[key] = (write_script(w, sc, new, cmds), rep)
                    at, rep = done[key]
                    w.ptr(o + 0xC, at)
                    R["rows"][r] = {"clip": clip, "frames": frames, "script": [hex(sc), hex(at)], "placed": len(rep["placed"]),
                                    "dropped": rep["dropped"], "old_settexanim_stripped": rep["stripped"],
                                    "inlined_subroutines": rep.get("inlined_subroutines", 0)}
                if r in ovl and "words" in ovl[r]:
                    old = [int(x, 16) if isinstance(x, str) else int(x) for x in ovl[r]["words"]]
                    oc = FS.parse_words(old)
                    if any(c2[0] == FS.GOTO for c2 in oc): R["notes"].append("overlay row %d has a Goto: left alone" % r)
                    else:
                        nw, rp = FS.insert(oc, enc, strip={SETTEXANIM}, clip=frames)
                        nw, fixed = FS.fix_overlay_skips(oc, nw)
                        ovl[r]["words"] = ["0x%08X" % x for x in FS.to_words(nw)]
                        R["overlays"][r] = {"placed": len(rp["placed"]), "dropped": rp["dropped"], "skips_fixed": fixed}
        r += 1
    R["summary"] = {"rows": len(R["rows"]), "overlays": len(R["overlays"]),
                    "events_placed": sum(v["placed"] for v in R["rows"].values()),
                    "events_dropped": sum(len(v["dropped"]) for v in R["rows"].values()),
                    "states": E["n_states"], "worst_quantisation_uv": E["worst_quantisation_uv"],
                    "subroutines_inlined": sum(v.get("inlined_subroutines", 0) for v in R["rows"].values())}
    if write:
        w.save(pl_path)
        if G is not None: json.dump(G, open(geno_path, "w"), indent=1)


def main():
    f = os.path.join(A.mod, "files")
    eyes(os.path.join(f, "PlBm.dat"), os.path.join(A.mod, "geno.json"), not A.dry)
    os.makedirs(os.path.join(MK, "model", "work"), exist_ok=True)
    json.dump(REP, open(os.path.join(MK, "model", "work", "visuals_report.json"), "w"), indent=1, default=str)
    s = REP["eyes"]["summary"]
    print("   visuals: eyes %d rows + %d overlays, %d SetTexAnim placed, %d dropped (%d states, <= %.4f uv)%s" % (
        s["rows"], s["overlays"], s["events_placed"], s["events_dropped"], s["states"], s["worst_quantisation_uv"], " (dry run)" if A.dry else ""))


if __name__ == "__main__":
    main()
