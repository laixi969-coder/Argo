from src.score import score_real_demand


def test_score_fills_fields():
    opps = [{"idea": "给独立开发者的发票工具", "signal": 50}]
    out = score_real_demand(opps, llm=lambda p: '{"verdict":"真需求","score":75,"reason":"用户一直吐槽离不开"}')
    assert out[0]["verdict"] == "真需求"
    assert out[0]["score"] == 75
    assert out[0]["reason"]

def test_score_degrades_on_bad_json():
    opps = [{"idea": "x", "signal": 40}]
    out = score_real_demand(opps, llm=lambda p: "模型今天抽风不是 JSON")
    assert out[0]["verdict"] == "待验证"
    assert out[0]["score"] == 40


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
