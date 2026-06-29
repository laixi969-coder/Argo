from src.extract import extract_ideas


def test_extract_fills_idea():
    opps = [{"title": "Anyone know a tool to auto-split invoices?", "raw_text": ""}]
    out = extract_ideas(opps, llm=lambda p: "面向自由职业者的自动发票拆分工具")
    assert out[0]["idea"] == "面向自由职业者的自动发票拆分工具"


def test_extract_collects_demand_evidence_without_inventing_it():
    response = '''{
      "idea": "面向自由职业者的自动发票拆分工具",
      "customer": "自由职业者",
      "job": "把一张发票按客户拆分",
      "past_behavior": "发帖者每月手工拆分",
      "workaround": "电子表格",
      "cost_paid": "每月约 2 小时",
      "wtp_evidence": "未知",
      "frequency_urgency": "每月发生，中等紧迫",
      "missing_evidence": ["没有实际付款记录", "没有报价接受记录"]
    }'''
    opps = [{"title": "Need invoice splitting", "raw_text": "I do this monthly in sheets."}]
    out = extract_ideas(opps, llm=lambda p: response)

    assert out[0]["customer"] == "自由职业者"
    assert out[0]["past_behavior"] == "发帖者每月手工拆分"
    assert out[0]["wtp_evidence"] == "未知"
    assert out[0]["missing_evidence"] == ["没有实际付款记录", "没有报价接受记录"]


def test_extract_bad_json_falls_back_without_fake_evidence():
    opps = [{"title": "Need invoice splitting", "raw_text": ""}]
    out = extract_ideas(opps, llm=lambda p: "模型没有按 JSON 输出")

    assert out[0]["idea"] == "模型没有按 JSON 输出"
    assert out[0]["past_behavior"] == "未知"
    assert out[0]["wtp_evidence"] == "未知"
    assert out[0]["missing_evidence"] == ["结构化证据提取失败"]


def test_extract_broken_json_with_inner_quotes_does_not_dump_blob():
    # LLM 输出 JSON 但内部引号未转义 → 解析失败；不能把整坨 JSON 当 idea
    bad = '{\n "idea": "低维护室内植物产品",\n "customer": "评论者（"me"）",\n "job": "养护室内植物"\n}'
    opps = [{"title": "house plants that survive neglect", "raw_text": "x"}]
    out = extract_ideas(opps, llm=lambda p: bad)
    assert out[0]["idea"] == "低维护室内植物产品"
    assert "{" not in out[0]["idea"] and '"job"' not in out[0]["idea"]


def test_extract_broken_json_no_salvageable_idea_uses_title():
    bad = '{ "customer": "某人", "note": "完全没有 idea 字段的坏 JSON" '
    opps = [{"title": "原始标题兜底", "raw_text": "x"}]
    out = extract_ideas(opps, llm=lambda p: bad)
    assert out[0]["idea"] == "原始标题兜底"
