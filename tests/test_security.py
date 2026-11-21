import pytest
from core.security import (
    is_loopback_target,
    target_is_in_scope,
    validate_domain,
    validate_port,
    validate_safe_name,
    verify_dns_txt_ownership,
)


def test_domain_normalization():
    assert validate_domain("Example.COM.") == "example.com"


@pytest.mark.parametrize(
    "value", ["", "https://example.com", "bad_domain.com", "-bad.com", "localhost"]
)
def test_invalid_domains(value):
    with pytest.raises(ValueError):
        validate_domain(value)


def test_port_validation():
    assert validate_port("443") == 443
    assert validate_port(" 443 ") == 443
    assert validate_port(443) == 443

    for value in (
        0, 65536, "abc", True, 80.5, 80.0,
        "80.5", "+443", None
    ):
        with pytest.raises(ValueError):
            validate_port(value)


def test_safe_name():
    assert validate_safe_name("plugin-1") == "plugin-1"
    with pytest.raises(ValueError):
        validate_safe_name("../bad")


def test_loopback_scope_default():
    assert is_loopback_target("127.0.0.1")
    assert is_loopback_target("::1")
    assert is_loopback_target("localhost")
    assert not target_is_in_scope("example.com")
    assert target_is_in_scope(
        "example.com", ownership_verified=True, authorization_confirmed=True
    )
    assert not target_is_in_scope("example.com", ownership_verified=True)


def test_dns_txt_verification_with_stub():
    class Answer:
        strings = [b"abcdefghijklmnop"]

    class Resolver:
        def resolve(self, name, record_type, lifetime):
            assert name == "_uncle-toolkit-verify.example.com"
            assert record_type == "TXT" and lifetime == 4.0
            return [Answer()]

    assert verify_dns_txt_ownership(
        "example.com", "abcdefghijklmnop", resolver=Resolver()
    )


@pytest.mark.parametrize("value", [None, 123, "", "../bad", "a" * 65])
def test_safe_name_rejects_invalid_inputs(value):
    with pytest.raises(ValueError):
        validate_safe_name(value)


@pytest.mark.parametrize("value", [None, 123, "", "a" * 254])
def test_domain_rejects_invalid_input_types_and_lengths(value):
    with pytest.raises(ValueError):
        validate_domain(value)


def test_dns_txt_wrong_token_returns_false():
    class Answer:
        strings = [b"abcdefghijklmnop"]

    class Resolver:
        def resolve(self, name, record_type, lifetime):
            return [Answer()]

    assert not verify_dns_txt_ownership(
        "example.com", "ponmlkjihgfedcba", resolver=Resolver()
    )


def test_dns_txt_empty_response_returns_false():
    class Resolver:
        def resolve(self, name, record_type, lifetime):
            return []

    assert not verify_dns_txt_ownership(
        "example.com", "abcdefghijklmnop", resolver=Resolver()
    )


def test_dns_txt_os_error_returns_false():
    class Resolver:
        def resolve(self, name, record_type, lifetime):
            raise OSError("simulated DNS network error")

    assert not verify_dns_txt_ownership(
        "example.com", "abcdefghijklmnop", resolver=Resolver()
    )


def test_domain_rejects_invalid_idna_input():
    with pytest.raises(ValueError, match="Invalid internationalized domain"):
        validate_domain("\ud800.example")


@pytest.mark.parametrize("value", [None, 123, ""])
def test_loopback_rejects_invalid_inputs(value):
    assert not is_loopback_target(value)


@pytest.mark.parametrize("target", ["localhost", "127.0.0.1", "::1"])
def test_loopback_targets_are_in_scope(target):
    assert target_is_in_scope(target)


@pytest.mark.parametrize("token", [None, "short", "invalid-token!"])
def test_dns_txt_rejects_invalid_tokens(token):
    class Resolver:
        def resolve(self, name, record_type, lifetime):
            raise AssertionError("Resolver must not be called")

    with pytest.raises(ValueError, match="Token must be"):
        verify_dns_txt_ownership(
            "example.com",
            token,
            resolver=Resolver(),
        )


def test_dns_txt_returns_false_when_dnspython_is_missing(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def blocked_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "dns.resolver":
            raise ImportError("simulated missing optional dependency")

        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked_import)

    assert not verify_dns_txt_ownership(
        "example.com",
        "abcdefghijklmnop",
    )


def test_dns_txt_reraises_unexpected_resolver_errors():
    class Resolver:
        def resolve(self, name, record_type, lifetime):
            raise RuntimeError("unexpected resolver failure")

    with pytest.raises(RuntimeError, match="unexpected resolver failure"):
        verify_dns_txt_ownership(
            "example.com",
            "abcdefghijklmnop",
            resolver=Resolver(),
        )


def test_dns_txt_uses_available_dnspython_resolver(monkeypatch):
    import builtins
    from types import SimpleNamespace

    class Answer:
        strings = [b"abcdefghijklmnop"]

    class Resolver:
        def resolve(self, name, record_type, lifetime):
            assert name == "_uncle-toolkit-verify.example.com"
            assert record_type == "TXT"
            assert lifetime == 4.0
            return [Answer()]

    fake_dns = SimpleNamespace(resolver=Resolver())
    original_import = builtins.__import__

    def mocked_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "dns.resolver":
            return fake_dns

        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", mocked_import)

    assert verify_dns_txt_ownership(
        "example.com",
        "abcdefghijklmnop",
    )
