import re
import uuid

from datetime import datetime
from typing import Callable

from .command_result import CommandResult


class MessageService:
    """家族間の伝言登録と受け取りを担当する。"""

    def __init__(
        self,
        state: dict,
        current_member: str,
        save: Callable[[], None],
        get_member: Callable[[str], dict],
        normalize_member_id: Callable[[str], str],
    ):
        self.state = state
        self.current_member = current_member
        self.save = save
        self.get_member = get_member
        self.normalize_member_id = normalize_member_id

    def handle_command(self, text: str) -> CommandResult:
        receive_result = self._handle_receive(text)

        if receive_result.handled:
            return receive_result

        send_result = self._handle_send(text)

        if send_result.handled:
            return send_result

        return CommandResult(False)

    def pending_messages_for(
        self,
        member_id: str,
    ) -> list[dict]:
        return [
            message
            for message in self.state["messages"]
            if message["to"] == member_id
            and not message.get("delivered")
        ]

    def _handle_send(self, text: str) -> CommandResult:
        match = re.match(
            r"^(.+?)に[、,]?\s*(.+?)(?:って)?伝えて[。]?$",
            text,
        )

        if not match:
            return CommandResult(False)

        recipient_name = match.group(1).strip()
        body = match.group(2).strip(" 、。")

        body = re.sub(
            r"(?:って)$",
            "",
            body,
        ).strip(" 、。")

        if not recipient_name or not body:
            return CommandResult(False)

        recipient_id = self.normalize_member_id(
            recipient_name
        )

        recipient = self.get_member(recipient_id)
        recipient["display_name"] = recipient_name

        self.state["messages"].append(
            {
                "id": self._new_id(),
                "from": self.current_member,
                "to": recipient_id,
                "text": body,
                "delivered": False,
                "created_at": self._now(),
            }
        )

        self.save()

        return CommandResult(
            True,
            f"{recipient_name}さんへの伝言を預かったよ。",
        )

    def _handle_receive(
        self,
        text: str,
    ) -> CommandResult:
        if not any(
            phrase in text
            for phrase in [
                "伝言ある",
                "伝言はある",
                "伝言を教えて",
                "メッセージある",
            ]
        ):
            return CommandResult(False)

        messages = self.pending_messages_for(
            self.current_member
        )

        if not messages:
            return CommandResult(
                True,
                "今のところ伝言はないよ。",
            )

        formatted_messages = []

        for message in messages:
            sender_name = self._member_name(
                message["from"]
            )

            formatted_messages.append(
                f"{sender_name}さんから、"
                f"「{message['text']}」"
            )

            message["delivered"] = True
            message["delivered_at"] = self._now()

        self.save()

        return CommandResult(
            True,
            "伝言は、"
            + "。".join(formatted_messages)
            + "。",
        )

    def _member_name(self, member_id: str) -> str:
        return self.get_member(
            member_id
        ).get(
            "display_name",
            member_id,
        )

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex[:12]

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(
            timespec="seconds"
        )