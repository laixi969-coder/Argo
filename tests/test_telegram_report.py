from src.telegram_report import render


def test_render_lists_opportunities():
    opps = [{"idea": "发票工具", "verdict": "真需求", "score": 80,
             "reason": "刚需", "url": "http://x", "source": "reddit"}]
    txt = render(opps, missing_sources=[])
    assert "发票工具" in txt and "真需求" in txt and "80" in txt and "http://x" in txt


def test_render_shows_missing_source():
    txt = render([], missing_sources=["producthunt"])
    assert "producthunt" in txt and "无机会入榜" in txt


def test_render_has_followup_hint():
    opps = [{"idea": "x", "verdict": "真需求", "score": 70,
             "reason": "r", "url": "http://x", "source": "reddit"}]
    assert "第 N 条" in render(opps, [])


def test_render_blocks_malicious_source_url():
    text = render([{
        "idea": "x", "verdict": "待验证", "score": 50, "reason": "r",
        "url": 'javascript:alert(1)\" onclick=\"steal()', "source": "reddit",
    }], [])
    assert "javascript:" not in text and "onclick=" not in text
    assert 'href="#"' in text
