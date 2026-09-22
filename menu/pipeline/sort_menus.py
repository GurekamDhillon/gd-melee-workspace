"""Sort every vanilla menu texture into what replacing it actually needs.

    python pipeline/sort_menus.py

Reads ONLY the metadata index (meleedump/index/*.json): names, sizes,
formats, animation structure, dat/usd differences. It never opens a decoded
PNG. That is deliberate - this repo produces original art, and the sort has
to be possible without anyone on the art side looking at Melee's pixels.
Anything the metadata cannot settle goes to `review` with the file name, so a
person can look once and decide.

Writes meleedump/sort/SORT.md (the readable answer) and sort.json (every
texture with its bucket, confidence and reason).

Buckets, per texture:
  text          baked-in language-specific text -> replaced by the font atlas
  ip_character  per-character / per-costume art -> stays disc-loaded
  ip_stage      per-stage art -> stays disc-loaded
  roster_text   character/stage NAMES: roster-sized arrays that differ
                between .dat and .usd, so they are words, not pictures. The
                font atlas can render them from strings - whether to ship
                the names is a separate call from the art rule
  numerals      10/11-frame intensity arrays: a digit set 0-9 (+ a symbol)
                -> the font atlas's numerals, not ten icons
  icon_mask     small intensity-format mask: icon, glyph, shape -> kit-style
                white-mask icon, tinted by material (as the hub does)
  fx_mask       large intensity-format mask: glow, gradient, wipe -> usually
                better as geometry / vertex colour than as a texture
  chrome        small colour texture: panel piece, bar, frame -> the kit
  backdrop      large colour texture: background art -> new art, or
                flat geometry in the hub style
  review        metadata can't decide; named in SORT.md for one human look

Every screen gets a new layout regardless: the framework builds new menus
rather than reskinning Melee's scenes. So "needs a layout" is not a bucket;
what differs between screens is which ASSETS they need.
"""
import collections
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DUMP = os.path.join(ROOT, "meleedump")
INDEX = os.path.join(DUMP, "index")
OUT = os.path.join(DUMP, "sort")

INTENSITY = {"I4", "I8", "IA4", "IA8"}
SMALL_MASK = 128 * 128          # area; above this an intensity mask is fx
SMALL_CHROME = 64 * 64          # area; above this a colour texture is backdrop

# Screens whose big animation arrays are menu animation, not roster arrays.
# GmTitle's 30-frame array is the US title animation (confirmed by whoever
# ran the dump); MnMaAll/MnExtAll arrays sit in backdrop scenes.
NON_ROSTER_ARCHIVES = {"MnMaAll", "MnExtAll", "GmTitle", "GmTtAll"}

# Screens whose character content lives in files that were NOT dumped
# (trophy models, GmRstM*), per MANIFEST.md's dependency table. Taken from
# the dump's notes, not verified by walking those files.
EXTERNAL_IP = {"TyMnDisp": "trophy models", "TyMnFigp": "trophy models",
               "TyMnView": "trophy models", "IfPrize": "trophy models",
               "GmRegClr": "trophy models", "GmRst": "GmRstM* results models"}

# HUD entries that hold stock icons (one per character/costume)
STOCK_ENTRIES = re.compile(r"^(Stc_|ScInfStc)")


def friendly_names():
    names = {}
    with open(os.path.join(DUMP, "MANIFEST.md"), encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"\|\s*`([^`]+)`\s*\|\s*\d+\s*\|\s*([^|]+)\|", line)
            if m:
                names[m.group(1).split(".")[0]] = m.group(2).strip()
    return names


def screen_of(archive, entry):
    """MnMaAll/MnExtAll hold many scenes; group entries by scene prefix.
    Everything else is one screen per archive."""
    if archive in ("MnMaAll", "MnExtAll"):
        return archive + ":" + re.sub(r"_Top_.*$|_(joint|animjoint|matanim_joint|"
                                      r"shapeanim_joint)$", "", entry)
    return archive


def classify(archive, t):
    tags = {tg["tag"]: tg["reason"] for tg in t["tags"]}
    fmt, area = t["format"], t["w"] * t["h"]
    frames = t["anim_frames"] or 0
    entries = t["entries"]

    differs = "baked_text" in tags and tags["baked_text"].startswith("content differs")

    # --- roster arrays that change with language are names, not pictures
    if differs and (frames >= 100 or 24 <= frames <= 31):
        return "roster_text", "medium", ("%d-frame array that differs between .dat "
                                         "and .usd: per-roster names" % frames)

    # --- IP: per-character / per-stage pictures
    if frames >= 100 and archive not in NON_ROSTER_ARCHIVES:
        return "ip_character", "high", "%d-frame array: one per costume" % frames
    if any(STOCK_ENTRIES.match(e) for e in entries):
        return "ip_character", "high", "HUD stock-icon entry (%s)" % entries[0]
    if 24 <= frames <= 31:
        if archive == "MnSlMap":
            return "ip_stage", "medium", "%d-frame array on stage select: one per stage" % frames
        if archive not in NON_ROSTER_ARCHIVES:
            return "ip_character", "medium", "%d-frame array: one per character" % frames
        return "review", "low", ("%d-frame array in a menu scene: roster-sized, but "
                                 "could be menu animation" % frames)
    if any(e.startswith("MenMainFace") for e in entries):
        return "review", "low", "entry name suggests faces (%s)" % entries[0]

    # --- language
    if differs:
        if fmt in INTENSITY or (fmt in ("CI4", "CI8") and area <= 256 * 64):
            return "text", "high", "differs between .dat and .usd, %s" % fmt
        return "review", "medium", ("differs between .dat and .usd but is a large "
                                    "%s - localised art (e.g. a logo), not plain text" % fmt)

    # --- digit sets: 0-9, or 0-9 plus one symbol
    if fmt in INTENSITY and frames in (10, 11):
        return "numerals", "medium", "%d-frame %s array: digit set" % (frames, fmt)

    # --- everything else, by format and size
    if fmt in INTENSITY:
        if area <= SMALL_MASK:
            return "icon_mask", "medium", "%s %dx%d" % (fmt, t["w"], t["h"])
        return "fx_mask", "medium", "large %s %dx%d" % (fmt, t["w"], t["h"])
    if area <= SMALL_CHROME:
        return "chrome", "medium", "small %s %dx%d" % (fmt, t["w"], t["h"])
    if archive.startswith("If") or archive == "GmPause":
        # overlays have no backgrounds; a big colour texture here is most
        # likely a splash word or banner drawn in colour
        return "review", "low", ("large %s %dx%d in an in-game overlay: likely a "
                                 "splash word/banner, not a backdrop" % (fmt, t["w"], t["h"]))
    return "backdrop", "medium", "%s %dx%d" % (fmt, t["w"], t["h"])


def main():
    names = friendly_names()
    rows, orphans = [], {}
    for path in sorted(glob.glob(os.path.join(INDEX, "*.json"))):
        if os.path.basename(path).startswith("_"):
            continue
        d = json.load(open(path, encoding="utf-8"))
        if not d.get("decoded_to_png"):
            continue                      # the .dat twin of a .usd, or a data table
        archive = d["archive"].split(".")[0]
        orphans[archive] = len(d["cross_check"]["found_by_scan_only"])
        for t in d["textures"]:
            bucket, conf, why = classify(archive, t)
            screens = sorted({screen_of(archive, e) for e in t["entries"]})
            rows.append(dict(
                archive=archive, file=d["archive"], id=t["id"], png=t["file"],
                w=t["w"], h=t["h"], format=t["format"], bytes=t["image_bytes"],
                sha1=t["sha1"], animated=t["animated"], anim_frames=t["anim_frames"],
                screens=screens, bucket=bucket, confidence=conf, reason=why))

    BUCKETS = ["text", "roster_text", "numerals", "ip_character", "ip_stage",
               "icon_mask", "fx_mask", "chrome", "backdrop", "review"]

    # global totals, de-duplicated by content across archives. The same pixels
    # can be classified differently in two archives (only one has a .dat twin
    # to prove it is language text), so keep the most specific verdict.
    PRIORITY = {b: i for i, b in enumerate(
        ["roster_text", "text", "numerals", "ip_character", "ip_stage", "review",
         "icon_mask", "fx_mask", "chrome", "backdrop"])}
    uniq = {}
    for r in rows:
        cur = uniq.get(r["sha1"])
        if cur is None or PRIORITY[r["bucket"]] < PRIORITY[cur["bucket"]]:
            uniq[r["sha1"]] = r
    tot = collections.Counter(r["bucket"] for r in uniq.values())
    tot_kb = collections.Counter()
    for r in uniq.values():
        tot_kb[r["bucket"]] += r["bytes"] / 1024

    # per screen, de-duplicated within the screen
    per_screen = collections.defaultdict(lambda: collections.defaultdict(set))
    for r in rows:
        for s in r["screens"] or [r["archive"]]:
            per_screen[s][r["bucket"]].add(r["sha1"])

    # text geometry: how many font sizes does the atlas need?
    text_rows = [r for r in uniq.values() if r["bucket"] == "text"]
    heights = collections.Counter(r["h"] for r in text_rows)

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "sort.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(rules=__doc__, textures=rows, orphans=orphans), fh, indent=1)

    L = []
    L.append("# Vanilla menu sort — what replacing each screen needs\n")
    L.append("Generated by `pipeline/sort_menus.py` from `meleedump/index` "
             "metadata only — no pixels were opened. Confidence is the rule's, "
             "not a verified fact. Rules are in the script's docstring.\n")
    L.append("## Totals (unique textures, de-duplicated by content across archives)\n")
    L.append("| bucket | textures | KB (as stored) | what it means |")
    L.append("|---|---:|---:|---|")
    meaning = dict(
        text="font atlas replaces it — no per-texture art",
        roster_text="character/stage names — font atlas, if you ship names",
        numerals="digit sets — the font atlas's numerals",
        ip_character="stays disc-loaded; our framework composes around it",
        ip_stage="stays disc-loaded",
        icon_mask="new white-mask icon/shape in the kit style",
        fx_mask="glow/gradient/wipe — prefer geometry or vertex colour",
        chrome="kit pieces (panel, bar, frame)",
        backdrop="new background art, or flat geometry",
        review="needs one human look — listed below")
    for b in BUCKETS:
        L.append("| `%s` | %d | %.0f | %s |" % (b, tot[b], tot_kb[b], meaning[b]))
    L.append("| **all** | **%d** | **%.0f** | |" % (len(uniq), sum(tot_kb.values())))
    n_orph = sum(orphans.values())
    L.append("\nPlus **%d orphan images** found only by the byte scan, with no "
             "size/format in the index — unclassified. Per archive: %s.\n"
             % (n_orph, ", ".join("%s %d" % kv for kv in sorted(orphans.items()) if kv[1])))

    L.append("## Font atlas sizing\n")
    L.append("Heights of the %d baked-text textures (texels). Each cluster is "
             "roughly one text size the atlas needs:\n" % len(text_rows))
    L.append("| height | textures |")
    L.append("|---:|---:|")
    for h, n in sorted(heights.items()):
        L.append("| %d | %d |" % (h, n))
    widest = max(text_rows, key=lambda r: r["w"]) if text_rows else None
    if widest:
        L.append("\nWidest single text texture: %dx%d (%s) — the longest "
                 "line the layout has to fit.\n" % (widest["w"], widest["h"], widest["png"]))

    L.append("## Per screen\n")
    L.append("Counts are unique textures used by that screen. A texture shared by "
             "several screens counts in each.\n")
    L.append("| screen | what | text | names | digits | ip | icon | fx | chrome | backdrop | review | verdict |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")

    def verdict(c, s):
        ext = EXTERNAL_IP.get(s)
        ip = len(c["ip_character"]) + len(c["ip_stage"])
        if ext and not ip:
            return "**disc-dependent** (%s, per manifest)" % ext
        art = len(c["icon_mask"]) + len(c["backdrop"])
        if ip:
            return "**disc-dependent**" + (" (+ %s)" % ext if ext else "")
        if c["review"]:
            return "review first"
        if art == 0 and not c["fx_mask"]:        # text, numerals, chrome only
            return "font atlas + kit"
        return "font atlas + kit + new art"

    for s in sorted(per_screen, key=lambda s: (s.split(":")[0], s)):
        c = per_screen[s]
        arch = s.split(":")[0]
        L.append("| `%s` | %s | %d | %d | %d | %d | %d | %d | %d | %d | %d | %s |" % (
            s, names.get(arch, "") if ":" not in s else "", len(c["text"]),
            len(c["roster_text"]), len(c["numerals"]),
            len(c["ip_character"]) + len(c["ip_stage"]), len(c["icon_mask"]),
            len(c["fx_mask"]), len(c["chrome"]), len(c["backdrop"]),
            len(c["review"]), verdict(c, s)))

    L.append("\n## Review list\n")
    L.append("Textures the metadata can't settle. Files are in "
             "`Desktop\\meleedump\\textures\\<archive>\\`.\n")
    L.append("| archive | png | size | format | why |")
    L.append("|---|---|---|---|---|")
    rv = [r for r in uniq.values() if r["bucket"] == "review"]
    # collapse animation arrays to one line each
    seen = set()
    for r in sorted(rv, key=lambda r: (r["archive"], r["png"])):
        key = (r["archive"], r["reason"], r["w"], r["h"]) if r["animated"] else r["sha1"]
        if key in seen:
            continue
        seen.add(key)
        n = sum(1 for x in rv if r["animated"] and x["animated"] and
                (x["archive"], x["reason"], x["w"], x["h"]) == key)
        L.append("| %s | `%s`%s | %dx%d | %s | %s |" % (
            r["archive"], r["png"], " (+%d more frames)" % (n - 1) if n > 1 else "",
            r["w"], r["h"], r["format"], r["reason"]))

    with open(os.path.join(OUT, "SORT.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")

    print("%d texture references, %d unique" % (len(rows), len(uniq)))
    for b in BUCKETS:
        print("  %-13s %5d  %7.0f KB" % (b, tot[b], tot_kb[b]))
    print("  orphans       %5d  (unclassified)" % n_orph)
    print("screens: %d   -> %s" % (len(per_screen), os.path.relpath(OUT, ROOT)))


if __name__ == "__main__":
    main()
