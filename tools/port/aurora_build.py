#!/usr/bin/env python3
"""Build Aurora only when its source/configuration or required outputs changed."""
import argparse
import filecmp
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


LIBRARIES = ("core", "gx", "main", "vi", "os", "pad", "si", "card", "mtx", "gd", "ms")


def tree_hash(source):
    digest = hashlib.sha256()
    for base, dirs, files in os.walk(source):
        dirs[:] = sorted(d for d in dirs if d not in {".git", "build", "__pycache__"})
        for name in sorted(files):
            path = Path(base) / name
            if name == ".git":
                continue
            digest.update(path.relative_to(source).as_posix().encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def ensure(source, stamp, outputs, config, builder):
    key = {"source": str(source.resolve()), "tree": tree_hash(source), "config": config}
    try:
        saved = json.loads(stamp.read_text())
    except (OSError, ValueError):
        saved = {}
    if saved == key and all(p.is_file() for p in outputs):
        print(f"aurora    up to date ({stamp.parent})", flush=True)
        return False
    reason = "inputs changed" if saved else "no successful build stamp"
    if any(not p.is_file() for p in outputs):
        reason = "missing libraries"
    print(f"aurora    rebuild: {reason} -> {stamp.parent}", flush=True)
    # A failed/interrupted build must never leave a success stamp for partial libs.
    stamp.unlink(missing_ok=True)
    # A content-key change is stronger evidence than Ninja's mtimes. Branches
    # created by agent_new can have changed but backdated sources/headers. Remove
    # Aurora and its bundled extern objects, retaining the large fetched-dependency
    # build trees. Everything removed lives under this build root, never in sources.
    for base, dirs, files in os.walk(stamp.parent):
        if Path(base) == stamp.parent:
            dirs[:] = [d for d in dirs if d != "_deps"]
        for name in files:
            if Path(name).suffix in {".obj", ".o"}:
                (Path(base) / name).unlink()
    builder()
    missing = [str(p) for p in outputs if not p.is_file()]
    if missing:
        raise RuntimeError("Aurora build did not produce: " + ", ".join(missing))
    if tree_hash(source) != key["tree"]:
        raise RuntimeError("Aurora source changed during the build; rebuild")
    temporary = stamp.with_suffix(".tmp")
    temporary.write_text(json.dumps(key, indent=2) + "\n")
    temporary.replace(stamp)
    print(f"aurora    rebuilt {len(outputs)} libraries", flush=True)
    return True


def seed_dependencies(build, caches):
    """Copy source caches, never configure/build/patch inside another lane."""
    options = []
    seen = set()
    for cache in caches:
        for source in sorted(cache.glob("*-src")):
            if not source.is_dir() or source.name in seen:
                continue
            seen.add(source.name)
            target = build / "_deps" / source.name
            if not target.is_dir():
                print(f"aurora    copying dependency source {source.name}", flush=True)
                staging = target.with_name(target.name + ".pending")
                if staging.exists():
                    if not staging.resolve().is_relative_to(build.resolve()):
                        raise RuntimeError(f"dependency staging directory escapes build root: {staging}")
                    shutil.rmtree(staging)
                shutil.copytree(source, staging)
                staging.rename(target)
            dependency = source.name.removesuffix("-src").upper()
            options.append(f'set(FETCHCONTENT_SOURCE_DIR_{dependency} "{target.as_posix()}" CACHE PATH "" FORCE)')
    preload = build / "source-cache.cmake"
    preload.write_text("\n".join(options) + "\n")


def windows_link_inputs(template, build):
    entries = []
    for line in template.read_text().splitlines():
        item = line.strip().strip('"').replace("\\", "/")
        if not item:
            continue
        if item.startswith("../ax86/_deps/"):
            item = item.removeprefix("../ax86/")
        if item.startswith("aurora_") or "/" in item:
            entries.append(build / item)
        else:
            entries.append(item)  # system libraries and linker switches
    return entries


def windows_link_libraries(template, build):
    entries = []
    for item in windows_link_inputs(template, build):
        if isinstance(item, Path):
            if not item.is_file():
                raise RuntimeError(f"missing private Aurora link input: {item}")
            entries.append('"' + item.as_posix() + '"')
        else:
            entries.append(item)
    return "\n".join(entries) + "\n"


def linux_link_inputs(build):
    """The example carries Aurora's resolved transitive dependencies."""
    ninja = build / "build.ninja"
    if not ninja.is_file():
        return []
    lines = ninja.read_text().splitlines()
    edge = next((i for i, s in enumerate(lines) if s.startswith("build examples/simple: ")), None)
    if edge is None:
        return []
    linkline = next((s.split(" = ", 1)[1] for s in lines[edge + 1:edge + 15]
                     if s.startswith("  LINK_LIBRARIES = ")), "")
    paths = []
    for word in linkline.replace("$ ", "\0").split():
        word = word.replace("\0", " ").replace("$$", "$").strip('"')
        if not word.startswith("-"):
            path = Path(word)
            paths.append(path if path.is_absolute() else build / path)
    return paths


def runtime_sources(build):
    return (build / "_deps/sdl3_prebuilt-src/bin/SDL3.dll",
            build / "_deps/dawn-build/webgpu_dawn.dll")


def stage_runtime(build, lane):
    for source in runtime_sources(build):
        target = lane / source.name
        if not target.is_file() or not filecmp.cmp(source, target, shallow=False):
            temporary = target.with_suffix(".dll.tmp")
            shutil.copy2(source, temporary)
            temporary.replace(target)
            print(f"aurora    staged {source.name}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("windows", "linux"), required=True)
    args = parser.parse_args()
    root = Path(os.environ["GW_ROOT"]).resolve()
    melee = Path(os.environ["GW_MELEE"]).resolve()
    lane = Path(os.environ["GW_BUILD_ROOT"]).resolve()
    variable = "GW_AURORA_BUILD" if args.platform == "windows" else "GW_AURORA_LINUX_BUILD"
    build = Path(os.environ.get(variable, str(lane / "ax86m"))).resolve()
    if not build.is_relative_to(lane):
        raise RuntimeError(f"{variable} must be inside GW_BUILD_ROOT: {build}")
    source = melee / "extern/aurora"
    if not (source / "CMakeLists.txt").is_file():
        raise RuntimeError(f"no Aurora source at {source}")
    build.mkdir(parents=True, exist_ok=True)
    port = root / "tools/port"
    recipe = port / ("build_aurora_windows.bat" if args.platform == "windows" else "build_aurora_linux.sh")
    variables = ("GW_CLANG", "GW_CLANGXX", "GW_VCVARSALL", "GW_VSDIR", "GW_AURORA_CPUFLAGS", "GW_DEPS_SOURCE_CACHE")
    config = json.dumps({"platform": args.platform,
                         "recipe": hashlib.sha256(recipe.read_bytes()).hexdigest(),
                         "driver": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                         "env": {v: os.environ.get(v) for v in variables}}, sort_keys=True)
    suffix, prefix = (".lib", "") if args.platform == "windows" else (".a", "lib")
    outputs = [build / f"{prefix}aurora_{name}{suffix}" for name in LIBRARIES]
    if args.platform == "windows":
        outputs.extend(runtime_sources(build))
        outputs.extend(p for p in windows_link_inputs(root / "_build/melee_link_libs.rsp", build)
                       if isinstance(p, Path))
    else:
        outputs.extend(linux_link_inputs(build))
    outputs = list(dict.fromkeys(outputs))

    def compile_aurora():
        env = dict(os.environ, GW_AURORA_BUILD=build.as_posix(), GW_AURORA_LINUX_BUILD=build.as_posix())
        if args.platform == "windows":
            cache = Path(os.environ.get("GW_DEPS_SOURCE_CACHE", str(root / "_build/ax86m/_deps")))
            seed_dependencies(build, [cache, cache.parent.parent / "ax86/_deps"])
            subprocess.run(["cmd.exe", "/d", "/c", str(recipe)], env=env, check=True)
        else:
            caches = [Path(os.environ["GW_DEPS_SOURCE_CACHE"])] if os.environ.get("GW_DEPS_SOURCE_CACHE") else []
            seed_dependencies(build, caches)
            subprocess.run(["bash", str(recipe), "--build"], env=env, check=True)

    ensure(source, build / ".aurora.json", outputs, config, compile_aurora)
    if args.platform == "windows":
        response = windows_link_libraries(root / "_build/melee_link_libs.rsp", build)
        (lane / ".aurora_link_libs.rsp").write_text(response)
        stage_runtime(build, lane)


if __name__ == "__main__":
    main()
