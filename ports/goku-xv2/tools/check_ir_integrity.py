"""Independent source/host gate beyond JSON Schema; never edits the source package.

Checks actual external refs, unique scopes, provenance, raw-file coverage, all
referenced file hashes and JSON Pointers. Each distinct file is read once here;
decoded JSON is loaded one sidecar at a time rather than retained in memory.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
PORT = ROOT / "ports/goku-xv2"
REF = re.compile(r"^([A-Za-z0-9_.-]+#)?[a-z][a-z0-9_]*:[A-Za-z0-9_.@/+-]+$")
DEFERRED_DOCS = {"ports/goku-xv2/ROLE-MAP.md", "ports/goku-xv2/PARITY.md", "ports/ir/schema/engines/xv2.md"}


def walk(value, path=()):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, path + (index,))


def ids(doc):
    return {v["id"] for _, v in walk(doc) if isinstance(v, dict) and isinstance(v.get("id"), str)}


def check_references(doc, host):
    errors = []
    local, remote = ids(doc), ids(host)
    for path, value in walk(doc):
        if (not isinstance(value, str) or value.startswith(("http://", "https://"))
                or not REF.fullmatch(value) or (path and path[-1] == "id")):
            continue
        if "#" in value:
            owner, ident = value.split("#", 1)
            if owner != host["document_id"] or ident not in remote:
                errors.append(f"Unresolved external ref {value} at {path}")
        elif value not in local:
            errors.append(f"Unresolved local ref {value} at {path}")
    return errors


def json_pointer(value, pointer):
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise ValueError("JSON Pointer must begin with /")
    for token in pointer[1:].split("/"):
        if re.search(r"~(?![01])", token):
            raise ValueError("Invalid JSON Pointer escape")
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise ValueError("Invalid JSON Pointer array index")
            value = value[int(token)]
        else:
            value = value[token]
    return value


def check_files(doc, root, defer_docs=False):
    files = defaultdict(lambda: {"hashes": set(), "sizes": set(), "pointers": set(), "records": [], "actions": []})
    errors = []
    def register(path, digest=None, size=None, pointer=None, record=None, action=None):
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = root / resolved
        row = files[resolved.resolve()]
        if digest: row["hashes"].add(digest)
        if size is not None: row["sizes"].add(size)
        if pointer is not None: row["pointers"].add(pointer)
        if record is not None: row["records"].append((pointer, record))
        if action is not None: row["actions"].append((pointer, action))

    for evidence in doc.get("evidence", []):
        path = evidence.get("path", "")
        if not path or path.startswith(("http://", "https://")):
            continue
        if defer_docs and path in DEFERRED_DOCS:
            continue
        register(path, evidence.get("sha256"), evidence.get("length"))
    resource_by_id = {r["id"]: r for r in doc.get("resources", {}).get("files", [])}
    for resource in resource_by_id.values():
        if resource.get("local_path"):
            register(resource["local_path"], resource.get("sha256"), resource.get("size"))
    for _, node in walk(doc):
        if not isinstance(node, dict):
            continue
        if node.get("kind") == "sidecar":
            if not node.get("path") or not node.get("sha256"):
                errors.append("Sidecar is missing path or hash")
                continue
            match = re.search(r"JSON Pointer (.*?);", node.get("note", ""))
            register(node["path"], node["sha256"], pointer=match.group(1) if match else None)
        if "decoded_pointer" in node:
            resource = resource_by_id.get(node.get("source_file"), {})
            blob = resource.get("engine", {}).get("xv2.pc", {}).get("decoded", {})
            if not blob.get("path"):
                errors.append(f"Decoded pointer has no source sidecar: {node.get('source_file')}")
            else:
                register(blob["path"], blob.get("sha256"), pointer=node["decoded_pointer"])
        if "op" in node and "raw" in node and "frame" in node:
            extra = node.get("args", {}).get("engine", {}).get("xv2.pc", {})
            resource = resource_by_id.get(extra.get("source_file"), {})
            blob = resource.get("engine", {}).get("xv2.pc", {}).get("decoded", {})
            if blob.get("path") and extra.get("decoded_pointer"):
                register(blob["path"], blob.get("sha256"), pointer=extra["decoded_pointer"],
                         record={"typeId": node["raw"].get("opcode"), "kind": node["raw"].get("engine_name"),
                                 "startFrame": node["frame"], "durationFrames": extra.get("duration_frames")})
        if isinstance(node.get("index"), dict) and node["index"].get("space") == "xv2.bcm.node":
            extra = node.get("engine", {}).get("xv2.pc", {})
            resource = resource_by_id.get(extra.get("source_file"), {})
            blob = resource.get("engine", {}).get("xv2.pc", {}).get("decoded", {})
            if blob.get("path") and extra.get("decoded_pointer"):
                register(blob["path"], blob.get("sha256"), pointer=extra["decoded_pointer"], action=node)
    pointers = hashed = records = actions = 0
    for path, expected in files.items():
        if not path.is_file():
            errors.append(f"Missing file {path}")
            continue
        raw = path.read_bytes()
        if expected["hashes"]:
            hashed += 1
            actual = hashlib.sha256(raw).hexdigest()
            if expected["hashes"] != {actual}:
                errors.append(f"File hash mismatch {path}")
        if expected["sizes"] and expected["sizes"] != {len(raw)}:
            errors.append(f"File size mismatch {path}")
        if expected["pointers"]:
            try:
                decoded = json.loads(raw.decode("utf-8-sig"))
            except (ValueError, UnicodeDecodeError) as error:
                errors.append(f"Cannot decode pointer sidecar {path}: {error}")
                continue
            for pointer in expected["pointers"]:
                pointers += 1
                try:
                    json_pointer(decoded, pointer)
                except (KeyError, IndexError, TypeError, ValueError) as error:
                    errors.append(f"Invalid JSON pointer {pointer} in {path}: {error}")
            for pointer, record in expected["records"]:
                records += 1
                try:
                    source = json_pointer(decoded, pointer)
                    if not isinstance(source, dict):
                        errors.append(f"Decoded event target is not an object at {path}#{pointer}")
                        continue
                    for field, value in record.items():
                        if source.get(field) != value:
                            errors.append(f"Decoded event {field} mismatch at {path}#{pointer}")
                except (KeyError, IndexError, TypeError, ValueError, AttributeError):
                    pass  # The pointer check above already reports malformed targets.
            if expected["actions"]:
                nodes = decoded["nodes"]
                children = defaultdict(list)
                by_source = {str(n["sourceId"]): n for n in nodes}
                for node in nodes:
                    if node["parent"] is not None: children[node["parent"]].append(node)
                for pointer, action in expected["actions"]:
                    actions += 1
                    try:
                        node = json_pointer(decoded, pointer)
                    except (KeyError, IndexError, TypeError, ValueError):
                        continue
                    extra = action["engine"]["xv2.pc"]
                    scope = extra["scope"]
                    edges = {"action:" + scope + "/" + child["id"] for child in children[node["id"]]}
                    for field in ("LoopAsChild", "LoopAsSibling"):
                        target = by_source.get(str(node["sourceFields"].get(field)))
                        if target: edges.add("action:" + scope + "/" + target["id"])
                    if set(action.get("enters", [])) != edges:
                        errors.append(f"BCM graph edges differ from decoded child/loop links at {action['id']}")
                    if (action["index"]["value"] != int(node["sourceId"])
                            or action.get("name") != node["inputLabels"]
                            or extra.get("input_mask") != node["inputMask"]):
                        errors.append(f"BCM node label/index/input mismatch at {action['id']}")
                    for field in ("BacEntryPrimary", "BacEntryAirborne", "BacEntryCharge",
                                  "BacEntryUserConnect", "BacEntryVictimConnect", "BacEntryTargetingOverride"):
                        value = node["sourceFields"].get(field)
                        binding = extra.get("bac_bindings", {}).get(field)
                        valid = isinstance(value, int) and value >= 0 and value != 65535
                        if valid and (not binding or binding.get("index", {}).get("value") != value):
                            errors.append(f"BCM BAC binding lost or changed {field} at {action['id']}")
                        elif not valid and binding:
                            errors.append(f"BCM BAC sentinel incorrectly bound {field} at {action['id']}")
    return errors, {"files": len(files), "hashed_files": hashed, "json_pointers": pointers,
                    "decoded_events": records, "decoded_actions": actions}


def check_semantics(doc, host, package, root):
    errors = []
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8-sig"))
    checks = dict((line.split("  ", 1)[1], line.split("  ", 1)[0])
                  for line in (package / "package-files.sha256").read_text().splitlines())
    resources = {r["name"]: r for r in doc["resources"]["files"]}
    for asset in manifest["assets"]:
        if asset["kind"] != "raw": continue
        resource = resources.get(asset["source"])
        if not resource:
            errors.append(f"Raw file absent from resources: {asset['source']}")
        elif resource.get("sha256") != asset["sha256"] or resource.get("sha256") != checks[asset["file"]]:
            errors.append(f"Raw file manifest/checksum disagreement: {asset['source']}")
    for path, node in walk(doc):
        if isinstance(node, dict) and node.get("confidence") == "observed":
            errors.append(f"Unsupported runtime-observed confidence at {path}")

    # File-local IDs must remain unique within their explicit owning file.
    for collection, space in [(doc["behavior"]["actions"], "xv2.bcm.node"),
                              (doc["behavior"]["subactions"], "xv2.bac.entry")]:
        scoped = set()
        for row in collection:
            scope = row.get("engine", {}).get("xv2.pc", {}).get("scope")
            idx = row["index"]
            key = (scope, idx["value"])
            if not scope or scope not in resources or idx["space"] != space or key in scoped:
                errors.append(f"Invalid/duplicate file-scoped index on {row['id']}")
            scoped.add(key)
    scoped = set()
    for clip in doc["assets"]["animations"]["clips"]:
        extra = clip["engine"]["xv2.pc"]
        idx = extra["clip_index"]
        key = (extra["scope"], idx["value"])
        if clip["file"] != "file:" + extra["scope"] or idx["space"] != "xv2.ean.clip" or key in scoped:
            errors.append(f"Invalid/duplicate clip scope on {clip['id']}")
        scoped.add(key)
    schema = json.loads((root / "ports/ir/schema/behavior.schema.json").read_text())
    expected_inputs = set(schema["$defs"]["Move"]["properties"]["input"]["enum"])
    moves = doc["behavior"]["moves"]
    if Counter(m["input"] for m in moves) != Counter(expected_inputs):
        errors.append("Canonical move inputs are missing or duplicated")
    parity_here = Counter(p["here"] for p in doc["parity"])
    subs = {s["id"]: s for s in doc["behavior"]["subactions"]}
    for move in moves:
        if parity_here[move["id"]] != 1:
            errors.append(f"Missing/duplicate canonical move parity: {move['id']}")
        evidence = set(move["provenance"].get("evidence", []))
        for ref in move.get("subactions", []):
            sub = subs.get(ref)
            if sub:
                raw = {e for e in sub["provenance"]["evidence"] if e.startswith("ev:raw/")}
                if not raw <= evidence:
                    errors.append(f"Move provenance omits candidate source: {move['id']} {sorted(raw - evidence)}")
    skels = {s["id"]: s for s in doc["assets"]["skeletons"]}
    for role in doc["assets"]["bone_roles"]:
        joints = {j["index"]: j for j in skels[role["skeleton"]]["joints"]}
        joint = joints.get(role["joint"])
        if not joint or not any(p["here"] == joint["id"] and f"Role {role['role']};" in p["differences"]
                                for p in doc["parity"]):
            errors.append(f"Missing role parity: {role['role']}")
    hostattrs = {a["engine_name"]: a for a in host["behavior"]["attributes"]["common"]}
    sourceattrs = {a["engine_name"]: a for a in doc["behavior"]["attributes"]["common"]}
    required = json.loads((root / "tools/geno/artist/data/default_attributes.json").read_text())["attributes"]
    for field in required:
        h, s = hostattrs.get(field), sourceattrs.get(field)
        if not h or not s:
            errors.append(f"Missing importer attribute comparison: {field}")
            continue
        if "value" in s or s["provenance"]["confidence"] != "unknown" or s["key"] != h["key"]:
            errors.append(f"Source attribute falsely populated: {field}")
        rows = [p for p in doc["parity"] if p["here"] == "issue:attribute/" + h["key"]]
        if len(rows) != 1 or rows[0]["relation"] != "no_counterpart" or rows[0]["there"] != host["document_id"] + "#file:plca":
            errors.append(f"Incorrect attribute parity: {field}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ir", type=Path, default=PORT / "ir/goku.xv2.ir.json")
    parser.add_argument("--host-ir", type=Path, default=PORT / "ir/host.melee.ir.json")
    parser.add_argument("--defer-docs", action="store_true", help="Only while the three provenance documents are being written")
    args = parser.parse_args()
    doc = json.loads(args.source_ir.read_text(encoding="utf-8"))
    host = json.loads(args.host_ir.read_text(encoding="utf-8"))
    package = Path(doc["integration"]["hosts"][0]["engine_detail"]["xv2.pc"]["source_package"])
    errors = check_references(doc, host)
    file_errors, stats = check_files(doc, ROOT, args.defer_docs)
    errors += file_errors + check_semantics(doc, host, package, ROOT)
    print(json.dumps({**stats, "parity_rows": len(doc["parity"]), "errors": len(errors)}))
    for error in errors[:50]: print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
