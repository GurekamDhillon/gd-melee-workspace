"""Extract the existing production JSON parser for the standalone item fixture."""
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[2]
source = (root / 'melee/pc/platform/geno_registry.c').read_text()
start = source.index('enum { JN_NULL')
end = source.index('/* ---- hashing')
out = Path(sys.argv[1])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(source[start:end])
