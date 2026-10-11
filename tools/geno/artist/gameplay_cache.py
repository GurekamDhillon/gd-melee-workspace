"""Pure metadata guard for artist gameplay-only rebuilds (no art import)."""
import json
from pathlib import Path

NAME = "gameplay-cache.json"
_GAMEPLAY = {"attributes", "jumps", "moves", "name", "thrown_as"}


def signature(config):
    config = Path(config).resolve()
    text = config.read_text(encoding="utf-8-sig")
    cfg = json.loads("\n".join(line for line in text.splitlines()
                              if not line.lstrip().startswith("//")))
    sources = {}
    # Art and sidecar files affect the plan, costumes or bank. They stay cached.
    for path in sorted(config.parent.rglob("*")):
        if not path.is_file() or path.resolve() == config:
            continue
        if path.suffix.lower() not in (".blend", ".glb", ".gltf", ".bin", ".png", ".jpg", ".jpeg", ".json"):
            continue
        # Outputs can live beside fighter.json, but must not invalidate themselves.
        if any(part in ("build", "mods", "package", ".workbench") for part in path.relative_to(config.parent).parts):
            continue
        stat = path.stat()
        sources[str(path.resolve())] = [stat.st_size, stat.st_mtime_ns]
    for key in ("blend", "glb"):
        value = cfg.get("art", {}).get(key)
        if not value:
            continue
        path = (config.parent / value).resolve()
        candidates = [path]
        if key == "glb" and Path(str(path) + ".geno.json").is_file():
            candidates.append(Path(str(path) + ".geno.json"))
        for asset in candidates:
            stat = asset.stat()
            sources[str(asset)] = [stat.st_size, stat.st_mtime_ns]
    return {"config": {k: v for k, v in cfg.items() if k not in _GAMEPLAY}, "art": sources}


def write(config, build_dir, *, token, costumes, height, ref_speeds):
    data = dict(schema="geno-gameplay-cache/1", stage_a=signature(config), token=token,
                costumes=costumes, height=height, ref_speeds=ref_speeds)
    (Path(build_dir) / NAME).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read_current(config, build_dir):
    try:
        data = json.loads((Path(build_dir) / NAME).read_text(encoding="utf-8"))
        if data.get("schema") != "geno-gameplay-cache/1" or data.get("stage_a") != signature(config):
            raise ValueError("art or clip configuration changed")
        for key in ("token", "costumes", "height", "ref_speeds"):
            if key not in data:
                raise ValueError("incomplete gameplay cache")
        return data
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError("Gameplay-only rebuild needs a full build first: " + str(exc)) from exc
