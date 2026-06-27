import pytest
from src import auth, users


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(users, "USERS", tmp_path / "users")
    monkeypatch.setattr(auth, "_SECRET_FILE", tmp_path / ".secret")
    monkeypatch.setattr(auth.config, "get", lambda k, d=None: "test-secret-key")


def test_roundtrip_cookie():
    u = users.create("a@b.com", "password1")
    cookie = auth.make_cookie(u["id"])
    assert "argo_session=" in cookie and "HttpOnly" in cookie
    # 用生成的 cookie 反解出用户
    token = cookie.split(";")[0]  # argo_session=<uid>.<sig>
    got = auth.current_user(token)
    assert got["id"] == u["id"] and got["plan"] == "free"


def test_tampered_cookie_rejected():
    u = users.create("a@b.com", "password1")
    assert auth.current_user(f"argo_session={u['id']}.deadbeefsig") is None


def test_no_cookie():
    assert auth.current_user("") is None
    assert auth.current_user("other=1") is None


def test_secure_flag():
    assert "Secure" in auth.make_cookie("x", secure=True)
    assert "Secure" not in auth.make_cookie("x", secure=False)
