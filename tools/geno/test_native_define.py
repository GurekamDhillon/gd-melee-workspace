"""Standalone C contracts; builds only synthetic tests, never the game."""
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class NativeDefineTests(unittest.TestCase):
    def test_synthetic_native_core(self):
        kits = Path(os.environ.get("ProgramFiles(x86)", "")) / "Windows Kits/10"
        compilers = sorted(Path(os.environ.get("ProgramFiles", "")).glob("Microsoft Visual Studio/*/*/VC/Tools/MSVC/*/bin/Hostx64/x64/cl.exe"))
        sdks = sorted((kits / "Include").glob("*"))
        if not compilers or not sdks: self.skipTest("MSVC/SDK unavailable")
        compiler, sdk = compilers[-1], sdks[-1]; vc = compiler.parents[3]
        out = ROOT / "_build/tmp/geno-define-tests"; out.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy(); env["PATH"] = str(compiler.parent)+os.pathsep+env.get("PATH", "")
        args = [str(compiler), "/nologo", "/TC", "/std:c11", "/W3",
            *["/I"+str(p) for p in (vc/"include", sdk/"ucrt", sdk/"shared", sdk/"um")],
            "melee/pc/tests/geno_define_core_test.c", "/Fo"+str(out/"core.obj"), "/Fe"+str(out/"core.next.exe"),
            "/link", *["/LIBPATH:"+str(p) for p in (vc/"lib/x64", kits/"Lib"/sdk.name/"ucrt/x64", kits/"Lib"/sdk.name/"um/x64")]]
        result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, timeout=60)
        # Diagnostics are private local artifacts, never echoed with host paths.
        (out/"compile.txt").write_bytes(result.stdout+result.stderr)
        self.assertEqual(result.returncode, 0, "standalone C compilation failed; inspect local diagnostics")
        result = subprocess.run([str(out/"core.next.exe")], cwd=ROOT, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, "standalone catalogue/article contract failed")
        self.assertIn(b"PASS", result.stdout)


if __name__ == "__main__": unittest.main()
