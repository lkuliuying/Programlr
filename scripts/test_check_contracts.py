"""确认检查入口拒绝漂移，且不把未知业务接口纳入 M1。"""

import unittest

from check_contracts import require_equal, verify_catalog


class ContractChecksTests(unittest.TestCase):
    def test_line_endings_are_portable(self) -> None:
        require_equal("a\r\nb\r\n", "a\nb\n", "契约")

    def test_stale_output_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "已漂移"):
            require_equal("changed", "original", "契约")

    def test_catalog_requires_exact_operations(self) -> None:
        schema = {"paths": {"/api/v1/csrf/": {"get": {"operationId": "csrf_retrieve"}}}}
        row = "| workbench | GET | `/api/v1/csrf/` | `csrf_retrieve` | 说明 |"
        verify_catalog(schema, row, "workbench")
        for invalid in (
            "",
            row.replace("GET", "POST"),
            row.replace("csrf_retrieve", "other"),
            row
            + "\n| workbench | POST | `/api/v1/projects/` | `projects_create` | 未来 |",
        ):
            with self.subTest(catalog=invalid), self.assertRaises(ValueError):
                verify_catalog(schema, invalid, "workbench")

    def test_catalog_includes_snapshot_patch(self) -> None:
        schema = {
            "paths": {
                "/api/v1/snapshots/{snapshot_id}/": {
                    "patch": {"operationId": "snapshots_rename"}
                }
            }
        }
        row = (
            "| workbench | PATCH | `/api/v1/snapshots/{snapshot_id}/` "
            "| `snapshots_rename` | 快照名称 |"
        )
        verify_catalog(schema, row, "workbench")
        with self.assertRaises(ValueError):
            verify_catalog(schema, row.replace("PATCH", "POST"), "workbench")


if __name__ == "__main__":
    unittest.main()
