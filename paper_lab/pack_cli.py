"""本地证据包构建命令。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evidence_pack import build_evidence_pack


def main() -> int:
    parser = argparse.ArgumentParser(description="解析赛题、论文和附件为可审计证据包")
    parser.add_argument("--problem", type=Path, required=True)
    parser.add_argument("--paper", type=Path, required=True)
    parser.add_argument("--attachment", type=Path, action="append", default=[])
    parser.add_argument("--attachments-dir", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    paths = [*args.attachment, *args.attachments_dir]
    result = build_evidence_pack(args.problem, args.paper, paths, args.out)
    print(json.dumps({"status": result["status"], "quality": result["quality"]}, ensure_ascii=False, indent=2))
    return 0 if result["quality"]["gate"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

