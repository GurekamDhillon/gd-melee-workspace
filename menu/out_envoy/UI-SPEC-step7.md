# Envoy UI, step 7 addendum: loops, sessions, the bank, the fighter picker, wave fights

Read with `UI-SPEC.md`. Everything there still holds (rules, parts, motion, buttons) unless a line
here replaces it. Where the two disagree, this file wins.

- Picture of everything: `preview/step7-sessions.png`.
- Reference per screen: `screens/<name>.png` (640x480) and `screens/<name>@2x.png`.
- Source: `build_step7.py` (imports `build_final.py`; run it to regenerate).

Positions are game pixels in a 640x480 frame, origin top left, `(x, y)` or `(x, y, w x h)`. A
sticker's position is its unrotated top-left corner. 60 frames a second.

Contents: 0 what replaces what, 1 words, 2 new parts, 3 the screens (A to F), 4 motion, 5 strings,
6 what the engine must provide, 7 decisions made here, 8 open questions, 9 drifts seen in the built game.

---

## 0. What replaces what

| in UI-SPEC.md | now |
|---|---|
| Acts 1 to 3, the 15-mark run strip (3.10) | Loops without end. The **loop strip** (2.1 here): one loop, 5 fights and 2 stops |
| Flow: fight, pick of three, map, fight | Flow: road, fight, banner, fight, banner, fight, **stop** (rewards one by one, keystone if due, shop), road, ... |
| Map poster shows one fight (2.4) | Road poster lists the next **session** (C4 here) |
| Camp row "Run length" (2.2) | Gone. The **Fighters** row opens the picker (D here) |
| "Run cleared!" results (2.8) | A run only ends by losing or abandoning. One results layout (E5 here) |
| Level is 1 to 3: three pips or three stars | No top. Past 3: three full pips or stars and a "+N" flag (2.4 here) |
| Stock pool 4 or 5 | 4 or 5 at loop 1, +1 per loop cleared, 8 at most (2.5 here) |
| Rule 1.7: Start at the camp starts the run | Unchanged, and the picker has no Start action |
| Pick of three after every fight | Each win **banks** a reward; all are opened at the stop |

Unchanged and not redrawn: keystone wedges, the pick-of-three layout, the rest stop (it is the shop
step of the stop), pause, Second Wind, the Heat bar, the tag and chip kit.

## 1. Words

One word each, used the same way everywhere.

| word | meaning |
|---|---|
| loop | 5 fights: fights 1 to 3, a stop, fight 4 (the elite), fight 5 (the boss), a stop. "Loop 3" |
| session | fights played back to back with no menu between. Never printed as a word on a list row; the screens say "Fights 1 to 3" and "Elite, boss". The banner alone says "This session" |
| stop | the one pause after a session: rewards, a keystone if due, the shop |
| reward | one thing in the bank: a pick of three, a banked drive, or a keystone that is due |
| banked | won but not opened yet. "Banked for the stop", "Frost is banked" |
| drop | a drive left on the floor by a KO |
| main, partner | a player's two fighters. The main starts each fight |
| best | the highest loop reached in any run: "Best: loop 4" |

The fight label is **"Loop 3, fight 2 of 5"** (a comma, sentence case), not "Loop 3 - Fight 2 of 5".

## 2. New parts

### 2.1 The loop strip

Replaces the run strip. One sunny sticker, 46 high, 3 px ink edge, shadow (3, 4).

Wide (608 wide; road, results), x offsets from the sticker's left inner edge:

| item | x | y |
|---|---|---|
| "Loop N", Bricolage 800, 22 | 13 | 9 |
| label "Fights 1 to 3", 11 lilac | 120 | 3 |
| marks for fights 1, 2, 3: circles r 7 | 134, 184, 234 | centre 31 |
| stop: tent, r 6 | 290 | 31 |
| label "Elite, boss", 11 lilac | 330 | 3 |
| fight 4: diamond, half-diagonal 8.5 | 346 | 31 |
| fight 5: star, r 7 scale | 396 | 31 |
| stop: tent | 452 | 31 |
| "then loop N+1", 11 ink | 486 | 23 |

Small (312 wide; camp): "Loop N" at 15 px at (8, 13); labels at x 64 and 162; marks at 74, 98, 122,
tent 148, 174, 199, tent 225; r 5.5; centre y 30; no "then".

Mark states are the run strip's: done = ink fill, next = coral fill with an ink ring r+4.4, to do =
white fill, lost = white with a ring and a coral cross. The first tent is ink once fight 4 is next.
The second tent is never filled: when it is passed the strip is redrawn for the next loop.

On the road a coral pointer (26 x 14) sits under the next mark at y 50. Variants: a white face with
the label "A loop", all marks to do, tab "Every loop" (camp with no saved run); a coral stamp
"Loop N cleared" at the right end, 14.5 px, tilted -5 degrees, in place of "then loop N+1".

### 2.2 Bank tokens

18 px each, 3 px apart, drawn in a 25-unit box.

| token | drawing |
|---|---|
| a reward to open | white disc r 8.2, 2.2 ink edge, an ink question mark drawn as a path |
| a banked drive | the drive's own badge at 18 px, no rarity edge |
| a keystone that is due | the ink wedge with a white die-cut and a small sunny star |
| done (at the stop) | ink disc with a white tick; any kind |
| the one being opened | the token on a sunny disc r 11.4 with a 1.6 ink edge |

Order in the bank: rewards in the order won, banked drives where they were picked up, the keystone last.

### 2.3 The bank counter (fight HUD) and the stop sticker (menus)

- **Bank counter**: the coin counter's pill (19 high, white, 2 px ink edge, Bricolage 800, 13) with
  a 17 px reward token and the number of things banked. It sits 6 px right of the coin counter.
  Hidden while the bank is empty.
- **Stop sticker**: white, 28 high, 3 px ink edge, radius 10, shadow (3, 4), tilted 0.6 degrees,
  right edge at x 624, top y 441. Inside, left to right: the bank as tokens, then a label in
  Bricolage 800, 13, then what follows in Source Sans 3 700, 12, lilac. It is the only progress
  marker of the stop. It is not on the shop: the shop's hint line needs the room and the shop is last.

### 2.4 Levels past 3

- **Chip (22 px badge on a fighter sticker)**: all three pips ink, and an ink flag "+N" (N = level
  minus 3) over the badge's top right: ink face, 1.5 px white edge, radius 7, Bricolage 800, 11,
  white, right edge 3 px outside the chip box, top 3 px above it. While a level-up is previewed on
  that chip the flag drops to y +9 so the coral arrow keeps the corner.
- **HUD chip (30 px)**: the same flag, top 4 px above the chip box.
- **Tag (the 58 px badge)**: three stars, then "+N" in Bricolage 800, 11, inside the star ribbon.
- **Words**: "Bolt, level 4". The pick-of-three tag for a duplicate past level 3 needs a line the
  mechanics do not give yet (see 8).

### 2.5 Stock dots at 5 to 8

| where | 4 to 6 | 7 and 8 |
|---|---|---|
| fight HUD, bottom centre, centred on x 314 | 14 px, pitch 18 | 12 px, pitch 15, 2 px edge, y +1 |
| on a white sticker, in the ink capsule | 12 px, pitch 15 | the same; the sticker grows: 128 wide to six dots, 136 for seven, 151 for eight |

Eight HUD dots are 117 wide, which clears the two five-slot corners. The label reads "5 of 7".

### 2.6 The best sticker

White, 30 high, auto width, a 17 px sunny star, "Best: loop N" in Bricolage 800, 14. A new best is
the same sticker with a sunny face and a white star: "New best: loop N". No burst.

---

## 3. The screens

### A. The banner (`banner.png`, `banner-boss.png`)

Shown over the load between two fights of a session. It takes no input and has no strip and no hints.

| part | position | notes |
|---|---|---|
| ground | whole frame | flat #2C1E70; the fight number as one giant numeral, Bricolage 800, 470 px, #33257C, centred on x 320, baseline y 412; a hill band #251861 from y 420 |
| the sticker | (118, 146, 404 x 100), sunny, tilted -1.5 | |
| tab "Loop 3" | sticker (-7, -9) | ink face, white text, 14 px, tilted -7 |
| kind picture | sticker (14, 20), 58 px | duel, pack, elite or boss |
| "Fight 2 of 5" | sticker (84, 13) | Bricolage 800, 36 |
| "Pack on Stage 4" | sticker (86, 56) | kind in Bricolage 800, 17; the rest Source Sans 3 700, 13.5 |
| "This session" | right 14, top 50 | 11 px, ink |
| the session's marks | right 12, top 64 | r 8, 30 apart: three circles, or diamond and star. Done, next, to do |
| the three quiet groups | row at y 286, centred, 38 apart | each: an 11 px pale lilac label, then a 22 high line 7 px under it |
| group 1 | | "Team stocks" (or "Solo stocks"; "Last stock" when one is left) and the HUD stock dots |
| group 2 | | "Coins" and the coin counter |
| group 3 | | "Banked for the stop", the bank tokens, and "N rewards" in white 12.5. With an empty bank: "Nothing yet" |

Timing: it is up from the first black frame of the load and stays at least 120 frames; if the load is
longer it stays until the fight is ready. Start, A and B do nothing.

### B. The drop (`drop.png`, `drop-worn.png`, `drop-level-up.png`, `drop-banked.png`)

**In the world.** The drive's badge at 24 px on a white disc (r 15, 2.4 ink edge), its centre 27 px
above the floor; under it on the floor a sunny ellipse ring (21 x 6.5, 3 px sunny over 6.5 px ink)
and a fainter one (33 x 10, 2 px, 45%); over it the drive's name on a white name tag (Source Sans 3
700, 11) 20 px above the disc. It is a white sticker, so it reads as ours.

**Picking up.** The fighter in play takes it by touching it. No button. Either player's fighter can.
The drop stays until the fight ends; a drop still on the floor then is banked.

**The pickup line.** A white sticker, 24 high, 2.5 px ink edge, shadow (2, 3), tilted -1.5 degrees,
with the drive's badge at 17 px and one line in Bricolage 800, 12.5. Its top is at y 360 for P1 and
P2 alike (22 px above the drive row), and a 12 x 9 notch under it points at the chip it is about.
It stays 90 frames.

| case | row | line | also |
|---|---|---|---|
| a free slot | the badge appears in the next free slot, charge 0, with a sunny ring r 16 for 90 frames | "Frost on, slot 5" | |
| a duplicate | the chip's level goes up; ring on that chip | "Bolt, level 4" | the "Level up!" burst (50 px) at the line's right end |
| the row is full | nothing changes | "Row full. Frost is banked." | the bank counter pops and counts one more |

**The top left of the fight HUD** (all fights): keystone wedges from x 14 at y 14 (34 apart), the
coin counter 4 px after them, the bank counter 6 px after that; under them at (14, 47) the fight
label "Loop 3, fight 2 of 5" on a white name tag (Source Sans 3 700, 11, 2 px ink edge).

### C. The stop

Order: every banked reward, one screen each, in bank order; then the keystone pick if one is due;
then the shop; then the road. Nothing can be skipped except with each screen's own Skip.

**C1. A reward (`stop-pick.png`, `stop-pick-solo.png`).** The pick of three exactly as in UI-SPEC 2.6
(both players choose at once, each with their own cursor, strip and Skip). Added: the stop sticker
with the label "Reward 1 of 3" and "then a keystone, then the shop" (or "then the shop").

**C2. A banked drive.** Not drawn. It is the same screen with one tag instead of three and the title
"A banked drive": the player whose fighter touched it chooses who wears it (the full-row step of 2.6
if needed) or Skip. The other player's half shows only their two fighters and "Waiting for P1.".

**C3. The keystone (`stop-keystone.png`).** UI-SPEC 2.3 as it is, with the stop sticker: label "The
keystone", then "then the shop". No B.

**C4. The shop.** The rest stop, UI-SPEC 2.7, unchanged. Its last row, "Back on the road", opens the road.

**C5. The road (`road-session.png`, `road-loop-clear.png`).** The map screen, UI-SPEC 2.4, with:

| part | position | notes |
|---|---|---|
| loop strip, wide | (16, 8) | pointer under the next fight |
| session poster | (20, 70, 300 x 290), tilted -1 | sunny head 56 high: headline Bricolage 800, 24 at (10, 5); an 11 px ink line at (11, 35) |
| a fight line | from poster (10, 59), each 47 high, dashed rule between | kind picture 34 px at x 0; "Fight 4" 11 px lilac at (42, 6); kind in Bricolage 800, 17 at (42, 18); name Bricolage 800, 13.5 at (108, 7); place 12.5 lilac under it; an elite's drives as 20 px badges at the right |
| under the lines | dashed rule, then | "If you win" 11 px; one sentence 13 px; one lilac sentence 12.5 |
| the party | (340, 72), 2 x 2, 146 x 90 pitch | fighter stickers, five slots |
| stocks | (342, 254) | width by 2.5 |
| coins | 12 px right of the stocks sticker, y 256, 104 wide | label "Coins" |
| keystone pills | (344, 316) and (486, 316) | |

Headlines: "Next: three fights" / "Loop 3, fights 1 to 3, back to back", and "Next: elite, then
boss" / "Loop 3, fights 4 and 5, back to back".

The loop-clear version is the same screen when fight 1 of a new loop is next: headline "Loop 3
begins"; the stamp "Loop 2 cleared" on the strip; flat sunny rays (12%) behind the poster from
(170, 214); a "+1" burst (44 px) on the stock sticker's right edge with the coins moved 22 px right;
and, only on a new best, the sunny best sticker at (470, 348).

Buttons on the road: A starts the session ("Start fight 4", "Start loop 3"), Y reads the drives,
Start pauses. Quit to camp is in the pause, as before.

### D. The camp and the picker

**D1. Camp (`camp-loops.png`, `camp-loops-saved.png`).** UI-SPEC 2.2 with these rows, top to bottom:

| no saved run | a saved run |
|---|---|
| Start run / "A new run, from loop 1." | Continue run / "Loop 3, fight 4 of 5. 5 of 7 stocks left." |
| | New run |
| Fighters, value "2 each" ("2" solo) | Fighters, faded to 50%, a lock and "set for this run" |
| Team attack | Team attack |
| NG+ level | NG+ level |
| Collection | Collection |
| Back | Back |

Row y: 58 (the big row, 54 high), then every 36 from 120. "Run length" is gone.

Right side: the four fighter cards as before (the last party used, or the saved party); the small
loop strip at (290, 182); the stock sticker at (294, 244); the best sticker to its right (y 252 with
no saved run; y 310 under the keystone pills with one); the "Set for this run" tag at (296, 304)
with a saved run only. Before any run has ended there is no best sticker.

A on Fighters opens the picker. With a saved run the row cannot be opened; the strip says "The party
is set for this run. Start a new run to change it."

**D2. The picker (`fighters.png`, `fighters-solo.png`).**

| part | position | notes |
|---|---|---|
| title "Choose fighters" | (16, 2), 24 px | |
| one line | (232, 15), white 12 | "Each player brings two: a main and a partner." ("Bring two: a main and a partner." solo) |
| the grid | 9 columns, first cell at (26, 40), pitch 66 x 81 | a cell is a small fighter card, 60 x 75: head picture 36 wide, name Bricolage 800, 11. Idle cells tilt by under one degree |
| last cell | | "Random": a lilac question mark, 34 px |
| a tray per player | P1 (20, 290, 294 x 92); P2 (326, 290, 294 x 92) | white sticker with the player's tab |
| seats in a tray | x 8 and x 112, y 7, 100 x 70 | an 11 px label ("Main", "Partner"), a 21 px head and the name in Bricolage 800, 12.5 |
| Done | tray x 217, y 24, 64 x 34 | a dialog button; 36% until both seats are filled |
| strips | (24, 403) and (330, 403) | one per player; solo has the one full strip |

With more than 27 cells the grid keeps 9 columns and scrolls by rows; names over 9 letters use a
short form.

States of a cell: idle (white); hovered (sunny, white ring, upright, the player's sticker cursor at
its lower right); picked (the player's tab on its top edge reading "Main" or "Partner": P1's at the
left corner, P2's at the right, so both fit on one cell); locked (faded #DAD7E8 face, grey head, a
lock, the name replaced by "Locked"; hovering it keeps the faded face and adds the white ring).

Steps, the same for each player, each with their own cursor at the same time:

1. **Main.** The cursor starts on the main they had. The "Main" seat is sunny and reads "Main,
   choosing"; it shows the hovered fighter. A picks; B leaves the picker and keeps the old party.
2. **Partner.** The cursor starts on the partner they had. The seat reads "Partner, choosing". The
   player's own main cannot be picked again (A does nothing; the strip says why). B goes back to step 1.
3. **Done.** The cursor jumps to the tray's Done, which turns sunny. A confirms: Done becomes a
   coral "Ready" stamp. B goes back to step 2.

So A, A, A keeps the last party. When every joined player is Ready the picker closes after 20
frames and the camp shows the new cards. Two players may pick the same fighter. Random fills the
seat with "Random" and is rolled when the run starts. Player 2 cannot join from here (camp only).

### E. Loops and levels

**E1. Fight HUD (`hud-loop.png`).** The fight label, bank counter, "+N" flags and small dots, as in
2.3 to 2.5 and B. Nothing else moves. In a boss fight the boss bar keeps its place; the label stays
under the keystones.

**E2. Main menu (`menu-loop.png`).** The saved-run stickers of UI-SPEC 2.1 with: sub line "Loop 3,
fight 4 of 5. Saved at the stop."; five chip slots a row; the punch card replaced by a **loop card**
at the same place and size (97 x 136, sunny, tilted 3 degrees): "Loop 3" in Bricolage 800, 20 at
(9, 5); marks r 6.5 in two lines (three circles at y 47; diamond and star at y 75, 26 apart); "Fight
4 of 5" at (9, 98) and "Best: loop 4" at (9, 112), 11 px ink. The stock sticker grows by 2.5 and the
keystone pills start 14 px right of it. Bottom bar: "Continue your run from loop 3, fight 4."

**E3. Results (`results-loop.png`).** One layout. Title "The run ended" (30 px); under it "Reached
loop 4, fight 3: the duel on Stage 9 took the last stock."; the best sticker at (364, 6), sunny when
it is a new best; time at (534, 6); the wide loop strip at (16, 62) for the loop the run ended in,
with the lost mark and no "then"; the party at (18, 122); keystone pills from (18, 212); four
numbers at y 216: Loops cleared (166, 100 wide), Drives fired (276, 100), Coins earned (386, 140),
Stocks lost (536, 86); "Unlocked" and its stickers as before. Strip: "Loop 4 is your new best. It
was loop 3." or "Your best is still loop 4.". A: Back to camp.

### F. Wave fights (`waves.png`), provisional

The foe plates are replaced by one ink plate in the same corner: right edge x 624, top 14, 38 high,
white edge, as a foe plate. Inside: a 17 px small-foe head; "Wave 2 of 3" (11 px, pale lilac) with
one 8 px pip per wave after it (done pale lilac, current sunny with an ink and white ring, to come
hollow); under it "5 left" in Bricolage 800, 21, white. With one wave the label is "Pack" and there
are no pips. Foes carry no plates and no percent.

---

## 4. Motion

Added to UI-SPEC section 4. Same rules: ease out, small, nothing loops unless noted.

| moment | motion | frames |
|---|---|---|
| banner in | ground cuts in; the sticker enters as a sticker (0.85 to 1.04 to 1.0); the three groups fade in together | 9, then 6 |
| banner, the session marks | the mark of the fight just won fills ink, then the ring moves to the next | 6 + 6, starting at frame 20 |
| banner, bank | a token banked by the last fight pops 1.3 to 1.0 | 6, at frame 30 |
| banner out | everything fades | 6 |
| a drop appears | the disc pops out of the KO flare, rises 16 px and settles 10 px over the floor | 12 |
| a drop waits | the outer floor ring grows from the inner ring's size and fades (loop); the disc bobs 2 px | 60 a cycle |
| pickup | the disc flies to the slot (or to the bank counter) on a straight line, shrinking to chip size | 10 |
| pickup line | enters as a sticker, holds, fades | 9, 90, 6 |
| bank counter counts up | scale 1.0 to 1.2 to 1.0, sunny burst behind it | 6 |
| "+N" changes | the flag pops 1.6 to 1.0 in coral, then turns ink | 8, then 30 hold |
| stop sticker | the opened token turns to its tick; the sunny disc slides to the next token | 6 + 4 |
| stock pool gains a dot | the "+1" burst pops; the new dot grows from the ink point | 7, then 8 |
| loop-clear road | the stamp lands: scale 1.4 to 1.0 with its tilt; rays fade in | 6, then 12 |
| picker, a pick | the cell presses (1.0 to 0.94 to 1.0); the tab pops onto it; the seat's head swaps | 6 |
| picker, Ready | the stamp lands as above | 6 |
| wave cleared | the current pip fills; "N left" counts back up from 0 over the new wave's size | 12 |

## 5. Strings

Fight and banner: `Loop {n}, fight {f} of 5` · `Fight {f} of 5` · `Loop {n}` · `This session` ·
`Team stocks` · `Solo stocks` · `Last stock` · `Coins` · `Banked for the stop` · `{n} reward` /
`{n} rewards` · `Nothing yet` · `{Kind} {place}` with kinds `Duel`, `Pack`, `Elite`, `Boss`.

Drop: `{Drive} on, slot {s}` · `{Drive}, level {l}` · `Row full. {Drive} is banked.` · `Level up!`

Stop: `Reward {i} of {n}` · `The keystone` · `A banked drive` · `then a keystone, then the shop` ·
`then the shop` · `Waiting for P{p}.`

Road: `Next: three fights` · `Next: elite, then boss` · `Loop {n} begins` · `Loop {n}, fights 1 to
3, back to back` · `Loop {n}, fights 4 and 5, back to back` · `Fights 1 to 3, back to back` ·
`Fight {f}` · `Five small foes` · `If you win` · `Each win banks a reward for the stop.` · `The
elite banks one of its drives and a reward. The boss banks a keystone.` · `After this: a stop, then
the elite and the boss.` · `After this: a stop, then loop {n+1}. The pool gains a stock.` · `Loop
{n} cleared` · strip `An elite, then the boss, with no stop between them.` · `Three fights, with no
stop between them.` · `Loop {n} is cleared. Foes hit harder in loop {n+1}, and the pool gains a
stock.` · hints `Start fight {f}` · `Start loop {n}` · `Read your drives` · `Pause`.

Loop strip: `Loop {n}` · `A loop` · `Fights 1 to 3` · `Elite, boss` · `then loop {n+1}` · tabs
`Saved run`, `Every loop`.

Camp: `Start run` / `A new run, from loop 1.` · `Continue run` / `Loop {n}, fight {f} of 5. {a} of
{b} stocks left.` · `Fighters` / `2 each` / `2` / `set for this run` · `Best: loop {n}` · `New
best: loop {n}` · strips `Choose who you bring. Each player picks a main and a partner.` · `Pick up
at loop {n}, fight {f} with the saved party.` · `The party is set for this run. Start a new run to
change it.` · hint `Choose fighters`.

Picker: `Choose fighters` · `Each player brings two: a main and a partner.` · `Bring two: a main
and a partner.` · `Main` · `Partner` · `Main, choosing` · `Partner, choosing` · `Not picked` ·
`Done` · `Ready` · `Random` · `Locked` · strips `{Fighter} as your main.` · `{Fighter} as your
partner.` · `{Fighter} is already your main.` · `Locked. {How it opens}.` · `Both picked. A: Done.`
· `Ready. Waiting for P{p}.` · hints `Stick` Choose · `A` Pick (no A on a locked or taken cell; `A`
Done on Done) · `B` Back.

Menu and results: `Loop {n}, fight {f} of 5. Saved at the stop.` · `Continue your run from loop
{n}, fight {f}.` · `Fight {f} of 5` · `The run ended` · `Reached loop {n}, fight {f}: the {kind}
{place} took the last stock.` · `Loops cleared` · `Loop {n} is your new best. It was loop {m}.` ·
`Your best is still loop {n}.`

Waves: `Wave {w} of {n}` · `{k} left` · `Pack`.

## 6. What the engine must provide

- The loop number, the fight number 1 to 5, the session (first or second) and the fight's kind and stage name.
- The bank as an ordered list: reward, banked drive (which, and whose fighter touched it), keystone due.
- A drop's drive, its floor position, and on pickup: which fighter, and worn / level-up / banked.
- A drive's level as an integer with no top.
- The stock pool's size (4 to 8) and what is left.
- The best loop of any finished run, and whether this run passed it.
- The party last used, per player: main and partner. The roster with a locked flag and a one-line
  reason for each locked fighter.
- For a wave fight: the wave, the number of waves, foes left in the wave.
- The banner needs the next fight's kind, number and stage before the load starts.

## 7. Decisions made here (delegated; the owner may overturn any)

| # | decision |
|---|---|
| 29 | The fight label is "Loop 3, fight 2 of 5", with a comma, on a white name tag so it reads on bright stages |
| 30 | The things in the bank are called **rewards**. The marker reads "Reward 1 of 3", not "Pick 1 of 3", because "pick 1 of 3" also describes choosing one drive of the three on that same screen |
| 31 | The stop's only progress marker is one sticker at the bottom right; it is not on the shop |
| 32 | A loop is drawn as fights 1 to 3, a tent, the elite's diamond, the boss's star, a tent. The elite gets its own mark (a diamond) |
| 33 | The banner takes no input and cannot be skipped; 120 frames at least |
| 34 | A drop is taken by touch, by either player's fighter in play; one left on the floor at the end of the fight is banked, not lost |
| 35 | A banked drive is opened at the stop by the player whose fighter touched it |
| 36 | "Run length" leaves the camp; a run has no length |
| 37 | The Fighters row is locked while a run is saved; changing the party means a new run |
| 38 | The picker is one grid with a cursor per player at once (the second screen, after the pick of three, where P2 has their own). Three presses: main, partner, Done. The cursor starts on what the player had |
| 39 | Two players may pick the same fighter; one player may not pick the same fighter twice. A Random cell closes the grid |
| 40 | Past level 3 the flag sits on the badge's top right, like a count badge, so it never pushes the row wider |
| 41 | Seven and eight stock dots are drawn at 12 px in the fight HUD rather than on two lines |
| 42 | A new best is a sunny sticker, not a burst; the loop-clear road has one stamp and one "+1" burst and nothing else new |
| 43 | Clearing the boss reads "Loop 2 cleared" and "Loop 3 begins", not "Run cleared!", because the run goes on |
| 44 | Results have one layout; "Loops cleared" replaces "Longest chain" among the four numbers |
| 45 | A run is saved at a stop only, so the menu says "Saved at the stop" |

## 8. Open questions

- **Tag text past level 3.** The tag's "Level N adds: ..." line has two entries per drive. Past 3
  it needs either a general line ("Level 4 adds: 10% more.") or more data.
- **Keystones in an endless run.** The seats, the HUD wedges and the results stack hold three. If a
  keystone is due after every boss, a fourth has nowhere to go: cap at three, or replace one.
- **Slots past loop 2.** The row is drawn at five slots from loop 3 on.
- **What foes gain per loop.** The loop-clear strip says "Foes hit harder"; the true rule should
  replace it in one short clause.
- **NG+** is still on the camp and the menu. With endless loops it may be the same idea twice.
- **Solo banked drives and the timer.** The pick's 20 second timer is kept; whether it runs for
  each reward of a long stop is a rules question.
- **Wave fights**: whether small foes show any damage, and whether a wave fight can leave drops.

## 9. Drifts seen in the built game (not redesigned here)

From the screenshots in `scratch/envoy-demo/screenshots/v3/`, against `UI-SPEC.md`.

1. **Fight label**: plain white text with no plate under the keystones ("Fight 2 of 5"); it is lost
   on bright stages. Use the white name tag (B, top left).
2. **Fight HUD, name tags**: fighter names are in capitals ("DR. MARIO", "MARTH") in the corner, the
   bench sticker, the pick, the shop and the menu. The spec is sentence case, Bricolage 800.
3. **Fight HUD, bench sticker**: it carries the name and no percent; the spec has head, percent and
   the tag button, and no name.
4. **Fight HUD, level pips**: drawn as yellow dashes under the chips; the spec has three boxed pips,
   white when filled.
5. **Fight HUD, Heat flame**: a small grey drop at the bar's foot; the spec's flame is 22 px and
   takes the state colour.
6. **Fight HUD, active drive**: a round badge in a burst; the spec's active is the badge cut square.
7. **Boss bar**: the segments change colour (coral in one shot, sunny in another) and two unlabelled
   thin bars sit under the name; "Phase 2" is sunny text with no plate and collides with other text.
   The spec has one bar cut in quarters and nothing else.
8. **Pick of three**: the tags show a third line ("DR. MARIO: new  LUIGI: new") that is clipped by
   the tag's bottom edge; the star ribbon is cut off at the badge; unfocused tags are faded while the
   player is still choosing among them (the spec fades them only after A).
9. **Pick of three**: Skip sits under the "who wears it" pointer and the two overlap.
10. **Empty slots**: drawn as solid pale discs; the spec's empty slot is a dashed ring, so it never
    reads as a faded drive.
11. **Fighter stickers**: a generic head-in-a-circle icon replaces the fighter picture, and the
    player tab is missing on the pick and the road.
12. **Shop**: the hovered row's badge is drawn over the row's left edge; the tag's badge sits outside
    its top left corner rather than on it; "Level up a drive" shows no price; "Back on the road" is
    lilac-filled like a disabled row; only one fighter is shown with an "X / Y: switch" pill and an
    extra hint, where the spec shows all four and uses no X; "Not enough coins." is a coral sticker
    where the spec puts the reason in the strip and the price in deep coral; a bare "28 s" timer sits
    top right.
13. **Road**: three list rows ("On to the next fight", "Abandon run", "Leave (the run is kept)")
    were added under the poster, and the strip reads "Pick the stage, then the fight starts.". The
    spec has no list here (A starts, Start pauses, quitting is in the pause), and the run now picks
    the stage. The poster lost the foe picture and what it carries, and adds "Pool: 4 stocks." which
    the stock sticker already says.
14. **Run strip**: five evenly spread marks with no labels; the boss mark is a ring with a small
    star inside rather than the star. Superseded by the loop strip (2.1).
15. **Camp**: the fighter cards are dashed "Pick, next screen" seats; hint "A Open" does not say
    what opens; "Collection: soon". Superseded by D1.
16. **Main menu**: the run card lists one fighter with chips and the other with none, with the
    generic head icon; the stickers overlap the retail frame's right edge. Layout is otherwise close.
17. **Scenery pixelation**: the campfire and tents are visibly low resolution next to the crisp
    stickers. Flat shapes should be drawn at the output resolution.
