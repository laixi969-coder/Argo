import time

import requests

from src import config


_RETRIES = 2


def _post(messages, temperature, timeout, retries=_RETRIES):
    last_error = None
    settings = config.get_many("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")
    base_url = (settings.get("LLM_BASE_URL") or "").rstrip("/")
    for attempt in range(retries + 1):
        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.get('LLM_API_KEY') or ''}"},
                json={
                    "model": settings.get("LLM_MODEL"),
                    "messages": messages,
                    "temperature": temperature,
                },
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.RequestException as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last_error


def call_llm(prompt, timeout=60):
    return _post([{"role": "user", "content": prompt}], 0.3, timeout)


def chat_llm(messages, timeout=20):
    # 交互请求最多重试一次：兼顾中转偶发抖动，并把最坏时长控制在 Vercel 60 秒内。
    return _post(messages, 0.5, min(timeout, 20), retries=1)
