import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class CommandResult:
    handled: bool
    message: str | None = None


@dataclass
class FamilyStore:
    path: Path
    state: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "FamilyStore":
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            try:
                state = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                state = {}
        else:
            state = {}

        store = cls(path=path, state=state)
        store._ensure_shape()
        return store

    @property
    def current_member(self) -> str:
        return self.state["current_member"]

    def save(self) -> None:
        self.path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    def context_for_prompt(self) -> str:
        member = self._member(self.current_member)
        shared = self.state["shared"]
        events = self.events_for(self.current_member)[:5]
        messages = self.messages_for(self.current_member)[:3]
        shopping_items = [item["text"] for item in self.state["shopping_list"] if not item.get("done")]

        lines = [
            f"今話している家族: {member['display_name']}",
            f"この人の好み: {self._join_or_none(member['preferences'])}",
            f"この人について覚えていること: {self._join_or_none(member['notes'])}",
            f"家族共通メモ: {self._join_or_none(shared['notes'])}",
        ]
        if events:
            lines.append("近い予定: " + " / ".join(self._format_event(event) for event in events))
        if shopping_items:
            lines.append("買い物メモ: " + "、".join(shopping_items[:8]))
        if messages:
            lines.append("未読の伝言: " + " / ".join(f"{msg['from']}さんから「{msg['text']}」" for msg in messages))
        return "\n".join(lines)

    def handle_command(self, text: str) -> CommandResult:
        normalized = text.strip()
        if not normalized:
            return CommandResult(False)

        result = self._handle_member_switch(normalized)
        if result.handled:
            return result

        result = self._handle_memory(normalized)
        if result.handled:
            return result

        result = self._handle_schedule(normalized)
        if result.handled:
            return result

        result = self._handle_shopping(normalized)
        if result.handled:
            return result

        result = self._handle_message(normalized)
        if result.handled:
            return result

        result = self._handle_show(normalized)
        if result.handled:
            return result

        return CommandResult(False)

    def events_for(self, owner: str | None = None) -> list[dict]:
        events = self.state["events"]
        if owner:
            events = [event for event in events if event["owner"] == owner or event["owner"] == "家族"]
        return sorted(events, key=lambda event: (event.get("date", ""), event.get("time", "")))

    def messages_for(self, member_id: str) -> list[dict]:
        display_name = self._member(member_id)["display_name"]
        return [
            message
            for message in self.state["messages"]
            if not message.get("delivered") and message.get("to") in {display_name, member_id}
        ]

    def _ensure_shape(self) -> None:
        self.state.setdefault("current_member", "guest")
        self.state.setdefault("members", {})
        self.state.setdefault("shared", {"notes": []})
        self.state.setdefault("events", [])
        self.state.setdefault("shopping_list", [])
        self.state.setdefault("messages", [])
        self._member(self.state["current_member"])

    def _member(self, member_id: str) -> dict:
        members = self.state["members"]
        if member_id not in members:
            members[member_id] = {
                "display_name": member_id,
                "preferences": [],
                "notes": [],
                "created_at": self._now(),
            }
        return members[member_id]

    def _handle_member_switch(self, text: str) -> CommandResult:
        patterns = [
            r"^(?:私は|わたしは)(?P<name>.+?)(?:です|だよ|だ)?$",
            r"^(?P<name>.+?)(?:に|へ)切り替えて$",
            r"^(?P<name>.+?)(?:として話して|として話す)$",
        ]
        for pattern in patterns:
            match = re.match(pattern, text)
            if not match:
                continue
            name = match.group("name").strip()
            if not name:
                return CommandResult(False)
            member_id = self._normalize_member_id(name)
            member = self._member(member_id)
            member["display_name"] = name
            self.state["current_member"] = member_id
            self.save()
            return CommandResult(True, f"わかった。今は{name}さんとして覚えておくね。")

        if text in {"今だれ", "今誰", "今の話者は"}:
            member = self._member(self.current_member)
            return CommandResult(True, f"今は{member['display_name']}さんとして話しているよ。")

        return CommandResult(False)

    def _handle_memory(self, text: str) -> CommandResult:
        match = re.match(r"^家族(?:のこととして)?(.+?)(?:を|って)?覚えて(?:おいて|て)$", text)
        if match:
            note = match.group(1).strip()
            self._append_unique(self.state["shared"]["notes"], note)
            self.save()
            return CommandResult(True, f"家族のメモとして「{note}」を覚えておくね。")

        match = re.match(r"^(.+?)(?:を|って)?覚えて(?:おいて|て)$", text)
        if match:
            note = match.group(1).strip()
            self._append_unique(self._member(self.current_member)["notes"], note)
            self.save()
            return CommandResult(True, f"うん、「{note}」って覚えておくね。")

        match = re.match(r"^(.+?)(?:が好き|好き)$", text)
        if match and len(text) <= 30:
            preference = match.group(1).strip() + "が好き"
            self._append_unique(self._member(self.current_member)["preferences"], preference)
            self.save()
            return CommandResult(True, f"いいね。「{preference}」って覚えておくね。")

        if text in {"私の記憶を見せて", "覚えていることを教えて"}:
            member = self._member(self.current_member)
            items = member["notes"] + member["preferences"]
            if not items:
                return CommandResult(True, "まだ個人メモはないよ。")
            return CommandResult(True, "今は、" + "、".join(items[:8]) + "って覚えているよ。")

        return CommandResult(False)

    def _handle_schedule(self, text: str) -> CommandResult:
        if "予定" in text and any(word in text for word in ["入れて", "追加", "登録"]):
            owner = self._extract_owner(text) or self.current_member
            title = self._extract_schedule_title(text)
            event = {
                "id": self._new_id(),
                "owner": owner,
                "title": self._clean_schedule_title(title),
                "date": self._extract_date_label(text),
                "time": self._extract_time(text),
                "note": "",
                "created_at": self._now(),
            }
            self.state["events"].append(event)
            self.save()
            owner_name = self._owner_name(owner)
            return CommandResult(True, f"{owner_name}の予定に「{self._format_event(event)}」を入れたよ。")

        if "予定" in text and any(word in text for word in ["教えて", "見せて", "確認"]):
            owner = None if "家族" in text or "全員" in text else self.current_member
            events = self.events_for(owner)[:6]
            if not events:
                return CommandResult(True, "今のところ予定は入っていないよ。")
            return CommandResult(True, "予定は、" + "。".join(self._format_event(event) for event in events) + "。")

        return CommandResult(False)

    def _handle_shopping(self, text: str) -> CommandResult:
        if "買い物" in text and any(word in text for word in ["入れて", "追加", "買う"]):
            item = self._extract_after_keywords(text, ["買い物リストに", "買い物メモに", "買い物に"]) or text
            item = self._clean_shopping_item(item)
            if not item:
                return CommandResult(False)
            self.state["shopping_list"].append(
                {"id": self._new_id(), "text": item, "added_by": self.current_member, "done": False, "created_at": self._now()}
            )
            self.save()
            return CommandResult(True, f"買い物メモに「{item}」を入れたよ。")

        if "買い物" in text and any(word in text for word in ["見せて", "教えて", "リスト"]):
            items = [item["text"] for item in self.state["shopping_list"] if not item.get("done")]
            if not items:
                return CommandResult(True, "買い物メモは空だよ。")
            return CommandResult(True, "買い物メモは、" + "、".join(items) + "だよ。")

        match = re.match(r"^(.+?)(?:買った|買いました)$", text)
        if match:
            item_text = match.group(1).strip()
            for item in self.state["shopping_list"]:
                if not item.get("done") and item_text in item["text"]:
                    item["done"] = True
                    item["done_at"] = self._now()
                    self.save()
                    return CommandResult(True, f"うん、「{item['text']}」は買ったことにしたよ。")

        return CommandResult(False)

    def _handle_message(self, text: str) -> CommandResult:
        match = re.match(r"^(?P<to>.+?)(?:に|へ)、?(?P<body>.+?)(?:って)?(?:伝えて|言っておいて)$", text)
        if match:
            to_name = match.group("to").strip()
            body = match.group("body").strip()
            sender = self._member(self.current_member)["display_name"]
            self.state["messages"].append(
                {"id": self._new_id(), "from": sender, "to": to_name, "text": body, "delivered": False, "created_at": self._now()}
            )
            self.save()
            suffix = "" if to_name.endswith("さん") else "さん"
            return CommandResult(True, f"{to_name}{suffix}への伝言として「{body}」を預かったよ。")

        if "伝言" in text and any(word in text for word in ["ある", "見せて", "教えて"]):
            messages = self.messages_for(self.current_member)
            if not messages:
                return CommandResult(True, "今のところ伝言はないよ。")
            for message in messages:
                message["delivered"] = True
                message["delivered_at"] = self._now()
            self.save()
            return CommandResult(
                True,
                "伝言があるよ。" + "。".join(f"{message['from']}さんから「{message['text']}」" for message in messages) + "。",
            )

        return CommandResult(False)

    def _handle_show(self, text: str) -> CommandResult:
        if text in {"家族を教えて", "家族メンバーを教えて"}:
            names = [member["display_name"] for member in self.state["members"].values()]
            return CommandResult(True, "登録されている家族は、" + "、".join(names) + "だよ。")
        return CommandResult(False)

    def _extract_owner(self, text: str) -> str | None:
        match = re.match(r"^(.+?)の予定", text)
        if match:
            name = match.group(1).strip()
            if any(label in name for label in ["今日", "明日", "明後日", "来週", "毎週"]) or re.search(r"\d{1,2}(?:時|:)", name):
                return None
            if name in {"私", "わたし", "自分"}:
                return self.current_member
            if name == "家族":
                return "家族"
            member_id = self._normalize_member_id(name)
            self._member(member_id)["display_name"] = name
            return member_id
        return None

    def _extract_schedule_title(self, text: str) -> str:
        match = re.search(r"(?:に|から)?(.+?)の予定", text)
        if match:
            return match.group(1).strip()
        return self._extract_after_keywords(text, ["予定に", "予定として", "登録", "追加"]) or text

    def _extract_after_keywords(self, text: str, keywords: list[str]) -> str | None:
        for keyword in keywords:
            if keyword in text:
                return text.split(keyword, 1)[1].strip(" 、。")
        return None

    def _extract_date_label(self, text: str) -> str:
        for label in ["今日", "明日", "明後日", "来週", "毎週"]:
            if label in text:
                return label
        match = re.search(r"(\d{1,2})月(\d{1,2})日", text)
        if match:
            return f"{match.group(1)}月{match.group(2)}日"
        return "日付未設定"

    def _extract_time(self, text: str) -> str:
        match = re.search(r"(\d{1,2})(?:時|:)(\d{0,2})", text)
        if not match:
            return ""
        minute = match.group(2) or "00"
        return f"{int(match.group(1)):02d}:{int(minute):02d}"

    def _clean_schedule_title(self, text: str) -> str:
        cleaned = text
        for word in ["予定", "入れて", "追加して", "登録して", "今日", "明日", "明後日", "来週", "毎週"]:
            cleaned = cleaned.replace(word, "")
        cleaned = re.sub(r"\d{1,2}(?:時|:)\d{0,2}", "", cleaned)
        cleaned = re.sub(r"^[にのを]+", "", cleaned)
        cleaned = re.sub(r"[にのを]+$", "", cleaned)
        return cleaned.strip(" 、。") or "予定"

    def _clean_shopping_item(self, text: str) -> str:
        cleaned = text.replace("入れて", "").replace("追加して", "").replace("買う", "")
        cleaned = re.sub(r"[をにへ]+$", "", cleaned.strip(" 、。"))
        return cleaned.strip()

    def _format_event(self, event: dict) -> str:
        date = event.get("date") or "日付未設定"
        time = event.get("time")
        title = event.get("title") or "予定"
        if time:
            return f"{date}{time}に{title}"
        return f"{date}に{title}"

    def _owner_name(self, owner: str) -> str:
        if owner == "家族":
            return "家族"
        return self._member(owner)["display_name"]

    def _normalize_member_id(self, name: str) -> str:
        return re.sub(r"\s+", "_", name.strip().lower())

    def _append_unique(self, items: list[str], value: str) -> None:
        if value and value not in items:
            items.append(value)

    def _join_or_none(self, values: list[str]) -> str:
        return "、".join(values[:8]) if values else "まだなし"

    def _new_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def _now(self) -> str:
        return datetime.now().isoformat(timespec="seconds")
