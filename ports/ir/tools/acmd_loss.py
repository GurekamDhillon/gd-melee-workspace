"""Reviewed ACMD omissions and per-install, machine-readable loss records.

Entries are exact command or case names. A wildcard would hide newly introduced data,
so it is deliberately unsupported. No entry is shipped until a reviewer approves it.
"""
import json
import hashlib
from pathlib import Path

ALLOWLIST = Path(__file__).with_name("acmd_allowlist.json")


def verify_acmd_source(path):
    source = Path(path)
    sidecar = Path(str(source) + ".audit.json")
    if not sidecar.is_file():
        raise ValueError(f"unaudited ACMD parse {source}: regenerate with current acmd_parse.py")
    audit = json.loads(sidecar.read_text(encoding="utf-8"))
    data = source.read_bytes()
    parser = Path(__file__).with_name("acmd_parse.py")
    if (audit.get("version") != 1 or
            audit.get("source_sha256") != hashlib.sha256(data).hexdigest() or
            audit.get("parser_sha256") != hashlib.sha256(parser.read_bytes()).hexdigest()):
        raise ValueError(f"stale ACMD parse {source}: regenerate with current acmd_parse.py")
    return data


def load_allowlist(path=ALLOWLIST):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("entries"), list):
        raise ValueError(f"invalid ACMD allowlist: {path}")
    entries = {}
    for entry in data["entries"]:
        if not isinstance(entry, dict) or any(not isinstance(entry.get(key), str) or
                                               not entry[key].strip() for key in
                                               ("kind", "name", "reason", "approved_by")):
            raise ValueError(f"ACMD allowlist entry needs kind, name, reason, approved_by: {entry!r}")
        if (not isinstance(entry.get("moves"), list) or not entry["moves"] or
                any(not isinstance(move, str) or not move.strip() or "*" in move
                    for move in entry["moves"])):
            raise ValueError(f"ACMD allowlist entry needs exact agent/script moves: {entry!r}")
        key = (entry["kind"], entry["name"])
        if entry["kind"] not in ("command", "case") or "*" in entry["name"] or key in entries:
            raise ValueError(f"invalid or duplicate ACMD allowlist key: {key}")
        entries[key] = entry
    return entries


class LossGuard:
    def __init__(self, move, allowlist=None):
        self.move = move
        self.allowlist = load_allowlist() if allowlist is None else allowlist
        self.losses = []

    def omit(self, frame, kind, name, what):
        entry = self.allowlist.get((kind, name))
        if entry is None or self.move not in entry["moves"]:
            raise ValueError(f"{self.move} frame {frame:g}: {what} ({kind} {name}) cannot be converted; "
                             "add an exact reviewed entry to ports/ir/tools/acmd_allowlist.json")
        self.losses.append({"move": self.move, "frame": frame, "what": what,
                            "why": entry["reason"], "approved_by": entry["approved_by"],
                            "allowlist": {"kind": kind, "name": name}})

    def remap(self, frame, box):
        self.losses.append({"move": self.move, "frame": frame,
                            "what": f"hitbox id {box['id']} (damage {box['damage']}, radius {box['radius']})",
                            "why": f"four Melee hitbox slots: {box['reason']}",
                            "source": "four-slot remap", "sample": box.get("sample"),
                            "joint": box.get("joint"), "position": box.get("position")})


def write_losses(path, *reports):
    losses, seen = [], set()
    for report in reports:
        for loss in report.get("losses", []):
            key = json.dumps(loss, sort_keys=True)
            if key not in seen:
                losses.append(loss)
                seen.add(key)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps({"version": 1, "losses": losses}, indent=2) + "\n", encoding="utf-8")
    tmp.replace(out)
    return losses
