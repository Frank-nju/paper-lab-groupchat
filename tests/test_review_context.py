from pathlib import Path

from paper_lab.evidence_pack import build_evidence_pack, review_context


def test_review_context_budget_keeps_every_question(tmp_path: Path) -> None:
    problem = tmp_path / "problem.txt"
    problem.write_text(
        "\n".join(
            f"问题{index}：建立第{index}问模型，明确输入、输出、约束、评价指标、数据范围和验证方案。"
            for index in range(1, 5)
        ),
        encoding="utf-8",
    )
    paper = tmp_path / "paper.txt"
    paper.write_text(
        "模型、结果和验证均应可定位。本文记录变量、单位、约束、边界、数据来源和验证方法。" * 600,
        encoding="utf-8",
    )
    attachments = []
    for index in range(12):
        path = tmp_path / f"附件{index + 1}.csv"
        path.write_text("time,load\n2026-01-01,10\n", encoding="utf-8")
        attachments.append(path)

    build_evidence_pack(problem, paper, attachments, tmp_path / "pack")
    context = review_context(tmp_path / "pack")

    assert len(context) <= 24_000
    assert all(f"===== Q{index}" in context for index in range(1, 5))

