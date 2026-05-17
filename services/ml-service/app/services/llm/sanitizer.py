import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
TOKEN_RE = re.compile(r"(?i)\b(?:api[_-]?key|token|secret|password|jwt)\s*[:=]\s*[\w.\-+/=]{8,}")
WHITESPACE_RE = re.compile(r"\s+")
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore (?:all )?(?:previous|prior|system) instructions"),
    re.compile(r"(?i)disregard (?:all )?(?:previous|prior|system) instructions"),
    re.compile(r"(?i)reveal (?:the )?(?:system prompt|developer message|secret|token)"),
]
FORBIDDEN_CONTEXT_KEYS = {"email", "oauth", "token", "cookie", "secret", "password", "authorization"}


@dataclass(frozen=True)
class SanitizedNote:
    text: str
    flags: list[str] = field(default_factory=list)
    original_sha256: str | None = None


def sanitize_note(value: str | None, max_chars: int = 1200) -> SanitizedNote:
    if not value:
        return SanitizedNote(text="", flags=[])
    original = value
    flags: set[str] = set()
    text, count = EMAIL_RE.subn("[email]", value)
    if count:
        flags.add("email_masked")
    text, count = PHONE_RE.subn("[phone]", text)
    if count:
        flags.add("phone_masked")
    text, count = TOKEN_RE.subn("[secret]", text)
    if count:
        flags.add("secret_masked")
    for pattern in PROMPT_INJECTION_PATTERNS:
        text, count = pattern.subn("[ignored_instruction]", text)
        if count:
            flags.add("prompt_injection_text_removed")
    text = WHITESPACE_RE.sub(" ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rstrip()
        flags.add("truncated")
    return SanitizedNote(text=text, flags=sorted(flags), original_sha256=hashlib.sha256(original.encode()).hexdigest())


def sanitize_context(value: Any, max_note_chars: int = 1200) -> Any:
    if isinstance(value, dict):
        sanitized = {}
        for key, nested in value.items():
            if any(part in key.lower() for part in FORBIDDEN_CONTEXT_KEYS):
                continue
            if isinstance(nested, str) and ("note" in key.lower() or "text" in key.lower()):
                sanitized[key] = sanitize_note(nested, max_chars=max_note_chars).__dict__
            else:
                sanitized[key] = sanitize_context(nested, max_note_chars=max_note_chars)
        return sanitized
    if isinstance(value, list):
        return [sanitize_context(item, max_note_chars=max_note_chars) for item in value]
    return value
