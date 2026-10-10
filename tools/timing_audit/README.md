# timing_audit

Local-only audit of animation-length / actionability for ported fighters vs the native roster.

    source .env
    python tools/timing_audit/audit.py     # data.json: native (25 fighters, no Kirby), Goku, Meta Knight, Sora, state classes
    python tools/timing_audit/report.py    # _build/timing-audit/actionability.md
    tools/timing_audit/probe/              # Lua ledge probe (mod ledge-timing) + run scripts; copy into a mods dir with geno-lab

Everything it reads is disc- or package-derived and stays under `_build/`; nothing here embeds that data.
