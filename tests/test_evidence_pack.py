import json
from pathlib import Path

from paper_lab.evidence_pack import build_evidence_pack, load_evidence_pack


def test_pack_has_hashes_locations_and_question_packs(tmp_path: Path) -> None:
    problem = tmp_path / "problem.txt"
    problem.write_text(
        "问题一：根据附件数据建立预测模型，给出误差指标。\n"
        "问题二：在约束条件下给出储能调度方案，并验证可行性。\n",
        encoding="utf-8",
    )
    paper = tmp_path / "paper.txt"
    paper.write_text(
        "1 问题分析\n本文研究预测模型和误差指标。\n"
        "2 调度模型\n储能状态转移和可行性验证见表 2。\n",
        encoding="utf-8",
    )
    attachment = tmp_path / "attachment.csv"
    attachment.write_text("time,load\n2026-01-01 00:00,10\n", encoding="utf-8")

    result = build_evidence_pack(problem, paper, [attachment], tmp_path / "pack")
    loaded = load_evidence_pack(tmp_path / "pack")

    assert result["quality"]["gate"] is True
    assert loaded["status"] == "ready"
    assert set(loaded["problem"]["question_ids"]) == {"Q1", "Q2"}
    assert loaded["sources"][0]["sha256"]
    assert loaded["paper"]["chunk_count"] >= 1
    assert (tmp_path / "pack" / "question_packs" / "Q1.json").exists()
    q1 = json.loads((tmp_path / "pack" / "question_packs" / "Q1.json").read_text(encoding="utf-8"))
    assert q1["problem"]["location"].startswith("problem.txt")
    assert all(item["location"] for item in q1["evidence"])


def test_empty_problem_is_blocked_without_touching_inputs(tmp_path: Path) -> None:
    problem = tmp_path / "problem.txt"
    problem.write_text("", encoding="utf-8")
    paper = tmp_path / "paper.txt"
    paper.write_text("论文内容", encoding="utf-8")
    before = paper.read_bytes()

    result = build_evidence_pack(problem, paper, [], tmp_path / "pack")

    assert result["status"] == "blocked"
    assert result["quality"]["gate"] is False
    assert paper.read_bytes() == before

