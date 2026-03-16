import os
import socket
from pathlib import Path
from urllib.parse import urlparse

import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

env_path = Path(__file__).resolve().parents[2] / "configs" / "api_keys.env"
load_dotenv(env_path)

MEGA_API_KEY = os.getenv("MEGA_API_KEY")
MEGA_URL = os.getenv("MEGA_API_URL", "https://ai.megallm.io/v1/chat/completions")

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


def _query_megallm(query: str, timeout_seconds: int = 30) -> str:
    if not MEGA_API_KEY:
        raise ValueError("MEGA_API_KEY not found in configs/api_keys.env")

    headers = {
        "Authorization": f"Bearer {MEGA_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": query}],
    }

    try:
        response = requests.post(
            MEGA_URL,
            headers=headers,
            json=payload,
            timeout=timeout_seconds,
            verify=False,
        )
    except requests.exceptions.SSLError as exc:
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
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"MegaLLM request failed for {MEGA_URL}: {exc}") from exc

    if response.status_code != 200:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"MegaLLM HTTP {response.status_code}: {detail}")

    result = response.json()
    text = _extract_megallm_text(result)
    usage = result.get("usage") if isinstance(result, dict) else None
    _set_last_call_info("megallm", "gpt-4o", usage if isinstance(usage, dict) else None)
    return text


def generate_answer(query: str, max_retries: int = 3) -> str:
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            return _query_megallm(query)
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                print(f"Warning: MegaLLM attempt {attempt}/{max_retries} failed: {exc}")

    _set_last_call_info("megallm", "gpt-4o", None)
    raise RuntimeError(f"MegaLLM generation failed after {max_retries} attempts: {last_error}")