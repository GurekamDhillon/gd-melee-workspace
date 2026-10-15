"""Post the 0.3.0 announcement (text only) to #announcements.

    python tools/discord/announce_022.py            # dry run (default): prints, sends nothing
    python tools/discord/announce_022.py --post     # sends ONE message to #announcements

The token stays in the adjacent
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
RELEASE = "https://github.com/GurekamDhillon/gd-melee-workspace/releases/tag/v0.3.0"
IMAGES = []
ALT = []

TEXT = f"""**GD's Melee 0.3.0 is out**
GD's Melee is a native PC port of Super Smash Bros. Melee (NTSC 1.02) for Windows and Linux: no emulator, built-in rollback netplay, m-ex mod support and Lua scripting.

**New in 0.3.0**
- UCF 0.84 on by default offline (toggle in Settings or the launcher)
- Up to six fighters in a match
- Melee-style character select with coins and hands; tap jump per player
- Nucleus mod browser: stage skins, effects, menus, audio, custom stages, opt-in mod fighters
- Stage skin picker (X/Y on stage select) and mod sync for online rooms
- Mod discs with m-ex dynamic alternate stages now play
- `.gdlp` replays (export to `.slp`), template fighters, engine effects
- Fixed: a second match in a session could crash

**Download (Windows + Linux):** <{RELEASE}>
You need your own Melee NTSC-U 1.02 disc image; no game data is included. Online is now protocol 9: 0.3.0 plays 0.3.0 only (not 0.2.x or the release candidates), so update both sides.
Mods from SSBM Nucleus - https://ssbmnucleus.net
Report bugs in <#{BUGS}>."""


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
