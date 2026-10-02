"""仅用于独立 5176/5177 验收的固定模型替身；不发起 HTTP 或执行导入源码。"""

import json
import os
from typing import Any
from unittest.mock import patch


def respond(
    config: Any, messages: list[dict[str, str]], **kwargs: Any
) -> tuple[str, str, None]:
    if (
        config.model != "m4-test-double"
        or config.base_url != "https://model-test.invalid/v1"
    ):
        raise RuntimeError("替身只接受专用测试配置。")
    context = json.loads(messages[1]["content"])
    reference = context["snippets"][0]["source_ref"]
    content = {
        "purpose": [
            {
                "kind": "source_fact",
                "text": "本地替身：所选接口的源码片段已传入。此文字只用于验收流程。",
                "source_refs": [reference],
            }
        ],
        "evidence": [
            {
                "kind": "source_fact",
                "text": "本地替身仅回显预览内的引用，未调用真实模型。",
                "source_refs": [reference],
            }
        ],
        "mechanism": [
            {
                "kind": "static_inference",
                "text": "静态关系需要回到源码核对，不能据此断言完整运行轨迹。",
                "source_refs": [reference],
            }
        ],
        "knowledge": [
            {
                "kind": "general_principle",
                "text": "输入校验用于在持久化前拒绝不符合约束的数据。",
                "source_refs": [],
            }
        ],
        "verification": [
            {
                "kind": "general_principle",
                "text": "请打开引用位置，复核文件和行号。这里没有实际执行业务请求。",
                "source_refs": [],
            }
        ],
    }
    return json.dumps(content, ensure_ascii=False), "m4-test-double", None


def main() -> None:
    if (
        os.environ.get("APP_PORT") not in {"5176", "5177"}
        or os.environ.get("MODEL_NAME") != "m4-test-double"
    ):
        raise RuntimeError("该入口只允许独立 M4/M5 本地验收配置。")
    import django

    django.setup()
    from config.celery import app

    with patch("apps.explanations.services.complete", side_effect=respond):
        app.worker_main(
            [
                "worker",
                "--loglevel=WARNING",
                "--concurrency=1",
                "--without-gossip",
                "--without-mingle",
            ]
        )


if __name__ == "__main__":
    main()
