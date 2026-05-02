import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_hall.app import run

if __name__ == "__main__":
    q = " ".join(sys.argv[1:]).strip() or "Who invented relativity?"
    out = run(q)
    print(out.model_dump_json(indent=2))

