import json
from pathlib import Path

import anthropic

from places_core.settings import settings

from .tools import TOOLS, dispatch_tool

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "system.md").read_text()

# The model specified in Claude_Instructions.md. Prompt caching is enabled
# for the static system prompt to reduce latency and token cost across
# the many short turns in a booking conversation.
_MODEL = "claude-sonnet-4-6"


def run_agent(
    user_message: str,
    conversation_history: list[dict],
    user_context: str | None = None,
) -> str:
    """Run one turn of the DeskMate agentic loop.

    Args:
        user_message: The raw message from the user.
        conversation_history: All prior turns for this session.
        user_context: Optional one-line context string injected into the first
            user message of a new session (e.g. user name and today's date).
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None)

    # If this is the first turn, prepend the user context as a hidden header so
    # the model knows who it is talking to without it appearing in the chat UI.
    if user_context and not conversation_history:
        first_content = f"[CONTEXT: {user_context}]\n\n{user_message}"
    else:
        first_content = user_message

    messages = conversation_history + [{"role": "user", "content": first_content}]

    while True:
        response = client.messages.create(
            model=_MODEL,
            max_tokens=4096,
            # Cache the static system prompt — saves tokens on every turn after
            # the first because the prompt content never changes.
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            return next(
                block.text for block in response.content if hasattr(block, "text")
            )

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = dispatch_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    }
                )

        messages.append({"role": "user", "content": tool_results})
