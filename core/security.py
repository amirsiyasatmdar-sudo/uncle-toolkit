"""Input validation and explicit target-scope checks."""
from __future__ import annotations
import ipaddress
import re

_DOMAIN_LABEL = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{16,256}$")

def validate_domain(domain: str) -> str:
    if not isinstance(domain, str):
        raise ValueError("Domain must be text")
    value = domain.strip().rstrip(".")
    if not value or len(value) > 253 or "://" in value or "/" in value:
        raise ValueError("Invalid domain")
    try:
        value = value.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError("Invalid internationalized domain") from exc
    labels = value.split(".")
    if len(labels) < 2 or any(not _DOMAIN_LABEL.fullmatch(x) for x in labels):
        raise ValueError("Invalid domain")
    return value

def validate_safe_name(value: str) -> str:
    if not isinstance(value, str) or not _SAFE_NAME.fullmatch(value):
        raise ValueError("Name contains unsupported characters")
    return value

def validate_port(port: int | str) -> int:
    if isinstance(port, bool):
        raise ValueError("Invalid port")
    try:
        result = int(port)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid port") from exc
    if not 1 <= result <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    return result

def is_loopback_target(target: str) -> bool:
    if not isinstance(target, str) or not target.strip():
        return False
    host = target.strip().strip("[]").lower()
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False

def target_is_in_scope(target: str, *, ownership_verified: bool = False,
                       authorization_confirmed: bool = False) -> bool:
    """Non-loopback targets require both ownership proof and explicit authorization."""
    if is_loopback_target(target):
        return True
    return bool(ownership_verified and authorization_confirmed)

def verify_dns_txt_ownership(domain: str, expected_token: str, *, resolver=None) -> bool:
    """Check _uncle-toolkit-verify.<domain> TXT; DNS proof is not legal authorization."""
    normalized = validate_domain(domain)
    if not isinstance(expected_token, str) or not _TOKEN.fullmatch(expected_token):
        raise ValueError("Token must be 16-256 URL-safe characters")
    try:
        if resolver is None:
            import dns.resolver
            resolver = dns.resolver
        answers = resolver.resolve(f"_uncle-toolkit-verify.{normalized}", "TXT", lifetime=4.0)
        for answer in answers:
            value = b"".join(getattr(answer, "strings", ())).decode("utf-8", errors="replace")
            if value == expected_token:
                return True
    except ImportError:
        return False
    except Exception as exc:
        if exc.__class__.__module__.startswith("dns.") or isinstance(exc, OSError):
            return False
        raise
    return False
