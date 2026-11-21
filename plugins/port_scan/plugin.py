"""Bounded, read-only TCP connectivity checks for loopback only.

This plugin never resolves DNS names, scans remote hosts, sends application
payloads, or performs service/banner detection.
"""

from __future__ import annotations

import errno
import ipaddress
import math
import socket
import time
from typing import Any

from core.plugin_loader import BasePlugin


class Plugin(BasePlugin):
    MAX_PORTS = 16
    MIN_TIMEOUT = 0.1
    MAX_TIMEOUT = 1.0

    def get_metadata(self) -> dict[str, Any]:
        return {
            "name": "port_scan",
            "version": "1.0.0",
            "description": "Bounded TCP port checks for IPv4/IPv6 loopback only",
        }

    def validate(self) -> bool:
        return True

    @staticmethod
    def _parse_host(
        host: str,
    ) -> tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, int]:
        if not isinstance(host, str) or len(host) > 64:
            raise ValueError("Host must be a literal loopback IP address")
        try:
            address = ipaddress.ip_address(host)
        except ValueError as exc:
            raise ValueError("DNS names and non-IP targets are not supported") from exc
        # Accept only the two canonical loopback literals. In particular,
        # reject IPv4-mapped IPv6 forms such as ::ffff:127.0.0.1.
        if address not in {
            ipaddress.IPv4Address("127.0.0.1"),
            ipaddress.IPv6Address("::1"),
        }:
            raise ValueError("Only 127.0.0.1 and ::1 are allowed")
        family = socket.AF_INET6 if address.version == 6 else socket.AF_INET
        return address, family

    @classmethod
    def _validate_ports(cls, ports: list[int] | tuple[int, ...]) -> list[int]:
        if not isinstance(ports, (list, tuple)) or not ports:
            raise ValueError("Ports must be a non-empty list or tuple")
        if len(ports) > cls.MAX_PORTS:
            raise ValueError(f"No more than {cls.MAX_PORTS} ports may be checked")
        validated: list[int] = []
        for port in ports:
            if isinstance(port, bool) or not isinstance(port, int):
                raise ValueError("Each port must be an integer")
            if not 1 <= port <= 65535:
                raise ValueError("Ports must be between 1 and 65535")
            if port in validated:
                raise ValueError("Duplicate ports are not supported")
            validated.append(port)
        return validated

    @staticmethod
    def _check_one(
        address: ipaddress.IPv4Address | ipaddress.IPv6Address,
        family: int,
        port: int,
        timeout: float,
    ) -> tuple[str, str | None, float]:
        started = time.monotonic()
        sockaddr: tuple[Any, ...]
        if family == socket.AF_INET6:
            sockaddr = (address.compressed, port, 0, 0)
        else:
            sockaddr = (address.compressed, port)

        sock = None
        try:
            sock = socket.socket(family, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex(sockaddr)
        except (OSError, TimeoutError) as exc:
            code = getattr(exc, "errno", None)
            if code in {errno.ECONNREFUSED, getattr(errno, "WSAECONNREFUSED", -1)}:
                status, error = "closed", None
            elif isinstance(exc, TimeoutError) or code in {
                errno.ETIMEDOUT,
                getattr(errno, "WSAETIMEDOUT", -1),
            }:
                status, error = "filtered", "timeout"
            else:
                status, error = "unknown", type(exc).__name__
        else:
            if result == 0:
                status, error = "open", None
            elif result in {errno.ECONNREFUSED, getattr(errno, "WSAECONNREFUSED", -1)}:
                status, error = "closed", None
            elif result in {errno.ETIMEDOUT, getattr(errno, "WSAETIMEDOUT", -1)}:
                status, error = "filtered", "timeout"
            else:
                status, error = "unknown", f"socket_error_{result}"
        finally:
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
        elapsed_ms = round((time.monotonic() - started) * 1000, 2)
        return status, error, elapsed_ms

    def run(
        self,
        host: str = "127.0.0.1",
        ports: list[int] | tuple[int, ...] = (80, 443),
        timeout: float = 0.5,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if kwargs:
            raise ValueError("Unsupported options")
        address, family = self._parse_host(host)
        validated_ports = self._validate_ports(ports)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise ValueError("Timeout must be a number")
        timeout_value = float(timeout)
        if not math.isfinite(timeout_value) or not self.MIN_TIMEOUT <= timeout_value <= self.MAX_TIMEOUT:
            raise ValueError("Timeout must be between 0.1 and 1.0 seconds")

        started = time.monotonic()
        results = []
        for port in validated_ports:
            status, error, elapsed_ms = self._check_one(
                address, family, port, timeout_value
            )
            results.append(
                {
                    "port": port,
                    "protocol": "tcp",
                    "status": status,
                    "response_time_ms": elapsed_ms,
                    "error": error,
                }
            )

        summary = {
            state: sum(1 for item in results if item["status"] == state)
            for state in ("open", "closed", "filtered", "unknown")
        }
        result = {
            "plugin": "port_scan",
            "version": "1.0.0",
            "target": address.compressed,
            "scope": "loopback_only",
            "results": results,
            "summary": summary,
            "total_time_ms": round((time.monotonic() - started) * 1000, 2),
        }
        return result
