"""The shared kit: palette, section tints, port/team colours, type scale.

    python pipeline/kit.py        -> out_kit/kit.json (+ a CVD swatch sheet)

Every other kit build imports this module, so there is one source of truth.
Checks run on every build: text contrast, port distinctness under colour-
blindness simulation (Machado 2009, severity 1.0; distance CIEDE2000), and
section tints staying apart.
"""
import itertools
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import colour as K                                        # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out_kit")

# ----------------------------------------------------------------- palette
PALETTE = dict(
    ink="#0a0e18",          # outlines, backplates, text on light fills
    bone="#f2efe4",         # primary text on dark fills
    muted="#b8c2dc",        # secondary text (values, hints)
    disabled="#7d88a6",     # disabled text and glyphs
    gold="#f0b429",         # selection, everywhere, in every section
    gold_lt="#ffd766",      # selection flash
    gold_dk="#a9761a",      # selection plate / icon on gold
    danger="#e5483b",       # destructive dialog button (Erase Data)
    ok="#27b88a",           # toast / saved
)

# Each section is a place: its own face hue, with backdrop, band and icon
# colours derived from it at fixed lightness steps. Gold selection, ink
# structure and bone text never change, so it stays one system.
#
# Colour is one of three cues. Five dark faces that all carry light text
# cannot all stay apart for red-green colour-blind players (the joint
# optimum is grey and brown), so each section also has its own backdrop
# band rhythm and its hub icon in the breadcrumb.
#
# bands: (x, width) in the hub's unsheared space, full height, sheared.
SECTION_FACES = {
    "versus":     dict(face="#1e3a8c", bands=[(18, 22), (572, 40)]),
    "solo":       dict(face="#6a4308", bands=[(0, 64)]),
    "collection": dict(face="#5a2a6e", bands=[(560, 8), (576, 8), (592, 8)]),
    "options":    dict(face="#2e3640", bands=[]),
    "data":       dict(face="#1c5a4a", bands=[(16, 6), (30, 6), (44, 6), (586, 22)]),
}
STEPS = dict(bg=-10, band=-6, face_hi=+42)       # Lab L relative to the face


def _derive():
    out = {}
    for s, v in SECTION_FACES.items():
        face = K.hexrgb(v["face"])
        L = K.lab(face)[0]
        out[s] = dict(
            face=v["face"],
            bg=K.rgbhex(K.with_lightness(face, L + STEPS["bg"])),
            band=K.rgbhex(K.with_lightness(face, L + STEPS["band"])),
            face_hi=K.rgbhex(K.with_lightness(face, L + STEPS["face_hi"], 0.9)),
            bands=v["bands"])
    return out


SECTIONS = _derive()

# Ports keep the conventional hues players expect (red, blue, yellow, green)
# but are separated in lightness as well as hue, which is what survives
# red-green colour blindness: P1/P2 mid, P3/P4 light, on opposite
# blue-yellow sides.
PORTS = {
    "p1": "#e5483b",
    "p2": "#2f7cf0",
    "p3": "#f4d23a",
    "p4": "#27b88a",
    "cpu": "#7e8490",       # darker than P3/P4: at #9aa0aa P4 read khaki-grey beside it
}
CLOSED = dict(fill="#1b2130", hatch="#2a3244", text="disabled",
              note="closed slot: dark fill + diagonal hatch mask + the word from strings; "
                   "never port-coloured")
TEAMS = {"red": "p1", "blue": "p2", "green": "p4"}

# ---------------------------------------------------------------- type scale
# Sizes are the em size in px at 1x (640x480). Cap height is 0.66 em.
# Reconciled with the baked-text height clusters in meleedump/sort/SORT.md
# (texel heights 16, 20, 24, 28-32, 40-48, 56-64). The 104-128 cluster is
# in-match splash text, out of scope for the menus.
# Two faces from one family. Source Sans 3 (proportional) sets names, labels,
# sentences and numbers - its default figures are tabular, which the atlas
# build checks. Hasklug (Hasklig = Source Code Pro, the monospaced sibling)
# is kept only where fixed width is the point: name tags, name entry and
# network codes.
FONTS = {
    "sans": dict(name="Source Sans 3", licence="SIL OFL 1.1", dir="SourceSans3",
                 files={"bold": "SourceSans3-Bold.otf", "black": "SourceSans3-Black.otf"}),
    "mono": dict(name="Hasklug Nerd Font (Hasklig)", licence="SIL OFL 1.1", dir="Hasklug",
                 files={"bold": "HasklugNerdFont-Bold.otf", "black": "HasklugNerdFont-Black.otf"}),
}


def font_path(face, weight):
    return os.path.join(ROOT, FONTS[face]["dir"], FONTS[face]["files"][weight])
ASCII = "".join(chr(c) for c in range(0x20, 0x7F))
EXTRA = "×%°…–—←→↑↓★"
CAPS = "".join(chr(c) for c in range(0x20, 0x7F) if not chr(c).islower()) + EXTRA
TYPE_SCALE = [
    dict(role="caption", size=12, face="sans", weight="bold",  charset="full",
         use="badges, section-divider labels, table footnotes; the smallest size allowed"),
    dict(role="body",    size=14, face="sans", weight="bold",  charset="full",
         use="descriptions, footer hints, dialog body, breadcrumb, table cells, "
             "character names on player panels"),
    dict(role="row",     size=16, face="sans", weight="black", charset="full",
         use="list rows and widget values, stage name plate"),
    dict(role="label",   size=20, face="sans", weight="black", charset="full",
         use="secondary hub tiles, dialog buttons"),
    dict(role="title",   size=24, face="sans", weight="black", charset="full",
         use="header titles, dialog titles, ordinal suffixes"),
    dict(role="heading", size=32, face="sans", weight="black", charset="full",
         use="panel headings, banners"),
    dict(role="hero",    size=44, face="sans", weight="black", charset="caps",
         use="hero tile labels (always set in capitals)"),
    dict(role="display", size=56, face="sans", weight="black", charset="caps",
         use="placement numerals, READY banner"),
    dict(role="tag",     size=20, face="mono", weight="black", charset="full",
         use="name tags and the name-entry field: 4 fixed-width cells, so the caret "
             "and the plate never move as letters change"),
    # Online (out_kit ONLINE.md): addresses like 203.0.113.7:51500 are read aloud and
    # typed back, so they get fixed cells - digits, dots and the colon line up between
    # the two players' screens, and a changing code never shifts the copy icon. Hasklug's
    # zero is dotted, so 0/O never confuse. Bold, not Black: at 16px Black fills the
    # counters of 6/8/9 and the '.'/':' pair loses its gap.
    dict(role="code",    size=16, face="mono", weight="bold",  charset="code",
         use="network codes and addresses (code plate): max 21 characters, "
             "255.255.255.255:65535 = 201.6 px"),
]
FONT_CHOICE = dict(
    proportional=dict(
        face="sans", why=[
            "Hasklug is monospaced (0.6 em a cell), so a 20-character name at body size is "
            "168 px against a 136 px portrait; proportional Source Sans 3 sets the longest "
            "vanilla name, 'Mr. Game & Watch', in 110.5 px.",
            "Same designer and skeleton as Source Code Pro, which Hasklig is built on: the two "
            "faces share letter shapes and weights, so the switch between them does not show.",
            "SIL OFL 1.1 (licence text in SourceSans3/LICENSE.md, files from Adobe's official "
            "3.052R release). Its CJK companion, Source Han Sans, is also OFL - the second-"
            "script pages can come from the same family.",
            "Its default figures are tabular (540 units in Black), so numbers and stats do not "
            "need a separate monospaced face; font_atlas.py checks digits in every role."]),
    monospaced=dict(
        face="mono", roles=["tag", "code"], why=[
            "Only where fixed cells are the point: the 4-character name tag and name entry "
            "(the caret and plate never move), and network codes (digits line up, and a code "
            "that changes never shifts the copy icon; the zero is dotted)."]),
)
# Character names on CSS player panels (section 3): the plate is the portrait's width.
NAME_FIT = dict(
    plate_1x=136, pad_1x=6, roles=["body", "caption"], max_chars=20,
    rule="Set in body; if wider than plate - 2*pad, caption; if still wider, truncate "
         "with '…'. font_atlas.py checks the 20-character test names below.",
    test_names=["Mr. Game & Watch Jr.", "Captain Falcon Alt 2", "Princess Daisy (SSB)",
                "Dark Samus & Metroid", "Wario Man, Microgame", "Young Link (Classic)"],
)
MIN_SIZE = 12
SHEAR = 0.25     # italic: drawn by shearing the glyph quads, same angle as the hub

ORDINAL = dict(numeral="display", suffix="title", align="suffix cap top = numeral cap top",
               suffixes=["st", "nd", "rd", "th"])


# IPv4 "a.b.c.d:port" plus room for IPv6 "[hex:...]:port"; anything else falls back to '?'
CODE = " -.0123456789:?[]ABCDEFabcdefx…"


def charset(name):
    return {"full": ASCII + EXTRA, "caps": CAPS, "code": CODE}[name]


# ------------------------------------------------------------------ checks
CVD_KINDS = ["normal", "deuteranopia", "protanopia", "tritanopia"]
REQUIRED_CVD = ["normal", "deuteranopia", "protanopia"]   # per the brief
MIN_PORT_DE = {"normal": 18, "deuteranopia": 12, "protanopia": 12, "tritanopia": 8}
MIN_SECTION_DE = 12     # normal vision; under CVD the bands and icon carry it
MIN_TEXT = 4.5          # WCAG AA, body text
MIN_GRAPHIC = 3.0       # WCAG non-text: icons on faces, port swatches on panels
MIN_DISABLED = 2.0      # disabled is meant to recede, but must still be seen


def rgb(h):
    return K.hexrgb(h)


def best_text(fill):
    ink, bone = rgb(PALETTE["ink"]), rgb(PALETTE["bone"])
    ci, cb = K.contrast(ink, rgb(fill)), K.contrast(bone, rgb(fill))
    return ("ink", ci) if ci >= cb else ("bone", cb)


def check():
    errs, report = [], {}

    # ports: pairwise distance under each simulation
    ports = dict(PORTS)
    pairs = {}
    for kind in CVD_KINDS:
        rows = []
        for a, b in itertools.combinations(ports, 2):
            d = K.de2000(K.simulate(rgb(ports[a]), kind), K.simulate(rgb(ports[b]), kind))
            rows.append((round(d, 1), a, b))
        rows.sort()
        pairs[kind] = dict(closest=rows[0], all=rows)
        if rows[0][0] < MIN_PORT_DE[kind] and kind in REQUIRED_CVD:
            errs.append("ports %s/%s only dE %.1f apart under %s (need %d)"
                        % (rows[0][1], rows[0][2], rows[0][0], kind, MIN_PORT_DE[kind]))
    report["port_distance"] = pairs

    # ports vs the selection gold: reported, not required (see notes)
    report["port_vs_gold"] = {
        kind: {p: round(K.de2000(K.simulate(rgb(v), kind), K.simulate(rgb(PALETTE["gold"]), kind)), 1)
               for p, v in ports.items()} for kind in CVD_KINDS}

    # label text on each port colour
    report["port_label_text"] = {}
    for p, v in ports.items():
        which, c = best_text(v)
        report["port_label_text"][p] = dict(text=which, contrast=round(c, 2))
        if c < MIN_TEXT:
            errs.append("text on %s only %.2f:1" % (p, c))

    # port swatches must also show up on every section's face
    for s, t in SECTIONS.items():
        for p, v in ports.items():
            c = K.contrast(rgb(v), rgb(t["face"]))
            if p != "cpu" and c < 1.5:
                errs.append("%s nearly vanishes on %s face (%.2f:1)" % (p, s, c))

    # sections
    report["sections"] = {}
    for s, t in SECTIONS.items():
        r = dict(
            bone_on_face=round(K.contrast(rgb(PALETTE["bone"]), rgb(t["face"])), 2),
            bone_on_bg=round(K.contrast(rgb(PALETTE["bone"]), rgb(t["bg"])), 2),
            muted_on_face=round(K.contrast(rgb(PALETTE["muted"]), rgb(t["face"])), 2),
            icon_on_face=round(K.contrast(rgb(t["face_hi"]), rgb(t["face"])), 2),
            disabled_on_face=round(K.contrast(rgb(PALETTE["disabled"]), rgb(t["face"])), 2),
            face_vs_bg=round(K.contrast(rgb(t["face"]), rgb(t["bg"])), 2),
        )
        report["sections"][s] = r
        if r["bone_on_face"] < MIN_TEXT or r["bone_on_bg"] < MIN_TEXT:
            errs.append("%s: bone text below %.1f:1" % (s, MIN_TEXT))
        if r["muted_on_face"] < MIN_TEXT:
            errs.append("%s: muted text %.2f:1 on face" % (s, r["muted_on_face"]))
        if r["icon_on_face"] < MIN_GRAPHIC:
            errs.append("%s: icon %.2f:1 on face" % (s, r["icon_on_face"]))
        if r["disabled_on_face"] < MIN_DISABLED:
            errs.append("%s: disabled %.2f:1 on face" % (s, r["disabled_on_face"]))
    ink, gold = rgb(PALETTE["ink"]), rgb(PALETTE["gold"])
    report["ink_on_gold"] = round(K.contrast(ink, gold), 2)
    report["ink_on_gold_dk_icon"] = round(K.contrast(rgb(PALETTE["gold_dk"]), gold), 2)

    sec_rows = {}
    for kind in CVD_KINDS:
        rows = sorted((round(K.de2000(K.simulate(rgb(SECTIONS[a]["face"]), kind),
                                      K.simulate(rgb(SECTIONS[b]["face"]), kind)), 1), a, b)
                      for a, b in itertools.combinations(SECTIONS, 2))
        sec_rows[kind] = rows[0]
        if rows[0][0] < MIN_SECTION_DE and kind == "normal":
            errs.append("sections %s/%s faces only dE %.1f apart"
                        % (rows[0][1], rows[0][2], rows[0][0]))
    report["section_face_closest"] = sec_rows
    rhythms = [tuple(v["bands"]) for v in SECTIONS.values()]
    if len(set(rhythms)) != len(rhythms):
        errs.append("two sections share a band rhythm - no non-colour cue left")
    return errs, report


def kit_dict(report):
    return dict(
        units="colours are sRGB hex; material colour 0..1 = hex/255",
        palette=PALETTE,
        sections=SECTIONS,
        section_rules=[
            "A section changes bg, band, face, face_hi and its band rhythm only. "
            "Gold selection, ink structure and bone text are identical everywhere.",
            "Three cues per section: colour, band rhythm, and the section's hub "
            "icon at the root of the breadcrumb. Colour alone is not enough under "
            "red-green colour blindness (see checks.section_face_closest).",
            "bands are (x, width) in the hub's unsheared space, full screen "
            "height, pushed through the hub shear; they may bleed off-screen.",
        ],
        ports=dict(
            colours=PORTS, closed=CLOSED, teams=TEAMS,
            label_text=report["port_label_text"],
            rules=[
                "Every port-coloured element also carries its port number (P1-P4, "
                "or CPU) from strings, so colour is never the only cue.",
                "Port colours are never used for selection; selection is gold "
                "plus the lift-and-plate motion.",
                "P3 yellow and the selection gold sit close under red-green "
                "colour blindness (see checks.port_vs_gold); the number and "
                "the plate extrusion carry the difference.",
            ],
        ),
        type=dict(
            fonts={k: dict(name=v["name"], licence=v["licence"],
                           files={w: "%s/%s" % (v["dir"], f) for w, f in v["files"].items()})
                   for k, v in FONTS.items()},
            scale=TYPE_SCALE,
            choice=FONT_CHOICE,
            names=NAME_FIT,
            fit=["Slots are sized in px (max_width_1x); a character count is only a guide "
                 "for proportional text.",
                 "If a string is wider than its slot: set it one role smaller (same face); "
                 "if still too wide, truncate with '…'. Never squash horizontally."],
            min_size=MIN_SIZE,
            italic=dict(method="shear glyph quads", S=SHEAR,
                        formula="x' = x + (baseline_y - y) * S"),
            ordinal=ORDINAL,
            charsets=dict(full="printable ASCII 0x20-0x7E + extras",
                          caps="ASCII without a-z + extras; engine uppercases hero/display text",
                          code="network codes only: " + CODE + " (anything else -> '?')",
                          extras=EXTRA),
        ),
        checks=report,
    )


def swatches(path):
    """One row per simulation: sections, then ports."""
    from PIL import Image, ImageDraw
    cols = [SECTIONS[s]["face"] for s in SECTIONS] + [PALETTE["gold"]] + list(PORTS.values())
    names = list(SECTIONS) + ["gold"] + list(PORTS)
    W, Hh = 70, 44
    img = Image.new("RGB", (W * len(cols) + 110, (Hh + 16) * len(CVD_KINDS) + 16), (20, 20, 24))
    dr = ImageDraw.Draw(img)
    for i, n in enumerate(names):
        dr.text((110 + i * W + 4, 2), n, fill=(200, 200, 200))
    for r, kind in enumerate(CVD_KINDS):
        y = 16 + r * (Hh + 16)
        dr.text((4, y + 16), kind, fill=(200, 200, 200))
        for i, h in enumerate(cols):
            c = tuple(round(v) for v in K.simulate(rgb(h), kind))
            dr.rectangle((110 + i * W, y, 110 + i * W + W - 4, y + Hh), fill=c)
    img.save(path)


def main():
    os.makedirs(os.path.join(OUT, "preview"), exist_ok=True)
    errs, report = check()
    with open(os.path.join(OUT, "kit.json"), "w", encoding="utf-8") as fh:
        json.dump(kit_dict(report), fh, indent=2, ensure_ascii=False)
    swatches(os.path.join(OUT, "preview", "kit_cvd_swatches.png"))

    for kind, v in report["port_distance"].items():
        print("ports %-13s closest dE %5.1f (%s/%s)" % (kind, *v["closest"]))
    for kind, v in report["section_face_closest"].items():
        print("sections %-10s closest dE %5.1f (%s/%s)" % (kind, *v))
    print("port label text:", {p: "%s %.2f" % (v["text"], v["contrast"])
                               for p, v in report["port_label_text"].items()})
    for s, r in report["sections"].items():
        print("  %-10s %s" % (s, r))
    if errs:
        print("\nCHECKS FAILED:")
        for e in errs:
            print("  - " + e)
        return 1
    print("\nkit checks ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
