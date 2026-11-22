"""Where the user's Brawl files are: the one hook for an unpack step (a disc-image unpacker can be added here
without touching the rest). Accepts an unpacked disc tree (<root>/fighter/..., <root>/files/fighter/...,
<root>/disc/files/fighter/...) or a Brawl mod build laid out as pf/fighter/<name>/Fit<Name>NN.pac|.pcs
(BrawlEx / BrawlCrate / BrawlInstaller builds). Disc images are NOT unpacked here: pass the unpacked folder.
"""
import os, re

SUBS = ("fighter", "files/fighter", "disc/files/fighter", "pf/fighter", "private/wii/app/RSBE/pf/fighter", "DATA/files/fighter")


class NotUnpacked(Exception):
    pass


def brawl_root(path):
    """-> the folder holding fighter/<name>/ for an unpacked tree or mod build; raises NotUnpacked otherwise."""
    if os.path.isfile(path):
        raise NotUnpacked("this is a file (a disc image?): unpack it first with your Brawl tools and choose the folder")
    for sub in SUBS:
        d = os.path.join(path, sub)
        if os.path.isdir(d): return d
    if any(re.match(r"Fit\w+\d\d\.(pac|pcs)$", f, re.I) for f in os.listdir(path)):
        return os.path.dirname(path)            # a single fighter folder was chosen
    raise NotUnpacked("no fighter/ folder found under it (looked for %s)" % ", ".join(SUBS))


def characters(root):
    """{name: [costume files]} for every fighter folder with Fit<Name>NN.pac/.pcs costumes."""
    out = {}
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if not os.path.isdir(d): continue
        cs = sorted(f for f in os.listdir(d) if re.match(r"Fit\w+?\d\d\.(pac|pcs)$", f, re.I))
        if cs: out[name] = [os.path.join(d, f) for f in cs]
    return out


def costume_number(path):
    m = re.search(r"(\d\d)\.(pac|pcs)$", path, re.I); return int(m.group(1)) if m else None


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser(); ap.add_argument("--brawl-root", required=True); a = ap.parse_args()
    r = brawl_root(a.brawl_root); print(json.dumps({k: [os.path.basename(f) for f in v] for k, v in characters(r).items()}, indent=1))
