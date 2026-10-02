from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.learning.content import load_content


class Command(BaseCommand):
    help = "载入经过核对的教学内容；同版本漂移拒绝，历史版本保留。"

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            cards, exercises = load_content()
        except (OSError, ValueError):
            raise CommandError(
                "教学内容载入失败，请核对文件、结构与版本；没有覆盖旧内容。"
            ) from None
        self.stdout.write(f"教学内容就绪：{cards} 张卡片、{exercises} 道固定题。")
