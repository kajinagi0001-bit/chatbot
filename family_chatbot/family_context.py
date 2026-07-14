from typing import Callable


class FamilyContextBuilder:
    """LLMへ渡す家族情報のコンテキストを生成する。"""

    def __init__(
        self,
        state: dict,
        current_member: str,
        get_member: Callable[[str], dict],
        events_for: Callable[[str | None], list[dict]],
        format_event: Callable[[dict], str],
    ):
        self.state = state
        self.current_member = current_member
        self.get_member = get_member
        self.events_for = events_for
        self.format_event = format_event

    def build(self) -> str:
        member = self.get_member(self.current_member)

        display_name = member.get(
            "display_name",
            self.current_member,
        )

        sections = [
            f"今話している家族: {display_name}",
        ]

        self._append_list_section(
            sections,
            "この人について覚えていること",
            member.get("notes", []),
        )

        self._append_list_section(
            sections,
            "この人の好み",
            member.get("preferences", []),
        )

        shared_notes = self.state.get(
            "shared",
            {},
        ).get(
            "notes",
            [],
        )

        self._append_list_section(
            sections,
            "家族共通の情報",
            shared_notes,
        )

        events = self.events_for(
            self.current_member
        )[:6]

        if events:
            formatted_events = [
                self.format_event(event)
                for event in events
            ]

            self._append_list_section(
                sections,
                "現在の予定",
                formatted_events,
            )

        shopping_items = [
            item["text"]
            for item in self.state.get(
                "shopping_list",
                [],
            )
            if not item.get("done")
        ]

        self._append_list_section(
            sections,
            "現在の買い物メモ",
            shopping_items,
        )

        pending_messages = [
            message
            for message in self.state.get(
                "messages",
                [],
            )
            if message.get("to")
            == self.current_member
            and not message.get("delivered")
        ]

        if pending_messages:
            sections.append(
                "未確認の伝言がある。"
                "ただし、ユーザーが伝言を尋ねるまでは"
                "内容を勝手に読み上げないこと。"
            )

        return "\n".join(sections)

    @staticmethod
    def _append_list_section(
        sections: list[str],
        title: str,
        values: list[str],
    ) -> None:
        if not values:
            return

        sections.append(
            f"{title}: "
            + " / ".join(values)
        )