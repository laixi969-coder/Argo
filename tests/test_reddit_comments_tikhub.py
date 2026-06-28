"""reddit_comments_tikhub 解析单测：合成评论组件流验证归一化，不打网络。"""
from src.sources import reddit_comments_tikhub as rc


def _fake_body():
    comment = {
        "id": "t1_abc123",
        "score": 88,
        "content": {"markdown": "There should be an app that auto-tracks my subscriptions, hate doing it manually"},
        "postInfo": {
            "id": "t3_xyz789",
            "title": "What app do you wish existed?",
            "subreddit": {"prefixedName": "r/apps"},
        },
    }
    return {
        "code": 200,
        "data": {"search": {"dynamic": {"components": {"main": {"edges": [
            {"node": {"children": [{"comment": comment}]}}
        ]}}}}},
    }


def test_comment_url():
    assert rc._comment_url("t1_abc123", "t3_xyz789") == "https://www.reddit.com/comments/xyz789/comment/abc123/"
    assert rc._comment_url("", "t3_x") == ""


def test_extract_normalizes_comment():
    out = rc._extract_comments(_fake_body())
    assert len(out) == 1
    o = out[0]
    assert o["source"] == "reddit_comment"
    assert o["url"] == "https://www.reddit.com/comments/xyz789/comment/abc123/"
    assert "auto-tracks my subscriptions" in o["raw_text"]
    assert "r/apps 评论" in o["raw_text"] and "帖:What app" in o["raw_text"]
    assert o["signal"] == 88.0


if __name__ == "__main__":
    test_comment_url()
    test_extract_normalizes_comment()
    print("ok")
