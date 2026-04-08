"""
LLM Provider abstraction — supports any vision-capable model.
Swap providers by changing LLM_PROVIDER in .env, no code changes needed.

Supported:
    ollama    — local (llava, moondream, etc.)
    gemini    — Google Gemini (gemini-2.0-flash, etc.)
    openai    — OpenAI (gpt-4o, etc.)
    anthropic — Anthropic (claude-sonnet-4-5, etc.)
"""

import base64
import logging
import os
from abc import ABC, abstractmethod

import cv2

log = logging.getLogger(__name__)


def _encode_frame(frame) -> bytes:
    """Encode OpenCV frame to JPEG bytes."""
    _, buf = cv2.imencode(".jpg", frame)
    return buf.tobytes()

def _encode_frame_b64(frame) -> str:
    """Encode OpenCV frame to base64 string."""
    return base64.b64encode(_encode_frame(frame)).decode("utf-8")


# --- Base class ---

class VisionProvider(ABC):
    @abstractmethod
    def ask(self, frame, prompt: str) -> str:
        """Send a frame + prompt to the vision model, return text response."""
        pass


# --- Ollama ---

class OllamaProvider(VisionProvider):
    def __init__(self):
        import ollama
        host        = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model  = os.getenv("LLM_MODEL", "moondream")
        self.client = ollama.Client(host=host)
        log.info(f"LLM provider: Ollama ({self.model}) @ {host}")

    def ask(self, frame, prompt: str) -> str:
        try:
            res = self.client.chat(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": prompt,
                    "images": [_encode_frame(frame)]
                }]
            )
            return res["message"]["content"].strip()
        except Exception as e:
            log.error(f"Ollama error: {e}")
            return ""


# --- Gemini ---

class GeminiProvider(VisionProvider):
    def __init__(self):
        import google.genai as genai
        from PIL import Image
        self._Image = Image
        api_key     = os.getenv("GEMINI_API_KEY")
        self.model  = os.getenv("LLM_MODEL", "gemini-2.0-flash")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY is required for Gemini provider")
        self.client = genai.Client(api_key=api_key)
        log.info(f"LLM provider: Gemini ({self.model})")

    def ask(self, frame, prompt: str) -> str:
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = self._Image.fromarray(frame_rgb)
            response  = self.client.models.generate_content(
                model=self.model,
                contents=[prompt, pil_image]
            )
            return response.text.strip()
        except Exception as e:
            log.error(f"Gemini error: {e}")
            return ""


# --- OpenAI ---

class OpenAIProvider(VisionProvider):
    def __init__(self):
        from openai import OpenAI
        api_key     = os.getenv("OPENAI_API_KEY")
        self.model  = os.getenv("LLM_MODEL", "gpt-4o")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is required for OpenAI provider")
        self.client = OpenAI(api_key=api_key)
        log.info(f"LLM provider: OpenAI ({self.model})")

    def ask(self, frame, prompt: str) -> str:
        try:
            b64 = _encode_frame_b64(frame)
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{b64}"
                        }}
                    ]
                }]
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            log.error(f"OpenAI error: {e}")
            return ""


# --- Anthropic ---

class AnthropicProvider(VisionProvider):
    def __init__(self):
        import anthropic
        api_key     = os.getenv("ANTHROPIC_API_KEY")
        self.model  = os.getenv("LLM_MODEL", "claude-sonnet-4-5")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is required for Anthropic provider")
        self.client = anthropic.Anthropic(api_key=api_key)
        log.info(f"LLM provider: Anthropic ({self.model})")

    def ask(self, frame, prompt: str) -> str:
        try:
            b64 = _encode_frame_b64(frame)
            res = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": b64
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }]
            )
            return res.content[0].text.strip()
        except Exception as e:
            log.error(f"Anthropic error: {e}")
            return ""


# --- Factory ---

_PROVIDERS = {
    "ollama":    OllamaProvider,
    "gemini":    GeminiProvider,
    "openai":    OpenAIProvider,
    "anthropic": AnthropicProvider,
}

def get_provider() -> VisionProvider:
    name = os.getenv("LLM_PROVIDER", "ollama").lower()
    if name not in _PROVIDERS:
        raise ValueError(f"Unknown LLM_PROVIDER '{name}'. Choose from: {list(_PROVIDERS.keys())}")
    return _PROVIDERS[name]()