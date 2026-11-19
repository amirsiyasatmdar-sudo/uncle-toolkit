import pytest
from core.resource_manager import RateLimitExceeded, ResourceManager

def test_low_profile_limits():
    manager = ResourceManager("low")
    assert manager.profile.max_workers == 1
    assert manager.profile.memory_limit_mb == 50

def test_unknown_profile_rejected():
    with pytest.raises(ValueError):
        ResourceManager("turbo")

def test_rate_limit_per_key():
    manager = ResourceManager("low")
    manager.profile = manager.profile.__class__("low", 1, 50, 2)
    manager.check_rate_limit("a")
    manager.check_rate_limit("a")
    with pytest.raises(RateLimitExceeded):
        manager.check_rate_limit("a")
    manager.check_rate_limit("b")

def test_operation_releases_slot():
    manager = ResourceManager("low")
    with manager.operation(timeout=0.1):
        pass
    with manager.operation(timeout=0.1):
        pass

def test_operation_without_timeout():
    manager = ResourceManager("low")
    with manager.operation():
        pass
