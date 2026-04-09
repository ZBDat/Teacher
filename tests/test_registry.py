"""Tests for the tool and skill registry."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.agent.registry import SkillRegistry, ToolRegistry
from backend.tools.base import BaseTool
from backend.skills.base import BaseSkill


# ---------------------------------------------------------------------------
# Fixtures – minimal concrete implementations
# ---------------------------------------------------------------------------


class EchoTool(BaseTool):
    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Returns the input unchanged."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        }

    async def run(self, text: str, **_) -> dict:
        return {"echo": text}


class AnotherTool(BaseTool):
    @property
    def name(self) -> str:
        return "another"

    @property
    def description(self) -> str:
        return "Another tool."

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def run(self, **_) -> dict:
        return {}


class EchoSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "echo_skill"

    @property
    def description(self) -> str:
        return "Skill that echoes."

    async def execute(self, **kwargs):
        return kwargs


# ---------------------------------------------------------------------------
# ToolRegistry tests
# ---------------------------------------------------------------------------


def test_tool_registry_register_and_get():
    registry = ToolRegistry()
    tool = EchoTool()
    registry.register(tool)
    assert registry.get("echo") is tool


def test_tool_registry_duplicate_raises():
    registry = ToolRegistry()
    registry.register(EchoTool())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(EchoTool())


def test_tool_registry_get_unknown_raises():
    registry = ToolRegistry()
    with pytest.raises(KeyError):
        registry.get("nonexistent")


def test_tool_registry_all():
    registry = ToolRegistry()
    registry.register(EchoTool())
    registry.register(AnotherTool())
    names = {t.name for t in registry.all()}
    assert names == {"echo", "another"}


def test_tool_to_openai_tools():
    registry = ToolRegistry()
    registry.register(EchoTool())
    schemas = registry.to_openai_tools()
    assert len(schemas) == 1
    schema = schemas[0]
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "echo"
    assert "parameters" in schema["function"]


# ---------------------------------------------------------------------------
# SkillRegistry tests
# ---------------------------------------------------------------------------


def test_skill_registry_register_and_get():
    registry = SkillRegistry()
    skill = EchoSkill()
    registry.register(skill)
    assert registry.get("echo_skill") is skill


def test_skill_registry_duplicate_raises():
    registry = SkillRegistry()
    registry.register(EchoSkill())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(EchoSkill())


def test_skill_registry_all():
    registry = SkillRegistry()
    registry.register(EchoSkill())
    assert len(registry.all()) == 1


# ---------------------------------------------------------------------------
# BaseTool.to_openai_function
# ---------------------------------------------------------------------------


def test_base_tool_openai_function_schema():
    tool = EchoTool()
    schema = tool.to_openai_function()
    assert schema["type"] == "function"
    fn = schema["function"]
    assert fn["name"] == "echo"
    assert fn["description"] == "Returns the input unchanged."
    assert fn["parameters"]["required"] == ["text"]
