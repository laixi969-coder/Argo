from src import prefilter, rank
from src.score import score_real_demand
from src.extract import extract_ideas
from src.email_report import render_html

def test_full_pipeline_with_fakes():
    fake_opps = [{"source":"reddit","title":f"need AI tool {i}","raw_text":"",
                  "url":"http://x","signal":float(i)} for i in range(40)]
    top = prefilter.prefilter(fake_opps, 30)
    assert len(top) == 30
    top = extract_ideas(top, llm=lambda p: '{"idea":"某工具","is_ai_application":true}')
    top = score_real_demand(top, llm=lambda p: '{"verdict":"真需求","score":70,"reason":"刚需"}')
    final = rank.rank(top, 20)
    assert len(final) == 20
    assert all(o["verdict"] != "伪需求" for o in final)
    html = render_html(final, [])
    assert "某工具" in html
