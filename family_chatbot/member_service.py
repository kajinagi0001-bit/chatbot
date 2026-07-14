import re

from typing import Callable

from .command_result import CommandResult


class MemberService:
    """家族メンバーの管理と現在の話者切り替えを担当する。"""

    def __init__(
        self,
        state: dict,
        save: Callable[[], None],
    ):
        self.state = state
        self.save = save

    @property
    def current_member(self) -> str:
        return self.state["current_member"]

    def handle_command(self, text: str) -> CommandResult:
        member_name = self._extract_member_name(text)

        if member_name is None:
            return CommandResult(False)

        member_id = self.normalize_member_id(member_name)
        member = self.get_member(member_id)

        member["display_name"] = member_name
        self.state["current_member"] = member_id

        self.save()

        return CommandResult(
            True,
            f"{member_name}さんとして話すね。",
        )

    def get_member(self, member_id: str) -> dict:
        members = self.state["members"]

        if member_id not in members:
            members[member_id] = self._default_member(
                member_id
            )

        member = members[member_id]

        member.setdefault(
            "display_name",
            member_id,
        )
        member.setdefault(
            "notes",
            [],
        )
        member.setdefault(
            "preferences",
            [],
        )

        return member

    def current_member_data(self) -> dict:
        return self.get_member(
            self.current_member
        )

    def display_name(
        self,
        member_id: str | None = None,
    ) -> str:
        target = member_id or self.current_member

        return self.get_member(target).get(
            "display_name",
            target,
        )

    @staticmethod
    def normalize_member_id(name: str) -> str:
        normalized = name.strip()

        normalized = re.sub(
            r"\s+",
            "_",
            normalized,
        )

        return normalized.lower()

    @staticmethod
    def _extract_member_name(
        text: str,
    ) -> str | None:
        patterns = [
            r"^私は(.+?)です[。]?$",
            r"^わたしは(.+?)です[。]?$",
            r"^僕は(.+?)です[。]?$",
            r"^ぼくは(.+?)です[。]?$",
            r"^(.+?)として話して[。]?$",
            r"^(.+?)に切り替えて[。]?$",
        ]

        for pattern in patterns:
            match = re.match(pattern, text)

            if not match:
                continue

            name = match.group(1).strip(" 、。")

            if name:
                return name

        return None

    @staticmethod
    def _default_member(
        member_id: str,
    ) -> dict:
        return {
            "display_name": member_id,
            "notes": [],
            "preferences": [],
        }