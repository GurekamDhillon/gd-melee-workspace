# Envoy UI: implementer's spec

The final design for Envoy's screens, consolidated from the six step sheets. Where this file and a
step sheet (`step2` to `step6`) disagree, this file wins. Where this file and
`envoy-synergy-v3.md` disagree on a rule listed in section 9, this file wins.

- Picture of everything: `preview/final-spread.png` (also split as `preview/final-flow.png` and
  `preview/final-parts.png`).
- Reference target per screen: `screens/<name>.png` (640x480) and `screens/<name>@2x.png`.
- Source of every picture: `build_final.py` (run it to regenerate all of the above).

All positions are **game pixels in a 640x480 frame, origin top left**, written `(x, y)` or
`(x, y, w x h)`. A sticker's position is its unrotated top-left corner; it rotates about its centre.
Frames are 60 per second.

Contents: 1 rules for every screen, 2 the screens, 3 parts, 4 motion, 5 every text string,
6 what the engine must provide, 7 wide screens, 8 what will be hard, 9 decisions.

---

## 1. Rules for every screen

1. **Stickers on paper.** Anything a player can read or land on is a sticker: a flat face, a 3 px
   grape-ink edge, a hard ink shadow offset (3, 4), no blur. Scenery is flat violet shapes with no
   outline. There are no backing panels.
2. **Whose it is.** White face with an ink edge is ours. Ink face with a white edge is a foe or a
   keystone. Sunny is the cursor or something ready. Coral is Player 1, lagoon is Player 2.
3. **One list, one cursor.** Menus are plain lists. Player 1 holds the cursor on shared screens. Only
   the pick of three gives each player their own.
4. **A says what it does.** The hint line never says "OK" or "Select". It names the result.
5. **The strip.** One white sticker at (24, 403), 30 high, holds one sentence about the hovered
   thing. On the pick of three each half has its own, at (x0 + 24, 403).
6. **The hint line** sits at (26, 449). Order is always: move, A, B, Y, Start, then "P2: hold B".
7. **Buttons mean one thing each.**

| button | meaning everywhere |
|---|---|
| Stick or D-pad | move the cursor. The hint says "Up / Down", "Left / Right" or "Stick" |
| A | do the hovered thing; the hint names it |
| B | back one step, or the safe answer in a yes/no. Never destructive |
| Y | Read your drives (map and rest stop) |
| Start | at the camp: start or continue the run. Inside a run: pause |
| D-pad down (in a fight) | tag in your other fighter |
| D-pad right (in a fight) | fire your active drive |
| P2 Start (camp only) | join. P2 holding B for 30 frames leaves |

8. **Counts that vary.** A fighter's row has 3 slots, 4 after boss 1, 5 after boss 2. A run holds 1
   to 3 keystones. A party is 2 fighters (solo) or 4. Every layout below is given for the largest
   case and must not move for the smaller ones.
9. **Smallest text is 11 px.** No Heat digits in a fight. Sentence case everywhere.

---

## 2. The screens

Flow: main menu, camp, keystone pick, map, fight, pick of three, (keystone pick after a boss), map,
... rest stop, boss, ... results, camp. There is no character select between fights.

### 2.1 Main menu row and stickers (`menu.png`, `menu-no-run.png`, `menu-cleared.png`, `menu-no-disc.png`)

**Purpose.** Envoy is a real sixth row of the retail main menu, between Vs. Mode and Trophies. While
it is hovered the port hides the retail right-hand panel and draws loose stickers in that space.

**Layout.** Retail parts are the grey boxes in the reference and are not ours to restyle.

| piece | position | notes |
|---|---|---|
| row plates (retail) | x 28, y 84 + 46 * row, 222 x 38 | Envoy is row 2, y 176 |
| Envoy label (ours) | drawn on the plate, 222 x 38 | emblem centre (25, 19), wordmark from x 47, baseline y 28 |
| sticker space | (272, 76, 340 x 296) | positions below are inside this box |
| description bar (retail) | (28, 398, 584 x 34) | our text, 15 px |

Label L3: a two-pog emblem (white disc r 11.5 in an ink ring r 14.5; coral pog at -3.6, lagoon at
+3.6, each r 5) and the word "Envoy" in Bricolage 800, 26 px, 4.5 px ink edge.

| label state | emblem | word |
|---|---|---|
| idle | ink ring | white |
| hovered | a sunny ring (r 13, 3.2 wide) closes round it | sunny |
| disc missing | replaced by the no-disc mark (coral disc with a slash), scale 1.55 | pale #D5D1EA |

Stickers, by state (space coordinates; add (272, 76) for the screen):

| state | stickers |
|---|---|
| **A saved run** (`menu`) | run card (2, 8, 246 x 198, rot -2): sunny band 54 high with "Continue run" 23 px and one line; then one 34 px line per fighter: player tag (first of each pair), head, name 11 px, the row's chips. Punch card (245, 0, 97 x 136, rot 3, sunny): three lines of five marks. NG+ tag (254, 146, 80 x 30, rot 4, lagoon). Coins (262, 186, 72 x 28, rot -3). Stocks (8, 218, 126 x 50, rot -3). Keystone pills at (150, 220), (158, 249), third at (150, 278) |
| **No run yet** (`menu-no-run`) | card (2, 8, 246 x 164, rot -2) "Start a run" with two empty lines; punch card, all marks open; stock-pool note (176, 160, 150 x 70, rot -3) |
| **Run cleared** (`menu-cleared`) | card "Run cleared!" with the NG+ ladder 0 to 10 and "New in the box"; punch card all filled with a coral Cleared stamp (rot -14); "NG+ 1 open" tag (216, 170, 104 x 38, rot 4, coral) |
| **Brawl disc missing** (`menu-no-disc`) | dashed cream card (2, 8, 246 x 176, rot -2): "Needs your Brawl disc", the no-disc mark and three steps; punch card at 50% opacity |

**Buttons.** Retail. A opens the camp. With the disc missing, A opens a message with the same three
steps and the camp never loads.

**Motion.** On hover: stickers enter (section 4, "enter") staggered 2 frames apart in the order
card, punch card, the rest. On leaving the row they are removed at once (the retail panel returns).

### 2.2 Camp (`camp.png`, `camp-first-time.png`)

**Purpose.** Set up or continue a run. Player 2 joins here; a run started solo stays solo.

**Layout.**

| piece | position | notes |
|---|---|---|
| title | (22, 12) | emblem + "Envoy camp", 23 px |
| big row | (30, 58, 234 x 54) | "Continue run" or "Start run", 23 px, with one 12.5 px line |
| rows | x 30, 234 x 30, y 120 + 36 * i | with a saved run: New run, Fighters, Run length, Team attack, NG+ level, Collection. Without: the list starts at Fighters, y 120 |
| Back | 112 x 28, after the last row | |
| hovered row | moves to x 42, rotation 0, sunny | pointer at (10, row y + 2), big row y + 14 |
| P1 fighters | (292, 54) rot -3 and (368, 60) rot 2, 72 x 94 each | swap mark at (354, 92) |
| P2 fighters | (468, 58) rot -2 and (544, 54) rot 3 | swap mark at (530, 92). Not joined: one dashed card (462, 58, 152 x 92, rot 2) |
| run strip | (290, 182, 312 x 46, rot -1) | marks 18 apart, r 5.5; sunny with tab "Saved run", or white with tab "A full run" |
| stocks | (294, 244, 128 x 50, rot 2) | "Team stocks" or "Solo stocks" |
| keystone pills | (440, 242), (446, 271), (440, 300) | saved run only |
| locked rules | (296, 304, 124 x 52, rot -2) | "Set for this run", saved run only |
| strip, hints | (24, 403), (26, 449) | |

Idle row rotations, top to bottom: -1.2, 0.9, -0.7, 1, -0.9, 0.7, -1.1, 1.2 degrees.

**States.** Saved run with two players (`camp`); first time solo (`camp-first-time`); P2 joining
(their two cards appear dashed with "Pick", stocks go 4 to 5 with a "+1" burst, a "P2 joined" burst
at (566, 18)); Fighters (a sticker sheet (270, 44, 348 x 348) covers the status board: 5 x 3 cards
of 58 x 77, both players' cursors on it, locked cards grey with what opens them); NG+ level (the
status board shows a ladder 0 to 10: opened by both solid, by one dashed, locked grey); Abandon
(dialog (148, 132, 344 x 176), cursor starts on "Keep the run"). Online guest: the Run length, Team
attack and NG+ rows show a lock and the host's value, and the strip reads "The host sets the rules."

**Cursor order.** Top to bottom, wraps. Buttons:

| button | does |
|---|---|
| Up / Down | move |
| A | the hovered row: Continue run, New run (asks to abandon a saved run), open Fighters, switch Team attack, open Collection, Back |
| Left / Right | change Run length and NG+ level on their rows |
| B | Main menu |
| Start | Continue run or Start run, from any row |
| P2 Start / P2 hold B | join / leave |

**Motion.** List rows enter top to bottom, 2 frames apart. Status-board stickers enter after the
list. Hover moves a row 12 px right over 4 frames.

### 2.3 Keystone pick (`keystone.png`, `keystone-after-boss.png`)

**Purpose.** Take one rule for the whole run. Shown at run start and after bosses 1 and 2.

**Layout.**

| piece | position | notes |
|---|---|---|
| title | (16, 2) | "Choose a keystone", 21 px |
| sub line | (22, 36) | white, 12 px |
| seats | (444, 12) | three 22 px wedge outlines, filled sunny for keystones held, then "Keystone N of 3" |
| held pills | (446, 38 + 27 * i) | picks 2 and 3 only |
| wedges | x 28 + 199 * i, y 118 (middle one 106), 186 x 276 | rot -4, 0, +4; emblem 62 px centred on the top edge; name 25 px on two lines; rule 14.5 px; "Good with ..." line 30 px above the bottom |
| hovered wedge | y - 8, rotation 0, sunny face, ink text | pointer from above at (44 + 199 * i, 62) with the P1 tag |
| strip, hints | (24, 403), (26, 449) | |

**Buttons.** Left / Right choose, A "Take it". B "Back to camp" exists only at run start (nothing is
saved yet). Player 1 chooses; online, the host.

**Motion.** Wedges enter left to right, 3 frames apart. On A: the taken wedge grows to 1.16 and
moves to the centre over 12 frames while the other two rotate out (to -24 and +24 degrees) and fade
to 30%; a "Set!" burst pops at its top right; the next seat fills. Holds until A ("Start the first
fight" at run start, "On to act N" after a boss).

### 2.4 Map (`map.png`)

**Purpose.** Say what the next stop is. The path is a straight line, so there is nothing to choose.
The game saves when this screen opens.

**Layout.**

| piece | position | notes |
|---|---|---|
| run strip | (16, 8, 608 x 46, rot -0.4) | acts at x 12 + 200 * a; marks 31 apart, r 7 |
| pointer | under the next mark, y 49 | coral triangle 26 x 14 |
| poster | (20, 70, 300 x 290, rot -1) | sunny band 56 high: kind picture 40 px, kind 28 px, "Act N, fight N of 3"; picture box (10, 68, 124 x 118); name 18 px, place, "Carries" + badges or a note; dashed rule at y 197; "If you win"; "After this:" |
| party | 140 x 80 at (340, 72), (486, 72), (340, 162), (486, 162) | solo: the first two |
| stocks | (342, 254, 128 x 50, rot -1.5) | solo: y 162 |
| purse | (484, 256, 124 x 50, rot 1.5) | "Coins, one purse" |
| keystone pills | (344, 316), (486, 316), (344, 344) | |
| strip, hints | (24, 403), (26, 449) | |

**States.** By the kind of the next stop: Duel, Pack, Elite, Shift room, Rest stop (A reads "Go
in"), Boss (A reads "Fight the boss"; the win line says keystone). Start of act 1: empty rows.

**Buttons.** A starts it. Y opens Read drives (the pause panel's second view). Start pauses.

**Motion.** The strip is there first; the poster enters, then the party. The pointer slides from the
previous mark to the next over 20 frames, and the mark just finished fills ink.

### 2.5 Fight HUD (`fight.png`, `boss.png`, `second-wind.png`)

**Purpose.** Percent, Heat, drives, the bench, and what the party shares, readable over any stage.

**Layout.** `n` is the number of drives worn by the fighter in play (0 to 5).

| piece | position | notes |
|---|---|---|
| P1 corner | origin (14, 382) | everything below is relative to the corner origin |
| P2 corner | origin (626 - (136 + 30 n), 382) | mirrored anchor: the corner's right edge is fixed at x 626 |
| player tag, name | (0, -3), (27, -3) | tag 12 px on coral or lagoon; name 12 px on white |
| percent | (-2, 10) | 40 px, the sign 20 px |
| drive row | (100, 12), 30 px a chip | badge 19 px with a charge ring r 11.6; level pips under it |
| active drive | (106 + 30 n, 12) | square badge 23 px, D-pad glyph at its top right, 2 to 4 pips under it |
| Heat bar | P1 (0, 59); P2 (30 n - 90, 59) | so P2's bar always starts at screen x 400. 122 px for 150 Heat, 11 high |
| bench sticker | 153 right of the Heat bar's start, 1 lower | about 62 x 22: head, percent 14 px, D-pad down glyph |
| stock dots | centred on x 314, y 446 | 14 px dots, 18 apart |
| keystones | (14, 14), 32 x 27 each, 34 apart | emblem only, 1 to 3 |
| coins | right of the keystones, 6 px gap, y 18 | 19 high |
| foes | right-aligned to x 624, y 14, 8 apart | minion plate 28 high, elite 38 high with its drives and Burning dots |
| boss bar | (224, 15, 340 x 15), head circle 34 px at (184, 4), name at (226, 34) | cut in quarters; replaces the foe plates |

With five drives each the two rows are 40 px apart at 4:3 and nothing else moves. With a raised
Heat cap the bar is longer (203 px at 250); if it would reach the bench sticker, that corner moves
up 22 px and the bench sticker goes under the bar's start.

**States.** Heat state Cold, Warm, Hot, Blazing (section 3.9). A drive ready, fired, chained
(a sunny line joins the fired badges). Active ready (sunny burst behind it, D-pad arm coral). Just
tagged (bench sticker greys and refills left to right). Last stock (one coral dot on a sunny
burst). Boss break (a burst on the bar at the break, the quarter mark sparks).

**The Second Wind offer** (`second-wind`). When the pool empties, once a run: the fight freezes
under an 86% ink veil and a dialog (128, 124, 384 x 192, rot -1) asks. Buttons inside at
(16, 140) and (200, 140), 168 x 34. The cursor starts on "Use Second Wind". A confirms; there is
no B. Yes gives one stock and the same fight carries on.

**Motion.** Section 4.2.

### 2.6 Pick of three (`pick.png`, `pick-row-full.png`, `pick-solo.png`)

**Purpose.** After a won fight each player takes one of three drives for one of their own two
fighters, or skips.

**Layout.** Two halves split by a zigzag paper seam at x 320 (teeth 6 px, every 24 px).
`x0` is 0 for P1 and 320 for P2; solo is one half at `x0` 163 with no seam and no player tags.

| piece | position | notes |
|---|---|---|
| title, timer | (222, 0), (372, 2) | 21 px; timer 38 px disc |
| player tags | (30, 10) rot -4, (572, 10) rot 4 | 16 px |
| offers | (x0 + 30, 44 + 78 * k, 284 x 72) | the tag of section 3.4; idle rot -0.5, 0.4, -0.3 |
| pointer | (x0 + 2, 66 + 78 * k) | the player's colour |
| Skip | (x0 + 32, 278, 84 x 26, rot -1.5) | |
| fighters | (x0 + 30, 312) and (x0 + 174, 312), 140 x 80 | the first carries the player tag |
| strip | (x0 + 24, 403) | says what A will do |
| hints | (26, 449) | "Stick Choose, A Take, B Back" |

**States, per player.**

| state | what shows |
|---|---|
| hovering | hovered tag sunny with a "Slot N" flag; the fighter it would go to shows the new chip haloed in that slot |
| a duplicate | the tag reads "Level N adds: ..." with a "Level up!" burst and sunny rays from the moment it is offered; the fighter's chip shows the new pip coral |
| choosing who wears it | after A: the other two offers fade to 34%, a pointer comes down onto the player's fighters, starting on the one the game would pick |
| **the row is full** | hovering: flag "Row full" on the tag. After choosing that fighter the cursor walks the row's chips (Left / Right) with the chip ring on the one that will go; the tag's flag becomes "Slot N"; the strip asks "Replace X with Y for good?". A replaces, B goes back. A duplicate never needs this: it levels up |
| done | the chip is in the row; the strip says who is waited for |
| skip | Skip is the fourth stop of the same cursor |
| timer under 5 s | the timer becomes a coral burst; the first offer of anyone still choosing is flagged "Taken at 0" |

**Cursor order.** Offer 1, 2, 3, Skip (Up / Down). Then fighters (Left / Right). Then, if full,
chips (Left / Right). B steps back one level each time.

**Motion.** Offers enter top to bottom, 3 frames apart, both halves together. Taking: section 4.

### 2.7 Rest stop (`rest.png`, `rest-buying.png`, `rest-reorder.png`)

**Purpose.** Once an act, just before the boss: spend coins, level, restore a stock, reorder rows.
This is the only place drives are reordered.

**Layout.**

| piece | position | notes |
|---|---|---|
| title | (16, 2) | "Rest stop", 24 px |
| purse | (160, 4, 128 x 34, rot 1) | coin, number 20 px, "one purse" |
| list | x 30, 238 x 28; hovered x 40 | y: 44, 75, 106, then 142, then 178, 209, then 245, 276, then 312, then 348 |
| hovered drive's tag | (296, 50, 284 x 72) | |
| party | 140 x 80 at (300, 146), (446, 146), (300, 236), (446, 236) | |
| stocks | (302, 330, 128 x 50, rot -1.5) | |
| strip, hints | (24, 403), (26, 449) | |

Rows, in order: three drives (badge, name, price); an active drive (square badge); Level up a drive;
Restore a stock; Swap the drives on sale; Reorder drives (free); the pact (ink row, "1 stock");
Back on the road.

**States.** Shop. Who wears it (list fades to 36%, a pointer comes down on one of the four fighters;
a full row continues into the same replace step as 2.6). Cannot pay (price in deep coral, A does
nothing, the tag shows "N short" and the strip gives both numbers). Reorder (pick a fighter; their
row opens as a sticker at (296, 34), 102 high, 18 + 76 n wide for up to four slots and 18 + 64 n for
five; the held drive's cell is sunny, raised 5, with a coral arrow each side). Pact (dialog
(132, 132, 376 x 186), ink, cursor starts on "Keep the stock").

**Cursor.** One, Player 1's. Player 2 takes it by pressing A; the pointer changes colour.

| button | does |
|---|---|
| Up / Down | move |
| A | "Buy", "Pay N coins", "Put it down", or the row's own name |
| B | back one step (nothing at the top level) |
| Y | Read your drives |
| Start | pause |

### 2.8 Results (`results.png`, `results-lost.png`)

**Purpose.** How the run went, what it unlocked, one button.

| piece | position | notes |
|---|---|---|
| title | (16, 0) | "Run cleared!" or "The run ended", 30 px |
| sub line | (22, 38) | white, 13 px |
| time | (534, 6, 88 x 46, rot 3) | |
| run strip | (16, 62, 608 x 46) | cleared: a Cleared stamp at its right end. Lost: a ring and coral cross on the stop where it ended |
| party | 140 x 80 at x 18 + 152 * i, y 122 | final rows |
| keystone pills | (18, 212 + 27 * i) | |
| four numbers | y 216, 48 high, at x 166, 270, 378, 532, widths 96, 100, 146, 88 | Drives fired, Longest chain, Coins earned (per player), Stocks lost |
| "Unlocked" | (14, 293), 17 px | |
| unlock stickers | y 322 to 324, 58 high | a locked one is dashed cream and says what opens it |
| strip, hints | (24, 403), (26, 449) | A "Back to camp" |

Cleared adds sunny rays behind everything (18 rays from (320, 40), 13% opacity) and confetti squares.

### 2.9 Pause (`pause.png`, `pause-read-drives.png`)

**Purpose.** Stop, check a rule, or leave. Either player's Start opens it; that player owns the cursor.

| piece | position | notes |
|---|---|---|
| veil | whole frame | rgba(26, 16, 74, 0.86) over the frozen fight |
| title | (16, 2), "P2 paused" tag at (118, 12) | |
| Resume | (30, 46, 230 x 46); hovered x 40 | 22 px |
| Read drives, Quit to camp | (30, 104) and (30, 138), 230 x 28 | Quit carries "the run is kept" |
| D-pad sticker | (28, 186, 236 x 82, rot -1) | the two fight buttons |
| party | 140 x 80 at (300, 44), (446, 44), (300, 130), (446, 130) | |
| keystone slabs | (298, 220 + 50 * i, 316 x 42) | emblem 34 px, name 14 px, rule 11.5 px |
| strip, hints | (24, 403), (26, 449) | |

**Read drives.** The cursor walks every chip of every fighter (stick, row by row). The hovered
chip wears the ring and its tag opens at (6, 284). B goes back. Y on the map and at the rest stop
opens this view directly.

**Quit to camp** asks once, with the camp's Abandon dialog shape and "Keep playing" first. The run
is kept at the start of this fight.

Start always resumes, from either view.

---

## 3. Parts

### 3.1 Colours

| name | hex | use |
|---|---|---|
| Sunny | #FFD84A | cursor, hovered sticker, ready, keystone names, run strip |
| Grape ink | #2A1A6E | every outline and shadow, text, foe and keystone faces |
| White | #FFFFFF | sticker faces |
| Coral | #FF4D6D | Player 1, the last stock, stamps, warning flags |
| Lagoon | #00A99D | Player 2 |
| Lilac | #5A4C99 | quiet text on white |
| Pale lilac | #C9BFF5 | quiet text on ink or violet, dashed seats |
| Deep coral | #C2183F | a price the purse cannot pay |
| Faded sticker | #DAD7E8 | done, locked |
| Cream | #FBF6DD | dashed empty seat |
| Paper violets | #4C3D9E base, #43348F, #33257C ground, #3A2B86 and #2C1E70 (keystone, results), #5849AE moon, #6253B6 tents | scenery only |
| Heat | Cold #B9B2DE, Warm #FFBE2E, Hot #FF8A1F, Blazing #FF4A1C, track #170E45 | |
| Epic foil | #FF8FB8, #FFE066, #8CF0C8, #7FD4FF, #C9A0FF, #FFB27A | linear, 135 degrees; the only gradient |
| Veil | rgba(26, 16, 74, 0.86) pause; 0.66 to 0.70 behind a dialog | |

Families (badge face colour, glyph in white with an ink edge):

| family | hex | glyph |
|---|---|---|
| Fire | #FF7A1F (tangerine) | flame |
| Lightning | #3E6BFF (blue) | bolt |
| Frost | #62CCF5 (sky blue) | six-point flake |
| Wind | #86D63C (lime) | two curls |
| Technique | #C866F2 (orchid) | ring with a centre dot |
| Utility | #AEA8CC (lilac-grey) | two linked rings |
| Spare, clay | #C99455 | hexagon |
| Spare, rose | #FF9CC4 | drop |

### 3.2 Type

Two families: **Bricolage Grotesque 800** (names, numbers, headlines; tracking about -0.02 em) and
**Source Sans 3 700** (sentences, labels).

| role | face | size / line |
|---|---|---|
| results title | Bricolage, white, 4.5 ink edge | 30 |
| screen title | same | 24 (21 on the two picks) |
| sticker headline | Bricolage, ink | 22 to 28 / +2 |
| big list row | Bricolage | 22 to 23 |
| drive name | Bricolage | 16 / 18 |
| fighter name, list row, dialog button | Bricolage | 14 to 15 / 17 |
| strip | Source Sans | 13 / 23 |
| hints | Source Sans, white | 12.5 / 18; button caps Bricolage 11 |
| tag text | Source Sans; the charge phrase in Bricolage | 11.5 / 13 |
| smallest label | Source Sans, lilac | 11 / 12 |
| percent | Bricolage, white, 8 ink edge, ink shadow (1.5, 2.5) | 40, sign 20 |
| foe percent | Bricolage, white on ink | 21 elite, 16 minion |

### 3.3 The sticker

| property | value |
|---|---|
| edge | 3 px ink (2.5 on small pills, 2 on name tags) |
| corner radius | 12 general, 10 list rows, 9 to 11 small pills, 13 the tag |
| shadow | ink, offset (3, 4), hard |
| hovered | sunny face, a 3 px white ring outside the edge, shadow (4, 6), rotation 0 |
| P2's hover on a shared grid | face #D8F5F1, ring lagoon |
| idle rotation | -4 to +4 degrees for cards, under 1.3 for list rows, alternating sign down a list |
| faded | 34 to 36% opacity |
| dashed seat | cream face, dashed ink edge, no shadow |
| ink sticker (foe, deal, keystone) | ink face, 2.5 to 3 white edge, then a 2 to 2.5 ink ring, shadow outside that |

### 3.4 The drive badge, chip and tag

- **Badge.** A disc in the family colour, 2.4 ink edge, white glyph. Sizes: 58 (tag), 32 (reorder),
  22 (chip), 19 (HUD row), 15 (in orbit round the fighter).
- **Tier is the edge.** Common: plain. Rare: a white die-cut ring 1.28 times the disc radius. Epic:
  the same ring in foil, with a sunny four-point spark at its top right.
- **Level.** On a tag: three 11 px stars in a white ribbon under the badge. On a chip: three pips
  6 x 5 under the badge, filled ink. A pip or star just gained is coral.
- **Chip.** 26 x 34: a 22 px badge and its pips. New: a sunny halo disc behind it. Levelling: halo
  plus a coral up-arrow dot at its top right. Empty slot: a dashed lilac circle r 9.5.
- **HUD chip.** 30 x 38: a 19 px badge inside an ink disc r 13.4 with a charge ring (r 11.6, 2.9
  wide, sunny over lilac, clockwise from the top). Pips 7 x 6 under it. Fired: a sunny 16-point
  burst behind it.
- **Active drive.** The same badge cut square (radius 42% of half its side), 23 px, with the D-pad
  glyph and 2 to 4 round pips.
- **Tag.** 284 x 72. Badge 58 at (-3, -4); paper (40, 2, 244 x 68) with radius 11; line 1: name 16
  left, "Rare frost" 11 right; then "**Every N% you deal:** what it does." 11.5; then "Lv N: what
  it adds." 11 lilac. Flags: "Slot N" (ink, top right, rot 4) or a coral flag ("Row full",
  "Taken at 0", "N short") in place of the rarity words.
- **Charge text never counts hits.** Always "Every N% you deal".

### 3.5 The fighter sticker

140 x 80. Head 22 px at (5, 3); name 14.5 at (33, 9); chips from (4, 38), 26 px each, so five fit
exactly. The first of a player's pair carries their tag at the top left (rot -7). Rotations in a
group of four: -0.6, 0.5, 0.4, -0.5.

### 3.6 The keystone

| form | where | size |
|---|---|---|
| wedge | the pick | 186 x 276, sides slant in 22 px; ink face, 2.5 white line, ink edge; hovered: sunny face |
| seat | the pick, top right | 22 px outline, dashed pale lilac; filled sunny when held |
| pill | camp, map, results, main menu | 25 high, ink, radius 9: emblem 21 + name 12.5 sunny |
| slab | pause | 316 x 42 ink sticker: emblem 34, name 14 sunny, rule 11.5 white |
| mini wedge | fight | 32 x 27 ink with a white edge, emblem 19, no words |

### 3.7 List row, pointer, cursors

- **Row.** 28 high (big 46 to 54), label Bricolage 14 to 15 left, value right (Source Sans 12 lilac,
  or a coin and a price in Bricolage 13.5). Hovered: sunny, moves 10 to 12 px right. Ink row: a deal.
- **List pointer.** 28 x 26 block arrow, player colour, 2.5 ink edge, 6 px white die-cut. It sits
  20 to 22 px left of the hovered row.
- **Sticker cursor.** 24 x 27 arrow with the player tag at its lower right; used on grids and chips,
  pinned over the sticker's lower right.
- **Pointer from above.** 26 x 28 down arrow with the tag; used over wedges and fighter stickers.
- **Chip ring.** r 13, sunny 2.6 over ink 5.

### 3.8 Strip and hints

- **Strip.** 30 high, 3 ink edge, radius 10, padding 11, rotation -0.6, Source Sans 700 13 px. Width
  fits the sentence; at most 292 on a half screen (about 42 characters) and 590 on a full one.
- **Hint.** A white cap (18 high, radius 9, 2 ink edge, Bricolage 11) then the words in white Source
  Sans 12.5; 16 px between hints.

### 3.9 The Heat bar

Rules: +1 Heat per 1% dealt, -1 per 1% taken, no decay, 0 at the start of each fight. Cap 150,
raisable to 250. A KO pays out and the player keeps half; in co-op every player with 10% or more on
that foe cashes out.

| state | from | fill | flame at the bar's foot |
|---|---|---|---|
| Cold | 0 | #B9B2DE | scale 0.12, grey |
| Warm | 25 | #FFBE2E | 0.165 |
| Hot | 60 | #FF8A1F | 0.21, sunny core |
| Blazing | 110 | #FF4A1C with a 2.6 px white streak | 0.26, white core |

Geometry: track 122 x 11 for 150 Heat (0.813 px per Heat), radius 5.5, inside an ink ring 2.5 and a
white ring 2. Marks at 25, 60 and 110: a 2 px line through the bar and a 5.5 px white tick above it.
Gain: the new piece is white for 6 frames. Loss: the lost piece shows dashed for 10 frames and three
chips fall. Crossing a mark: a small burst on the mark. At the cap: the outer ring turns sunny and
sparks leave the end. Cash-out: the paid half shows at 38% and coins leave the bar's end.

### 3.10 Stocks, coins, timer, run strip

- **Stock dot.** White, 14 px, 2.5 ink edge, a 1.5 white ring, shadow (1.5, 3). Spent: ink with a
  white edge at 60% size. One left: coral, on a sunny burst. On a white sticker the dots are 12 px
  white discs in an ink capsule (radius 10); spent ones are hollow lilac rings.
- **Coins.** Earned per player, kept in one party purse. Coin: sunny disc with an inner ring.
  Counter: white pill 19 high in a fight; purse sticker 124 x 50 between fights.
- **Timer.** 38 px white disc, a coral ring that empties clockwise, digits 15. Under 5 s: a coral
  burst 54 px with the digit 22.
- **Run strip.** Sunny, 46 high. Fight: disc. Rest stop: triangle. Boss: star. Done: ink. Next:
  coral inside an ink ring. To do: white. Lost here: ring with a coral cross.

### 3.11 Bursts, stamps, flags, tags

- **Burst.** 16-point star, coral (lagoon for P2 joining), 3.5 ink edge, rot 8, white text with a
  3 ink edge. "Set!", "Level up!", "Once a run", "P2 joined", "+1".
- **Stamp.** "Cleared": coral text and a 3 coral edge on white, rot -7 (or -14 on the punch card).
- **Player tag.** Small: 12 px white on the player colour, 2.5 ink edge, radius 8. Large: 16 px.

---

## 4. Motion

Keep it small. Nothing loops except the two noted. All easing is "ease out" (fast start) unless
noted; a linear lerp with the listed overshoot key is enough.

### 4.1 Menus

| moment | motion | frames |
|---|---|---|
| a sticker enters | scale 0.85 to 1.04 to 1.0, opacity 0 to 1, from its own centre, at its resting rotation | 6 + 3 |
| a list or group enters | members 2 frames apart (3 for cards and wedges), top to bottom or left to right | |
| hover on | rotation to 0, face to sunny, move 10 to 12 px (rows) or up 4 to 8 px (cards, wedges) | 4 |
| hover off | back to the resting rotation and place | 4 |
| pointer moves | slides to the new row | 4 |
| A on a row or card | scale 1.0 to 0.94 to 1.0 | 2 + 4 |
| a drive is taken | its badge shrinks from the tag to the chip slot along a straight line; the slot's halo pops 1.3 to 1.0 | 10, then 6 |
| a level-up | the new pip or star pops 1.6 to 1.0 in coral, then turns ink; rays behind the tag turn 4 degrees a second while it is offered (loop) | 8, then 30 hold |
| a replace | the old chip drops 10 px and fades | 8 |
| others fade | to 34% | 6 |
| a burst | scale 0 to 1.2 to 1.0, with its 8 degree tilt | 4 + 3; stays |
| a dialog | veil fades in; the dialog enters as a sticker | 6 |
| a screen leaves | all stickers fade | 6 |
| timer | the ring empties continuously; under 5 s the burst pulses 1.0 to 1.1 each second | |
| campfire | the flame swaps between two shapes every 20 frames (loop) | |

### 4.2 Fight

| moment | motion | frames |
|---|---|---|
| Heat gain | bar extends at once; the new piece is white, then takes the state colour | 6 |
| Heat loss | bar shortens at once; the lost piece stays dashed, three chips fall 10 px and fade | 10 |
| state up | burst on the mark 0 to 1; the flame steps to the next size | 6 |
| state down | the flame steps down; no burst | 4 |
| a drive charges | the ring grows continuously | |
| a drive fires | sunny burst behind its badge, badge scale 1.25 to 1.0 | 6 |
| a chain | the link line runs badge to badge, one link every 6 frames, at most 4 links | 6 a link |
| active ready | burst behind the badge pops; the D-pad arm turns coral | 6 |
| cash-out | the paid half dims; 3 coins fly from the bar's end to the coin counter; the counter pops 1.2 | at most 30 |
| tag | the bench sticker's face fills grey and refills left to right over the cooldown | cooldown |
| a stock is lost | the dot shrinks to the ink point | 8 |
| last stock | the burst behind the dot pulses 1.0 to 1.15 once a second (loop) | |
| boss break | burst on the bar at the break, three chips fall | 12 |

---

## 5. Every text string

Braces are values. Fighter, foe, stage, drive and keystone names come from data.

**Main menu.** Row: `Envoy`. Bar: `A co-op run for 1 or 2 players, three acts long.` /
`Continue your run from act {a}, fight {f}.` / `Run cleared. NG+ {n} is open at the camp.` /
`Envoy needs your Brawl disc. Add it in the launcher.` Stickers: `Continue run` /
`Act {a}, fight {f}. Saved after fight {f-1}.` / `Start a run` /
`Three acts: fights, a rest stop, a boss.` / `Pick two fighters at the camp.` /
`A second player joins at the camp.` / `One stock pool` / `5 together, 4 solo` / `Run cleared!` /
`NG+ {n} is open. Start it at the camp.` / `NG+ level, up to 10` / `New in the box` /
`{n} fighter, {n} drives` / `NG+ {n}` / `NG+ {n} open` / `Cleared` / `Needs your Brawl disc` /
`Envoy opens once the disc is added.` / `Open the launcher.` / `Add your Brawl disc.` /
`Restart the game.` / `Team stocks` / `{n} of {n}` / `Act 1` `Act 2` `Act 3`.

**Camp.** `Envoy camp` / `Continue run` / `Act {a}, fight {f}. {n} of {n} stocks left.` /
`Start run` / `A new full run, from act 1.` / `New run` / `Fighters` `2 each` / `Run length`
`Full, 3 acts` `Short, 5 fights` / `Team attack` `On` `Off` / `NG+ level` `{n}` `0 only` /
`Collection` `{n} of {n}` / `Back` / `Player 2` `Join` `on controller 2` / `Pick` / `Saved run` /
`A full run` / `Solo stocks` / `Set for this run` `NG+ level {n}` `Team attack off` /
`P2 joined` / `+1`.
Strip: `Pick up at act {a}, fight {f} with the saved party.` /
`Three acts. Each is 3 fights, a rest stop, then a boss.` /
`Player 2 is in: 5 stocks together. Pick two fighters, then start.` /
`Bring two fighters each. You swap between your two mid-fight.` /
`Together you play the lower level. P2 has opened {n}, so {n} is the top.` /
`On: your attacks hit your partner too. Fixed once the run starts.` /
`The host sets the rules.`
Fighters sheet: `Fighters` / `Tagged ones are in the party. A swaps one in.` /
`{n} still locked. Each says what opens it.` Abandon: `Abandon the saved run?` /
`Act {a}, fight {f} and its {n} stocks will be gone for good.` / `Keep the run` / `Abandon it`.

**Keystone pick.** `Choose a keystone` / `One rule for the whole run. The party shares it.` /
`One more rule, on top of what the party holds.` / `Keystone {n} of 3` / `Good with {x}` /
`Set!` / `{keystone} is the rule`. Strip: one sentence per keystone, plus how it fits the party.

**Map.** `Duel` `Pack` `Elite` `Shift room` `Rest stop` `Boss` / `Act {a}, fight {f} of 3` /
`Act {a}, the boss` / `Act {a}, once an act` / `on {stage}` / `Carries` / `If you win` /
`Your pick of three drives.` / `One of its two drives, then your pick of three.` /
`A new keystone, then act {a}.` / `After this: {next}, then {next}.` / `No fight here` /
`A shop and a breather` / `Buy or level a drive, restore a stock, reorder a row.` /
`Coins, one purse` / `Coins`.
Strip: `The first fight of the run. One fighter, nothing extra.` /
`An elite: a strong fighter with two drives of its own.` /
`A rest stop: spend coins, reorder drives, then on to the boss.` /
`The act {a} boss. Beat it and the party takes a new keystone.`

**Fight.** `P1` `P2` / `Elite` / `Boss {n}` / `{n}%`. Second Wind: `Use your Second Wind?` /
`The stock pool is empty. Once a run the party can get back up with one stock and carry on with this fight.` /
`Say no and the run ends here.` / `Use Second Wind` / `End the run` / `Once a run`.

**Pick of three.** `Pick a drive` / `Skip` / `Slot {n}` / `Row full` / `Taken at 0` / `Level up!` /
`{Common|Rare|Epic} {family}` / `Every {n}% you deal:` / `Lv {n}: {adds}.` / `Top level.` /
`Level {n} adds: {adds}.` / `{fighter} has level {n}.`
Strip: `{drive} goes to {fighter}, slot {n}.` / `{fighter}'s {drive} goes up to level {n}.` /
`{fighter}'s row is full. A picks a slot.` / `Who wears {drive}? {fighter}, slot {n}.` /
`Who wears {drive}? Level up on {fighter}.` / `Who wears {drive}? {fighter}'s row is full.` /
`Replace {old} with {drive} for good?` / `{drive} is on {fighter}. Waiting for P{n}.` /
`Take nothing this time.` / `3 seconds left: {drive} will be taken.`

**Rest stop.** `Rest stop` / `one purse` / `{active}, an active` / `Level up a drive` /
`Restore a stock` / `Swap the drives on sale` / `Reorder drives` `free` /
`Pact: {drive} for a stock` `1 stock` / `Back on the road` / `{n} short` /
`{fighter}'s row` `fires left to right` `Slot {n}` `Empty`.
Strip: `Buy {drive} for {n} coins. You choose who wears it next.` /
`Who wears {drive}? {fighter}, slot {n}.` / `{drive} costs {n} coins. The purse has {n}.` /
`Holding {drive}. Move it left or right, then put it down.` /
`Pick one of your drives to raise a level.` / `One stock back in the shared pool.` /
`Three new drives on the counter.` / `Change the order your drives fire in.` /
`Leave for the boss.`
Pact: `A pact is offered` / `{drive}, an epic drive, for one stock from the pool. Once this act.` /
`Stock pool` `becomes` / `Keep the stock` / `Take the pact`.

**Results.** `Run cleared!` / `All three acts, with {n} of {n} stocks to spare.` / `The run ended` /
`Act {a}, fight {f}: {foe} on {stage} took the last stock.` / `Time` / `Drives fired` /
`Longest chain` `{n} drives` / `Coins earned` / `Stocks lost` / `Unlocked` / `New fighter` /
`New drive` / `New keystone` / `NG+ level {n} is open` / `Still locked` /
`{fighter} opens when you beat act {a}.` / `Cleared`.
Strip: `{drive} can now turn up in any run.` /
`{n} new things are waiting at camp, and a harder run.`

**Pause.** `Paused` / `P{n} paused` / `Resume` / `Read drives` / `Quit to camp` `the run is kept` /
`The D-pad in a fight` / `Down: tag in your other fighter` / `Right: fire your active drive`.
Strip: `Back to the fight. Either player can pause.` /
`{drive}, level {n}, in {fighter}'s slot {n}.` Quit: `Quit to camp?` /
`The run waits at the start of this fight.` / `Keep playing` / `Quit to camp`.

**Hints (the whole set).** `Up / Down` `Left / Right` `Stick` + `Choose` | `Choose a fighter` |
`Choose a drive` | `Move {drive}` | `Change level`. `A` + `Continue run` | `Start run` | `Open` |
`Switch` | `Take it` | `Start the fight` | `Go in` | `Fight the boss` | `Take` | `Buy` |
`Pay {n} coins` | `Put it down` | `Swap in` | `Resume` | `Use Second Wind` | `Keep the stock` |
`Back to camp` | `Start the first fight`. `B` + `Back` | `Main menu` | `Back to camp` |
`Keep the run` | `Keep the stock` | `Done`. `Y` + `Read your drives`. `Start` + `Continue run` |
`Start run` | `Pause` | `Resume`. `P2: hold B` + `Leave`.

---

## 6. What the engine must provide

1. **A textured quad with rotation and scale about its centre**, alpha blended, with per-quad
   opacity, drawn in a fixed order (painter's order; no depth test needed).
2. **Stickers as 9-slices.** The rounded rectangle with its ink edge and hard shadow, in four
   faces (white, sunny, ink with white edge, dashed cream), stretched by a 9-slice so one texture
   serves every size. Corner radius 12 and 10 are enough; pre-bake both.
3. **Baked sprites** for everything with a fixed shape: badges (8 families x 3 tiers, round; 8
   square), family glyphs, keystone emblems, wedge (idle and hovered face), stars, pips, pointers
   and cursors in two colours, button caps, D-pad glyphs, flame in four states, coin, burst,
   run-strip marks, head silhouettes, lock, swap mark, the no-disc mark. All are in
   `build_final.py` as SVG and can be rendered to an atlas at 1x and 2x.
4. **Text in two fonts** (Bricolage Grotesque 800, Source Sans 3 700) at the sizes of 3.2, with
   left, centre and right alignment, one colour per run, and word wrap inside a width. Two extra
   needs: text with an **outline** (titles: 4.5 px ink; percent: 8 px ink plus an offset ink copy),
   which can be a pre-outlined glyph atlas; and **mixed faces in one line** (the tag's bold phrase).
5. **A ring or arc**: a stroked circle drawn from the top clockwise to a fraction (drive charge,
   timer). A 32-step triangle strip or a radial-wipe shader both work.
6. **A clipped bar**: a rounded track with a fill clipped to it, up to three fill segments (kept,
   paid, gained), plus tick marks. A scissor rectangle and a rounded mask sprite are enough.
7. **A full-frame veil** (one translucent quad) and **freeze** of the fight under it.
8. **Flat scenery**: a handful of filled shapes per screen (hills, tents, moon, rays, the seam). One
   pre-rendered 854 x 480 background per screen is the cheap route (5 backgrounds: camp, key,
   road, rest, reward; results reuses key with rays).
9. **Per-player input routing** on the pick of three (two cursors at once), and "either player" on
   pause and Second Wind.
10. **Layout in 640x480 units**, scaled uniformly to the output and centred for wide screens.

---

## 7. Wide screens (16:9, 853 x 480)

Menu screens keep the 640-wide block centred (offset 106) and only the scenery extends. The fight
HUD is the exception: the two corners, the keystones and the foe plates follow the screen edges;
the stock dots stay centred. Nothing is stretched or resized.

---

## 8. What will be hard or expensive

- **Outlined text at many sizes.** Titles and percent need a thick ink edge. Stroking at run time
  is costly; bake outlined atlases for the few sizes used (21, 24, 30, and 40 for digits and %).
- **Rotated text.** Every idle sticker is tilted, so its text is too. Under one degree at 11 px on
  a 640x480 target shimmers. Render the UI at the output resolution (not 640x480 then upscaled),
  or snap tilts under 1 degree to 0 at 1x and keep them only when the output is 2x or more.
- **The tag's sentences.** Three lines of 11 to 11.5 px text with a bold phrase, in 244 px. This is
  the densest text in the design and the first thing to check on a real 480-line output. It needs
  word wrap and two faces in one line.
- **The Epic foil rim.** A six-stop gradient ring. Bake it per badge size.
- **Rays and bursts behind stickers** are many thin triangles; bake them as sprites and rotate.
- **Five slots in the fight HUD.** Two rows of five chips plus two active drives fill the width
  (40 px between corners at 4:3). There is no room for a sixth, or for longer fighter names than
  about 11 characters, which overlap the row.
- **A raised Heat cap** changes a corner's height by 22 px (the bench sticker moves). It is the
  only layout in the HUD that depends on state.
- **Up to 11 HUD stickers over the stage in a fight**, each with an edge and a shadow. Flat quads,
  so cheap, but the charge rings update every frame; keep them as arcs, not re-baked textures.
- **Two live cursors on the pick of three**, each with a three-level focus (offer, fighter, chip)
  and a shared timer.
- **The hidden retail panel** on the main menu: the port must suppress the retail right-hand
  panel while the Envoy row is hovered and restore it on the other rows.

---

## 9. Decisions

"Owner" means chosen by the owner on a step sheet or stated in the final brief. "Delegated" means
decided here, in the owner's pattern, under the delegation in the final brief.

| # | decision | by |
|---|---|---|
| 1 | Direction: Party pack (sunny, grape ink, white stickers, coral P1, lagoon P2, Bricolage + Source Sans 3) | Owner |
| 2 | A real sixth main-menu row between Vs. Mode and Trophies; label L3; right-hand space as P2 loose stickers in four states | Owner |
| 3 | Camp C1; drive D2; pick of three R2; keystone pick K1; HUD H2 + M1 with the small bench sticker; map N2; shop S1; results and pause as drawn | Owner |
| 4 | Heat: +1 per 1% dealt, -1 per 1% taken, no decay, 0 each fight; Cold, Warm 25, Hot 60, Blazing 110; cap 150, raisable to 250; a KO pays and keeps half; co-op cash-out at 10%+; no Heat digits | Owner |
| 5 | Drive text never counts hits: "Every N% you deal" | Owner |
| 6 | Slots 3, 4 after boss 1, 5 after boss 2; order matters; reordering only at the rest stop | Owner |
| 7 | Up to three keystones a run (start, after boss 1, after boss 2) | Owner |
| 8 | Coins earned per player, one shared purse; tiers Common, Rare, Epic | Owner |
| 9 | Rest stop just before the boss; Second Wind gives one stock and the same fight carries on | Owner |
| 10 | A full row: a new drive replaces one the player picks, or skip; a duplicate still levels up | Owner |
| 11 | No character select between fights | Owner |
| 12 | Co-op needs P2 to have joined at the camp; no "Play online" hint; online shown only as "the host sets the rules" | Owner |
| 13 | Stock dots white, the last one coral; eight family colours | Owner |
| 14 | One hint set and one description strip on every screen | Owner (the rule); Delegated (the set in 1.7 and the strip in 3.8) |
| 15 | Start means pause everywhere inside a run. The map's "Start: Save and quit" and the rest stop's "Start: Back on the road" are gone; leaving the rest stop is its last row | Delegated |
| 16 | B is never destructive. The Second Wind offer has no B; "End the run" must be chosen with A | Delegated |
| 17 | The pick of three hints read "Stick Choose" because one line serves both players at different depths | Delegated |
| 18 | The full-row step: after choosing the fighter, the same cursor walks that row's chips; the strip asks "Replace X with Y for good?" | Delegated |
| 19 | In a fight the keystones are emblem-only wedges at the top left with the coin counter beside them; the stock dots stay alone at the bottom centre. Three names do not fit between two five-slot corners | Delegated |
| 20 | In a boss fight the boss bar sits 60 px right of centre to clear the keystones | Delegated |
| 21 | On white stickers the stock dots sit in an ink capsule, so white dots read | Delegated |
| 22 | Held keystones are pills with their own emblem (not a star) on the camp, map, results and menu; slabs in the pause | Delegated |
| 23 | The main-menu run card lists all four fighters, one line each, with chips; the punch card and every run strip have five marks an act (the step 2 and 3 sheets had four) | Delegated |
| 24 | The strip is one size (30 high, 13 px) on every screen, including both halves of the pick of three (step 4 used a smaller one) | Delegated |
| 25 | Results show coins earned per player; the purse stays one number everywhere else | Delegated |
| 26 | The rest stop list adds one row for an active drive, and prices follow the mechanics note (40, 80, 150; level 60; swap 10). "Restore a stock" (50) is kept from the chosen S1 sheet | Delegated; prices are data |
| 27 | Spare families are named "clay" (hexagon) and "rose" (drop) until they get real names | Delegated |
| 28 | The camp's solo P2 seat reads "Start: Join, on controller 2" | Delegated |

### Still open

- **"Restore a stock" and the pact's wording** are on the chosen S1 sheet but "Restore a stock" is
  not in the mechanics note. The row is drawn; the mechanics owner should keep or cut it.
- **Where an active drive comes from besides the shop** (first boss, a rare card) has no screen of
  its own. It can reuse the pick of three's tag with a square badge.
- **The 20 second timer on the pick of three** is kept from the chosen R2 sheet. Whether it runs
  offline is a rules question; the UI works with or without it.
- **Keystone rule sentences** on the wedges are the step 4 samples, not the mechanics note's
  current rules. The wedge fits about 60 characters at 14.5 px.
- **Collection, the Fighters sheet, NG+ ladder and the Abandon and Quit dialogs** are specified
  from the step 3 sheet and were not redrawn here; their strings and positions are in 2.2 and 5.
- **Short run** (5 fights) shortens the run strip to one line of five marks; not redrawn.
