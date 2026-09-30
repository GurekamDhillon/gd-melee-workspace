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
  Each disc keeps its own memory card, in userdata\saves\<disc>.
  The Qt launcher stores its disc library in userdata\launcher.json and imports the older
  launcher.cfg automatically. Change ISO and Rename preserve each disc's save folder.
  If the installation folder is read-only, settings go under %LOCALAPPDATA%\GDMelee instead.

  Shortcuts: "GD Melee.exe" --play boots the default disc straight away, and
  "GD Melee.exe" --play ACE boots the disc named ACE.


CONTROLS
  Play with a controller: a GameCube controller through an adapter (Wii U mode on Mayflash
  adapters; plug it in any time), or any gamepad. With no controller the game says
  "Connect a controller".
  The first time the game starts it opens SETTINGS > CONTROLS: each port shows what it reads
  live (press buttons, move the sticks), with the adapter's recalibrate, a stick dead zone for
  Xbox / PlayStation-style pads, and How to Play Online. It is always there under SETTINGS.
  The keyboard does not play. It is for hotkeys only:
    F9           controller panel (and, with an adapter, recalibrate)
    F10          put every overlay back on screen
    `            the console (the key left of 1)
  Mods and scripts can add their own hotkeys.
  The mouse works in the menus: point and click, right-click goes back, the wheel scrolls.


LAB
  SOLO > LAB is an offline practice and fighter-inspection mode. Pause with START to open its
  full-screen menu for display modes, frame stepping, rewind, saved states and creator tools.
  TRAINING shows frame advantage, move data, inputs and technique feedback. Set up a human-port
  dummy for DI, techs, reactions or recorded inputs; use COMBO to review follow-ups and DRILLS
  for scored practice. A controller is required to play; the keyboard is for LAB hotkeys only.


MODS AND SCRIPTS
  The Mods tab lists installed mods: switch one off for the next start, or remove it from the
  active list. Removed mods are moved to the .removed folder. Dependencies and conflicts are
  checked when enabling mods. Open the mods folder to add your local content.
  Remote mod browsing and downloads are not included in the current Qt launcher.
  Lua scripts: scripts\ next to the game (examples in scripts\examples). Press ` in the game for
  the console.


CURRENT SCOPE
  The shared Qt launcher covers offline play and local custom content. It has no Online tab.
  Linux development support is documented in docs/LINUX_PORT_STATUS.md in the workspace repo;
  the Linux package has its own runtime requirements and README.


IF SOMETHING GOES WRONG
  - "This disc can't be used": the launcher says why (wrong region, wrong revision, not Melee,
    compressed image). You need NTSC-U 1.02.
  - The game closes at once: use the launcher's Diagnostics page to open the run logs. Each
    launch creates its own directory under userdata\runs (or the fallback data directory).
  - "VCRUNTIME140.dll was not found": the files next to melee-pc.exe were not all unzipped; unzip
    the whole folder again.


FILES
  GD Melee.exe        the launcher
  launcher\           the Qt application, runtime and licences; keep this folder intact
  melee-pc.exe        the game (you can also run it directly: melee-pc.exe --iso "C:\path\melee.iso")
  ui\                 GD's Melee's own menu art
  mods\               your installed mods (the Mods tab manages them)
  scripts\            Lua scripts; examples\ holds the examples
  userdata\           your settings and saves (created on first run)
  LICENSES\           licences of the port and every library in it
  MANIFEST.sha256     checksums of every file in this release
  version.txt         which build this is


Source code: https://github.com/GurekamDhillon/melee (branch pc-port) and
https://github.com/GurekamDhillon/gd-melee-workspace. Super Smash Bros. Melee is (c) Nintendo /
HAL Laboratory; this project is not affiliated with or endorsed by them.
