from pathlib import Path

from paper_lab.rounds_impl import KNOWLEDGE_FILES, load_reviewer_knowledge


ROOT = Path(__file__).resolve().parents[1]


def test_2026_hard_constraints_are_loaded_into_reviewer_knowledge() -> None:
    relative = "references/cumcm-2026-hard-constraints.md"
    assert relative in KNOWLEDGE_FILES

    bundle = load_reviewer_knowledge(ROOT)

    assert "AI 工具使用声明" in bundle
    assert "AI工具使用详情.pdf" in bundle
    assert "核心建模与分析必须由参赛队主导" in bundle
    assert "未来数据泄漏" in bundle
    assert "unverifiable" in bundle


def test_2026_audit_skill_has_non_negotiable_gates() -> None:
    skill = (ROOT / "skills" / "cumcm-2026-audit" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "CUMCM 2026" in skill
    assert "P0 / fatal / blocking" in skill
    assert "不能继续输出“通过”" in skill
    assert "承诺修改”不算已修复" in skill
