GD's Melee
==========

A native Windows port of Super Smash Bros. Melee, built from the community decompilation.
It runs the game from YOUR OWN disc image. This download contains no Nintendo game data.


WHAT YOU NEED
  - Windows 10 or 11, and a graphics card that can run Direct3D 11.
  - A disc image of Super Smash Bros. Melee, NTSC-U (USA) revision 1.02, as a plain .iso
    (game ID GALE01). Dump it from your own disc (a Wii with CleanRip, or Dolphin).
    The ACE and Akaneia builds, which are made from that disc, work too.
    Training Mode (TM-CE) and 20XX discs boot too, but their own features (the training lab,
    the 20XX menus) are not supported yet: they play like vanilla Melee for now.
    Compressed images (.rvz, .ciso) must be converted to .iso first: in Dolphin, right-click the
    game > Convert File... > ISO.
  - A controller: a GameCube controller through a Wii U / Mayflash adapter (Wii U mode), or an
    Xbox-style pad. The keyboard does not play (hotkeys only).


START
  1. Unzip this whole folder somewhere you can write to (Desktop, Documents, Games - not
     Program Files).
  2. Double-click "GD Melee.exe".
     If Windows says "Windows protected your PC": More info > Run anyway.
  3. The first time, it asks for your .iso. It checks the file and tells you what it found
     (for example "Melee 1.02 (vanilla)" or "ACE (m-ex mod)"), then remembers it.
  4. Press PLAY.


MORE THAN ONE DISC ("MODPACKS")
  The Play tab keeps a list of discs. "Add disc..." adds another one (say vanilla Melee and ACE);
  select one and press PLAY (or double-click it) to boot it. The starred one is the default.
    Change ISO...  point a disc at a different file (a newer version of a mod, or the file moved).
                   Its saves stay.
    Forget         remove it from the list. The .iso itself is never touched, and its saves stay.
  "Unlock every character and stage" (on by default) opens the whole roster, all stages and the
  unlockable rules without touching your save; untick it to play the unlocks the normal way.
  Online matches always have everything unlocked for both players.
  Each disc keeps its own memory card, in userdata\saves\<disc>. Deleting userdata\launcher.cfg
  makes the launcher forget everything and ask again (saves are kept).

  Shortcuts: "GD Melee.exe" --play boots the default disc straight away, and
  "GD Melee.exe" --play ACE boots the disc named ACE.


CONTROLS
  Play with a controller: a GameCube controller through an adapter (Wii U mode on Mayflash
  adapters; plug it in any time), or any gamepad. With no controller the game says
  "Connect a controller".
  The keyboard does not play. It is for hotkeys only:
    F9           controller panel (and, with an adapter, recalibrate)
    F10          put every overlay back on screen
    `            the console (the key left of 1)
  Mods and scripts can add their own hotkeys.
  The mouse works in the menus: point and click, right-click goes back, the wheel scrolls.


MODS AND SCRIPTS
  The Mods tab lists the mods in the mods folder: untick one to switch it off at the next start,
  or Remove it. To get new mods, "Edit sources..." and add sources you trust (a GitHub repo like
  owner/repo, or an https link to an index) - none are listed by default. "Refresh sources" shows
  what they offer; Install downloads a mod and anything it needs, checks it and unpacks it.
  Nothing downloaded is run by the launcher; mod scripts run in the game's sandbox.
  Lua scripts: scripts\ next to the game (examples in scripts\examples). Press ` in the game for
  the console.


ONLINE
  See "HOW TO PLAY ONLINE.txt". Both players need this same release of GD's Melee.
  Mods are welcome online: fighters and stages are matched with your opponent by their content,
  so anything you both have can be picked, and anything only one of you has is greyed out. Mods
  that change the rules of the whole game (codes, physics) must match on both sides.
  The Online tab in the launcher sets the matchmaking server used for room codes.
  If Windows Firewall asks about melee-pc.exe, tick both Private and Public, then Allow.


IF SOMETHING GOES WRONG
  - "This disc can't be used": the launcher says why (wrong region, wrong revision, not Melee,
    compressed image). You need NTSC-U 1.02.
  - The game closes at once: the launcher offers to open melee-pc.log. Crash reports are in the
    crashlogs folder. Please include them when you report a bug.
  - "VCRUNTIME140.dll was not found": the files next to melee-pc.exe were not all unzipped; unzip
    the whole folder again.


FILES
  GD Melee.exe        the launcher
  melee-pc.exe        the game (you can also run it directly: melee-pc.exe --iso "C:\path\melee.iso")
  ui\                 GD's Melee's own menu art
  mods\               your mods (the Mods tab manages them), sources.txt says where to find more
  scripts\            Lua scripts; examples\ holds the examples
  userdata\           your settings and saves (created on first run)
  LICENSES\           licences of the port and every library in it
  MANIFEST.sha256     checksums of every file in this release
  version.txt         which build this is


Source code: https://github.com/GurekamDhillon/melee (branch pc-port) and
https://github.com/GurekamDhillon/gd-melee-workspace. Super Smash Bros. Melee is (c) Nintendo /
HAL Laboratory; this project is not affiliated with or endorsed by them.
