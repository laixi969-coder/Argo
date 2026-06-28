"""twitter_tikhub 解析单测：合成 timeline 验证归一化，不打网络。"""
from src.sources import twitter_tikhub


def _fake_body():
    return {
        "code": 200,
        "data": {"timeline": [
            {
                "tweet_id": "123",
                "screen_name": "alice",
                "text": "I would pay for an app that auto-files my taxes",
                "favorites": 40,
                "retweets": 8,
                "replies": 12,
            },
            {"tweet_id": "123", "screen_name": "alice", "text": "dup same url"},  # 去重
            {"tweet_id": "", "screen_name": "x", "text": "no id skipped"},        # 跳过
        ]},
    }


def test_extract_normalizes_tweet():
    out = twitter_tikhub._extract_tweets(_fake_body())
    assert len(out) == 1
    o = out[0]
    assert o["source"] == "twitter"
    assert o["url"] == "https://x.com/alice/status/123"
    assert "auto-files my taxes" in o["raw_text"] and o["raw_text"].startswith("@alice:")
    assert o["signal"] == 60.0  # 40 + 8 + 12


if __name__ == "__main__":
    test_extract_normalizes_tweet()
    print("ok")
