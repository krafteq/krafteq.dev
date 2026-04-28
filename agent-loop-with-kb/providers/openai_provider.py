"""
OpenAI-compatible provider adapter.

Works with any provider that implements the OpenAI chat completions API:
  - OpenAI          (api_key_env: OPENAI_API_KEY)
  - Groq            (api_key_env: GROQ_API_KEY,    base_url: https://api.groq.com/openai/v1)
  - Together AI     (api_key_env: TOGETHER_API_KEY, base_url: https://api.together.xyz/v1)
  - Mistral         (api_key_env: MISTRAL_API_KEY,  base_url: https://api.mistral.ai/v1)
  - Ollama (local)  (api_key_env: unused,           base_url: http://localhost:11434/v1)
  - Any other OpenAI-compatible endpoint
"""

import json
from openai import OpenAI as _OpenAI

from .base import BaseProvider, ChatResponse, ToolCall, ToolParam


class OpenAIProvider(BaseProvider):
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str | None = None,
        max_tokens: int = 4096,
    ):
        kwargs = {"api_key": api_key or "ollama"}  # Ollama doesn't need a real key
        if base_url:
            kwargs["base_url"] = base_url
        self._client     = _OpenAI(**kwargs)
        self._model      = model
        self._max_tokens = max_tokens

    @property
    def name(self) -> str:
        return f"OpenAI-compatible ({self._model})"

    def chat(
        self,
        system: str,
        messages: list[dict],
        tools: list[ToolParam] | None = None,
    ) -> ChatResponse:
        oai_messages = self._convert_messages(system, messages)

        kwargs = dict(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=oai_messages,
        )
        if tools:
            kwargs["tools"] = self._convert_tools(tools)
            kwargs["tool_choice"] = "auto"

        response = self._client.chat.completions.create(**kwargs)
        choice   = response.choices[0]
        msg      = choice.message

        text = msg.content or ""
        tool_calls = []

        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    inputs = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    inputs = {}
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    inputs=inputs,
                ))

        stop_reason = "tool_use" if tool_calls else "end_turn"
        return ChatResponse(text=text, tool_calls=tool_calls, stop_reason=stop_reason)

    # ── Format converters ─────────────────────────────────────────────────────

    def _convert_messages(self, system: str, messages: list[dict]) -> list[dict]:
        """Convert neutral message format to OpenAI format."""
        result = [{"role": "system", "content": system}]

        for msg in messages:
            role    = msg["role"]
            content = msg["content"]

            if isinstance(content, str):
                result.append({"role": role, "content": content})
                continue

            if isinstance(content, list):
                # Handle tool_use (assistant) and tool_result (user) blocks
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    t = item.get("type")

                    if t == "tool_use":
                        # Assistant requesting a tool call
                        result.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": item["id"],
                                "type": "function",
                                "function": {
                                    "name": item["name"],
                                    "arguments": json.dumps(item.get("input", {})),
                                },
                            }],
                        })

                    elif t == "tool_result":
                        # Tool result back to the model
                        result.append({
                            "role": "tool",
                            "tool_call_id": item["tool_call_id"],
                            "content": item["content"],
                        })

                    elif t == "text" and item.get("text"):
                        result.append({"role": role, "content": item["text"]})
                continue

            result.append({"role": role, "content": str(content)})

        return result

    def _convert_tools(self, tools: list[ToolParam]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

    def make_assistant_history_entry(self, chat_response: ChatResponse, raw_blocks=None) -> dict:
        """
        For OpenAI, store a structured assistant message that includes
        tool_call references so the next turn resolves correctly.
        """
        if chat_response.tool_calls:
            return {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.inputs,
                    }
                    for tc in chat_response.tool_calls
                ],
            }
        return {"role": "assistant", "content": chat_response.text}

    def make_tool_result_entry(self, results: list) -> dict:
        """Format tool results as a user turn (OpenAI uses role=tool per result)."""
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
