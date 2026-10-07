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

## Crash and sweep triage

```powershell
python tools/jev/triage_run.py _build/sweep/results.json --offline
python tools/jev/triage_run.py _build/sweep/runs/vanilla-st-fountain
python tools/jev/triage_run.py crash-report.log
```

The JSON input is the list emitted by `tools/sweep/crash_sweep.py`. Each non-PASS
row is classified as `real_bug`, `known_issue`, or `harness_artifact` using its
`sandbox` field, or `runs/<tag>` beside the JSON for older results. PASS rows are
skipped. A directory input has no harness verdict; it is classified as an unknown
failure unless its tail has crash evidence. A compact crash-report file is also
accepted for uploaded reports.

At most 4096 UTF-8 bytes of combined log tails are sent per run: roughly half
`melee-pc.log`, half the newest text `crashlogs/*.log`. Binary dumps are excluded.
Absolute paths and credential assignments are redacted before transmission.
Run metadata fields are also bounded and redacted. Log text is treated as
untrusted data. Edit `known_issues.json`, or pass `--known-issues TABLE.json`.
The unused **stage** names `akaneia`/`icetop` are distinct from the Akaneia disc.
Load-induced timeouts require progressing logic **and** presentation plus no
fault evidence. A tail cannot establish that an earlier freeze never happened;
read full logs before accepting any artifact classification.

The sweep's optional `--jev` flag annotates `results.json` and adds a `triage`
column to `results.md` after all games have finished. It does not change results
or exit status. Test the writer independently without running the sweep:

```powershell
python -m unittest discover -s tools/jev -p 'test_integrations.py'
```

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

## Agent claim checks

```powershell
python tools/jev/check_claims.py report.txt build.log test.log --offline
python tools/jev/check_claims.py report.txt build.log --history-dir _build/jev-reports
```

Use `-` for the report to read stdin. Extracted claims include `N/N tests pass`,
`build OK`, `shown in game`, and `no window opened`. The tool scans logs for
relevant lines and sends only the latest redacted snippets (2 KB per claim).
Each evidenced claim gets two nouls: explicit support and explicit contradiction.
Contradiction >= 0.8 means `unsupported`; support >= 0.8 with contradiction <= 0.2
means `supported`; all other outcomes mean `no evidence`. A claim with no relevant
lines stays `no evidence` without a request. Missing log files provide no evidence.
Logs are not authenticated: the caller must supply the correct run's logs.
An absence of window messages cannot prove no window opened; a heartbeat does not
prove the game was shown or visually inspected. Recognition is intentionally
limited to the documented claim forms, not a general agent-report verifier.

With `--history-dir`, exact report content is checked against earlier `.md`/`.txt`
reports in that folder and a `.jev-report-sha256.json` hash history. The current
report file is excluded from the comparison. This works independently of Jev;
only SHA-256 hashes are stored. History access should be serialized by the caller.

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
