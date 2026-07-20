from io import BytesIO

from api import index
from src import traffic


def _call(path, *, method="GET", body=b"", content_length=None, ip="198.51.100.11"):
    recorded = {}
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "CONTENT_LENGTH": str(len(body) if content_length is None else content_length),
        "wsgi.input": BytesIO(body),
        "REMOTE_ADDR": ip,
    }

    def start_response(status, headers):
        recorded["status"] = status
        recorded["headers"] = dict(headers)

    result = b"".join(index.app(environ, start_response))
    return recorded, result


def test_vercel_entry_sets_public_cache_and_security_headers(monkeypatch):
    traffic._reset_for_tests()
    monkeypatch.delenv("VERCEL", raising=False)
    recorded, _ = _call("/api/daily")
    assert recorded["status"].startswith("200")
    assert "s-maxage=120" in recorded["headers"]["Cache-Control"]
    assert recorded["headers"]["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in recorded["headers"]


def test_vercel_entry_rejects_large_body_before_reading(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    recorded, body = _call("/api/chat", method="POST", content_length=traffic.MAX_BODY_BYTES + 1)
    assert recorded["status"].startswith("413")
    assert recorded["headers"]["Cache-Control"] == "no-store"
    assert "请求体过大" in body.decode("utf-8")
