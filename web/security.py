from urllib.parse import urlsplit

ALLOWED_HOST = "127.0.0.1"
SAFE_METHODS = {"GET", "HEAD"}


def _has_whitespace_or_control(value):
    return any(
        char.isspace() or ord(char) < 32 or ord(char) == 127
        for char in value
    )


def valid_host(value):
    if not value or len(value) > 255:
        return False

    if _has_whitespace_or_control(value):
        return False

    if value.endswith(":"):
        return False

    try:
        parsed = urlsplit("//" + value)

        return (
            parsed.hostname == ALLOWED_HOST
            and parsed.username is None
            and parsed.password is None
            and not parsed.path
            and not parsed.query
            and not parsed.fragment
            and (parsed.port is None or 1 <= parsed.port <= 65535)
        )
    except ValueError:
        return False


def valid_origin(origin, host):
    if not origin or len(origin) > 512:
        return False

    if _has_whitespace_or_control(origin):
        return False

    if not valid_host(host):
        return False

    try:
        parsed = urlsplit(origin)
        host_parsed = urlsplit("//" + host)

        origin_port = parsed.port if parsed.port is not None else 80
        host_port = host_parsed.port if host_parsed.port is not None else 80

        return (
            parsed.scheme == "http"
            and parsed.hostname == ALLOWED_HOST
            and parsed.username is None
            and parsed.password is None
            and parsed.path in ("", "/")
            and not parsed.query
            and not parsed.fragment
            and (parsed.port is None or 1 <= parsed.port <= 65535)
            and origin_port == host_port
        )
    except ValueError:
        return False


def validate_request(method, host, origin=None, fetch_site=None):
    if method.upper() not in SAFE_METHODS:
        return 405, "Method not allowed"

    if not valid_host(host):
        return 400, "Invalid Host header"

    if origin is not None and not valid_origin(origin, host):
        return 403, "Cross-origin request rejected"

    if fetch_site is not None:
        normalized_fetch_site = fetch_site.strip().lower()

        if normalized_fetch_site not in {"same-origin", "none"}:
            return 403, "Cross-site request rejected"

    return None
