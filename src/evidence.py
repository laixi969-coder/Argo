"""原文证据的最小可核验工具。"""
import re


_SPACE = re.compile(r"\s+")


def source_text(opportunity: dict) -> str:
    return "\n".join(
        str(opportunity.get(field) or "")
        for field in ("title", "raw_text")
    )


def normalize(text: object) -> str:
    return _SPACE.sub(" ", str(text or "").strip()).casefold()


def is_verbatim(opportunity: dict, quote: object) -> bool:
    normalized_quote = normalize(quote)
    # 太短的片段没有证据价值，也会极易误匹配。
    return len(normalized_quote) >= 8 and normalized_quote in normalize(source_text(opportunity))


def verified_quotes(opportunity: dict, candidates: object, limit: int = 3) -> list[str]:
    if not isinstance(candidates, list):
        return []
    verified = []
    for candidate in candidates:
        quote = str(candidate or "").strip()
        if quote and quote not in verified and is_verbatim(opportunity, quote):
            verified.append(quote)
        if len(verified) >= limit:
            break
    return verified
