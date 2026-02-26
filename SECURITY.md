# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please email the maintainer or create a private security advisory on GitHub.

## Recent Security Updates

### Resolved Vulnerabilities (February 2026)

#### Python Dependencies

| Package                | Version  | CVE(s)                                      | Severity | Status          |
| ---------------------- | -------- | ------------------------------------------- | -------- | --------------- |
| opencv-python-headless | 4.8.1.78 | Multiple CVEs (see below)                   | High     | Fixed (4.13.0+) |
| flask-cors             | 4.0.2    | CVE-2024-6866, CVE-2024-6844, CVE-2024-6839 | High     | Fixed (6.0.0+)  |
| gunicorn               | 21.2.0   | CVE-2024-1135, CVE-2024-6827                | High     | Fixed (22.0.0)  |

**OpenCV Vulnerabilities Fixed:**

- CVE-2023-4863: Bundled libwebp binaries vulnerability (High)
- Multiple Out-of-bounds Write vulnerabilities (High)
- Multiple Out-of-bounds Read vulnerabilities (High/Moderate)
- NULL Pointer Dereference (High)
- Divide By Zero (Moderate)

**Actions Taken:**

- Updated `opencv-python-headless` from 4.8.1 to 4.13.0
- Updated `Flask-CORS` from 4.0.x to 6.0.x (fixes CVE-2024-6866, CVE-2024-6844, CVE-2024-6839)
- Enabled strict, environment-driven CORS configuration (disabled by default, explicit origin allowlist)
- Updated `gunicorn` from version 21.2 to 22.0

#### Node.js Dependencies

| Package     | Version | Vulnerability               | Severity | Status          |
| ----------- | ------- | --------------------------- | -------- | --------------- |
| markdown-it | 13.0.0  | GHSA-38c4-r59v-3vqw (ReDoS) | Moderate | Fixed (14.1.0+) |

**Actions Taken:**

- Updated `markdownlint-cli2` from 0.20.0 to 0.21.0 (which uses markdown-it 14.1.0+)

### Known Issues

#### Development Dependencies (Acceptable Risk)

| Package | Version | Vulnerability               | Severity | Risk Assessment |
| ------- | ------- | --------------------------- | -------- | --------------- |
| ajv     | 6.12.6  | GHSA-2g4f-4pwh-qvx6 (ReDoS) | Moderate | Low             |

**Details:**

- **Vulnerability:** Regular Expression Denial of Service (ReDoS) when using `$data` option
- **Affected Component:** `ajv` version < 8.18.0, used by `eslint` (dev dependency)
- **CVSS Score:** 0 (no score assigned)
- **Exploitation Requirements:**
  - Only affects ESLint during development/linting
  - Requires specific `$data` option to be enabled
  - Not present in production code or dependencies
- **Mitigation:**
  - This is a development-only dependency used for code linting
  - The vulnerability cannot be exploited in production
  - ESLint does not use the `$data` option in our configuration
  - Updating to ajv 8.x would break ESLint compatibility
- **Timeline:** Will be resolved when ESLint updates its dependencies to ajv 8.x

**Why This Is Acceptable:**

1. **Scope:** Development dependencies only, not shipped to production
2. **Exploitability:** Low - requires specific configuration not used in this project
3. **Impact:** Limited to development environment performance
4. **Trade-off:** Breaking ESLint functionality is a worse outcome than accepting this minimal risk

## Security Best Practices

When contributing to this project:

1. **Dependencies:** Regularly check for updates to dependencies
2. **Auditing:** Run `npm audit` and `.venv/bin/pip-audit` before committing
3. **Virtual Environment:** Always use the Python virtual environment (`.venv/`)
4. **Review:** Review all dependency updates for breaking changes

## Automated Security Checks

- **GitHub Dependabot:** Automatically monitors dependencies for vulnerabilities
- **CI/CD:** Linting and testing run on all pull requests
- **Regular Reviews:** Security advisories are reviewed monthly
