import time

import requests

from src import config


_RETRIES = 2


def _post(messages, temperature, timeout):
    last_error = None
    for attempt in range(_RETRIES + 1):
        try:
            response = requests.post(
                f"{config.get('LLM_BASE_URL').rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {config.get('LLM_API_KEY')}"},
                json={
                    "model": config.get("LLM_MODEL"),
                    "messages": messages,
                    "temperature": temperature,
                },
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.RequestException as exc:
            last_error = exc
            if attempt < _RETRIES:
                time.sleep(1.5 * (attempt + 1))
    raise last_error


def call_llm(prompt, timeout=60):
    return _post([{"role": "user", "content": prompt}], 0.3, timeout)


def chat_llm(messages, timeout=60):
    return _post(messages, 0.5, timeout)
