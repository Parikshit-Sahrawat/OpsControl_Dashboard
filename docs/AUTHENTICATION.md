# Authentication, roles and tenant isolation — review-branch implementation

**Status:** Security work in draft PR #17. Do not treat it as production-approved until CI, security review and release gates pass.

## Local first run

Install backend dependencies, start PostgreSQL and apply migrations as shown in [Quickstart](QUICKSTART.md). Create the first platform administrator **interactively** from `backend/`:

```bash
python -m scripts.create_admin --username admin
```

The command prompts twice for a strong password and refuses to run if a platform administrator already exists. Do **not** put credentials in the shell command, a committed config, GitHub Actions logs, or sample data. Then run the API and UI normally. Open the UI and sign in as that administrator.

Existing upgraded databases are **not** automatically provisioned with a default account. This is intentional, to avoid publicly known default credentials.

## Roles

| Role | Read organizations/resources | Modify monitoring configuration | Create organizations/users | Investigations |
|---|---|---|---|---|
| Platform administrator | All | All | Yes | Yes |
| Organization administrator | Assigned organizations | Assigned organizations only | No | Yes |
| Operator | Assigned organizations | No | No | Selected investigation transitions/notes (pending full verification) |
| Viewer | Assigned organizations | No | No | Read-only |

For now, membership and user creation is restricted to platform administrators through `POST /api/v1/auth/users` and `POST /api/v1/auth/memberships`. Use a secure API client with the admin's bearer token; inspect request schemas at `/docs`. No public sign-up is available.

The organization selector is only a UI preference. The API derives permitted organizations from database-backed memberships on **each request**. Unauthenticated resource access returns 401, and inaccessible tenant resources are filtered or return 404. Reassigning owner IDs through ordinary PATCH is forbidden. The system also verifies cross-entity ownership during writes.

## Session policy

- `POST /api/v1/auth/login` takes username and password and returns an opaque random bearer token valid for 12 hours.
- Store only the SHA-256 digest in the database; logout deletes the session.
- Frontend stores the token in browser **sessionStorage** (tab-scoped), not persistent localStorage. HTTPS, XSS protections, rate limiting, session rotation and audit logging still need release hardening.
- `GET /api/v1/auth/me` returns the logged-in username, platform role and currently active memberships.
- `POST /api/v1/auth/logout` invalidates the session.

## Security limitations / future gates

- **Do not expose publicly yet.** Login brute-force rate limiting, organization-user lifecycle UI, explicit worker service identities, audit logs, security headers, provider integration secret handling and manual threat-model review remain needed.
- Background worker sessions are intentionally separate from HTTP user sessions. No user credentials should be supplied to workers; worker authorization and scoped remote-agent protocols are a separate security milestone.
- The ORM read filter is defense for legacy API queries; direct SQL bypasses it. Prohibit raw SQL endpoints and audit new routers before release; database RLS may add defense in depth.
- Built-in demo seed contains environment-shaped examples and should not be used for public demos.
- **Test gate:** run `python scripts/auth_tenant_probe.py` from `backend/` against an isolated migrated test DB and local running API. It asserts anonymous rejection, tenant-scoped listings, direct-ID read/write denial, forged org creation denial and allowed reads/writes. The GitHub Actions staging workflow also exercises an authenticated browser session.
