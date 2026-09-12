"""论文群聊入口：高级双阶段讨论、低价执行、人工审批后再进入下一轮。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from paper_lab.config import ProjectConfig, load_config
from paper_lab.llm import OnlineConfigError
from paper_lab.rounds import RoundController
from paper_lab.storage import read_paper


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GPT6/Fable51 数模评审群聊")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--paper", type=Path, help="覆盖配置中的论文路径")
    parser.add_argument(
        "--problem",
        type=Path,
        default=Path("data/problem_statement.pdf"),
        help="原始赛题路径；用于题意索引和证据审计",
    )
    parser.add_argument("--task", default="审查论文并形成可执行修改意见")
    parser.add_argument("--offline", action="store_true", help="不请求 API，运行离线流程")
    parser.add_argument("--interactive", action="store_true", help="进入审批式交互")
    return parser


def _resolve_config_path(path: Path) -> Path:
    return path if path.is_absolute() else Path(__file__).resolve().parent / path


def _resolve_data_path(config: ProjectConfig, path: Path | None, default: Path) -> Path:
    selected = default if path is None else path
    return selected if selected.is_absolute() else config.root / selected


def _controller(
    config: ProjectConfig,
    paper_path: Path,
    problem_path: Path,
    task: str,
    offline: bool,
) -> RoundController:
    problem_text = read_paper(problem_path, config.max_paper_chars)
    return RoundController(config, paper_path, problem_text, task, offline=offline)


def _print_round(result: dict) -> None:
    print(
        f"\n第 {result['round_number']} 轮已完成高级讨论和低价执行，"
        f"当前状态：{result['status']}。"
    )
    for item in result["messages"]:
        print(f"\n[{item['speaker']} · {item['stage']}]\n{item['content']}")
    print(
        "\n审批命令：/approve；低价返工：/return cheap 反馈；"
        "人工返工：/return human 反馈；审批后用 /next 开始下一轮。"
    )
    print(f"产物目录：{result.get('session_dir', '见 outputs/round_sessions')}")


def run_once(
    config: ProjectConfig,
    paper_path: Path,
    problem_path: Path,
    task: str,
    offline: bool,
) -> dict:
    controller = _controller(config, paper_path, problem_path, task, offline)
    result = controller.start_round()
    result["session_dir"] = str(controller.session_dir)
    _print_round(result)
    return result


def _interactive(
    config: ProjectConfig,
    paper_path: Path,
    problem_path: Path,
    task: str,
    offline: bool,
) -> None:
    controller = _controller(config, paper_path, problem_path, task, offline)
    print(
        "输入 /review、/chat 任务、/approve、/next、/return cheap 反馈、"
        "/return human 反馈、/submit human 内容、/status、/read 或 /quit。"
    )
    while True:
        try:
            command = input("paper-lab> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if command in {"/quit", "/exit"}:
            return
        if command == "/read":
            text = read_paper(paper_path, config.max_paper_chars)
            print(f"论文：{paper_path}\n字符数：{len(text)}\n\n{text[:2000]}")
            continue
        try:
            if command in {"/review", "/proposal", "/next"}:
                if command == "/proposal":
                    controller.task = "审查论文并形成可执行修改意见"
                result = controller.start_round()
                _print_round(result)
                continue
            if command.startswith("/chat "):
                controller.task = command[6:].strip()
                result = controller.start_round()
                _print_round(result)
                continue
            if command.startswith("/approve"):
                parts = command.split(maxsplit=1)
                result = controller.approve(parts[1] if len(parts) == 2 else "human")
                print(f"已审批第 {result['round_number']} 轮；请使用 /next 开始下一轮。")
                continue
            if command.startswith("/return cheap "):
                result = controller.redo_worker(command[len("/return cheap ") :].strip())
                _print_round(result)
                continue
            if command.startswith("/return human "):
                result = controller.request_human_rework(
                    command[len("/return human ") :].strip()
                )
                print(f"已进入人工返工状态：{result['human_rework_request']}")
                continue
            if command.startswith("/submit human "):
                result = controller.submit_human_rework(
                    command[len("/submit human ") :].strip()
                )
                _print_round(result)
                continue
            if command == "/status":
                print(json.dumps(controller.status(), ensure_ascii=False, indent=2))
                continue
            if command == "/audit":
                print(
                    "Evidence Audit 已融合为高级模型知识库；需要运行完整确定性门禁时，"
                    "请执行 python -m paper_lab.rebattle.cli --audit-only。"
                )
                continue
            print("未识别命令。可用 /review、/approve、/next、/return cheap、/return human、/status。")
        except RuntimeError as exc:
            print(f"状态机拒绝该操作：{exc}")


def main() -> int:
    args = _parser().parse_args()
    config_path = _resolve_config_path(args.config)
    load_dotenv(config_path.parent / ".env")
    config = load_config(config_path)
    paper_path = _resolve_data_path(config, args.paper, config.paper_path)
    problem_path = _resolve_data_path(config, args.problem, Path("data/problem_statement.pdf"))
    offline = args.offline
    if not offline and not all(
        os.getenv(spec.api_key_env, "").strip()
        for spec in (config.gpt6, config.fable51, config.cheap)
    ):
        print("未检测到完整 API Key，自动切换离线模式；配置 .env 后可在线运行。")
        offline = True
    try:
        if args.interactive:
            _interactive(config, paper_path, problem_path, args.task, offline)
        else:
            run_once(config, paper_path, problem_path, args.task, offline)
    except (FileNotFoundError, OnlineConfigError, OSError) as exc:
        print(f"运行失败：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
