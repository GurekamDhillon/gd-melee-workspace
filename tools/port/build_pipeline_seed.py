#!/usr/bin/env python3
"""Merge every run sandbox's aurora pipeline cache into one seed: _build/initial_pipeline_cache.db.

Aurora compiles a render pipeline the first time a draw needs one, so a match on a cold cache pops
in piece by piece. It also loads a read-only seed, `initial_pipeline_cache.db` next to the exe
(aurora's resourcesPath), and warms every pipeline in it in the background; the loading screen
holds until that queue is empty (gw_Gfx_PipelinesPending counts background warm-ups too). A seed
built from a full sweep - every stage and every fighter on every disc - therefore means a fresh
install drops into a match with its pipelines already built.

  python tools/port/build_pipeline_seed.py            # after a sweep
"""
import glob
import os
import sqlite3
import sys

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
build = os.path.join(root, "_build")
out = os.path.join(build, "initial_pipeline_cache.db")
tmp = out + ".tmp"

sources = sorted(glob.glob(os.path.join(build, "runs", "*", "pipeline_cache.db")))
if not sources:
    sys.exit("no _build/runs/*/pipeline_cache.db to merge - run a sweep first")

if os.path.exists(tmp):
    os.remove(tmp)
db = sqlite3.connect(tmp)
schema = None
for src in sources:
    s = sqlite3.connect("file:%s?mode=ro" % src.replace("\\", "/"), uri=True)
    try:
        ver = s.execute("SELECT value FROM aurora_schema").fetchone()
        ddl = s.execute("SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL").fetchall()
    except sqlite3.DatabaseError:
        s.close()
        continue
    if schema is None:
        schema = ver
        for _, sql in ddl:
            db.execute(sql)
        db.execute("INSERT INTO aurora_schema VALUES (?)", ver)
    elif ver != schema:
        s.close()
        continue
    rows = s.execute("SELECT type, hash, config_version, config_size, config, first_frame_used "
                     "FROM pipeline_cache").fetchall()
    # Keep the earliest first use: aurora warms in that order, so what a match draws first builds first.
    db.executemany("INSERT INTO pipeline_cache VALUES (?,?,?,?,?,?) "
                   "ON CONFLICT(type, hash) DO UPDATE SET "
                   "first_frame_used = MIN(first_frame_used, excluded.first_frame_used)", rows)
    s.close()
db.commit()
n = db.execute("SELECT COUNT(*) FROM pipeline_cache").fetchone()[0]
db.execute("VACUUM")
db.close()
os.replace(tmp, out)
print("seed: %d pipelines from %d caches -> %s" % (n, len(sources), out))
