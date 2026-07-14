from dataclasses import dataclass


@dataclass
class CommandResult:
    handled: bool
    message: str | None = None