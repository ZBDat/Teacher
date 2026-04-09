"""Abstract base class for all agent tools."""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Base class that every tool must inherit from.

    To add a new tool:
    1. Create a subclass of BaseTool.
    2. Implement ``name``, ``description``, ``parameters``, and ``run``.
    3. Register the tool via ``ToolRegistry.register()``.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name used in OpenAI function definitions."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description shown to the model."""

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """JSON Schema object describing the tool's parameters."""

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any:
        """Execute the tool and return a result."""

    def to_openai_function(self) -> dict:
        """Return the OpenAI function-calling schema for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
