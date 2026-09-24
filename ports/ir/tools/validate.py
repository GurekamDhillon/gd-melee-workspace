#!/usr/bin/env python3
"""validate.py - check a character IR document against the schema, then check what JSON Schema can't.

    python ports/ir/tools/validate.py ports/halberd/ir/metaknight.brawl.ir.json

1. JSON Schema (draft 2020-12) validation against schema/character.schema.json, with the other schema
   files resolved locally (no network).
2. Referential integrity: every Id is unique; every Ref (a string value in a field whose name ends in
   a reference-ish key, see REF_KEYS) resolves to an Id in the document, unless it names another
   document ('other-doc#ns:path'), which is reported as external.
3. Evidence: every EvidenceRef used is defined in the registry, and unused evidence is listed.
4. Namespace discipline: Ids in known collections use the namespace the collection documents.

Exit 0 = valid, 1 = schema errors, 2 = integrity errors.
"""
import json
import os
import re
import sys

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_DIR = os.path.join(HERE, "..", "schema")
BASE = "https://gd-melee.local/character-ir/"

ID_RE = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9_.@/+-]+$")
REF_RE = re.compile(r"^([A-Za-z0-9_.-]+#)?[a-z][a-z0-9_]*:[A-Za-z0-9_.@/+-]+$")
EV_RE = re.compile(r"^ev:")

# Field names whose string values (or string-array values) are references to entities.
REF_KEYS = {
    "file", "files", "skeleton", "model", "material", "default_texture", "texture", "images",
    "material_animation", "reference", "used_by", "target", "variant_of", "costume", "ui", "via_base",
    "override", "declared_base", "animation", "script", "scripts", "state", "states", "subaction",
    "subactions", "action", "actions", "move", "article", "articles", "code_unit", "function",
    "functions", "callee", "affects", "container", "clip", "bank", "effect_bank", "sound_bank",
    "enters", "exits", "next", "parent_move", "provider", "hitbox_set", "copy_of", "set", "costumes",
}
# Collections whose items' ids must use a given namespace.
NAMESPACES = {
    ("resources", "files"): "file",
    ("assets", "skeletons"): "skel",
    ("assets", "models"): "model",
    ("assets", "materials"): "mat",
    ("assets", "textures"): "tex",
    ("assets", "material_animations"): "matanim",
    ("assets", "part_visibility"): "vis",
    ("assets", "costumes"): "costume",
    ("assets", "costume_sets"): "costumeset",
    ("assets", "effects"): "fxbank",
    ("assets", "audio"): "sfxbank",
    ("assets", "ui"): "ui",
    ("assets", "media"): "media",
    ("assets", "collectibles"): "collectible",
    ("behavior", "actions"): "action",
    ("behavior", "subactions"): "subaction",
    ("behavior", "scripts"): "script",
    ("behavior", "moves"): "move",
    ("behavior", "articles"): "article",
    ("code", "units"): "code",
    ("issues",): "issue",
}


def load_registry():
    reg = Registry()
    for name in os.listdir(SCHEMA_DIR):
        if name.endswith(".schema.json"):
            with open(os.path.join(SCHEMA_DIR, name), encoding="utf-8") as f:
                doc = json.load(f)
            reg = reg.with_resource(BASE + name, Resource.from_contents(doc))
    return reg


def walk(node, path=()):
    yield path, node
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, path + (i,))


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    with open(sys.argv[1], encoding="utf-8") as f:
        doc = json.load(f)

    reg = load_registry()
    root = reg.contents(BASE + "character.schema.json")
    validator = Draft202012Validator(root, registry=reg)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
    for e in errors[:50]:
        loc = "/".join(str(p) for p in e.absolute_path) or "(root)"
        print(f"SCHEMA {loc}: {e.message[:300]}")
    if errors:
        print(f"{len(errors)} schema error(s)")
        return 1

    ids = {}
    problems = []
    for path, node in walk(doc):
        if isinstance(node, dict) and isinstance(node.get("id"), str) and ID_RE.match(node["id"]):
            if node["id"].startswith("ev:"):
                continue
            if node["id"] in ids:
                problems.append(f"duplicate id {node['id']} at {'/'.join(map(str, path))} and {ids[node['id']]}")
            ids[node["id"]] = "/".join(map(str, path))

    evidence = {e["id"] for e in doc.get("evidence", [])}
    used_ev = set()
    external = set()
    for path, node in walk(doc):
        if not path:
            continue
        key = path[-1] if not isinstance(path[-1], int) else (path[-2] if len(path) > 1 else None)
        if isinstance(node, str) and EV_RE.match(node) and path[-1] != "id":
            used_ev.add(node)
            if node not in evidence:
                problems.append(f"undefined evidence {node} at {'/'.join(map(str, path))}")
        elif isinstance(node, str) and key in REF_KEYS and REF_RE.match(node):
            if "#" in node:
                external.add(node)
            elif node not in ids:
                problems.append(f"dangling ref {node} at {'/'.join(map(str, path))}")

    for coll, ns in NAMESPACES.items():
        node = doc
        for k in coll:
            node = node.get(k, {}) if isinstance(node, dict) else {}
        if isinstance(node, list):
            for item in node:
                if isinstance(item, dict) and "id" in item and not item["id"].startswith(ns + ":"):
                    problems.append(f"{'/'.join(coll)} item {item['id']} should use namespace '{ns}:'")

    for p in problems:
        print("INTEGRITY", p)
    unused = sorted(evidence - used_ev)
    print(f"ids: {len(ids)}  evidence: {len(evidence)} ({len(unused)} unused)  external refs: {len(external)}")
    if unused:
        print("unused evidence:", ", ".join(unused))
    if problems:
        print(f"{len(problems)} integrity problem(s)")
        return 2
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
