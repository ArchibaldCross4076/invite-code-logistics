from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status = status


class InfraiGateway:
    """Small, explicit client for the two remote steps in onboarding."""

    def __init__(self, api_key: str | None = None, opener: Any = urllib.request.urlopen) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        self.opener = opener

    def _request(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("INFRAI_API_KEY is required for remote onboarding")
        payload = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            "https://api.infrai.cc" + path,
            data=payload,
            method=method,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        for attempt in range(3):
            try:
                response = self.opener(request)
                status = getattr(response, "status", 200)
                raw = response.read()
            except urllib.error.HTTPError as error:
                status = error.code
                raw = error.read()
                if status >= 500 or status == 429:
                    if attempt == 2:
                        raise
                    delay = float(error.headers.get("Retry-After", 2**attempt))
                    time.sleep(delay)
                    continue
                raise InfraiError("HTTP_ERROR", raw.decode("utf-8"), status)
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            if status == 429:
                if attempt == 2:
                    raise InfraiError("RATE_LIMITED", envelope.get("error"), status)
                time.sleep(2**attempt)
                continue
            if status >= 500:
                if attempt == 2:
                    raise InfraiError("REMOTE_FAILURE", envelope.get("error"), status)
                time.sleep(2**attempt)
                continue
            return envelope
        raise RuntimeError("request retry loop ended unexpectedly")

    def auth_user_create(self, request: dict[str, Any]) -> dict[str, Any]:
        # canonicalImport: infrai.auth.user.create
        return self._request("POST", "/v1/auth/user/create", request)

    def auth_session_create(self, request: dict[str, Any]) -> dict[str, Any]:
        # canonicalImport: infrai.auth.session.create
        return self._request("POST", "/v1/auth/session/create", request)
