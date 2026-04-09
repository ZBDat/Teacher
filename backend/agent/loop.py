"""Core OpenAI-powered agent loop.

The loop:
1. Receives a user message (and optional conversation history).
2. Calls the OpenAI Chat Completions API with the registered tools exposed as
   function definitions.
3. If the model requests a tool call, dispatches it to the matching tool in the
   registry, appends the result, and loops.
4. Returns the final assistant text response together with the updated history.

Extending the agent
-------------------
- **Add a tool**: instantiate a ``BaseTool`` subclass and call
  ``agent.tool_registry.register(my_tool)``.
- **Add a skill**: instantiate a ``BaseSkill`` subclass and call
  ``agent.skill_registry.register(my_skill)``.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from backend.agent.registry import SkillRegistry, ToolRegistry
from backend.tools.pdf_converter import PdfToMarkdownTool

logger = logging.getLogger(__name__)

# System prompt describing the agent's role
_SYSTEM_PROMPT = """You are an AI teaching assistant that helps teachers grade student assignments.

Your capabilities include:
- Reviewing and evaluating student submissions
- Converting PDF assignments to text for analysis
- Providing detailed feedback based on a rubric
- Summarising strengths and weaknesses

Always be encouraging, constructive, and objective in your feedback.
When grading, explain your reasoning clearly and refer to specific parts of the submission."""


class AgentLoop:
    """Stateless agent loop backed by OpenAI Chat Completions.

    Each call to ``run()`` is independent; conversation state is maintained by
    the caller (pass ``history`` in and receive an updated copy back).
    """

    def __init__(
        self,
        openai_client: AsyncOpenAI,
        model: str = "gpt-4o",
        system_prompt: str = _SYSTEM_PROMPT,
    ) -> None:
        self.client = openai_client
        self.model = model
        self.system_prompt = system_prompt

        # Registries – callers may inject tools/skills at any time
        self.tool_registry = ToolRegistry()
        self.skill_registry = SkillRegistry()

        # Register built-in tools
        self.tool_registry.register(PdfToMarkdownTool())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        user_message: str,
        history: list[dict] | None = None,
        max_tool_rounds: int = 5,
    ) -> dict:
        """Run one turn of the agent loop.

        Parameters
        ----------
        user_message:
            The latest message from the user.
        history:
            Previous conversation messages (list of OpenAI message dicts).
            Pass ``None`` or ``[]`` for a fresh conversation.
        max_tool_rounds:
            Safety limit on the number of consecutive tool-call rounds to
            prevent infinite loops.

        Returns
        -------
        dict with keys:
            ``reply``   – the assistant's final text response.
            ``history`` – the updated conversation history (append to next call).
        """
        messages: list[dict] = [{"role": "system", "content": self.system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        tools = self.tool_registry.to_openai_tools()

        for round_num in range(max_tool_rounds + 1):
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = await self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            assistant_message = choice.message

            # Always append the raw assistant message for faithful history
            messages.append(assistant_message.model_dump(exclude_unset=True))

            if choice.finish_reason == "tool_calls":
                if round_num == max_tool_rounds:
                    logger.warning("Reached max_tool_rounds (%d); stopping.", max_tool_rounds)
                    break
                # Dispatch all requested tool calls
                tool_results = await self._dispatch_tool_calls(
                    assistant_message.tool_calls  # type: ignore[arg-type]
                )
                messages.extend(tool_results)
                continue  # Let the model see the results

            # finish_reason is "stop" (or similar) – return the text reply
            reply = assistant_message.content or ""
            # Strip the leading system message from the returned history
            returned_history = messages[1:]
            return {"reply": reply, "history": returned_history}

        # Fallback – shouldn't normally be reached
        reply = (assistant_message.content or "").strip()
        return {"reply": reply, "history": messages[1:]}

    async def stream(
        self,
        user_message: str,
        history: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        """Streaming variant – yields text chunks as they arrive.

        Tool calls are handled silently (blocking); only the final text
        response is streamed.

        Yields
        ------
        str
            Text delta chunks from the assistant response.
        """
        # Run the full loop first (tool calls may happen), then stream the reply
        result = await self.run(user_message, history=history)
        for char in result["reply"]:
            yield char

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _dispatch_tool_calls(self, tool_calls: list) -> list[dict]:
        """Execute all *tool_calls* and return tool-role messages."""
        results: list[dict] = []
        for tc in tool_calls:
            tool_name = tc.function.name
            try:
                arguments = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            try:
                tool = self.tool_registry.get(tool_name)
                output = await tool.run(**arguments)
                content = json.dumps(output, ensure_ascii=False)
            except KeyError:
                content = json.dumps({"error": f"Unknown tool: {tool_name}"})
            except Exception as exc:  # noqa: BLE001
                logger.exception("Tool '%s' raised an exception.", tool_name)
                content = json.dumps({"error": str(exc)})

            results.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": content,
                }
            )
        return results
