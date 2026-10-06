from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.learning.content import load_cards_only


class Command(BaseCommand):
    help = "载入版本化知识卡片；不发布退役课程或练习，历史版本保留。"

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            cards = load_cards_only()
        except (OSError, ValueError):
            raise CommandError(
                "教学内容载入失败，请核对文件、结构与版本；没有覆盖旧内容。"
            ) from None
        self.stdout.write(f"知识内容就绪：{cards} 张卡片。")
