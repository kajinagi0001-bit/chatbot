import re
import uuid

from datetime import datetime
from typing import Callable

from .command_result import CommandResult


class ShoppingService:
    """買い物リストの操作と自然言語コマンド処理を担当する。"""

    def __init__(
        self,
        state: dict,
        current_member: str,
        save: Callable[[], None],
    ):
        self.state = state
        self.current_member = current_member
        self.save = save

    def handle_command(self, text: str) -> CommandResult:
        add_result = self._handle_add(text)
        if add_result.handled:
            return add_result

        show_result = self._handle_show(text)
        if show_result.handled:
            return show_result

        complete_result = self._handle_complete(text)
        if complete_result.handled:
            return complete_result

        return CommandResult(False)

    def active_item_names(self) -> list[str]:
        return [
            item["text"]
            for item in self.state["shopping_list"]
            if not item.get("done")
        ]

    def _handle_add(self, text: str) -> CommandResult:
        if not (
            "買い物" in text
            and any(
                word in text
                for word in ["入れて", "追加", "買う"]
            )
        ):
            return CommandResult(False)

        item = self._extract_after_keywords(
            text,
            [
                "買い物リストに",
                "買い物メモに",
                "買い物に",
            ],
        ) or text

        item = self._clean_item(item)

        if not item:
            return CommandResult(False)

        self.state["shopping_list"].append(
            {
                "id": self._new_id(),
                "text": item,
                "added_by": self.current_member,
                "done": False,
                "created_at": self._now(),
            }
        )

        self.save()

        return CommandResult(
            True,
            f"買い物メモに「{item}」を入れたよ。",
        )

    def _handle_show(self, text: str) -> CommandResult:
        if not (
            "買い物" in text
            and any(
                word in text
                for word in ["見せて", "教えて", "リスト"]
            )
        ):
            return CommandResult(False)

        items = self.active_item_names()

        if not items:
            return CommandResult(
                True,
                "買い物メモは空だよ。",
            )

        return CommandResult(
            True,
            "買い物メモは、" + "、".join(items) + "だよ。",
        )

    def _handle_complete(self, text: str) -> CommandResult:
        match = re.match(
            r"^(.+?)(?:を)?(?:買った|買いました)$",
            text,
        )

        if not match:
            return CommandResult(False)

        item_text = match.group(1).strip(" 、。")
        item_text = re.sub(
            r"[をは]$",
            "",
            item_text,
        ).strip()

        for item in self.state["shopping_list"]:
            if item.get("done"):
                continue

            if item_text not in item["text"]:
                continue

            item["done"] = True
            item["done_at"] = self._now()

            self.save()

            return CommandResult(
                True,
                f"うん、「{item['text']}」は買ったことにしたよ。",
            )

        return CommandResult(False)

    @staticmethod
    def _extract_after_keywords(
        text: str,
        keywords: list[str],
    ) -> str | None:
        for keyword in keywords:
            if keyword in text:
                return text.split(
                    keyword,
                    1,
                )[1].strip(" 、。")

        return None

    @staticmethod
    def _clean_item(text: str) -> str:
        cleaned = text

        for word in [
            "入れて",
            "追加して",
            "追加",
            "買う",
        ]:
            cleaned = cleaned.replace(word, "")

        cleaned = re.sub(
            r"[をにへ]+$",
            "",
            cleaned.strip(" 、。"),
        )

        return cleaned.strip()

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex[:12]

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(
            timespec="seconds"
        )