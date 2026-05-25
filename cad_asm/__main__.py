"""Allow `python -m cad_asm` invocation."""
from cad_asm.cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
