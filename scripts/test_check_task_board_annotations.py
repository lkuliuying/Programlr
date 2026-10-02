import copy
import json
import unittest

from check_task_board_annotations import ANNOTATION, validate


class AnnotationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(ANNOTATION.read_text(encoding="utf-8"))

    def test_current_references(self) -> None:
        validate(self.data)

    def test_drift_is_rejected(self) -> None:
        self.data["nodes"][0]["source_ref"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "摘要漂移"):
            validate(self.data)

    def test_out_of_range_is_rejected(self) -> None:
        self.data["nodes"][0]["source_ref"]["end_line"] = 10**9
        with self.assertRaisesRegex(ValueError, "行号越界"):
            validate(self.data)

    def test_unsafe_path_is_rejected(self) -> None:
        for path in ["../outside.py", "C:/outside.py", "/outside.py", "..\\outside.py"]:
            with self.subTest(path=path):
                data = copy.deepcopy(self.data)
                data["nodes"][0]["source_ref"]["file_path"] = path
                with self.assertRaisesRegex(ValueError, "路径越界"):
                    validate(data)

    def test_dangling_relation_is_rejected(self) -> None:
        self.data["edges"][0]["to"] = "nonexistent"
        with self.assertRaisesRegex(ValueError, "不存在的节点"):
            validate(self.data)

    def test_framework_rule_is_required(self) -> None:
        self.data["framework_rules"] = {}
        with self.assertRaisesRegex(ValueError, "缺少规则依据"):
            validate(self.data)


if __name__ == "__main__":
    unittest.main()
