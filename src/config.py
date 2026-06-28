import json
import os
from pathlib import Path
from src import kv

_ROOT = Path(__file__).resolve().parent.parent
OVERRIDES = _ROOT / "data" / "config.json"


def _load_env():
    env = _ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                os.environ.setdefault(k.strip(), v)

_load_env()

def get(key, default=None):
    overrides = _overrides()
    if overrides.get(key):
        return overrides[key]
    return os.environ.get(key, default)


def _overrides():
    if kv.enabled():
        return kv.get_json("config") or {}
    if not OVERRIDES.exists():
        return {}
    try:
        return json.loads(OVERRIDES.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def set_override(key, value):
    overrides = _overrides()
    overrides[key] = value
    if kv.enabled():
        kv.set_json("config", overrides)
        return
    OVERRIDES.parent.mkdir(parents=True, exist_ok=True)
    OVERRIDES.write_text(json.dumps(overrides, ensure_ascii=False), encoding="utf-8")
