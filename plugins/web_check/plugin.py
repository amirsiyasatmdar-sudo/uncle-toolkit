"""Local-only HTTP/TLS security checks.

This plugin intentionally accepts only literal loopback IP addresses.
It does not follow redirects, use environment proxies, or contact DNS names.
"""

from __future__ import annotations

from datetime import datetime, timezone
import ipaddress
import math
import socket
import ssl
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)

from core.plugin_loader import BasePlugin


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Plugin(BasePlugin):
    """Perform a bounded, read-only check against a loopback web service."""

    def __init__(self) -> None:
        self._last_result: dict[str, Any] | None = None

    def get_metadata(self) -> dict[str, Any]:
        return {
            "name": "web_check",
            "version": "1.0.0",
            "description": "Local-only HTTP security header and TLS checks",
        }

    def validate(self) -> bool:
        return True

    @staticmethod
    def _parse_target(url: str):
        if not isinstance(url, str) or len(url) > 2048:
            raise ValueError("URL must be text no longer than 2048 characters")
        parts = urlsplit(url)
        if parts.scheme.lower() not in {"http", "https"}:
            raise ValueError("Only http and https URLs are supported")
        if (
            not parts.hostname
            or parts.username is not None
            or parts.password is not None
        ):
            raise ValueError("URL must contain a host and no embedded credentials")
        if parts.fragment:
            raise ValueError("URL fragments are not supported")
        try:
            address = ipaddress.ip_address(parts.hostname)
        except ValueError as exc:
            raise ValueError(
                "Only literal loopback IP addresses are allowed; DNS names are disabled"
            ) from exc
        if not address.is_loopback or getattr(address, "ipv4_mapped", None) is not None:
            raise ValueError("Target must be a canonical loopback IP address")
        try:
            port = parts.port
        except ValueError as exc:
            raise ValueError("Invalid target port") from exc
        if port is None:
            port = 443 if parts.scheme.lower() == "https" else 80
        if not 1 <= port <= 65535:
            raise ValueError("Invalid target port")
        path = parts.path or "/"
        if parts.query:
            path += "?" + parts.query
        # Rebuild authority from parsed literal IP and validated port.
        host_for_url = (
            f"[{address.compressed}]" if address.version == 6 else address.compressed
        )
        default_port = 443 if parts.scheme.lower() == "https" else 80
        authority = host_for_url if port == default_port else f"{host_for_url}:{port}"
        normalized = f"{parts.scheme.lower()}://{authority}{path}"
        return parts.scheme.lower(), address.compressed, port, normalized

    @staticmethod
    def _check_certificate(host: str, port: int, timeout: float) -> dict[str, Any]:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=host) as tls:
                cert = tls.getpeercert()
                if not cert:
                    raise ssl.SSLError("Peer did not provide a verifiable certificate")
                not_after = cert.get("notAfter")
                expires_at = None
                days_remaining = None
                if not_after:
                    expiry = datetime.fromtimestamp(
                        ssl.cert_time_to_seconds(not_after), tz=timezone.utc
                    )
                    expires_at = expiry.isoformat()
                    days_remaining = (expiry - datetime.now(timezone.utc)).days
                return {
                    "valid": True,
                    "expires_at": expires_at,
                    "days_remaining": days_remaining,
                }

    def run(
        self, url: str | None = None, timeout: float = 3.0, **kwargs: Any
    ) -> dict[str, Any]:
        if kwargs:
            raise ValueError("Unsupported options")
        if url is None:
            raise ValueError("A loopback URL is required")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise ValueError("Timeout must be a number")
        try:
            timeout_value = float(timeout)
        except (OverflowError, ValueError) as exc:
            raise ValueError("Timeout must be a finite number") from exc
        if not math.isfinite(timeout_value) or not 0.2 <= timeout_value <= 10.0:
            raise ValueError("Timeout must be between 0.2 and 10 seconds")

        scheme, host, port, normalized_url = self._parse_target(url)
        started = time.monotonic()
        certificate: dict[str, Any] | None = None
        if scheme == "https":
            try:
                certificate = self._check_certificate(host, port, timeout_value)
            except (OSError, ssl.SSLError, ValueError) as exc:
                certificate = {"valid": False, "error": type(exc).__name__}

        request = Request(
            normalized_url,
            headers={
                "User-Agent": "uncle-toolkit-web-check/1.0.0",
                "Connection": "close",
            },
            method="GET",
        )
        opener = build_opener(
            ProxyHandler({}),  # Ignore HTTP(S)_PROXY environment variables.
            _NoRedirect(),
            HTTPSHandler(context=ssl.create_default_context()),
        )
        status = None
        headers: dict[str, str] = {}
        redirect_location = None
        request_error = None
        try:
            with opener.open(request, timeout=timeout_value) as response:
                status = response.status
                headers = {k.lower(): v for k, v in response.headers.items()}
                if status is not None and 300 <= status < 400:
                    redirect_location = headers.get("location")
        except HTTPError as exc:
            status = exc.code
            headers = {k.lower(): v for k, v in exc.headers.items()}
            if 300 <= exc.code < 400:
                redirect_location = exc.headers.get("Location")
            exc.close()
        except (URLError, OSError, TimeoutError, ssl.SSLError) as exc:
            reason = getattr(exc, "reason", exc)
            request_error = type(reason).__name__

        elapsed_ms = round((time.monotonic() - started) * 1000, 2)
        checks = {
            "strict_transport_security": bool(headers.get("strict-transport-security"))
            if scheme == "https"
            else False,
            "content_security_policy": bool(headers.get("content-security-policy")),
            "x_content_type_options": headers.get("x-content-type-options", "").lower()
            == "nosniff",
            "frame_protection": bool(
                headers.get("x-frame-options")
                or "frame-ancestors"
                in headers.get("content-security-policy", "").lower()
            ),
            "referrer_policy": bool(headers.get("referrer-policy")),
        }
        result = {
            "plugin": "web_check",
            "version": "1.0.0",
            "target": normalized_url,
            "status_code": status,
            "response_time_ms": elapsed_ms,
            "security_headers": checks,
            "tls_certificate": certificate,
            "redirect_location": redirect_location,
            "error": request_error,
        }
        self._last_result = result
        return result
