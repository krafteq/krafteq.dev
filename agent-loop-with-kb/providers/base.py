"""
Provider abstraction layer.

Every provider adapter must implement BaseProvider.chat().
The rest of the agent code only ever talks to this interface —
it never imports an SDK directly.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# ─── Shared data types ────────────────────────────────────────────────────────

@dataclass
class ToolCall:
    """A single tool invocation requested by the model."""
    id: str
    name: str
    inputs: dict


@dataclass
class ChatResponse:
    """Normalised response from any provider."""
    text: str                          # assistant's text (may be empty)
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"      # "end_turn" | "tool_use" | "stop"


@dataclass
class ToolResult:
    """Result of a tool call, to be fed back in the next turn."""
    tool_call_id: str
    content: str


# ─── Tool schema — provider-agnostic internal format ─────────────────────────

@dataclass
class ToolParam:
    """
    Internal tool definition.
    Each provider adapter converts this to its own wire format.
    """
    name: str
    description: str
    parameters: dict   # JSON Schema object describing the inputs


# ─── Abstract base ────────────────────────────────────────────────────────────

class BaseProvider(ABC):
    """
    All provider adapters inherit from this.

    Implementors only need to fill in:
      - __init__(model, api_key, base_url, max_tokens)
      - chat(system, messages, tools) → ChatResponse

    `messages` is a list of dicts in a neutral format:
      {"role": "user" | "assistant", "content": str | list}

    Tool results are passed as a special content item in the user turn:
      {"role": "user", "content": [{"type": "tool_result", ...}]}

    Each adapter is responsible for translating to/from its provider's wire format.
    """

    @abstractmethod
    def chat(
        self,
        system: str,
        messages: list[dict],
        tools: list[ToolParam] | None = None,
    ) -> ChatResponse:
        """Send a chat request and return a normalised ChatResponse."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name for display."""
        ...
