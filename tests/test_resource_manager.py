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


def test_operation_rejects_invalid_timeouts():
    manager = ResourceManager("low")

    for value in (-0.1, "invalid", True, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            with manager.operation(timeout=value):
                pass


def test_rate_limit_removes_expired_keys(monkeypatch):
    import core.resource_manager as resource_module

    current_time = [100.0]
    monkeypatch.setattr(
        resource_module.time,
        "monotonic",
        lambda: current_time[0],
    )

    manager = ResourceManager("low")
    manager.check_rate_limit("old-key")

    assert "old-key" in manager._requests

    current_time[0] += 61
    manager.check_rate_limit("new-key")

    assert "old-key" not in manager._requests
    assert "new-key" in manager._requests


def test_rate_limit_expires_request_at_exact_60_second_boundary(
    monkeypatch,
):
    import core.resource_manager as resource_module

    current_time = [100.0]
    monkeypatch.setattr(
        resource_module.time,
        "monotonic",
        lambda: current_time[0],
    )

    manager = ResourceManager("low")
    manager.profile = manager.profile.__class__("low", 1, 50, 1)

    manager.check_rate_limit("boundary")
    current_time[0] = 160.0

    # A request exactly 60 seconds old is expired.
    manager.check_rate_limit("boundary")


def test_rate_limit_is_thread_safe():
    import threading

    manager = ResourceManager("low")
    manager.profile = manager.profile.__class__("low", 1, 50, 5)

    barrier = threading.Barrier(20)
    results = []
    results_lock = threading.Lock()

    def worker():
        barrier.wait()
        try:
            manager.check_rate_limit("shared")
            result = True
        except RateLimitExceeded:
            result = False

        with results_lock:
            results.append(result)

    threads = [
        threading.Thread(target=worker)
        for _ in range(20)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert sum(results) == 5
    assert len(results) == 20


def test_operation_rejects_unrepresentable_timeout():
    manager = ResourceManager("low")

    with pytest.raises(ValueError):
        with manager.operation(timeout=10**10000):
            pass


def test_operation_raises_timeout_when_worker_slot_unavailable():
    manager = ResourceManager("low")

    with manager.operation():
        with pytest.raises(TimeoutError):
            with manager.operation(timeout=0):
                pass


@pytest.mark.parametrize("key", [None, 123, "", "a" * 129])
def test_rate_limit_rejects_invalid_keys(key):
    manager = ResourceManager("low")

    with pytest.raises(ValueError, match="Rate-limit key"):
        manager.check_rate_limit(key)


def test_memory_usage_returns_none_when_psutil_is_missing(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def blocked_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "psutil":
            raise ImportError("simulated missing psutil")

        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked_import)

    assert ResourceManager("low").memory_usage_mb() is None


def test_memory_usage_returns_rss_in_megabytes(monkeypatch):
    import sys
    from types import SimpleNamespace

    fake_psutil = SimpleNamespace(
        Process=lambda: SimpleNamespace(
            memory_info=lambda: SimpleNamespace(rss=2 * 1024 * 1024)
        )
    )

    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    assert ResourceManager("low").memory_usage_mb() == 2.0


@pytest.mark.parametrize("error", [OSError("simulated OS error"), RuntimeError("simulated runtime error")])
def test_memory_usage_returns_none_on_process_errors(monkeypatch, error):
    import sys
    from types import SimpleNamespace

    class FakeProcess:
        def memory_info(self):
            raise error

    fake_psutil = SimpleNamespace(Process=FakeProcess)

    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    assert ResourceManager("low").memory_usage_mb() is None


@pytest.mark.parametrize(
    ("usage", "expected"),
    [
        (None, None),
        (49.0, False),
        (50.0, False),
        (51.0, True),
    ],
)
def test_memory_budget_exceeded(usage, expected, monkeypatch):
    manager = ResourceManager("low")
    monkeypatch.setattr(manager, "memory_usage_mb", lambda: usage)

    assert manager.memory_budget_exceeded() is expected
