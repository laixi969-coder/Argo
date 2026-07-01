from src.email_report import render_html

def test_render_lists_opportunities():
    opps = [{"idea": "发票工具", "verdict": "真需求", "score": 80,
             "reason": "刚需", "url": "http://x", "source": "reddit",
             "industry": "金融", "commercial_potential": "高", "tags": ["发票自动化"],
             "demand_evidence": "每月手工处理 2 小时",
             "next_validation": "测试 99 元预付款"}]
    html = render_html(opps, missing_sources=[])
    assert "发票工具" in html and "真需求" in html and "80" in html
    assert "每月手工处理 2 小时" in html
    assert "测试 99 元预付款" in html
    assert "高商业潜力" in html and "金融" in html and "发票自动化" in html

def test_render_shows_missing_source_notice():
    html = render_html([], missing_sources=["producthunt"])
    assert "producthunt" in html


def test_render_escapes_untrusted_content():
    opps = [{"idea": "<script>alert(1)</script>", "verdict": "待验证", "score": 31,
             "reason": "x", "url": "http://x", "source": "reddit"}]
    html = render_html(opps, missing_sources=[])
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
