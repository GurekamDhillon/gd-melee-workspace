# Character IR

A semantic, evidence-backed **intermediate representation of one fighter**: what it's made of, how
it plays, what code it ships, and how a framework (m-ex) and a host runtime (GD's Melee) handle it.
Every port in `ports/` first describes its source fighter in this shape, so a Brawl fighter and a
Melee fighter can be compared field by field before anything is built.

```
schema/                   JSON Schema (draft 2020-12), one file per layer
  character.schema.json   root: subject, evidence, identity, coverage, parity + the layers below
  common.schema.json      ids/refs, evidence, confidence, index spaces, engine addresses, units, blobs, issues
  resources.schema.json   files, containers, symbols, how the engine locates each file
  assets.schema.json      skeleton, bone roles, models, materials, textures, animation library, effects, audio, UI
  behavior.schema.json    attributes, body, actions, subactions, scripts (+ languages), moves, variables, articles
  code.schema.json        relocatable code units, overrides, hidden imports, intrinsics, escapes, functions
  integration.schema.json frameworks (registration, hook slots, id rules, API, patches) and hosts
  engines/melee.md        index spaces and engine extension blocks for melee.gc / melee.mex / melee.gdport
tools/
  validate.py             schema + referential integrity + evidence + namespace checks
```

Layers go identity → resources → assets → behavior → code → integration; a layer only points down.
Every fact carries evidence (a tool output, a decomp symbol, a source file) and a confidence.

## Validate an instance

```
pip install jsonschema referencing
python ports/ir/tools/validate.py ports/halberd/ir/metaknight.brawl.ir.json
```

Exit 0 = valid, 1 = schema errors, 2 = integrity errors.

## Instances

| Instance | Port |
|---|---|
| [`../halberd/ir/metaknight.brawl.ir.json`](../halberd/ir/metaknight.brawl.ir.json) | Halberd: vanilla *Brawl* Meta Knight (attributes, 290 actions, PSA scripts, skeleton, relocatable code). |

The IR describes the source game's data; it contains no game assets.
