# APTron Observability — Customer Infrastructure Cost Planning

> APTron is open-source self-hosted software. **No APTron-billed infrastructure** is required. All amounts below are **fictional illustrative assumptions in INR**, not live prices, supplier quotes or purchase authorization.

## Worksheet method

| Category | On-prem customer | Customer-managed AWS / Azure / GCP / other cloud |
| --- | --- | --- |
| Compute | Hardware CAPEX / lifetime months | VM hourly × host count × monthly hours |
| Data | Disks, replacement and maintenance | Block storage GiB × rate |
| Backups | Separate media/storage and restores | Backup GiB × rate, restore egress |
| Networking | Internet/link/maintenance | Egress, load balancer, IPs and support |
| Energy | kWh × tariff | Reflected in supplier usage charges |
| Tax | Customer-specific | Customer-specific |

## Topology examples (NOT validated sizing)

| Scenario | Hosts | CPU / RAM per host | Classification |
| --- | ---: | --- | --- |
| Demo / lab | 1 | 4 vCPU / 16 GiB | Non-HA |
| Reference production HA | 3 | 16 vCPU / 64 GiB | Candidate; benchmarks pending |
| HA plus passive DR | 6 | 16 vCPU / 64 GiB | Two customer-operated independent sites |

Download the [example infrastructure assumption values (CSV)](./ASSUMED_INFRASTRUCTURE_VALUES.csv) for local editing. This CSV is intentionally generic and contains fictional values only.\n\nFor editable assumed values and cost formulas, use the companion internal planning workbook **APTron_SH_v1.0_Illustrative_Customer_Infrastructure_Cost_Assumptions.xlsx**; it is *not embedded in this public source repository*. Administrators may copy it into their own local cost model. Do not share confidential provider quotations or credentials through the application Help UI.

## Replace all sample numbers with real provider quotes

- [AWS Pricing Calculator](https://calculator.aws/)
- [Microsoft Azure Pricing Calculator](https://azure.microsoft.com/en-us/pricing/calculator/)
- [Google Cloud Pricing Calculator](https://cloud.google.com/products/calculator)

Use actual region, SKUs, discount, FX, taxes, data transfer, backup retention and monitoring requirements. APTron does not invoice cloud/on-prem cost or guarantee vendor pricing.
