"""python -m tools.geno.disasm words.txt [-o output.genoasm]."""
import sys
from .script import main

if __name__ == "__main__":
    sys.argv.insert(1, "disasm")
    raise SystemExit(main())
