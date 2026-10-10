# Jev tools

Small advisory tools for the GD's Melee workspace, powered by TypeSafe's Jev
(System One). Python 3.10+ and the standard library are sufficient; no SDK install
is needed. The shared client is `jev.py`. API shapes were checked against
[the API reference](https://docs.typesafe.ai/api) and
[the Python SDK docs](https://docs.typesafe.ai/sdk/python), discovered through
[llms.txt](https://docs.typesafe.ai/llms.txt).

Set **only** `TYPESAFE_API_KEY` in the process environment. These tools do not
source `.env`, inspect disc paths, build, launch games, or upload whole files.
The client POSTs `state`, `model: jev-latest`, and typed `questions` to
`https://api.typesafe.ai/v1/systemone`. Each attempt defaults to an 8-second
timeout, with one retry after 250 ms for connection errors, timeouts, or transient
HTTP failures. Authentication, validation, and malformed-answer errors do not
retry. Error bodies, credentials, and request payloads are never logged.

Every CLI accepts `--offline` (alias `--dry-run`) and `--timeout SECONDS`.
Offline mode never needs a key or network and returns a deterministic **stub**,
explicitly marked `source: stub`. Its keyword rules are test fixtures, not verified
Jev decisions. Missing keys or failed calls print `jev: unavailable` to stderr;
ranking retains the original order, triage records unavailability, and claims
retain `no evidence` with `source: unavailable`. None changes a sweep verdict.

## How lanes should call these (v2, 2026-10-09)

The design follows TypeSafe's own guidance (docs: *How to build with TypeSafe*, *State*,
*Choice*, *Noul*, *Confidence*, *Confidence-gated routing*, *Jev 1.13 jaggedness*): code owns
control flow and every deterministic fact; Jev gets only narrow, typed questions over only the
relevant text; every answer is gated on confidence in code. Rules of thumb used throughout:
facts (PASS/FAIL, exit codes, counts, timeouts) are parsed, never asked; one condition per
Noul; Choice options carry `what`/`not_for`/`examples`; a Choice is asked twice with the
options reversed because Jev 1.13 leans to the first option; irrelevant text is filtered out
in code first (distractors hurt); an unsure answer routes to a human.

| you want | run | what comes back |
|---|---|---|
| "did this run pass / why not" | `python tools/jev/runparse.py RUN_DIR_OR_LOG [--expect-mod ID]` | typed verdict, no model, no key, no network |
| the same, plus a judgment on a crash | `python tools/jev/triage_run.py RUN_DIR` | `choice`, `band` (act / confirm / human), `source` (code / rule / jev / stub) |
| "did the report do what the brief asked" | `python tools/jev/coverage.py BRIEF.md REPORT.md` | per requirement done / owed / unaddressed / unclear, plus a needs-human list |
| "are the report's test/build/run claims true" | `python tools/jev/check_claims.py REPORT LOG_OR_RUN_DIR... ` | per claim supported / unsupported / no evidence |
| rank review findings | `python tools/jev/rank_findings.py findings.txt` | by player impact, low-confidence ones marked `read it` |

Add `--offline` for the deterministic stub (never a key, never the network). Without
`TYPESAFE_API_KEY` the model-backed steps degrade to `jev: unavailable` and everything decided
in code still works. **Read `band`**: `act` may be used, `confirm` is probable (look once),
`human` means do not trust it. `source: stub` is a test fixture, not a Jev decision.

## Deterministic run parser (`runparse.py`)

No model. Reads `melee-pc.log`, `exit.json`, `diagnosis.json`, newest `crashlogs/*.log` of a run
dir, or any log/`*.run.txt`. Output classes:

| class | meaning | decided in code |
|---|---|---|
| `pass` | at least one PASS result line (`RESULT PASS`, `*CHECK ... PASS`, `TESTS: pass=N fail=0`), no FAIL, no fault, clean exit | yes |
| `clean_no_verdict` | clean exit 0, no FAIL, no fault, but the script printed no PASS/FAIL token (e.g. `LANDCHECK RESULT cases=40 sinking=0`). Never a bug by itself; read the numbers | yes |
| `test_fail` | any FAIL result line or `TESTS: TIMEOUT` | yes |
| `harness_setup` | a hard setup signature and no PASS verdict: `MELEE_SCENE: rejected`, `define refused` (geno.json newer than the build), expected mod not loaded (`--expect-mod`, or `geno:<id>/` in the scene), disk full (ENOSPC / "No space left"), sandbox failure | yes |
| `timeout` | launcher `TIMEOUT code=124` with none of the above; `cause` is `load_progress`, `unexplained`, or a soft setup signal such as `turbo_refused` | the fact yes, the cause no |
| `fault` | assertion, FATAL, access violation, panic, watchdog stall (not on a paused/hidden window), Lua error, or a crash log. Teardown noise ("ignored at exit", Dawn device loss) is excluded. Includes a bounded, redacted `signature` | no: this is the only thing sent on to the model |
| `unknown` | no verdict, no exit information | no |

`turbo: refused without a pad script or LAB batch export` is a *soft* setup signal: with PASS
lines it is a note, with a timeout it names the cause. The harness footer lines `exit N` and
`FATAL 0` of `*.run.txt` are parsed as exit code, not as faults.

## Crash and sweep triage (`triage_run.py`)

```powershell
python tools/jev/triage_run.py _build/sweep/results.json --offline
python tools/jev/triage_run.py _build/sweep/runs/vanilla-st-fountain
python tools/jev/triage_run.py crash-report.log
```

1. `runparse` first. A decided class is returned with `source: code` and never leaves the machine.
2. The unused-stage rule (`known_issues.json`, stages akaneia/icetop) and the load-progress HANG
   rule stay code rules (`source: rule`).
3. Only a `fault` reaches Jev: one Choice over the code-extracted crash signature (fault line,
   locations, last 10 non-noise lines, crash log head; at most about 2 KB, redacted), options from
   `known_issues.json` (`what`, `not_for`, `examples`, plus `none_of_the_above`). It is asked in
   forward and reversed option order in one request. Disagreement, or confidence under the floor,
   gives `needs_human`. Each entry's `label` is what `choice` reports (`mod_content`,
   `script_bug`, `real_bug`, `known_issue`). `match` regexes in the table drive only the offline stub.
4. The sweep's `--jev` flag and the crash-upload service call `classify(row, log_text)` and get
   the same dict (`choice`, `band`, `source`, plus `parse`).

Edit `known_issues.json` to add an option: write `what`/`not_for`/`examples` as you would brief a
colleague; add a `label`.

## Requirement coverage (`coverage.py`)

```powershell
python tools/jev/coverage.py brief.md report.md --offline
```

Brief: one requirement per line, or a checklist / numbered / bulleted list. For each requirement code
retrieves up to four report lines by IDF-weighted token overlap (plus lines citing the item as `#N`);
then three Noul questions are asked with only those lines as state: *completed*, *concrete
evidence*, *states it is NOT done / owed*. A requirement that shares no word with the report is
`unaddressed` without a model call (a paraphrase with no shared word lands there: read those). The
state also lists requirement words absent from the whole report. Combination is in code
(`combine`): done = completed + evidence + not owed; owed = owed and not completed; completed with no
evidence or both completed and owed = `unclear`; any answer between the Noul thresholds is
`needs_human_read`. Payload per requirement: the requirement plus under 1.6 KB of report text.

## Confidence routing (`confidence.py`)

Shared by all tools. Choice/Score `confidence` bands: below the floor `human`, floor to act `confirm`,
at/above act `act` (defaults 0.6 / 0.85 for Choice, 0.5 / 0.8 for Score, from the docs' own banking
example). Noul: yes at p >= 0.8, no at p <= 0.2, otherwise `unsure`. **These defaults are
conservative and NOT calibrated on this repo's data**: collect labelled runs, plot confidence
against accuracy, then set them. Override per call (`thresholds=`) or with env `JEV_THRESHOLDS`
(JSON object or path to a JSON file); an unreadable override is ignored.

## Local evaluation (`eval_local.py`)

`python tools/jev/eval_local.py [--live]` replays the 2026-10-09 artifacts with known truth (needs
the main checkout's untracked `_build/`). Offline it scores the code layer only; the coverage
statuses it prints offline come from a keyword stub, not Jev. `--live` needs `TYPESAFE_API_KEY`.

## TypeSafe agent skill (not installed by this repo)

The docs (docs.typesafe.ai/agent-skill) give a local install that needs no account or key (a key is
only needed if the agent should run test queries). It changes your agent configuration, so run it
yourself:

```bash
claude plugin marketplace add typesafe-ai/skills
claude plugin install typesafe@typesafe-ai      # then /typesafe:typesafe-ai
# other agents (Codex etc.): npx skills add typesafe-ai/skills --skill typesafe-ai   (-g for global)
```

Use one method only. Update: `claude plugin marketplace update typesafe-ai` then
`claude plugin update typesafe@typesafe-ai`.

## Review finding ranking

```powershell
python tools/jev/rank_findings.py findings.txt --offline
Get-Content findings.txt | python tools/jev/rank_findings.py
```

Findings start with `N. SEVERITY, file:line ... scenario`; continuation lines stay
with their finding. Jev scores each finding on the ordered rubric 0 cosmetic,
1 wrong result, 2 stuck player, 3 online desync, 4 crash/data loss. Output sorts
descending by score, keeps ties in original order, and displays the score beside
the original reviewer severity and finding text. `--json` exposes distributions,
confidence, and source. Finding input to the API is limited to 4 KB per finding;
local output preserves its full text with privacy redaction.

## Agent claim checks (`check_claims.py`)

```powershell
python tools/jev/check_claims.py report.txt build.log test.log _build/runs/foo --offline
```

Use `-` for the report to read stdin. Claims recognised: `N/N tests pass`, `build OK`, `all runs PASS`,
`shown in game`, `no window opened`. Test, build and run claims are decided in code (`source: code`;
run claims through `runparse` on the given run dirs) and never sent to Jev. Only the semantic claims
(shown in game, no window) get two Noul questions (support, contradiction) with just their own claim
and snippets (2 KB, redacted) as state, gated by `confidence.noul_state`; an unsure answer sets
`needs_human_read`. A claim with no relevant log lines stays `no evidence`. Logs are not
authenticated: the caller must supply the correct run's logs. Absence of window messages cannot
prove no window opened. With `--history-dir`, exact repeats of earlier reports are flagged by SHA-256.
Recognition is limited to these forms; use `coverage.py` for free-text requirements.

## Crash-upload service

`tools/netplay/server/README.md` points to the separate
`tools/release/crash_upload_server.py`. Its `--jev` setting defaults off.
When enabled, its storage function adds the same classifier's answer to the
existing metadata JSON; classification runs in a worker thread and an unavailable
classifier does not reject the upload. Deploy the `tools/jev/` directory in the
same repository layout and supply the key to the service environment. A standalone
copy without the module records `jev: unavailable`. `--jev --jev-offline` uses
the stub; embedded users can pass `jev_enabled=True` to `start_crash_upload`.
No deployment was performed by this change. Enabling it opts the service into
sending up to 4 KB of each redacted compact report to TypeSafe.

For manual classification of existing service reports:

```powershell
python tools/jev/triage_run.py path/to/stored-report.log
```

## Verification

```powershell
python -m unittest discover -s tools/jev -p 'test_*.py'
python -m unittest discover -s tools/sweep -p 'test_*.py'
python -m unittest discover -s tools/netplay/server -p 'test_*.py'
```

Tests use synthetic logs and deterministic stubs, plus mocked transport failures
to exercise retries and invalid responses. They require neither a key nor external
network access; HTTP integration checks use loopback sockets only.
TypeSafe is credited in the root `CREDITS.md`.

## Earlier helpers

The existing `triage_runs.py`, `rank_chunks.py`, and `rerank_files.py` remain
available; they predate the shared client and do not offer this offline/fallback
contract. Their entry points are:

```text
python tools/jev/triage_runs.py RUNS_FOLDER [--pattern GLOB] [--limit N]
python tools/jev/rank_chunks.py --goal GOAL --chunks findings.tsv [--top N]
python tools/jev/rerank_files.py --task TASK --candidates shortlist.tsv --root ROOT [--top N]
```

`triage_runs.py` produces `jev-triage.md`/`.json` in the runs folder, using test
and script verdict lines instead of raw teardown noise. Aurora's final device-loss
messages may describe normal exit, so they alone do not establish a crash.
The earlier accuracy records are `_build/agents/batcha/jev-triage-2026-09-28.md`
and `jev-triage-v2-2026-09-28.md` (local artifacts, not current verification).
`rank_chunks.py` consumes `label<TAB>text` lines and writes `rank_chunks.md`/`.json`;
`rerank_files.py` consumes `path<TAB>description` lines and writes
`jev-rerank.md`/`.json` beside its input. Use the new tools above for offline tests
and bounded/redacted API input. Do not source the whole workspace `.env`.
