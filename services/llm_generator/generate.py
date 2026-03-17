import os
import socket
from pathlib import Path
from urllib.parse import urlparse

import urllib3
from dotenv import load_dotenv
from requests.exceptions import RequestException, SSLError

from services.llm_generator.client import MegaLLMClient
from services.llm_generator.fallback import is_model_unavailable_error, pick_models

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

env_path = Path(__file__).resolve().parents[2] / "configs" / "api_keys.env"
load_dotenv(env_path)

MEGA_API_KEY = os.getenv("MEGA_API_KEY")
MEGA_FALLBACK_API_KEY = os.getenv("MEGA_FALLBACK_API_KEY")
MEGA_URL = os.getenv("MEGA_API_URL", "https://ai.megallm.io/v1/chat/completions")
MEGA_MODELS = [
    model.strip()
    for model in os.getenv(
        "MEGA_MODELS",
        "gpt-5,claude-sonnet-4-5-20250929,openai-gpt-oss-20b",
    ).split(",")
    if model.strip()
]

_LAST_CALL_INFO = {
    "provider": "none",
    "model": "",
    "usage": None,
}


def get_last_call_info() -> dict:
    return dict(_LAST_CALL_INFO)


def _set_last_call_info(provider: str, model: str, usage: dict | None) -> None:
    _LAST_CALL_INFO["provider"] = provider
    _LAST_CALL_INFO["model"] = model
    _LAST_CALL_INFO["usage"] = usage


def _extract_megallm_text(result: dict) -> str:
    choices = result.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError(f"Invalid MegaLLM response: missing/empty choices. Response: {result}")

    message = choices[0].get("message", {})
    content = message.get("content")
    if not content:
        raise ValueError(f"Invalid MegaLLM response: missing message.content. Response: {result}")

    return content


def _sanitize_key(raw_key: str | None) -> str:
    if not raw_key:
        return ""
    value = raw_key.strip()
    if " #" in value:
        value = value.split(" #", 1)[0].strip()
    return value


def _available_api_keys() -> list[str]:
    keys = []
    primary = _sanitize_key(MEGA_API_KEY)
    fallback = _sanitize_key(MEGA_FALLBACK_API_KEY)

    if primary:
        keys.append(primary)
    if fallback and fallback != primary:
        keys.append(fallback)

    return keys


def _query_megallm(query: str, model: str, api_key: str, timeout_seconds: int = 30) -> str:
    client = MegaLLMClient(api_key=api_key, base_url=MEGA_URL)

    try:
        result = client.chat_completion(model=model, query=query, timeout_seconds=timeout_seconds)
    except SSLError as exc:
        host = urlparse(MEGA_URL).hostname or "unknown-host"
        resolved_ip = "unknown"
        try:
            resolved_ip = socket.gethostbyname(host)
        except Exception:
            pass
        raise RuntimeError(
            "MegaLLM TLS handshake failed before HTTP request. "
            f"URL={MEGA_URL}, host={host}, resolved_ip={resolved_ip}. "
            "Set MEGA_API_URL in configs/api_keys.env to the exact endpoint from your MegaLLM dashboard/docs. "
            "Current endpoint may be incorrect or blocked by upstream TLS config. "
            f"Original error: {exc}"
        ) from exc
    except RequestException as exc:
        raise RuntimeError(f"MegaLLM request failed for {MEGA_URL}: {exc}") from exc

    text = _extract_megallm_text(result)
    usage = result.get("usage") if isinstance(result, dict) else None
    _set_last_call_info("megallm", model, usage if isinstance(usage, dict) else None)
    return text


def generate_answer(query: str, max_retries: int = 3) -> str:
    api_keys = _available_api_keys()
    if not api_keys:
        raise RuntimeError("No MegaLLM API keys found. Set MEGA_API_KEY (and optional MEGA_FALLBACK_API_KEY) in configs/api_keys.env")

    models = pick_models(MEGA_MODELS)
    if not models:
        raise RuntimeError("MEGA_MODELS is empty. Set MEGA_MODELS in configs/api_keys.env")

    last_error = None
    tried_models = []
    tried_key_labels = []

    def key_label(index: int) -> str:
        return "primary" if index == 0 else f"fallback{index}"

    for key_index, api_key in enumerate(api_keys):
        label = key_label(key_index)
        tried_key_labels.append(label)

        for model in models:
            tried_models.append(model)
            for attempt in range(1, max_retries + 1):
                try:
                    return _query_megallm(query, model=model, api_key=api_key)
                except Exception as exc:
                    last_error = exc
                    if is_model_unavailable_error(exc):
                        print(f"Warning: MegaLLM model '{model}' unavailable for {label} key. Trying next Mega model.")
                        break
                    if attempt < max_retries:
                        print(f"Warning: MegaLLM ({model}, {label} key) attempt {attempt}/{max_retries} failed: {exc}")

        if key_index < len(api_keys) - 1:
            print(f"Warning: Switching MegaLLM from {label} key to {key_label(key_index + 1)} key.")

    _set_last_call_info("megallm", tried_models[-1], None)
    raise RuntimeError(
        f"MegaLLM generation failed. Tried keys={tried_key_labels}, models={tried_models}, retries/model={max_retries}. Last error: {last_error}"
    )