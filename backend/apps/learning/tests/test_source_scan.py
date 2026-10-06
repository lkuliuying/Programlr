import json
from typing import Any

import pytest

from apps.analysis.types import Source
from apps.learning.source_scan import scan_knowledge_facts

SNAPSHOT = "00000000-0000-4000-8000-000000000001"


def scan(*sources: tuple[str, str]) -> dict[str, Any]:
    return scan_knowledge_facts(
        SNAPSHOT, [Source(path, text) for path, text in sources]
    )


def test_empty_scan_and_comment_strings_do_not_invent_syntax() -> None:
    assert scan()["hits"] == []
    result = scan(
        (
            "a.py",
            '# async with yield match try\ntext = "@decorator [x for x in values]"\n',
        )
    )
    assert result["hits"] == [] and result["packages"] == []
    assert result["coverage"]["complete"]


def test_eight_syntax_categories_have_precise_snapshot_references() -> None:
    text = """@decorate
async def work(value: int) -> int:
    async with manager():
        await operation()
    result = [item for item in values]
    yield from result
    try:
        raise ValueError()
    except ValueError:
        pass
    match value:
        case 1:
            return 1
"""
    result = scan(("source.py", text))
    assert {hit["concept_key"] for hit in result["hits"]} == {
        "python-decorators",
        "python-context-managers",
        "python-comprehensions",
        "python-generators",
        "python-async",
        "python-exceptions",
        "python-pattern-matching",
        "python-type-annotations",
    }
    for hit in result["hits"]:
        ref = hit["source_ref"]
        assert ref["snapshot_id"] == SNAPSHOT and ref["file_path"] == "source.py"
        assert 1 <= ref["start_line"] <= ref["end_line"] <= len(text.splitlines())


def test_import_classification_preserves_unknown_and_local_collision() -> None:
    result = scan(
        (
            "main.py",
            "import json\nimport requests\nimport mystery\nfrom . import absent\n",
        ),
        ("requests.py", "value = 1\n"),
    )
    kinds = {package["name"]: package["kind"] for package in result["packages"]}
    assert kinds == {
        "json": "stdlib",
        "requests": "local",
        "mystery": "unknown",
        ".": "unknown",
    }
    assert not any(hit["concept_key"] == "requests-client" for hit in result["hits"])


def test_manifest_names_versions_and_urls_are_not_executed_or_retained() -> None:
    result = scan(
        ("a.py", "import unknown_lib\nimport requests\n"),
        (
            "requirements-dev.txt",
            "unknown-lib>=1; python_version>'3'\nrequests @ https://name:secret@example.invalid/file.whl\n-r outside.txt\n",
        ),
        (
            "pyproject.toml",
            '[project]\ndependencies = ["httpx>=0.2"]\n[project.optional-dependencies]\nextra = ["django==5.2"]\n',
        ),
        ("random.txt", "pandas>=2\n"),
    )
    packages = {package["name"]: package for package in result["packages"]}
    assert packages["unknown_lib"]["kind"] == "third_party"
    assert packages["unknown_lib"]["distribution"] == "unknown-lib"
    assert not any(hit["concept_key"].startswith("unknown") for hit in result["hits"])
    assert {item["distribution"] for item in result["declarations"]} == {
        "unknown-lib",
        "requests",
        "httpx",
        "django",
    }
    assert next(
        item for item in result["declarations"] if item["distribution"] == "django"
    )["optional"]
    encoded = json.dumps(result)
    assert "secret" not in encoded and "example.invalid" not in encoded
    assert {item["code"] for item in result["diagnostics"]} == {
        "DEPENDENCY_URL_NOT_FOLLOWED",
        "DEPENDENCY_DIRECTIVE_UNSUPPORTED",
    }


def test_framework_alias_and_function_shadowing_are_conservative() -> None:
    result = scan(
        (
            "a.py",
            """from rest_framework import serializers as s
class Good(s.Serializer):
    pass
def bad(s):
    return s.Serializer()
def good():
    return s.Serializer()
""",
        )
    )
    refs = [
        hit["source_ref"]["start_line"]
        for hit in result["hits"]
        if hit["concept_key"] == "drf-serializers"
    ]
    assert 2 in refs and 7 in refs and 5 not in refs


def test_invalid_python_and_manifest_keep_other_knowledge() -> None:
    result = scan(
        ("bad.py", "def ("),
        ("ok.py", "with manager():\n    pass\n"),
        ("pyproject.toml", "[project"),
    )
    assert result["coverage"]["syntax_failed_files"] == 1
    assert result["hits"][0]["concept_key"] == "python-context-managers"
    assert not result["coverage"]["complete"]


def test_unknown_package_usage_has_precise_references_without_a_card() -> None:
    result = scan(
        ("a.py", "import mysterious as m\ndef selected():\n    return m.call()\n")
    )
    package = result["packages"][0]
    assert package["name"] == "mysterious" and package["kind"] == "unknown"
    assert package["source_refs"][0]["start_line"] == 1
    assert package["usage_refs"][0]["start_line"] == 3
    assert not result["hits"]


def test_decorator_owner_preserves_precise_source_and_selected_symbol() -> None:
    result = scan(
        (
            "a.py",
            "from rest_framework.decorators import api_view\n@api_view(['GET'])\ndef selected():\n    return response\n",
        )
    )
    hit = next(
        item for item in result["hits"] if item["concept_key"] == "python-decorators"
    )
    assert hit["source_ref"]["start_line"] == 2 and hit["source_ref"]["end_line"] == 2
    assert hit["owner_ref"]["start_line"] == 3 and hit["owner_ref"]["end_line"] == 4


def test_local_unparseable_file_and_expression_shadowing_do_not_invent_package_api() -> (
    None
):
    result = scan(
        ("requests.py", "def ("),
        (
            "a.py",
            "import requests\nfrom rest_framework import serializers as s\n"
            "value = lambda s: s.Serializer()\nvalue = [s.Serializer() for s in values]\n"
            "class Scoped:\n    s = custom\n    value = s.Serializer()\n"
            "def selected():\n    return s.Serializer()\n",
        ),
    )
    assert (
        next(
            package for package in result["packages"] if package["name"] == "requests"
        )["kind"]
        == "local"
    )
    refs = {
        hit["source_ref"]["start_line"]
        for hit in result["hits"]
        if hit["concept_key"] == "drf-serializers"
    }
    assert refs == {9}


def test_hit_limit_is_explicit_and_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("apps.learning.source_scan.MAX_FACTS", 1)
    result = scan(("a.py", "with one():\n    pass\nwith two():\n    pass\n"))
    assert len(result["hits"]) == 1 and result["coverage"]["truncated"]
    assert not result["coverage"]["complete"]


def test_byte_budget_preserves_complete_individual_facts_and_reports_truncation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("apps.learning.source_scan.MAX_KNOWLEDGE_BYTES", 2048)
    result = scan(("a.py", "with manager():\n    pass\n" * 100))
    assert (
        len(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode())
        <= 2048
    )
    assert result["coverage"]["truncated"] and not result["coverage"]["complete"]
    assert result["coverage"]["hit_count"] == len(result["hits"])
    assert "KNOWLEDGE_OUTPUT_LIMIT" in {item["code"] for item in result["diagnostics"]}
    assert result["hits"] and result["hits"][0]["source_ref"]["start_line"] == 1
