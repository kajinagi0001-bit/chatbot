from dataclasses import dataclass, field
from pathlib import Path

from .command_result import CommandResult
from .family_repository import (
    FamilyRepository,
    FamilyRepositoryProtocol,
)

from .family_context import FamilyContextBuilder
from .member_service import MemberService
from .memory_service import MemoryService
from .message_service import MessageService
from .schedule_service import ScheduleService
from .shopping_service import ShoppingService



@dataclass
class FamilyStore:
    path: Path
    state: dict = field(default_factory=dict)
    repository: FamilyRepositoryProtocol | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    @classmethod
    def load(
        cls,
        path: Path,
        repository: FamilyRepositoryProtocol | None = None,
    ) -> "FamilyStore":
        actual_repository = (
            repository
            if repository is not None
            else FamilyRepository(path)
        )

        state = actual_repository.load()

        store = cls(
            path=path,
            state=state,
            repository=actual_repository,
        )
        store._ensure_shape()

        return store

    @property
    def current_member(self) -> str:
        return self._member_service().current_member

    def save(self) -> None:
        if self.repository is None:
            self.repository = FamilyRepository(
                self.path
            )

        self.repository.save(self.state)

    def context_for_prompt(self) -> str:
        return self._context_builder().build()

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

    def events_for(
        self,
        owner: str | None = None,
    ) -> list[dict]:
        return self._schedule_service().events_for(owner)

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
        return self._member_service().get_member(
            member_id
        )

    def _handle_member_switch(
        self,
        text: str,
    ) -> CommandResult:
        return self._member_service().handle_command(text)

    def _handle_memory(
        self,
        text: str,
    ) -> CommandResult:
        return self._memory_service().handle_command(text)

    def _handle_schedule(
        self,
        text: str,
    ) -> CommandResult:
        return self._schedule_service().handle_command(text)

    def _handle_shopping(
        self,
        text: str,
    ) -> CommandResult:
        service = ShoppingService(
            state=self.state,
            current_member=self.current_member,
            save=self.save,
        )

        return service.handle_command(text)

    def _handle_message(
        self,
        text: str,
    ) -> CommandResult:
        return self._message_service().handle_command(text)

    def _handle_show(self, text: str) -> CommandResult:
        if text in {"家族を教えて", "家族メンバーを教えて"}:
            names = [member["display_name"] for member in self.state["members"].values()]
            return CommandResult(True, "登録されている家族は、" + "、".join(names) + "だよ。")
        return CommandResult(False)

    def _format_event(
        self,
        event: dict,
    ) -> str:
        return self._schedule_service().format_event(event)

    def _normalize_member_id(self, name: str) -> str:
        return self._member_service().normalize_member_id(name)
    
    def _schedule_service(self) -> ScheduleService:
        return ScheduleService(
            state=self.state,
            current_member=self.current_member,
            save=self.save,
            get_member=self._member,
            normalize_member_id=self._normalize_member_id,
        )
    
    def _message_service(self) -> MessageService:
        return MessageService(
            state=self.state,
            current_member=self.current_member,
            save=self.save,
            get_member=self._member,
            normalize_member_id=self._normalize_member_id,
        )
    
    def _memory_service(self) -> MemoryService:
        return MemoryService(
            state=self.state,
            current_member=self.current_member,
            save=self.save,
            get_member=self._member,
        )
    def _member_service(self) -> MemberService:
        return MemberService(
            state=self.state,
            save=self.save,
        )
    
    def _context_builder(
        self,
    ) -> FamilyContextBuilder:
        return FamilyContextBuilder(
            state=self.state,
            current_member=self.current_member,
            get_member=self._member,
            events_for=self.events_for,
            format_event=self._format_event,
        )
