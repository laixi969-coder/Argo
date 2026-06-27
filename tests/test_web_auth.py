import json
import pytest
from src import web, users, auth, plans, billing, store, saved


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(users, "USERS", tmp_path / "users")
    monkeypatch.setattr(auth, "_SECRET_FILE", tmp_path / ".secret")
    monkeypatch.setattr(auth.config, "get", lambda k, d=None: "test-secret")
    monkeypatch.setattr(plans, "QUOTA_DIR", tmp_path / "quota")
    monkeypatch.setattr(billing, "INTENTS", tmp_path / "intents.jsonl")
    monkeypatch.setattr(store, "HISTORY", tmp_path / "history")
    monkeypatch.setattr(store, "LATEST", tmp_path / "latest.json")
    monkeypatch.setattr(saved, "SAVED", tmp_path / "saved")


def _form(d):
    import urllib.parse
    return urllib.parse.urlencode(d).encode()


def test_signup_sets_cookie_and_redirects():
    st, extra, _ = web.auth_action("POST", "/signup", _form({"email": "a@b.com", "password": "password1"}))
    assert st == 303
    hdrs = dict(extra)
    assert "argo_session=" in hdrs["Set-Cookie"] and hdrs["Location"] == "/?welcome=1"
    assert users.get_by_email("a@b.com")  # 用户已建


def test_signup_duplicate_shows_error():
    users.create("a@b.com", "password1")
    st, extra, body = web.auth_action("POST", "/signup", _form({"email": "a@b.com", "password": "password2"}))
    assert st == 200 and "已注册" in body  # 回到表单带报错


def test_login_wrong_password():
    users.create("a@b.com", "password1")
    st, _, body = web.auth_action("POST", "/login", _form({"email": "a@b.com", "password": "nope"}))
    assert st == 200 and "邮箱或密码不对" in body


def test_login_success_and_logged_in_sidebar():
    users.create("a@b.com", "password1")
    st, extra, _ = web.auth_action("POST", "/login", _form({"email": "a@b.com", "password": "password1"}))
    cookie = dict(extra)["Set-Cookie"].split(";")[0]
    # 带 cookie 访问首页，侧栏显示邮箱 + 登出
    _, _, body = web.route("GET", "/", b"", {"cookie": cookie})
    assert "a@b.com" in body and "登出" in body


def test_logout_clears_cookie():
    st, extra, _ = web.auth_action("GET", "/logout", b"")
    assert st == 303 and "Max-Age=0" in dict(extra)["Set-Cookie"]


def test_upgrade_records_intent():
    users.create("a@b.com", "password1")
    st, extra, _ = web.auth_action("POST", "/login", _form({"email": "a@b.com", "password": "password1"}))
    cookie = dict(extra)["Set-Cookie"].split(";")[0]
    st2, extra2, _ = web.auth_action("GET", "/upgrade", b"", {"cookie": cookie})
    assert st2 == 303 and dict(extra2)["Location"].startswith("/account")
    assert billing.INTENTS.exists()  # 升级意向已登记


def test_free_feed_ungated():
    # 放 8 条今天的机会，免费版应该全部显示
    opps = [{"idea": f"机会{i}", "verdict": "值得做", "score": 90 - i, "reason": "r",
             "url": f"http://x/{i}", "source": "s", "category": "AI应用"} for i in range(8)]
    from datetime import date
    store.append(opps, day=date.today().isoformat())
    _, _, body = web.route("GET", "/app", b"", {})
    assert "解锁全部" not in body
    assert body.count('href="/items/') == 8  # 免费全显


def test_pricing_page_404():
    st, _, body = web.route("GET", "/pricing", b"", {})
    assert st == 404


def test_landing_for_logged_out():
    _, _, body = web.route("GET", "/", b"", {})
    assert "值得做、能赚钱" in body and "免费开始" in body  # 落地页 hero + CTA
    assert "广度扫描" in body and "变现分析" in body          # 工作流程


def test_app_route_shows_feed():
    from datetime import date
    store.append([{"idea": "x", "verdict": "值得做", "score": 80, "reason": "r",
                   "url": "http://x", "source": "s", "category": "AI应用"}], day=date.today().isoformat())
    _, _, body = web.route("GET", "/app", b"", {})
    assert "今日热点" in body and "精选" in body  # /app 永远是机会流


def test_web_chat_requires_login():
    import json as _j
    st, _, body = web.route("POST", "/api/chat", _j.dumps({"text": "hi"}).encode(), {})
    assert st == 401 and "请先登录" in body


def test_web_chat_allows_multiple(monkeypatch):
    import json as _j
    monkeypatch.setattr(web.agent, "handle_message", lambda t, user_id="api": "答")
    monkeypatch.setattr(web.config, "get", lambda k, d=None: "")  # 无 token
    u = users.create("a@b.com", "password1")
    cookie = auth.make_cookie(u["id"])
    st, _, _ = web.route("POST", "/api/chat", _j.dumps({"text": "q"}).encode(), {"cookie": cookie})
    assert st == 200
    st, _, body = web.route("POST", "/api/chat", _j.dumps({"text": "q"}).encode(), {"cookie": cookie})
    assert st == 200 and "答" in body


def test_detail_shows_login_prompt_for_deepdive():
    from datetime import date
    store.append([{"idea": "x", "verdict": "值得做", "score": 80, "reason": "r",
                   "url": "http://x", "source": "s", "category": "AI应用"}], day=date.today().isoformat())
    iid = store.item_id({"url": "http://x"})
    _, _, body = web.route("GET", f"/items/{iid}", b"", {})
    assert "深挖这条机会" in body and "登录开聊" in body  # 未登录给引导


def test_admin_gated(monkeypatch):
    users.create("boss@argo.com", "password1")
    users.create("rando@x.com", "password1")
    boss = auth.make_cookie(users.get_by_email("boss@argo.com")["id"])
    rando = auth.make_cookie(users.get_by_email("rando@x.com")["id"])
    monkeypatch.setattr(web.config, "get",
                        lambda k, d=None: {"ARGO_ADMIN_EMAIL": "boss@argo.com", "ARGO_SECRET": "test-secret"}.get(k, ""))
    _, _, body = web.route("GET", "/admin", b"", {"cookie": boss})
    assert "运营台" in body and "总用户" in body and "近 7 天注册趋势" in body and "boss@argo.com" in body
    _, _, body2 = web.route("GET", "/admin", b"", {"cookie": rando})
    assert "仅运营可见" in body2  # 非运营被挡
    _, _, body3 = web.route("GET", "/admin", b"", {})
    assert "仅运营可见" in body3  # 未登录被挡


def test_api_is_fully_accessible(monkeypatch):
    import json as _j
    from datetime import date
    monkeypatch.setattr(web.config, "get", lambda k, d=None: "")  # 无 token
    opps = [{"idea": f"机会{i}", "verdict": "值得做", "score": 90 - i, "reason": "r",
             "url": f"http://x/{i}", "source": "s", "category": "AI应用"} for i in range(8)]
    store.append(opps, day=date.today().isoformat())
    # 匿名/免费：API 应该返回全部 (不被付费墙拦截)
    _, _, body = web.route("GET", "/api/opportunities", b"", {})
    assert len(_j.loads(body)) == 8
    # IM 可信 token：全量
    monkeypatch.setattr(web.config, "get", lambda k, d=None: "tok" if k == "ARGO_API_TOKEN" else "")
    _, _, body2 = web.route("GET", "/api/opportunities", b"", {"x-argo-token": "tok"})
    assert len(_j.loads(body2)) == 8


def test_deepdive_injects_opp_context(monkeypatch):
    import json as _j
    from datetime import date
    captured = {}
    monkeypatch.setattr(web.agent, "handle_message",
                        lambda t, user_id="api": captured.setdefault("t", t) or "答")
    monkeypatch.setattr(web.config, "get", lambda k, d=None: "")
    u = users.create("a@b.com", "password1")
    cookie = auth.make_cookie(u["id"])
    store.append([{"idea": "发票工具", "verdict": "值得做", "score": 80, "reason": "r",
                   "url": "http://x", "source": "s", "category": "AI应用",
                   "pain": "手动拆发票痛", "money": "订阅收费"}], day=date.today().isoformat())
    iid = store.item_id({"url": "http://x"})
    web.route("POST", "/api/chat", _j.dumps({"text": "谁先买单", "item_id": iid}).encode(),
              {"cookie": cookie})
    # agent 收到的文本应含该机会的分析上下文
    assert "手动拆发票痛" in captured["t"] and "订阅收费" in captured["t"] and "谁先买单" in captured["t"]


def test_save_toggle_and_page(monkeypatch):
    import json as _j
    from datetime import date
    store.append([{"idea": "发票工具", "verdict": "值得做", "score": 80, "reason": "r",
                   "url": "http://x", "source": "s", "category": "AI应用"}], day=date.today().isoformat())
    iid = store.item_id({"url": "http://x"})
    u = users.create("a@b.com", "password1")
    cookie = auth.make_cookie(u["id"])
    # 未登录收藏被拒
    st, _, _ = web.route("POST", "/save", _j.dumps({"item_id": iid}).encode(), {})
    assert st == 401
    # 登录收藏 → saved True
    st, _, body = web.route("POST", "/save", _j.dumps({"item_id": iid}).encode(), {"cookie": cookie})
    assert st == 200 and _j.loads(body)["saved"] is True
    # 收藏页能看到
    _, _, page = web.route("GET", "/saved", b"", {"cookie": cookie})
    assert "发票工具" in page
    # 再点取消
    _, _, body2 = web.route("POST", "/save", _j.dumps({"item_id": iid}).encode(), {"cookie": cookie})
    assert _j.loads(body2)["saved"] is False


def test_login_bruteforce_lockout(monkeypatch, tmp_path):
    monkeypatch.setattr(auth, "THROTTLE", tmp_path / "throttle")
    users.create("a@b.com", "password1")
    # 连续 5 次错误后锁定
    for _ in range(5):
        st, _, body = web.auth_action("POST", "/login", _form({"email": "a@b.com", "password": "wrong"}))
        assert "密码不对" in body
    st, _, body = web.auth_action("POST", "/login", _form({"email": "a@b.com", "password": "password1"}))
    assert "尝试次数过多" in body  # 即使密码对也被锁


def test_admin_can_set_plan(monkeypatch):
    import json as _j
    monkeypatch.setattr(web.config, "get",
                        lambda k, d=None: {"ARGO_ADMIN_EMAIL": "boss@argo.com", "ARGO_SECRET": "test-secret"}.get(k, ""))
    boss = users.create("boss@argo.com", "password1")
    cust = users.create("cust@x.com", "password1")
    bc = auth.make_cookie(boss["id"])
    # 非运营不能改
    st, _, _ = web.route("POST", "/admin/setplan",
                         _j.dumps({"uid": cust["id"], "plan": "pro"}).encode(), {})
    assert st == 403
    # 运营手动开通专业版
    st, _, body = web.route("POST", "/admin/setplan",
                            _j.dumps({"uid": cust["id"], "plan": "pro"}).encode(), {"cookie": bc})
    assert st == 200 and _j.loads(body)["ok"] is True
    assert users.get(cust["id"])["plan"] == "pro"
    # 非法 plan 拒绝
    st, _, _ = web.route("POST", "/admin/setplan",
                         _j.dumps({"uid": cust["id"], "plan": "hacker"}).encode(), {"cookie": bc})
    assert st == 400


def test_seo_meta_present():
    _, _, body = web.route("GET", "/pricing", b"", {})
    assert 'name=description' in body and 'og:title' in body


def test_signup_redirects_to_welcome():
    st, extra, _ = web.auth_action("POST", "/signup", _form({"email": "a@b.com", "password": "password1"}))
    assert dict(extra)["Location"] == "/?welcome=1"


def test_welcome_banner_for_new_user():
    from datetime import date
    store.append([{"idea": "x", "verdict": "值得做", "score": 80, "reason": "r",
                   "url": "http://x", "source": "s", "category": "AI应用"}], day=date.today().isoformat())
    u = users.create("a@b.com", "password1")
    cookie = auth.make_cookie(u["id"])
    _, _, body = web.route("GET", "/?welcome=1", b"", {"cookie": cookie})
    assert "欢迎来到金羊毛" in body
    _, _, body2 = web.route("GET", "/", b"", {"cookie": cookie})
    assert "欢迎来到金羊毛" not in body2  # 非 welcome 不显示


def test_paywall_removed():
    from datetime import date
    opps = [{"idea": f"机会{i}", "verdict": "值得做", "score": 90 - i, "reason": "r",
             "url": f"http://x/{i}", "source": "s", "category": "AI应用",
             "pain": "痛", "money": "钱"} for i in range(5)]
    store.append(opps, day=date.today().isoformat())
    top_id = store.item_id({"url": "http://x/0"})
    second_id = store.item_id({"url": "http://x/1"})
    # /all 应该能看到全部 5 条机会
    _, _, allbody = web.route("GET", "/all", b"", {})
    assert allbody.count('href="/items/') == 5
    # 直接访问详情页 → 正常全套，无升级门槛
    _, _, d2 = web.route("GET", f"/items/{second_id}", b"", {})
    assert "升级专业版解锁" not in d2 and "机会判定" in d2
    _, _, d1 = web.route("GET", f"/items/{top_id}", b"", {})
    assert "机会判定" in d1


def test_robots_and_sitemap():
    st, ct, body = web.route("GET", "/robots.txt", b"", {})
    assert st == 200 and "text/plain" in ct and "Disallow: /admin" in body
    st2, ct2, body2 = web.route("GET", "/sitemap.xml", b"", {})
    assert st2 == 200 and "xml" in ct2 and "/pricing" not in body2


def test_account_self_delete():
    u = users.create("a@b.com", "password1")
    saved.toggle(u["id"], "someid")  # 制造个人数据
    cookie = auth.make_cookie(u["id"])
    st, extra, _ = web.auth_action("POST", "/account/delete", b"", {"cookie": cookie})
    assert st == 303 and "Max-Age=0" in dict(extra)["Set-Cookie"]  # 删除并登出
    assert users.get(u["id"]) is None              # 用户已删
    assert saved.list_ids(u["id"]) == []           # 个人数据已清


def test_password_reset_flow(monkeypatch):
    # 不配 SMTP 也不报错；token 可重置密码
    u = users.create("a@b.com", "password1")
    # forgot：邮箱不存在/存在都返回同样提示（不枚举）
    st, _, body = web.auth_action("POST", "/forgot", _form({"email": "a@b.com"}))
    assert st == 200 and "重置链接已发送" in body
    st2, _, body2 = web.auth_action("POST", "/forgot", _form({"email": "nobody@x.com"}))
    assert "重置链接已发送" in body2  # 同样提示
    # 用有效 token 重置密码
    token = auth.make_reset_token(u["id"])
    st3, extra, _ = web.auth_action("POST", "/reset", _form({"token": token, "password": "newpassword9"}))
    assert st3 == 303 and dict(extra)["Location"] == "/login"
    assert users.verify("a@b.com", "newpassword9")  # 新密码生效
    assert users.verify("a@b.com", "password1") is None  # 旧密码失效
    # 失效 token 被拒
    st4, _, body4 = web.auth_action("POST", "/reset", _form({"token": "bad.0.sig", "password": "x" * 9}))
    assert "链接失效" in body4
