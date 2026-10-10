"""Entry point for blender --python bootstrap.py -- --project P --port N."""

import argparse
from pathlib import Path
import sys


def _script_arguments(argv):
    if "--" not in argv:
        return []
    return argv[argv.index("--") + 1:]


def main(argv=None):
    package_parent = str(Path(__file__).resolve().parent.parent)
    if package_parent not in sys.path:
        sys.path.insert(0, package_parent)

    import bpy
    import geno_workbench

    from geno_workbench import api
    from geno_workbench.props import STRINGS

    parser = argparse.ArgumentParser(
        description=STRINGS["bootstrap_description"]
    )
    parser.add_argument(
        "--project",
        required=True,
        help=STRINGS["project_argument"],
    )
    parser.add_argument(
        "--port",
        required=True,
        type=int,
        help=STRINGS["port_argument"],
    )
    arguments = _script_arguments(sys.argv) if argv is None else argv
    args = parser.parse_args(arguments)

    if not 1 <= args.port <= 65535:
        parser.error(STRINGS["invalid_port"])

    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        parser.error(STRINGS["invalid_project"].format(path=project))

    geno_workbench.register()
    settings = bpy.context.scene.geno_wb
    settings.project = str(project)
    settings.host = "127.0.0.1"
    settings.port = args.port

    result = bpy.ops.geno_wb.connect()
    if "FINISHED" not in result:
        raise RuntimeError(
            api.session().last_error or STRINGS["bootstrap_connect_failed"]
        )

    if hasattr(bpy.ops.geno_wb, "load_fighter"):
        load_fighter = bpy.ops.geno_wb.load_fighter
        try:
            load_fighter.get_rna_type()
        except (AttributeError, KeyError, RuntimeError):
            # bpy.ops can fabricate an attribute for an unregistered operator.
            # Task 6 must also work before Task 7 supplies load_fighter.
            return

        result = load_fighter()
        if "FINISHED" not in result:
            raise RuntimeError(
                api.session().last_error or STRINGS["bootstrap_fighter_failed"]
            )


if __name__ == "__main__":
    main()
