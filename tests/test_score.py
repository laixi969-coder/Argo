from src.score import score_real_demand


def test_score_fills_fields():
    opps = [{"idea": "给独立开发者的发票工具", "signal": 50}]
    out = score_real_demand(opps, llm=lambda p: '{"verdict":"真需求","score":75,"reason":"用户一直吐槽离不开"}')
    assert out[0]["verdict"] == "真需求"
    assert out[0]["score"] == 75
    assert out[0]["reason"]
    assert out[0]["commercial_potential"] == "中"
    assert out[0]["category"] == "服务"
    assert out[0]["industry"] == "金融"
    assert out[0]["tags"]

def test_score_degrades_on_bad_json():
    def bad_llm(prompt):
        raise RuntimeError("judge timeout")

    opps = [{"idea": "x", "signal": 40}]
    out = score_real_demand(opps, llm=bad_llm)
    assert out[0]["verdict"] == "待验证"
    assert out[0]["score"] == 40
    assert out[0]["judge_error"] == "judge_timeout"


def test_score_failure_cannot_become_high_potential_from_source_heat():
    item = score_real_demand(
        [{"idea": "热门但未精判", "signal": 100}], llm=lambda p: "bad json"
    )[0]

    assert item["score"] == 45
    assert item["commercial_potential"] == "低"
    assert item["verdict"] == "待验证"


def test_score_failure_rewrites_repo_title_and_fills_analysis_fields():
    item = score_real_demand(
        [{
            "idea": "yuanzhongqiao/printfilm：AI Short Film Motion Comic Generation Platform",
            "title": "yuanzhongqiao/printfilm",
            "raw_text": "AI Short Film Motion Comic Generation Platform",
            "source": "github",
            "signal": 100,
        }],
        llm=lambda p: "bad json",
    )[0]

    assert item["idea"] == "AI 短片漫画生成开始产品化：内容团队可以把分镜资产直接压成可验证样片"
    assert item["pain"] and item["buyer"] and item["money"]
    assert "/" not in item["idea"]


def test_score_failure_keeps_distinct_fallback_titles_for_different_repos():
    items = score_real_demand(
        [
            {
                "idea": "team/video-maker：AI Short Film Motion Comic Generation Platform",
                "title": "team/video-maker",
                "raw_text": "AI Short Film Motion Comic Generation Platform",
                "source": "github",
                "signal": 100,
            },
            {
                "idea": "team/scene-studio：Image to Video Storyboard Tool",
                "title": "team/scene-studio",
                "raw_text": "Image to Video Storyboard Tool",
                "source": "github",
                "signal": 100,
            },
        ],
        llm=lambda p: "bad json",
    )

    assert items[0]["idea"] != items[1]["idea"]
    assert items[0]["idea"] == "AI 短片漫画生成开始产品化：内容团队可以把分镜资产直接压成可验证样片"
    assert items[1]["idea"] == "图生视频进入快预览阶段：内容团队可以低成本批量试镜头再筛选精修"


def test_score_failure_uses_task_titles_not_obscure_product_names():
    items = score_real_demand(
        [
            {
                "idea": "Windsurf",
                "title": "Windsurf",
                "raw_text": "AI coding IDE integration for developer productivity",
                "source": "futurepedia",
                "signal": 70,
            },
            {
                "idea": "Wan2.2 14B Preview",
                "title": "Wan2.2 14B Preview",
                "raw_text": "open model preview for video generation",
                "source": "huggingface",
                "signal": 100,
            },
            {
                "idea": "team/nopua：Agent workflow dashboard",
                "title": "team/nopua",
                "raw_text": "Agent workflow dashboard for teams",
                "source": "github",
                "signal": 100,
            },
        ],
        llm=lambda p: "bad json",
    )

    assert [item["idea"] for item in items] == [
        "IDE 编程助手从补全走向交付：开发者需要能理解项目并可靠改代码的工具",
        "图生视频进入快预览阶段：内容团队可以低成本批量试镜头再筛选精修",
        "AI Agent 从单人玩具走向团队协作：任务编排、权限、日志和交付追踪会成为刚需",
    ]


def test_score_success_keeps_specific_chinese_title():
    raw = '''{
      "verdict":"待验证",
      "score":62,
      "category":"Agent",
      "industry":"内容创意",
      "commercial_potential":"中",
      "idea":"给短剧团队的角色一致性分镜生成工具",
      "reason":"有交付成果但缺少付费证据"
    }'''
    item = score_real_demand([{
        "idea": "yuanzhongqiao/printfilm：AI Short Film Motion Comic Generation Platform",
        "title": "yuanzhongqiao/printfilm",
        "raw_text": "AI Short Film Motion Comic Generation Platform",
        "source": "github",
        "signal": 100,
    }], llm=lambda p: raw)[0]

    assert item["idea"] == "给短剧团队的角色一致性分镜生成工具"


def test_score_success_keeps_opportunity_judgement_title():
    raw = '''{
      "verdict":"待验证",
      "score":66,
      "category":"AI应用",
      "industry":"内容创意",
      "commercial_potential":"中",
      "idea":"中文 TTS 成本继续下降：品牌声音、短视频配音和 AI 客服开始适合小团队试水",
      "reason":"有可运行 Demo 但缺少付费证据"
    }'''
    item = score_real_demand([{
        "idea": "Qwen3-TTS Demo",
        "title": "Qwen3-TTS Demo",
        "raw_text": "Qwen3-TTS Demo text to speech voice generation",
        "source": "huggingface",
        "signal": 80,
    }], llm=lambda p: raw)[0]

    assert item["idea"] == "中文 TTS 成本继续下降：品牌声音、短视频配音和 AI 客服开始适合小团队试水"


def test_score_success_rewrites_missing_or_generic_idea():
    raw = '''{
      "verdict":"待验证",
      "score":60,
      "category":"AI应用",
      "industry":"内容创意",
      "commercial_potential":"中",
      "hook":"图生视频模型可以更快生成预览片段",
      "buyer":"内容团队",
      "angle":"图生视频快预览",
      "risk":"缺少稳定质量和付费证据",
      "reason":"有模型预览但缺少付费证据"
    }'''
    item = score_real_demand([{
        "idea": "围绕「Wan2.2 14B Fast Preview」的 AI 应用机会",
        "title": "Wan2.2 14B Fast Preview",
        "raw_text": "generate a video from an image with a text prompt",
        "source": "huggingface",
        "signal": 90,
    }], llm=lambda p: raw)[0]

    assert item["idea"] == "图生视频进入快预览阶段：内容团队可以低成本批量试镜头再筛选精修"


def test_unknown_technical_title_fallback_is_not_source_summary():
    item = score_real_demand(
        [{
            "idea": "team/unknown-demo：Next Gen AI Demo",
            "title": "team/unknown-demo",
            "raw_text": "Next Gen AI Demo for a narrow task",
            "source": "github",
            "signal": 80,
        }],
        llm=lambda p: "bad json",
    )[0]

    assert item["idea"] == "新 AI 工具信号：先判断它替代哪段人工、谁会付费和能否持续交付"
    assert "围绕" not in item["idea"]
    assert "unknown-demo" not in item["idea"]


def test_qwen_coding_model_does_not_fall_into_tts_title():
    item = score_real_demand(
        [{
            "idea": "Qwen3-Coder-14B",
            "title": "Qwen3-Coder-14B",
            "raw_text": "Qwen coding model for code completion and agentic editing",
            "source": "huggingface",
            "signal": 80,
        }],
        llm=lambda p: "bad json",
    )[0]

    assert "TTS" not in item["idea"]
    assert "配音" not in item["idea"]
    assert item["idea"] == "AI 编程工具需要重点看：它是否解决准确改代码和团队可控交付问题"


def test_non_video_14b_preview_does_not_fall_into_video_title():
    item = score_real_demand(
        [{
            "idea": "Foo-14B Preview",
            "title": "Foo-14B Preview",
            "raw_text": "large language model preview for document analysis",
            "source": "huggingface",
            "signal": 80,
        }],
        llm=lambda p: "bad json",
    )[0]

    assert "图生视频" not in item["idea"]
    assert "试镜头" not in item["idea"]
    assert item["idea"] == "新 AI 工具信号：先判断它替代哪段人工、谁会付费和能否持续交付"


def test_chinese_opportunity_title_with_slash_is_preserved():
    raw = '''{
      "verdict":"待验证",
      "score":64,
      "category":"服务",
      "industry":"金融",
      "commercial_potential":"中",
      "idea":"收款/风控压力上升：出海平台需要备用支付通道和资金预案",
      "reason":"案例暴露资金冻结风险但缺少付费验证"
    }'''
    item = score_real_demand([{
        "idea": "Stripe withheld funds",
        "title": "Stripe withheld funds",
        "raw_text": "Stripe withheld $85k from our EU platform",
        "source": "hackernews",
        "signal": 80,
    }], llm=lambda p: raw)[0]

    assert item["idea"] == "收款/风控压力上升：出海平台需要备用支付通道和资金预案"


def test_mixed_language_opportunity_judgement_title_is_preserved():
    raw = '''{
      "verdict":"待验证",
      "score":64,
      "category":"Agent",
      "industry":"开发者工具",
      "commercial_potential":"中",
      "idea":"MCP/Agent 成本下降：团队开始需要权限、日志和协作层",
      "reason":"协作需求成立但缺少付费验证"
    }'''
    item = score_real_demand([{
        "idea": "Agent workflow dashboard",
        "title": "Agent workflow dashboard",
        "raw_text": "MCP and agent workflow dashboard for teams",
        "source": "github",
        "signal": 80,
    }], llm=lambda p: raw)[0]

    assert item["idea"] == "MCP/Agent 成本下降：团队开始需要权限、日志和协作层"


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

    assert item["category"] == "服务"
    assert item["industry"] == "跨行业"
    assert item["commercial_potential"] == "中"
    assert isinstance(item["tags"], list)


def test_score_only_labels_a_good_business_candidate_with_strong_market_proof():
    raw = ('{"verdict":"市场已验证","score":91,"reason":"已有持续付费客户",'
           '"commercial_potential":"高","evidence_strength":"强",'
           '"market_proof":"12 家客户连续付费 6 个月"}')
    item = score_real_demand([{"idea": "企业设备维保服务", "signal": 80}], llm=lambda p: raw)[0]

    assert item["business_stage"] == "好生意候选"


def test_score_does_not_label_an_unproven_signal_as_a_good_business():
    raw = ('{"verdict":"待验证","score":88,"reason":"只有热度，没有付款证据",'
           '"commercial_potential":"高","evidence_strength":"弱","market_proof":"无"}')
    item = score_real_demand([{"idea": "热门消费品趋势", "signal": 95}], llm=lambda p: raw)[0]

    assert item["business_stage"] == "发现线索"
