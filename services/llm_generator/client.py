import requests
import os
from pathlib import Path

from dotenv import load_dotenv


class MegaLLMClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url

    def chat_completion(self, model: str, query: str, timeout_seconds: int = 30) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": query}],
        }
        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=timeout_seconds,
            verify=False,
        )
        if response.status_code != 200:
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            raise RuntimeError(f"MegaLLM HTTP {response.status_code}: {detail}")
        return response.json()


def call_llm(prompt: str, timeout_seconds: int = 45) -> str:
    env_path = Path(__file__).resolve().parents[2] / "configs" / "api_keys.env"
    load_dotenv(env_path)

    api_key = (os.getenv("MEGA_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("MEGA_API_KEY not found in configs/api_keys.env")

    base_url = os.getenv("MEGA_API_URL", "https://ai.megallm.io/v1/chat/completions")
    models_raw = os.getenv("MEGA_MODELS", "gpt-5")
    models = [model.strip() for model in models_raw.split(",") if model.strip()]
    if not models:
        models = ["gpt-5"]

    client = MegaLLMClient(api_key=api_key, base_url=base_url)

    last_error = None
    for model in models:
        try:
            result = client.chat_completion(model=model, query=prompt, timeout_seconds=timeout_seconds)
            choices = result.get("choices") if isinstance(result, dict) else None
            if not isinstance(choices, list) or not choices:
                raise RuntimeError("Missing choices in MegaLLM response")
            message = choices[0].get("message", {})
            content = message.get("content")
            if not content:
                raise RuntimeError("Missing message.content in MegaLLM response")
            return str(content)
        except Exception as exc:
            last_error = exc
            continue

    raise RuntimeError(f"call_llm failed across models {models}. Last error: {last_error}")
