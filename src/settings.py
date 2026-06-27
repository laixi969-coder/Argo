"""Argo 本机所有者（超级管理员）配置检查与修改入口。"""

import argparse
import base64
import getpass
import hashlib
import hmac
import os
import secrets
from pathlib import Path


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
PASSWORD_ITERATIONS = 600_000

SETTINGS = {
    "REDDIT_CLIENT_ID": ("Reddit Client ID", True),
    "REDDIT_CLIENT_SECRET": ("Reddit Client Secret", True),
    "PRODUCTHUNT_TOKEN": ("Product Hunt Token", True),
    "TIKHUB_BASE_URL": ("TikHub API 地址", False),
    "TIKHUB_API_KEY": ("TikHub API Key", True),
    "REDFOX_BASE_URL": ("红狐数据 API 地址", False),
    "REDFOX_API_KEY": ("红狐数据 API Key", True),
    "REDFOX_TEST_PATH": ("红狐数据测试端点", False),
    "REDFOX_AUTH_HEADER": ("红狐数据鉴权 Header", False),
    "REDFOX_AUTH_PREFIX": ("红狐数据鉴权前缀", False),
    "LLM_BASE_URL": ("LLM API 地址", False),
    "LLM_API_KEY": ("LLM API Key", True),
    "LLM_MODEL": ("LLM 模型", False),
    "SMTP_HOST": ("SMTP 地址", False),
    "SMTP_PORT": ("SMTP 端口", False),
    "SMTP_USER": ("发件邮箱", False),
    "SMTP_PASS": ("邮箱应用密码", True),
    "REPORT_TO": ("日报收件人", False),
}


def hash_password(password, salt=None, iterations=PASSWORD_ITERATIONS):
    if not password:
        raise ValueError("password cannot be empty")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return "$".join(
        (
            "pbkdf2_sha256",
            str(iterations),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        )
    )


def verify_password(password, encoded):
    try:
        algorithm, rounds, salt_text, expected_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(rounds)
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(expected_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _read_values(path=ENV_PATH):
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _is_configured(value):
    return bool(value and value not in {"CHANGE_ME", "REPLACE_ME"})


def authenticate(path=ENV_PATH):
    values = _read_values(path)
    admin_email = values.get("ADMIN_EMAIL", "")
    password_hash = values.get("ADMIN_PASSWORD_HASH", "")
    if not admin_email or not password_hash:
        raise SystemExit("超级管理员账号尚未完成初始化")
    email = input("超级管理员邮箱: ").strip()
    password = getpass.getpass("超级管理员密码: ")
    if not hmac.compare_digest(email, admin_email) or not verify_password(
        password, password_hash
    ):
        raise SystemExit("认证失败")
    print("认证成功。")


def show_status(path=ENV_PATH):
    values = _read_values(path)
    print("Argo 超级管理员配置状态（密钥不会显示）")
    for key, (label, _) in SETTINGS.items():
        state = "已配置" if _is_configured(values.get(key)) else "未配置"
        print(f"- {label}: {state}")


def _replace_value(key, value, path=ENV_PATH):
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    replacement = f"{key}={value}"
    for index, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[index] = replacement
            break
    else:
        lines.append(replacement)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def set_value(key, path=ENV_PATH):
    if key not in SETTINGS:
        raise SystemExit(f"不支持的配置项：{key}")
    label, secret = SETTINGS[key]
    prompt = f"请输入 {label}: "
    value = getpass.getpass(prompt) if secret else input(prompt)
    if not value.strip():
        raise SystemExit("配置值不能为空")
    if "\n" in value or "\r" in value:
        raise SystemExit("配置值不能包含换行")
    _replace_value(key, value.strip(), path)
    print(f"{label} 已保存；值未回显。")


def main():
    parser = argparse.ArgumentParser(description="Argo 超级管理员设置")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="检查配置状态，不显示密钥")
    setter = subparsers.add_parser("set", help="安全设置一个配置项")
    setter.add_argument("key", choices=SETTINGS)
    args = parser.parse_args()

    if args.command == "status":
        authenticate()
        show_status()
    else:
        authenticate()
        set_value(args.key)


if __name__ == "__main__":
    main()
