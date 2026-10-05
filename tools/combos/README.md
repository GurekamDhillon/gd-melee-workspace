# Combo tree

A persistent record of what the in-game combo search has measured, so the next search reads it first and only
explores where the tree has no answer. One JSON file per context in `tree/`, named
`<attacker>-vs-<victim>__<stage>__rules-<rule word hex>.json` (`rules-vanilla` when Turbo is off).

Only data a search measured in the game is in a tree. Not hand-written sequences, not suggested seeds, not replay
statistics (those stay in `_build/audit-20261003/turbo-combo/slp-hints/`, uncommitted). A suggested string enters only
by being run and measured, and is then recorded as a result. No disc path, machine path, replay path or player name.

## Format (`"format": 1`)

    header   attacker, victim, stage, rules (the Turbo rule word, hex), build (exe hash and commits), date,
             start (scene text and the placement), seed, continuity (how hitstun continuity was judged),
             victim_behaviour (idle CPU: no DI, no tech)
    nodes    { "<path>": { "situation": {...}, "edges": [ edge, ... ] } }

A node is a situation reached by a path: `@ax<fox x>_vx<victim x>` is the root (the start placement), and a child
path is its parent path plus `/` plus the edge's `move`. The search's move names carry every parameter (kind, delay,
direction), so a name is one input program in one node. `situation` is informational: `victim_percent` band,
`grounded`, `note`.

An edge is one tried link:

    move                 name
    result               "true"    the next hit landed and the victim's hitstun was unbroken
                         "broke"   it hit, or the victim got free, with hitstun already over (`broke_frame`, `free_frames`)
                         "whiff"   no hit inside the horizon
                         "refused" the rule refused the exit (the log shows no 'turbo: cancel' line)
    inputs               [{f, x, y, cx, cy, buttons}]  frames counted from the node's hit (f=1 is the first sample after it)
    hit_frame, damage, victim_hitstun, victim_percent_after, fox_action_at_hit     (true and broke links)
    turbo                {cancel_from_key, into_motion, then}  when the log showed `turbo: cancel` for it
    fox_dx / fox_actions probe cases: how far Fox moved and the action ids with the frame each began
    confirmed            how many runs measured it the same way (starts at 1)
    source               "search" | "search-probe"
    conflicts            added by merge when a later measurement differs (kept, never overwritten)

Failures are recorded on purpose: a `broke`, `whiff` or `refused` edge stops the next search retesting it.

## Tools

    python tools/combos/tree.py validate  tree/<file>.json
    python tools/combos/tree.py merge     tree/<file>.json results.jsonl [more...]   # exit 2 on a conflict
    python tools/combos/tree.py export-lua tree/<file>.json -o <script data folder>/search/tree.lua
    python tools/combos/tree.py show      tree/<file>.json
    python tools/combos/test_tree.py                                                 # unit tests, plain python

`merge` takes a tree-shaped JSON or the JSON lines `search.lua` writes. Same edge, same measurement: `confirmed` goes
up. Same edge, a different `result`, `hit_frame`, `damage` or `victim_hitstun`: a conflict (for instance after an
engine change); the stored value stays and the conflict is listed on the edge and on stdout.
`import_session.py` turns the files an earlier session left (committed chain, root candidates, a probe log) into a
result file; it only reads lines a game run printed.

## How a search uses it (`search.lua`)

1. Export the tree to `tree.lua` in the search script's data folder (`MELEE_SCRIPT_DATA_DIR/search/`).
2. Load `search.lua` in a LAB match against an idle CPU from a fresh scene with the same placement, then `ts_go`
   (arguments `key=number`: `maxdepth topk Hmax killp loop bshine`; the defaults start Fox at x=-72, Falco at -63).
3. At each node the search looks up its path. Known true edges are tried first, by score, and re-measured by the run
   itself (a known link that no longer hits is logged `DRIFT`). Known `broke`/`whiff`/`refused` edges are skipped.
   New candidates are generated and measured only if the known true edges do not lead to a kill.
4. Every measured candidate is written to `results_<tag>.jsonl` (tag defaults to `run`); merge it back. A repeat run
   confirms (`confirmed`+1) or conflicts.

Checked: with the tree loaded the waveshine search followed the stored chain with zero new evaluations (evals=0),
re-measured all 10 links, reached the same KO, and merging its results bumped each link to confirmed 2 with no conflicts.

## Limits

Idle victim only (no DI, no tech, no SDI); one stage per file; one build and one rule word per file (a different rule
word is a different file); one attacker per file. The tree says what worked on that build against that victim from that
placement and a fresh stale-move queue; it is not a technique for a human opponent. Measured by state readback, not
by eye. Root candidates of the first session were stored with `inputs_from_name` (the search regenerates them from the
name); the chain edges carry exact inputs. Only true edges of that root run were kept; its failed candidates were not
logged by that older search (a current search records them).
