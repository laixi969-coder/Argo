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


def test_extract_marks_non_demand_as_false():
    resp = '{"is_demand": false, "idea": "未知", "customer": "未知"}'
    opps = [{"title": "Backdoor in xz/liblzma", "raw_text": ""}]
    out = extract_ideas(opps, llm=lambda p: resp)
    assert out[0]["is_demand"] is False


def test_extract_defaults_is_demand_true_when_absent():
    resp = '{"idea": "自动发票拆分工具", "customer": "自由职业者"}'
    opps = [{"title": "x", "raw_text": "y"}]
    out = extract_ideas(opps, llm=lambda p: resp)
    assert out[0]["is_demand"] is True


def test_extract_prompt_keeps_concrete_existing_products_as_opportunity_signals():
    seen = {}

    def fake_llm(prompt):
        seen["prompt"] = prompt
        return '''{
          "is_demand": true,
          "idea": "面向广告团队的 AI 视频工作流",
          "customer": "广告团队",
          "job": "批量制作广告视频",
          "market_proof": "已有付费方案"
        }'''

    out = extract_ideas([{"title": "Video workflow launched", "raw_text": "For ad teams"}], llm=fake_llm)

    assert "产品公告" in seen["prompt"] and "is_demand 记 true" in seen["prompt"]
    assert out[0]["is_demand"] is True
    assert out[0]["market_proof"] == "已有付费方案"


def test_producthunt_product_is_not_dropped_as_a_generic_announcement():
    resp = '''{
      "is_demand": false,
      "idea": "面向设计团队的 AI 素材版本管理工具",
      "customer": "设计团队",
      "job": "管理素材版本"
    }'''
    opps = [{
        "source": "producthunt",
        "opportunity_type": "已有成果产品",
        "title": "AssetFlow",
        "raw_text": "Version control for design assets",
    }]

    out = extract_ideas(opps, llm=lambda p: resp)

    assert out[0]["is_demand"] is True
