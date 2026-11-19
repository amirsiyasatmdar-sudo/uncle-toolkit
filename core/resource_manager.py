"""Lightweight, advisory resource controls."""
from __future__ import annotations
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
import threading
import time
from typing import Iterator

@dataclass(frozen=True)
class ResourceProfile:
    name: str
    max_workers: int
    memory_limit_mb: int
    requests_per_minute: int

PROFILES = {
    "low": ResourceProfile("low", 1, 50, 30),
    "normal": ResourceProfile("normal", 2, 150, 120),
}

class RateLimitExceeded(RuntimeError):
    """Raised when an operation exceeds its configured request rate."""

class ResourceManager:
    """Thread-safe concurrency and per-key sliding-window rate limiter."""
    def __init__(self, profile: str = "low") -> None:
        try:
            self.profile = PROFILES[profile]
        except KeyError as exc:
            raise ValueError(f"Unknown resource profile: {profile}") from exc
        self._semaphore = threading.BoundedSemaphore(self.profile.max_workers)
        self._lock = threading.Lock()
        self._requests: dict[str, deque[float]] = {}

    @contextmanager
    def operation(self, *, timeout: float | None = None) -> Iterator[None]:
        acquired = (self._semaphore.acquire() if timeout is None
                    else self._semaphore.acquire(timeout=timeout))
        if not acquired:
            raise TimeoutError("Could not acquire a worker slot")
        try:
            yield
        finally:
            self._semaphore.release()

    def check_rate_limit(self, key: str = "global") -> None:
        if not isinstance(key, str) or not key or len(key) > 128:
            raise ValueError("Rate-limit key must be 1-128 characters")
        now = time.monotonic()
        with self._lock:
            history = self._requests.setdefault(key, deque())
            while history and history[0] <= now - 60:
                history.popleft()
            if len(history) >= self.profile.requests_per_minute:
                raise RateLimitExceeded(f"Rate limit exceeded for {key!r}")
            history.append(now)

    def memory_usage_mb(self) -> float | None:
        """Return process RSS if optional psutil is installed."""
        try:
            import psutil
        except ImportError:
            return None
        try:
            return psutil.Process().memory_info().rss / (1024 * 1024)
        except (OSError, RuntimeError):
            return None

    def memory_budget_exceeded(self) -> bool | None:
        usage = self.memory_usage_mb()
        return None if usage is None else usage > self.profile.memory_limit_mb
