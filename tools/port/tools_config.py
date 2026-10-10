"""Shared authoring-tool paths. See TOOLS_CONFIG.md; discovery never runs a tool."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Mapping


TOOL_KEYS = (
    "GW_BLENDER", "GW_BLENDER_351", "GW_LAUNCHER", "GW_ENGINE_EXE", "GW_QT_BIN",
    "GW_ISO_VANILLA", "GW_ISO_AKANEIA", "GW_ISO_ACE",
)
ALIASES = {"GW_BLENDER": ("BLENDER",), "GW_BLENDER_351": ("BLENDER_351", "GW_BLENDER35")}


class ToolsConfigError(ValueError):
    """A local configuration file is unreadable or malformed."""


def workspace_root(root=None, env: Mapping[str, str] | None = None) -> Path:
    env = os.environ if env is None else env
    return Path(root or env.get("GW_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()


def _dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ToolsConfigError(f"{path}: cannot read .env ({exc})") from exc
    out = {}
    for number, line in enumerate(lines, 1):
        line = line.strip().removeprefix("export ").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue
        if value.startswith(('"', "'")):
            end = value.find(value[0], 1)
            if end < 0 or (value[end + 1:].strip() and not value[end + 1:].strip().startswith("#")):
                raise ToolsConfigError(f"{path}:{number}: invalid quoted value for {key}")
            value = value[1:end]
        else:
            value = re.sub(r"\s+#.*$", "", value).rstrip()
        out[key] = value
    return out


def _canonical(layer: Mapping[str, str]) -> dict[str, str]:
    out = dict(layer)
    for key, aliases in ALIASES.items():
        if key not in out:
            for alias in aliases:
                if alias in out:
                    out[key] = out[alias]
                    break
    return out


def _expand(value: str, values: Mapping[str, str]) -> str:
    pattern = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)|%([A-Za-z_][A-Za-z0-9_]*)%")
    for _ in range(10):
        expanded = pattern.sub(lambda match: values.get(next(g for g in match.groups() if g), match.group(0)), value)
        if expanded == value:
            break
        value = expanded
    if pattern.search(value):
        raise ToolsConfigError(f"unresolved or recursive variable in tool path: {value!r}; set the referenced variable")
    return value


def _path(value: str, root: Path, values: Mapping[str, str]) -> str:
    if not value.strip():
        return ""
    path = Path(_expand(value.strip(), values)).expanduser()
    return str(path if path.is_absolute() else root / path)


def config_path(root: Path, env: Mapping[str, str]) -> Path:
    raw = env.get("GW_TOOLS_CONFIG", "").strip()
    return Path(_path(raw, root, dict(env, GW_ROOT=str(root)))) if raw else root / "_build/tools.json"


def _cache(path: Path, required=False) -> dict[str, str]:
    if not path.exists() and not required:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or type(data.get("schema")) is not int or data["schema"] != 1:
            raise ValueError("expected schema 1")
        paths = data.get("paths")
        if not isinstance(paths, dict) or any(k not in TOOL_KEYS or not isinstance(v, str) for k, v in paths.items()):
            raise ValueError("paths must map supported GW_* tool keys to strings")
        return paths
    except (OSError, UnicodeError, ValueError) as exc:
        raise ToolsConfigError(f"{path}: cannot read tool config ({exc}); repair this file or set GW_TOOLS_CONFIG") from exc


def _first_file(candidates) -> str:
    for path in candidates:
        try:
            if Path(path).is_file():
                return str(Path(path).resolve())
        except OSError:
            continue
    return ""


def _on_path(name: str, env: Mapping[str, str]) -> str:
    path = env.get("PATH", "")
    return (shutil.which(name, path=path) or shutil.which(name + ".exe", path=path) or "") if path else ""


def _steam_blender_candidates(steam: Path) -> list[Path]:
    libraries = [steam]  # Retain the default library even if the VDF is unavailable.
    try:
        document = (steam / "steamapps/libraryfolders.vdf").read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        pass
    else:
        for raw_path in re.findall(r'"path"\s*"((?:\\.|[^"\\])*)"', document):
            # VDF escapes backslashes; unicode_escape would corrupt paths such
            # as C:\Users and non-ASCII library names.
            library = re.sub(r'\\([\\"])', r'\1', raw_path)
            if library and Path(library).is_absolute():
                libraries.append(Path(library))
    return [library / "steamapps/common/Blender/blender.exe" for library in libraries]


def _discover(root: Path, values: Mapping[str, str]) -> dict[str, str]:
    found = {}
    if "GW_BLENDER" not in values:
        candidates = []
        for key in ("PROGRAMFILES", "ProgramFiles", "LOCALAPPDATA"):
            if values.get(key):
                base = Path(values[key])
                foundation = base / ("Programs/Blender Foundation" if key == "LOCALAPPDATA" else "Blender Foundation")
                candidates.extend(path for path in foundation.glob("Blender */blender.exe")
                                  if tuple(int(n) for n in re.findall(r"[0-9]+", path.parent.name)) >= (4, 0))
        candidates.sort(key=lambda p: tuple(int(n) for n in re.findall(r"[0-9]+", p.parent.name)), reverse=True)
        steam = values.get("PROGRAMFILES(X86)") or values.get("ProgramFiles(x86)")
        if steam:
            candidates.extend(_steam_blender_candidates(Path(steam) / "Steam"))
        found["GW_BLENDER"] = _on_path("blender", values) or _first_file(candidates)
    if "GW_BLENDER_351" not in values:
        candidates = [root / "_build/tools/blender-3.5.1-windows-x64/blender.exe"]
        for key in ("PROGRAMFILES", "ProgramFiles"):
            if values.get(key):
                candidates.append(Path(values[key]) / "Blender Foundation/Blender 3.5.1/blender.exe")
        found["GW_BLENDER_351"] = _first_file(candidates)
    if "GW_LAUNCHER" not in values:
        found["GW_LAUNCHER"] = _first_file([root / "_build/wb-win/gd-melee-launcher.exe"])
        if not found["GW_LAUNCHER"]:
            candidates = []
            for path in (root / "_build").rglob("gd-melee-launcher*"):
                try:
                    if path.name in ("gd-melee-launcher", "gd-melee-launcher.exe") and path.is_file():
                        candidates.append((path.stat().st_mtime_ns, str(path.resolve())))
                except OSError:
                    continue
            found["GW_LAUNCHER"] = max(candidates)[1] if candidates else _on_path("gd-melee-launcher", values)
    if "GW_ENGINE_EXE" not in values:
        found["GW_ENGINE_EXE"] = _first_file([
            root / "_build/wb-goku/engine/melee-pc.exe",
            root / "_build/agents/geno-workbench/melee-pc.exe", root / "_build/melee-pc.exe",
        ])
    if "GW_QT_BIN" not in values:
        candidates = []
        for key in ("GW_QT_ROOT", "QT_ROOT"):
            if values.get(key):
                candidates.append(Path(_path(values[key], root, values)) / "bin")
        for prefix in values.get("CMAKE_PREFIX_PATH", "").split(os.pathsep):
            if prefix:
                candidates.append(Path(prefix) / "bin")
        if values.get("Qt6_DIR"):
            cmake = Path(_path(values["Qt6_DIR"], root, values))
            if len(cmake.parents) >= 3:
                candidates.append(cmake.parents[2] / "bin")
        found["GW_QT_BIN"] = next((str(p.resolve()) for p in candidates if p.is_dir()), "")
    return found


def load_config(root=None, env: Mapping[str, str] | None = None, *, detect=True) -> dict[str, str]:
    """Environment > .env > tools.json > discovery; explicit empty values disable discovery.

    Tool paths are relative to the workspace, not the caller's working directory.
    Other environment values are retained for subprocess consumers but never cached.
    """
    env = dict(os.environ if env is None else env)
    root = workspace_root(root, env)
    dotenv = _canonical(_dotenv(root / ".env"))
    location_env = {**dotenv, **env, "GW_ROOT": str(root)}
    path = config_path(root, location_env)
    values = _cache(path, required=bool(location_env.get("GW_TOOLS_CONFIG")))
    values.update(dotenv)
    values.update(_canonical(env))
    values["GW_ROOT"] = str(root)
    if detect:
        values.update(_discover(root, values))
    for key in TOOL_KEYS:
        values[key] = _path(values.get(key, ""), root, values)
    return values


def missing_tools(values: Mapping[str, str], keys=TOOL_KEYS) -> list[str]:
    """Report every missing path; Qt is a directory, the other tools are files."""
    missing = []
    for key in keys:
        value = values.get(key, "")
        kind = "directory" if key == "GW_QT_BIN" else "file"
        try:
            valid = bool(value) and (Path(value).is_dir() if kind == "directory" else Path(value).is_file())
        except OSError:
            valid = False
        if not valid:
            missing.append(f"{key}: missing {kind} {value!r}; set {key} in .env or _build/tools.json")
    return missing


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", help="workspace containing .env and _build/tools.json (default: GW_ROOT or this checkout)")
    ap.add_argument("--detect", action="store_true", help="write resolved tool paths to the local config; never runs any tool")
    ap.add_argument("--check", action="store_true", help="list every missing tool/disc; return 1 if any are missing")
    args = ap.parse_args(argv)
    try:
        values = load_config(args.root)
        if args.detect:
            root = Path(values["GW_ROOT"])
            path = config_path(root, values)
            configured_keys = set(_cache(path)) | set(_canonical(_dotenv(root / ".env"))) | set(_canonical(os.environ))
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
                    temporary = Path(file.name)
                    json.dump({"schema": 1, "paths": {key: values[key] for key in TOOL_KEYS
                                                      if values[key] or key in configured_keys}}, file, indent=2)
                    file.write("\n")
                temporary.replace(path)
            finally:
                if temporary is not None and temporary.exists():
                    temporary.unlink()
            print(f"wrote {path}")
        if args.check:
            missing = missing_tools(values)
            for message in missing:
                print(message)
            if not missing:
                print("all configured tools and discs exist")
            return 1 if missing else 0
        if not args.detect:
            for key in TOOL_KEYS:
                print(f"{key}={values[key]}")
        return 0
    except (ToolsConfigError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
