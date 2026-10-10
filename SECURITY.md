# OpsControl Security Policy

OpsControl is an independent open-source monitoring project under active development.

## Supported security status

The security hardening in [draft PR #19](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/19) is **not a production security certification**. Until independently reviewed and merged, deploy only to a trusted isolated development environment with **fictional sources and credentials**.

Never expose the API, worker port, React development server, PostgreSQL or internal monitoring sources to an untrusted/public network solely on the basis of passing CI.

## Vulnerability reporting

Avoid posting live credentials, exploits involving real infrastructure, private targets or customer information in public GitHub issues. Use the repository's private GitHub vulnerability reporting feature if available. If that feature is not enabled, arrange a private communication channel with the repository maintainer before sharing sensitive evidence. Do not assume a public issue is confidential.

## Security boundaries

- Human sessions: 12-hour random bearer tokens (only SHA-256 digest retained), authenticated per request. No default public admin account. Interactive bootstrap only.
- Identity lifecycle: administrators may disable users, reset passwords and change/revoke organization memberships, invalidating sessions.
- Organization isolation: server-side memberships and ORM tenant predicate; the frontend organization selector is a preference, not access control.
- Worker identity: separate organization-scoped, expiring, revocable token; worker `whoami` validates scope but **no remote task dispatch is authorized or implemented**.
- Audit: security events record actor/action/outcome and bounded resource identifiers, not request bodies/tokens/passwords. Admin read-only endpoint; protect DB permissions and backups separately.
- Login throttling: PostgreSQL-backed username/client-address limits; ensure your reverse proxy passes client identity only via a trusted ingress. Do not trust arbitrary `X-Forwarded-For` headers.
- Deployment: use properly configured TLS and trusted proxy headers, explicit HTTPS browser-origin allowlist and protected PostgreSQL credentials.
- Configuration: reject embedded password/token/key JSON fields, use opaque `*_ref` identifiers; legacy configs are redacted on API output but **existing stored values require remediation and rotation before production**.
- Monitoring connectivity: collecting private URLs safely requires a separately approved outbound-only agent, secret provider, bounded egress and SSRF mitigations. Proposed architecture is not a finished capability.

## Release gate

The [security review checklist](docs/SECURITY_RELEASE_CHECKLIST.md) distinguishes automated evidence from deployment and third-party review. A green static scan/CI run is not permission to expose the application or close release blockers. 
