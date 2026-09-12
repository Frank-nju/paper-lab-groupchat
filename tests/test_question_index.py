from pathlib import Path

from paper_lab.evidence_pack import build_evidence_pack


def test_repeated_result_references_do_not_create_new_questions(tmp_path: Path) -> None:
    problem = tmp_path / "problem.txt"
    problem.write_text(
        "问题 1 建立预测模型并给出结果。\n"
        "问题 2 建立调度模型并验证约束。\n"
        "附录 1 参数说明。问题 1 的结果文件见附件 5。问题 2 的全部结果见表格。",
        encoding="utf-8",
    )
    paper = tmp_path / "paper.txt"
    paper.write_text(
        "本文建立预测模型并给出结果，同时建立调度模型并验证约束。"
        "所有变量、单位、边界、数据来源和验证方法均有说明。",
        encoding="utf-8",
    )

    result = build_evidence_pack(problem, paper, [], tmp_path / "pack")

    assert result["problem"]["question_ids"] == ["Q1", "Q2"]
    assert len(result["problem"]["questions"]) == 2

