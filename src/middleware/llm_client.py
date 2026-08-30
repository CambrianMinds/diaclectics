"""LLM Clients for Dialectical Inference Middleware.

Provides interfaces for OpenRouter chat completions (synchronous and streaming)
and deterministic mock clients.
"""

from __future__ import annotations

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional
import requests

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """Abstract client interface for LLM inference generation."""

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Generate response given chat message history."""
        pass

    @abstractmethod
    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Iterator[str]:
        """Stream response tokens given chat message history."""
        pass


class MockLLMClient(BaseLLMClient):
    """Controllable mock LLM client for deterministic testing and sycophancy simulation."""

    def __init__(self, default_response: str = "I understand your point.") -> None:
        self.default_response = default_response
        self.response_queue: List[str] = []
        self.call_history: List[List[Dict[str, str]]] = []

    def enqueue_response(self, response: str) -> None:
        """Queue a specific response for the next call."""
        self.response_queue.append(response)

    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        self.call_history.append(messages)
        if self.response_queue:
            return self.response_queue.pop(0)
        return self.default_response

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Iterator[str]:
        full_text = self.generate(messages, system_prompt, temperature, max_tokens)
        words = full_text.split(" ")
        for i, w in enumerate(words):
            yield w + (" " if i < len(words) - 1 else "")


class OpenRouterLLMClient(BaseLLMClient):
    """Chat completion client connecting to OpenRouter models."""

    DEFAULT_MODEL = "deepseek/deepseek-chat"
    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_retries: int = 4,
        base_backoff_seconds: float = 2.0,
    ) -> None:
        self.api_key = (
            api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY", "")
        )
        self.model = model
        self.max_retries = max_retries
        self.base_backoff = base_backoff_seconds

    def _prepare_payload(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
    ) -> Tuple[Dict[str, str], Dict[str, Any]]:
        formatted_messages = list(messages)
        if system_prompt:
            formatted_messages = [{"role": "system", "content": system_prompt}] + formatted_messages

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/justin-bogner/diaclectics",
            "X-Title": "Diaclectics Epistemic Engine",
        }

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        return headers, payload

    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required for OpenRouterLLMClient.")

        headers, payload = self._prepare_payload(
            messages, system_prompt, temperature, max_tokens, stream=False
        )

        attempt = 0
        while attempt < self.max_retries:
            try:
                response = requests.post(
                    self.API_URL, headers=headers, json=payload, timeout=45
                )

                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "")
                    return ""

                elif response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait_time = (
                        float(retry_after)
                        if retry_after and retry_after.isdigit()
                        else self.base_backoff * (2**attempt)
                    )
                    logger.warning(
                        f"OpenRouter Chat 429 Rate Limit. Waiting {wait_time:.1f}s"
                    )
                    time.sleep(wait_time)
                    attempt += 1

                else:
                    raise RuntimeError(
                        f"OpenRouter Chat API Error {response.status_code}: {response.text}"
                    )

            except requests.RequestException as e:
                attempt += 1
                if attempt >= self.max_retries:
                    raise RuntimeError(
                        f"OpenRouter Chat failed after {self.max_retries} attempts: {e}"
                    )
                time.sleep(self.base_backoff * (2**attempt))

        return ""

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Iterator[str]:
        """Stream real-time tokens from OpenRouter API using Server-Sent Events (SSE)."""
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required for OpenRouterLLMClient.")

        headers, payload = self._prepare_payload(
            messages, system_prompt, temperature, max_tokens, stream=True
        )

        response = requests.post(
            self.API_URL, headers=headers, json=payload, timeout=45, stream=True
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"OpenRouter Stream Error {response.status_code}: {response.text}"
            )

        for line in response.iter_lines():
            if not line:
                continue
            line_str = line.decode("utf-8") if isinstance(line, bytes) else line
            if line_str.startswith("data: "):
                data_content = line_str[6:].strip()
                if data_content == "[DONE]":
                    break
                try:
                    chunk_json = json.loads(data_content)
                    choices = chunk_json.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token
                except Exception:
                    continue
