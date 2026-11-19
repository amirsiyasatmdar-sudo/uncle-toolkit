# Web Check Plugin — Phase 3

## Scope
`web_check` is deliberately local-only in version 1.0.0. It accepts only literal
loopback IP addresses (`127.0.0.1` or `::1`). DNS names, public IPs, proxy
environment variables, and automatic redirect following are disabled.

External-domain support is deferred until a separately reviewed design can pin
resolved addresses and enforce ownership plus explicit authorization without
SSRF or DNS-rebinding gaps. DNS TXT proof alone is not legal authorization.

## Install
Extract this archive into the repository root so `plugins/web_check/`,
`tests/test_web_check.py`, and this document are placed in the existing project.

## Run
```bash
python -m pytest -q
python -m core.cli plugins --directory plugins
```

## Behavior
- Sends one bounded GET request to a loopback service.
- Timeout is mandatory and limited to 0.2–10 seconds.
- Does not follow redirects; reports the `Location` header only.
- Ignores proxy environment variables.
- For HTTPS, performs standard certificate verification and reports expiry
  information when the peer certificate is available.
- Does not execute JavaScript, submit forms, modify data, or send telemetry.

## Limitations
The plugin checks response headers and a verified TLS handshake. It does not
perform a vulnerability scan, crawl pages, inspect application content, or
prove that a web application is secure.
