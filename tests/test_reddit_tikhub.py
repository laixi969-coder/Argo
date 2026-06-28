"""reddit_tikhub 解析单测：用合成的 TikHub 组件流验证归一化，不打网络。"""
from src.sources import reddit_tikhub


def _fake_body():
    post = {
        "postTitle": "I wish there was an app for tracking subscriptions",
        "permalink": "/r/apps/comments/abc/i_wish/",
        "url": "https://www.reddit.com/r/apps/comments/abc/i_wish/",
        "content": {"markdown": "Spending too much, no good tool exists. Would pay."},
        "subreddit": {"prefixedName": "r/apps"},
        "score": 42,
        "commentCount": 13,
    }
    # 模拟真实嵌套：data.search.dynamic.components.main.edges[].node.children[].post
    return {
        "code": 200,
        "data": {"search": {"dynamic": {"components": {"main": {"edges": [
            {"node": {"children": [{"post": post}]}}
        ]}}}}},
    }


def test_extract_normalizes_post():
    out = reddit_tikhub._extract_posts(_fake_body())
    assert len(out) == 1
    o = out[0]
    assert o["source"] == "reddit"
    assert o["url"] == "https://www.reddit.com/r/apps/comments/abc/i_wish/"
    assert "subscriptions" in o["title"]
    assert "r/apps" in o["raw_text"] and "Would pay" in o["raw_text"]
    assert o["signal"] == 55.0  # score 42 + comments 13


def test_extract_dedupes_and_skips_empty():
    body = _fake_body()
    # 两条同 url → 去重；一条无标题 → 跳过
    edges = body["data"]["search"]["dynamic"]["components"]["main"]["edges"]
    edges.append({"node": {"children": [{"post": dict(edges[0]["node"]["children"][0]["post"])}]}})
    edges.append({"node": {"children": [{"post": {"postTitle": "", "url": "x"}}]}})
    out = reddit_tikhub._extract_posts(body)
    assert len(out) == 1


if __name__ == "__main__":
    test_extract_normalizes_post()
    test_extract_dedupes_and_skips_empty()
    print("ok")
