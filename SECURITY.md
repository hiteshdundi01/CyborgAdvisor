# Security Policy

## Supported Versions

The following versions of the **Cyborg Advisor** are currently supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of our users' financial data extremely seriously. The **Cyborg Advisor** is designed with a "Security-First" architecture, including mandatory role-based access control (RBAC), immutable audit logs, and deterministic validation gates.

### How to Report

If you discover a security vulnerability, please **DO NOT** open a public issue. Instead, please report it via encrypted email to:

**security@cyborgadvisor.ai**

Please include:
1. A description of the vulnerability.
2. Steps to reproduce the issue.
3. The potential impact (e.g., unauthorized trade execution, PII leakage).
4. Any proof-of-concept code (optional but helpful).

### Our Response Process

1. **Acknowledgment:** We will acknowledge receipt of your report within 24 hours.
2. **Triaging:** Our security team will investigate the issue and determine its severity.
3. **Fix:** If a vulnerability is confirmed, we will work to patch it immediately.
4. **Disclosure:** Once the patch is released, we will coordinate a responsible disclosure with you.

### Scope

The following areas are in scope for bug bounties (if active) and security reports:
*   **Authentication & Authorization:** Bypassing RBAC or KYA agent identity verification.
*   **Data Privacy:** Unauthorized access to PII or financial data.
*   **Deterministic Integrity:** Exploits that allow bypassing the "Math Ban" or validation gates to inject malicious logic.
*   **Saga Transaction Integrity:** Methods to force the system into an inconsistent state (e.g., cash settled but trade not executed).

### Out of Scope

*   DDoS attacks or other denial of service scenarios.
*   Social engineering attacks against our employees.
*   Vulnerabilities in third-party libraries (unless actionable via configuration).

## Security Architecture

The Cyborg Advisor employs a defense-in-depth strategy:

1.  **Identity:** All agents use cryptographically verifiable Decentralized Identifiers (DIDs).
2.  **Access Control:** Strict Role-Based Access Control (RBAC) enforces least privilege.
3.  **Audit:** An immutable, append-only audit log records every action and reasoning trace.
4.  **Isolation:** The "System 2" deterministic layer is isolated from the probabilistic LLM layer.
5.  **Validation:** Input sanitization and output validation gates prevent injection attacks.
