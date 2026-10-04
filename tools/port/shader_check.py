"""Standalone shader contract tests and syntax checks; never builds/launches Melee."""
from pathlib import Path
import os
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
MELEE = ROOT / "melee"
OUT = ROOT / "_build/tmp/shader-check"

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    vs = Path(os.environ.get("GW_SHADER_MSVC", "C:/Program Files/Microsoft Visual Studio/18/Community/VC/Tools/MSVC/14.51.36231"))
    sdk = Path("C:/Program Files (x86)/Windows Kits/10")
    version = "10.0.26100.0"
    env = os.environ.copy()
    env["INCLUDE"] = ";".join(str(p) for p in [vs / "include", *[sdk / "Include" / version / x for x in ("ucrt", "shared", "um")]])
    env["LIB"] = ";".join(str(p) for p in [vs / "lib/x64", sdk / "Lib" / version / "ucrt/x64", sdk / "Lib" / version / "um/x64"])
    compiler = vs / "bin/Hostx64/x64/cl.exe"
    env["PATH"] = str(compiler.parent) + ";" + env["PATH"]
    common = [str(compiler), "/nologo", "/std:c++20", "/EHsc", "/MD", "/DWEBGPU_DAWN"]
    source = MELEE / "pc/tests/shader_contract_test.cpp"
    command = common + [str(source), "/Fo" + str(OUT / "contract.obj"), "/Fe" + str(OUT / "contract.exe")]
    subprocess.run(command, cwd=OUT, env=env, check=True)
    subprocess.run([str(OUT / "contract.exe")], cwd=OUT, env=env, check=True)
    if "--syntax" in sys.argv:
        includes = [MELEE / "pc/platform", MELEE / "extern/aurora/include",
                    ROOT / "_build/ax86/_deps/dawn-src/include",
                    ROOT / "_build/ax86m/_deps/dawn-build/gen/include"]
        subprocess.run(common + ["/Zs", *["/I" + str(p) for p in includes],
                                 str(MELEE / "pc/platform/gw_fx_render.cpp")], env=env, check=True)
        for name in ("gw_fx.c", "gw_script.c"):
            subprocess.run([str(compiler), "/nologo", "/TC", "/std:c11", "/Zs", "/DTARGET_PC",
                            *["/I" + str(p) for p in includes], str(MELEE / "pc/platform" / name)], env=env, check=True)
    if "--runtime" in sys.argv:
        env["LIB"] = env["LIB"].replace("x64", "x86")
        compiler = vs / "bin/Hostx64/x86/cl.exe"
        env["PATH"] = str(compiler.parent) + ";" + str(ROOT / "_build") + ";" + env["PATH"]
        includes = [MELEE / "pc/platform", MELEE / "extern/aurora/include",
                    ROOT / "_build/ax86/_deps/dawn-src/include",
                    ROOT / "_build/ax86m/_deps/dawn-build/gen/include"]
        command = [str(compiler), "/nologo", "/std:c++20", "/EHsc", "/MD", "/Gy", "/Gw", "/DWEBGPU_DAWN",
                   *["/I" + str(p) for p in includes], str(MELEE / "pc/tests/shader_runtime_test.cpp"),
                   "/Fo" + str(OUT / "runtime.obj"), "/Fe" + str(OUT / "runtime.exe"),
                   "/link", "/OPT:REF", "ole32.lib", str(ROOT / "_build/ax86m/_deps/dawn-build/src/dawn/native/webgpu_dawn.lib")]
        subprocess.run(command, cwd=OUT, env=env, check=True)
        fixture = OUT / ("fixture-" + uuid.uuid4().hex)
        contained = fixture / "root"
        outside = fixture / "outside"
        contained.mkdir(parents=True)
        outside.mkdir()
        (contained / "good.wgsl").write_text("return vec4f(1.0);\n")
        (outside / "stolen.wgsl").write_text("return vec4f(0.0);\n")
        # A directory junction needs no symlink privilege. No shell deletion or path moves.
        subprocess.run(["cmd", "/c", "mklink", "/J", str(contained / "junction"), str(outside)], env=env, check=True)
        subprocess.run([str(OUT / "runtime.exe"), str(MELEE / "pc/geno/mods/shader-demo"), str(contained)], cwd=OUT, env=env, check=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
