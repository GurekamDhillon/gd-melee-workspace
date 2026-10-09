"""Post the 0.2.2 announcement (text + chart images) to #announcements.

    python tools/discord/announce_022.py            # dry run (default): prints, sends nothing
    python tools/discord/announce_022.py --post     # sends ONE message to #announcements

Render the chart first: python menu/pipeline/announce_chart.py. The token stays in the adjacent
git-ignored .env (discord_setup.API reads it); it is never printed. No mentions are allowed
(allowed_mentions parse=[]), like every earlier post in tools/discord. Run --post only when the
owner has approved the text and images.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from discord_setup import API, GUILD_ID, ROOT  # noqa: E402

ANNOUNCEMENTS = "1552904416305225770"   # state.json channels.announcements (type 5, read-only to members)
BUGS = "1552904442171359266"            # state.json channels.bugs
RELEASE = "https://github.com/GurekamDhillon/gd-melee-workspace/releases/tag/v0.2.2"
IMAGES = [ROOT / "menu/out_announce/chart_1.png", ROOT / "menu/out_announce/chart_2.png"]
ALT = ["GD's Melee 0.2.2 vs vanilla Melee: platform and online",
       "GD's Melee 0.2.2 vs vanilla Melee: content, modes, quality of life, download"]

TEXT = f"""**GD's Melee 0.2.2 is out**
GD's Melee is a native PC port of Super Smash Bros. Melee (NTSC 1.02) for Windows and Linux: no emulator, built-in rollback netplay, m-ex mod support and Lua scripting.

**New in 0.2.2**
- In-game mod browser for SSBM Nucleus, with an install queue that survives restarts
- Everything unlocked from the start (Settings > Gameplay turns it off)
- Fullscreen (F11 / Alt+Enter) and 255 costumes per fighter
- Online: tied games replay instead of sudden death; Envoy sets resume after a disconnect
- Stricter disc check online, much faster Linux rollback snapshots

The charts below put everything in our build next to vanilla Melee.

**Download (Windows + Linux):** <{RELEASE}>
You need your own Melee NTSC-U 1.02 disc image; no game data is included. 0.2.2 plays 0.2.2 (Windows and Linux), not 0.2.1 or earlier, so update both sides.
Mods from SSBM Nucleus - https://ssbmnucleus.net
Public test build: report bugs in <#{BUGS}>."""


def payload():
    return {"content": TEXT, "allowed_mentions": {"parse": []},
            "attachments": [{"id": i, "filename": p.name, "description": ALT[i]} for i, p in enumerate(IMAGES)]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--post", action="store_true", help="really send (default is a dry run)")
    ap.add_argument("--dry-run", action="store_true", help="the default; accepted for clarity")
    a = ap.parse_args()
    if a.post and a.dry_run:
        ap.error("choose one")
    body = payload()
    assert len(TEXT) <= 2000, "Discord limit"
    for p in IMAGES:
        assert p.exists(), f"missing {p}: run menu/pipeline/announce_chart.py"
    print(f"{'POST' if a.post else 'DRY RUN'}: channel {ANNOUNCEMENTS} (#announcements, guild {GUILD_ID})")
    print(f"text: {len(TEXT)} chars; allowed_mentions={body['allowed_mentions']}")
    for p in IMAGES:
        print(f"attachment: {p.name} {p.stat().st_size} bytes")
    print("--- text ---\n" + TEXT + "\n--- end ---")
    if not a.post:
        print("Dry run only: nothing sent. Re-run with --post to send.")
        return
    api = API()
    api.inspect()   # registers the channel ids the scope guard allows
    files = [(p.name, p.read_bytes()) for p in IMAGES]
    m = api.request("POST", f"/channels/{ANNOUNCEMENTS}/messages", body, files)
    print("posted:", f"https://discord.com/channels/{GUILD_ID}/{ANNOUNCEMENTS}/{m['id']}")


if __name__ == "__main__":
    main()
