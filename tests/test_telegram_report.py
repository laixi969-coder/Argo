from src.telegram_report import render


def test_render_lists_opportunities():
    opps = [{"idea": "发票工具", "verdict": "真需求", "score": 80,
             "reason": "刚需", "url": "http://x", "source": "reddit",
             "industry": "金融", "commercial_potential": "高", "tags": ["发票自动化"]}]
    txt = render(opps, missing_sources=[])
    assert "发票工具" in txt and "真需求" in txt and "80" in txt and "http://x" in txt
    assert "高商业潜力" in txt and "金融" in txt and "发票自动化" in txt


def test_render_hides_scores_below_30():
    txt = render([
        {"idea": "低分", "verdict": "待验证", "score": 29, "reason": "弱",
         "url": "https://x.example", "source": "reddit"},
        {"idea": "达标", "verdict": "待验证", "score": 30, "reason": "可看",
         "url": "https://y.example", "source": "reddit"},
    ], [])

    assert "达标" in txt and "低分" not in txt and "Top 1" in txt


def test_render_shows_missing_source():
    txt = render([], missing_sources=["producthunt"])
    assert "producthunt" in txt and "无机会入榜" in txt


def test_render_has_followup_hint():
    opps = [{"idea": "x", "verdict": "真需求", "score": 70,
             "reason": "r", "url": "http://x", "source": "reddit"}]
    assert "第 N 条" in render(opps, [])


def test_render_separates_ai_supply_side_track():
    opps = [
        {"idea": "实体产品", "verdict": "真需求", "score": 70, "reason": "有预算",
         "url": "http://x", "source": "reddit", "radar_track": "真实需求主榜",
         "evidence_quotes": ["I would pay for this service."]},
        {"idea": "模型 Demo", "verdict": "待验证", "score": 50, "reason": "仅技术信号",
         "url": "http://y", "source": "huggingface", "radar_track": "AI 供给副榜"},
    ]

    text = render(opps, [])

    assert "真实需求主榜" in text and "AI 供给副榜" in text
    assert "未等于商业机会" in text
    assert "I would pay for this service." in text


def test_render_keeps_pending_track_before_ai_track_and_numbers_in_order():
    opps = [
        {"idea": "缺摘录的服务", "verdict": "待验证", "score": 60, "reason": "r",
         "url": "http://x", "source": "reddit", "radar_track": "待核验证据副榜"},
        {"idea": "AI 模型", "verdict": "待验证", "score": 50, "reason": "r",
         "url": "http://y", "source": "github", "radar_track": "AI 供给副榜"},
    ]

    text = render(opps, [])

    assert text.index("待核验证据副榜") < text.index("AI 供给副榜")
    assert "<b>1. 缺摘录的服务</b>" in text
    assert "<b>2. AI 模型</b>" in text


def test_render_blocks_malicious_source_url():
    text = render([{
        "idea": "x", "verdict": "待验证", "score": 50, "reason": "r",
        "url": 'javascript:alert(1)\" onclick=\"steal()', "source": "reddit",
    }], [])
    assert "javascript:" not in text and "onclick=" not in text
    assert 'href="#"' in text
