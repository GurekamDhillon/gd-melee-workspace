# Skins as their own mod kind: the registry (2026-10-08)

Owner's goal: "we need to make sure we can support infinite character models/skins, so people can just willy nilly install stuff."
Base: game branch `agent/skins255` at `92d5788f9` (per-fighter costume tables sized from boot counts, ids 0..254, missing art falls
back to the fighter's default; its report is `_build/tmp/codex-skins255-report.md`). This brief is built on `agent/skins-registry` (game) and
`ws/skins-registry` (this repo). Read with `docs/mods-packaging.md` (the mods folder), `melee/docs/geno.md` 22.6 (Geno costumes) and
`_research/nucleus-mod-format-2026-10-08.md` (costume DATs are typed by content; one DAT is one colour slot).

Status: **brief first, then built**. The "Results" section at the end is filled in by the lane; until then every claim here is a design.

## 1. The idea in one paragraph

A **skin** is a mod (`mods/<id>/mod.json`, `"kind": "skin"`) that adds one or more costumes to **one target fighter**: a retail fighter, an
m-ex fighter, or a Geno define. At boot the registry reads every *mounting* skin mod, turns each into extra rows at the end of that fighter's
costume tables (the tables skins255 already sizes from boot counts), and does nothing else. No costume file is opened at boot; a costume's DAT
is read the first time somebody picks it (the game's existing per-costume load, `ftData_80085820`). Skins are cosmetic: they are not part of
the simulation and never refuse a netplay match.

## 2. The format

`mods/<id>/mod.json` (the folder name is the id, as for every mod). The usual flat fields (`name`, `version`, `kind`, `authors`, `description`,
`requires`, `conflicts`, `hash`) are read by `gw_mods.c` unchanged; `kind` gains the value `skin`. The skin's own data is a nested `skin` object
(the flat reader already skips nested values; the registry re-reads the file with the strict JSON reader Geno uses):

```json
{
  "kind": "skin", "name": "Neon Fox", "version": "1.0.0", "authors": "someone",
  "skin": {
    "format": 1,
    "target": { "retail": "fox" },
    "order": 0,
    "costumes": [
      { "name": "Neon",
        "file": "skins/fox-neon/PlFxNeon.dat",
        "joint": "PlyFox5KBu_Share_joint",
        "matanim": "PlyFox5KBu_Share_matanim_joint",
        "team": "red",
        "like": 0,
        "kirby_hat": 0,
        "csp": "skins/fox-neon/csp.gxtex",
        "stock": "skins/fox-neon/stock.gxtex",
        "partner": { "file": "...", "joint": "...", "matanim": "..." } }
    ]
  }
}
```

| key | meaning |
|---|---|
| `skin.format` | `1`. A higher number is refused with a log line (the mod is skipped, nothing else changes) |
| `skin.target` | exactly one of `{"retail": "<name or Pl code>"}` (`fox`, `captain`, `PlFx.dat`; the names `geno.json` already accepts), `{"mex": "<Pl file>"}` (`PlWf.dat`: the m-ex fighter's own Pl file, which is its identity in the filtered-base model), `{"geno": "<define key>"}` (a `geno.json` define's `key`; a donor-based define wears Mario's costumes, so its skins are installed as Mario's). A content-identity check for m-ex targets (a costume built for another pack's Wolf can crash on load) is NOT in format 1: list the fighter mod in `requires` and keep skins with the pack they were made for |
| `skin.order` | optional integer, default 0: the sort key before the mod id (section 3) |
| `costumes[]` | 1..255 entries; each is one costume of the target. A pack of ten recolours is one mod with ten entries |
| `name` | what the select screen shows (printable ASCII, 1..23 characters). Missing: the mod's name (with the entry number when there are several) |
| `file` | the costume DAT, a path inside the mod's `files/` folder. It is mounted as a disc path (`files/skins/x/a.dat` answers `/skins/x/a.dat`), so give it a folder of its own: a path two mods both provide is the existing overlay conflict (`mods: X overrides Y's /path`) |
| `joint`, `matanim` | the DAT's public symbols (what `Ply<Name>5K<Colour>_Share_joint` is called inside it). `joint` is required; `matanim` is optional like in a retail row. The importer (section 9) reads them out of the DAT |
| `team` | `red`, `blue` or `green`: this costume is that team battle colour. The first one in boot order wins; a second is logged and ignored |
| `like` | the existing costume (0-based, of the fighter's original list) whose **part-visibility** and Kirby behaviour this one copies. Default 0. Link's shield, Fox's blaster etc. are gated by tables indexed per costume; this is the one number a skin has to get right for a fighter that has such tables, and 0 is right for nearly all |
| `kirby_hat` | 0..5, only meaningful on a Kirby skin: which of Kirby's six authored copy-hat colour rows this costume wears when Kirby copies. Default: `like` |
| `csp`, `stock` | optional `.gxtex` files (same container and tool as Geno's `presentation`: `pc/tools/png2gx.py --allow-odd-size`; the stock icon must be rgb5a3 or rgba8). Missing art falls back to the fighter's **default** art (skins255 rule), never to another fighter's |
| `icon` | accepted and ignored in format 1 (the select tile is the fighter's, not the costume's) |
| `partner` | only for a fighter with a partner kind (Popo with Nana, Zelda with Sheik): the partner's costume at the same index. Missing: the partner shows its own default costume at that index |

Rules the loader enforces (each failure is one log line `skins: <id>: <why>`, and skips only that costume or that mod):
unknown `format`; both or neither of `target` keys; an unknown key in `skin` or in a costume (strict, like a Geno define: a typo does not
silently do nothing); `file` absent from the mod's `files/`; a name that is not printable ASCII; a `team`/`like`/`kirby_hat` out of range.

Not in format 1 (stated so nobody expects it): a custom Kirby hat model, a costume that changes a fighter's moves (that is a Geno define), a skin
for a stage, a skin that replaces an existing costume slot (that is a plain loose-file override, which already works: `mods/<id>/files/PlFxBu.dat`).

## 3. Building the lists at boot

Order of events (all before the arena is carved, because `gw_CostumeRegionSize` sums the counts; today that sum already reads MxDt and the Geno
defines, so the skins join it):

1. `gw_mods.c` scans, resolves and mounts as always. `skin` is a known kind with the rank of `fighter` (mounts after the base and the fighter
   mods it may `requires`). A skin mod that does not mount is not read.
2. The registry reads each mounting skin mod's `mod.json` once, resolves its target to a **FighterKind** (retail: the Pl-file lookup Geno uses;
   m-ex: the dense slot whose Pl file matches; Geno: `kind = CharacterKind - 1` of the define) and checks that every `file` exists in the
   mod's payload (a `stat`, no read). A target the install lacks (the fighter mod is not enabled, the define is absent) logs
   `skins: <id>: fighter <x> is not installed - skipped` and the skin is simply not offered.
3. Per fighter, the skin costumes are sorted by `(skin.order, mod id, entry number)` using a case-folded byte compare, and appended after the
   fighter's own costumes. **So costume index = original count + position in that order.** Same mods installed => the same indices on every
   machine and every boot. Adding or removing a skin renumbers the later skins of that fighter (stated, not hidden: section 8 says what stores an
   index). `skin.order` lets a pack pin its place.
4. **Cap 255 per fighter.** The 256th costume of a fighter (counting its own) is refused: the whole entry is skipped, the log says
   `skins: <fighter> is at 255 costumes - refused <id> (<n> more skipped)`, and the order above decides who made it in, so the refusal is
   deterministic. Nothing else is affected.
5. The counts feed `gw_CostumeRegionSize` (the persistent pool is exactly the sum of the installed rows, as skins255 built it), and
   `ftData_MexInitKinds` / `GenoDefine_InitKinds` install the rows through the one production installer `ftData_PcInstallCostumes` (retail rows
   preserved byte for byte, new rows appended). Total cost per skin: 12 bytes of strings + 24 bytes of runtime row in the pool, plus the registry's
   own malloc'd record (~600 bytes). 250 skins on every one of 26 fighters is ~2 MB of pool, well inside the reservation.
6. Everything that asks "how many costumes does this fighter have" already goes through `CostumeListsForeachCharacter[k].numCostumes`
   (skins255 audited it); the three places that still answered from a static or an m-ex table are routed through the registry:
   `gm_GetNumCostumesForCKind` (replacing skins255's Mario fixture special case with the general answer), `Mex_CostumeVisIdx` (a skin
   costume answers its `like`), and the team-colour getters (`gm_80169264/90/BC`: a declared `team` wins).

**Conflicts.** Two skins never conflict by content (they are different rows). The existing resolution still applies: `conflicts`/`requires`
lists, and two mods providing one disc path (the overlay logs it, the later one wins; a skin that ships `files/PlFxBu.dat` is a slot
replacement, not a skin, and is not in this registry's business). The registry adds three refusals of its own: the 255 cap, a missing
file, and a duplicate `(mod id, entry)` identity (impossible unless two folders differ only in case; the second is dropped).

**Memory: costumes load when picked.** Boot reads only mod.json files and stats the costume files. A costume archive is read by
`ftData_80085820` the first time a player is set up with it (the same call retail uses), by name, through the overlay. A match with N
distinct costumes loads N archives; the 250 others cost nothing. The one existing "load every costume of a fighter" path (`color == 0xFF`
in `ftData_800855C8`) is audited and bounded in the build (Results).

## 4. Select screen

The Atlas select already steps `n / count Name` with X/Y (skins255). Added here: the **name** of any skin costume (not only a Geno define's) on
the card and the stepper; **paging**: on your own card with more than 12 costumes, L/R skip 10 back or forward (X/Y still step one; on the fighter grid L/R keep turning the pages), so 255 costumes are 26 presses end to end; the
portrait and the HUD stock icon come from the skin's `csp`/`stock` when it has them (through the same kit-texture path Geno's presentation
uses), else the fighter's default. The original CSS (`MELEE_NATIVE_CSS=1`) still steps by X/Y and shows the default art for any costume past
the authored ones.

## 5. Netplay: skins are cosmetic, never a refusal

The simulation and its hash never read the costume (verified in the build against `gw_RB_GameHash`; Results). So the only job is that **each
side loads the right file for the costume the other player chose, or the fighter's default when it does not have it.**

The costume byte keeps travelling as an int on the existing paths (HELLO `id:<hex>/c<N>`, lobby `CHAR`/state, the scene string `p1=...`),
but what it carries changes meaning in the netplay layer only: a **wire costume**.

- base costume (the fighter's own, index below its original count): the wire value is the index (0..254), exactly as today. Two installs
  of one fighter agree on these.
- skin costume: the wire value is `0x40000000 | (skin identity & 0x3FFFFFFF)`. A **skin identity** is a 64-bit hash of the mod id, the entry
  number within the mod and the mod's `hash` field (the packer's content digest) or, when there is none, its `version`. It reads no file at
  boot. 30 bits is enough to tell apart the <=250 skins of one fighter (collision chance ~3e-5 per pair set; a collision shows the other
  side's colliding skin, which is cosmetic).
- `gw_Skins_ToWire(fk, idx)` turns a local index into a wire value (when a player picks); `gw_Skins_FromWire(fk, wire, avoid)` turns a
  received wire value into a local index: a value below 255 is that index if the fighter has it, else 0; a skin wire value is matched against
  the local skins of that fighter, and **no match means the fighter's default costume (index 0)**. The lookup is by fighter first, so the same
  skin hash on another fighter cannot be picked up by accident.
- Where it is applied: `np.color`/`lb.color` hold wire values; the netplay entry points that take a costume from the menu convert in
  (`gw_Netplay_MenuBegin`, `RandomBegin`, `LobbyChar`, the env defaults), and the ones that hand it back to the menu convert out
  (`gw_Netplay_LocalColor`, `gw_Netplay_LobbyPlayer(who, 1)`). The scene string already carries `/c<N>` with a plain `%d`; the scene parser
  (`gw_sl_parse_player`) accepts a wire value there and resolves it with `FromWire` once the fighter is known. HELLO's info string and the
  host's state broadcast are unchanged text.
- Consequences, stated: each side may show a *different* costume on the same fighter (A sees B's `Neon` and B sees A's default). Two
  players on one fighter can end up with the same default colour when one is missing the other's skin. A peer that is an older build
  never sees a wire value above 254 because the exe hash must match to connect at all. The identity table that fighters use (`MXE`)
  is not extended: wire values carry the identity themselves, so there is nothing to exchange and nothing that can arrive late.

**Replays and savestates.** A `.slp` stores the player's costume byte (Slippi's own field), i.e. the **local index of the recorder**.
Playback on an install with the same skin set shows the same costumes; with a different set a byte past the fighter's count falls back
to costume 0 (`ftData_80085820`'s existing guard) and a byte that now names another skin shows that skin. This is cosmetic, it never
desyncs a replay (replays do not hash costumes), and it is the documented limit of a fixed-width format. Savestates and rollback
snapshots restore the fighter's struct, costume byte included, in the same process: no cross-install loading exists.

## 6. What the owner should see (the check list the lane ends with)

Listed in the Results section with the exact commands. In short: the Atlas stepper over a 100+ skin fighter with names and `L`-held paging;
a skin with art and one without (default art, no other fighter's face); a Kirby skin; a team match (a `team: red` skin is the red
costume); the MODS screen showing the skin mods; a netplay pair with one side missing skins.

## 7. Tests the lane builds

1. Native (`pc/tests/skins_core_test.c`, header-only `gw_skins_core.h`): ordering, the 255 cap and its message, `like`/`team` rules, wire
   round trips for 0..254, skin hashes, collision handling, the fallback for unknown wire values and unknown fighters, 250-skin stress.
2. Headless (in the exe, `run.sh --test`): mod.json parse and every refusal above on a temp mods folder; a retail, an m-ex and a Geno target
   resolved; the production installer called with skin rows and the retail prefix byte-identical; the scene string `c<wire>` parse;
   `gm_GetNumCostumesForCKind`, `Mex_CostumeVisIdx`, team getters; `gw_Netplay_*` wire conversions.
3. A synthetic **test pack generator** (`tools/skins/make_test_skins.py`): original/synthetic art only (generated number-on-gradient CSPs
   and stock icons), and for the model files **a copy of the player's own retail costume DAT extracted at run time from their disc image
   into a local test folder that is git-ignored** (never committed, never in the repo tree). Parameters: fighters, skins per fighter.
4. A run with 100+ installed skins over several fighters: boot time and resident memory against the same run with no skins; a match with
   the highest skin of a fighter.
5. A two-client netplay match, one side with skins the other lacks: 0 desyncs, each side showing the default for a missing skin, checked
   from the log and a screenshot-free probe (the loaded costume file name per player is logged).
6. `run.sh --test` all pass; the native suite has no failure beyond the 8 that already fail on integration.

## 8. What stores a costume index (and the limit each has)

| store | what it holds | across a skin-set change |
|---|---|---|
| a `.slp` replay | the recorder's local index | same set: identical; other set: default or another skin (cosmetic) |
| netplay wire | the wire costume (identity) | exact for base costumes, identity-matched for skins |
| a script's `gd.*` costume argument | a local index | renumbers with the set; scripts should read the count/name API, not hard-code a skin |
| the scene string `cN` | a local index (offline) or a wire value (netplay) | as the script |
| the memory card / saved CSS pick | none (the CSS does not persist a costume) | n/a |

## 9. Importing (so "willy nilly" works)

`tools/skins/skin_import.py` (workspace) turns what people already have into a skin mod folder: a costume `.dat`/`.usd` (typed by content, as
Nucleus does: the public symbol `Ply<Fighter>5K<Colour>_Share_joint` names the fighter and the colour slot), optional `csp`/`stock` PNGs
(converted to `.gxtex`), and writes `mod.json` with the symbols filled in. It never touches a disc image and never redistributes anything.
`docs/mods-packaging.md` gets a "skins" section with the format; `docs/mods-browser.md`'s index format needs no change (a skin is `kind: skin`).

## 10. Decisions for the owner (also in the lane's report)

1. **Index stability.** Alphabetical-by-id order (with `skin.order`) renumbers later skins when the set changes. Alternative: a sticky
   `userdata/skin_slots.txt` that remembers first-seen order and leaves a placeholder where a skin was removed. Recommendation: ship the
   simple rule; sticky slots only if replays of skin matches become a thing people exchange.
2. **Kirby hats.** Format 1 maps a Kirby skin onto one of the six authored hat rows; a custom hat is a later format.
3. **Cap.** 255 is the u8 byte's limit (skins255); the registry does not try to lift it.
