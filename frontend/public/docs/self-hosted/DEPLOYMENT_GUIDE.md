# APTron Observability — Self-Hosted Deployment Guide (design reference)

> This is **customer-operated** software. APTron does not host customer instances or bill cloud infrastructure. This is a guidance draft in the legacy OpsControl repository, **not** a declaration that the final APTron deployment is implemented, certified, or released.

## Supported deployment choices

- **On-premises Linux**: customer-owned servers, networking, power, persistent disks, backups, DNS, certificates, and operations.
- **Private cloud / virtualization**: customer-operated Linux VMs with documented failure domains and storage.
- **AWS, Azure, Google Cloud or other providers**: optional customer-controlled accounts/subscriptions/projects; select Linux VMs, isolated networks, storage, backup destinations, and load balancers according to supported configurations.
- No vendor is mandatory or preferred. APTron needs no access to customer cloud billing credentials.

## Reference architecture

- The initial application packaging direction is Docker Compose on Linux. Monitored hosts may include Windows and Linux.
- **One-host** examples are suitable for training or development and must be labeled **non-HA**.
- The reviewed production **candidate** is **3 independent hosts, 16 vCPU / 64 GiB each**, with PostgreSQL/Patroni, 3-member etcd, authenticated ingress and safe fencing. No capacity or reliability certification is implied.
- Disaster recovery options: **D — independent passive site feasibility first**, and **A — clean immutable backup/rebuild cyber comparator**. The customer owns any actual DR site and runs its exercises.

## Operator responsibilities

The customer provisions hosts, networks, storage, IAM/IdP, PKI/KMS/HSM, secrets, backup and restore, patching, monitoring policy and supplier contracts. APTron provides supported software, validated configuration templates, secure defaults, documentation, audit functions and software/security fixes.

## Important safety notes

- Do not place real production/customer credentials into training examples.
- Product installation does not establish compliance with a customer's law or contracts.
- Current design/release gates for HA, Collector CL-1/2/3 durability, security and recovery remain open pending test evidence.
- For costs, use [Infrastructure Cost Planning](./COST_PLANNING.md); amounts are not APTron subscriptions.
- For labs, use [Learning & Training](./TRAINING_GUIDE.md).
