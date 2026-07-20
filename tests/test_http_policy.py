from src import http_policy


def test_public_content_has_short_cdn_cache_but_account_pages_do_not():
    assert "s-maxage=300" in http_policy.cache_control("GET", "/daily")
    assert "s-maxage=120" in http_policy.cache_control("GET", "/api/daily")
    assert http_policy.cache_control("GET", "/") == "no-store"
    assert http_policy.cache_control("POST", "/api/chat") == "no-store"
    assert "s-maxage=604800" in http_policy.cache_control("GET", "logo.png", is_static=True)


def test_security_headers_cover_framing_mime_and_browser_capabilities():
    headers = dict(http_policy.security_headers(secure=True))
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert "camera=()" in headers["Permissions-Policy"]
    assert "max-age=31536000" in headers["Strict-Transport-Security"]
