# Phase 3 — Port Scan installation and testing

Extract the archive at the repository root, then run:

```bash
cd ~/uncle-toolkit
unzip -o ~/storage/downloads/uncle-toolkit-phase3-port-scan.zip -d ~/uncle-toolkit
python -m pytest -q
python -m compileall -q core plugins tests
python -m core.cli plugins --directory plugins
```

Expected new plugin entry: `port_scan 1.0.0`.

This plugin is deliberately restricted to literal IPv4/IPv6 loopback
addresses, at most 16 TCP ports per call, and a 0.1–1.0 second timeout.
It does not perform DNS resolution, remote scans, service detection, or
application-level requests.

Do not commit or push until the review and explicit approval are complete.
