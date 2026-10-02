"""验证工具下载的摘要与续传边界，不连接外部网络。"""

import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from prepare_toolchain import download


class Response(io.BytesIO):
    """只替代下载传输，测试真实的文件写入和摘要计算。"""

    def __init__(self, data: bytes, status: int, content_range: str = "") -> None:
        super().__init__(data)
        self.status = status
        self.headers = {"Content-Range": content_range}


class DownloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.destination = Path(self.directory.name) / "tool.zip"
        self.content = b"verified-tool-content"
        self.checksum = hashlib.sha256(self.content).hexdigest()

    def test_valid_download_is_published(self) -> None:
        with patch("urllib.request.urlopen", return_value=Response(self.content, 200)):
            download("https://example.invalid/tool", self.destination, self.checksum)
        self.assertEqual(self.destination.read_bytes(), self.content)

    def test_verified_cache_does_not_access_network(self) -> None:
        self.destination.write_bytes(self.content)
        with patch("urllib.request.urlopen") as request:
            download("https://example.invalid/tool", self.destination, self.checksum)
            request.assert_not_called()

    def test_complete_partial_is_verified_before_reuse(self) -> None:
        self.destination.with_suffix(".zip.part").write_bytes(self.content)
        with patch("urllib.request.urlopen") as request:
            download("https://example.invalid/tool", self.destination, self.checksum)
            request.assert_not_called()
        self.assertEqual(self.destination.read_bytes(), self.content)

    def test_checksum_mismatch_is_not_published(self) -> None:
        with patch("urllib.request.urlopen", return_value=Response(b"corrupt", 200)):
            with self.assertRaisesRegex(RuntimeError, "SHA-256"):
                download(
                    "https://example.invalid/tool", self.destination, self.checksum
                )
        self.assertFalse(self.destination.exists())

    def test_partial_download_resumes_at_exact_offset(self) -> None:
        self.destination.with_suffix(".zip.part").write_bytes(self.content[:8])
        response = Response(
            self.content[8:],
            206,
            f"bytes 8-{len(self.content) - 1}/{len(self.content)}",
        )
        with patch("urllib.request.urlopen", return_value=response) as request:
            download("https://example.invalid/tool", self.destination, self.checksum)
            self.assertEqual(request.call_args.args[0].get_header("Range"), "bytes=8-")
        self.assertEqual(self.destination.read_bytes(), self.content)

    def test_server_ignoring_range_restarts_safely(self) -> None:
        self.destination.with_suffix(".zip.part").write_bytes(b"old-partial")
        with patch("urllib.request.urlopen", return_value=Response(self.content, 200)):
            download("https://example.invalid/tool", self.destination, self.checksum)
        self.assertEqual(self.destination.read_bytes(), self.content)

    def test_wrong_offset_is_rejected(self) -> None:
        partial = self.destination.with_suffix(".zip.part")
        partial.write_bytes(b"existing")
        with patch(
            "urllib.request.urlopen", return_value=Response(b"data", 206, "bytes 0-3/4")
        ):
            with self.assertRaisesRegex(RuntimeError, "起始位置"):
                download(
                    "https://example.invalid/tool", self.destination, self.checksum
                )
        self.assertEqual(partial.read_bytes(), b"existing")
        self.assertFalse(self.destination.exists())

    def test_truncated_download_preserves_resumable_content(self) -> None:
        with patch(
            "urllib.request.urlopen", return_value=Response(self.content[:8], 200)
        ):
            with self.assertRaises(EOFError):
                download(
                    "https://example.invalid/tool",
                    self.destination,
                    self.checksum,
                    expected_size=len(self.content),
                )
        self.assertEqual(
            self.destination.with_suffix(".zip.part").read_bytes(), self.content[:8]
        )
        self.assertFalse(self.destination.exists())

    def test_oversized_response_is_not_published(self) -> None:
        with patch(
            "urllib.request.urlopen",
            return_value=Response(self.content + b"extra", 200),
        ):
            with self.assertRaisesRegex(RuntimeError, "超过锁定大小"):
                download(
                    "https://example.invalid/tool",
                    self.destination,
                    self.checksum,
                    expected_size=len(self.content),
                )
        self.assertFalse(self.destination.exists())

    def test_wrong_total_size_is_rejected(self) -> None:
        self.destination.with_suffix(".zip.part").write_bytes(self.content[:8])
        response = Response(
            self.content[8:], 206, f"bytes 8-{len(self.content) - 1}/999"
        )
        with patch("urllib.request.urlopen", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "总大小"):
                download(
                    "https://example.invalid/tool",
                    self.destination,
                    self.checksum,
                    expected_size=len(self.content),
                )
        self.assertFalse(self.destination.exists())

    def test_corrupt_complete_partial_restarts_instead_of_requesting_past_end(
        self,
    ) -> None:
        self.destination.with_suffix(".zip.part").write_bytes(b"x" * len(self.content))
        with patch(
            "urllib.request.urlopen", return_value=Response(self.content, 200)
        ) as request:
            download(
                "https://example.invalid/tool",
                self.destination,
                self.checksum,
                expected_size=len(self.content),
            )
        self.assertIsNone(request.call_args.args[0].get_header("Range"))

    def test_redirect_to_untrusted_host_is_rejected(self) -> None:
        response = Response(self.content, 200)
        response.geturl = lambda: "https://example.invalid/tool"
        with patch("urllib.request.urlopen", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "官方来源"):
                download(
                    "https://files.pythonhosted.org/tool",
                    self.destination,
                    self.checksum,
                    allowed_host="files.pythonhosted.org",
                )
        self.assertFalse(self.destination.exists())


if __name__ == "__main__":
    unittest.main()
