"""确认检查入口拒绝漂移，且不把未知业务接口纳入 M1。"""

import unittest

from check_contracts import require_equal, verify_catalog, verify_operation_count


class ContractChecksTests(unittest.TestCase):
    def test_operation_count_and_unique_ids_are_checked(self) -> None:
        schema = {
            "paths": {
                f"/api/v1/check-{index}/": {
                    "get": {"operationId": f"operation_{index}"}
                }
                for index in range(83)
            }
        }
        verify_operation_count(schema, "workbench")
        with self.assertRaises(ValueError):
            verify_operation_count(
                {"paths": dict(list(schema["paths"].items())[:-1])}, "workbench"
            )
        schema["paths"]["/api/v1/check-1/"]["get"]["operationId"] = "operation_0"
        with self.assertRaises(ValueError):
            verify_operation_count(schema, "workbench")

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

    def test_catalog_includes_permanent_delete(self) -> None:
        schema = {
            "paths": {
                "/api/v1/projects/{project_id}/": {
                    "delete": {"operationId": "projects_delete"}
                }
            }
        }
        row = "| workbench | DELETE | `/api/v1/projects/{project_id}/` | `projects_delete` | 永久删除 |"
        verify_catalog(schema, row, "workbench")
        with self.assertRaises(ValueError):
            verify_catalog(schema, row.replace("DELETE", "GET"), "workbench")


if __name__ == "__main__":
    unittest.main()
