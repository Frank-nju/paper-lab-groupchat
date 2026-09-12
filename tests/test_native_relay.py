from pathlib import Path

import pytest

from paper_lab.evidence_pack import build_evidence_pack
from paper_lab.native_relay import (
    assemble_worker_packet,
    prepare_relay_session,
    submit_native_response,
)


def _make_pack(tmp_path: Path) -> Path:
    problem = tmp_path / "problem.txt"
    problem.write_text(
        "问题一：建立模型并验证结果，明确输入、输出、约束、评价指标、数据范围和可复现的验证方案。\n",
        encoding="utf-8",
    )
    paper = tmp_path / "paper.txt"
    paper.write_text(
        "模型、结果和验证均应可定位。本文还记录变量、单位、约束、边界、数据来源和结果解释，"
        "用于测试证据包的页级质量门禁。",
        encoding="utf-8",
    )
    pack = tmp_path / "pack"
    build_evidence_pack(problem, paper, [], pack)
    return pack


def test_native_relay_preserves_two_advanced_responses(tmp_path: Path) -> None:
    pack = _make_pack(tmp_path)
    session = prepare_relay_session(pack, tmp_path / "relay", "审查证据链")

    assert session["status"] == "awaiting_native_responses"
    assert "Q1" in (tmp_path / "relay" / "prompts" / "GPT6.md").read_text(encoding="utf-8")

    submit_native_response(tmp_path / "relay", "GPT6", "GPT6意见：Q1缺少时间切分证据。")
    submit_native_response(tmp_path / "relay", "Fable51", "Fable意见：请补充约束和单位核对。")
    worker = assemble_worker_packet(tmp_path / "relay")

    assert worker["status"] == "ready_for_worker"
    content = (tmp_path / "relay" / "worker_packet.md").read_text(encoding="utf-8")
    assert content.index("GPT6意见") < content.index("Fable意见")
    assert "只能执行质量控制" in content


def test_native_relay_rejects_blocked_pack(tmp_path: Path) -> None:
    problem = tmp_path / "problem.txt"
    problem.write_text("", encoding="utf-8")
    paper = tmp_path / "paper.txt"
    paper.write_text("论文", encoding="utf-8")
    pack = tmp_path / "pack"
    build_evidence_pack(problem, paper, [], pack)

    with pytest.raises(ValueError, match="质量门禁"):
        prepare_relay_session(pack, tmp_path / "relay", "审查")

