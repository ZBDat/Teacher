"""Tool and Skill registries used by the agent loop."""

from __future__ import annotations

from typing import Dict, Type

from backend.tools.base import BaseTool
from backend.skills.base import BaseSkill


class ToolRegistry:
    """Maintains a mapping of tool name → tool instance.

    Usage::

        registry = ToolRegistry()
        registry.register(PdfToMarkdownTool())

        # Retrieve later:
        tool = registry.get("pdf_to_markdown")
        result = await tool.run(file_path="/tmp/hw.pdf")
    """

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register *tool*.  Raises ``ValueError`` if the name is already taken."""
        if tool.name in self._tools:
            raise ValueError(f"A tool named '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        """Return the tool with *name* or raise ``KeyError``."""
        return self._tools[name]

    def all(self) -> list[BaseTool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def to_openai_tools(self) -> list[dict]:
        """Return the list of OpenAI function definitions for all registered tools."""
        return [t.to_openai_function() for t in self._tools.values()]


class SkillRegistry:
    """Maintains a mapping of skill name → skill instance.

    Usage::

        registry = SkillRegistry()
        registry.register(GradingSkill())

        skill = registry.get("grading")
        result = await skill.execute(submission="…", rubric="…")
    """

    def __init__(self) -> None:
        self._skills: Dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        """Register *skill*.  Raises ``ValueError`` if the name is already taken."""
        if skill.name in self._skills:
            raise ValueError(f"A skill named '{skill.name}' is already registered.")
        self._skills[skill.name] = skill

    def get(self, name: str) -> BaseSkill:
        """Return the skill with *name* or raise ``KeyError``."""
        return self._skills[name]

    def all(self) -> list[BaseSkill]:
        """Return all registered skills."""
        return list(self._skills.values())
