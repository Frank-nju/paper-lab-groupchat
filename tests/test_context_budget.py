from pathlib import Path

from paper_lab.evidence_pack import build_evidence_pack, review_context


def test_question_pack_does_not_duplicate_all_attachment_metadata(tmp_path: Path) -> None:
    problem = tmp_path / "problem.txt"
    problem.write_text(
        "问题一：根据附件1的负荷数据建立模型并验证结果，明确输入、输出、约束、评价指标、数据范围和可复现方案。",
        encoding="utf-8",
    )
    paper = tmp_path / "paper.txt"
    paper.write_text(
        "模型、结果和验证均应可定位。本文记录变量、单位、约束、边界、数据来源和验证方法。",
        encoding="utf-8",
    )
    attachments = []
    for index in range(30):
        path = tmp_path / f"附件{index + 1}.csv"
        path.write_text("time,load\n2026-01-01,10\n", encoding="utf-8")
        attachments.append(path)

    result = build_evidence_pack(problem, paper, attachments, tmp_path / "pack")
    q1 = (tmp_path / "pack" / "question_packs" / "Q1.json").read_text(encoding="utf-8")

    assert result["quality"]["gate"] is True
    assert q1.count('"source_id"') < 15
    assert len(review_context(tmp_path / "pack")) < 30_000

