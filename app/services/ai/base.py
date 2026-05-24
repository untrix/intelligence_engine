"""Abstract base class defining the AI provider interface for tool-calling conversations."""

from abc import ABC, abstractmethod
from typing import Awaitable, Callable


class AIProvider(ABC):
    """Base class for AI providers with tool-calling support."""

    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.extra_config = kwargs

    @abstractmethod
    async def run_thread(
        self,
        messages: list[dict],
        model: str,
        tools: list[dict],
        tool_executor: Callable[[str, dict], Awaitable[str]],
        on_message: Callable[[dict], Awaitable[None]],
    ) -> dict:
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        ...
