import json

from src import kv, users, saved, plans, auth, web


def _fake_kv(monkeypatch):
    data = {}
    sets = {}
    monkeypatch.setattr(kv, "enabled", lambda: True)
    monkeypatch.setattr(kv, "get_json", lambda key: data.get(key))

    def set_json(key, value, **opts):
        if opts.get("nx") and key in data:
            return False
        data[key] = value
        return True

    monkeypatch.setattr(kv, "set_json", set_json)
    monkeypatch.setattr(kv, "delete", lambda key: data.pop(key, None))
    monkeypatch.setattr(kv, "sadd", lambda key, value: sets.setdefault(key, set()).add(value))
    monkeypatch.setattr(kv, "srem", lambda key, value: sets.setdefault(key, set()).discard(value))
    monkeypatch.setattr(kv, "smembers", lambda key: list(sets.get(key, set())))
    return data


def test_account_data_uses_kv_when_configured(monkeypatch):
    data = _fake_kv(monkeypatch)
    user = users.create("cloud@example.com", "password1")
    assert users.verify("cloud@example.com", "password1")["id"] == user["id"]
    assert users.count() == 1
    assert users.all_users()[0]["email"] == "cloud@example.com"

    assert saved.toggle(user["id"], "item-1") is True
    assert saved.list_ids(user["id"]) == ["item-1"]
    assert plans.use_chat(user) is True
    assert data[f"quota:{user['id']}:" + plans.clock.today_iso().replace("-", "")]["chat"] == 1


def test_throttle_uses_kv(monkeypatch):
    _fake_kv(monkeypatch)
    for _ in range(5):
        auth.note_fail("cloud@example.com")
    assert auth.login_blocked("cloud@example.com") is True
    auth.note_ok("cloud@example.com")
    assert auth.login_blocked("cloud@example.com") is False


def test_vercel_without_storage_returns_503(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)
    monkeypatch.delenv("KV_REST_API_URL", raising=False)
    monkeypatch.delenv("KV_REST_API_TOKEN", raising=False)
    monkeypatch.delenv("ARGO_SECRET", raising=False)
    body = b"email=a%40b.com&password=password1"
    status, _, html = web.auth_action("POST", "/login", body)
    assert status == 503
    assert "KV_REST_API_URL" in html and "ARGO_SECRET" in html


def test_upstash_rest_command(monkeypatch):
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://redis.example")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "secret")
    seen = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return b'{"result":"OK"}'

    def urlopen(req, timeout):
        seen["body"] = json.loads(req.data)
        seen["auth"] = req.headers["Authorization"]
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setattr(kv.urllib.request, "urlopen", urlopen)
    assert kv.command("SET", "argo:x", "1") == "OK"
    assert seen == {"body": ["SET", "argo:x", "1"],
                    "auth": "Bearer secret", "timeout": 5}


def test_vercel_marketplace_variable_names(monkeypatch):
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)
    monkeypatch.setenv("KV_REST_API_URL", "https://redis.example")
    monkeypatch.setenv("KV_REST_API_TOKEN", "token")
    assert kv.enabled() is True


def test_lock_release_is_owner_safe(monkeypatch):
    calls = []
    monkeypatch.setattr(kv, "command", lambda *args: calls.append(args) or 1)

    assert kv.release_lock("daily-pipeline", "owner-1") is True
    args = calls[0]
    assert args[0] == "EVAL" and "redis.call('get'" in args[1]
    assert args[-1] == json.dumps("owner-1")
