# Authoring-tool paths

Artist commands, Workbench launchers (Goku, Falcon and Splice), and the Workbench
add-on use the same standard-library resolver: [tools_config.py](tools_config.py).
The one local config is `_build/tools.json`; it is git-ignored. No tool is executed
by discovery, and no disc contents are read or copied by the resolver.

From the workspace root:

```text
python tools/port/tools_config.py --detect
python tools/port/tools_config.py --check
```

`--detect` saves resolved paths atomically. It preserves configured values and
fills unset tools from PATH, standard Blender installation directories, Steam
libraries and build outputs. Unresolved discoveries are omitted, so a later `--detect` can find newly
installed tools; explicitly empty settings are preserved. Set paths that discovery cannot find in `.env` or edit the local JSON.
`--check` lists **every** missing file/directory and exits 1 if any is missing;
malformed configuration exits 2 with the file named. It checks existence, not
executable versions or DLL compatibility. With neither flag, the command prints
only the resolved tool keys. `--detect --check` does both operations.

| Key | Purpose |
|---|---|
| `GW_BLENDER` | Modern Blender executable: artist tools require 4.2+, Workbench requires 4.0+ |
| `GW_BLENDER_351` | Separate Blender 3.5.1 executable for legacy exporters; never substituted for the modern authoring tool |
| `GW_LAUNCHER` | Qt `gd-melee-launcher.exe` or the release stub `GD Melee.exe` (it forwards arguments and stdio), with Workbench `--serve` support |
| `GW_ENGINE_EXE` | `melee-pc.exe` with the Workbench protocol; launchers copy it to their own session sandbox |
| `GW_QT_BIN` | Qt DLL directory, prepended to the launcher's PATH |
| `GW_ISO_VANILLA` | Local vanilla disc image |
| `GW_ISO_AKANEIA` | Local Akaneia disc image |
| `GW_ISO_ACE` | Local ACE disc image |

Precedence: process environment, then `.env`, then `_build/tools.json`, then
discovery. An explicitly empty setting suppresses lower-priority values and
discovery. `BLENDER` remains an alias for `GW_BLENDER`; `BLENDER_351` and
`GW_BLENDER35` alias `GW_BLENDER_351`. The canonical key wins within each layer.

`GW_ROOT` selects the workspace containing both local files (default: the
checkout containing the resolver). The CLI's `--root DIR` overrides it.
`GW_TOOLS_CONFIG` can select another local JSON file; ignore that file too.
Relative tool paths resolve against the selected workspace. Quoted values,
optional `export`, comments and `$GW_ROOT` / `${GW_ROOT}` / `%GW_ROOT%`
expansion are supported in `.env` values. Shell commands in `.env` are never run.

The JSON shape is:

```json
{
  "schema": 1,
  "paths": {
    "GW_BLENDER": "_build/tools/blender/blender.exe",
    "GW_BLENDER_351": "_build/tools/blender-3.5.1-windows-x64/blender.exe",
    "GW_LAUNCHER": "_build/wb-win/gd-melee-launcher.exe",
    "GW_ENGINE_EXE": "_build/wb-goku/engine/melee-pc.exe",
    "GW_QT_BIN": "",
    "GW_ISO_VANILLA": "_local/discs/vanilla.iso",
    "GW_ISO_AKANEIA": "",
    "GW_ISO_ACE": ""
  }
}
```

These are examples; use your installed tools and your own discs. Other environment
keys and credentials are never written to the JSON. Modern Blender is detected
on PATH or in standard 4.0+ installation directories, then in Steam libraries.
Steam discovery reads `%ProgramFiles(x86)%/Steam/steamapps/libraryfolders.vdf` and
checks `steamapps/common/Blender/blender.exe` in every listed library, including
libraries on other drives. The default Steam library is still checked if that file
is missing or unreadable. `GW_BLENDER` keeps its override precedence (an explicit
empty value disables discovery). Pinned Blender discovery only considers
3.5.1-specific locations. Launcher discovery prefers `_build/wb-win`, then the
newest launcher under `_build`, then PATH. Engine discovery considers the existing
Workbench sandbox, `_build/agents/geno-workbench`, and `_build/melee-pc.exe`.
Qt discovery uses `GW_QT_ROOT`, `QT_ROOT`, `CMAKE_PREFIX_PATH` or `Qt6_DIR`.

The Goku/Falcon engine session needs the modern Blender, launcher, engine, vanilla
disc, and project/art/mods paths. Qt bin may be empty if the launcher already has
its DLLs beside it. Pinned Blender and the other discs are optional for this flow,
so `--check` can report missing optional items even when that session is usable.
Goku startup lists all missing requirements before it stops. Explicit Blender UI
fields and launch CLI project/art/mods/work arguments keep their overrides.
If your only engine copy is inside a custom `--work` / `GW_WB_WORK` sandbox, set
`GW_ENGINE_EXE` to that copy in `.env` or the local JSON; work-directory selection
no longer adds a separate engine-discovery rule.

For an installed Workbench add-on outside this checkout, set `GW_ROOT` before
opening Blender so its helper can import the shared resolver. Launch scripts pass
the resolved configuration to both Blender and the launcher. Disabled Workbench
operators explain their precondition in the tooltip; starting a server on an
already-serving port reports reuse and leaves ownership with the original process.
