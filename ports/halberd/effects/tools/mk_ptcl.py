"""Meta Knight's three REFF particle effects, re-authored as Melee particle generators (HSD ptcl + texg).

REFF (Brawl, NW4R effect) and HSD ptcl are different systems: an REFF emitter has keyed curves (colour, alpha, scale,
fields such as spin / random) and TEV blending of up to three textures, one of them the frame buffer; an HSD generator
has a shape (disc / line / tornado / ...), an emission rate, and a per-particle byte-code (size, colour and texture
changes over time). What carries over, per emitter:

  PtcMetaknightDrillLush  (Drill Rush, EFLS 21; attached to the sword bone, 40 frames)
    parent 'PtcMetaknightDrillLush': yellow 'ptc_cmn_dead' flame along the sword, life 4, one a frame, additive
        -> gen 3: a LINE generator along the blade (joint-oriented), ptc_cmn_dead, yellow (255,224,32) fading, life 4
    child  'MetaknightDrillLushBlue': 'ptc_cmn_wind' streaks from the sword tip, radial 1.5, FIELD_SPIN, life 10 +-50%,
        colour (224,240,255) -> (32,0,255) fading, additive
        -> gen 0: a TORNADO generator on the blade axis (particles orbit it while they travel to the tip - HSD's own
           spiral physics stand in for the REFF spin field), ptc_cmn_wind, white-blue -> blue fading, life 10
  PtcMetaknightMantleStart / MantleEnd  (Dimensional Cape, EFLS 22 / 23)
    two directional bursts of 8 (left / right), life 5, 'FB' + drop mask + indirect warp: Brawl draws them as a
    refraction of the frame buffer. Melee has no frame-buffer effect: the burst keeps its count, direction, speed and
    life, drawn with the drop-mask shape as dark violet wisps (the look of the distortion over MK's dark palette)
        -> gen 1 (start, speed 1.0) / gen 2 (end, speed 1.5): 16-particle disc burst in the screen plane
"""
import base64

# ParticleKind bits (HSDRaw HSD_ParticleGroup.cs): Gravity 1, Friction 2, BlendOne 0x400000 (additive)
FRICTION, BLEND_ONE = 0x2, 0x400000
# generator type high bits: 0x100 | 0x400 = orient the emission by the attached joint's rotation (generator.c)
JOINT_ORIENT = 0x100 | 0x400
DISC, LINE, TORNADO = 0, 1, 2


def _tex(ef, name):
    t = next(x for x in ef["reft"] if x["name"] == name and x.get("w"))
    return {"name": name, "w": t["w"], "h": t["h"], "fmt": {"I8": "I8", "IA8": "IA8", "I4": "I4", "IA4": "IA4"}.get(t["fmt"], "RGBA8"),
            "frames": [t["rgba"]]}


def _hdr(type_, gflags, texg, genlife, life, kind, grav, fric, vel, radius, angle, random, size, param=(0, 0, 0)):
    return {"type": type_, "gflags": gflags, "texg": texg, "genlife": genlife, "life": life, "kind": kind, "gravity": grav,
            "friction": fric, "vel": list(vel), "radius": radius, "angle": angle, "random": random, "size": size, "param": list(param)}


def spec(ef, id_start):
    tex = [_tex(ef, "ptc_cmn_wind"), _tex(ef, "ptc_cmn_drop_mask"), _tex(ef, "ptc_cmn_dead")]
    gens = []
    # gen 0: drill spiral (MetaknightDrillLushBlue)
    gens.append({"name": "DrillLushBlue (spiral)", "behavior": 5,
                 "header": _hdr(TORNADO, JOINT_ORIENT, 0, 45, 12, BLEND_ONE, 0.45, 0.0, (0, 0.8, 0), -5.0, 0.35, -3.0, 4.5),
                 "ops": [[0x40, "b", 0], [0xE6, ""], [0xA0, "ef", 0, 4.5], [0xA0, "ef", 12, 2.5],
                         [0xC0, "ebbbb", 0, 224, 240, 255, 255], [0xAD, ""], [0xD0, "ebbbb", 0, 32, 0, 255, 0],
                         [0xC0, "ebbbb", 12, 64, 64, 255, 0], [0x00, "s", 12], [0xFF, ""]]})
    # gen 1 / 2: Dimensional Cape start / end bursts
    for nm, speed, life in (("MantleStart", 1.0, 6), ("MantleEnd", 1.5, 5)):
        gens.append({"name": nm + " (burst)", "behavior": 0,
                     "header": _hdr(DISC, 0, 1, 1, life, FRICTION, 0.0, 0.88, (0, 0, speed), -3.0, 1.5707964, -16.0, 4.0),
                     "ops": [[0x40, "b", 0], [0xA0, "ef", 0, 4.0], [0xA0, "ef", life, 7.0],
                             [0xC0, "ebbbb", 0, 90, 50, 140, 200], [0xAD, ""], [0xD0, "ebbbb", 0, 20, 0, 40, 0],
                             [0xC0, "ebbbb", life, 50, 30, 90, 0], [0x00, "s", life], [0xFF, ""]]})
    # gen 3: drill flame along the blade (PtcMetaknightDrillLush parent)
    gens.append({"name": "DrillLush (sword flame)", "behavior": 5,
                 "header": _hdr(LINE, JOINT_ORIENT, 2, 45, 4, BLEND_ONE, 0.0, 0.0, (0, 0, 0), 0.0, 0.0, -2.0, 3.5, (0, 13.0, 0)),
                 "ops": [[0x40, "b", 0], [0xC0, "ebbbb", 0, 255, 224, 32, 255], [0xAD, ""], [0xD0, "ebbbb", 0, 255, 128, 0, 0],
                         [0xC0, "ebbbb", 4, 255, 224, 32, 0], [0x00, "s", 4], [0xFF, ""]]})
    reff_directional(gens)
    return {"id_start": id_start, "generators": gens, "texgroups": tex}


# ParticleKind DirVec (HSDRaw HSD_ParticleGroup.cs 0x00200000; psdisp.c: the billboard's up axis turns to the particle's
# screen-space velocity). Visuals pass (not the effects pass): Brawl draws both drill emitters as 'Directional'
# particles with 'Direction: Speed' / 'TypeAxis: OnlyY' (ef_metaknight.json reff emitters) - each streak's texture Y axis
# follows its velocity - which is exactly DirVec. Only the moving blue streaks (gen 0) get it: the sword flame (gen 3)
# is emitted with no velocity, and a zero screen velocity makes DirVec turn a billboard by 90 degrees.
DIR_VEC = 0x200000


def reff_directional(gens):
    for g in gens:
        if g["name"].startswith("DrillLushBlue"):
            g["header"]["kind"] |= DIR_VEC
