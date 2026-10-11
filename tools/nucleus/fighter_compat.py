#!/usr/bin/env python3
"""fighter_compat.py - what GD's m-ex runtime could do with a MexManager fighter zip (fighter.json + Pl*.dat + Pl*AJ.dat + effect bank + sound.zip + costumes).

    python -I tools/nucleus/fighter_compat.py PACKAGE.zip     (prints the verdict; exit 0 always, 2 when the zip is unreadable)

It READS the zip only (no extraction to disk) and answers the browser's three words:
  works   every callback address is retail code (a clone of a retail fighter) and every file the json names is in the zip
  partial it would load but something is dropped (sound bank above the retail ones, a trophy/ending/demo file missing, Kirby copy data)
  needs-base  callbacks point outside the retail dol: the fighter was built against another clone base (ACE / Akaneia / a custom m-ex ISO)
The installer (pc/platform/gw_nucleus_fighter.h) computes the same verdict; the runtime LOADER is pc/platform/gw_mex_modfighter.inc.
"""
import json, sys, zipfile

RETAIL_LO, RETAIL_HI = 0x80000000, 0x81800000


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    try:
        z = zipfile.ZipFile(sys.argv[1])
        names = {n.split("/")[-1].lower(): n for n in z.namelist()}
        if "fighter.json" not in names:
            print("not a MexManager fighter zip: no fighter.json")
            return 2
        d = json.loads(z.read(names["fighter.json"]))
    except (zipfile.BadZipFile, ValueError, KeyError) as e:
        print("unreadable:", e)
        return 2
    notes, partial, needs = [], [], []
    f = d.get("files", {})
    for key in ("fighterDataPath", "animFile", "effectFile"):
        fn = f.get(key, "")
        if fn and fn.lower() not in names:
            needs.append("%s %s is not in the zip" % (key, fn))
    out = []
    for k, v in sorted((d.get("functions") or {}).items()):
        if isinstance(v, int) and v >= 0x100000 and not (RETAIL_LO <= v < RETAIL_HI):
            out.append(k)
        if isinstance(v, int) and v >= RETAIL_HI and v < 0xFFFFFFFF:
            out.append(k)
    if out:
        needs.append("%d callback(s) outside the retail dol (%s...): built for another clone base" % (len(out), ", ".join(out[:3])))
    if int(d.get("soundBank", 0)) > 54:
        partial.append("sound bank %s is not a retail bank" % d.get("soundBank"))
    if d.get("hasKirbyCostumes") or f.get("kirbyCapFileName"):
        partial.append("Kirby copy hat not supported on a vanilla disc")
    if d.get("items"):
        needs.append("%d custom item(s) need the item tables of an m-ex disc" % len(d["items"]))
    if int(d.get("announcerCall", -1) or -1) > 0:
        partial.append("announcer call is the clone base's")
    if "sound.zip" in names and int(d.get("soundBank", 0)) <= 54:
        partial.append("sound.zip is not installed (retail sound bank used)")
    for c in d.get("costumes", []):
        fn = (c.get("file") or {}).get("fileName", "")
        if fn and fn.lower() not in names and fn.lower().replace(".dat", ".zip") not in names:
            partial.append("costume file %s missing" % fn)
    verdict = "needs-base" if needs else "partial" if partial else "works"
    print("%s: %s | %s | %d callbacks, %d costumes" % (verdict, d.get("name"), "; ".join(needs + partial) or "all callbacks are retail code", len(d.get("functions") or {}), len(d.get("costumes", []))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
