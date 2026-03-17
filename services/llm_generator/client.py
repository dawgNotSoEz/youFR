import requests


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
