"""
Anthropic provider adapter.
Supports all Claude models via the official anthropic SDK.
"""

import anthropic as _anthropic

from .base import BaseProvider, ChatResponse, ToolCall, ToolParam


class AnthropicProvider(BaseProvider):
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str | None = None,
        max_tokens: int = 4096,
    ):
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client    = _anthropic.Anthropic(**kwargs)
        self._model     = model
        self._max_tokens = max_tokens

    @property
    def name(self) -> str:
        return f"Anthropic ({self._model})"

    def chat(
        self,
        system: str,
        messages: list[dict],
        tools: list[ToolParam] | None = None,
    ) -> ChatResponse:
        kwargs = dict(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=self._convert_messages_to_anthropic(messages),
        )
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        response = self._client.messages.create(**kwargs)

        text = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    inputs=block.input,
                ))

        stop_reason = "tool_use" if tool_calls else "end_turn"
        return ChatResponse(text=text, tool_calls=tool_calls, stop_reason=stop_reason)

    # ── Anthropic-specific message format ─────────────────────────────────────

    def _convert_messages_to_anthropic(self, messages: list[dict]) -> list[dict]:
        """
        Our neutral format maps cleanly to Anthropic's format.
        Tool results need special handling.
        """
        converted = []
        for msg in messages:
            role    = msg["role"]
            content = msg["content"]

            if isinstance(content, str):
                converted.append({"role": role, "content": content})
                continue

            # List content — may include tool_use blocks or tool_result blocks
            if isinstance(content, list):
                anthropic_content = []
                for item in content:
                    if isinstance(item, dict):
                        t = item.get("type")
                        if t == "tool_result":
                            anthropic_content.append({
                                "type": "tool_result",
                                "tool_use_id": item["tool_call_id"],
                                "content": item["content"],
                            })
                        elif t == "tool_use":
                            anthropic_content.append(item)
                        elif t == "text":
                            anthropic_content.append(item)
                        else:
                            anthropic_content.append(item)
                    else:
                        anthropic_content.append(item)
                converted.append({"role": role, "content": anthropic_content})
                continue

            converted.append({"role": role, "content": content})

        return converted

    def _convert_tools(self, tools: list[ToolParam]) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]

    def build_tool_use_content(self, response_raw) -> list:
        """
        Return the raw content blocks from a response so they can be stored
        in history and replayed correctly on the next turn.
        Used by the loop when it needs to store assistant tool_use blocks.
        """
        return response_raw

    def make_assistant_history_entry(self, chat_response: ChatResponse, raw_blocks) -> dict:
        """
        Anthropic needs the raw content blocks (including tool_use objects) in
        the assistant history entry, not just the text.
        """
        return {"role": "assistant", "content": raw_blocks}

    def make_tool_result_entry(self, results: list) -> dict:
        """Format tool results as a user turn for Anthropic."""
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_call_id": r.tool_call_id,
                    "content": r.content,
                }
                for r in results
            ],
        }
