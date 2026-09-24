#!/usr/bin/env python3
"""Merge every run sandbox's aurora pipeline cache into one seed: _build/initial_pipeline_cache.db.

Aurora compiles a render pipeline the first time a draw needs one, so a match on a cold cache pops
in piece by piece. It also loads a read-only seed, `initial_pipeline_cache.db` next to the exe
(aurora's resourcesPath), and warms every pipeline in it in the background; the loading screen
holds until that queue is empty (gw_Gfx_PipelinesPending counts background warm-ups too). A seed
built from a full sweep - every stage and every fighter on every disc - therefore means a fresh
install drops into a match with its pipelines already built.

  python tools/port/build_pipeline_seed.py            # after a sweep

ORDER MATTERS MORE THAN SIZE. Aurora warms the seed in first_frame_used order, and warming all of
it takes minutes. One match uses ~90 pipelines spread across the whole seed, so a first-use order
is useless for "the next match". What does work is commonness: ~180 pipelines (those used by at
least 5% of the sweep's runs) cover about three quarters of a typical match. So first_frame_used is
rewritten to a rank by how many runs used the pipeline, the core compiles first, and its size goes
to initial_pipeline_cache.core for the loading screen to wait on (gw_Gfx_SeedCoreCount).
"""
import collections
import glob
import os
import sqlite3
import sys

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
build = os.path.join(root, "_build")
out = os.path.join(build, "initial_pipeline_cache.db")
tmp = out + ".tmp"

sources = sorted(glob.glob(os.path.join(build, "runs", "*", "pipeline_cache.db")))
# Extra sandbox roots (e.g. a lane's _build/agents/<lane>/runs) as arguments.
for extra in sys.argv[1:]:
    sources += sorted(glob.glob(os.path.join(extra, "*", "pipeline_cache.db")))
if not sources:
    sys.exit("no _build/runs/*/pipeline_cache.db to merge - run a sweep first")

if os.path.exists(tmp):
    os.remove(tmp)
db = sqlite3.connect(tmp)
schema = None
freq = collections.Counter()
n_runs = 0
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
        for name, sql in ddl:
            if name != "pipeline_tags":
                db.execute(sql)
        db.execute("INSERT INTO aurora_schema VALUES (?)", ver)
        # Tag bits per pipeline (AURORA_PIPELINE_TAG_*: 1 = drawn by an item model, which the
        # match loading screen prewarms). A side table, so older caches without it still merge.
        db.execute("CREATE TABLE pipeline_tags (type INTEGER NOT NULL, hash INTEGER NOT NULL, "
                   "tags INTEGER NOT NULL, PRIMARY KEY (type, hash))")
    elif ver != schema:
        s.close()
        continue
    try:
        tags = s.execute("SELECT type, hash, tags FROM pipeline_tags").fetchall()
    except sqlite3.DatabaseError:
        tags = []
    db.executemany("INSERT INTO pipeline_tags VALUES (?,?,?) ON CONFLICT(type, hash) DO UPDATE SET "
                   "tags = tags | excluded.tags", tags)
    rows = s.execute("SELECT type, hash, config_version, config_size, config, first_frame_used "
                     "FROM pipeline_cache").fetchall()
    if rows:
        n_runs += 1
        freq.update(set((r[0], r[1]) for r in rows))
    # Keep the earliest first use: aurora warms in that order, so what a match draws first builds first.
    db.executemany("INSERT INTO pipeline_cache VALUES (?,?,?,?,?,?) "
                   "ON CONFLICT(type, hash) DO UPDATE SET "
                   "first_frame_used = MIN(first_frame_used, excluded.first_frame_used)", rows)
    s.close()
db.commit()
# Re-rank: most-used first (ties keep their earliest first use), so aurora warms the core first.
ranked = db.execute("SELECT type, hash, first_frame_used FROM pipeline_cache").fetchall()
ranked.sort(key=lambda r: (-freq[(r[0], r[1])], r[2]))
db.executemany("UPDATE pipeline_cache SET first_frame_used = ? WHERE type = ? AND hash = ?",
               [(i, r[0], r[1]) for i, r in enumerate(ranked)])
core = sum(1 for r in ranked if freq[(r[0], r[1])] >= 0.05 * max(n_runs, 1))
db.commit()
n = db.execute("SELECT COUNT(*) FROM pipeline_cache").fetchone()[0]
n_tagged = db.execute("SELECT COUNT(*) FROM pipeline_tags t JOIN pipeline_cache c "
                      "ON c.type = t.type AND c.hash = t.hash WHERE t.tags & 1").fetchone()[0]
db.execute("VACUUM")
db.close()
os.replace(tmp, out)
with open(os.path.join(build, "initial_pipeline_cache.core"), "w") as f:
    f.write("%d\n" % core)
print("seed: %d pipelines from %d caches (%d runs), core %d, item-tagged %d -> %s" % (
    n, len(sources), n_runs, core, n_tagged, out))
