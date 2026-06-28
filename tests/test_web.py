import json
import pytest
from src import web, store, plans


@pytest.fixture(autouse=True)
def seed(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "HISTORY", tmp_path / "history")
    monkeypatch.setattr(store, "LATEST", tmp_path / "latest.json")
    # 这些是筛选/详情/搜索逻辑测试，放开付费墙，聚焦逻辑本身
    monkeypatch.setattr(plans, "feed_limit", lambda u: 999)
    monkeypatch.setattr(plans, "history_days", lambda u: 999)
    opps = [
        {"idea": "发票工具", "verdict": "值得做", "score": 84, "reason": "刚需",
         "url": "http://x", "source": "reddit", "category": "AI应用",
         "title": "auto invoice", "raw_text": "freelancers hate splitting invoices manually",
         "hook": "自由职业者天天手动拆发票", "pain": "反复手动折腾耗时易错",
         "buyer": "自由职业者愿月付 50", "angle": "单点切入先跑通付费", "risk": "可能只是看着方便"},
        {"idea": "遛狗排班", "verdict": "待验证", "score": 62, "reason": "看看",
         "url": "http://y", "source": "producthunt", "category": "服务",
         "title": "dog walk", "raw_text": "neighborhood dog walking schedule"},
    ]
    from datetime import date, timedelta
    today = date.today().isoformat()
    yest = (date.today() - timedelta(days=1)).isoformat()
    store.append(opps, day=yest)
    store.append(opps, day=today)
    return opps


def test_featured_page():
    status, ctype, body = web.route("GET", "/app", b"", {})
    assert status == 200 and "text/html" in ctype
    assert "发票工具" in body and "机会分" in body and "金羊毛" in body
    assert "搜索" in body and "精选" in body  # 内容头：搜索框 + 标题
    assert "logo-on-light.png" in body  # 真 logo 已嵌入


def test_all_page_has_pager_and_dategroup():
    from datetime import date
    status, _, body = web.route("GET", "/all", b"", {})
    assert status == 200
    assert date.today().isoformat() in body and "/ " in body  # 日期组 + 分页 "x / y"
    assert "上一页" in body and "下一页" in body


def test_category_filter():
    _, _, body = web.route("GET", "/all?cat=服务", b"", {})
    # 主列表只剩「服务」类的机会卡（查详情链接），AI应用的发票工具卡不出现
    fapiao_id = store.item_id({"url": "http://x"})
    dog_id = store.item_id({"url": "http://y"})
    assert f"/items/{dog_id}" in body          # 遛狗排班(服务)在
    assert f"/items/{fapiao_id}" not in body   # 发票工具(AI应用)被筛掉
    assert 'class="on"' in body                # 分类高亮生效


def test_pagination_second_page():
    # 每页 8 条，2 天×2 条=4 条 → 只有 1 页；越界回落到末页仍 200
    status, _, body = web.route("GET", "/all?page=9", b"", {})
    assert status == 200


def test_item_detail_and_404():
    item_id = store.item_id({"url": "http://x"})
    status, _, body = web.route("GET", f"/items/{item_id}", b"", {})
    assert status == 200 and "机会判定" in body and "阅读原帖" in body
    # 结构化分析呈现（决策者视角）
    assert "痛点" in body and "谁愿意付费" in body and "商业切入点" in body and "风险" in body
    assert "单点切入先跑通付费" in body
    s404, _, _ = web.route("GET", "/items/deadbeef", b"", {})
    assert s404 == 404


def test_search_filters():
    _, _, body = web.route("GET", "/all?q=遛狗", b"", {})
    dog_id = store.item_id({"url": "http://y"})
    fapiao_id = store.item_id({"url": "http://x"})
    assert f"/items/{dog_id}" in body and f"/items/{fapiao_id}" not in body
    assert "搜索「遛狗」" in body


def test_agent_page():
    status, _, body = web.route("GET", "/agent", b"", {})
    assert status == 200 and "/api/chat" in body


def test_api_opportunities_json():
    status, ctype, body = web.route("GET", "/api/opportunities", b"", {})
    assert status == 200 and "json" in ctype
    assert json.loads(body)[0]["idea"] == "发票工具"


def test_api_chat_token_path(monkeypatch):
    # IM 可信通道：带正确 token → 200，不带 → 401
    monkeypatch.setattr(web.agent, "handle_message", lambda t, user_id="api": f"答:{t}")
    monkeypatch.setattr(web.config, "get", lambda k, d=None: "tok" if k == "ARGO_API_TOKEN" else "")
    st, _, body = web.route("POST", "/api/chat", json.dumps({"text": "hi"}).encode(),
                            {"x-argo-token": "tok"})
    assert st == 200 and json.loads(body)["reply"] == "答:hi"
    s401, _, _ = web.route("POST", "/api/chat", json.dumps({"text": "hi"}).encode(), {})
    assert s401 == 401  # 无 token 无登录 → 拒绝


def test_card_shows_hook_and_weekday():
    _, _, body = web.route("GET", "/app", b"", {})
    assert "自由职业者天天手动拆发票" in body  # 卡片摘要用钩子/痛点
    assert "周" in body                          # 日期带星期


def test_daily_page():
    status, _, body = web.route("GET", "/daily", b"", {})
    assert status == 200 and "AI 日报" in body and "发票工具" in body


def test_feedback_page():
    status, _, body = web.route("GET", "/feedback", b"", {})
    assert status == 200 and "反馈" in body


def test_dark_mode_toggle_present():
    _, _, body = web.route("GET", "/app", b"", {})
    assert "argoTheme" in body and "data-theme" in body


def test_attr_escaping_blocks_injection(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "HISTORY", tmp_path / "h2")
    monkeypatch.setattr(store, "LATEST", tmp_path / "l2.json")
    from datetime import date as _d
    evil = 'http://x" onmouseover="alert(1)'
    store.append([{"idea": "i", "verdict": "值得做", "score": 80, "reason": "r",
                   "url": evil, "source": "s", "category": "AI应用", "pain": "p"}],
                 day=_d.today().isoformat())
    iid = store.item_id({"url": evil})
    _, _, body = web.route("GET", f"/items/{iid}", b"", {})
    assert 'href="http://x" onmouseover=' not in body  # href 属性未被逃逸
    assert "&quot;" in body                              # 引号已转义
    # 搜索框 value 注入
    _, _, b2 = web.route("GET", "/all?q=%22%3E%3Cscript%3E", b"", {})
    assert '"><script>' not in b2


def test_unknown_route_404():
    status, _, _ = web.route("GET", "/nope", b"", {})
    assert status == 404
