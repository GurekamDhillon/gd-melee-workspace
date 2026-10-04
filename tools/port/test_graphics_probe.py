#!/usr/bin/env python3
"""Verify the 32-bit graphics helper the launcher runs before the Linux game starts.

    python3 tools/port/test_graphics_probe.py [path/to/melee-graphics-probe]

The launcher reads this helper's JSON through parseGraphicsReport(), so these
tests assert that same contract: format 1, bits 32, a devices array whose
entries carry name/vendor/device/usable, and an exit code of 0 only when at
least one device is usable. The missing-loader and missing-driver diagnostics
are exercised for real, not simulated from fixtures.
"""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROBE = ROOT / "_build" / "launcher-qt" / "melee-graphics-probe"


def probe_path() -> Path:
    if __name__ == '__main__' and len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        return Path(sys.argv[1]).resolve()
    return DEFAULT_PROBE


def is_elf32(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            header = handle.read(20)
    except OSError:
        return False
    if len(header) < 20 or header[:4] != b"\x7fELF":
        return False
    little_endian = header[5] == 1
    return header[4] == 1 and struct.unpack("<H" if little_endian else ">H", header[18:20])[0] == 3


def run_probe(path: Path, **overrides: str) -> tuple[int, dict]:
    env = dict(os.environ)
    for key in ("VK_ICD_FILENAMES", "VK_DRIVER_FILES", "LD_LIBRARY_PATH"):
        env.pop(key, None)
    env.update(overrides)
    done = subprocess.run([str(path)], capture_output=True, text=True, env=env, timeout=120)
    try:
        report = json.loads(done.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"probe stdout was not JSON ({exc}): {done.stdout!r}") from exc
    return done.returncode, report


def report_problems(report: dict) -> list[str]:
    """The checks parseGraphicsReport() makes before it trusts a report."""
    problems = []
    if not isinstance(report, dict):
        return ["report is not an object"]
    if report.get("format") != 1:
        problems.append(f"format is {report.get('format')!r}, expected 1")
    if report.get("bits") != 32:
        problems.append(f"bits is {report.get('bits')!r}, expected 32")
    devices = report.get("devices")
    if not isinstance(devices, list):
        return problems + ["devices is not an array"]
    for index, device in enumerate(devices):
        if not isinstance(device, dict):
            problems.append(f"device {index} is not an object")
            continue
        if not isinstance(device.get("name"), str):
            problems.append(f"device {index} name is not a string")
        for field in ("vendor", "device"):
            if not isinstance(device.get(field), int) or isinstance(device.get(field), bool):
                problems.append(f"device {index} {field} is not a number")
        if not isinstance(device.get("usable"), bool):
            problems.append(f"device {index} usable is not a boolean")
    return problems


def ready(report: dict) -> bool:
    """GraphicsReport::ready(): valid, no top-level error, and a usable device."""
    return (
        not report_problems(report)
        and not report.get("error")
        and any(d.get("usable") for d in report["devices"])
    )


@unittest.skipUnless(sys.platform.startswith('linux'), 'requires the Linux Vulkan graphics helper')
class GraphicsProbeTests(unittest.TestCase):
    probe = probe_path()

    def test_probe_exists_and_is_32_bit(self):
        self.assertTrue(self.probe.is_file(), f"missing probe: {self.probe}")
        self.assertTrue(
            is_elf32(self.probe),
            f"{self.probe} is not a 32-bit ELF; build it with tools/port/build_graphics_probe.sh",
        )

    def test_healthy_driver_reports_a_usable_device(self):
        code, report = run_probe(self.probe)
        self.assertEqual(report_problems(report), [])
        self.assertEqual(code, 0, f"probe failed: {report.get('error')!r}")
        self.assertTrue(ready(report), "no usable 32-bit Vulkan device was reported")
        usable = [d for d in report["devices"] if d["usable"]]
        for device in usable:
            self.assertEqual(device["reason"], "", "a usable device must not carry a reason")

    def test_missing_loader_is_reported_not_crashed(self):
        with tempfile.TemporaryDirectory() as fake:
            shadow = Path(fake)
            (shadow / "libvulkan.so.1").write_bytes(b"not an ELF")
            code, report = run_probe(self.probe, LD_LIBRARY_PATH=fake)
        self.assertEqual(report_problems(report), [])
        self.assertEqual(report["devices"], [])
        self.assertEqual(code, 2)
        self.assertFalse(ready(report))
        self.assertTrue(report["error"], "a failed probe must explain itself")

    def test_missing_driver_is_reported_with_guidance(self):
        code, report = run_probe(self.probe, VK_ICD_FILENAMES="/nonexistent-icd.json")
        self.assertEqual(report_problems(report), [])
        self.assertEqual(report["devices"], [])
        self.assertEqual(code, 2)
        self.assertFalse(ready(report))
        self.assertIn("driver", report["error"].lower())

    def test_a_64_bit_build_is_refused(self):
        source = ROOT / "tools" / "port" / "graphics_probe.c"
        compiler = os.environ.get("CC") or "cc"
        with tempfile.TemporaryDirectory() as out:
            built = Path(out) / "probe64"
            done = subprocess.run(
                [compiler, "-std=c11", "-O2", str(source), "-ldl", "-o", str(built)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if done.returncode != 0:
                self.skipTest(f"no working native compiler: {done.stderr.strip()[:200]}")
            code, report = run_probe(built)
        self.assertEqual(report["bits"], 64)
        self.assertEqual(report["devices"], [])
        self.assertEqual(code, 2)
        self.assertFalse(ready(report))
        self.assertIn("32-bit", report["error"])


if __name__ == "__main__":
    if not probe_path().is_file():
        print(f"probe not built: {probe_path()}", file=sys.stderr)
        print("build it with: bash tools/port/build_graphics_probe.sh", file=sys.stderr)
        raise SystemExit(1)
    unittest.main(argv=[sys.argv[0], *[a for a in sys.argv[1:] if a.startswith("-")]], exit=True)
