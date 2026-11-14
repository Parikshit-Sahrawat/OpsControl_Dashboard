# APTron Observability — Self-Hosted Learning & Training

> Educational content for customer-operated deployments. Any single-host demonstration is **not HA**, and a tabletop recovery discussion is **not DR certification**.

This curriculum includes planned capabilities. Confirm support in the installed version before attempting any lab. This foundation slice does not implement or certify native Collector replacement, SOS/JS7 connectors, Synthetic Monitoring or RUM.

## Learning path

1. **Basics — 60 min:** Learn the APTron software/customer infrastructure responsibility boundary; compare on-premises, customer AWS/Azure/GCP and private clouds.
2. **Operations — 90 min:** Review resource tenancy, synthetic Windows/Linux host signals, process/service state, stale-metric gaps and restart markers.
3. **Job/API/Synthetic/RUM — 120 min:** Explore read-only SOS JobScheduler 1.x / JS7 job evidence, API checks, Synthetic journeys and privacy/consent-aware RUM with fabricated data.
4. **Deployment & resilience — 120 min:** Compare Linux Compose single-host and candidate 3-host HA, backup verification, upgrades/rollback and Option D/A DR patterns.
5. **Security — 120 min:** Understand tenant RBAC, mTLS, authenticated receipt classes CL-1/2/3, audit, user consent and key custody; never use production keys in a lab.
6. **Cost & compliance — 60 min:** Practice with fictitious rates in the [Cost Planning](./COST_PLANNING.md) worksheet method and review the [Deployment Guide](./DEPLOYMENT_GUIDE.md).

## Industry security alignment

APTron targets application requirements from **OWASP ASVS 5.0**, risk governance outcomes in **NIST CSF 2.0**, and defensive guidance in **CIS Controls v8.1**. ISO/IEC 27001:2022 is a possible control mapping, not a claim that APTron or customer deployments are certified.

- OWASP ASVS: https://asvs.owasp.org/
- NIST CSF: https://www.nist.gov/cyberframework
- CIS v8.1: https://www.cisecurity.org/controls/v8-1

## Product/customer separation

APTron owns secure software features, accurate documentation, updates, bug fixes, SBOM/license notices and released software test evidence. Customers decide and administer legal obligations, hosting, accounts, identities, network, keys, backup and recovery operations. Neither side's responsibilities eliminate the other's.
