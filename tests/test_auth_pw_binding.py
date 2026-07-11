"""会话与重置令牌必须绑定密码：改密后旧凭证立即失效。"""
import pytest
from src import auth, users


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(users, "USERS", tmp_path / "users")
    monkeypatch.setattr(auth, "_SECRET_FILE", tmp_path / ".secret")
    monkeypatch.setattr(auth.config, "get", lambda k, d=None: "test-secret")


def _cookie_header(uid):
    return auth.make_cookie(uid).split(";")[0]


def test_old_cookie_dies_after_password_change():
    u = users.create("a@b.com", "password1")
    old = _cookie_header(u["id"])
    assert auth.current_user(old)["id"] == u["id"]
    users.set_password(u["id"], "password2")
    assert auth.current_user(old) is None  # 被盗 cookie 改密后作废
    assert auth.current_user(_cookie_header(u["id"]))["id"] == u["id"]


def test_reset_token_single_use_via_password_change():
    u = users.create("a@b.com", "password1")
    token = auth.make_reset_token(u["id"])
    assert auth.verify_reset_token(token) == u["id"]
    users.set_password(u["id"], "password2")
    assert auth.verify_reset_token(token) is None  # 用过（密码已改）即作废
