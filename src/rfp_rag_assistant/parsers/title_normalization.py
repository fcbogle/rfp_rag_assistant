from __future__ import annotations

import re


def normalize_section_title(title: str) -> str:
    text = " ".join(title.split()).strip()
    if not text:
        return ""

    if text.isupper():
        return _smart_title(text)

    words = text.split()
    if words and sum(1 for word in words if word[:1].isupper()) / len(words) >= 0.7:
        return _smart_title(text)

    return text


def _smart_title(text: str) -> str:
    minor_words = {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "for",
        "in",
        "of",
        "on",
        "or",
        "the",
        "to",
        "via",
    }

    def transform_token(token: str, *, is_first: bool) -> str:
        if not token:
            return token
        if len(token) == 1 and token.isalpha():
            return token.upper()
        if re.search(r"\d", token) and any(char.islower() for char in token) and any(char.isupper() for char in token):
            return token
        lowered = token.lower()
        if not is_first and lowered in minor_words:
            return lowered
        if re.search(r"\d", token):
            return token.upper()
        if token.isupper() and len(token) <= 4:
            return token
        if "/" in token:
            return "/".join(transform_token(part, is_first=is_first and index == 0) for index, part in enumerate(token.split("/")))
        if "-" in token:
            return "-".join(transform_token(part, is_first=is_first and index == 0) for index, part in enumerate(token.split("-")))
        if re.fullmatch(r"\d+(\.\d+)*", token):
            return token
        return lowered[:1].upper() + lowered[1:]

    return " ".join(transform_token(token, is_first=index == 0) for index, token in enumerate(text.split()))
