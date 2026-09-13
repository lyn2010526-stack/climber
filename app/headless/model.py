"""Standard-library Chat Completions client and explicitly scripted test model."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request


class ModelError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ModelError("Model endpoint redirects are disabled")


class OpenAICompatibleModel:
    label = "openai-compatible"

    def __init__(self, base_url: str, model: str, api_key: str, insecure_http: bool = False):
        parsed = urllib.parse.urlsplit(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Invalid USER_LLM_BASE_URL")
        if parsed.scheme == "http" and not insecure_http and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Remote model endpoints require HTTPS")
        if not model or not api_key:
            raise ValueError("USER_LLM_MODEL and USER_LLM_API_KEY are required")
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.api_key = api_key

    @classmethod
    def from_environment(cls):
        return cls(
            os.environ.get("USER_LLM_BASE_URL", "https://api.openai.com/v1"),
            os.environ.get("USER_LLM_MODEL", ""),
            os.environ.get("USER_LLM_API_KEY", ""),
        )

    @classmethod
    def from_arc_env(cls):
        """Build from ARC-Bench platform injected vars, falling back to USER_LLM_*.

        The platform provides OPENAI_API_KEY / OPENAI_BASE_URL / MODEL. Platform
        endpoints may be plain-HTTP seats on the grading network, so HTTPS
        enforcement is relaxed on this path only.
        """

        def pick(primary: str, fallback: str, default: str = "") -> str:
            value = os.environ.get(primary, "").strip()
            if value:
                return value
            return os.environ.get(fallback, "").strip() or default

        api_key = pick("OPENAI_API_KEY", "USER_LLM_API_KEY")
        model = pick("MODEL", "USER_LLM_MODEL")
        base_url = pick("OPENAI_BASE_URL", "USER_LLM_BASE_URL", "https://api.openai.com/v1")
        if not base_url.rstrip("/").endswith("/v1") and not base_url.rstrip("/").endswith("/chat/completions"):
            base_url = base_url.rstrip("/") + "/v1"
        if base_url.rstrip("/").endswith("/chat/completions"):
            base_url = base_url.rstrip("/")[: -len("/chat/completions")]
        return cls(base_url, model, api_key, insecure_http=True)

    def complete(self, messages, tools, max_tokens, timeout):
        payload = json.dumps(
            {"model": self.model, "messages": messages, "tools": tools, "max_tokens": max_tokens, "stream": False}
        ).encode()
        request = urllib.request.Request(
            self.url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.api_key,
            },
        )
        try:
            with urllib.request.build_opener(NoRedirect).open(request, timeout=timeout) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ModelError("Model response exceeds byte limit")
            return json.loads(raw)
        except urllib.error.HTTPError as exc:
            raise ModelError(f"Model HTTP error {exc.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise ModelError("Model transport or JSON error") from None


class ScriptedFakeModel:
    label = "scripted-fake"

    def __init__(self, responses: list):
        if not isinstance(responses, list):
            raise ValueError("Fake model script must be a JSON array of response envelopes")
        self.responses = iter(responses)

    def complete(self, messages, tools, max_tokens, timeout):
        try:
            return next(self.responses)
        except StopIteration:
            raise ModelError("Scripted fake model exhausted") from None
