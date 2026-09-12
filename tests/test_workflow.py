from paper_lab.workflow import (
    build_round_plan,
    compact_to_one_sentence,
    run_offline_review,
)


def test_round_plan_keeps_gpt6_and_fable_equal() -> None:
    assert build_round_plan() == ["GPT6", "Fable51", "CheapWorker"]


def test_compact_to_one_sentence() -> None:
    result = compact_to_one_sentence("第一句。第二句。")

    assert result == "第一句。"


def test_offline_review_has_one_message_per_role() -> None:
    result = run_offline_review("论文内容示例")

    assert [item["speaker"] for item in result] == [
        "GPT6",
        "Fable51",
        "CheapWorker",
    ]
    assert all(item["sentence_count"] == 1 for item in result)
    assert "GPT6" in result[2]["content"]
    assert "Fable51" in result[2]["content"]


def test_offline_review_does_not_modify_paper() -> None:
    paper = "原稿文本"

    result = run_offline_review(paper)

    assert result[-1]["paper_unchanged"] is True
