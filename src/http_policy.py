"""HTTP 响应策略：安全头与可共享内容的缓存边界。"""
from __future__ import annotations


def security_headers(*, secure: bool = False) -> list[tuple[str, str]]:
    """默认收紧浏览器能力；不依赖 Web 框架，供本机与 Vercel 共用。"""
    headers = [
        ("X-Content-Type-Options", "nosniff"),
        ("X-Frame-Options", "DENY"),
        ("Referrer-Policy", "strict-origin-when-cross-origin"),
        ("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()"),
        ("Cross-Origin-Opener-Policy", "same-origin"),
        ("Content-Security-Policy", (
            "default-src 'self'; base-uri 'self'; form-action 'self'; "
            "frame-ancestors 'none'; object-src 'none'; "
            "img-src 'self' data: https:; media-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "connect-src 'self'"
        )),
    ]
    if secure:
        headers.append(("Strict-Transport-Security", "max-age=31536000; includeSubDomains"))
    return headers


def cache_control(method: str, raw_path: str, *, is_static: bool = False) -> str:
    """只缓存与用户身份无关的公开内容，避免 CDN 泄露会话状态。"""
    if is_static:
        # 静态资源会被 Vercel 边缘长期复用；保留一天浏览器缓存以便更换未哈希文件。
        return "public, max-age=86400, s-maxage=604800, stale-while-revalidate=86400"
    if method != "GET":
        return "no-store"

    path = raw_path.split("?", 1)[0]
    public_pages = ("/landing", "/daily", "/all", "/sources", "/robots.txt", "/sitemap.xml", "/llms.txt")
    if path in public_pages or path.startswith("/items/"):
        return "public, max-age=60, s-maxage=300, stale-while-revalidate=600"
    if path in ("/api/daily", "/api/opportunities"):
        return "public, max-age=30, s-maxage=120, stale-while-revalidate=300"
    # / 会随登录 cookie 变更，其他账户、管理、认证、对话入口也不可共享。
    return "no-store"
