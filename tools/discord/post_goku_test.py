"""Post the Goku ALPHA test-build announcement (text + videos + cards) to its Discord channel.

    python tools/discord/post_goku_test.py                    # dry run (default): resolves the channel, prints text and attachments, sends nothing
    python tools/discord/post_goku_test.py --post --zip-link URL   # sends (only when the owner has approved the text and the media)

The token stays in the adjacent git-ignored .env (discord_setup.API reads it) and is never printed. No mentions are allowed
(allowed_mentions parse=[]). The channel id is fixed (CHANNEL below) and resolved through the API; the script prints its name,
the guild's boost tier and the upload limit that tier gives (10 MiB on tier 0/1, 50 MiB on tier 2, 100 MiB on tier 3 as of the
2024 limits; the script re-checks the real file sizes against that). Media comes from _build/goku-media (git-ignored: Goku is
never committed or put on GitHub). Files are grouped into messages of at most GROUP_MB and 10 files, the text rides on the first.
--post refuses while any TODO-CONFIRM marker is left in the text or the download link is missing.
"""
import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from discord_setup import API, GUILD, GUILD_ID  # noqa: E402

CHANNEL = "1558288588070723674"        # the Goku test channel (custom-fighters)
BUGS = "1552904442171359266"           # state.json channels.bugs
MEDIA = Path("E:/Projects/Melee Workspace/_build/goku-media")
LIMITS_MIB = {0: 10, 1: 10, 2: 50, 3: 100}
GROUP_MB = 9.5                          # per message, under the 10 MiB tier-0 limit

TEXT_1 = """**GOKU - ALPHA test build**
An early, playable Goku for GD's Melee, built by hand from Xenoverse 2 move data. This is an **alpha**: hitboxes are still being hand-authored, balance is unfinished, some animations are rough, and bugs are expected. Bug reports are the whole point of this build.

**What is in it**
- A ki meter: hits and charging fill it, specials spend it
- Kamehameha (tap, charged, and Super at full ki), Dragon Rush into the Rush Combo, flight on up B with flight aerials and ledge grabs
- A light string with heavy finishers, launcher into air strings, spiking aerials, charged smashes
- Ki charge (down B, ground and air), shield + B homing dash kick, D-pad ki blast barrage
- Instant Transmission roll, Falcon-style grab and throws, ledge options
The reel is attached. The controls and combo cards are in the next message."""

TEXT_2 = """**Controls** (cards attached: controls, then the four combo cards)
- Light string: A, A, A, A, A (each hit must connect). Heavy: C-stick off a light hit (up launches, forward finishes, down is the down smash)
- Kamehameha: B starts the charge, B again fires. Shield stores it
- Dragon Rush: forward + B. Flight: up + B, then A or C-stick
- Ki charge: hold down + B. Ki blast: D-pad down (hold for a barrage). Dash kick: shield + B with the stick neutral
- Instant Transmission roll: shield + left or right

**Install**
{INSTALL}

**Known issues**
- Alpha balance and hitboxes: expect numbers to change
- The down air may show a hitbox on the landing frame (not confirmed)
- The costume arrows on the character select show "n / 5" instead of the costume name
- No announcer call and no series emblem yet
- Placeholder sounds except Kamehameha and Instant Transmission
- Hitboxes are samples that are still being hand-authored
- Online: both sides need the exe in this zip (netplay protocol 9; it won't connect to rc5) and the same Goku package (a mismatch is refused with a message); not yet tested online with this build

**Report bugs** in <#{BUGS}>: say what you pressed, the stage and what you expected. Screenshots and clips help."""

TEXT_3 = "**Screenshots**: the character select with Goku (five costumes) and in-game moments."
TEXT_4 = "**Move previews**: Kamehameha, the light string, Dragon Rush, the ki blast barrage and a reverse ledge grab from flight."

INSTALL_ZIP = ("1. Download the Goku alpha zip: {LINK}\n"
               "2. Unzip it over your GD's Melee 0.3.0-rc5 folder (say yes to replace melee-pc.exe) or into a fresh folder\n"
               "3. Run GD Melee, check Goku is on in Mods, pick him on the character select")


def plan_files():
    reel = MEDIA / "reel/goku_alpha_reel_720p30.mp4"
    cards = [MEDIA / "overlays/card_controls.png"] + sorted((MEDIA / "cards").glob("card_[1-4]_*.png")) + [MEDIA / "overlays/card_costumes.png"]
    stills = sorted((MEDIA / "stills").glob("*.png"))
    gifs = [MEDIA / "gifs" / (n + ".gif") for n in ("kame_charged", "light_heavy", "rush", "ki_blast", "flight_ledge")]
    return [("reel", [reel], TEXT_1), ("cards", cards, TEXT_2), ("stills", stills, TEXT_3), ("gifs", gifs, TEXT_4)]


def group(files):
    out, cur, size = [], [], 0.0
    for f in files:
        mb = f.stat().st_size / 1048576
        if cur and (size + mb > GROUP_MB or len(cur) >= 10):
            out.append(cur); cur, size = [], 0.0
        cur.append(f); size += mb
    if cur:
        out.append(cur)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--post", action="store_true", help="really send (default is a dry run)")
    ap.add_argument("--zip-link", default="", help="where the Goku zip is hosted (the zip is over the upload limit)")
    a = ap.parse_args()

    api = API()
    info = api.inspect()                       # registers the channel ids the scope guard allows
    guild = info["guild"]
    tier = guild.get("premium_tier", 0)
    limit = LIMITS_MIB.get(tier, 10)
    ch = next((c for c in info["channels"] if c["id"] == CHANNEL), None)
    if ch is None:
        sys.exit("channel %s not found in the guild" % CHANNEL)
    print("guild: %s (%s) boost tier %s -> upload limit %d MiB" % (guild["name"], GUILD_ID, tier, limit))
    print("channel: #%s (%s) type %s" % (ch["name"], CHANNEL, ch["type"]))
    roles = {r["id"]: r for r in api.request("GET", GUILD + "/roles")}
    perms = int(roles[GUILD_ID]["permissions"])
    for rid in info["bot_member"].get("roles", []):
        perms |= int(roles[rid]["permissions"])
    if perms & (1 << 3):
        print("bot permissions: administrator (channel overwrites do not remove it)")
    else:
        # apply the channel's overwrites in Discord's order: @everyone, then roles, then the member
        for ow in ch.get("permission_overwrites", []):
            if ow["id"] == GUILD_ID:
                perms = (perms & ~int(ow["deny"])) | int(ow["allow"])
        for ow in ch.get("permission_overwrites", []):
            if ow["type"] == 0 and ow["id"] in info["bot_member"].get("roles", []):
                perms = (perms & ~int(ow["deny"])) | int(ow["allow"])
        print("bot can view/send/attach in the channel: %s / %s / %s" % tuple(bool(perms & (1 << b)) for b in (10, 11, 15)))

    zip_path = MEDIA / "package/GokuAlpha-test.zip"
    zip_mb = zip_path.stat().st_size / 1048576 if zip_path.exists() else None
    if zip_mb is not None:
        print("zip: %s %.1f MiB (%s the %d MiB limit)" % (zip_path.name, zip_mb, "over" if zip_mb > limit else "within", limit))
    link = a.zip_link or "{ZIP LINK: host the zip, then pass --zip-link}"
    text1 = TEXT_1
    text2 = TEXT_2.replace("{INSTALL}", INSTALL_ZIP.replace("{LINK}", link)).replace("{BUGS}", BUGS)
    for t in (text1, text2, TEXT_3, TEXT_4):
        assert len(t) <= 2000, "Discord message limit: %d" % len(t)
    msgs = []
    texts = {TEXT_1: text1, TEXT_2: text2, TEXT_3: TEXT_3, TEXT_4: TEXT_4}
    for name, files, text in [(n, f, texts[t]) for n, f, t in plan_files()]:
        missing = [f for f in files if not f.exists()]
        if missing:
            print("MISSING media:", ", ".join(str(m) for m in missing))
        files = [f for f in files if f.exists()]
        for i, g in enumerate(group(files) or [[]]):
            msgs.append((text if i == 0 else "", g))
    for i, (t, g) in enumerate(msgs, 1):
        print("--- message %d: %d chars, %d file(s) %.1f MiB" % (i, len(t), len(g), sum(f.stat().st_size for f in g) / 1048576))
        for f in g:
            mb = f.stat().st_size / 1048576
            print("    %s %.2f MiB%s" % (f.name, mb, "  OVER LIMIT" if mb > limit else ""))
        print(t)
    blockers = []
    if any("TODO-CONFIRM" in t for t, _ in msgs):
        blockers.append("TODO-CONFIRM markers left in the text")
    if "{ZIP LINK" in "".join(t for t, _ in msgs):
        blockers.append("no --zip-link")
    if any(f.stat().st_size / 1048576 > limit for _, g in msgs for f in g):
        blockers.append("a file is over the upload limit")
    if not a.post:
        print("\nDry run only: nothing sent. Blockers for --post: %s" % (blockers or "none"))
        return
    if blockers:
        sys.exit("refusing to post: " + "; ".join(blockers))
    for t, g in msgs:
        body = {"content": t, "allowed_mentions": {"parse": []}}
        if g:
            body["attachments"] = [{"id": i, "filename": f.name} for i, f in enumerate(g)]
        m = api.request("POST", "/channels/%s/messages" % CHANNEL, body, [(f.name, f.read_bytes()) for f in g] or None)
        print("posted: https://discord.com/channels/%s/%s/%s" % (GUILD_ID, CHANNEL, m["id"]))


if __name__ == "__main__":
    main()
