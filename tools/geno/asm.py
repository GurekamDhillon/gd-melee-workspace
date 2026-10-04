"""python -m tools.geno.asm input.genoasm [-o output.json] [--words]."""
import sys
from .script import main

if __name__ == "__main__":
    sys.argv.insert(1, "asm")
    raise SystemExit(main())
