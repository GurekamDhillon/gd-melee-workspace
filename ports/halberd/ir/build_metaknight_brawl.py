#!/usr/bin/env python3
"""build_metaknight_brawl.py - generate instances/metaknight.brawl.ir.json for vanilla SSBB Meta Knight.

Inputs (all local research outputs, regenerate with the tools named):
  ports/halberd/dump/*.json     BrawlLib dumps (brawl-kirby/tools/brawl_dump/bin/mdump.exe, x86):
                                             fitmk.json (+ MoveDef .bin), motionetc.json, cos00.json, brsar.json
  ports/halberd/dump/mk_bones.json, mantle_bones.json   (bone trees from cos00.json)
  ports/halberd/analysis/brawl_metaknight.json          tools/decode_mk.py (generalised from the Brawl
                                             Kirby decoder build_kirby.py: PSA decode + simulation of hit windows)
  ports/halberd/dump/rel_mk.json, sora_mk.json          tools/rel_mk.py, tools/sora_mk.py (module analysis
                                             with the doldecomp/brawl symbol lists in experiment/tooling/brawl)
The script / action conversion (conv_events, timeline) is the one from build_shadow_brawl_sate.py, extended with
simulated (loop-unrolled) hit windows from the decoder.
"""
import collections
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.normpath(os.path.join(HERE, "..", "..", "..", "experiment"))
MK = os.path.normpath(os.path.join(HERE, ".."))
DUMP = os.path.join(MK, "dump")
OUT = os.path.join(HERE, "metaknight.brawl.ir.json")
DISC = "C:/iso/brawl-extract/files/"
MELEE = "shadow.melee-ace#"

A = json.load(open(os.path.join(MK, "analysis", "brawl_metaknight.json"), encoding="utf-8"))
AM = json.load(open(os.path.join(MK, "analysis", "brawl_metaknight_model.json"), encoding="utf-8"))
REL = json.load(open(os.path.join(DUMP, "rel_mk.json"), encoding="utf-8"))
SORA = json.load(open(os.path.join(DUMP, "sora_mk.json"), encoding="utf-8"))
BONES = json.load(open(os.path.join(DUMP, "mk_bones.json")))
MANTLE_BONES = json.load(open(os.path.join(DUMP, "mantle_bones.json")))
COS = json.load(open(os.path.join(DUMP, "cos00.json"), encoding="utf-8"))
FIT = json.load(open(os.path.join(DUMP, "fitmk.json"), encoding="utf-8"))
MOVEDEF_BIN = open(os.path.join(DUMP, "fitmk.json.MoveDef_FitMetaknight.bin"), "rb").read()


def prov(conf, *ev, note=None):
    p = {"confidence": conf}
    if ev:
        p["evidence"] = list(ev)
    if note:
        p["note"] = note
    return p


def slug(s):
    return re.sub(r"[^A-Za-z0-9_]+", "_", str(s)).strip("_").lower()


def find(n, t, out):
    if n["t"] == t:
        out.append(n)
    for c in n.get("c", []):
        find(c, t, out)
    return out


EVIDENCE = [
    {"id": "ev:disc", "kind": "disc_image", "path": DISC, "revision": "RSBE01 (NTSC-U) extracted", "note": "fighter/metaknight/*, module/ft_metaknight.rel, effect/*, sound/smashbros_sound.brsar"},
    {"id": "ev:decode", "kind": "tool_output", "path": "ports/halberd/analysis/brawl_metaknight.json",
     "command": "python ports/halberd/tools/decode_mk.py", "note": A["note"][:900]},
    {"id": "ev:dump", "kind": "tool_output", "path": "ports/halberd/dump/",
     "command": "experiment/brawl-kirby/tools/brawl_dump/bin/mdump.exe <pac> <json> 60 (BrawlLib net472, x86, ParseMoveDef = true)",
     "note": "Raw BrawlLib node trees: FitMetaknight.pac (moveset + embedded ef_metaknight), FitMetaknight00.pac, FitMetaknightMotionEtc.pac, smashbros_sound.brsar (depth 8)."},
    {"id": "ev:rel", "kind": "tool_output", "path": "ports/halberd/dump/rel_mk.json", "command": "python ports/halberd/tools/rel_mk.py",
     "note": "REL sections/relocations, 700 function boundaries, 110 vtables via CodeWarrior RTTI, call graph, jump tables."},
    {"id": "ev:sora", "kind": "tool_output", "path": "ports/halberd/dump/sora_mk.json", "command": "python ports/halberd/tools/sora_mk.py",
     "note": "MK / glide classes found in sora_melee.rel (engine module) via RTTI: ftMetaknightStatusUniqProcessSpecialNSpin, ftMetaknightTransactor, ftStatusUniqProcessGlide."},
    {"id": "ev:decomp", "kind": "decomp", "path": "experiment/tooling/brawl/config/RSBE01_02/", "revision": "doldecomp/brawl 345952a3",
     "note": "symbols.txt / splits.txt for main.dol, sora_melee and ft_metaknight (function boundaries; ft_metaknight functions are unnamed fn_111_*)."},
    {"id": "ev:headers", "kind": "source_code", "path": "experiment/tooling/BrawlHeaders/Brawl/Include/",
     "note": "ft/fighter.h status kinds (Glide_Start 0x84..Glide_End 0x88, Metaknight_Final 0xEF), ft/ft_value_accesser.h param ids (Jump_Glide_Frame 23004, Glide_Type 23186, Squat_Walk_Type 23187), so/status/so_status_module_impl.h soStatusUniqProcess virtual order."},
    {"id": "ev:brawllib", "kind": "source_code", "path": "experiment/BrawlCrate/BrawlLib/SSBB/ResourceNodes/Moveset/", "note": "MoveDef parser: FDefMultiJump / MoveDefGlideNode layouts, attribute names."},
]

# ------------------------------------------------------------------ identity
IDENTITY = {
    "names": {"display": {"en": "Meta Knight"}, "internal": ["Metaknight", "FitMetaknight", "ftMetaknight", "ft_metaknight (module)", "wnMetaknightMantle (cape article)"], "series": "Kirby"},
    "indices": [
        {"space": "brawl.fighter_id", "value": 22, "stability": "stable", "provenance": prov("verified", "ev:rel", "ev:headers", note="ftClassInfoImpl<22, ftMetaknight>; ft_entry.h Fighter_MetaKnight = 0x16")},
        {"space": "brawl.module_id", "value": 111, "stability": "stable", "provenance": prov("verified", "ev:rel", note="REL header id; modules.h FT_METAKNIGHT = 111")},
        {"space": "brawl.rsar_group", "value": 683, "stability": "stable", "provenance": prov("verified", "ev:dump", note="snd/group/chara/metaknight (se); voice group [486]")},
    ],
    "lineage": [{"source": "vBrawl Meta Knight", "relation": "port_of", "extent": "retail content, no mod lineage", "provenance": prov("verified", "ev:disc")}],
    "behavior_host": {"mode": "self", "binding": "authored"},
    "provenance": prov("verified", "ev:disc"),
}

# ------------------------------------------------------------------ resources
FILE_LIST = [
    ("fighter/metaknight/FitMetaknight.pac", "fighter_data", "moveset (MoveDef_FitMetaknight) + embedded ef_metaknight effect ARC"),
    ("fighter/metaknight/FitMetaknightMotionEtc.pac", "animation_bank", "331 CHR0, 112 SRT0, 1 CLR0 + ai_metaknight (ATKD/AIPD)"),
    ("fighter/metaknight/FitMetaknightEntry.pac", "demo_animation", "entry (Halberd) article"),
    ("fighter/metaknight/FitMetaknightFinal.pac", "other", "Final Smash (Galaxia Darkness) resources"),
    ("fighter/metaknight/FitMetaknightResult.pac", "result_animation", "results-screen anims"),
    ("fighter/metaknight/FitMetaknightSpy.pac", "costume_model", "Spycloak (invisible) model"),
    ("fighter/metaknight/FitMetaknightSpy.pcs", "costume_model", "Spycloak, compressed variant"),
    ("fighter/metaknight/FitMetaknightDark.pac", "costume_model", "SSE dark (shadow-bug) variant"),
    ("fighter/metaknight/FitMetaknightDark.pcs", "costume_model", "SSE dark, compressed variant"),
    ("module/ft_metaknight.rel", "module", "fighter module id 111"),
    ("effect/fighter/ef_metaknight.pac", "effect_bank", "standalone copy of the effect ARC also embedded in FitMetaknight.pac"),
    ("effect/final/ef_FinMetaknight.pac", "effect_bank", "Final Smash effects"),
    ("fighter/kirby/FitKirbyMetaknight.pac", "copy_ability", "Kirby's MK hat moveset (belongs to Kirby; integration only)"),
    ("fighter/kirby/FitKirbyMetaknight00.pac", "copy_ability", "Kirby's MK hat model (Kirby-owned)"),
    ("fighter/kirby/FitKirbyMetaknightSpy.pac", "copy_ability", "Kirby's MK hat, Spycloak (Kirby-owned)"),
    ("effect/kirby_cp/ef_KbMetaknight.pac", "copy_ability", "Kirby copy effects (Kirby-owned)"),
    ("toy/fig/MetaknightR1.brres", "trophy", "trophy model"),
    ("movie/End_Metaknight.thp", "movie", "classic/all-star ending movie"),
]
for n in range(6):
    FILE_LIST.append((f"fighter/metaknight/FitMetaknight{n:02d}.pac", "costume_model", f"costume {n:02d} (model + textures + cape article model + article anims)"))
    FILE_LIST.append((f"fighter/metaknight/FitMetaknight{n:02d}.pcs", "costume_model", f"costume {n:02d}, compressed variant (loaded when memory is tight: SSE/teams)"))
FILES, FID = [], {}
for path, role, note in FILE_LIST:
    fid = "file:" + slug(os.path.basename(path))
    ext = path.rsplit(".", 1)[-1].lower()
    fmt = {"pac": "arc_pac", "pcs": "arc_pac", "rel": "rel_module", "brres": "brres", "thp": "thp"}.get(ext, "other")
    c = {"format": fmt, "endianness": "big"}
    if ext == "pcs":
        c["compression"] = "lz77"
    full = DISC + path
    FILES.append({"id": fid, "name": os.path.basename(path), "role": role, "size": os.path.getsize(full) if os.path.exists(full) else 0,
                  "local_path": full, "container": c, "provenance": prov("verified", "ev:disc", note=note)})
    FID[path] = fid
F_MOVESET, F_MOTION, F_MODULE, F_EF = FID["fighter/metaknight/FitMetaknight.pac"], FID["fighter/metaknight/FitMetaknightMotionEtc.pac"], FID["module/ft_metaknight.rel"], FID["effect/fighter/ef_metaknight.pac"]

# ------------------------------------------------------------------ assets: skeleton
names = [b["name"] for b in BONES]
ROLE_OF = {"TopN": "root", "TransN": "trans", "HipN": "hip", "BodyN": "body", "BodyBN": "head", "LHandN": "hand_l", "RHandN": "hand_r", "LHaveN": "item_l",
           "RHaveN": "item_r", "SwordM": "weapon", "LFootJ": "foot_l", "RFootJ": "foot_r", "ThrowN": "throw", "LShoulderJ": "shoulder_l", "RShoulderJ": "shoulder_r",
           "LLegJ": "leg_l", "RLegJ": "leg_r", "LKneeJ": "knee_l", "RKneeJ": "knee_r", "LArmJ": "arm_l", "RArmJ": "arm_r", "XRotN": "x_rot", "YRotN": "y_rot"}
VIS = {"MantM": "closed cape (wrapped) mesh set", "WingM": "bat wings mesh set", "SwordM": "sword mesh set (also the blade bone)", "metaMantleM": "open mantle mesh set"}
joints = []
for b in BONES:
    tr = []
    if b["index"] == 0:
        tr.append("skeleton_root")
    if b["name"] in VIS:
        tr.append("visibility_gate")
    if b["name"] in ("LHaveN", "RHaveN"):
        tr.append("item_hold")
    if b["name"] == "ThrowN":
        tr.append("throw_anchor")
    j = {"index": b["index"], "name": b["name"], "parent": names.index(b["parent"]) if b["parent"] in names else None}
    if b.get("translation"):
        j["rest"] = {"translation": [float(x) for x in b["translation"].strip("()").split(",")]}
    if tr:
        j["traits"] = tr
    if b["name"] in ROLE_OF:
        j["role_guess"] = ROLE_OF[b["name"]]
    joints.append(j)
SKEL = {"id": "skel:main", "name": "FitMetaknight00 boneset", "joint_count": len(joints), "order": "depth_first", "joints": joints,
        "provenance": prov("verified", "ev:dump", note="Same 77 bones in all six costumes (checked in 00; 01-05 are same-size texture swaps). Chains: 16 cape bones "
                                                         "(Mantbase/Ceri/Cmant/Leri/Lmant/Reri/Rmant), 22 wing bones (Wingbase, L/R wing M/A/B/C), 4 visibility gate bones "
                                                         "(MantM, WingM, SwordM, metaMantleM). Hitbox/hurtbox/GFX bone numbers in the moveset are these MDL0 indices directly.")}
MSKEL = {"id": "skel:mantle", "name": "WpnMetaknightMantle boneset", "joint_count": len(MANTLE_BONES), "order": "depth_first",
         "joints": [{"index": b["index"], "name": b["name"], "parent": [x["name"] for x in MANTLE_BONES].index(b["parent"]) if b["parent"] else None} for b in MANTLE_BONES],
         "provenance": prov("verified", "ev:dump", note="Cape article (Dimensional Cape / shield / dodge wrap): TopN, HaveN, RotN + 25 mantle cloth bones.")}
ROLES = [{"role": r, "joint": names.index(n), "skeleton": "skel:main", "provenance": prov("inferred", "ev:dump", note=f"bone '{n}'")} for n, r in ROLE_OF.items() if n in names]

# ------------------------------------------------------------------ models / materials / textures
mdls = {m["n"]: m for m in find(COS, "MDL0Node", [])}
MODELS, MATS, TEX = [], [], []
for mname, role, skel in [("FitMetaknight00", "body", "skel:main"), ("FitMetaknightShd", "drop_shadow", "skel:main"), ("WpnMetaknightMantle", "other", "skel:mantle"), ("WpnMetaknightMantleShd", "drop_shadow", "skel:mantle")]:
    m = mdls[mname]
    objs = find(m, "MDL0ObjectNode", [])
    meshes = []
    for i, o in enumerate(objs):
        q = o["p"]
        draws = []
        for dc in q.get("DrawCalls") or []:
            mm = re.match(r"(OPA|XLU) \d+: (\S+) (\S+)", dc)
            if mm:
                draws.append({"material": mm.group(2), "visibility_bone": mm.group(3), "pass": {"OPA": "opaque", "XLU": "translucent"}[mm.group(1)]})
        me = {"index": i, "name": o["n"], "vertices": q.get("VertexCount"), "faces": q.get("FaceCount"), "draws": draws}
        sb = q.get("SingleBind")
        me["single_bind"] = None if sb in (None, "(none)") else sb
        meshes.append(me)
    MODELS.append({"id": "model:" + slug(mname), "name": mname, "role": role, "skeleton": skel, "shared_by_costumes": True, "meshes": meshes,
                   "stats": {"meshes": len(meshes)}, "provenance": prov("verified", "ev:dump", note="role 'other' = the wnMetaknightMantle article model" if mname == "WpnMetaknightMantle" else None)})
    for mat in find(m, "MDL0MaterialNode", []):
        q = mat["p"]
        mid = "mat:" + slug(mname) + "." + slug(mat["n"])
        if any(x["id"] == mid for x in MATS):
            continue
        layers = [{"texture_slot": r["n"], "coord_source": r["p"].get("MapMode"), "wrap": [str(r["p"].get("UWrapMode", "")).lower().replace("repeat", "repeat") if str(r["p"].get("UWrapMode", "")).lower() in ("clamp", "repeat", "mirror") else "repeat",
                                                                                         str(r["p"].get("VWrapMode", "")).lower() if str(r["p"].get("VWrapMode", "")).lower() in ("clamp", "repeat", "mirror") else "repeat"]}
                  for r in mat.get("c", []) if r["t"] == "MDL0MaterialRefNode"]
        MATS.append({"id": mid, "name": mat["n"], "shading": {"alpha": "blend" if q.get("XLUMaterial") else "opaque",
                                                              "cull": {"Cull_Inside": "back", "Cull_Outside": "front", "Cull_None": "none", "Cull_All": "both"}.get(q.get("CullMode"), "unknown")},
                     "layers": layers, "provenance": prov("verified", "ev:dump"),
                     **({"variant_of": "mat:" + slug(mname) + "." + slug(mat["n"][:-7]), "variant_role": "metal"} if mat["n"].endswith("_ExtMtl") else {})})
for t in find(COS, "TEX0Node", []):
    q = t["p"]
    TEX.append({"id": "tex:" + slug(t["n"]), "name": t["n"], "width": q.get("Width"), "height": q.get("Height"), "format": str(q.get("Format")),
                "mipmaps": q.get("LevelOfDetail", 1) or 1, "provenance": prov("verified", "ev:dump", note="FitMetaknight00.pac Texture Data[0]")})
PARTVIS = [{"id": "vis:main", "driver": "visibility_bones",
            "parts": [{"part": k, "semantic": s, "gate_bone": b} for k, (b, s) in enumerate(VIS.items())],
            "provenance": prov("verified", "ev:dump", "ev:decode", note="Draw calls are gated by bone visibility; PSA 'Model Changer' / 'Visibility' events (e.g. Attack100Start Model Changer 2 -> 0) toggle them: closed cape vs wings vs open mantle.")}]

COSTUMES = []
for n in range(6):
    COSTUMES.append({"id": f"costume:{n:02d}", "index": {"space": "brawl.costume_file_id", "value": n}, "name": f"FitMetaknight{n:02d}",
                     "files": [FID[f"fighter/metaknight/FitMetaknight{n:02d}.pac"], FID[f"fighter/metaknight/FitMetaknight{n:02d}.pcs"]],
                     "model": "model:fitmetaknight00", "kind": "base" if n == 0 else "texture_swap",
                     "provenance": prov("verified" if n == 0 else "inferred", "ev:disc", "ev:dump", note=None if n == 0 else "same byte size (1,071,872) as 00; assumed texture/palette swap, not diffed")})
COSTUMES.append({"id": "costume:dark", "index": {"space": "brawl.costume_file_id", "value": 100}, "name": "FitMetaknightDark", "files": [FID["fighter/metaknight/FitMetaknightDark.pac"], FID["fighter/metaknight/FitMetaknightDark.pcs"]],
                 "kind": "mixed", "provenance": prov("inferred", "ev:disc", note="SSE shadow-bug variant; index value is a placeholder (no numeric costume id)")})
COSTUMES.append({"id": "costume:spy", "index": {"space": "brawl.costume_file_id", "value": 101}, "name": "FitMetaknightSpy", "files": [FID["fighter/metaknight/FitMetaknightSpy.pac"], FID["fighter/metaknight/FitMetaknightSpy.pcs"]],
                 "kind": "mixed", "provenance": prov("inferred", "ev:disc", note="Spycloak item transparency model; index value is a placeholder")})

# ------------------------------------------------------------------ animations
mo = AM["motion"]
motion_tree = json.load(open(os.path.join(DUMP, "motionetc.json"), encoding="utf-8"))
chr0 = {c["n"]: c for c in find(motion_tree, "CHR0Node", [])}
srt0 = find(motion_tree, "SRT0Node", [])
clr0 = find(motion_tree, "CLR0Node", [])
used_by = collections.defaultdict(list)
for s in A["subactions"]["list"]:
    if s["anim"]:
        used_by[s["name"]].append(f"subaction:{s['index']}")
CLIPS, clip_by_name = [], {}
for name, fr in mo["frames"].items():
    cid = "clip:" + slug(name)
    c = chr0.get(name, {"p": {}})
    clip = {"id": cid, "name": name, "file": F_MOTION, "frames": fr, "loop": bool(c["p"].get("Loop")),
            "tracks": {"per_channel": {"bones": len(c.get("c", []))}}, "provenance": prov("verified", "ev:dump")}
    if used_by.get(name):
        clip["used_by"] = sorted(set(used_by[name]))[:12]
    CLIPS.append(clip)
    clip_by_name[name] = cid
for s in srt0:
    CLIPS.append({"id": "clip:srt0." + slug(s["n"]), "name": s["n"], "file": F_MOTION, "frames": s["p"].get("FrameCount"), "loop": bool(s["p"].get("Loop")),
                  "provenance": prov("verified", "ev:dump", note="SRT0 texture-matrix animation (eye/texture scroll)")})
for s in clr0:
    CLIPS.append({"id": "clip:clr0." + slug(s["n"]), "name": s["n"], "file": F_MOTION, "frames": s["p"].get("FrameCount"), "loop": bool(s["p"].get("Loop")),
                  "provenance": prov("verified", "ev:dump", note="CLR0 material colour animation")})
mantle_anims = [c["n"] for c in find(COS, "CHR0Node", [])]
for n in mantle_anims:
    CLIPS.append({"id": "clip:mantle." + slug(n), "name": n, "file": FID["fighter/metaknight/FitMetaknight00.pac"], "authored_for": {"skeleton": "skel:mantle"},
                  "provenance": prov("verified", "ev:dump", note="cape article (WpnMetaknightMantle) animation, stored in each costume pac")})

# ------------------------------------------------------------------ effects
efarc = [c for c in FIT["c"] if c["n"] == "ef_metaknight"][0]
efls = [e["n"] for e in find(efarc, "EFLSEntryNode", [])]
reff = [e["n"] for e in find(efarc, "REFFEntryNode", [])]
eftex = [e["n"] for e in find(efarc, "TEX0Node", [])]
efmdl = [e["n"] for e in find(efarc, "MDL0Node", [])]
gfx_uses = collections.defaultdict(list)
for s in A["subactions"]["list"]:
    for fr, n, args in s["gfx"]:
        if isinstance(args, dict):
            g = args.get("Graphic")
            if isinstance(g, dict):
                gfx_uses[("ext", g.get("gfx_file"), g.get("efls_index"))].append(f"subaction:{s['index']}")
            elif g is not None:
                gfx_uses[("common", g)].append(f"subaction:{s['index']}")
EFFECTS = [{"id": "fxbank:ef_metaknight", "file": F_EF, "owner": "self",
            "id_scheme": "External Graphic Effect args {gfx_file: 'Meta Knight' (ef_metaknight), efls_index: n}; common effects use plain Graphic ids (ef_common)",
            "models": [{"name": m} for m in efmdl] if False else None,
            "generators": [{"local_index": i, "used_by": sorted(set(gfx_uses.get(("ext", "Meta Knight", i), [])))[:8]} for i, n in enumerate(efls) if gfx_uses.get(("ext", "Meta Knight", i)) or n != "<null>"],
            "provenance": prov("verified", "ev:dump", "ev:decode", note=f"EFLS {len(efls)} entries ({', '.join(n for n in efls if n != '<null>')} named), REFF emitters {reff}, "
                                                                        f"REFT textures {len([e for e in find(efarc, 'REFTEntryNode', [])])}, {len(eftex)} TEX0, {len(efmdl)} effect models ({', '.join(efmdl[:8])}...). "
                                                                        f"Distinct external effect uses in scripts: {len([k for k in gfx_uses if k[0] == 'ext'])}; common graphic ids used: {len([k for k in gfx_uses if k[0] == 'common'])}.")}]
EFFECTS[0].pop("models")
EFFECTS.append({"id": "fxbank:ef_finmetaknight", "file": FID["effect/final/ef_FinMetaknight.pac"], "owner": "self", "provenance": prov("verified", "ev:disc", note="Final Smash effects; not decoded")})

# ------------------------------------------------------------------ audio (BRSAR names for PSA sound ids)
brsar = json.load(open(os.path.join(DUMP, "brsar.json"), encoding="utf-8"))
snd = {}


def walk_snd(n, path):
    p = path + [n["n"]]
    if n["t"] == "RSARSoundNode":
        snd[n["p"]["InfoIndex"]] = dict(name="/".join(p[1:]), file=n["p"].get("SoundFile"))
    for c in n.get("c", []):
        walk_snd(c, p)


walk_snd(brsar, [])
SFX_EV = ("Sound Effect", "Sound Effect 2", "Sound Effect (Transient)", "Other Sound Effect 1", "Other Sound Effect 2", "Low Voice Clip", "Damage Voice Clip", "Ottotto Voice Clip", "Stop Sound Effect")
snd_uses = collections.defaultdict(set)
for s in A["subactions"]["list"]:
    for fr, n, args in s["sfx"] + s["main_timeline"] + s["other"]:
        if n in SFX_EV and isinstance(args, dict):
            v = next((x for x in args.values() if isinstance(x, int)), None)
            if v is not None:
                snd_uses[v].add(f"subaction:{s['index']}")
mk_se = sorted(k for k, v in snd.items() if "chara/metaknight" in str(v["file"]))
AUDIO = [{"id": "sfxbank:metaknight", "index": {"space": "brawl.rsar_group", "value": 683},
          "id_scheme": "PSA sound ids are smashbros_sound.brsar sound InfoIndex values (global); MK's own sounds are in groups [683] snd/group/chara/metaknight (se, 109 sounds) and [486] (voice, 47).",
          "sound_events": [{"event_id": k, "used_by": sorted(snd_uses[k])[:10]} for k in sorted(snd_uses)],
          "engine": {"brawl.wii": {"names": {str(k): snd[k]["name"] for k in sorted(snd_uses) if k in snd},
                                   "own_sounds": len(mk_se), "own_sound_names_sample": [snd[k]["name"] for k in mk_se[:20]]}},
          "provenance": prov("verified", "ev:dump", "ev:decode", note=f"{len(snd_uses)} distinct sound ids used by MK scripts; {sum(1 for k in snd_uses if k in snd)} resolved to BRSAR names. Samples (RWSD waves) not extracted.")}]
UI = [{"id": "ui:css_portrait", "role": "css_portrait", "provenance": prov("assumed", "ev:disc", note="In shared menu archives (menu2/sc_selcharacter*, info*, char_bust_tex); not extracted in this pass.")},
      {"id": "ui:stock_icon", "role": "stock_icon", "provenance": prov("assumed", "ev:disc", note="In shared info/stock archives; not extracted.")},
      {"id": "ui:announcer", "role": "announcer_call", "provenance": prov("verified", "ev:dump", note="snd/group/narration/characall entry")}]
MEDIA = [{"id": "media:ending", "kind": "movie", "purpose": "ending movie", "file": FID["movie/End_Metaknight.thp"], "provenance": prov("verified", "ev:disc")}]
COLLECT = [{"id": "collectible:trophy", "kind": "trophy", "file": FID["toy/fig/MetaknightR1.brres"], "origin": "retail", "provenance": prov("verified", "ev:disc")}]

# ------------------------------------------------------------------ attributes
KEYMAP = {"Walk Initial Velocity": "ground.walk.initial_speed", "Walk Acceleration": "ground.walk.accel", "Walk Maximum Velocity": "ground.walk.max_speed",
          "Stopping Velocity": "ground.friction", "Dash & StopTurn Initial Velocity": "ground.dash.initial_speed", "Run Initial Velocity": "ground.run.max_speed",
          "Jump Startup Time": "jump.squat_frames", "Jump H Initial Velocity": "jump.h_initial", "Jump V Initial Velocity": "jump.v_initial",
          "Ground to Air Jump Momentum Multiplier": "jump.ground_momentum_mul", "Jump H Maximum Velocity": "jump.h_max", "Hop V Initial Velocity": "jump.short_hop_v",
          "Air Jump Multiplier": "jump.air_v_mul", "Jumps": "jump.count", "Gravity": "air.gravity", "Terminal Velocity": "air.terminal_velocity",
          "Air Mobility": "air.drift_mul", "Air Stopping Mobility": "air.drift_base", "Maximum H Air Velocity": "air.max_speed", "Horizontal Momentum Decay": "air.friction",
          "Fastfall Terminal Velocity": "air.fast_fall_velocity", "Glide Frame Window": "glide.jump_hold_frames", "Weight": "body.weight", "Size": "body.model_scale",
          "Shield Size": "shield.size", "Shield Break Bounce Velocity": "shield.break_velocity", "Normal Landing Lag": "landing.normal_frames",
          "Nair Landing Lag?": "landing.nair_frames", "Fair Landing Lag?": "landing.fair_frames", "Bair Landing Lag?": "landing.bair_frames",
          "Uair Landing Lag?": "landing.uair_frames", "Dair Landing Lag": "landing.dair_frames", "Walljump H Velocity": "walljump.h_velocity", "Walljump V Velocity": "walljump.v_velocity"}
ATTRS, used = [], set()
for a in A["attributes"]:
    n = a["name"]
    if re.match(r"^\*?0x[0-9A-Fa-f]+$", n):
        k = "unknown." + n.lstrip("*").lower()
    else:
        k = KEYMAP.get(n, "brawl." + slug(n))
    if k in used:
        k = f"{k}_{a['index']}"
    used.add(k)
    at = {"key": k, "offset": "0x%X" % int(a["offset"], 16), "engine_name": n, "value": a["value"], "type": "s32" if a["type"] == "int" else "f32", "provenance": prov("verified", "ev:decode")}
    if a.get("description"):
        at["meaning"] = a["description"][:300]
    if n == "Jumps":
        at["meaning"] = "Total jumps including the ground jump: 6 = 1 ground + 5 midair."
    if n == "Glide Frame Window":
        at["meaning"] = "Frames the jump button must be held after a midair jump to enter glide (param Customize_Param_Int_Jump_Glide_Frame 23004)."
        at["provenance"] = prov("verified", "ev:decode", "ev:headers")
    ATTRS.append(at)

# special: param blocks (ftMetaknight extend params), multijump, glide
PB = {p["name"].split("__")[0]: p for p in A["param_blocks"] if p["name"].startswith("param")}
SORA_FN = {}
for v in SORA:
    for k, s in enumerate(v["slots"]):
        if s.get("size", 0) > 8:
            SORA_FN[(v["class_name"], k)] = s
UNIQ_SLOTS = ["dtor", "initStatus", "exitStatus", "execStatus", "execStop", "execMapCorrection", "execFixPosCounter", "execFixPos", "execFixCamera", "checkDamage",
              "checkAttack", "onChangeLr", "leaveStop", "checkTransitionPrecede"]
# ftMetaknightExtendParamAccesser = ftExtendParamAccesserEx<3999, 27, 23999, 8>: 27 float ids 4000.., 8 int ids 24000..
# Inferred numbering: floats then ints, in block order N, S, Lw, Final (trailing zero word of N/S/Final = padding).
blocks = [("special_n", "paramSpecialN"), ("special_s", "paramSpecialS"), ("special_lw", "paramSpecialLw"), ("final", "paramFinal")]
fid_next, iid_next = 4000, 24000
SPECIAL = []
READS = {4012: ("sora", "ftMetaknightStatusUniqProcessSpecialNSpin", 3), 4013: ("sora", "ftMetaknightStatusUniqProcessSpecialNSpin", 3),
         4014: ("sora", "ftMetaknightStatusUniqProcessSpecialNSpin", 3), 4015: ("sora", "ftMetaknightStatusUniqProcessSpecialNSpin", 3),
         24000: ("sora", "ftMetaknightStatusUniqProcessSpecialNSpin", 3), 4020: ("mk", "fn_111_C710", None), 24005: ("mk", "fn_111_CCD8", None)}
MEANING = {"special_n": "Mach Tornado", "special_s": "Drill Rush", "special_lw": "Dimensional Cape", "final": "Galaxia Darkness"}
for key, bname in blocks:
    p = PB[bname]
    raw = bytes.fromhex(p["raw"])
    nwords = len(raw) // 4
    for i in range(nwords):
        w = raw[4 * i:4 * i + 4]
        iv = struct.unpack(">i", w)[0]
        is_int = -100000 < iv < 100000
        last_pad = (i == nwords - 1 and iv == 0 and key != "special_lw")
        if last_pad:
            SPECIAL.append({"key": f"{key}.w{i:02d}", "offset": "0x%X" % (4 * i), "engine_name": bname + f"[{i}]", "value": 0, "type": "s32",
                            "meaning": "padding / unused (not counted by the param accesser)", "provenance": prov("inferred", "ev:decode", "ev:rel")})
            continue
        if is_int:
            pid, iid_next = iid_next, iid_next + 1
            val, typ = iv, "s32"
        else:
            pid, fid_next = fid_next, fid_next + 1
            val, typ = float("%.6g" % struct.unpack(">f", w)[0]), "f32"
        at = {"key": f"{key}.w{i:02d}", "offset": "0x%X" % (4 * i), "engine_name": f"{bname}[{i}] (param id {pid}, inferred)", "value": val, "type": typ,
              "meaning": MEANING[key] + " parameter", "provenance": prov("verified", "ev:decode", note="value verified; the param id numbering is inferred")}
        r = READS.get(pid)
        if r:
            if r[0] == "sora":
                at["read_by"] = [f"fn:sora.{SORA_FN[(r[1], r[2])]['name']}"]
                at["meaning"] += f"; read by {r[1]}::{UNIQ_SLOTS[r[2]]} (sora_melee) via soValueAccesser id {pid}"
            else:
                at["read_by"] = [f"fn:{r[1]}"]
                at["meaning"] += f"; read by module function {r[1]} via soValueAccesser id {pid}"
        SPECIAL.append(at)
# multijump
mj_off = A["misc_section"]["MultiJumpOffset"]
BASE = 0x20
h = struct.unpack(">4f3I", MOVEDEF_BIN[BASE + mj_off:BASE + mj_off + 28])
hops = [round(x, 4) for x in struct.unpack(">%df" % ((mj_off - h[4]) // 4), MOVEDEF_BIN[BASE + h[4]:BASE + mj_off])]
unks = [round(x, 4) for x in struct.unpack(">%df" % ((h[4] - h[5]) // 4), MOVEDEF_BIN[BASE + h[5]:BASE + h[4]])]
for k, (nm, v, mean) in enumerate([("multijump.unk1", h[0], None), ("multijump.unk2", h[1], None), ("multijump.unk3", h[2], None),
                                    ("multijump.horizontal_boost", h[3], "BrawlLib name HorizontalBoost"),
                                    ("multijump.turn_frames", h[6], "BrawlLib name TurnFrames (inline int, 12)")]):
    SPECIAL.append({"key": nm, "offset": "0x%X" % mj_off, "engine_name": "Misc MultiJump " + nm.split(".")[1], "value": round(v, 4) if isinstance(v, float) else v,
                    "type": "f32" if isinstance(v, float) else "s32", **({"meaning": mean} if mean else {}), "provenance": prov("verified", "ev:decode", "ev:brawllib")})
SPECIAL.append({"key": "multijump.hop_velocities", "offset": "0x%X" % h[4], "engine_name": "Misc MultiJump Hops", "value": hops, "type": "blob",
                "meaning": "Vertical velocity of midair jumps 1..5 (decreasing: 2.2, 2.1, 2.0, 1.88, 1.75). Five entries = five midair jumps; the common 'Air Jump Multiplier' is 0.",
                "provenance": prov("verified", "ev:decode", "ev:brawllib", note="meaning inferred from count and shape")})
SPECIAL.append({"key": "multijump.unk_list", "offset": "0x%X" % h[5], "engine_name": "Misc MultiJump Unks", "value": unks, "type": "blob",
                "meaning": "12 values 15..180 step 15 (unknown; looks like an angle/turn table paired with turn_frames = 12)", "provenance": prov("verified", "ev:decode")})
gl = A["misc_blocks"]["glide"]["words"]
GL_MEAN = {0: "max glide angle up (degrees, inferred)", 1: "max glide angle down (degrees, inferred)"}
for i, v in enumerate(gl[:22]):
    SPECIAL.append({"key": f"glide.w{i:02d}", "offset": "0x%X" % (A["misc_section"]["GlideOffset"] + 4 * i), "engine_name": f"Misc Glide Entries[{i}]" if i < 20 else f"Misc Glide Int{i - 19}",
                    "value": v, "type": "f32" if i < 20 else "s32", **({"meaning": GL_MEAN[i]} if i in GL_MEAN else {}),
                    "provenance": prov("verified", "ev:decode", "ev:brawllib", note="read by the common ftStatusUniqProcessGlide (sora_melee); field names unknown in BrawlLib/OpenSA3")})
ATTRIBUTES = {"common": ATTRS, "special": {"size": sum(len(bytes.fromhex(PB[b]["raw"])) for _, b in blocks) + 28 + 0x58,
                                          "location": {"kind": "source_range", "path": DISC + "fighter/metaknight/FitMetaknight.pac", "note": "MoveDef data: paramSpecialN/S/Lw/Final__16ftMetaknightNode, Misc MultiJump, Misc Glide"},
                                          "fields": SPECIAL, "coverage": "all words decoded; meanings: jump count, glide window, 5 hop velocities, 2 glide angles (inferred), which param ids the MK code reads; the rest unnamed"}}

# ------------------------------------------------------------------ scripts / subactions / actions
OPS = {"Asynchronous Timer": "timer.async_wait", "Synchronous Timer": "timer.sync_wait", "Set Loop": "loop.begin", "Execute Loop": "loop.end",
       "Subroutine": "control.subroutine", "Return": "control.return", "Goto": "control.goto", "Else": "control.else", "End If": "control.end_if",
       "Offensive Collision": "hitbox.create", "Special Offensive Collision": "hitbox.create", "Thrown Collision": "hitbox.create", "Terminate Collisions": "hitbox.clear", "Delete Hitbox": "hitbox.remove",
       "Change Hitbox Damage": "hitbox.adjust_damage", "Change Hitbox Size": "hitbox.adjust_size",
       "Body Collision": "body.state", "Sound Effect": "sfx.play", "Sound Effect 2": "sfx.play", "Sound Effect (Transient)": "sfx.play", "Other Sound Effect 1": "sfx.play",
       "Other Sound Effect 2": "sfx.play", "Low Voice Clip": "sfx.play", "Damage Voice Clip": "sfx.play", "Ottotto Voice Clip": "sfx.play",
       "Stop Sound Effect": "sfx.stop", "Graphic Effect": "gfx.spawn", "External Graphic Effect": "gfx.spawn", "Terminate Graphic Effect": "gfx.remove",
       "Allow Interrupt": "interrupt.enable", "Rumble": "rumble", "Frame Speed Modifier": "timer.set_anim_rate", "Bit Variable Set": "var.flag",
       "Bit Variable Clear": "var.flag", "Float Variable Set": "var.set", "Int Variable Set": "var.set", "Int Variable Add": "var.add", "Float Variable Add": "var.add",
       "Visibility": "model.visibility", "Model Changer 1": "model.part_state", "Model Changer 2": "model.part_state",
       "Set Momentum": "move.velocity", "Add/Subtract Character Momentum": "move.velocity", "Throw Specifier": "throw.set", "Throw Collision": "throw.set",
       "Grab Collision": "grab.box", "Article Generate": "article.spawn", "Generate Article": "article.spawn", "Set Air/Ground": "air.state", "Reverse Direction": "move.reverse"}
ELEM = {"Normal": "normal", "Fire": "fire", "Electric": "electric", "Slash": "slash", "Coin": "coin", "Ice": "ice", "Sleep": "sleep", "Grounded": "grounded",
        "Cape": "cape", "Empty": "empty", "Disable": "disable", "Darkness": "darkness", "Paralyze": "paralyze", "Flower": "flower", "Aura": "aura"}


def conv_events(evs):
    out = []
    for e in evs:
        n = e["name"] or "unknown"
        op = OPS.get(n)
        if op is None:
            op = "control.if" if n.startswith("If") else "engine." + (slug(n) or "unknown")
        ev = {"op": op, "raw": {"opcode": "0x" + e["id"], "engine_name": n, "offset": e["off"]}}
        if e.get("frame") is not None:
            ev["frame"] = e["frame"]
        if e.get("args"):
            ev["args"] = {"values": e["args"]}
        h = e.get("hitbox")
        if h:
            hb = {"slot": h.get("id"), "joint": h.get("bone"), "joint_role": h.get("bone_name"), "damage": h.get("damage"), "angle": h.get("angle"),
                  "angle_kind": "sakurai" if h.get("angle") == 361 else ("autolink" if h.get("angle") in (365, 366, 367) else "fixed"),
                  "knockback_growth": h.get("kbg"), "weight_dependent_set_knockback": h.get("wdsk"),
                  "base_knockback": h.get("bkb"), "size": h.get("size"), "offset": h.get("offset"), "element": ELEM.get(h.get("element"), "other"),
                  "shield_damage": h.get("shield_damage"), "targets": {"ground": bool(h.get("ground", True)), "air": bool(h.get("air", True))},
                  "flags": [x for x, on in [("clank", h.get("clang")), ("direct", h.get("direct"))] if on],
                  "engine": {"brawl.psa": {k: h[k] for k in ("hitlag_mult", "sdi_mult", "trip_rate", "sfx", "hit_type", "flags_hex", "rehit_rate", "special_flags") if h.get(k) is not None}}}
            ev["hitbox"] = {k: v for k, v in hb.items() if v is not None}
        out.append(ev)
    return out


def sim_timeline(s, evs):
    """hit windows from the decoder's loop-unrolled simulation (0-based [start,end) -> 1-based [start+1, end])."""
    t = {"static": not any(e["op"] in ("control.goto", "loop.begin", "control.if") for e in evs)}
    wins = collections.OrderedDict()
    for h in s["hitboxes"]:
        key = (h["start"], h["end"])
        w = wins.setdefault(key, {"start": h["start"] + 1, "end": h["end"] if h["end"] is not None else s["script_end_frame"], "slots": [], "damage": []})
        w["slots"].append(h["id"])
        w["damage"].append(h["damage"])
    if wins:
        t["hit_windows"] = list(wins.values())
    if s["iasa_frame"] is not None:
        t["interruptible_from"] = s["iasa_frame"] + 1
    if s["script_end_frame"] is not None:
        t["length"] = s["script_end_frame"]
    return t


SCRIPTS, SUBACTIONS = [], []
HB_COUNT = 0
for s in A["subactions"]["list"]:
    i = s["index"]
    chans = {}
    for ch, evs in s["channels_raw"].items():
        if not evs:
            continue
        sid = f"script:sa.{i}.{ch}"
        e = conv_events(evs)
        sc = {"id": sid, "language": "brawl.psa", "location": {"file": F_MOVESET}, "role": "subaction_" + ch, "events": e, "provenance": prov("verified", "ev:decode")}
        if ch == "main":
            sc["timeline"] = sim_timeline(s, e)
            HB_COUNT += len(s["hitboxes"])
            if s["sim_notes"]:
                sc["provenance"]["note"] = "simulation: " + ", ".join(s["sim_notes"])
        SCRIPTS.append(sc)
        chans[ch] = sid
    sub = {"id": f"subaction:{i}", "index": {"space": "brawl.subaction_id", "value": i}, "name": s["name"],
           "clip": clip_by_name.get(s["anim"]) if s["anim"] else None, "scripts": chans,
           "playback": {"loop": "Loop" in str(s.get("flags", "")), "transition_in_frames": s.get("in_translation_time") or 0},
           "flags": {"semantic": [x.strip().lower() for x in str(s.get("flags", "None")).split(",") if x.strip() and x.strip() != "None"]},
           "engine": {"brawl.psa": {"class": s["klass"], "anim_frames": s["anim_frames"]}},
           "provenance": prov("verified", "ev:decode")}
    if s["name"] == "<null>" or not chans and not s["anim"]:
        sub["empty"] = True
    SUBACTIONS.append(sub)
for sr in A["subroutines"]:
    e = conv_events(sr["events"])
    SCRIPTS.append({"id": f"script:sub.{sr['off']}", "language": "brawl.psa", "location": {"file": F_MOVESET, "offset": sr["off"]}, "role": "subroutine",
                    "events": e, "provenance": prov("verified", "ev:decode", note=sr["name"])})

# common status names 0x000..0x111 from BrawlHeaders ft/fighter.h
fh = open(os.path.join(EXP, "tooling", "BrawlHeaders", "Brawl", "Include", "ft", "fighter.h"), encoding="utf-8").read()
seg = fh[fh.index("enum Kind {"):fh.index("Test_Motion")]
STATUS = {int(v, 16): n for n, v in re.findall(r"(\w+)\s*=\s*(0x[0-9A-Fa-f]+)", seg)}
STATUS[0x111] = "Test_Motion"
CAT = [(("Attack_Air", "Landing_Attack"), "aerial_attack"), (("Attack_S4", "Attack_Hi4", "Attack_Lw4"), "smash"), (("Attack",), "ground_attack"), (("Catch",), "grab"), (("Throw",), "throw"),
       (("Guard", "Escape"), "shield"), (("Damage", "Down", "Passive", "Fura", "Capture", "Thrown", "Bury", "Swallowed", "Catched", "Clung"), "damage"), (("Cliff",), "ledge"),
       (("Item", "Swing", "Heavy", "Light", "Ladder"), "item"), (("Appeal",), "taunt"), (("Entry", "Win", "Lose", "Standby"), "entry_exit"),
       (("Wait", "Walk", "Dash", "Run", "Turn", "Jump", "Fall", "Squat", "Landing", "Glide", "Fly", "Pass", "Ottoto", "Slip", "Swim"), "movement")]


def cat(n):
    for keys, c in CAT:
        if any(n.startswith(k) for k in keys):
            return c
    return "misc"


def first_sub(evs):
    for e in evs:
        if e["name"] and e["name"].startswith("Change Subaction") and e.get("args"):
            v = e["args"][0]
            if isinstance(v, int) and 0 <= v < len(A["subactions"]["list"]):
                return v
    return None


ee = {a["index"]: a for a in A["actions"]["entry_exit"]}
SPECIAL_NAMES = {0x112: "SpecialN (Mach Tornado start)", 0x113: "SpecialS (Drill Rush start)", 0x114: "SpecialHi (Shuttle Loop rise)", 0x115: "SpecialLw (Dimensional Cape start)",
                 0x116: "Final (Galaxia Darkness start)", 0x117: "SpecialNSpin", 0x118: "SpecialNEnd", 0x119: "SpecialSDrill (SpecialSRush uniq process)", 0x11A: "SpecialSEnd",
                 0x11B: "SpecialLw teleport (F/B/N)", 0x11C: "SpecialLwEnd / attack", 0x11D: "SpecialHiLoop", 0x11E: "SpecialHiEnd (landing)",
                 0x11F: "Final follow-up A", 0x120: "Final follow-up B", 0x121: "Final follow-up C"}
SPECIAL_ACTION_NAME = {}
ACTIONS = []
for a in A["actions"]["list"]:
    i = a["index"]
    act = {"id": f"action:{i}", "index": {"space": "brawl.action_id", "value": i}, "source": "engine_common" if a["kind"] == "common" else "content",
           "flags": {"raw": "0x%08X" % (a["flags"][-1] & 0xFFFFFFFF)} if a.get("flags") else {}, "provenance": prov("verified", "ev:decode")}
    if i in STATUS:
        act["name"] = STATUS[i]
        act["category"] = cat(STATUS[i])
        act["provenance"] = prov("verified", "ev:decode", "ev:headers")
    if i in ee:
        refs = []
        fs = None
        for which, evs in ee[i]["scripts"].items():
            if evs:
                sid = f"script:act.{i}.{which}"
                e = conv_events(evs)
                SCRIPTS.append({"id": sid, "language": "brawl.psa", "location": {"file": F_MOVESET}, "role": "action_entry" if which == "entry" else "action_exit",
                                "events": e, "provenance": prov("verified", "ev:decode")})
                refs.append(sid)
                if which == "entry":
                    fs = first_sub(evs)
        if refs:
            act["scripts"] = refs
        if i >= 0x112:
            act["category"] = "special"
            if fs is not None:
                act["subaction"] = f"subaction:{fs}"
            act["name"] = SPECIAL_NAMES[i]
            tg = []
            for e in ee[i]["scripts"].get("entry", []):
                if e["name"] and e["name"].startswith("Change Action") and e.get("args"):
                    v = e["args"][0] if e["name"] == "Change Action" else (e["args"][1] if len(e["args"]) > 1 else None)
                    if isinstance(v, int) and 0 <= v < len(A["actions"]["list"]) and f"action:{v}" not in tg:
                        tg.append(f"action:{v}")
            if tg:
                act["enters"] = tg
                act["summary"] = "entry script transitions: " + ", ".join("%s (0x%X %s)" % (t, int(t[7:]), STATUS.get(int(t[7:]), SPECIAL_NAMES.get(int(t[7:]), ""))) for t in tg)
            act["provenance"] = prov("inferred", "ev:decode", "ev:rel", note="name inferred: Brawl orders a fighter's entry statuses N, S, Hi, Lw, Final (0x112-0x116), then follow-ups; follow-ups named from their subaction / Change Action chain; 0x11F-0x121 = the three Final uniq-process classes in the module (order not confirmed)")
    if a.get("pre_name") and "name" not in act:
        act["name"] = a["pre_name"]
    if not act["flags"]:
        act.pop("flags")
    ACTIONS.append(act)

# overrides (statusAnimCmdDisguise lists)
for o in A["action_overrides"]:
    pass

BODY = {"hurtboxes": [{"index": k, "joint": hb["bone"], "role": hb["bone_name"], "zone": hb["zone"] if hb["zone"] in ("low", "mid", "high") else "mid", "a": hb["offset"],
                       "b": [round(hb["offset"][j] + hb["stretch"][j], 4) for j in range(3)], "radius_scale": hb["radius"], "provenance": prov("verified", "ev:decode")}
                      for k, hb in enumerate(A["hurtboxes"])],
        "environment_collision": {"boxes": [{"kind": "ledge_grab", **b} for b in A["ledge_grab"]]},
        "special_joints": [{"purpose": f"bone reference {b['slot']}", "joint": b["bone"], "engine_field": b["bone_name"]} for b in A["bone_references"]] +
                          [{"purpose": "item hold", "joint": b["bone"], "engine_field": b["bone_name"]} for b in A["hand_bones"]],
        "provenance": prov("verified", "ev:decode")}


def sub_id(*nm):
    return [f"subaction:{s['index']}" for s in A["subactions"]["list"] if s["name"] in nm]


def hb_desc(name):
    s = [x for x in A["subactions"]["list"] if x["name"] == name]
    if not s:
        return ""
    s = ([x for x in s if x["hitboxes"]] or s)[0]
    ws = collections.OrderedDict()
    for h in s["hitboxes"]:
        ws.setdefault((h["start"] + 1, h["end"]), []).append(h)
    parts = []
    for (st, en), hs in list(ws.items())[:3]:
        d = sorted(set(h["damage"] for h in hs))
        parts.append(f"f{st}-{en if en is not None else 'end'}: {'/'.join(str(x) for x in d)}% angle {hs[0]['angle']} kbg {hs[0]['kbg']} bkb {hs[0]['bkb']} wdsk {hs[0]['wdsk']} ({hs[0]['element']}, {len(hs)} boxes)")
    more = f" (+{len(ws) - 3} more windows)" if len(ws) > 3 else ""
    return "; ".join(parts) + more + (f"; IASA {s['iasa_frame'] + 1}" if s["iasa_frame"] is not None else "") + f"; anim {s['anim_frames']} frames"


MOVE_DEFS = [("jab", "rapid_jab", "Rapid jab (no Attack11/12/13: slots 0x48-0x4A are empty; jab goes straight to Attack100Start)", ["Attack100Start", "Attack100", "AttackEnd"]),
             ("dash_attack", "dash_attack", "Dash attack", ["AttackDash"]), ("ftilt", "ftilt", "Three-hit forward tilt (AttackS3S -> S3S2 -> S3S3)", ["AttackS3S", "AttackS3S2", "AttackS3S3"]),
             ("utilt", "utilt", "Up tilt", ["AttackHi3"]), ("dtilt", "dtilt", "Down tilt", ["AttackLw3"]), ("fsmash", "fsmash", "Forward smash", ["AttackS4Start", "AttackS4S", "AttackS4Hold"]),
             ("usmash", "usmash", "Up smash (multi-hit)", ["AttackHi4Start", "AttackHi4", "AttackHi4Hold"]), ("dsmash", "dsmash", "Down smash", ["AttackLw4Start", "AttackLw4", "AttackLw4Hold"]),
             ("nair", "nair", "Neutral air", ["AttackAirN"]), ("fair", "fair", "Forward air (multi-hit)", ["AttackAirF"]), ("bair", "bair", "Back air (multi-hit)", ["AttackAirB"]),
             ("uair", "uair", "Up air", ["AttackAirHi"]), ("dair", "dair", "Down air", ["AttackAirLw"]), ("grab", "grab", "Grab", ["Catch", "CatchDash", "CatchTurn"]),
             ("pummel", "pummel", "Pummel", ["CatchAttack"]), ("fthrow", "fthrow", "Forward throw", ["ThrowF"]), ("bthrow", "bthrow", "Back throw", ["ThrowB"]),
             ("uthrow", "uthrow", "Up throw", ["ThrowHi"]), ("dthrow", "dthrow", "Down throw", ["ThrowLw"])]
MOVES = []
for mid, inp, desc, subs in MOVE_DEFS:
    d = "; ".join(x for x in (hb_desc(n) for n in subs) if x)
    MOVES.append({"id": f"move:{mid}", "input": inp, "subactions": [x for n in subs for x in sub_id(n)], "description": f"{desc}. {d}", "provenance": prov("verified", "ev:decode")})
MOVES += [
    {"id": "move:special_n", "input": "special_n", "name": "Mach Tornado", "subactions": [x for n in ("SpecialNStart", "SpecialAirNStart", "SpecialNSpin", "SpecialNEnd", "SpecialAirNEnd") for x in sub_id(n)],
     "description": "Spin: SpecialNSpin loops 1% special hitboxes (vacuum angles, wdsk 50-90) every few frames; finisher SpecialNEnd " + hb_desc("SpecialNEnd") + ".",
     "mechanics": ["Tap-B rise, horizontal drift and duration are NOT in PSA or ft_metaknight.rel: they are the sora_melee class ftMetaknightStatusUniqProcessSpecialNSpin::execStatus (fn_27_358CF4, 696 bytes), which reads params 4012-4015 (paramSpecialN floats 16.0, 80.0, 1.5, 2.0 under the inferred numbering) and int 24000 (10).",
                   "paramSpecialN[0..10] (1.0, 0.7, 80.0, 0.12, 2.0, 0.1, 1.7, 0.008, -0.08, 0.5, 1.0) are read by generic sora_melee code by id (not traced)."],
     "provenance": prov("verified", "ev:decode", "ev:sora")},
    {"id": "move:special_s", "input": "special_s", "name": "Drill Rush", "subactions": [x for n in ("SpecialSStart", "SpecialAirSStart", "SpecialSDrill", "SpecialSEnd", "SpecialAirSEnd") for x in sub_id(n)],
     "description": "Drill: " + hb_desc("SpecialSDrill") + ". End: " + hb_desc("SpecialSEnd") + ".",
     "mechanics": ["Steering (stick angle control) and the rush itself: ft_metaknight.rel class ftMetaknightStatusUniqProcessSpecialSRush (execStatus fn_111_C710 reads param 4020 = paramSpecialS[3] 3.0, inferred numbering; exitStatus fn_111_C820). End/bounce: ftMetaknightStatusUniqProcessSpecialSEnd (fn_111_C9B8, fn_111_CB48)."],
     "provenance": prov("verified", "ev:decode", "ev:rel")},
    {"id": "move:special_hi", "input": "special_hi", "name": "Shuttle Loop", "subactions": [x for n in ("SpecialHi", "SpecialAirHiStart", "SpecialHiLoop", "SpecialHiEnd") for x in sub_id(n)],
     "description": "Rise: " + hb_desc("SpecialHi") + ". Loop: " + hb_desc("SpecialHiLoop") + ".",
     "mechanics": ["Shuttle Loop -> glide is PSA: the entry scripts of actions 0x114 (SpecialHi) and 0x11D (SpecialHiLoop) run 'Change Action 133 (0x85 Glide) on Animation End + In Air'; on ground 0x11D goes to 0x11E SpecialHiEnd. So glide is entered as the ordinary common Glide status.",
                   "No MK-specific code class for Up-B: the loop path is animation-driven (root motion in the CHR0) plus PSA momentum events; ftMetaknightTransactor (sora_melee, slot 12 fn_27_35A0EC) is the only MK transition code (not traced).",
                   "No paramSpecialHi block exists in the moveset."],
     "provenance": prov("verified", "ev:decode", "ev:sora")},
    {"id": "move:special_lw", "input": "special_lw", "name": "Dimensional Cape", "articles": ["article:1"],
     "subactions": [x for n in ("SpecialLwStart", "SpecialAirLwStart", "SpecialLw", "SpecialAirLw", "SpecialLwF", "SpecialAirLwF", "SpecialLwB", "SpecialAirLwB", "SpecialLwEnd", "SpecialAirLwEnd") for x in sub_id(n)],
     "description": "Teleport with an optional attack on reappearance: " + hb_desc("SpecialLw") + ". F/B variants move the reappearance point; the cape article (wnMetaknightMantle) plays matching states.",
     "mechanics": ["Movement uses paramSpecialLw (0.5, 0.4, 0.5, 2.5, 0.5, 2.5: plausibly speed/accel pairs for neutral/forward/back, inferred) read by generic code; no MK uniq-process class for it.",
                   "Invisibility/intangibility is PSA (Visibility / Body Collision events) - see the SpecialLw* scripts."],
     "provenance": prov("inferred", "ev:decode", "ev:rel")},
    {"id": "move:final_smash", "input": "final_smash", "name": "Galaxia Darkness", "subactions": [x for n in ("FinalStart", "FinalAirStart", "FinalEndR", "FinalEndL", "FinalAirEndR", "FinalAirEndL") for x in sub_id(n)],
     "description": "Cape catch (0% boxes, " + hb_desc("FinalStart") + ") then a cutscene slash handled by module classes ftMetaknightStatusUniqProcessFinalAttackGallery/FinalEnd/FinalHitWait (param int 24005 read by fn_111_CCD8).",
     "provenance": prov("verified", "ev:decode", "ev:rel")},
    {"id": "move:glide", "input": "other", "name": "Glide", "subactions": [x for n in ("GlideStart", "GlideDirection", "GlideWing", "GlideAttack", "GlideEnd", "GlideLanding") for x in sub_id(n)],
     "description": "Common Brawl glide (statuses Glide_Start 0x84 .. Glide_End 0x88; subactions 0x39-0x3E). Entered by holding jump during a midair jump for 'Glide Frame Window' = 16 frames, or from Shuttle Loop. Glide attack: " + hb_desc("GlideAttack") + ".",
     "mechanics": ["Physics: ftStatusUniqProcessGlide in sora_melee (initStatus fn_27_167EF4 512 B, execStatus fn_27_1680F4 2220 B, execFixPos fn_27_1689A0) reading the Misc Glide block (20 floats + 2 ints) and common air params 3023/3024/3029/3030/3032.",
                   "Shared by Meta Knight, Pit and Charizard in Brawl (Info_Param_Int_Glide_Type 23186)."],
     "provenance": prov("verified", "ev:decode", "ev:sora", "ev:headers")},
    {"id": "move:multijump", "input": "other", "name": "Five midair jumps", "subactions": [x for n in ("JumpAerialF", "JumpAerialF2", "JumpAerialF3", "JumpAerialF4", "JumpAerialF5") for x in sub_id(n)],
     "description": "Jumps = 6 (1 ground + 5 air), each midair jump its own subaction/animation (JumpAerialF..F5) with velocities from Misc MultiJump hops [2.2, 2.1, 2.0, 1.88, 1.75].",
     "provenance": prov("verified", "ev:decode", "ev:brawllib")},
]

ART = []
for k, a in enumerate(A["articles"]):
    ART.append({"id": f"article:{k}", "local_index": k, "name": a["name"], "kind": "effect_object" if k == 0 else "companion", "descriptor": a.get("string_id", ""),
                "states": [{"index": x["index"] if isinstance(x["index"], int) else j, "name": x["name"]} for j, x in enumerate(a["subactions"])], "status": "active",
                "provenance": prov("verified", "ev:decode")})
ART[0]["name"] = "win-pose prop (static article)"
if len(ART) > 1:
    ART[1].update(name="Mantle (wnMetaknightMantle)", model="model:wpnmetaknightmantle", code_unit="code:ft_metaknight",
                  provenance=prov("verified", "ev:decode", "ev:rel", note="The cape as a separate weapon object: states for Dimensional Cape, shield/dodge wraps, Final Smash, taunt and wins. Class wnMetaknightMantle in the module (vtable at .data+0x6118, 80 slots, 39 own)."))
ART.append({"id": "article:entry", "local_index": 2, "name": "Entry article (Halberd)", "kind": "effect_object", "descriptor": "Entry Article", "status": "active",
            "provenance": prov("observed", "ev:dump", note="MoveDefArticleNode 'Entry Article' with FitMetaknightEntry.pac")})
VARIABLES = [{"name": "LA/RA/IC variables", "scope": "fighter", "storage": "PSA LA-Basic/Bit/Float, RA-*, IC-*", "meaning": "PSA scripts read/write these; MK's special statuses use them for the tornado/drill loops", "provenance": prov("verified", "ev:decode")}]

# ------------------------------------------------------------------ code
KNOWN = {"fn_111_C710": "ftMetaknightStatusUniqProcessSpecialSRush::execStatus - Drill Rush per-frame; reads param 4020 (getConstantFloat)",
         "fn_111_C820": "ftMetaknightStatusUniqProcessSpecialSRush::exitStatus",
         "fn_111_C9B8": "ftMetaknightStatusUniqProcessSpecialSEnd::execStatus", "fn_111_CB48": "ftMetaknightStatusUniqProcessSpecialSEnd::exitStatus",
         "fn_111_CCD8": "ftMetaknightStatusUniqProcessFinalAttackGallery::execFixPos - Final Smash victims (ftManager lookups, param int 24005)",
         "fn_111_CC64": "ftMetaknightStatusUniqProcessFinalAttackGallery::execFixPosCounter", "fn_111_D21C": "ftMetaknightStatusUniqProcessFinalEnd::execFixPos",
         "fn_111_D6EC": "ftMetaknightStatusUniqProcessFinalHitWait::initStatus", "fn_111_D010": "Final Smash helper (random, effect/camera calls)",
         "fn_111_DD64": "static initialiser (__sinit): constructs the global uniq-process / class-info objects (6008 bytes)",
         "fn_111_70": "large constructor (0x183C bytes) - ftFighterBuilder<ftMetaknightBuildConfig> module assembly (inferred from size and position)",
         "fn_111_7E5C": "ftMetaknight virtual [35] (task scheduler + dynamic_cast)", "fn_111_806C": "ftMetaknight virtual [40]", "fn_111_7C7C": "ftMetaknight virtual [41]",
         "fn_111_7FF8": "ftMetaknight virtual [42]", "fn_111_81A8": "ftMetaknightExtendParamAccesser: param-id lookup (ids 4000-4026 / 24000-24007)"}
FUNCS = []
for f in REL["functions"]:
    role = KNOWN.get(f["name"])
    if not role:
        if f["classes"]:
            role = "vtable slot: " + ", ".join(sorted(set(re.sub(r"<.*", "<...>", c) for c in f["classes"])))[:200]
        elif f["name"] in ("__register_global_object", "__destroy_global_chain", "_prolog", "_epilog", "_unresolved"):
            role = "runtime glue"
        else:
            role = "unclassified (not referenced from a vtable)"
    fn = {"id": f"fn:{f['name']}", "offset": f["offset"], "size": f["size"], "label": f["name"], "label_source": "debug_symbol" if not f["name"].startswith("fn_") else "call_target", "role": role}
    calls = [{"engine_symbol": k, "count": v} if not k.startswith("fn_111_") else {"callee": f"fn:{k}", "count": v} for k, v in list(f["calls"].items())[:12] if k]
    if calls:
        fn["calls"] = calls
    FUNCS.append(fn)
fnames = {f["label"] for f in FUNCS}
for fn in FUNCS:
    if "calls" in fn:
        fn["calls"] = [c for c in fn["calls"] if "callee" not in c or c["callee"][3:] in fnames]
DATA_OBJ = [{"id": "data:vt." + v["offset"].lower(), "offset": v["offset"], "kind": "vtable " + (v["class_name"] if len(v["class_name"]) < 80 else v["class_name"][:77] + "..."),
             "rows": len(v["slots"]), "row_size": 4, "row_count_source": "inferred_from_layout", "note": f"this-offset {v['this_offset']}, {v['own_slots']} slots point into this module"} for v in REL["vtables"]]
DATA_OBJ += [{"id": "data:" + j["name"], "offset": j["offset"], "kind": "switch jump table", "rows": j["entries"], "row_size": 4, "row_count_source": "declared", "note": f"used by {j['function']}"} for j in REL["jump_tables"]]
DATA_OBJ.append({"id": "data:homebtnicon", "offset": "0x68C0", "kind": "HomeBtnIcon image (6336 bytes, linked into every module)", "row_count_source": "declared"})
imp = collections.Counter()
for t in REL["import_targets"]:
    imp[(t["module"], t["target"])] += t["count"]
IMPORTS = [{"target": {"engine": "brawl.wii", "address": "0x0", "symbol": t, "unit": m}, "count": c, "via": "relocation"} for (m, t), c in imp.most_common(60)]
own_slots = sum(v["own_slots"] for v in REL["vtables"])
CODE_UNITS = [
    {"id": "code:ft_metaknight", "name": "ft_metaknight.rel", "kind": "module", "arch": "broadway", "file": F_MODULE,
     "code": {"offset": "0xCC", "size": 0x11340, "size_source": "declared", "rodata": [".rodata 0x5C bytes (float constants)", ".data 0x8180 bytes: 110 vtables + RTTI strings, 14 jump tables, HomeBtnIcon (0x18C0)"]},
     "relocations": {"count": REL["relocations_total"], "by_type": {"abs32": 1874, "lo16": 350, "hi16_adjusted": 287, "branch24": 1197},
                     "semantics": "REL imports: main.dol (module 0, absolute addend), sora_melee (27, section+offset), self (111). Names from doldecomp/brawl symbol lists."},
     "debug_symbols": {"count": 0, "stripped": True},
     "functions": FUNCS, "data_objects": DATA_OBJ, "imports": IMPORTS,
     "provenance": prov("verified", "ev:rel", "ev:decomp",
                        note=f"700 functions (decomp splits). Almost all of the module is C++ template boilerplate: ftFighterBuilder<ftMetaknightBuildConfig> (module/kinetic/article/sound/virtual-node pools), "
                             f"soKineticMediatorImpl with ftMetaknightKineticTransactor, soArticleMediatorImpl for wnMetaknightMantle, param accessers. {own_slots} vtable slots point into the module. "
                             "MK-specific native logic here: Drill Rush (SpecialSRush/SpecialSEnd uniq processes), Final Smash (FinalAttackGallery/FinalEnd/FinalHitWait), the Mantle article class, "
                             "and the ExtendParamAccesser (param ids). Mach Tornado spin control, glide and MK status transitions live in sora_melee (see code:sora_melee_mk).")},
    {"id": "code:sora_melee_mk", "name": "sora_melee.rel (engine module) - Meta Knight / glide classes", "kind": "other", "arch": "broadway",
     "functions": [{"id": f"fn:sora.{s['name']}", "offset": s["offset"], "size": s.get("size"), "label": s["name"], "label_source": "call_target",
                    "role": f"{v['class_name']}::{UNIQ_SLOTS[k] if 'UniqProcess' in v['class_name'] and k < len(UNIQ_SLOTS) else 'slot %d' % k}"}
                   for v in SORA for k, s in enumerate(v["slots"]) if s.get("size", 0) > 8],
     "provenance": prov("verified", "ev:sora", "ev:decomp",
                        note="Engine code, not shipped with the fighter: ftMetaknightStatusUniqProcessSpecialNSpin (Mach Tornado control, reads 4012-4015 + 24000), ftMetaknightTransactor (MK status transitions), "
                             "ftStatusUniqProcessGlide (common glide physics). Offsets are sora_melee .text offsets.")},
]

FRAMEWORK = {"engine": "brawl.wii", "name": "retail Brawl fighter framework (sora_melee)", "registration": [
    {"table": "ftClassInfoImpl<22, ftMetaknight>", "index": {"space": "brawl.fighter_id", "value": 22}, "fields": {"module": "ft_metaknight.rel", "module_id": 111}},
], "inheritance": {"declared_base": None, "inherited": ["common statuses 0x000-0x111 incl. Glide 0x84-0x88 and multi-jump (Jump_Aerial 0xC) from sora_melee", "common action scripts from Fighter.pac"],
                   "asset_lineage": []}, "provenance": prov("verified", "ev:rel", "ev:headers")}

ISSUES = [
    {"id": "issue:param_id_numbering", "title": "Special-param id numbering (4000+/24000+) is inferred", "layer": "ir", "severity": "info", "status": "open",
     "description": "ftExtendParamAccesserEx<3999, 27, 23999, 8> gives 27 float + 8 int ids; the mapping to paramSpecialN/S/Lw/Final words assumes floats-then-ints in block order. fn_111_81A8 (the lookup) was not disassembled to confirm.",
     "provenance": prov("inferred", "ev:rel")},
    {"id": "issue:sora_logic_not_decoded", "title": "Mach Tornado / glide / MK transitions are engine code in sora_melee, only located", "layer": "tooling", "severity": "info", "status": "open",
     "description": "fn_27_358CF4 (SpecialNSpin execStatus), fn_27_1680F4 (Glide execStatus), fn_27_35A0EC (Transactor) are unnamed in the decomp; behaviour must be read from disassembly or measured in Dolphin.",
     "affects": ["move:special_n", "move:glide", "move:special_hi"], "provenance": prov("verified", "ev:sora")},
    {"id": "issue:glide_fields_unnamed", "title": "Misc Glide block has no field names", "layer": "ir", "severity": "info", "status": "open",
     "description": "20 floats + 2 ints; only words 0/1 (80, -70: angle limits) have a plausible meaning. Needs reading of ftStatusUniqProcessGlide.", "provenance": prov("verified", "ev:brawllib")},
    {"id": "issue:frames_after_loops", "title": "Event frames are exact only before the first loop/goto; hit windows come from a simulation", "layer": "ir", "severity": "info", "status": "open",
     "description": "Infinite loops are run once (SpecialNSpin, Attack100); If takes the true branch. Hit windows are 1-based [start, end] from the unrolled simulation.", "provenance": prov("verified", "ev:decode")},
    {"id": "issue:costume_diff", "title": "Costumes 01-05 not diffed against 00", "layer": "ir", "severity": "info", "status": "open",
     "description": "Same size as 00; assumed texture/palette swaps. Only FitMetaknight00.pac was dumped.", "provenance": prov("inferred", "ev:disc")},
    {"id": "issue:unknown_events", "title": "A few PSA events are not in BrawlLib's dictionary", "layer": "tooling", "severity": "info", "status": "open",
     "description": "Unknown ids: " + json.dumps(A["event_stats"]["unknown_events"]) + " - kept as engine.<name> with raw opcode.", "provenance": prov("verified", "ev:decode")},
    {"id": "issue:ui_not_extracted", "title": "UI (CSS portrait, stock icon, BP) not extracted", "layer": "ir", "severity": "info", "status": "open",
     "description": "They live in shared menu archives (menu2/sc_selcharacter*, info*); not dumped in this pass.", "provenance": prov("assumed", "ev:disc")},
]

PARITY = [
    ("skel:main", MELEE + "skel:main", "analogous", "Brawl MK: 77 named bones with 16 cape + 22 wing bones and 4 visibility gates; Melee has no MK. Closest Melee skeleton by role is Kirby (short, round, no neck) - see metaknight.port-plan.md."),
    ("move:glide", MELEE + "move:special_hi", "no_counterpart", "Melee has no glide status."),
]

DOC = {
    "ir_version": "0.1.0", "document_id": "metaknight.brawl",
    "subject": {"character": "Meta Knight", "game": "ssbb", "engine": "brawl.wii",
                "distribution": {"name": "Super Smash Bros. Brawl (retail)", "kind": "retail", "media": DISC},
                "analysed_with": [{"tool": "BrawlLib MoveDef parser via experiment/brawl-kirby/tools/brawl_dump/mdump.exe (x86)"},
                                  {"tool": "ports/halberd/tools/decode_mk.py (from build_kirby.py)"},
                                  {"tool": "ports/halberd/tools/rel_mk.py + sora_mk.py with doldecomp/brawl symbols", "revision": "345952a3"}],
                "notes": "Vanilla Meta Knight for the GD's Melee port. Character-level only; Brawl global mechanics (tripping, air dodge, hitstun) are out of scope."},
    "evidence": EVIDENCE, "identity": IDENTITY,
    "resources": {"files": FILES, "shared_dependencies": [{"name": "Fighter.pac", "owner": "engine", "why": "common action scripts"},
                                                           {"name": "sora_melee.rel", "owner": "engine", "why": "all common statuses incl. glide, the MK SpecialNSpin uniq process and MK transactor"},
                                                           {"name": "smashbros_sound.brsar", "owner": "engine", "why": "PSA sound ids -> waves (groups 683 / 486)"},
                                                           {"name": "ef_common", "owner": "engine", "why": "common Graphic Effect ids"}]},
    "assets": {"skeletons": [SKEL, MSKEL], "bone_roles": ROLES, "models": MODELS, "materials": MATS, "textures": TEX, "part_visibility": PARTVIS, "costumes": COSTUMES,
               "animations": {"container": F_MOTION, "indexing": "CHR0 clips by name; a subaction names its clip",
                              "clips": CLIPS, "stats": {"chr0": len(chr0), "srt0": len(srt0), "clr0": len(clr0), "mantle_chr0": len(mantle_anims),
                                                        "used_by_subactions": sum(1 for n in mo["frames"] if used_by.get(n))}, "provenance": prov("verified", "ev:dump")},
               "effects": EFFECTS, "audio": AUDIO, "ui": UI, "media": MEDIA, "collectibles": COLLECT},
    "behavior": {"attributes": ATTRIBUTES, "body": BODY, "actions": ACTIONS, "subactions": SUBACTIONS, "scripts": SCRIPTS,
                 "script_languages": [{"id": "brawl.psa", "unit": "command_record", "opcode_field": "event id AABBCCDD (module, event, param count, flags)",
                                       "decoder": {"path": "experiment/BrawlCrate/BrawlLib/SSBB/ResourceNodes/Moveset/"}}],
                 "moves": MOVES, "variables": VARIABLES, "articles": ART,
                 "copy_abilities": [{"id": "copy:kirby", "recipient": "Kirby", "files": [FID["fighter/kirby/FitKirbyMetaknight.pac"], FID["fighter/kirby/FitKirbyMetaknight00.pac"], FID["fighter/kirby/FitKirbyMetaknightSpy.pac"], FID["effect/kirby_cp/ef_KbMetaknight.pac"]],
                                     "provenance": prov("verified", "ev:disc", note="Kirby-owned (Mach Tornado copy); integration only, not decoded.")}]},
    "code": {"units": CODE_UNITS},
    "integration": {"frameworks": [FRAMEWORK]},
    "issues": ISSUES,
    "coverage": {
        "identity": {"status": "complete"}, "resources": {"status": "complete", "note": f"{len(FILES)} fighter-owned or fighter-named files; UI in shared menu archives not listed."},
        "assets.skeletons": {"status": "complete"}, "assets.models": {"status": "complete", "note": "costume 00 body/shadow + mantle article models, meshes with draw calls"},
        "assets.textures": {"status": "complete", "note": "costume 00"}, "assets.costumes": {"status": "complete"},
        "assets.animations": {"status": "complete", "note": f"{len(chr0)} CHR0, {len(srt0)} SRT0, {len(clr0)} CLR0, {len(mantle_anims)} mantle CHR0."},
        "assets.effects": {"status": "summary"}, "assets.audio": {"status": "summary", "note": "sound ids used + BRSAR names; no waves"}, "assets.ui": {"status": "skeleton"},
        "behavior.attributes": {"status": "complete", "note": "185 common + all special words (4 param blocks, multijump, glide)."},
        "behavior.body": {"status": "complete"}, "behavior.actions": {"status": "complete", "note": f"{len(ACTIONS)} (274 common named from BrawlHeaders, 16 special named from their first subaction)."},
        "behavior.subactions": {"status": "complete"},
        "behavior.scripts": {"status": "complete", "note": "all 4 channels of every subaction, special actions' entry/exit, subroutines; hit windows from loop-unrolled simulation"},
        "behavior.moves": {"status": "complete"}, "behavior.articles": {"status": "complete"}, "behavior.copy_abilities": {"status": "skeleton"},
        "code": {"status": "summary", "note": "all 700 module functions with boundaries, vtable roles and calls; MK-specific ones labelled; sora_melee MK classes located, not decompiled"},
        "integration": {"status": "summary"}, "issues": {"status": "complete"},
    },
}
json.dump(DOC, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"wrote {OUT}: {len(FILES)} files, {len(joints)} bones, {len(MODELS)} models, {len(MATS)} materials, {len(TEX)} textures, {len(CLIPS)} clips, "
      f"{len(ACTIONS)} actions, {len(SUBACTIONS)} subactions, {len(SCRIPTS)} scripts, {HB_COUNT} hitbox windows, {len(ATTRS)}+{len(SPECIAL)} attributes, "
      f"{len(FUNCS)} module functions, {len(CODE_UNITS[1]['functions'])} sora functions, {len(snd_uses)} sound ids")
