import re
import uuid

from datetime import datetime
from typing import Callable

from .command_result import CommandResult


class ScheduleService:
    """予定の登録、検索、表示を担当する。"""

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
        if (
            "予定" in text
            and any(
                word in text
                for word in ["入れて", "追加", "登録"]
            )
        ):
            return self._add_event(text)

        if (
            "予定" in text
            and any(
                word in text
                for word in ["教えて", "見せて", "確認"]
            )
        ):
            return self._show_events(text)

        return CommandResult(False)

    def events_for(
        self,
        owner: str | None = None,
    ) -> list[dict]:
        events = self.state["events"]

        if owner:
            events = [
                event
                for event in events
                if event["owner"] in {owner, "家族"}
            ]

        return sorted(
            events,
            key=lambda event: (
                event.get("date", ""),
                event.get("time", ""),
            ),
        )

    def format_event(self, event: dict) -> str:
        date = event.get("date") or "日付未設定"
        time = event.get("time")
        title = event.get("title") or "予定"

        if time:
            return f"{date}{time}に{title}"

        return f"{date}に{title}"

    def _add_event(
        self,
        text: str,
    ) -> CommandResult:
        owner = self._extract_owner(text)
        title = self._clean_schedule_title(
            self._extract_schedule_title(text)
        )

        return self.add_event(
            title=title,
            date=self._extract_date_label(text),
            time=self._extract_time(text),
            owner=owner,
        )

    def _show_events(
        self,
        text: str,
    ) -> CommandResult:
        owner = (
            "家族"
            if "家族" in text or "全員" in text
            else None
        )

        return self.show_events(owner=owner)

    def _extract_owner(
        self,
        text: str,
    ) -> str | None:
        match = re.match(r"^(.+?)の予定", text)

        if not match:
            return None

        name = match.group(1).strip()

        if any(
            label in name
            for label in [
                "今日",
                "明日",
                "明後日",
                "来週",
                "毎週",
            ]
        ):
            return None

        if re.search(r"\d{1,2}(?:時|:)", name):
            return None

        if name in {"私", "わたし", "自分"}:
            return self.current_member

        if name == "家族":
            return "家族"

        member_id = self.normalize_member_id(name)
        member = self.get_member(member_id)
        member["display_name"] = name

        return member_id

    def _extract_schedule_title(
        self,
        text: str,
    ) -> str:
        match = re.search(
            r"(?:に|から)?(.+?)の予定",
            text,
        )

        if match:
            return match.group(1).strip()

        return (
            self._extract_after_keywords(
                text,
                [
                    "予定に",
                    "予定として",
                    "登録",
                    "追加",
                ],
            )
            or text
        )

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
    def _extract_date_label(text: str) -> str:
        for label in [
            "今日",
            "明日",
            "明後日",
            "来週",
            "毎週",
        ]:
            if label in text:
                return label

        match = re.search(
            r"(\d{1,2})月(\d{1,2})日",
            text,
        )

        if match:
            return (
                f"{match.group(1)}月"
                f"{match.group(2)}日"
            )

        return "日付未設定"

    @staticmethod
    def _extract_time(text: str) -> str:
        match = re.search(
            r"(\d{1,2})(?:時|:)(\d{0,2})",
            text,
        )

        if not match:
            return ""

        minute = match.group(2) or "00"

        return (
            f"{int(match.group(1)):02d}:"
            f"{int(minute):02d}"
        )

    @staticmethod
    def _clean_schedule_title(text: str) -> str:
        cleaned = text

        for word in [
            "予定",
            "入れて",
            "追加して",
            "登録して",
            "今日",
            "明日",
            "明後日",
            "来週",
            "毎週",
        ]:
            cleaned = cleaned.replace(word, "")

        # 「7月20日」のような具体的な日付を除去
        cleaned = re.sub(
            r"\d{1,2}月\d{1,2}日",
            "",
            cleaned,
        )

        cleaned = re.sub(
            r"\d{1,2}(?:時|:)\d{0,2}",
            "",
            cleaned,
        )
        cleaned = re.sub(
            r"^[にのを]+",
            "",
            cleaned,
        )
        cleaned = re.sub(
            r"[にのを]+$",
            "",
            cleaned,
        )

        return cleaned.strip(" 、。") or "予定"

    def _owner_name(self, owner: str) -> str:
        if owner == "家族":
            return "家族"

        return self.get_member(owner)["display_name"]

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex[:12]

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(
            timespec="seconds"
        )
    
    def add_event(
        self,
        title: str,
        date: str = "日付未設定",
        time: str = "",
        owner: str | None = None,
        note: str = "",
    ) -> CommandResult:
        title = title.strip(" 、。")
        date = date.strip(" 、。") or "日付未設定"
        time = time.strip()
        note = note.strip()

        if not title:
            return CommandResult(
                False,
                "予定の内容が分からなかったよ。",
            )

        normalized_time = self._normalize_time(time)

        if normalized_time is None:
            return CommandResult(
                False,
                "予定の時刻を確認できなかったよ。",
            )

        owner_id = self._resolve_owner(owner)

        event = {
            "id": self._new_id(),
            "owner": owner_id,
            "title": title,
            "date": date,
            "time": normalized_time,
            "note": note,
            "created_at": self._now(),
        }

        self.state["events"].append(event)
        self.save()

        return CommandResult(
            True,
            (
                f"{self._owner_name(owner_id)}の予定に"
                f"「{self.format_event(event)}」を入れたよ。"
            ),
        )

    def _resolve_owner(
        self,
        owner: str | None,
    ) -> str:
        if owner is None:
            return self.current_member

        owner = owner.strip()

        if not owner or owner in {
            "私",
            "わたし",
            "自分",
        }:
            return self.current_member

        if owner == "家族":
            return "家族"

        owner_id = self.normalize_member_id(owner)
        member = self.get_member(owner_id)
        member["display_name"] = owner

        return owner_id

    @staticmethod
    def _normalize_time(
        time: str,
    ) -> str | None:
        if not time:
            return ""

        match = re.fullmatch(
            r"(\d{1,2})(?::|時)(\d{0,2})",
            time,
        )

        if not match:
            return None

        hour = int(match.group(1))
        minute = int(match.group(2) or "0")

        if not 0 <= hour <= 23:
            return None

        if not 0 <= minute <= 59:
            return None

        return f"{hour:02d}:{minute:02d}"

    def show_events(
        self,
        owner: str | None = None,
        limit: int = 6,
    ) -> CommandResult:
        if owner in {
            "家族",
            "全員",
        }:
            owner_id = None
        elif owner is None:
            owner_id = self.current_member
        else:
            owner_id = self._resolve_owner(owner)

        events = self.events_for(owner_id)[:limit]

        if not events:
            return CommandResult(
                True,
                "今のところ予定は入っていないよ。",
            )

        formatted = "。".join(
            self.format_event(event)
            for event in events
        )

        return CommandResult(
            True,
            f"予定は、{formatted}。",
        )