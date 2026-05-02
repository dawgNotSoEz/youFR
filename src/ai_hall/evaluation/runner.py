from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ai_hall.app import run


@dataclass
class EvalItem:
    id: str
    query: str


def load_jsonl(path: Path) -> list[EvalItem]:
    items: list[EvalItem] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        items.append(EvalItem(id=str(obj.get("id", len(items))), query=str(obj["query"])))
    return items


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="JSONL with {id, query}")
    ap.add_argument("--output", required=True, help="Output JSONL of pipeline runs")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    items = load_jsonl(in_path)
    out_lines = []
    for it in items:
        pr = run(it.query)
        out_lines.append(pr.model_dump_json())

    out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

