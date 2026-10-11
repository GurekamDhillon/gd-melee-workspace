# Launcher update and version checks: design plan (2026-10-10)

Status: design only, nothing implemented. This is the first note on the topic, so nothing supersedes it.
Scope: the Qt launcher (`tools/release/launcher/qt/`). The C# launcher (`tools/release/launcher/*.cs`) is
reference-only and gets no updater.

## 0. What the code does today (checked)

| fact | where |
|---|---|
| Release version is `tools/release/VERSION` (currently `0.2.2`); tag `v<VERSION>`, zip `GDMelee-<v>-win64.zip` | `tools/release/README.md`, `VERSION` |
| The zip carries `version.txt`: line 1 `"<v> (melee <short>)"`, then melee/workspace commits, build date, `netplay_protocol N` | `build_release.ps1` ~L250 |
| The zip carries `MANIFEST.sha256` (sha256sum format, `/` paths, sorted) and the release has `<zip>.sha256` | `build_release.ps1` ~L258-266 |
| `publish.ps1` creates the GitHub release with `gh release create` on `GurekamDhillon/gd-melee-workspace` | `tools/release/README.md` |
| The launcher shows only line 1 of `version.txt` (`versionText`) in the title bar, the Diagnostics "Build" fact and the About tab | `qt/window.cpp` L100, 296, 592, 882-903 |
| The launcher has no network code except crash upload, which is **plain HTTP over a raw `QTcpSocket`** to `netplay_server.txt` | `qt/crash_upload.cpp` L60-75 |
| Qt6::Network is already linked; no TLS backend is deployed or checked | `qt/CMakeLists.txt` L10, L15 |
| User data: `<appDir>/userdata` when writable (portable), else `%LOCALAPPDATA%`-style `GenericDataLocation/GDMelee` | `qt/launcher_core.cpp` `pickUserDir` L153-168 |
| Mods: `<appDir>/mods` if it exists (the zip ships it), else `<user>/mods` — so shipped and user-installed mods share one folder | `launcher_core.cpp` `modsDir` L170 |
| Mods carry `id/name/version` in their manifest; the Mods tab shows the version | `launcher_core.h` L31, `window.cpp` L702-764 |
| The game checks `GW_NET_PROTOCOL_VERSION` (6) at handshake and refuses with "protocol version mismatch (host %u, you %u)" | `melee/pc/platform/gw_net.h` L58, `gw_net.c` L670 |
| The matchmaking server refuses mismatches too: `NETPLAY_PROTOCOL = 6`, "update GD's Melee on both PCs" | `tools/netplay/server/gdmelee_server.py` L47, L156 |
| **Drift found:** `netplay_protocol.ps1` `Get-NetplayProtocol` returns **5**, while `gw_net.h` and the server say 6. `Assert-NetplaySource` would throw on the next strict build. Fix before any release (one-line change; not done here). | `tools/release/netplay_protocol.ps1` L2 |
| Blender add-on is found at `<root>/tools/blender/geno_workbench` (needs `bootstrap.py`); it is a dev-tree path, not in the zip | `qt/workbench/blender_launch.cpp` L29 |

Consequence: everything below is new code. The useful existing pieces are `version.txt`, `MANIFEST.sha256`,
the `.sha256` per zip, `publish.ps1` and the protocol number.

## 1. What gets updated, what never does

Updated (all come from our build, contain nothing of Nintendo's, already pass `check_release.ps1`):
- **Launcher** (`gd-melee-launcher.exe` + its Qt DLLs/plugins).
- **Game** (`melee-pc.exe`, `melee-pc.map` — must move together, the map drives rollback snapshots —
  `SDL3.dll`, `webgpu_dawn.dll`, CRT DLLs, pipeline cache seed, `_build/ui` art, docs, licences).
- **Bundled mods** listed in `mod_rules.json` (LAB script mod, Envoy, etc.) — only the files the release ships.
- **Geno packages / Blender add-on**: phase 4, only if they start shipping in the zip (today the add-on does not).

Never touched by the updater:
- Disc images and anything derived from them (the user's own; the update never contains, reads or hashes them).
- `userdata/` (launcher settings JSON with disc paths, memory card `MELEE_CARD_PATH`, `config/settings.cfg`,
  crashlogs, last run dir).
- Any file under `mods/` that is not in the old release's `MANIFEST.sha256` (user-installed mods), and
  `mods/enabled.txt` (merge new defaults only for newly added mods).
- `netplay_server.txt` if the user edited it (hash differs from the old manifest).
- Any shipped file the user modified (hash ≠ old manifest): keep theirs as `<name>.local`, log it, tell them.

The rule is mechanical: **a file is ours iff its path and hash match the installed `MANIFEST.sha256`.**
Only ours are replaced or deleted.

## 2. Where version info comes from

New file published with every release: `update.json` (plus `update.json.sig`).

```json
{
  "schema": 1,
  "channel": "stable",
  "version": "0.3.0",
  "released": "2026-10-20",
  "netplay_protocol": 6,
  "min_launcher_for_self_update": "0.3.0",
  "notes_url": "https://github.com/GurekamDhillon/gd-melee-workspace/releases/tag/v0.3.0",
  "notes_short": {"en": "…", "es": "…"},
  "package": {
    "url": "https://github.com/…/releases/download/v0.3.0/GDMelee-0.3.0-win64.zip",
    "size": 123456789,
    "sha256": "…"
  },
  "files_manifest_sha256": "<sha256 of MANIFEST.sha256 inside the zip>",
  "critical": false
}
```

Plain text so it is diffable; `netplay_protocol` is copied from `version.txt`; notes come from
`tools/release/notes/<version>.md` (first paragraph; needs a Spanish line — the launcher is bilingual).

Hosting options:

| option | pros | cons |
|---|---|---|
| **GitHub Releases, `releases/latest/download/update.json`** | already where `publish.ps1` publishes; HTTPS + CDN; stable URL; free; no server to run | repo must be public (it is the public `gd-melee-workspace`), "latest" ignores drafts/prereleases (good); GitHub rate limits are generous for asset downloads |
| GitHub API (`/repos/…/releases/latest`) | no extra asset | 60 req/h unauthenticated per IP; JSON shape not ours; parsing more |
| Own matchmaking server (`gdmelee_server.py`) | already contacted by the launcher; could also report live protocol | plain HTTP today, one VPS = single point of failure; address is private by default (`-Server` off) |
| GitHub Pages / static host | custom domain | another thing to publish |

Recommendation: GitHub Releases asset, URL baked in at build time (overridable with
`update_url.txt` in the app dir for testing / friends builds).

## 3. Check flow

- **When:** on launcher start, in the background, at most once per 24 h (timestamp in settings);
  plus a manual "Check now" button. Never while the game is running (`process_.state() != NotRunning`).
- **Timeout:** 5 s connect, 15 s total; failure is silent (one muted line in the About tab: "Couldn't check
  for updates (offline?)"). Never block launch, never modal.
- **Offline:** cached last manifest is used only for the netplay hint; no nagging.
- **Opt-out:** toggle "Check for updates" (default **on**, see decisions), stored in launcher settings.
  `--no-update-check` CLI flag and `GDMELEE_NO_UPDATE_CHECK=1` for tests and CI.
- **Skip this version** button stored per version.
- **Compare:** semver on `version` vs `version.txt` line 1 (parse the leading `x.y.z[.w]`; note `0.1.8.1-linux`
  style tags exist, so allow a 4th component and ignore suffixes).
- **Privacy:** the request is a plain GET with `User-Agent: GDMeleeLauncher/<v>`; no IDs, no telemetry.
  Say this in the UI next to the toggle, like the crash-upload text does.

## 4. Download, verify, install

1. Download the zip to `<userdata>/updates/<v>/pkg.zip.part` with HTTP Range resume (QNetworkAccessManager);
   check free space first (2× size).
2. Verify **size + sha256** from the manifest, and the **signature** on `update.json` (see §8). Mismatch ⇒
   delete, report, never retry silently.
3. Extract to `<userdata>/updates/<v>/staged/`; verify every file against the zip's own `MANIFEST.sha256`;
   run the same path rules as `check_release.ps1` (no `..`, no absolute paths, no disc-like extensions —
   reuse its deny list) as defence in depth.
4. **Apply via a helper** because Windows locks a running exe:
   - The launcher copies `gd-melee-updater.exe` (small, Qt-Core-only or plain Win32, shipped in the zip)
     to `%TEMP%\gdmelee-updater-<pid>.exe` and starts it with: app dir, staged dir, old/new manifests,
     launcher PID, relaunch command. Then the launcher exits.
   - Updater waits for the launcher PID (and refuses if `melee-pc.exe` from that dir is running).
   - **Plan:** for each path in new manifest: if absent or ours-unchanged ⇒ replace; if user-modified ⇒
     keep as `.local`. For each path only in old manifest and still ours ⇒ delete. Everything else untouched.
   - **Swap:** move each target to `<appDir>/.update-backup/<oldv>/…` (`MoveFileEx`, same volume), then move
     the new file in (`MoveFileEx(MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)`). Renaming a running
     exe is allowed on NTFS; deleting is not — the rename-aside approach also covers the updater's own
     source copy. Write a `update-journal.json` before each step so a crash/power loss can be finished or
     reverted at next start.
   - Write the new `version.txt` and `MANIFEST.sha256` **last** (commit point).
   - Relaunch the launcher with `--updated-from <oldv>`.
5. **Rollback:** if the relaunched launcher does not write a "came up" marker within 30 s, or the journal
   is incomplete, the updater (or next start) restores `.update-backup/<oldv>`. Keep exactly one previous
   version; About tab offers "Roll back to <oldv>". Rollback also restores the old protocol, so warn.
6. **Permissions:** the zip is portable; if the app dir is not writable (Program Files), do not elevate —
   tell the user to move the folder or download manually. (No UAC in phase 1-3.)

## 5. User files preserved

Covered by the manifest rule in §1. Specific checks:
- `userdata/` is never in any manifest; the updater asserts it never writes under it except `updates/`.
- Non-portable users (`GenericDataLocation/GDMelee`) are untouched by construction.
- Disc paths live in launcher settings JSON (`launcher_core.cpp` L112-132) inside userdata: preserved.
- Settings schema changes: launcher migrates on load (already tolerant JSON); the updater never edits them.
- `mods/enabled.txt`: three-way merge — keep user state, add new default-on mods, drop removed shipped ids.

## 6. Netplay

- The manifest carries `netplay_protocol`. If newer release has a different protocol than the installed
  `version.txt`, the update card says: "This update changes online play: you can only play people on
  version ≥ X." and the Online area shows a persistent hint: "Players on 0.3 can't play you until you update."
- When the game refuses a match, the message already names both numbers (`gw_net.c` L671; server says
  "update GD's Melee on both PCs"). Launcher improvement: if the game log/exit reports a protocol mismatch,
  show "Your version (protocol 6) doesn't match theirs (7). Check for updates?" with the button.
- Future (optional): server handshake already knows the client protocol; it could reply with the latest
  release version string so mismatches name a version, not a number. Needs a server change, not required.
- Compatibility key is the **protocol number only**, not the release version (patch releases that keep
  the protocol stay compatible).
- Prerequisite: fix `netplay_protocol.ps1` (5) vs `gw_net.h`/server (6) drift, and add a test that all
  three agree (extend `test_netplay_protocol.ps1`).

## 7. Release-pipeline changes

- `build_release.ps1`: also ship `gd-melee-updater.exe` and a public key file is compiled in (not shipped).
- `publish.ps1`: generate `update.json` from VERSION, `version.txt`, the zip's size/sha256, the
  MANIFEST hash and the notes file; sign it (`update.json.sig`); upload both as release assets with
  `gh release create`; `-DryRun` prints them. Drafts are invisible to `releases/latest`, so `-Draft` is
  a safe staging step.
- Notes files gain a short bilingual summary block (`<!-- update-summary en: … es: … -->`).
- `check_release.ps1` learns the updater exe as an allowed file.
- New test: `test_update_manifest.py` (schema, version equals VERSION, protocol equals gw_net.h).
- Signing key lives outside the repo (like `.env`), never committed; `publish.ps1` refuses without it.

## 8. Security

- **Transport:** HTTPS only (GitHub). Qt needs a TLS backend: deploy Qt's `schannel` TLS plugin
  (`plugins/tls/qschannelbackend.dll`, Qt ≥ 6.2) and add it to the release guard's required files. No
  OpenSSL DLLs needed on Windows.
- **Integrity vs authenticity:** sha256 in a manifest fetched from the same place only proves integrity.
  Sign `update.json` with **Ed25519** (minisign/signify format; verify with a tiny vendored
  implementation, e.g. monocypher, ~1 file) with the public key compiled into the launcher. A compromised
  GitHub account then cannot push an update without the offline key.
- Downgrade protection: refuse `version` < installed unless the user picks rollback. Manifest `released`
  date must not go backwards vs cached.
- Zip-slip: reject `..`, absolute, drive-letter, ADS (`:`) and reserved names; extract only listed paths.
- The updater never runs anything from the download except the new launcher after swap, and only after
  the full manifest verified.
- Authenticode signing of the exes is separate (SmartScreen); see decisions.
- No disc data: the release guard already enforces it; the updater also runs the deny list on staged files.
- Crash upload stays plain HTTP; unrelated, but worth noting it is the only other network path.

## 9. UI sketch (Atlas style, inline `t("English","Spanish")` pairs)

Title bar: version text as today, plus a small accent pill **"Update 0.3.0"** when one is available
(click opens the About tab).

About tab (existing explainer with `addFact`):
```
Version        0.2.2 (melee 1a2b3c4)
Latest         0.3.0 · 20 Oct 2026            [ See what's new ]
Online play    Protocol 6 → 7 (players must update together)
               ───────────────────────────────────────────
               [ Download and install ]  [ Skip this version ]
               ▓▓▓▓▓▓▓▓░░░░ 62 %  48 / 77 MB   [ Cancel ]
Updates        [toggle] Check for updates when the launcher starts
               "Asks GitHub once a day for the newest version number. Nothing about you is sent."
               [ Check now ]   Last checked: today 14:02
Previous       0.2.1 kept.  [ Roll back ]
```
States: checking / up to date / available / downloading / ready ("Restart to finish") / failed (reason,
muted) / offline. Install button disabled while the game runs. All strings as `t()` pairs; run
`check_qt_strings.py` (CTest `launcher_qt_strings`).

## 10. Phased implementation and tests

**Phase 0 (prereq, small):** fix protocol drift; three-way agreement test.

**Phase 1 — check only.** `update_check.{h,cpp}` in `launcher_core` (QNetworkAccessManager, schannel),
manifest parser, semver compare, settings (enabled, last check, skipped). UI pill + About rows; "Download"
opens the release page in the browser. `publish.ps1` emits `update.json` (unsigned allowed in this phase).
Tests: `update_tests.cpp` (QtTest) with fixtures — parse/compare (incl. `0.1.8.1`), malformed JSON,
timeouts against a local `QTcpServer`, offline, opt-out flag; `test_update_manifest.py`.
Ships value immediately: users learn about new versions and protocol changes.

**Phase 2 — signed download + staging.** Ed25519 verify, resumable download, staged extract,
MANIFEST verification, deny list. Tests: tampered byte, wrong sig, truncated download + resume, zip-slip
fixtures, disc-extension fixture.

**Phase 3 — helper swap + rollback.** `gd-melee-updater.exe`, journal, backup, relaunch, rollback.
Tests (Windows, in a temp copy of a packaged release): update 0.x→0.y with a user mod, modified
`netplay_server.txt`, edited shipped file, running game (must refuse), kill updater mid-swap
(journal recovery), launcher fails to come up (auto-rollback), read-only dir. Add to
`test_launcher_paths.ps1` style scripts; a Windows agent must run these — headless/cloud agents cannot.

**Phase 4 — optional extras.** Mod/Geno package updates from their own manifest (only mods we publish;
third-party via Nucleus stays separate), Blender add-on if it ships, beta channel, server-reported
latest version on protocol mismatch.

## 11. Open decisions for the owner (recommendation each)

1. **Check on by default?** Rec: yes, once a day, with the toggle and the privacy line visible.
2. **Hosting.** Rec: GitHub Releases asset on `gd-melee-workspace` (`releases/latest/download/update.json`).
3. **Install in-app or just notify?** Rec: ship phase 1 (notify + link) in 0.3; in-app install (phases 2-3)
   after, once signing exists.
4. **Signing key.** Rec: Ed25519 key held offline by the owner, public key compiled in; no updates
   accepted unsigned from phase 2 on.
5. **Authenticode certificate** (SmartScreen warnings). Rec: not now (cost); revisit if public distribution grows.
6. **Channels.** Rec: stable only; a `beta` channel later via a second manifest name.
7. **Forced/critical updates?** Rec: never force; `critical` only changes the wording (e.g. security fix).
8. **Friends-zip builds with a baked server** (`-Server`): should they check GitHub? Rec: yes, same
   manifest; `update_url.txt` override for private test builds.
9. **Rollback depth.** Rec: keep one previous version.
10. **Linux tarball** (`package_linux.py`). Rec: check-only (phase 1) there too; no self-install.
