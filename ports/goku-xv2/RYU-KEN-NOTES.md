# What Ultimate's Ryu and Ken suggest for Goku's combo system (2026-10-08)

Local only. Source data: the extracted Ultimate fighter folders `experiment/tooling/ultimate/workspace/extracted/fighter/{ryu,ken}`
(found via `ports/ir/tools/convert_ultimate_anim.py`'s `GW_ULTIMATE_ROOT` default). **No ACMD, status or opff code for Ryu or
Ken exists locally**: only motion lists, the body skeleton IR and the CPU-AI tables `ai/param/attack_data_param.prc` (decoded
with ParamXML; start / end / combo_end / cancel frames and the next motion per move). Those AI tables are the only Ryu/Ken
numbers below that come from data; they are CPU timing hints, not verified player frame data. Everything else is labelled as
general knowledge of Ultimate's design, not read from local files.

| idea | what Ryu/Ken do (source) | Goku: adopt / adapt / reject | where it is |
|---|---|---|---|
| Light vs strong normals by tap vs hold | Ultimate Ryu/Ken have `_w` (weak, tap) and `_s` (strong, hold) versions of jab and tilts (AI table: `attack_11_w` 2-4 vs `attack_11_s` 9-11, `attack_hi3_w` 3-7 vs `_s` 7-12) | **Adapt, not built for Goku.** The approved split is light (A) vs heavy (smash / C-stick). A route's `hold` field already lets any define take a strong variant by holding A; using it for Goku would change the approved controls, so it is offered, not done | engine: `routes[].hold` |
| Jab chain with a cut-off | `attack_11_w -> attack_12 -> attack_13` with `combo_end` 23 (AI table): the next jab only inside a window | **Adopt** (it is XV2's light chain too): each link has the source's XV2 BAC cancel window | `combo.json` routes L1>L2..L4>L5 |
| Special-cancelling normals on hit | Ryu/Ken cancel normals into specials on hit (Ultimate design; the AI `cancel` column gives the latest frame, e.g. `attack_11_w` 16) | **Adopt** (approved): side B and neutral B cancel the light string on hit only | `Lx>Dragon Rush`, `Lx>Ki Volley` |
| Target combos | Ken's `attack_command1 -> attack_command3`, `attack_command2 -> attack_command3` (AI table `next`) | **Adopt**: this is exactly a route; XV2's L5 > heavy finisher is Goku's target combo | `L5>H finish` |
| Command inputs (QCF / DP) for stronger specials | Ultimate Ryu/Ken: input specials deal more and have a leniency window (general knowledge; the leniency numbers are in their param files, which are not local) | **Escalate, not built.** A command-input Kamehameha would change the approved controls and needs a motion-input reader in the engine (a sequence of stick directions in the buffer). The route buffer is the place it would live | open question for the coordinator |
| Auto-turnaround in 1v1 | Ryu/Ken always face the opponent in 1v1 (general knowledge) | **Reject** for Melee play (spacing, back-air, turnarounds are Melee skill); could be an optional per-fighter flag later | - |
| Focus Attack armour + crumple | Ryu/Ken down B: armour, crumple on full charge (AI table: `special_lw` 11-13, cancel 56) | **Model only** for Z-vanish / ki charge (owned by the Goku lane: Counter / down-B states). Geno has counter windows and Lua; no combo-graph change needed | - |
| Shoryuken invincibility | `special_hi` 6-20 active (AI table); start-up invincibility (general knowledge) | **Model only** for Instant Transmission (owned by the Goku lane); body_state intangibility in Geno scripts covers it | - |
| Hitstun / set knockback on string hits | Ultimate light hits often use set knockback and `set_add_reaction_frame` (extra hitstun) so strings stay true at every percent (general knowledge; Geno's HBSTUN is the latter, docs/geno.md 20 table) | **Adopt**: Light3-5 and the combo package's jab1/jab2 use `fkb` 10 / `kbg` 60 (the same push at every percent) and HBSTUN; heavy enders keep growth so DI and percent still decide the follow-up | `combo/moves/*.genoasm`, `combo.json jab_set_kb / jab_stun` |
| Multi-hit links (autolink) | Ultimate's multi-hit moves pull with autolink angles | **Tried and rejected** for the string: `LINK 3 2` pushed the victim away at Goku's step speed; dropped for set knockback | combo/moves history |
| SDI multipliers | Ultimate tunes SDI per hit | **Reject**: Melee's SDI stays (approved: DI preserved) | - |

Adopted ideas changing the approved control scheme: **none**. Command inputs are the one proposal that would; it is escalated,
not built.
