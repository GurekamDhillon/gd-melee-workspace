"""Brawl Meta Knight's PSA sound events (character IR) -> timed sound events per Brawl subaction.

The sfx script of a subaction is run statically (timers, Set Loop / Execute Loop, Goto across scripts - the
'Loop Rest' + Goto-to-self loops rest until the animation loops, asynchronous timers restart from there, and are unrolled
up to the clip length, Subroutine followed when its target was
decoded) into (frame, kind, sound id):
  play   Sound Effect / Sound Effect 2 / Other Sound Effect 1+2 / Sounds 05 / Sounds 07      (keeps playing)
  trans  Sound Effect (Transient)                                                            (stops with the action)
  stop   Stop Sound Effect
  vlow   Low Voice Clip      (a random attack grunt: Melee's RandomSmashSFX + ftData sfx.smash)
  vdmg   Damage Voice Clip   (a random damage voice)
  votto  Ottotto Voice Clip  (the teeter voice)
A name can repeat (AttackS4S = three variants, two of them a Goto into the third): the variant with the most sound
events is used."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
IR_PATH = os.path.abspath(os.path.join(HERE, "..", "..", "ir", "metaknight.brawl.ir.json"))

PLAY = {"Sound Effect": "play", "Sound Effect 2": "play", "Other Sound Effect 1": "play", "Other Sound Effect 2": "play",
        "Sounds 05": "play", "Sounds 07": "play", "Sound Effect (Transient)": "trans", "Stop Sound Effect": "stop",
        "Low Voice Clip": "vlow", "Damage Voice Clip": "vdmg", "Ottotto Voice Clip": "votto"}


def load_ir(path=IR_PATH):
    d = json.load(open(path, encoding="utf-8"))
    scripts = {s["id"]: s for s in d["behavior"]["scripts"]}
    at = {}
    for s in d["behavior"]["scripts"]:
        for i, e in enumerate(s["events"]):
            at[int(e["raw"]["offset"], 16)] = (s["id"], i)
    names = d["assets"]["audio"][0]["engine"]["brawl.wii"]["names"]
    subs = {}
    for x in d["behavior"]["subactions"]:
        n = len(flatten(x, scripts, at, 10 ** 6)[0])
        if x["name"] not in subs or n > subs[x["name"]][1]:
            subs[x["name"]] = (x, n)
    return {k: v[0] for k, v in subs.items()}, scripts, at


def flatten(x, scripts, at, lim):
    """-> ([(frame, kind, id or None, engine_name)], notes)"""
    sid = x["scripts"].get("sfx")
    notes = []
    if not sid or sid not in scripts:
        return [], notes
    anim = int(x["engine"]["brawl.psa"].get("anim_frames") or 0)
    out = []; f = 0.0; base = 0.0; loops = []; stack = []; steps = 0
    cur, i = sid, 0
    while steps < 20000 and f < lim:
        steps += 1
        ev = scripts[cur]["events"]
        if i >= len(ev):
            if stack:
                cur, i = stack.pop(); continue
            break
        e = ev[i]; name = e["raw"]["engine_name"]
        a = (e.get("args") or {}).get("values") or []
        if name == "Synchronous Timer": f += a[0]; i += 1; continue
        if name == "Asynchronous Timer": f = max(f, base + a[0]); i += 1; continue
        if name == "Loop Rest 1 for Goto":             # rest until the animation loops; timers restart from there
            if anim > 0:
                f = max(f, base + anim)
            base = f; i += 1; continue
        if name == "Set Loop": loops.append([cur, i + 1, a[0]]); i += 1; continue
        if name == "Execute Loop":
            if loops:
                L = loops[-1]
                if L[2] == -1 or L[2] > 1:
                    if L[2] != -1: L[2] -= 1
                    cur, i = L[0], L[1]; continue
                loops.pop()
            i += 1; continue
        if name in ("Goto", "Subroutine"):
            t = int(a[0]["off"], 16) if a and isinstance(a[0], dict) and "off" in a[0] else None
            if t is not None and t in at:
                if name == "Subroutine": stack.append((cur, i + 1))
                cur, i = at[t]; continue
            notes.append("%s to 0x%X not decoded (f%d)" % (name, t or 0, f))
            if name == "Goto": break
            i += 1; continue
        if name == "Return":
            if stack: cur, i = stack.pop(); continue
            break
        k = PLAY.get(name)
        if k:
            sid_ = a[0] if a and isinstance(a[0], int) else None
            out.append((int(f), k, sid_, name))
        i += 1
    return [t for t in out if t[0] < lim], notes


def events(name, subs, scripts, at, clip_frames):
    x = subs.get(name)
    if x is None:
        return [], ["no Brawl subaction %s" % name]
    return flatten(x, scripts, at, clip_frames)
