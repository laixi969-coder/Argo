"""本地管理员页面浏览器自检；密码仅从交互输入读取。"""

import getpass
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.settings import _read_values


def main():
    email = _read_values().get("ADMIN_EMAIL", "")
    password = getpass.getpass("管理员密码（不会回显）: ")
    console_errors = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1050})
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.goto("http://127.0.0.1:8765")
        page.wait_for_load_state("networkidle")
        assert page.get_by_text("舰长登舱").is_visible()
        page.locator("#email").fill(email)
        page.locator("#password").fill(password)
        page.get_by_role("button", name="进入控制室").click()
        page.get_by_text("舰长设置", exact=True).wait_for()
        assert page.get_by_text("直接数据源", exact=True).is_visible()
        assert page.get_by_text("数据供应商", exact=True).is_visible()
        assert page.get_by_text("Reddit 官方", exact=True).count() >= 1
        assert page.get_by_text("Product Hunt 官方", exact=True).count() >= 1
        assert page.locator('[name="LLM_BASE_URL"]').input_value() == "https://api.deepseek.com"
        assert page.locator('[name="LLM_MODEL"]').input_value() == "deepseek-chat"
        assert page.get_by_role("button", name="同步模型").is_visible()
        assert page.get_by_role("button", name="测试连接").count() == 5
        assert page.get_by_role("button", name="验证 Token 与余额").is_visible()
        assert page.locator('[name="TIKHUB_BASE_URL"]').input_value()
        assert page.locator('[name="TIKHUB_API_KEY"]').input_value() == ""
        assert page.locator('[name="TIKHUB_TEST_PATH"]').count() == 0
        assert page.locator('[name="TIKHUB_AUTH_HEADER"]').count() == 0
        assert page.locator('[name="REDFOX_API_KEY"]').input_value() == ""
        assert page.locator('[name="LLM_API_KEY"]').input_value() == ""
        page.screenshot(path="/tmp/argo-admin.png", full_page=True)
        browser.close()

    if console_errors:
        raise AssertionError(f"browser console errors: {console_errors}")
    print("admin_browser_check: passed")


if __name__ == "__main__":
    main()
