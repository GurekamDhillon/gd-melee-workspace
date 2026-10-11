"""Edit one projectile in Blender and write it through the Workbench server (the add-on's own Apply path).

    blender -b --factory-startup --python edit_projectile.py -- --port N --article KameOrb [--velocity F U] [--lifetime N]
                                                                [--gravity G] [--spawn F U]

Loads the project's articles over the server, builds the Projectiles collection, edits the named object's properties
(what an artist does in the N panel), and applies the diff with edit_article.  Prints EDIT lines; exit 1 on failure.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import bpy  # noqa: E402,F401
from geno_workbench import api, client, projectiles_bpy as PB  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, required=True)
ap.add_argument("--article", required=True)
ap.add_argument("--velocity", type=float, nargs=2)
ap.add_argument("--lifetime", type=int)
ap.add_argument("--gravity", type=float)
ap.add_argument("--spawn", type=float, nargs=2)
args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])

sess = api.WbSession(lambda: client.McpClient(port=args.port, timeout=10.0))
if not (sess.connect() and sess.refresh_projectiles()):
    print("EDIT FAIL", sess.last_error)
    raise SystemExit(1)
PB.import_articles(sess.articles)
obj = bpy.data.objects.get("Proj." + args.article)
if obj is None:
    print("EDIT FAIL no such projectile", args.article)
    raise SystemExit(1)
if args.velocity:
    obj["gp_velocity_0"], obj["gp_velocity_1"] = args.velocity
if args.lifetime is not None:
    obj["gp_lifetime"] = args.lifetime
if args.gravity is not None:
    obj["gp_gravity"] = args.gravity
if args.spawn:
    obj.location = PB._to_b(args.spawn[0], args.spawn[1])
plan = PB.pending_ops(sess.articles)
print("EDIT ops", plan["edits"])
for index, ops in plan["edits"].items():
    if not sess.edit_article(index, ops):
        print("EDIT FAIL", sess.last_error)
        raise SystemExit(1)
print("EDIT OK", sess.status)
