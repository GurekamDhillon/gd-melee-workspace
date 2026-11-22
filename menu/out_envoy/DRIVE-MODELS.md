# Envoy drive models: build specs (step 9)

Design only. Nothing here is built. Written by `build_step9.py`, from the same part lists that draw `preview/step9-drives-a.png` and `-b.png`, so the triangle counts below are counted from real meshes, not estimated. Everything is original geometry; nothing is traced or adapted from any game.

## 1. What the existing generator does (the baseline)

`pc/scripts/examples/envoy_drives/tools/make_drives.py` (standard library only) writes six family bodies, a glass shell, three rarity overlays and one shared atlas.

- **Primitives.** `Mesh.tri` (flat-shaded, wound away from a centre), `poly` (convex fan), `pyramid`, and `prism`: a convex 2D polygon extruded from z0 to z1 with the front cap shrunk about its centroid, so the side walls are the bevel. Bodies use bevels 0.55 to 0.62. Spheres are an inlined icosahedron or octahedron. `ring_overlay` is a three-sided ring about the vertical axis.
- **Size.** `normalise` centres each body and scales it into a cube of half-size 2.2 world units; Envoy lifts a drive 2.6 and draws it at scale 1.15.
- **Budget.** Bodies are 24 to 80 triangles; overlays 74 to 146; the shell 20. Every triangle has its own three vertices (flat shading), 32 bytes each.
- **Colour.** One 128 x 128 atlas; each 5-texel row is a ramp along u from a dark body colour to a bright one, and a second glow atlas holds the emissive part of the same ramp. A vertex picks a row (v) and a place on the ramp (u), so a seam or a core is bright and a wall is dark. No per-model texture.
- **Glass and glow.** The glass shell is an icosahedron drawn with alpha 0.28. The shader study (`scratch/envoy-notes/shader-effects-study.md`) found that today the glow atlas is sampled on the CPU and baked into vertex colours, and the glass is plain alpha blend: there is no bloom and no emissive pass.
- **Rarity.** An added overlay model at the same transform, never a new body. This document keeps that rule.

## 2. What must be added to the generator

| addition | what | why |
|---|---|---|
| `ring_xy(c, r, w, a0, a1, segs, zh, tilt)` | a ring or an arc facing the camera: a flat front face and two slanted back faces, 6 triangles a segment, end caps on arcs, an optional lean about X | Tempo's rings, Sky's arcs, Nova, Gatekeeper; 14 segments for a full ring |
| `ball(c, r)` | the icosahedron as a helper (20 triangles) | Comet, Snowball, pivots and knots |
| part lists | a drive is a list of parts (`P` prism, `R` ring, `B` ball) with a role: body, hot, or raised mark. `build(parts, family)` meshes it; `glyph_inner(parts)` draws the badge glyph from the same list | the model and the glyph cannot drift apart; the badge baker reads `glyphs/<id>.svg` |
| family rows in the Party pack colours | `fire` #FF7A1F, `frost` #62CCF5, `sky` #86D63C, `tempo` #C866F2, `guard` #C99455, `util` #AEA8CC, each with a `_hot` row (the colour mixed 35% toward a pale tint, to that tint) | the orbiter must be the colour of its sticker; the old rows (red, green, blue, yellow, purple, white) can stay for the old six bodies |
| rows `white`, `sun`, `ink`, `foil0` to `foil5` | the Rare ring, the ascended gold, the hull, the Epic ring | 22 rows are in use today and 25 fit (128 / 5); the new set needs 12 family rows + 9, so drop the six `prism` rows and the three old rarity rows, or make the atlas 128 x 256 |
| 32 Unique rows | a body row and a hot row per Unique | this is what forces the taller atlas; or give Uniques their own 128 x 128 atlas, which the shader work wants anyway |
| `hull(mesh, 0.09)` | a copy of the mesh pushed out along its face normals, wound inside out, in the `ink` row: the outline | the single biggest gain in legibility at 24 px. Doubles the triangle count. Better as an outline pass in a shader |
| `tier_ring(tier)` | the Rare and Epic rings as overlay models (`drive_ring_rare2`, `drive_ring_epic`), 84 triangles each, plus an 16-triangle spark | replaces magic / rare / unique overlays, which are a different tier set |
| `halo()` and `star()` | the ascended overlay: a 12-segment flat ring (72 triangles) and a two-sided ten-point star (20) | one overlay model serves all 46 |
| one mesh per drive | `drive_<id>.gxmesh`, `.material.json`, `.coll.json` for 46 drives and 16 Uniques | `drive_models.lua` picks by id, falling back to the family body |
| orbit facing | not the generator: the drawer must face models to the camera and rock them, not spin them | these are reliefs 0.4 deep; edge-on they vanish |

## 3. Shared treatments

**Proportions.** Parts are given in a box of -1 to 1 (x right, y up, z toward the camera); `normalise` then scales to half-size 2.2 as today. Body parts are prisms from z -0.2 to 0.2 with bevel 0.72 unless a spec says otherwise; hot parts z -0.24 to 0.26; raised marks z 0.14 to 0.33 in the hot row. Ramp positions: back 0.3, bevel rim 0.95, cap 0.7 (hot: 0.4, 0.95, 0.75). The bright bevel rim is the glowing seam of the existing family look.

**Triangle budget.** 16 to 168 for a body (mean 73), counted below; rings are the cost (84 a full ring), so Relay with two is the largest. With the ink hull, twice that. The existing bodies are 24 to 80, with a mean of 51, so the average rises by about half; five drives in orbit with hulls stay under 2,000 triangles.

**Orbit.** Each model faces the camera and rocks 12 degrees about its vertical axis (period 2.4 s, each slot a fifth of a period out of step). The per-drive animation below is added to that. The near half of the orbit draws at 26 px on a 640 x 480 screen, the far half at 21 px and behind the fighter.

| what | on the model | on the badge | better as a shader? | geometry-only version (drawn on the sheet) |
|---|---|---|---|---|
| Common | the body alone | plain edge | no | - |
| Rare | a white ring lying flat under the form (radius 0.84 at y -1.14), so the outline above it is untouched | thick white die-cut | no | the `white` row ring, 84 triangles |
| Epic | the same ring in foil, and a four-point sunny spark riding it | foil rim and spark | **yes**: a view-angle iridescence on the ring | the 14 segments take `foil0` to `foil5` in turn and the ring spins once in 3 s |
| Level 1, 2, 3 | size x1.0, x1.15, x1.3; seams lit at 2; the core pulses at 3 | one, two, three pips | **yes**: a rim light whose strength is the level | size alone, and the hot row baked one ramp step brighter per level (three copies of the u offset, no new mesh) |
| Levels 4 to 9 | the level 3 size | gold pips (4 to 6), white pips (7 to 9), as step 7 | no | - |
| Ascended (level 5) | the hot row swaps to `sun` (gold seams); a gold star (0.76 across) inside a small flat gold ring (radius 0.52) floats 0.4 over the form | the gold star on the badge's lower right edge | **yes**: a soft additive glow with slow rays round the star, the star as a sprite | the ring and star overlay model, 92 triangles |
| Unbound (level 9) | the ascended model at x1.3, riding 20 px above the fighter's head instead of in the ring | as the content pass: it leaves the row | no | - |
| The ink edge | an ink outline about 1.2 px at orbit size | (the badge has its own) | **yes**: an outline pass | `hull()`, the inside-out copy |

Tier sits under the form, ascension over it, level is size: three cues in three different places, so an ascended Epic at level 6 still reads and the family outline between them is never covered. A first version put the Rare ring round the waist and a large halo behind the form; both were dropped because the ring cut the outline and the halo made every ascended drive round, which is the language of Tempo.

**The floor drop.** Step 7's drop with the model in the badge's place. The white disc (r 15, 2.4 ink edge) stays behind the model as a backing plate, centre 27 px above the floor; the sunny ellipse rings (21 x 6.5 and 33 x 10) stay on the floor; the name tag stays 20 px above the disc. The model is drawn 22 px across, bobs 2 px (period 1.2 s) and rocks; the glass shell is dropped (the disc does its job). Tier rings show. An ascended drive cannot drop.

**The fly-in (30 frames).** Frames 0 to 6: the disc scales to nothing and the floor rings fade. Frames 0 to 30: the model follows an arc from the disc to its orbit slot, 62 px high at the middle, leaving a dotted sunny trail of five points that fade over 12 frames. Frame 30: it joins the orbit and the HUD chip gets step 7's sunny ring for 90 frames.

## 4. The six shape languages

| family (pool) | colour | language | why it separates at 24 px |
|---|---|---|---|
| Fire (RED) | #FF7A1F | Tall, round at the foot, one sharp point up. | Taller than wide and uneven top to bottom. Nothing else in the set tapers upward. |
| Frost (PURPLE) | #62CCF5 | Six-sided crystals and their clusters. | Straight edges at 60 degrees and points all round. The only family built on the hexagon. |
| Sky (YELLOW) | #86D63C | Wide, swept and open: fans, arcs, carets, wings. | Wider than tall, with daylight through or under it. The only family that spreads sideways. |
| Tempo (GREEN) | #C866F2 | A ring or a dial, with one thing that moves. | A round form with a hole reads at any size, and no other family is round. |
| Guard (BLUE) | #C99455 | Heavy plates and blocks with a flat top. | The most filled silhouette in the set: square shoulders, no hole, no point up. |
| Utility (WHITE) | #AEA8CC | Plain solids in sets of two or more. | Counted pieces with ink between them. No other family is made of separate equal parts. |

## 5. The 46 drives

Rows: body `<family>`, hot `<family>_hot`. "Emissive" lists the parts in the hot row beyond the bevel rims, which glow on every drive. Triangles are the body alone, without hull or overlays.

### Fire (RED), rows `fire` and `fire_hot`

| id | name | tier | triangles | form | emissive parts | orbit animation | glyph |
|---|---|---|---|---|---|---|---|
| `ember` | Ember | Common | 72 | A 10-sided teardrop prism, tip leaning left, 1.2 wide by 2.0 tall, bevel 0.72; a second small teardrop proud of the face as the core. | 1 of 2 parts | Faces the camera, rocks 12 degrees; the tip flickers (scale Y 1.0 to 1.06, 0.5 s). | `glyphs/ember.svg`: One flame with a hot core: the plain burst, and the family's base form. |
| `bolt` | Bolt | Common | 16 | Two long triangle prisms overlapped into a zigzag, 1.3 wide by 2.0 tall, bevel 0.55. | 0 of 2 parts | Faces the camera; snaps 8 degrees left and right every 20 frames, never eases. | `glyphs/bolt.svg`: A tall zigzag blade, sharp at both ends: it jumps to a foe. |
| `nova` | Nova | Rare | 76 | A narrow teardrop prism (0.8 by 2.0) and two ring arcs of 90 degrees, radius 0.82, left and right of it. | 0 of 3 parts | The arcs breathe outward (radius 0.82 to 0.95) on the drive's 12-second clock and snap back on the fire. | `glyphs/nova.svg`: A flame between two blast arcs: the blast goes out around you. |
| `wildfire` | Wildfire | Rare | 108 | A teardrop prism 0.8 by 1.9 and two small teardrops (0.44 by 0.76) standing apart from it at its foot, leaning out 20 degrees. | 2 of 3 parts | Rocks 12 degrees; the small flames hop 0.1 out and back, out of step with each other. | `glyphs/wildfire.svg`: One tall flame with a small one thrown off to each side: the fire jumps to the others. |
| `spire` | Spire | Rare | 20 | One tall triangle prism (0.56 wide at the foot, 1.75 tall) on a flat slab 1.3 wide; the needle uses the hot row. | 1 of 2 parts | Faces the camera, no rock; the needle stretches 10% on the drive's 10-second clock. | `glyphs/spire.svg`: A needle on a foot plate: it rises from the floor. |
| `kindle` | Kindle | Common | 48 | A thin upright bar (0.3 by 1.1) with a teardrop prism (0.84 by 1.1) as its head. | 0 of 2 parts | Rocks 12 degrees; the head flares (scale 1.2, 6 frames) on a smash that lands. | `glyphs/kindle.svg`: A struck match: a small flame on a stick. One hard hit lights it. |
| `cinder_heart` | Cinder Heart | Rare | 100 | Two 8-sided discs and a triangle prism make the coal; a small teardrop stands in the cleft (hot row). | 1 of 4 parts | Beats (scale 1.0 to 1.08, twice a second) once it holds a pip; faster at 20 pips. | `glyphs/cinder_heart.svg`: A heart-shaped coal with a flame at the cleft: it keeps what it has burned. |
| `solar_flare` | Solar Flare | Epic | 72 | A half disc (radius 0.55, flat side down) and five triangle prisms fanned over it, the middle one longest. | 5 of 6 parts | The rays lengthen one after another, left to right, on the 8-second clock; still when the wearer is not Blazing. | `glyphs/solar_flare.svg`: A rising half sun with five flame rays: fire from the sky. |

### Frost (PURPLE), rows `frost` and `frost_hot`

| id | name | tier | triangles | form | emissive parts | orbit animation | glyph |
|---|---|---|---|---|---|---|---|
| `frost` | Frost | Common | 80 | Three long hexagonal bars (0.34 by 2.0, pointed ends) crossed at 60 degrees, and a small hexagon boss. | 1 of 4 parts | Turns slowly in its own plane (one turn in 6 s), always facing the camera. | `glyphs/frost.svg`: A six-armed ice crystal: the family's base form. |
| `shatter` | Shatter | Common | 40 | One hexagon prism (radius 0.9) cut by a slanted plane into two five-sided prisms, moved 0.36 apart; one loose shard. | 1 of 3 parts | The halves drift 0.1 apart and back; they clap shut and fly open on the fire. | `glyphs/shatter.svg`: A hexagon broken in two, the halves slipped apart. |
| `hex` | Hex | Common | 56 | One flat-topped hexagon plate (radius 0.94, depth 0.3) cut by two planes at 45 degrees into four wedges 0.2 apart. | 0 of 4 parts | Faces the camera, rocks 12 degrees; the four wedges close up for 10 frames when a foe is Marked. | `glyphs/hex.svg`: A hexagon cut through by a cross into four pieces: the mark it leaves. |
| `static` | Static | Common | 72 | A tall six-sided column (0.72 by 2.0, pointed ends), a triangle barb on each side, a three-bar zigzag raised on the face. | 3 of 6 parts | The barbs twitch in and out 0.06, irregularly; the zigzag blinks while a foe is Shocked. | `glyphs/static.svg`: An upright crystal with two barbs and a zigzag belt: charge held in ice. |
| `affliction` | Affliction | Rare | 80 | Four small hexagon prisms (radius 0.34) in a diamond of honeycomb cells, 0.17 apart. | 0 of 4 parts | Faces the camera; a cell lights (hot row) for each word on the foe being hit. | `glyphs/affliction.svg`: Four hexagons in a honeycomb: one cell for each word a foe can carry. |
| `contagion` | Contagion | Rare | 116 | A hexagon prism (radius 0.48) with three small hexagons (radius 0.25) on short necks at 90, 210 and 330 degrees. | 1 of 7 parts | Turns in its own plane; the buds push out 0.15 and return when a word spreads. | `glyphs/contagion.svg`: One crystal budding three small ones: the word spreads outward. |
| `steam` | Steam | Epic | 88 | The lower half of a hexagon prism (1.6 wide) and three two-bar plumes above it, the middle one tallest (hot row). | 6 of 7 parts | The plumes rise and fade in turn (a 3-step loop, 0.9 s); only while a foe is both Burning and Chilled. | `glyphs/steam.svg`: Half a crystal as a cup, three plumes rising from it: ice meeting fire. |

### Sky (YELLOW), rows `sky` and `sky_hot`

| id | name | tier | triangles | form | emissive parts | orbit animation | glyph |
|---|---|---|---|---|---|---|---|
| `feather_storm` | Feather Storm | Common | 56 | Three kite prisms from one root at 56, 90 and 124 degrees, the middle one 1.86 long; a small ball at the root. | 1 of 4 parts | The fan opens and closes 8 degrees; it snaps shut on the fire and the feathers leave. | `glyphs/feather_storm.svg`: A fan of three feathers: the three it throws. The family's base form. |
| `gatekeeper` | Gatekeeper | Rare | 92 | A half ring (radius 0.7, width 0.34) on two upright bars with wide feet. | 0 of 5 parts | Faces the camera, no rock; the arch glows while a foe is offstage. | `glyphs/gatekeeper.svg`: An open arch on two feet: the gate at the edge of the stage. |
| `comet` | Comet | Common | 52 | An icosahedron (radius 0.4) above a 140-degree ring arc (radius 0.86) that opens upward. | 1 of 2 parts | The ball bobs 0.15 above the arc on the 9-second clock and jumps on the fire. | `glyphs/comet.svg`: A ball thrown up off a wide arc: the wave that pops foes up. |
| `updraft` | Updraft | Common | 48 | Two wide V-shaped prisms pointing up (1.8 wide, arms 0.3 thick), stacked 0.75 apart. | 0 of 4 parts | The lower caret rises into the upper one and resets (a 1 s loop); both flash when the jump is granted. | `glyphs/updraft.svg`: Two wide carets, one over the other: a second lift. |
| `skyhook` | Skyhook | Rare | 76 | An upright bar, a half ring at its foot turning up into a barb, and one kite prism as a wing on the shank. | 1 of 4 parts | Swings 10 degrees from its top like a hanging hook. | `glyphs/skyhook.svg`: A hook with a small wing on its shank: it holds you in the air. |
| `meteor` | Meteor | Epic | 44 | A triangle prism pointing down (1.0 wide) with two kite prisms and one bar streaming up behind it. | 1 of 4 parts | Points down always; shakes 0.04 while a foe is below the stage. | `glyphs/meteor.svg`: A dart diving point down with three tails: the KO off the bottom. |
| `thunderhead` | Thunderhead | Rare | 112 | Three 8-sided discs on a flat bar make the cloud (1.8 wide); two small triangle prisms make the bolt (hot row). | 2 of 6 parts | Drifts 0.08 left and right; the bolt shows only when the charge is over half. | `glyphs/thunderhead.svg`: A flat-bottomed cloud with a small bolt under it. |

### Tempo (GREEN), rows `tempo` and `tempo_hot`

| id | name | tier | triangles | form | emissive parts | orbit animation | glyph |
|---|---|---|---|---|---|---|---|
| `rush` | Rush | Common | 120 | A ring (radius 0.5, width 0.28) at the right and three flat bars trailing left, the middle one longest. | 0 of 4 parts | The ring turns in its plane; the bars stretch while Haste is on. | `glyphs/rush.svg`: A wheel with three speed lines behind it. |
| `tailwind` | Tailwind | Rare | 104 | A ring (radius 0.62) with a bar through its centre ending in a triangle arrow head at the right. | 1 of 3 parts | The arrow slides 0.2 through the hoop and back (0.8 s); faster in Haste. | `glyphs/tailwind.svg`: A hoop with an arrow flying through it: the push from behind. |
| `clean_landing` | Clean Landing | Common | 108 | A thin ring (radius 0.86, width 0.2) with a two-bar tick inside it in the hot row, the long arm reaching the rim. | 2 of 3 parts | Faces the camera; the tick pops (scale 1.3, 6 frames) on each L-cancel that counts. | `glyphs/clean_landing.svg`: A ring with a tick in it: the landing was clean. |
| `perfect_form` | Perfect Form | Rare | 140 | A ring (radius 0.84), a 10-sided disc inside it (radius 0.42) and a small ball at the centre. | 1 of 3 parts | A band lights for each L-cancel in the streak; all three pulse while the bonus is on. | `glyphs/perfect_form.svg`: A bullseye of three bands: three clean landings in a row. The family's base form. |
| `slipstream` | Slipstream | Common | 80 | Two ring arcs of 140 degrees (radius 0.7), each ending in a triangle arrow head. | 0 of 4 parts | Turns half a turn on each tag and stops. | `glyphs/slipstream.svg`: Two arrows chasing each other round a circle: the swap. |
| `slick` | Slick | Common | 108 | A ring (radius 0.86) tilted back 62 degrees so it reads as a flat oval, and two bars under it. | 0 of 3 parts | Slides 0.2 sideways and back with each wavedash; the bars fade over the one-second window. | `glyphs/slick.svg`: A ring lying flat with skid marks under it: the slide along the floor. |
| `jet_trail` | Jet Trail | Rare | 118 | A ring (radius 0.34) at the right and two ring arcs (radius 0.8 and 1.3, 80 and 56 degrees) behind it. | 0 of 3 parts | The wakes travel outward and fade (a 0.6 s loop) while Haste is on. | `glyphs/jet_trail.svg`: A small ring with two wakes spreading behind it. |
| `quicksilver` | Quicksilver | Epic | 140 | A ring (radius 0.7), a small block on top as the crown, one raised bar as the hand, a ball at the pivot. | 1 of 5 parts | The hand sweeps a turn every 2 s, every 1 s in Haste. | `glyphs/quicksilver.svg`: A stopwatch: the clock itself runs fast. |

### Guard (BLUE), rows `guard` and `guard_hot`

| id | name | tier | triangles | form | emissive parts | orbit animation | glyph |
|---|---|---|---|---|---|---|---|
| `riposte` | Riposte | Common | 44 | The family plate (flat top, point down) at 0.8 size in front of a long diagonal bar with a triangle tip. | 1 of 3 parts | Rocks 12 degrees; the blade jabs 0.2 along its length on a tech. | `glyphs/riposte.svg`: A plate with a blade crossed behind it: the answer to a hit. |
| `insulate` | Insulate | Rare | 108 | The family plate as a hollow frame (seven quads) with a smaller solid plate inside it (hot row). | 1 of 8 parts | The outer shell lifts 0.1 off the inner while the allowance is unspent and drops when it is used up. | `glyphs/insulate.svg`: A plate inside a second shell: two walls. |
| `bulwark` | Bulwark | Common | 48 | A half disc (radius 0.86, flat side down) on a flat slab 1.9 wide. | 0 of 2 parts | The dome swells 8% on the 15-second clock; it flattens for 10 frames when the orb is spent. | `glyphs/bulwark.svg`: A dome on a slab: the cover that takes one hit. |
| `thorns` | Thorns | Common | 56 | The family plate at 0.7 size with two triangle barbs on each side (hot row). | 4 of 5 parts | Rocks 12 degrees; the barbs stab out 0.15 when the wearer is hit. | `glyphs/thorns.svg`: A plate with barbs on both sides: it hurts to hit. |
| `leech` | Leech | Common | 36 | Two thick bars (0.56 by 1.9) crossed as a plus, with a small square boss raised at the crossing. | 1 of 3 parts | Faces the camera; the plus pulses once on each heal. | `glyphs/leech.svg`: A heavy plus: it gives health back. |
| `breaker` | Breaker | Rare | 32 | A triangle prism pointing down (1.0 wide, flat top) over two slab halves tilted into a shallow V. | 1 of 3 parts | The wedge taps down 0.1 each time shield damage counts; the halves fly apart on a break. | `glyphs/breaker.svg`: A wedge driven into a slab that has split: it breaks cover. |
| `last_stand` | Last Stand | Rare | 72 | An upright block (1.1 by 1.3) on a wider foot, three small blocks along its top, a slot raised on its face. | 1 of 6 parts | Still below 100%; from 100% it shakes 0.03 and the slot glows. | `glyphs/last_stand.svg`: A tower with a notched top: the place you hold. |
| `colossus` | Colossus | Epic | 36 | Three stacked slabs 0.7, 1.24 and 1.9 wide, 0.12 apart, the top one deepest. | 1 of 3 parts | The stack swells 15% while the wearer is Hot or hotter. | `glyphs/colossus.svg`: Three slabs, each wider than the one below: it grows. |

### Utility (WHITE), rows `util` and `util_hot`

| id | name | tier | triangles | form | emissive parts | orbit animation | glyph |
|---|---|---|---|---|---|---|---|
| `echo` | Echo | Rare | 36 | Three square prisms 0.86, 0.5 and 0.28 across in a row, depth equal to width. | 1 of 3 parts | The blocks pulse left to right (a 3-step loop) when the neighbour fires. | `glyphs/echo.svg`: Three blocks, each smaller, stepping to the right: the repeat, and which way it looks. |
| `metronome` | Metronome | Common | 36 | A tapered block (1.1 wide at the foot, 0.44 at the top) and a thin bar with a small weight leaning out of it. | 2 of 3 parts | The arm swings side to side once a second; it stops upright when the next move would not count. | `glyphs/metronome.svg`: A metronome with its arm swung over: change the beat. |
| `relay` | Relay | Rare | 168 | Two rings (radius 0.5, width 0.24) set diagonally and interlocked, one 0.12 in front of the other. | 1 of 2 parts | The links swing against each other 10 degrees; they pull tight on a tag. | `glyphs/relay.svg`: Two linked rings: the hand-off. The family's base form. |
| `surge` | Surge | Rare | 24 | Two parallelogram prisms (1.5 by 0.62, sheared 0.3), the upper pushed right and the lower pushed left, 0.2 apart. | 1 of 2 parts | The slabs slide 0.3 past each other and back on a stage shift. | `glyphs/surge.svg`: Two slabs sliding past each other: the stage shifts. |
| `crescendo` | Crescendo | Epic | 48 | Four upright bars 0.34 wide, 0.5, 0.95, 1.4 and 1.9 tall, on one base line, 0.14 apart; the tallest uses the hot row. | 1 of 4 parts | The pillars light left to right with the counter and all drop when the wearer is hit. | `glyphs/crescendo.svg`: Four pillars rising left to right: it builds while you are not hit. |
| `snowball` | Snowball | Rare | 40 | Two icosahedra, radius 0.27 and 0.66, on one floor line. | 1 of 2 parts | The big ball grows with its pips (radius 0.5 at none to 0.72 at twenty) and turns slowly. | `glyphs/snowball.svg`: A small ball and a big one: it grows as it rolls. |
| `magpie` | Magpie | Common | 88 | A squat eight-sided pouch body (1.7 wide), a wide flared neck above the tie (1.4 wide), a raised band at the tie and a raised disc on the body. | 2 of 4 parts | The pouch hops 0.1 on each cash-out. | `glyphs/magpie.svg`: A tied pouch with a coin mark: more coins. |
| `mirror` | Mirror | Epic | 44 | A solid triangle prism at the left and the same triangle as a hollow frame at the right, 0.4 apart. | 3 of 4 parts | In orbit it takes the left drive's mesh in the hot row; this form is for the floor, menus and an empty copy. | `glyphs/mirror.svg`: A diamond in two halves, the left solid and the right an empty outline: the copy of what is beside it. |

The exact coordinates of every part are in `DRIVES` in `build_step9.py`; copy the part list, not the prose.

## 6. The 16 Uniques

Rules and briefs: `scratch/envoy-notes/envoy-content-pass.md` section 9. Class treatment:

- **No family.** The body row runs from near black to a dark version of the Unique's own colour; the hot row is its second colour. None is a family colour, coral, lagoon or sunny.
- **Double edge.** Ink hull, then a white hull outside it (0.09 and 0.16). A family drive has the ink hull only. This is the cue that does not rely on colour.
- **Badge.** A diamond cut (a rounded square turned 45 degrees): the Unique's colour as the rim, a black face, the glyph in its light colour; one diamond pip where a drive has three level pips. Round is a drive, square is an active, a wedge is a keystone, a diamond is a Unique.
- **No tier ring, no levels, no halo, no star** (content pass 9.1).
- **Orbit.** Its own path, tilted 35 degrees to the row's ring and turning the other way, drawn at x1.2, with a short light trail (a shader sprite trail; without shaders, three fading copies).
- **Floor.** A black diamond plate with a white edge in place of the white disc, white floor rings in place of sunny, and a column of light 150 px tall.
- **Pick list.** Its own beat, as the content pass 9.5: the three tags clear, one dark tag slides in at x1.4 with the material running and the burst "A Unique"; input held 30 frames.
- **Shader.** Every signature material needs the mod draw layer the shader study recommends (per-object material with four parameters and a clock). Without it: the dark body, the double edge and one baked sheen band in the atlas row.

| id | name | triangles | form | colours (body, light) | signature material (shader) | what it must say | still on the sheet |
|---|---|---|---|---|---|---|---|
| `puppeteer` | Puppeteer | 120 | A tilted cross of two bars with three thin threads of different lengths hanging from it, a small ball on each. | #7A5433, #EDE3CB | Threads that glow in a pulse travelling to the left. | I pull that one. | `pulse` |
| `ashbank` | Ashbank | 196 | A lidded urn with two ear handles: a wide-shouldered body on a small foot, a flat lid and a knob; a slot raised on the belly. | #4A4854, #E0492C | An inner glow that rises with the banked Heat; ash drifts in. | How much is saved. | `glow` |
| `changing_of_the_guard` | Changing of the Guard | 64 | Two long poles crossed, each with an axe blade and a spike at its head. | #B99A46, #7A2329 | A brass sheen that flashes edge to edge when the tag is ready. | Tag now. | `sheen` |
| `turnabout` | Turnabout | 80 | An hourglass: two triangles tip to tip between two end plates, with a pivot ball on each side. | #8D96A2, #E8D9A9 | Sand that flows upward after each flip. | Which way the row reads. | `motes` |
| `mockingbird` | Mockingbird | 136 | A hollow bird: an eight-sided body with an open centre, a round head, a beak and a long tail. | #8B8B95, #D9D9E2 | A dissolve edge that eats the grey and shows the copied form. | Empty or loaded, and with what. | `dissolve` |
| `hundred_year_seed` | Hundred-Year Seed | 56 | A pointed seed lying at an angle with a short stem and two leaves; from loop 3 the stem lengthens a step each loop. | #6C4D2C, #86A552 | Growth rings lit from inside, one more band each loop. | How many loops it has grown. | `rings` |
| `lifeline_coin` | Lifeline Coin | 128 | A thick coin with a round hole, hung on a cord that rises to a knot. | #B38E3B, #2B2630 | Iridescent foil that goes dull when the purse is under the price. | You can afford one. | `foil` |
| `kiln` | Kiln | 80 | A brick furnace: a block on a slab with a chimney at one side and an arched mouth raised on its face. | #34313C, #FFF0CC | A heat-haze halo that bends the air around it, always sinking. | Heat is draining. | `haze` |
| `absolution` | Absolution | 136 | A shackle with a gap in its ring and a short broken link thrown off above it. | #707D8D, #F3F0F8 | A slow pearl sweep across the break while the price is off. | The price is lifted now. | `sheen` |
| `clockwork_heel` | Clockwork Heel | 184 | A spur: a half band open to the right, a short neck, a toothed wheel at the left, and a two-lobed key on top. | #566170, #DC9C8B | An animated gear pattern that ticks, and stops during the 3-second gate. | Ready or winding. | `pattern` |
| `hair_trigger` | Hair Trigger | 72 | A cocked hammer: a pivot disc, a leaning neck, a jaw block holding a wedge of flint, a thumb spur behind. | #405A7B, #F4F6FF | Sparks along the edge, denser when Heat can pay for more uses. | Uses in hand. | `sparks` |
| `shared_flame` | Shared Flame | 204 | Two rings one above the other, joined at the touch into a figure of eight, with a drop between them. | #AEB8C2, #F2F6FA | A liquid-metal flow from one ring to the other, toward whoever gained last. | Who is feeding the meter. | `flow` |
| `pied_piper` | Pied Piper | 92 | A long reed pipe set diagonally with a flared end, three holes raised on it and a pennant hanging from it. | #3B3780, #EDE3CB | A soft note-shaped trail behind each ally. | Which enemies are yours. | `trail` |
| `fools_gold` | Fool's Gold | 72 | A rough lopsided nugget of seven sides with a facet line, and one small chunk beside it. | #A39F58, #E6E2A4 | A glitter that scales with the purse and goes flat after a shop. | How rich, so how strong. | `glitter` |
| `albatross` | Albatross | 72 | One long wing: a bent spar from lower left to upper right with four feathers hanging off its trailing edge. | #7C8895, #F2F2EC | A wind-streak trail that appears only offstage. | You are in its element. | `streak` |
| `ouroboros` | Ouroboros | 122 | A ring that thins to a tail, with a wedge head closing on the tail and an eye raised on the head. | #6FA596, #1D2A28 | A scale pattern that runs once round the ring for each returned charge. | The loop closed. | `scales` |

Three briefs were bent to keep the class outside the family languages: **Shared Flame** was "two linked rings", which is Utility's family mark and Relay's form, so it is a figure of eight with a drop at the join. **Albatross** is one long bent wing, where Sky's forms are symmetric. **Ouroboros** is a ring, as Tempo's are, but it thins to a tail and has a head; it relies on the dark body and double edge.

## 7. Keystones and actives (2D only)

| id | name | emblem | file |
|---|---|---|---|
| `plague_bearer` | Plague Bearer | Three flames, one large. | `glyphs/keystone_plague_bearer.svg` |
| `glass_core` | Glass Core | A cut gem with a crack. | `glyphs/keystone_glass_core.svg` |
| `grand_finale` | Grand Finale | A sixteen-point burst. | `glyphs/keystone_grand_finale.svg` |
| `echo_oath` | Echo Oath | Two discs, one behind the other. | `glyphs/keystone_echo_oath.svg` |
| `overclock` | Overclock | A dial with its hand past the last mark. | `glyphs/keystone_overclock.svg` |
| `twin_soul` | Twin Soul | Two drops turning round each other. | `glyphs/keystone_twin_soul.svg` |
| `winter_oath` | Winter Oath | An ice crystal with a core. | `glyphs/keystone_winter_oath.svg` |
| `all_in` | All In | One notched token: the whole stake. | `glyphs/keystone_all_in.svg` |

Awakened: the wedge face turns sunny; the emblem disc gains a sunny outer ring and a white spark at its upper right; the 32 px HUD wedge does the same. Plague Bearer and Grand Finale use coral and Echo Oath uses lagoon in emblems drawn in earlier steps; those are the player colours, and worth a second look.

| id | name | pips | glyph | file |
|---|---|---|---|---|
| `volley` | Volley | 3 | Three darts in a line: the whole row, one after another. | `glyphs/active_volley.svg` |
| `overdrive` | Overdrive | 3 | A gauge with its needle past the top. | `glyphs/active_overdrive.svg` |
| `detonate` | Detonate | 2 | A burst with a core: the words go off. | `glyphs/active_detonate.svg` |
| `recall` | Recall | 2 | An arrow that turns back. | `glyphs/active_recall.svg` |
| `double_down` | Double Down | 4 | Two chevrons down: the stake, doubled. | `glyphs/active_double_down.svg` |

Actives are the drive badge cut square (`pog(..., sq=True)`) in cobalt #3E6BFF, which no family uses.

## 8. Too alike, and what was done

Measured: overlap of the 24 px black silhouettes (shared pixels over all pixels), every pair of the 62 models.

| closest pairs across families | overlap |
|---|---|
| Cinder Heart and Feather Storm | 74% |
| Last Stand and Magpie | 73% |
| Cinder Heart and Leech | 73% |
| Cinder Heart and Affliction | 72% |
| Affliction and Leech | 71% |
| Cinder Heart and Ashbank | 70% |
| Cinder Heart and Static | 70% |
| Ember and Static | 69% |
| Cinder Heart and Fool's Gold | 68% |
| Cinder Heart and Bulwark | 67% |

| closest pairs inside one family | overlap |
|---|---|
| Ember and Cinder Heart | 79% |
| Clean Landing and Perfect Form | 74% |

The overlap number is crude (two filled shapes of the same size always score high), so it was used to find pairs to look at, not to pass them. What it found and what was changed:

| pair | what was wrong | what was done |
|---|---|---|
| Hex, Clean Landing, Leech, Surge (82 to 89% with each other) | all four were a filled plate with a mark raised on it; in black they were the same blob | Hex is now cut through by its cross into four wedges; Clean Landing is a thin ring with the tick inside; Leech is the plus itself; Surge is two slabs sliding past each other |
| Wildfire and Feather Storm (78%) | both were three prongs fanned from one root | Wildfire is one tall flame with a small flame standing apart at each side of its foot |
| Leech and Mirror (83%) | a fat plus fills a diamond | the plus arms went from 0.66 to 0.56 wide; Mirror's halves moved 0.4 apart and its hollow half got a thinner frame. Now under 70% |
| Cinder Heart and Ashbank (79%) | a heart-shaped coal and an urn are both wide-shouldered with a knob on top | the urn got two ear handles; it is also dark with the double edge. Now 70% |
| Ember and Magpie (76%) | a pouch drawn narrow is a teardrop | the pouch is squatter (1.7 wide) with a wide flared neck |
| Comet and Meteor | both began as a ball with a tail | Comet is a ball thrown up off a wide arc; Meteor is a dart diving point down |
| Rush, Tailwind, Clean Landing | three discs with an ink mark each | Rush is a ring with three speed lines; Tailwind is an arrow through a hoop; Clean Landing is the ring with a tick |
| Tailwind and the Sky family mark | a curl of wind is Sky's own family glyph, and Tailwind is a Tempo drive | no curl: the hoop and arrow |
| Colossus and Affliction | both were three stacked bars | Affliction is four cells of honeycomb; Colossus keeps the stack, widening upward |
| Echo and Mirror | both were diamonds | Echo is three blocks stepping down to the right |
| Slick, Bulwark, Gatekeeper | three arches | Slick is a ring lying flat; Bulwark is a solid dome on a slab; Gatekeeper keeps the open arch |
| Hex and Tempo's rings | a hexagon ring with a centre dot is a bullseye | Hex has no hole |
| Shared Flame and Relay | the Unique was briefed as two linked rings, which is Utility's family mark and Relay's form | Shared Flame is a figure of eight, upright, with a drop at the join |
| The Rare ring and every outline | a ring round the waist cut the family outline at 24 px | the tier ring lies under the form |
| The ascended halo and Tempo | a large halo behind the form made every ascended drive round | the halo is a small ring with the star, over the form |

Still close and left: **Ember and Cinder Heart** (79%, same family: the heart is wider and has a cleft), **Clean Landing and Perfect Form** (74%, same family: a tick against a centre disc), **Cinder Heart** against several filled shapes (it is the roundest Fire form).

## 9. Least sure to read

1. **Jet Trail**: a small ring and two thin wakes; at 22 px the wakes are one pixel of white. May need to lose the outer wake.
2. **Nova**: the flame between two arcs; the arcs can read as a Tempo ring at orbit size.
3. **Slick**: a flat oval; it is the only tilted ring and can read as a Guard slab in black.
4. **Static**: the zigzag belt is an ink mark and is gone at 22 px; the two barbs carry it alone.
5. **Contagion**: the three buds are 4 px each at chip size.
6. **Clockwork Heel** (Unique): three small pieces; the key is too small for the chip.
7. **Puppeteer** (Unique): the threads are one pixel at chip size.
8. **Thunderhead and Bolt**: both carry a zigzag; the cloud is what separates them, and it does.
9. **Riposte and Thorns**: the same plate with different things sticking out.
