#!/usr/bin/env python3
"""Merge pipeline caches or export a no-launch coverage sweep.

python tools/port/build_pipeline_seed.py [cache.db | sandbox-root ...]
python tools/port/build_pipeline_seed.py --sweep-plan _build/pipeline-sweep --disc ace --probe-log <existing boot log> --items-json <runtime roster.json>

Inputs are read-only. Unique nonempty compatible caches count as runs. Common
keys are ranked first; tags and learned origin identities survive merging.
Sweep export writes a plan and Lua driver only: it never starts a game.
"""
import argparse
import collections
from contextlib import closing
from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT=ROOT/'_build/initial_pipeline_cache.db'


def discover_sources(inputs=(),include_default=True):
    paths=list(inputs)
    if include_default and (ROOT/'_build/runs').is_dir():paths.append(ROOT/'_build/runs')
    found=set()
    for value in paths:
        path=Path(value)
        if path.is_file():found.add(path.resolve())
        elif path.is_dir():found.update(p.resolve() for p in path.rglob('pipeline_cache.db'))
        else:raise ValueError('cache input does not exist: '+str(path))
    return sorted(found)


def merge_caches(sources,output):
    output=Path(output);tmp=output.with_name(output.name+'.tmp')
    output.parent.mkdir(parents=True,exist_ok=True)
    if tmp.exists():tmp.unlink()
    db=sqlite3.connect(tmp);schema=None;freq=collections.Counter();runs=0;accepted=0
    try:
        for src in sorted({Path(p).resolve() for p in sources}):
            if src==output.resolve():raise ValueError('output seed cannot also be an input')
            with closing(sqlite3.connect(src.as_uri()+'?mode=ro',uri=True)) as source:
                try:
                    ver=source.execute('SELECT value FROM aurora_schema').fetchone()
                    rows=source.execute('SELECT type,hash,config_version,config_size,config,first_frame_used FROM pipeline_cache').fetchall()
                except sqlite3.DatabaseError:continue
                if not ver or not rows:continue
                if schema is not None and ver!=schema:continue
                if schema is None:
                    schema=ver
                    for table in ('aurora_schema','pipeline_cache'):
                        ddl=source.execute('SELECT sql FROM sqlite_master WHERE type=\'table\' AND name=?',(table,)).fetchone()
                        if not ddl:raise ValueError('missing table '+table)
                        db.execute(ddl[0])
                    db.execute('INSERT INTO aurora_schema VALUES (?)',ver)
                    db.execute('CREATE TABLE pipeline_tags(type INTEGER,hash INTEGER,tags INTEGER,PRIMARY KEY(type,hash))')
                    db.execute('CREATE TABLE pipeline_origins(type INTEGER,hash INTEGER,origin TEXT,PRIMARY KEY(type,hash,origin))')
                runs+=1;accepted+=1;freq.update({(r[0],r[1]) for r in rows})
                db.executemany('INSERT INTO pipeline_cache(type,hash,config_version,config_size,config,first_frame_used) VALUES (?,?,?,?,?,?) ON CONFLICT(type,hash) DO UPDATE SET first_frame_used=MIN(first_frame_used,excluded.first_frame_used)',rows)
                for table,columns,sql in (
                    ('pipeline_tags','type,hash,tags','INSERT INTO pipeline_tags VALUES (?,?,?) ON CONFLICT(type,hash) DO UPDATE SET tags=tags | excluded.tags'),
                    ('pipeline_origins','type,hash,origin','INSERT OR IGNORE INTO pipeline_origins VALUES (?,?,?)')):
                    try:metadata=source.execute('SELECT '+columns+' FROM '+table).fetchall()
                    except sqlite3.DatabaseError:metadata=[]
                    db.executemany(sql,metadata)
        if not runs:raise ValueError('no nonempty compatible pipeline caches; existing seed preserved')
        ranked=db.execute('SELECT type,hash,first_frame_used FROM pipeline_cache').fetchall()
        ranked.sort(key=lambda row:(-freq[(row[0],row[1])],row[2],row[0],row[1]))
        db.executemany('UPDATE pipeline_cache SET first_frame_used=? WHERE type=? AND hash=?',[(i,row[0],row[1]) for i,row in enumerate(ranked)])
        core=sum(freq[(r[0],r[1])]>=0.05*runs for r in ranked)
        tagged=db.execute('SELECT COUNT(*) FROM pipeline_tags t JOIN pipeline_cache c ON c.type=t.type AND c.hash=t.hash WHERE t.tags & 1').fetchone()[0]
        origins=db.execute('SELECT COUNT(*) FROM pipeline_origins o JOIN pipeline_cache c ON c.type=o.type AND c.hash=o.hash').fetchone()[0]
        db.commit();db.execute('VACUUM');db.close();db=None
        tmp.replace(output)
        output.with_suffix('.core').write_text(str(core)+'\n')
        return dict(pipelines=len(ranked),runs=runs,caches=accepted,core=core,tagged=tagged,origins=origins)
    finally:
        if db is not None:db.close()
        if tmp.exists():tmp.unlink()


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('inputs',nargs='*',help='explicit .db paths or recursively scanned cache roots')
    ap.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    ap.add_argument('--no-default-runs',action='store_true')
    ap.add_argument('--sweep-plan',type=Path,help='export stage/content sweep driver here; no launch')
    ap.add_argument('--disc',choices=('vanilla','ace','akaneia'),default='vanilla')
    ap.add_argument('--probe-log',type=Path,help='existing runtime boot log with dynamic external stage count')
    ap.add_argument('--items-json',type=Path,help='runtime-discovered item list, or {items:[...]}')
    ap.add_argument('--seconds',type=int,default=24)
    args=ap.parse_args(argv)
    if args.sweep_plan:
        import json
        import pipeline_seed_sweep as sweep
        text=args.probe_log.read_text(encoding='utf-8',errors='replace') if args.probe_log else ''
        items=json.loads(args.items_json.read_text()) if args.items_json else []
        if isinstance(items,dict):items=items['items']
        plan=sweep.make_plan(args.disc,text,items,args.seconds)
        sweep.export_plan(plan,args.sweep_plan)
        print('sweep plan:',args.sweep_plan,'runs',len(plan['runs']),'stage/item roster complete',plan['stage_roster_complete'],plan['item_roster_complete'])
        return 0
    stats=merge_caches(discover_sources(args.inputs,not args.no_default_runs),args.output)
    print('seed:',stats,'->',args.output)
    return 0

if __name__=='__main__':raise SystemExit(main())
