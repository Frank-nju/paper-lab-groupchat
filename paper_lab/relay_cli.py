"""原生高级 Agent + 人工传话路线的命令行入口。"""

from __future__ import annotations

import argparse
from pathlib import Path

from .native_relay import assemble_worker_packet, prepare_relay_session, submit_native_response


def main() -> int:
    parser = argparse.ArgumentParser(description="准备或推进原生 Agent 人工传话审计流程")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--evidence-pack", type=Path, required=True)
    prepare.add_argument("--out", type=Path, required=True)
    prepare.add_argument("--task", default="审查论文的题意、模型和证据链")
    submit = sub.add_parser("submit")
    submit.add_argument("--out", type=Path, required=True)
    submit.add_argument("--role", choices=("GPT6", "Fable51"), required=True)
    submit.add_argument("--file", type=Path, required=True)
    assemble = sub.add_parser("assemble")
    assemble.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        state = prepare_relay_session(args.evidence_pack, args.out, args.task)
    elif args.command == "submit":
        state = submit_native_response(args.out, args.role, args.file.read_text(encoding="utf-8"))
    else:
        state = assemble_worker_packet(args.out)
    print(state["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

