import json
import time
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.config import settings


class LLMProviderError(RuntimeError):
    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code


class LLMProviderTimeout(LLMProviderError):
    def __init__(self, message: str = "LLM provider timed out"):
        super().__init__("provider_timeout", message)


class LLMProviderResponseError(LLMProviderError):
    pass


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMRequest:
    messages: list[LLMMessage]
    model: str
    temperature: float = 0.1
    max_tokens: int = 1024
    json_schema: dict | None = None
    timeout_seconds: float | None = None
    max_retries: int | None = None


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict = field(default_factory=dict)
    latency_ms: int | None = None


class LLMProvider(Protocol):
    def complete(self, request: LLMRequest) -> LLMResponse: ...


class NoopProvider:
    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content=json.dumps(
                {
                    "status": "skipped",
                    "confidence": 0,
                    "provider": "noop",
                    "model": request.model,
                    "prompt_version": "noop",
                    "issues": [],
                    "suggested_adjustments": [],
                    "user_summary_ru": None,
                    "defense_trace": "LLM quality gate is disabled.",
                }
            ),
            model=request.model,
            usage={},
            latency_ms=0,
        )


class FakeProvider:
    def __init__(self, responses: list[str] | None = None, error: Exception | None = None):
        self.responses = responses or []
        self.error = error
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if self.error:
            raise self.error
        content = self.responses.pop(0) if self.responses else "{}"
        return LLMResponse(content=content, model=request.model, usage={"fake": True}, latency_ms=1)


class YandexAIStudioQwenProvider:
    def __init__(
        self,
        api_key: str | None = None,
        folder_id: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        data_logging_enabled: bool | None = None,
    ):
        self.api_key = api_key or settings.LLM_API_KEY
        self.folder_id = folder_id or settings.LLM_FOLDER_ID
        self.base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.LLM_TIMEOUT_SECONDS
        self.max_retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES
        self.data_logging_enabled = (
            data_logging_enabled if data_logging_enabled is not None else settings.LLM_DATA_LOGGING_ENABLED
        )

    def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise LLMProviderError("missing_api_key", "Yandex AI Studio API key is not configured")
        if not self.folder_id:
            raise LLMProviderError("missing_folder_id", "Yandex AI Studio folder id is not configured")

        payload = {
            "model": self._model_uri(request.model),
            "messages": [{"role": message.role, "content": message.content} for message in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        if request.json_schema:
            payload["response_format"] = {"type": "json_schema", "json_schema": request.json_schema}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.api_key}",
            "OpenAI-Project": self.folder_id,
            "x-data-logging-enabled": "true" if self.data_logging_enabled else "false",
        }
        last_error: Exception | None = None
        max_retries = self.max_retries if request.max_retries is None else request.max_retries
        timeout_seconds = self.timeout_seconds if request.timeout_seconds is None else request.timeout_seconds
        for attempt in range(max_retries + 1):
            try:
                return self._post(payload, headers, timeout_seconds, request.model)
            except LLMProviderTimeout as exc:
                last_error = exc
                if attempt >= max_retries:
                    raise
            except LLMProviderError as exc:
                last_error = exc
                if attempt >= max_retries or not exc.error_code.startswith("http_"):
                    raise
        raise LLMProviderError("provider_unknown", str(last_error) if last_error else "LLM provider failed")

    def _post(self, payload: dict, headers: dict, timeout_seconds: float, display_model: str) -> LLMResponse:
        start = time.perf_counter()
        try:
            timeout = httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 2.0), write=2.0, pool=1.0)
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            raise LLMProviderTimeout() from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError("network_error", str(exc)) from exc

        latency_ms = int((time.perf_counter() - start) * 1000)
        if response.status_code >= 400:
            raise LLMProviderResponseError(f"http_{response.status_code}", response.text[:500])
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMProviderResponseError("invalid_response", "Unexpected Yandex AI Studio response") from exc
        return LLMResponse(content=content, model=display_model, usage=data.get("usage") or {}, latency_ms=latency_ms)

    def _model_uri(self, model: str) -> str:
        if model.startswith("gpt://"):
            return model
        return f"gpt://{self.folder_id}/{model}"


def get_provider() -> LLMProvider:
    if not settings.LLM_QUALITY_ENABLED:
        return NoopProvider()
    if settings.LLM_PROVIDER == "yandex":
        return YandexAIStudioQwenProvider()
    return NoopProvider()
