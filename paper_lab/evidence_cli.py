"""证据包路线的 Windows/Linux 统一命令行入口。"""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .evidence_rounds import EvidenceRoundController
from .storage import read_paper


def main() -> int:
    parser = argparse.ArgumentParser(description="使用本地证据包运行审批式数模审计群聊")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--paper", type=Path, default=Path("data/candidate_paper.pdf"))
    parser.add_argument("--problem", type=Path, default=Path("data/problem_statement.pdf"))
    parser.add_argument("--evidence-pack", type=Path, required=True)
    parser.add_argument("--task", default="审查论文的题意、模型和证据链")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else Path(__file__).resolve().parents[1] / args.config
    config = load_config(config_path)
    paper = args.paper if args.paper.is_absolute() else config.root / args.paper
    problem = args.problem if args.problem.is_absolute() else config.root / args.problem
    pack = args.evidence_pack if args.evidence_pack.is_absolute() else config.root / args.evidence_pack
    controller = EvidenceRoundController(
        config=config,
        paper_path=paper,
        problem_text=read_paper(problem, config.max_paper_chars),
        task=args.task,
        offline=args.offline,
        evidence_pack_dir=pack,
    )
    result = controller.start_round()
    print(f"第 {result['round_number']} 轮已完成，状态：{result['status']}")
    print(f"证据包模式：{pack}")
    print(f"产物目录：{controller.session_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

