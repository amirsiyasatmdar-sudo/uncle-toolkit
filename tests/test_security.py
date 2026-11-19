import pytest
from core.security import (is_loopback_target, target_is_in_scope, validate_domain,
                           validate_port, validate_safe_name, verify_dns_txt_ownership)

def test_domain_normalization():
    assert validate_domain("Example.COM.") == "example.com"

@pytest.mark.parametrize("value", ["", "https://example.com", "bad_domain.com", "-bad.com", "localhost"])
def test_invalid_domains(value):
    with pytest.raises(ValueError):
        validate_domain(value)

def test_port_validation():
    assert validate_port("443") == 443
    for value in (0, 65536, "abc", True):
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
    assert target_is_in_scope("example.com", ownership_verified=True, authorization_confirmed=True)
    assert not target_is_in_scope("example.com", ownership_verified=True)

def test_dns_txt_verification_with_stub():
    class Answer:
        strings = [b"abcdefghijklmnop"]
    class Resolver:
        def resolve(self, name, record_type, lifetime):
            assert name == "_uncle-toolkit-verify.example.com"
            assert record_type == "TXT" and lifetime == 4.0
            return [Answer()]
    assert verify_dns_txt_ownership("example.com", "abcdefghijklmnop", resolver=Resolver())
