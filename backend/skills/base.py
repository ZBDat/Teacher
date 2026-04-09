"""Abstract base class for all agent skills.

Skills are higher-level capabilities built on top of one or more tools.
They encapsulate multi-step workflows that the agent can invoke.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseSkill(ABC):
    """Base class that every skill must inherit from.

    To add a new skill:
    1. Create a subclass of BaseSkill.
    2. Implement ``name``, ``description``, and ``execute``.
    3. Register the skill via ``SkillRegistry.register()``.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this skill does."""

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Execute the skill and return a result."""
