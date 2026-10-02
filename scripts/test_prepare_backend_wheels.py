"""验证锁定来源和有界重试，不连接网络或安装依赖。"""

import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from prepare_backend_wheels import fetch_artifact, validate_artifact


class WheelPreparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.item = {
            "url": "https://files.pythonhosted.org/packages/example-1.0-py3-none-any.whl",
            "hash": "sha256:" + "a" * 64,
            "size": 100,
        }
        setting = patch("prepare_backend_wheels.WHEELHOUSE", Path(self.directory.name))
        setting.start()
        self.addCleanup(setting.stop)

    def test_official_artifact_is_accepted(self) -> None:
        self.assertEqual(validate_artifact(self.item), "example-1.0-py3-none-any.whl")

    def test_untrusted_artifacts_are_rejected(self) -> None:
        cases = [
            {"url": "http://files.pythonhosted.org/example.whl"},
            {"url": "https://example.invalid/example.whl"},
            {"url": "https://user@files.pythonhosted.org/example.whl"},
            {"url": "https://files.pythonhosted.org/%2e%2e%2fexample.whl"},
            {"hash": "sha256:invalid"},
            {"size": 0},
        ]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_artifact(self.item | changes)

    def test_retry_stops_after_three_transient_failures(self) -> None:
        result = subprocess.CompletedProcess([], 75)
        with patch("prepare_backend_wheels.subprocess.run", return_value=result) as run:
            with self.assertRaisesRegex(TimeoutError, "三次"):
                fetch_artifact(self.item, time.monotonic() + 1800)
        self.assertEqual(run.call_count, 3)

    def test_invalid_hash_is_not_retried(self) -> None:
        with patch(
            "prepare_backend_wheels.subprocess.run",
            return_value=subprocess.CompletedProcess([], 1),
        ) as run:
            with self.assertRaisesRegex(RuntimeError, "校验失败"):
                fetch_artifact(self.item, time.monotonic() + 1800)
        self.assertEqual(run.call_count, 1)

    def test_expired_budget_does_not_start_download(self) -> None:
        with patch("prepare_backend_wheels.subprocess.run") as run:
            with self.assertRaisesRegex(TimeoutError, "1800"):
                fetch_artifact(self.item, time.monotonic() - 1)
        run.assert_not_called()

    def test_timeout_retries_then_accepts_success(self) -> None:
        with patch(
            "prepare_backend_wheels.subprocess.run",
            side_effect=[
                subprocess.TimeoutExpired("download", 300),
                subprocess.CompletedProcess([], 0),
            ],
        ) as run:
            destination = fetch_artifact(self.item, time.monotonic() + 1800)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(destination.name, "example-1.0-py3-none-any.whl")


if __name__ == "__main__":
    unittest.main()
