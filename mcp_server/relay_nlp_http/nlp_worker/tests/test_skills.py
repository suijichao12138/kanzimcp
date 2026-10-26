from pathlib import Path

import pytest

from copilot_runtime import ConfigError, SkillEntry, SkillsConfig, load_skills


def test_load_skill_file_and_directory(tmp_path: Path) -> None:
    first = tmp_path / "one" / "SKILL.md"
    first.parent.mkdir()
    first.write_text("first", encoding="utf-8")
    second = tmp_path / "two" / "SKILL.md"
    second.parent.mkdir()
    second.write_text("second", encoding="utf-8")
    config = SkillsConfig(
        entries=[SkillEntry(path=first), SkillEntry(path=second.parent)]
    )

    result = load_skills(config)

    assert "first" in result
    assert "second" in result


def test_missing_enabled_skill_fails(tmp_path: Path) -> None:
    config = SkillsConfig(entries=[SkillEntry(path=tmp_path / "missing" / "SKILL.md")])

    with pytest.raises(ConfigError, match="does not exist"):
        load_skills(config)


def test_disabled_missing_skill_is_ignored(tmp_path: Path) -> None:
    config = SkillsConfig(
        entries=[SkillEntry(path=tmp_path / "missing" / "SKILL.md", enabled=False)]
    )
    assert load_skills(config) == ""


def test_parent_directory_discovers_sorted_child_skills(tmp_path: Path) -> None:
    parent = tmp_path / "skills"
    zulu = parent / "zulu" / "SKILL.md"
    alpha = parent / "alpha" / "SKILL.md"
    zulu.parent.mkdir(parents=True)
    alpha.parent.mkdir(parents=True)
    zulu.write_text("zulu-content", encoding="utf-8")
    alpha.write_text("alpha-content", encoding="utf-8")

    result = load_skills(SkillsConfig(entries=[SkillEntry(path=parent)]))

    assert result.index("alpha-content") < result.index("zulu-content")


def test_parent_and_explicit_skill_are_deduplicated(tmp_path: Path) -> None:
    skill = tmp_path / "skills" / "one" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("one-content", encoding="utf-8")
    config = SkillsConfig(
        entries=[
            SkillEntry(path=skill.parent.parent),
            SkillEntry(path=skill),
        ]
    )

    assert load_skills(config).count("one-content") == 1


def test_directory_with_own_skill_requires_recursive_for_children(tmp_path: Path) -> None:
    parent = tmp_path / "skills"
    own = parent / "SKILL.md"
    child = parent / "child" / "SKILL.md"
    child.parent.mkdir(parents=True)
    own.write_text("parent-content", encoding="utf-8")
    child.write_text("child-content", encoding="utf-8")

    direct_only = load_skills(SkillsConfig(entries=[SkillEntry(path=parent)]))
    recursive = load_skills(
        SkillsConfig(entries=[SkillEntry(path=parent, recursive=True)])
    )

    assert "parent-content" in direct_only
    assert "child-content" not in direct_only
    assert "parent-content" in recursive
    assert "child-content" in recursive


def test_empty_skill_parent_fails(tmp_path: Path) -> None:
    parent = tmp_path / "empty"
    parent.mkdir()

    with pytest.raises(ConfigError, match=r"contains no SKILL\.md"):
        load_skills(SkillsConfig(entries=[SkillEntry(path=parent)]))


def test_discovered_skills_apply_file_and_total_size_limits(tmp_path: Path) -> None:
    parent = tmp_path / "skills"
    first = parent / "one" / "SKILL.md"
    second = parent / "two" / "SKILL.md"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_text("12345", encoding="utf-8")
    second.write_text("67890", encoding="utf-8")

    with pytest.raises(ConfigError, match="max_file_bytes"):
        load_skills(
            SkillsConfig(
                max_file_bytes=4,
                max_total_bytes=100,
                entries=[SkillEntry(path=parent)],
            )
        )
    with pytest.raises(ConfigError, match="max_total_bytes"):
        load_skills(
            SkillsConfig(
                max_file_bytes=10,
                max_total_bytes=9,
                entries=[SkillEntry(path=parent)],
            )
        )
