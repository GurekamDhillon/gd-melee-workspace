# Roguelite CPU source audit — 2026-09-30

The implemented addition is an original, opt-in native **technical input assist**
for CPU Fox and Falco. It is not a port of 20XX, UnclePunch, SmashBot or Phillip,
and does not replace the vanilla CPU's neutral, navigation or recovery policy.
No third-party AI implementation, binaries, model weights or game assets were
imported. The observations below use the official repositories, their source
files, GitHub commit/release metadata and license endpoints checked on this date.

| Project | Audited revision / activity | Relevant published capability | Reuse and integration finding |
|---|---|---|---|
| [20XX Hack Pack](https://github.com/DRGN-DRC/20XX-HACK-PACK) | [ae2253f1](https://github.com/DRGN-DRC/20XX-HACK-PACK/commit/ae2253f1e3f4ad47bd3bbbb7f324985a1bd6b8f9), 2023-09-19; [v5.0.2](https://github.com/DRGN-DRC/20XX-HACK-PACK/releases/tag/v5.0.2), 2023-01-21 | The published [AI loader](https://github.com/DRGN-DRC/20XX-HACK-PACK/blob/ae2253f1e3f4ad47bd3bbbb7f324985a1bd6b8f9/Notes%20%26%20Source%20Codes/Source%20Codes/20XX%20AI%20Engine%20Loader.asm) loads `AI_Engine.bin` and installs an interrupt hook. | Public loader/source library is not evidence of a complete readable engine. The official repository's license endpoint returns 404; reuse license remains unresolved. No loader/binary copied. |
| [UnclePunch Training Mode](https://github.com/UnclePunch/Training-Mode) | [fa0b9ef4](https://github.com/UnclePunch/Training-Mode/commit/fa0b9ef4ecb587e20dcce4d2d8aac5b688a42e72), 2021-02-16; [v3.0-alpha.7.2](https://github.com/UnclePunch/Training-Mode/releases/tag/v3.0-alpha.7.2), 2022-05-31 | Author describes predefined technical practice events, automatic savestates and displays. | The README does not establish a stronger unrestricted fighting policy. License endpoint returns 404. No code copied. |
| [Training Mode Community Edition](https://github.com/AlexanderHarrison/TrainingMode-CommunityEdition) | [d75e17e8](https://github.com/AlexanderHarrison/TrainingMode-CommunityEdition/commit/d75e17e86fb7a145def07a36199ba786f656cdbe), 2026-09-22; [CE-v1.4](https://github.com/AlexanderHarrison/TrainingMode-CommunityEdition/releases/tag/CE-v1.4), 2026-04-09 | Current [lab.c](https://github.com/AlexanderHarrison/TrainingMode-CommunityEdition/blob/d75e17e86fb7a145def07a36199ba786f656cdbe/src/lab.c) has CPU state logic, technical lockout handling and training counter behavior. | Actively maintained technical training reference; this source audit does not establish strong open-ended neutral. License endpoint returns 404. No code copied. |
| [SmashBot](https://github.com/altf4/SmashBot) | [67c41209](https://github.com/altf4/SmashBot/commit/67c412092e4ef1576e1357a79461df5faedad3c2), 2024-05-16 | Its official README describes Fox competition through libmelee/Slippi; source separates strategies, tactics and controller chains. | [GPL-3.0](https://github.com/altf4/SmashBot/blob/67c412092e4ef1576e1357a79461df5faedad3c2/LICENSE). Python/emulator observation and controller dependencies require an explicit native adapter or port. No code copied. |
| [Slippi-AI / Phillip II](https://github.com/vladfi1/slippi-ai) | [275c0727](https://github.com/vladfi1/slippi-ai/commit/275c07270b5aa5f7b22aabff79dfe7f7b10a385f), 2026-09-23 | Official repository documents imitation learning from replays and self-play reinforcement learning, with Slippi/Dolphin execution. | [MIT code](https://github.com/vladfi1/slippi-ai/blob/275c07270b5aa5f7b22aabff79dfe7f7b10a385f/LICENSE). Code licensing alone does not establish model-weight redistribution terms. Native observation/input and inference integration remain separate work. No code or weights copied. |

## Original implementation and actual input path

`src/melee/ft/fighter.c` normally obtains CPU stick, trigger and button values
through `ftCo_GetCpu*`, normalizes LR input, then updates pressed-button history.
The new `technical_ai.inc` runs between those input stages. It adds a single
shoulder input and lets existing input, landing and damage collision routines
judge the result. It never writes motion state, landing lag, hitstun, tech timers,
position, velocity, jumps, percent or stocks.

The landing-cancel attempt requires an active common aerial attack with the
native landing-lag command flag, no actionable interrupt, downward motion, and
an actual floor found by `mpCheckFloor` from the current ECB and velocity. It
uses a light analogue shoulder pulse, which produces the ordinary LR edge but
does not produce the digital L/R edge that starts an air dodge. The native
`ftCo_LandingAir_EnterWithLag` tests its ordinary recent-LR timer; this addition
never sets that timer directly.

The ground-tech attempt uses digital R only in the native DamageFly hitstun
states, while descending towards a real floor. Actionable tumble is excluded,
so the assist does not independently air dodge out of tumble. The native prior
shoulder timer must have passed the common tech lockout. Direction choices,
wall/ceiling techs, recoveries and missed-tech followups remain baseline behavior.

Both decisions wait for repeated observations: skill 1/2/3 use 6/4/2 logic-frame
delays and deterministic 60/80/95-percent opportunity acceptance. These are
configured policy probabilities, **not measured success rates**. A private seeded
xorshift stream leaves the game's RNG untouched. One attempt per opportunity
plus 8-frame landing / 40-frame tech cooldowns prevents repeated shoulder pulses.
The ray extrapolates current motion over at most 12 frames; it does not know future
inputs, collisions or acceleration. Near a changing platform or hitstun end it
can miss. It does not model human perception or provide a complete fighting AI.

`gd.cpu_technical(port, skill, seed)` is script-owned and offline; zero clears
that script's configuration. Human fighters, partners, non-Fox/Falco models,
stand CPU, replay playback and netplay/rollback receive no assist. Pauses freeze
it. Actor replacement retires the configuration, and script disable/unload/scene
change clears owned state. Its read-only diagnostic reports input attempts and
missed decisions; it does not mislabel them successful cancels or techs.

## Validation scope

The new native `script_cpu_technical` check exercises the actual policy for delayed
input, deterministic repetition, a single pulse, no-floor fallback, tech lockout,
fresh-input gating, seeded misses and exact ownership cleanup. Lua adapter checks
run real Lua and test refusal/fallback/control routing without physics mocks.

The coordinating agent runs the native build, native tests and normal-speed live
comparison. Record that evidence separately before claiming observed technical
improvement. A win-rate gain, strong neutral, matchup coverage, a full human
playthrough or a 20XX/Phillip port is not established by policy tests.
