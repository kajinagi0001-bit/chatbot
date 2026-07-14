import re

from typing import Callable

from .command_result import CommandResult


class MemoryService:
    """家族ごとの記憶、共通メモ、好みを管理する。"""

    def __init__(
        self,
        state: dict,
        current_member: str,
        save: Callable[[], None],
        get_member: Callable[[str], dict],
    ):
        self.state = state
        self.current_member = current_member
        self.save = save
        self.get_member = get_member

    def handle_command(self, text: str) -> CommandResult:
        shared_result = self._handle_shared_memory(text)

        if shared_result.handled:
            return shared_result

        personal_result = self._handle_personal_memory(text)

        if personal_result.handled:
            return personal_result

        preference_result = self._handle_preference(text)

        if preference_result.handled:
            return preference_result

        return CommandResult(False)

    def personal_notes(
        self,
        member_id: str | None = None,
    ) -> list[str]:
        target = member_id or self.current_member

        return list(
            self.get_member(target).get(
                "notes",
                [],
            )
        )

    def preferences(
        self,
        member_id: str | None = None,
    ) -> list[str]:
        target = member_id or self.current_member

        return list(
            self.get_member(target).get(
                "preferences",
                [],
            )
        )

    def shared_notes(self) -> list[str]:
        return list(
            self.state["shared"].get(
                "notes",
                [],
            )
        )

    def _handle_shared_memory(
        self,
        text: str,
    ) -> CommandResult:
        prefixes = [
            "家族のこととして",
            "家族のメモとして",
            "家族共通で",
        ]

        prefix = next(
            (
                candidate
                for candidate in prefixes
                if text.startswith(candidate)
            ),
            None,
        )

        if prefix is None:
            return CommandResult(False)

        if not self._contains_memory_request(text):
            return CommandResult(False)

        note = text[len(prefix):]
        note = self._clean_memory_text(note)

        if not note:
            return CommandResult(False)

        notes = self.state["shared"]["notes"]
        added = self._append_unique(notes, note)

        if added:
            self.save()

        return CommandResult(
            True,
            (
                f"家族のこととして"
                f"「{note}」を覚えておくね。"
            ),
        )

    def _handle_personal_memory(
        self,
        text: str,
    ) -> CommandResult:
        if not self._contains_memory_request(text):
            return CommandResult(False)

        note = self._clean_memory_text(text)

        if not note:
            return CommandResult(False)

        member = self.get_member(
            self.current_member
        )
        notes = member.setdefault(
            "notes",
            [],
        )

        added = self._append_unique(
            notes,
            note,
        )

        if added:
            self.save()

        return CommandResult(
            True,
            f"「{note}」を覚えておくね。",
        )

    def _handle_preference(
        self,
        text: str,
    ) -> CommandResult:
        preference = self._extract_preference(text)

        if preference is None:
            return CommandResult(False)

        member = self.get_member(
            self.current_member
        )
        preferences = member.setdefault(
            "preferences",
            [],
        )

        added = self._append_unique(
            preferences,
            preference,
        )

        if added:
            self.save()

        return CommandResult(
            True,
            f"「{preference}」って覚えておくね。",
        )

    @staticmethod
    def _contains_memory_request(
        text: str,
    ) -> bool:
        return any(
            phrase in text
            for phrase in [
                "覚えておいて",
                "覚えといて",
                "記憶して",
                "メモして",
            ]
        )

    @staticmethod
    def _clean_memory_text(text: str) -> str:
        cleaned = text.strip(" 、。")

        for phrase in [
            "覚えておいて",
            "覚えといて",
            "記憶して",
            "メモして",
        ]:
            cleaned = cleaned.replace(
                phrase,
                "",
            )

        cleaned = re.sub(
            r"(?:って|と)$",
            "",
            cleaned,
        )

        return cleaned.strip(" 、。")

    @staticmethod
    def _extract_preference(
        text: str,
    ) -> str | None:
        patterns = [
            r"^(.+?)が好き(?:です)?[。]?$",
            r"^(.+?)が苦手(?:です)?[。]?$",
            r"^(.+?)は嫌い(?:です)?[。]?$",
        ]

        for pattern in patterns:
            if re.match(pattern, text):
                return text.strip(" 。")

        return None

    @staticmethod
    def _append_unique(
        values: list[str],
        value: str,
    ) -> bool:
        if value in values:
            return False

        values.append(value)
        return True