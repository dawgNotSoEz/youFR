from __future__ import annotations

from abc import ABC, abstractmethod
import time
from typing import Any

from ai_hall.pipeline.types import LLMGeneration, LLMUsage, QueryRequest


class LLMClient(ABC):
    @abstractmethod
    def generate(self, request: QueryRequest) -> LLMGeneration: ...

    @abstractmethod
    def judge(self, prompt: str, *, model: str | None = None) -> str: ...


class PassthroughClient(LLMClient):
    """
    Adapter that reuses the existing prototype generation stack.
    """

    def generate(self, request: QueryRequest) -> LLMGeneration:
        from services.llm_generator.generate import generate_answer, get_last_call_info

        started = time.perf_counter()
        if request.answer_override:
            return LLMGeneration(
                answer_text=request.answer_override,
                provider="override",
                model=None,
                latency_ms=int((time.perf_counter() - started) * 1000),
                usage=LLMUsage(prompt_tokens=0, completion_tokens=len(request.answer_override.split()), total_tokens=len(request.answer_override.split())),
                raw={"provider": "override"},
            )

        try:
            answer = generate_answer(request.query)
            info = get_last_call_info() or {}
        except Exception as e:
            answer, info = self._local_fallback(request.query, str(e))

        usage = info.get("usage") if isinstance(info, dict) else None
        provider = info.get("provider") if isinstance(info, dict) else None
        model = info.get("model") if isinstance(info, dict) else None
        parsed_usage = LLMUsage(**usage) if isinstance(usage, dict) else LLMUsage(total_tokens=len(answer.split()))

        return LLMGeneration(
            answer_text=answer,
            provider=provider,
            model=model,
            latency_ms=int((time.perf_counter() - started) * 1000),
            usage=parsed_usage,
            raw=info,
        )

    def _local_fallback(self, query: str, error: str) -> tuple[str, dict[str, Any]]:
        try:
            import requests

            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "phi3", "prompt": query, "stream": False},
                timeout=20,
            )
            resp.raise_for_status()
            payload = resp.json()
            text = str(payload.get("response", "")).strip()
            if text:
                return text, {"provider": "ollama", "model": "phi3", "usage": {"total_tokens": len(text.split())}, "fallback_from": error}
        except Exception:
            pass

        answer = (
            "I can't reliably answer this right now because generation is unavailable in this environment. "
            "I'll instead focus on verifying and explaining any provided content."
        )
        return answer, {"provider": "unavailable", "model": "safe-template", "usage": {"total_tokens": len(answer.split())}, "error": error}

    def judge(self, prompt: str, *, model: str | None = None) -> str:
        from services.llm_generator.client import call_llm

        try:
            return (call_llm(prompt) or "").strip()
        except Exception:
            return ""

