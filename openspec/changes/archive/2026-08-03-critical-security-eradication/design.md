## Context

The application interacts with external services to fetch metadata and images (e.g., from BoardGameGeek or MusicBrainz). These features are susceptible to two major vulnerabilities:

1. **Server-Side Request Forgery (SSRF)**: If an attacker can control the URL being fetched, they can force the server to make requests to internal services (localhost, AWS metadata endpoint `169.254.169.254`, or RFC 1918 private IPs), leading to data exfiltration or deeper network compromise.
2. **XML External Entity (XXE) DoS**: The application currently uses `xml.etree.ElementTree` to parse XML responses. This parser is vulnerable to XXE attacks (like the "Billion Laughs" attack), which can cause Denial of Service by consuming excessive memory/CPU.

## Goals / Non-Goals

**Goals:**

- Create a secure HTTP client wrapper for fetching external resources that actively blocks requests to private, loopback, and metadata IP addresses.
- Replace all instances of `xml.etree.ElementTree` with the safe `defusedxml.ElementTree` equivalent.

**Non-Goals:**

- Completely rewriting the external API integrations (only wrapping their HTTP calls and swapping their XML parsers).
- Implementing a full-fledged outbound proxy. We will solve SSRF at the application level using a Python-based wrapper.

## Decisions

### 1. SSRF Prevention Mechanism

- **Decision**: Implement a custom Python HTTP client wrapper (`app.utils.http_client` or similar) that resolves the hostname to an IP address *before* making the request, and verifies the IP is not in a restricted range (e.g., `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.169.254`).
- **Rationale**: This is the most reliable way to prevent SSRF in Python applications without relying on external infrastructure (like a proxy). It prevents DNS rebinding attacks if implemented correctly (resolve, check, and fetch using the resolved IP and original Host header).

### 2. XXE Prevention Mechanism

- **Decision**: Use the `defusedxml` package.
- **Rationale**: `defusedxml` is the Python standard recommendation for mitigating XML vulnerabilities. It acts as a drop-in replacement for standard library XML parsers, minimizing code changes while maximizing security.

## Risks / Trade-offs

- [Risk] **DNS resolution changes between check and fetch (DNS Rebinding)** → Mitigation: The secure client must resolve the IP, validate it, and then make the HTTP request directly to that IP address while passing the original hostname in the `Host` header.
- [Risk] **Legitimate local network requests fail** → Mitigation: If the application legitimately needs to contact other internal services, the wrapper should support an explicit, tight whitelist of allowed internal hosts (though ideally, external fetches use one client, internal fetches use another).
- [Risk] **Missing `defusedxml` dependency** → Mitigation: Ensure `defusedxml` is added to `requirements.txt` and/or `pyproject.toml`.
