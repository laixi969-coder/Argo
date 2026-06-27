import pytest
from src import users


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(users, "USERS", tmp_path / "users")


def test_create_and_verify():
    u = users.create("Cai@Example.com", "supersecret")
    assert u["email"] == "cai@example.com" and u["plan"] == "free"
    assert "pw" not in u and "salt" not in u  # 敏感字段不外泄
    assert users.verify("cai@example.com", "supersecret")["id"] == u["id"]
    assert users.verify("cai@example.com", "wrongpass") is None


def test_password_not_plaintext(tmp_path):
    users.create("a@b.com", "mypassword1")
    raw = (users.USERS / (users._uid("a@b.com") + ".json")).read_text()
    assert "mypassword1" not in raw  # 密码不落明文


def test_duplicate_email_rejected():
    users.create("a@b.com", "password1")
    with pytest.raises(ValueError, match="已注册"):
        users.create("A@B.com", "password2")


def test_validation():
    with pytest.raises(ValueError, match="邮箱"):
        users.create("notanemail", "password1")
    with pytest.raises(ValueError, match="密码需"):
        users.create("a@b.com", "short")


def test_set_plan():
    u = users.create("a@b.com", "password1")
    users.set_plan(u["id"], "pro")
    assert users.get(u["id"])["plan"] == "pro"


def test_input_length_caps():
    import pytest as _p
    with _p.raises(ValueError):
        users.create("a@b.com", "x" * 129)        # 密码超 128
    with _p.raises(ValueError):
        users.create("a@" + "x" * 260 + ".com", "password1")  # 邮箱超 254
