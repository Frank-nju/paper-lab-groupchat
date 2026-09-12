import json
from pathlib import Path

from paper_lab.config import default_config
from paper_lab.evidence_pack import build_evidence_pack, review_context
from paper_lab.evidence_rounds import EvidenceRoundController


def test_evidence_controller_uses_pack_and_records_mode(tmp_path: Path) -> None:
    problem = tmp_path / "problem.txt"
    problem.write_text(
        "问题一：建立模型并验证结果，明确输入、输出、约束、评价指标、数据范围和可复现的验证方案。",
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

    controller = EvidenceRoundController(
        config=default_config(tmp_path),
        paper_path=paper,
        problem_text=problem.read_text(encoding="utf-8"),
        task="审查证据链",
        offline=True,
        evidence_pack_dir=pack,
    )
    result = controller.start_round()
    state = json.loads((controller.session_dir / "session_state.json").read_text(encoding="utf-8"))

    assert result["status"] == "awaiting_approval"
    assert state["context_mode"] == "evidence_pack_retrieval"
    context = review_context(pack)
    assert "E-" in context
    assert "模型、结果和验证均应可定位" in context

