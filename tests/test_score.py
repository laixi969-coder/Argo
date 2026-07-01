from src.score import score_real_demand


def test_score_fills_fields():
    opps = [{"idea": "给独立开发者的发票工具", "signal": 50}]
    out = score_real_demand(opps, llm=lambda p: '{"verdict":"真需求","score":75,"reason":"用户一直吐槽离不开"}')
    assert out[0]["verdict"] == "真需求"
    assert out[0]["score"] == 75
    assert out[0]["reason"]
    assert out[0]["commercial_potential"] == "中"
    assert out[0]["category"] == "AI应用"
    assert out[0]["industry"] == "金融"
    assert out[0]["tags"]

def test_score_degrades_on_bad_json():
    opps = [{"idea": "x", "signal": 40}]
    out = score_real_demand(opps, llm=lambda p: "模型今天抽风不是 JSON")
    assert out[0]["verdict"] == "待验证"
    assert out[0]["score"] == 40


def test_score_failure_cannot_become_high_potential_from_source_heat():
    item = score_real_demand(
        [{"idea": "热门但未精判", "signal": 100}], llm=lambda p: "bad json"
    )[0]

    assert item["score"] == 45
    assert item["commercial_potential"] == "低"
    assert item["verdict"] == "待验证"


def test_score_passes_evidence_to_judge_and_keeps_validation_action():
    seen = {}

    def fake_llm(prompt):
        seen["prompt"] = prompt
        return '''{
          "verdict": "待验证",
          "score": 62,
          "reason": "有重复手工行为，但没有付费证据",
          "evidence_strength": "中",
          "next_validation": "向 5 名同类用户收取 99 元预付款"
        }'''

    opps = [{
        "idea": "自动发票拆分工具", "signal": 50,
        "past_behavior": "每月手工处理", "workaround": "电子表格",
        "cost_paid": "每月 2 小时", "wtp_evidence": "未知",
        "frequency_urgency": "每月", "missing_evidence": ["没有付款记录"],
    }]
    out = score_real_demand(opps, llm=fake_llm)

    assert "每月手工处理" in seen["prompt"]
    assert "不得补全" in seen["prompt"]
    assert out[0]["evidence_strength"] == "中"
    assert out[0]["next_validation"] == "向 5 名同类用户收取 99 元预付款"


def test_score_rejects_invalid_model_values():
    opps = [{"idea": "x", "signal": 40}]
    bad_values = lambda p: '{"verdict":"宇宙级需求","score":900,"reason":"相信我"}'
    out = score_real_demand(opps, llm=bad_values)

    assert out[0]["verdict"] == "待验证"
    assert out[0]["score"] == 40


def test_score_downgrades_unsupported_fake_demand_to_pending():
    raw = '{"verdict":"伪需求","score":12,"reason":"没有付费证据","disproof":"无"}'
    out = score_real_demand([{"idea": "AI 视频工作流", "signal": 30}], llm=lambda p: raw)

    assert out[0]["verdict"] == "待验证"
    assert out[0]["score"] == 40
    assert "缺少明确反证" in out[0]["reason"]


def test_score_keeps_fake_demand_when_explicit_disproof_exists():
    raw = '{"verdict":"伪需求","score":18,"reason":"用户明确拒绝付费","disproof":"受访用户明确表示不会付费"}'
    out = score_real_demand([{"idea": "x", "signal": 30}], llm=lambda p: raw)

    assert out[0]["verdict"] == "伪需求"


def test_score_accepts_market_validated_with_payment_proof():
    raw = '{"verdict":"市场已验证","score":82,"reason":"已有持续付费","market_proof":"100 名付费用户"}'
    out = score_real_demand([{"idea": "x", "signal": 30}], llm=lambda p: raw)

    assert out[0]["verdict"] == "市场已验证"
    assert out[0]["market_proof"] == "100 名付费用户"


def test_score_keeps_ai_industry_category_and_hint():
    seen = {}

    def fake_llm(prompt):
        seen["prompt"] = prompt
        return ('{"verdict":"真需求","score":78,"reason":"停机损失明确",'
                '"category":"AI × 工业"}')

    out = score_real_demand([{
        "idea": "工厂预测性维护",
        "signal": 50,
        "discovery_theme": "AI × 工业",
    }], llm=fake_llm)

    assert "AI × 工业" in seen["prompt"]
    assert out[0]["category"] == "AI × 工业"


def test_score_persists_commercial_analysis_industry_and_tags():
    raw = '''{
      "verdict":"市场已验证",
      "score":88,
      "category":"Agent",
      "industry":"制造业",
      "commercial_potential":"高",
      "tags":["预测性维护","设备诊断","B2B SaaS"],
      "hook":"停机一小时就产生真实损失",
      "pain":"设备故障导致非计划停机",
      "buyer":"工厂设备负责人",
      "money":"按设备订阅",
      "angle":"先接入高价值产线",
      "risk":"缺少设备历史数据",
      "commercial_evidence":"已有 20 家工厂付费",
      "market_proof":"20 家工厂付费",
      "reason":"真实停机损失且已有付费"
    }'''
    out = score_real_demand([{
        "idea": "工业设备诊断 Agent", "signal": 70,
        "industry_hint": "制造业", "source_tags": ["agent", "maintenance"],
    }], llm=lambda p: raw)
    item = out[0]

    assert item["commercial_potential"] == "高"
    assert item["industry"] == "制造业"
    assert item["tags"] == ["预测性维护", "设备诊断", "B2B SaaS"]
    assert item["buyer"] == "工厂设备负责人"
    assert item["money"] == "按设备订阅"
    assert item["commercial_evidence"] == "已有 20 家工厂付费"


def test_score_sanitizes_unknown_taxonomy_values():
    raw = ('{"verdict":"真需求","score":65,"reason":"有重复行为",'
           '"category":"宇宙产品","industry":"火星农业",'
           '"commercial_potential":"暴高","tags":"不是数组"}')
    item = score_real_demand([{"idea": "x", "signal": 30}], llm=lambda p: raw)[0]

    assert item["category"] == "AI应用"
    assert item["industry"] == "跨行业"
    assert item["commercial_potential"] == "中"
    assert isinstance(item["tags"], list)
