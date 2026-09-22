"""THE LOADING SCREEN: between the stage select (or the online lobby) and the match, on the kit.

    python pipeline/kit.py && python pipeline/font_atlas.py && python pipeline/glyphs.py \
        && python pipeline/icons.py && python pipeline/kit_ui.py && python pipeline/online.py \
        && python pipeline/lobby.py && python pipeline/loading.py

Writes out_loading/:
    loading_layout.json   the fighters' cards (two big, or up to four compact), the VS mark, the
                          stage plate (the stage's select icon, its name; online: room, game and
                          set), the progress bar and its readout; the chrome's description strip
                          carries the status line
    loading_motion.json   cards in, VS pop, stage in, ready (the bar tops out)
    icons_manifest.json   this section's mask (I4)
    manifest.json         textures per screen, memory, check results
    2x/ 1x/               the mask
    preview/*.png         composed from the JSON alone (lobby.py's element walker)

Same layout format as the lobby (lobby.py docstring): unsheared template space, kit colour
tokens, "<axis.key>" state lookups and "when". The engine fills the slots listed under
slots_engine_fills and sets the progress fill's right edge from real warm-up progress.
Everything here is original: drawn from SVG in this file, nothing traced, sampled or recoloured
from Melee or any other game.
"""
import json
import os
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit                                                  # noqa: E402
import kit_ui as U                                          # noqa: E402
import icons as IC                                          # noqa: E402
import online as ON                                         # noqa: E402
import lobby as LB                                          # noqa: E402
from build import downscale_half, save_png                 # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out_loading")
S, Y0 = kit.SHEAR, 240
SECTION = "versus"
text_w, base_for, cap = U.text_w, U.base_for, U.cap
QT, TT, draw_el = LB.QT, LB.TT, LB.draw_el
U.TEX_DIRS.append(os.path.join(OUT, "2x"))
U.TEX_DIRS.append(os.path.join(ROOT, "out_lobby", "2x"))

# ================================================================ the mask
ICONS = {
    "ico_bolt": dict(set="loading", size_2x=128, min_draw_1x=24,
                     use="the VS mark between the two fighters' cards: a lightning bolt",
                     body=IC.P("M38 2 L12 36 H29 L22 62 L52 24 H35 L44 2 Z")),
}


def build_icons(page):
    errs, rows = [], []
    for sub in ("2x", "1x", "preview"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    for name, ic in ICONS.items():
        img = IC.render(page, ic)
        save_png(img, os.path.join(OUT, "2x", name + ".png"))
        save_png(downscale_half(img), os.path.join(OUT, "1x", name + ".png"))
        full = IC.topology(img.getchannel("A"))
        small = IC.topology(IC.shrink(img, 2 * ic["min_draw_1x"]))
        if img.getchannel("A").getbbox() is None:
            errs.append("%s is empty" % name)
        if full != small:
            errs.append("%s loses its shape at %d px (%s -> %s)" % (name, ic["min_draw_1x"],
                                                                     full, small))
        rows.append(dict(name=name, file_2x="out_loading/2x/%s.png" % name,
                         file_1x="out_loading/1x/%s.png" % name, size_2x=[128, 128],
                         format="I4", fallback="IA4", min_draw_1x=ic["min_draw_1x"],
                         why=ic["use"], topology=list(full)))
    return errs, rows


# ================================================================ geometry
BIG = (200, 200)                       # a card when two fight
SMALL = (112, 200)                     # up to four
CARDS_Y = 84
BIG_X = dict(p1=92, p2=348)            # 92..292 | 56 gap | 348..548
SMALL_X0, SMALL_GAP = 92, 8            # 4 x 112 + 3 x 8 = 472 -> 92..564
STAGE = (92, 298, 548, 350)
BAR = (92, 362, 548, 372)
NAME_MAX = "Captain Falcon Alt 2"      # 20 characters, the kit's name rule
STAGE_MAX = "Princess Peach's Castle"
TAG_MAX = "GUEST"


def card(template, w, h):
    """A fighter's card, origin top-left; the engine sets <p> (p1..p4) per instance."""
    pad = 12 if w >= 160 else 8
    fy0, fy1 = 32, h - 46                          # the portrait's frame
    fw = w - 2 * pad
    # the captured CSS icon is 8:7 - as wide as the frame allows, centred
    aw = min(fw - 8, int((fy1 - fy0 - 8) * 8 / 7))
    ah = int(aw * 7 / 8)
    ax0 = (w - aw) / 2
    ay0 = fy0 + 4 + (fy1 - fy0 - 8 - ah) / 2
    name_role = "label" if w >= 160 else "body"
    return dict(
        id=template, size=[w, h], lift_joint=None,
        quads=[QT("card_outline", (-3, -3, w + 3, h + 3), "ink", joint="card_<p>"),
               QT("card_face", (0, 0, w, h), "@face", joint="card_<p>"),
               QT("port_band", (0, 0, w, 6), "port:<p>", joint="card_<p>"),
               QT("port_tab", (pad, 12, pad + 32, 28), "port:<p>", joint="card_<p>"),
               QT("portrait_frame", (pad, fy0, w - pad, fy1), "ink", joint="card_<p>"),
               dict(QT("portrait_art", (ax0, ay0, ax0 + aw, ay0 + ah), "#ffffff",
                       joint="card_<p>"), kind="disc_art", size_1x=[aw, ah],
                    note="the fighter's CSS icon, captured on the CSS (the engine's)"),
               QT("cpu_band", (pad, fy1 - 14, w - pad, fy1), "ink", joint="card_<p>",
                  opacity=0.75, kind=["cpu"])],
        slots=[TT("port_label", "caption", (pad + 16, 24.96), "P4", "ink", align="centre",
                  joint="card_<p>", max_width=28),
               TT("you_tag", "caption", (pad + 40, 24.96), "YOU", "gold", joint="card_<p>",
                  you=["yes"]),
               TT("tag", "caption", (w - pad, 24.96), TAG_MAX, "muted", align="right",
                  joint="card_<p>", max_width=w - 2 * pad - 72 if w >= 160 else w - 2 * pad - 36,
                  note="HOST / GUEST online; CPU for a computer player; empty otherwise"),
               TT("cpu_text", "caption", (w / 2, fy1 - 3.04), "CPU LV 9", "bone",
                  align="centre", joint="card_<p>", max_width=fw - 8, kind=["cpu"]),
               TT("name", name_role, (w / 2, h - 22), NAME_MAX if w >= 160 else "Captain Falcon",
                  "bone", align="centre", joint="card_<p>", max_width=w - 2 * pad,
                  note="the fighter's name (m-ex names from the fighter table); fit rule - "
                       "a compact card holds 14 characters at caption, longer names end in "
                       "an ellipsis")],
        states=dict(you=dict(yes={}, no={}),
                    kind=dict(human={}, cpu=dict(note="a computer player: its level on a band "
                                                      "over the portrait"))))


def layout():
    sx0, sy0, sx1, sy1 = STAGE
    bx0, by0, bx1, by1 = BAR
    icon_x0, icon_x1 = sx0 + 12, sx0 + 12 + 52          # the stage's select icon, 52x44
    tx = icon_x1 + 12
    vs = dict(
        id="vs_mark",
        quads=[QT("vs_bolt", (300, 146, 340, 206), "gold", texture="ico_bolt", joint="vs")],
        slots=[TT("vs_text", "title", (320, 234.92), "VS", "bone", align="centre", joint="vs")])
    stage = dict(
        id="stage_plate",
        quads=[QT("stage_ink", (sx0 - 3, sy0 - 3, sx1 + 3, sy1 + 3), "ink", joint="stage"),
               QT("stage_face", STAGE, "@face", joint="stage"),
               QT("stage_accent", (sx0, sy0, sx0 + 4, sy1), "gold", joint="stage"),
               QT("icon_frame", (icon_x0 - 2, sy0 + 4, icon_x1 + 2, sy1 - 4), "ink",
                  joint="stage"),
               dict(QT("stage_art", (icon_x0, sy0 + 6, icon_x1, sy1 - 6), "#ffffff",
                       joint="stage"), kind="disc_art", size_1x=[52, 40], optional=True,
                    note="the stage's select icon, captured on the SSS; absent (online) -> "
                         "@face_hi at 0.35")],
        slots=[TT("stage_label", "caption", (tx, sy0 + 17.96), "STAGE", "muted",
                  joint="stage"),
               TT("stage_name", "title", (tx, sy1 - 9.08), STAGE_MAX, "bone", joint="stage",
                  max_width=236),
               TT("set_line", "caption", (sx1 - 12, sy0 + 17.96), "GAME 5 - SET 2 - 2",
                  "gold", align="right", joint="stage", view=["online"]),
               TT("room_line", "body", (sx1 - 12, sy1 - 10.38), "ROOM KQ7X", "bone",
                  align="right", joint="stage", view=["online"])],
        states=dict(view=dict(local={}, online={})))
    bar = dict(
        id="progress",
        quads=[QT("bar_track", BAR, "ink", joint="bar"),
               dict(QT("bar_fill", BAR, "<bar.fill>", joint="bar_fill"),
                    note="the engine sets its right edge: x1 = x0 + (x1 - x0) * progress")],
        slots=[TT("bar_label", "caption", (bx0, by1 + 15.96), "WARMING UP", "muted",
                  joint="bar", note="WARMING UP while below 100%, READY at 100%"),
               TT("bar_pct", "caption", (bx1, by1 + 15.96), "100%", "bone", align="right",
                  joint="bar")],
        states=dict(bar=dict(working=dict(fill="gold"), ready=dict(fill="ok"))))
    cards = dict(big=card("card_big", *BIG), small=card("card_small", *SMALL))
    lay = dict(
        name="loading", space="unsheared", shear=dict(S=S, Y0=Y0), section=SECTION,
        element_format="see pipeline/lobby.py docstring: <axis.key> lookups and 'when'",
        chrome=dict(template="chrome_layout.json", title="GET READY",
                    crumbs=dict(local=["VERSUS", "MELEE", "LOADING"],
                                online=["VERSUS", "ONLINE PLAY", "ROOM KQ7X"]),
                    crumb_icon="ico_versus", hints=[],
                    description="the status line: 'Loading the match...', then 'Here we go!'"),
        cards=cards,
        card_places=dict(
            two=dict(template="card_big", origins=[[BIG_X["p1"], CARDS_Y],
                                                   [BIG_X["p2"], CARDS_Y]]),
            up_to_four=dict(template="card_small",
                            origins=[[SMALL_X0 + i * (SMALL[0] + SMALL_GAP), CARDS_Y]
                                     for i in range(4)],
                            rule="n cards centred as a group on x = 320 + (4 - n) * 60 / 2 "
                                 "shift; with 3, the first three origins moved right by 60")),
        vs_mark=vs,
        stage_plate=stage,
        progress=bar,
        slots_engine_fills=dict(
            chrome_crumbs="local: VERSUS / MELEE / LOADING; online: VERSUS / ONLINE PLAY / "
                          "ROOM <code>",
            card=dict(port_label="P1..P4", you_tag="online: this machine's card",
                      tag="HOST / GUEST online, CPU for a computer", name="fighter name",
                      portrait_art="captured CSS icon", cpu_text="CPU LV n"),
            vs_mark="two fighters only",
            stage=dict(stage_art="captured SSS icon (local)", stage_name="the stage",
                       set_line="online: GAME n - SET a - b", room_line="online: ROOM <code>"),
            progress="fill from the real warm-up progress; bar_pct 'n%'; bar state ready at "
                     "100%",
            status="the description strip"),
        rules=[
            "Shown after the stage select (local) and after the lobby's countdown (online), "
            "until the renderer has built what the match draws first (the pipeline seed's "
            "core), with a minimum so it never flashes and a ceiling so it never traps.",
            "Two fighters: the big cards and the VS mark. Three or four: the compact cards, no "
            "VS mark.",
            "Online both machines show the same screen; each marks its own card YOU."],
        textures=[])
    return lay


# ================================================================ motion
k, tr = U.k, U.tr


def motion():
    ev = {}
    ev["cards_in"] = dict(
        applies_to="on arrival: P1 slides in from the left, P2 from the right (compact cards: "
                   "each from below, 3 frames apart)",
        tracks=[tr("card_p1", "TRA_X", k(0, -48), k(12, 4), k(16, 0)),
                tr("card_p1", "ALPHA", k(0, 0, "LIN"), k(8, 1, "LIN")),
                tr("card_p2", "TRA_X", k(0, 48), k(12, -4), k(16, 0)),
                tr("card_p2", "ALPHA", k(0, 0, "LIN"), k(8, 1, "LIN"))],
        length_frames=16)
    ev["vs_pop"] = dict(
        applies_to="the VS mark, after the cards land",
        tracks=[tr("vs", "SCA_X", k(0, 0), k(10, 0), k(16, 1.3), k(22, 1)),
                tr("vs", "SCA_Y", k(0, 0), k(10, 0), k(16, 1.3), k(22, 1))],
        length_frames=22)
    ev["stage_in"] = dict(
        applies_to="the stage plate rises into place",
        tracks=[tr("stage", "TRA_Y", k(0, 16), k(10, -2), k(14, 0)),
                tr("stage", "ALPHA", k(0, 0, "LIN"), k(8, 1, "LIN"))],
        length_frames=14)
    ev["ready"] = dict(
        applies_to="the bar tops out: the fill pops (state 'ready' turns it ok-green)",
        tracks=[tr("bar_fill", "SCA_Y", k(0, 1), k(4, 1.8), k(10, 1))],
        length_frames=10)
    return dict(fps=60, format=LB.FORMAT, space="unsheared - applied before the screen shear",
                events=ev,
                sequences=dict(arrive=[dict(event="cards_in"), dict(event="vs_pop", at_frame=6),
                                       dict(event="stage_in", at_frame=8)],
                               ready=[dict(event="ready")]))


# ================================================================ previews
def draw_loading(view, players, stage, pct, crumbs, set_line=None, room=None,
                 status="Loading the match..."):
    L = LAY
    sc = U.Scene(SECTION)
    LB.chrome(sc, L["chrome"]["title"], crumbs, [], status)
    n = len(players)
    place = L["card_places"]["two" if n == 2 else "up_to_four"]
    el = L["cards"]["big" if n == 2 else "small"]
    origins = place["origins"]
    if n == 3:
        origins = [[x + 60, y] for x, y in origins[:3]]
    for i, p in enumerate(players):
        axes = dict(you="yes" if p.get("you") else "no", kind=p.get("kind", "human"),
                    p="p%d" % (i + 1))
        e = json.loads(json.dumps(el).replace("port:<p>", "port:p%d" % (i + 1)))
        draw_el(sc, e, axes, dict(port_label="P%d" % (i + 1), you_tag="YOU",
                                  tag=p.get("tag", ""), name=p["name"],
                                  cpu_text=p.get("cpu", "")), origin=origins[i])
    if n == 2:
        draw_el(sc, L["vs_mark"], {}, dict(vs_text="VS"))
    draw_el(sc, L["stage_plate"], dict(view=view),
            dict(stage_label="STAGE", stage_name=stage, set_line=set_line, room_line=room))
    bar = L["progress"]
    st = "ready" if pct >= 100 else "working"
    x0, y0, x1, y1 = BAR
    sc.quad(BAR, "ink")
    sc.quad((x0, y0, x0 + (x1 - x0) * pct / 100.0, y1), bar["states"]["bar"][st]["fill"])
    draw_el(sc, bar, dict(bar=st), dict(bar_label="READY" if pct >= 100 else "WARMING UP",
                                        bar_pct="%d%%" % pct),
            skip=("bar_track", "bar_fill"))
    return sc


def checks(L):
    errs = []
    def walk(o):
        if isinstance(o, dict):
            if o.get("kind") == "text":
                w = text_w(o["role"], o["max"])
                if w > o["max_width_1x"] + 0.5 and o["role"] not in ("caption",):
                    # the fit rule steps down to caption, then truncates: check the caption fits
                    if text_w("caption", o["max"]) > o["max_width_1x"] + 0.5:
                        errs.append("%s: '%s' is %.1f px > %.1f even at caption"
                                    % (o["id"], o["max"], w, o["max_width_1x"]))
                elif w > o["max_width_1x"] + 0.5:
                    errs.append("%s: '%s' %.1f px > %.1f" % (o["id"], o["max"], w,
                                                              o["max_width_1x"]))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(L)
    sx0, sy0, sx1, sy1 = U.SAFE
    for x0, y0, x1, y1 in (STAGE, BAR):
        if x0 < sx0 or x1 + (Y0 - y0) * S > sx1 + 40 or y1 > sy1:
            errs.append("a plate leaves the title-safe box")
    return errs


LAY = None


def main():
    global LAY
    sys.stdout.reconfigure(encoding="utf-8")
    ON.LAY = ON.layout()
    errs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(device_scale_factor=1)
        ierrs, rows = build_icons(page)
        errs += ierrs
        LAY = layout()
        mot = motion()
        errs += checks(LAY)
        sc = dict(
            loading_local=draw_loading(
                "local", [dict(name="Captain Falcon Alt 2"),
                          dict(name="Wario Man, Microgame", kind="cpu", tag="CPU",
                               cpu="CPU LV 9")],
                "Fountain of Dreams", 64, LAY["chrome"]["crumbs"]["local"]),
            loading_online=draw_loading(
                "online", [dict(name="Wolf", you=True, tag="HOST"),
                           dict(name="Sonic", tag="GUEST")],
                "Pokemon Stadium", 100, LAY["chrome"]["crumbs"]["online"],
                set_line="GAME 2 - SET 1 - 0", room="ROOM KQ7X", status="Here we go!"),
            loading_four=draw_loading(
                "local", [dict(name="Wolf"), dict(name="Sonic"),
                          dict(name="Knuckles", kind="cpu", tag="CPU", cpu="CPU LV 4"),
                          dict(name="Lucina", kind="cpu", tag="CPU", cpu="CPU LV 9")],
                STAGE_MAX, 30, LAY["chrome"]["crumbs"]["local"]))
        names = set()
        for s_ in sc.values():
            names |= {it["tex"] for it in s_.items if it["tex"]}
        LAY["textures"] = [r for r in rows if r["name"] in names]
        with open(os.path.join(OUT, "loading_layout.json"), "w", encoding="utf-8") as fh:
            json.dump(LAY, fh, indent=1, ensure_ascii=False)
        with open(os.path.join(OUT, "loading_motion.json"), "w", encoding="utf-8") as fh:
            json.dump(mot, fh, indent=1, ensure_ascii=False)
        with open(os.path.join(OUT, "icons_manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(dict(provenance="Original pictogram drawn in pipeline/loading.py (SVG on a "
                                      "64 grid); nothing traced, sampled or recoloured.",
                           textures=rows), fh, indent=1)
        mem = {}
        for n, s_ in sc.items():
            b, used = LB.memory(s_)
            mem[n] = round(b / 1024, 1)
            if b > U.BUDGET:
                errs.append("%s uses %.0f KB > 1 MB" % (n, b / 1024))
        with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(dict(provenance="Original. Layout, motion and mask from "
                                      "pipeline/loading.py.",
                           convert="from melee/: python pc/tools/png2gx.py --layout "
                                   "../menu/out_loading/loading_layout.json --outdir ../_build/ui",
                           textures=rows, memory_2x_per_screen_kb=mem,
                           checks=dict(errors=errs)), fh, indent=1)
        tx = U.Textures()
        for n, s_ in sc.items():
            img = U.render(page, s_, tx)
            img.save(os.path.join(OUT, "preview", "%s_2x.png" % n))
            downscale_half(img.convert("RGBA")).convert("RGB").save(
                os.path.join(OUT, "preview", "%s_1x.png" % n))
        browser.close()
    print("loading: %d mask, %d previews, memory %s" % (len(rows), len(sc), mem))
    if errs:
        print("CHECKS FAILED:")
        for e in errs:
            print("  - " + e)
        return 1
    print("loading checks ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
