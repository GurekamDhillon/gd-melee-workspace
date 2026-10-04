"""Assemble the original tutorial script. Run from anywhere; needs only Python."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from tools.geno.script import assemble

words = assemble((HERE / "geno/tutorial_b.genoasm").read_text(encoding="utf-8"))
(HERE / "geno/tutorial_b.txt").write_text(
    "# Generated from original tutorial_b.genoasm; no disc data.\n" +
    "\n".join(f"0x{w:08X}" for w in words) + "\n", encoding="utf-8")
print("Built geno/tutorial_b.txt")
