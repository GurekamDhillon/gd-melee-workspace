"""Keep build-specific bridge and build-id consumers out of the game checkout."""
import argparse
from pathlib import Path


def write_changed(path, body):
    if not path.exists() or path.read_bytes() != body:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(body)
        temporary.replace(path)


def prepare(melee, output):
    output.mkdir(parents=True, exist_ok=True)
    platform = melee / "pc/platform"
    # Preserve our generated table on later builds; the first link only needs a
    # seed table. The link-map fixpoint supplies the final addresses.
    for name in ("gw_mex_bridge.c", "gw_mex_bridge.h"):
        if not (output / name).exists():
            write_changed(output / name, (platform / name).read_bytes())
    consumers = set()
    for source in [*platform.glob("*.c"), *platform.glob("*.cpp")]:
        if source.name == "gw_mex_bridge.c":
            continue
        body = source.read_bytes()
        if b'"gw_build_id.h"' in body or b'"gw_mex_bridge.h"' in body:
            consumers.add(source.name)
            # Quoted includes search the source directory first. Compile a copy
            # of these few consumers beside the generated headers, then use the
            # original platform directory for their other includes.
            write_changed(output / source.name, body)
    for source in [*output.glob("*.c"), *output.glob("*.cpp")]:
        if source.name != "gw_mex_bridge.c" and source.name not in consumers:
            source.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--melee", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.melee, args.output)
