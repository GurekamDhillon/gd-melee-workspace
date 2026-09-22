# Publishing mods for the GD's Melee mods browser

The launcher's **Mods** tab lists installed mods, and installs, updates, enables and removes mods
offered by the **sources** a player adds. This page is for mod authors: how to make your mods show
up there. The folder layout a mod installs into is `docs/mods-packaging.md`; scripts are
`docs/scripting.md`.

## For players, in short

- `mods/sources.txt` next to the game lists sources, one per line (`#` comments). It ships empty:
  GD's Melee does not vouch for anyone's mods; add the ones you trust.
- **Refresh sources** reads every source; **Install** downloads a mod (and what it requires),
  checks it and unpacks it into `mods/<id>/`. The tick box enables or disables a mod for the next
  start of the game; **Remove** deletes its folder.
- Command line: `"GD Melee.exe" --install-mod <id> [...]`, `--list-mods`, `--enable-mod <id>`,
  `--disable-mod <id>` (results in `userdata/mods.log`), `--mods` opens straight on the Mods tab.

## 1. A source

A source line is one of:

| line | the index read |
|---|---|
| `owner/repo` | `https://raw.githubusercontent.com/owner/repo/HEAD/gdmelee-mods.json`, else the `gdmelee-mods.json` asset of the repo's **latest release** |
| `owner/repo@ref` | the same at a branch or tag: `.../owner/repo/<ref>/gdmelee-mods.json`, else the asset of release `<ref>` |
| `https://github.com/owner/repo` (optionally `/tree/<ref>` or `@ref`) | as above |
| `https://host/any/path/index.json` | that file |

So the simplest source is a GitHub repo with `gdmelee-mods.json` at its root and the mod zips as
release assets.

## 2. The index: `gdmelee-mods.json`

JSON Schema: [`tools/mods_browser/gdmelee-mods.schema.json`](../tools/mods_browser/gdmelee-mods.schema.json).

```json
{
  "schema": 1,
  "name": "My Melee mods",
  "mods": [
    {
      "id": "my-fox-recolour",
      "name": "Fox recolour",
      "version": "1.2.0",
      "kind": "fighter",
      "pack": "",
      "description": "A new colour for Fox.",
      "authors": "me",
      "requires": [],
      "conflicts": [],
      "url": "https://github.com/me/my-mods/releases/download/v1.2.0/my-fox-recolour-1.2.0.zip",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "size": 123456
    },
    {
      "id": "my-overlay",
      "name": "Combo counter",
      "version": "0.3.0",
      "kind": "script",
      "api_version": 1,
      "url": "my-overlay-0.3.0.zip",
      "sha256": "...",
      "size": 2048
    }
  ]
}
```

| field | required | meaning |
|---|---|---|
| `id` | yes | the mod's identity and its folder name in `mods/`: `^[a-z0-9][a-z0-9._-]{0,63}$`, not `targettest` |
| `version` | yes | any string; a string different from the installed one offers **Update** |
| `url` | yes | the zip: `https://...`, or a path **relative to the index's own URL** (handy when the index and the zips sit side by side) |
| `sha256`, `size` | yes | of the zip. The download is refused unless both match - update them with every new zip |
| `name`, `description`, `authors`, `homepage` | no | shown in the Mods tab |
| `kind` | no | `base`, `fighter`, `stage`, `misc` (default) or `script`, as in `mod.json` |
| `pack` | no | the family a mod belongs to |
| `requires`, `conflicts` | no | mod ids. Installing a mod offers to install what it requires (from any of the player's sources); enabled mods it conflicts with are disabled |
| `api_version` | scripts | the scripting API the mod needs; a newer one than the game has is refused with "update GD's Melee" |

When two sources offer the same id, the first source in `sources.txt` wins.

## 3. The zip

- `mod.json` at the zip's top level (or inside **one** top folder, which is stripped), then the
  mod's `files/` (disc paths, `docs/mods-packaging.md`) and/or `scripts/` (`docs/scripting.md`).
- If `mod.json` has an `id`, it must equal the index's `id`.
- Forward-slash paths only; no absolute paths, no drive letters, no `..`, no `:` in names, no
  reserved device names (`CON`, `NUL`, `COM1`...), no names ending in `.` or space, no symlinks,
  at most 3 GB unpacked. A zip that breaks any of these is refused as a whole.

`tools/mods_browser/make_index.py` builds conforming zips and the index from mod folders:

```
python tools/mods_browser/make_index.py --out dist --name "My Melee mods" mods/my-fox-recolour mods/my-overlay
python tools/mods_browser/make_index.py --out dist --base-url https://github.com/me/my-mods/releases/download/v1.2.0/ mods/my-fox-recolour
```

Then upload the zips as release assets and commit `dist/gdmelee-mods.json` to the repo root (or
upload it as a release asset too).

## 4. What the launcher guarantees a player

- Downloads are **https only** (plain http and `file://` work for `localhost` only, for testing),
  including after redirects.
- Every zip is checked against the index's `sha256` and `size` before it is opened.
- A mod is unpacked into `mods/.staging-<id>` and moved into place only when complete; an update
  replaces the old folder only after the new one unpacked cleanly.
- **Nothing downloaded is run by the launcher.** Scripts run in the game's Lua sandbox (no files, no
  network, no native code - `docs/scripting.md`), and only while their mod is enabled.
- `mods/enabled.txt`: absent means every mod is enabled (the game's rule). The launcher writes it
  (all installed mods except the ones switched off) the first time something is disabled, and
  appends new installs while it exists.

## 5. Please don't

Publish mods built from a Nintendo disc (packs or splits of mod discs made by
`tools/mex_port`), or other people's work without their permission. The mods browser is for your
own work and work you may redistribute.
