import json
from pathlib import Path


def test_python_function_has_explicit_chat_safe_duration():
    config = json.loads((Path(__file__).resolve().parent.parent / "vercel.json").read_text())
    assert "builds" not in config  # Vercel 不允许 legacy builds 与 functions 同时存在
    assert config["functions"]["api/index.py"]["maxDuration"] == 60
    assert config["functions"]["api/index.py"]["includeFiles"] == "static/**"
    assert config["rewrites"][0]["destination"] == "/api/index.py"
