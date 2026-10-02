"""验证真实框架加载、字段边界和工具的错误检测能力。"""

import subprocess
import sys
from pathlib import Path

import django
import pytest
from django.apps import apps
from rest_framework.exceptions import ValidationError
from rest_framework.fields import IntegerField

from tooling.check_versions import check_versions
from tooling.type_probe import render_count


def test_framework_and_versions() -> None:
    assert apps.ready
    assert django.get_version() == check_versions()["django"]
    assert render_count(0).content == b"0"
    assert render_count(10).content == b"10"


@pytest.mark.parametrize("value", [None, "", "invalid", -1, 11])
def test_field_rejects_invalid_input(value: object) -> None:
    with pytest.raises(ValidationError):
        IntegerField(min_value=0, max_value=10).run_validation(value)


def test_mypy_rejects_wrong_framework_type(tmp_path: Path) -> None:
    probe = tmp_path / "invalid_type.py"
    probe.write_text(
        "from django.http import HttpResponse\nresponse: HttpResponse = 123\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "-m", "mypy", str(probe), "--no-incremental"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "[assignment]" in result.stdout


def test_ruff_rejects_undefined_name() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--stdin-filename", "probe.py", "-"],
        input="print(undefined_toolchain_name)\n",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "F821" in result.stdout
