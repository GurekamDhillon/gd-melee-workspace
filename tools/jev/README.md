# tools/jev

Helpers for [Jev](https://docs.typesafe.ai/llms.txt) (TypeSafe System One) — fast, cheap typed
judgments (`choice` / `score` / `noul`) that code can combine. The API key lives in the workspace
`.env` as `TYPESAFE_API_KEY` (git-ignored — **never commit it**, never paste it into a document).

    set -a; . ./.env; set +a          # from the workspace root

## `triage_runs.py` — classify run logs

    python3 tools/jev/triage_runs.py _build/agents/batcha/runs

One Jev call per run directory (~$0.0001 each, ~0.3 s) with four questions: outcome
(`test_failed` / `test_passed` / `crashed` / `cut_short` / `normal_operation`), a defect-vs-artifact
noul, area, and a 0-4 severity score. Prints a table and writes `jev-triage.md` + `jev-triage.json`
into the runs directory.

Options: `--pattern <glob>` for the log filename (default `melee-pc.log`), `--limit N`.

**State hygiene is the whole game.** The first version fed the raw log tail and every run read as a
crash, because every log ends with the Aurora teardown block (`Device lost`,
`faulted inside Dawn ... ignored at exit`). The tool keeps only test/script verdict lines plus the
final exit line and drops engine/teardown noise; that moved outcome accuracy from 17/19 to 19/19 on
the batcha runs and separated severity cleanly (0 for passes, ~3 for failures). The before/after is
kept for the record in `_build/agents/batcha/jev-triage-2026-09-28.md` (v1) and
`jev-triage-v2-2026-09-28.md` (v2).

Run it after a sweep or a lane test batch; treat `outcome=test_failed` rows as the queue and
`severity` as the order. It is a triage aid, not proof — read the log it points at.
