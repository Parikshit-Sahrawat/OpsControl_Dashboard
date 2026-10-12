# [PRODUCT_NAME] End-User License Agreement and Terms of Service

Effective date: [EFFECTIVE_DATE]  
Provider: [COMPANY_NAME], organized under the laws of [COMPANY_JURISDICTION], with its principal address at [COMPANY_ADDRESS]  
Contract notices: [CONTACT_EMAIL]

**Execution status.** This is a complete agreement template for customization and legal review. It becomes the Provider's binding agreement only through the acceptance mechanism below and an authorized commercial release. A development deployment, marketing image, or unsigned template does not establish a hosted production SLA, a subscription, certification, or acceptance of unimplemented functionality.

## 1. Parties, acceptance, and documents

This Agreement is between [COMPANY_NAME] (the “Provider”) and the legal entity identified in an accepted Order Form or authorized business-account registration (the “Customer”). A person accepting for an entity represents that the person has authority to bind that entity. An individual without that authority may not accept on its behalf. Authorized Users access the Service through Customer and do not receive an independent ownership interest.

An Order Form becomes effective when executed by authorized representatives or accepted through an expressly identified electronic contracting process that makes this Agreement available before acceptance and records affirmative assent. Browsewrap access alone is not the intended acceptance method. The Order Form must identify the purchased deployment, subscription term, fees, support plan, hosting region where relevant, capacity, retention, and any negotiated terms.

The Agreement consists of the Order Form, these Terms, the applicable Software license provisions, the Data Processing Addendum (“DPA”), the SLA where applicable, and expressly incorporated schedules. The mandatory Standard Contractual Clauses prevail for their regulated subject matter. Otherwise, the DPA controls personal-data processing conflicts; a signed negotiated Order Form controls other conflicts; these Terms control standard documentation and marketing materials. A purchase-order form does not amend this Agreement unless Provider expressly signs the amendment.

## 2. Definitions

“Service” means the hosted [PRODUCT_NAME] components expressly purchased in an Order Form. “Software” means Provider software supplied for Customer installation under that Order Form, including an approved agent or customer-hosted deployment. “Documentation” means the applicable published operating documentation for the purchased version. “Customer Data” means information submitted, collected, or stored on Customer's behalf, including telemetry, logs, resource metadata, configurations, and investigation content. “Authorized User” means a person Customer authorizes within its purchased entitlement. “Usage Limits” means the objective limits in the Order Form and applicable technical specifications. “Subscription Term” means the purchased period. “Preview” means a trial, beta, experimental, development, or expressly non-production offering. “Confidential Information” is defined in Section 11. “Personal Data” has the meaning applicable under the DPA.

## 3. Hosted access and Software license

Subject to this Agreement and payment of undisputed fees, Provider grants Customer a non-exclusive, non-transferable right during the Subscription Term to access and use the purchased Service through its Authorized Users for Customer's internal business operations, including monitoring systems Customer is legally authorized to monitor. Customer may allow its contractors to act for Customer within the purchased entitlement and remains responsible for them. Affiliate rights exist only if the Order Form identifies the covered Affiliates.

For purchased Software, Provider grants Customer a non-exclusive license to install and execute the approved Software in the number and type of environments specified in the Order Form, and to make reasonable backup copies. The license lasts for the term stated in the Order Form. Source-code rights, perpetual rights, redistribution, OEM embedding, and transfer to an Affiliate or successor are included only if expressly granted. If the Order Form grants a perpetual paid-up license, expiration of support does not revoke that license; hosted access and subscription-only features still expire as agreed.

Except to the extent applicable law prohibits the restriction or an applicable open-source license permits the activity, Customer shall not distribute Provider's proprietary Software to third parties, remove proprietary notices, circumvent entitlement or security controls, or reverse engineer it to obtain protected source code or trade secrets. These restrictions do not prohibit legally protected interoperability, security research conducted under an authorized policy, or exercising applicable open-source rights.

Open-source and third-party components remain governed by their applicable licenses and notices. This Agreement does not convert those components into Provider-owned proprietary material, override permissive or copyleft rights, or establish rights Provider has not obtained. Provider must maintain the required notices and fulfill applicable source-disclosure obligations before distribution. Customer retains rights independently granted by those licenses.

## 4. Customer responsibilities and acceptable use

Customer shall maintain account security, assign appropriate roles and organization memberships, protect service credentials, review destination allowlists, obtain target-owner authorization, and ensure a lawful basis for Customer Data processing. Customer shall configure collection and retention to minimize unnecessary personal and sensitive data. Customer shall not submit credentials as telemetry, use the Service to monitor systems without permission, or knowingly collect data that infringes third-party rights.

Customer shall not use the Service to distribute malware, conduct denial-of-service attacks, evade network restrictions, exfiltrate data, conduct unlawful surveillance, attempt cross-tenant access, impersonate another customer, or materially interfere with Service integrity. Customer shall not intentionally bypass Usage Limits, replay conflicting measurements, forge health evidence, or present synthetic observations as genuine production measurements.

Unless the parties sign an appropriate regulated-use addendum, Customer shall not submit payment-card authentication data, medical records requiring a health-data processing agreement, classified information, or other data whose processing requires protections not included in the purchased Service. Ordinary infrastructure identifiers and appropriately minimized operational personal data may be processed under the DPA. This paragraph does not transfer Provider's independent privacy obligations to Customer.

## 5. Technical scope, API limits, and changes

Provider shall describe the purchased functionality and material restrictions in the Order Form and Documentation. Monitoring results depend on authorized collectors, configurations, network access, accepted evidence, and external systems. Unknown or missing evidence is not a representation that a target is healthy. A worker heartbeat is not a target-health assertion. Sampled success reports are not a continuous uptime guarantee. Roadmap statements and illustrative marketing assets are not purchased features unless expressly incorporated.

The Order Form shall specify [INGESTION_REQUESTS_PER_MINUTE], [INGESTION_EVENTS_PER_DAY], [MAX_CONCURRENT_WORKERS], [CONTRACTED_STORAGE_GB], purchased retention, and any burst policy. These limits must be operationally validated and enforced before Provider sells the corresponding capacity. The current worker protocol separately requires valid assigned leased jobs, JSON requests, and a maximum 8 KiB request body; this limit is not a general OTLP batch quota. No generic ingestion SDK is included unless expressly supplied and identified.

Provider may throttle, queue, or reject requests exceeding agreed or documented limits and shall provide appropriate error information where technically practicable. Where HTTP 429 and Retry-After apply, Customer shall honor the retry instruction with bounded backoff. Provider shall not impose undisclosed retrospective usage charges or require unlimited retries. Temporary protective limits may be applied proportionately to an active security or availability threat; Provider shall notify Customer where feasible and work to restore normal service.

Provider shall not materially reduce purchased functionality during a paid Subscription Term without an agreed remedy. Material API deprecations shall have at least ninety days' notice where reasonably practicable. Urgent security changes may take effect sooner with prompt notice and migration guidance. Customer-hosted versions and agents must follow the supported compatibility matrix; Provider need not support an indefinitely outdated or modified deployment unless expressly contracted.

## 6. Availability, support, and external systems

The 99.9% monthly availability commitment in Schedule A applies only to an accepted production hosted Service expressly covered by the Order Form. It does not apply to Preview, local Docker demonstrations, customer-hosted uptime, monitored target uptime, or third-party incident-delivery availability. Contracted latency objectives, if any, must be separately stated with their measurement method and workload assumptions; none arise merely from the term “real-time.”

Provider shall supply the support plan purchased in the Order Form. Priority-one support response target is [P1_RESPONSE_TIME]; other priorities and business hours are [SUPPORT_SCHEDULE]. A response target is not a guaranteed resolution time. The parties shall maintain emergency contacts and reasonable escalation procedures.

Third-party integrations require Customer-authorized accounts and provider permissions. Provider shall protect credentials and validate supported integration responses as required by the DPA and security schedule. Provider does not warrant a third party's continued API availability or compatibility, but shall use commercially reasonable efforts to maintain expressly supported integrations. Provider's own hosting subcontractors remain its responsibility under this Agreement and are not treated as unrelated customer-selected third parties.

## 7. Subscription, fees, billing, and taxes

The Subscription Term, fees, currency, billing frequency, committed capacity, and any usage charges are stated in the Order Form. Unless the Order Form provides otherwise, undisputed invoices are payable within thirty days of receipt. Provider shall give an itemized basis for measurable overage charges. Overage rates require agreement before the relevant usage is charged.

Customer shall notify Provider of a good-faith invoice dispute within thirty days after receipt, describe the disputed amount and reason, and pay the undisputed portion when due. The parties shall promptly investigate. Provider shall not suspend service solely for a disputed amount while Customer cooperates in good faith. Late charges on overdue undisputed amounts shall not exceed the lesser of one percent per month or the maximum lawful rate, following written notice.

Fees exclude applicable transaction taxes, which Customer shall pay except taxes on Provider's net income, employment, or property. Provider shall accept valid exemption documentation. Required withholding shall be handled under applicable law, with lawful receipts and cooperation; any gross-up obligation must be expressly specified in the Order Form.

A subscription renews automatically only if the Order Form expressly states the renewal term and cancellation mechanism. Otherwise it expires at the stated end date. For agreed automatic renewal, either party may give non-renewal notice at least thirty days before expiration. Provider shall disclose any renewal price change at least sixty days before renewal. In-term price changes require written agreement except pre-agreed measured overage charges.

## 8. Ownership and permitted data use

Customer retains ownership and applicable rights in Customer Data, Customer marks, and Customer-owned configurations and content. Customer grants Provider the limited right to process Customer Data only to provide, secure, support, and maintain the purchased Service, comply with documented instructions, and meet applicable law. Personal Data processing is governed by the DPA. Provider shall not sell Customer Data, use it for unrelated advertising, or train a general-purpose model on it without a separate explicit written agreement and a lawful basis.

Provider retains ownership of its independently developed platform, Documentation, service methods, and improvements, subject to applicable third-party and open-source rights. No assignment of Customer's intellectual property arises merely because it is processed in the Service. Provider may use genuinely deidentified or aggregated operational information for service planning only if it cannot reasonably identify Customer or an individual, is not reidentified, and does not reveal Customer Confidential Information. A contractual label alone does not make identifiable information anonymous.

Customer may provide voluntary feedback. Provider may use that feedback without payment to improve its products, provided it does not disclose Customer Confidential Information or appropriate Customer Data. No transfer of a disclosed patent right arises without an express written license or assignment.

## 9. Security, privacy, and data processing

Provider shall implement the technical and organizational measures in the executed DPA/security schedule and maintain an appropriate security program. Provider shall notify and assist Customer with Personal Data breaches as required by the DPA. Provider shall not advertise a certification, independent audit, or compliance status unless the relevant scope and evidence have been verified.

The Privacy Policy governs Provider's independent processing of account, contact, website, and support information. The DPA governs processing of Customer Personal Data on Customer's behalf. Provider shall not use a change to a public Privacy Policy to expand the agreed processor purposes or override the DPA. Customer shall not disable security controls or share administrative credentials to obtain unsupported access.

## 10. Warranties and disclaimers

Each party warrants that it has authority to enter into this Agreement. Provider warrants that it has the rights necessary to grant the licenses it actually supplies, will perform professional services with reasonable skill and care, and will cause the purchased Service to perform materially in accordance with the applicable Documentation during the paid term. Customer shall promptly report a reproducible material nonconformity. Provider shall use commercially reasonable efforts to correct it. If Provider cannot correct a material nonconformity within thirty days after sufficient notice and cooperation, Customer may terminate the affected service and receive a prorated refund of prepaid unused fees.

Except for express warranties and mandatory rights that cannot lawfully be excluded, the Service and Software are provided without additional implied warranties, including implied merchantability, fitness for a particular purpose, or error-free operation. Monitoring is an operational aid and does not replace Customer's incident response, safety systems, backups, or independent decision-making. This disclaimer does not negate the express SLA, security obligations, or infringement indemnity.

Preview offerings are supplied for evaluation without a production availability commitment or a warranty of complete functionality. Preview conditions shall be identified clearly and do not waive mandatory privacy/security duties or justify negligent handling of Customer Data.

## 11. Confidentiality

“Confidential Information” means non-public information disclosed by one party to the other that is marked confidential or reasonably should be understood as confidential, including Customer Data, security findings, credentials, source code, business plans, pricing, and non-public technical information. Information is excluded to the extent the receiving party proves it was lawfully known without restriction, becomes public without breach, is independently developed without use of the disclosing party's information, or is lawfully received without confidentiality obligations.

The receiving party shall use Confidential Information only to perform or exercise rights under this Agreement, protect it using at least reasonable care, and disclose it only to personnel and authorized advisers who need it and are bound by appropriate confidentiality duties. Legally compelled disclosure is permitted after lawful advance notice where allowed and reasonable efforts to limit the disclosure. Neither party shall prevent protected legal reporting or impose an unlawful confidentiality restriction.

These obligations survive for five years after termination, except trade secrets remain protected while legally qualifying as trade secrets, and Personal Data/credentials remain protected for as long as retained. Return or deletion is subject to the DPA, lawful holds, and permitted inaccessible backup retention. Confidentiality does not authorize indefinite retention of unnecessary Personal Data.

## 12. Provider infringement indemnity

Provider shall defend Customer against a third-party claim that the purchased, unmodified Service or Software, used as authorized, infringes that third party's patent, copyright, trademark, or trade secret rights, and shall pay damages and reasonable settlement amounts finally awarded or approved by Provider. Customer shall promptly notify Provider, allow Provider to control the defense, and provide reasonable cooperation at Provider's expense. Delayed notice excuses responsibility only to the extent Provider is materially prejudiced.

Provider has no obligation to the extent a claim arises from Customer Data, an unauthorized Customer modification, a combination not supplied or reasonably contemplated by Provider when the claim would not otherwise arise, or use after Provider supplies a non-infringing replacement of materially equivalent function with reasonable migration assistance. Provider may obtain rights, modify or replace the affected component without material loss of contracted function, or, if those remedies are not commercially reasonable, terminate the affected component and refund prepaid unused fees. Provider may not settle a claim by admitting Customer fault or imposing a non-monetary obligation on Customer without its reasonable written consent.

## 13. Customer indemnity

Customer shall defend Provider against a third-party claim arising from Customer Data that Customer lacked the right or lawful authority to submit, or Customer's unlawful monitoring or intentional prohibited use, and shall pay damages and reasonable settlement amounts finally awarded or approved by Customer. Provider shall give prompt notice, allow Customer to control the defense, and reasonably cooperate at Customer's expense. Customer has no obligation for a claim to the extent caused by Provider's breach, unauthorized processing, negligence, or willful misconduct. Customer may not impose an admission or non-monetary obligation on Provider without its reasonable written consent.

## 14. Liability allocation

To the maximum extent permitted by applicable law, neither party is liable for indirect, special, exemplary, or consequential damages, or lost profits, arising from this Agreement. This exclusion does not prevent recovery of amounts payable to a third party under an express indemnity or reasonably foreseeable direct costs of investigation, notification, restoration, and mitigation of a covered confidentiality or Personal Data breach.

Each party's aggregate liability arising from the Agreement shall not exceed fees paid or payable for the affected services during the twelve months before the first event giving rise to the claim. The cap for breach of confidentiality or the DPA/security obligations, and express indemnification obligations, is twice that amount. Amounts properly owed by Customer for purchased services are payment obligations and are not reduced by this liability cap.

The exclusions and caps do not apply to fraud, willful misconduct, liability for death or personal injury caused by negligence where non-excludable, or any other liability that applicable law does not permit the parties to limit. Nothing limits a regulator's powers or an individual's mandatory privacy rights. Regulatory fines are reimbursable between the parties only to the extent lawfully transferable and attributable under applicable law; this Agreement does not purport to eliminate statutory accountability.

## 15. Suspension, termination, and data return

Provider may suspend affected access only to the extent reasonably necessary for an actual security threat, unlawful use, material interference, or overdue undisputed payment remaining uncured fifteen days after written notice. Where practicable, Provider shall notify Customer before suspension, identify the affected functions, permit remediation, and avoid unnecessary interruption of unaffected services. Protective suspension does not authorize destruction of Customer Data.

Either party may terminate for material breach not cured within thirty days after written notice identifying the breach. A breach that cannot reasonably be cured may justify immediate termination as permitted by law. Either party may terminate if the other enters insolvency proceedings to the extent applicable law permits. Customer may exercise the additional remedies in the warranty and SLA provisions.

At termination, subscription access and term-limited licenses end. Provider shall make Customer Data available through supported export or an agreed assisted export for thirty days, subject to lawful security restrictions and agreed reasonable assistance charges. Provider shall then return or delete Customer Personal Data as required by the DPA and verified retention schedule. Historical/audit categories lacking a compliant deletion mechanism must be remediated before Provider accepts that contractual obligation; Provider may not conceal such a limitation behind an unsigned policy. Customer-hosted data remains Customer's responsibility unless managed deletion is purchased.

If Customer terminates for Provider's uncured material breach or a stated SLA termination right, Provider shall refund prepaid unused affected-service fees. Customer shall pay earned undisputed fees through termination. Ownership, confidentiality, accrued payment, indemnity, liability, data-protection obligations while data remains held, and dispute provisions survive as their nature requires.

## 16. Export, sanctions, and legal compliance

Each party shall comply with export controls and sanctions applicable to its activities. Customer shall not knowingly provide access to a prohibited destination or person, or use the Service for a prohibited end use. Provider shall not require Customer to violate an applicable blocking statute or lawful local restriction; the parties shall address conflicts through a lawful contractual solution. Customer remains responsible for authorization to monitor its targets; Provider remains responsible for its own legal duties.

## 17. General terms

This Agreement is governed by [GOVERNING_LAW], excluding conflict-of-law rules, without limiting applicable mandatory law or the DPA transfer provisions. The courts located in [EXCLUSIVE_FORUM] have jurisdiction over disputes unless the Order Form includes a mutually agreed arbitration clause. Before litigation, senior representatives shall attempt good-faith resolution for thirty days; either party may seek urgent relief where permitted without waiting for that period.

Neither party is liable for delay caused by an event beyond its reasonable control if it promptly notifies the other, mitigates the effects, and resumes performance. Ordinary capacity shortages, avoidable security failures, or failure to maintain agreed continuity measures are not automatically force majeure. If the event materially prevents performance for thirty days, the affected party may terminate the affected service and receive a refund of prepaid unused fees.

Neither party may assign the Agreement without the other's reasonable consent, except to an Affiliate or in a merger, reorganization, or sale of substantially all relevant assets if the successor assumes the obligations and the transfer does not materially increase privacy/security risk. The assigning party shall give notice. A subprocessor appointment remains subject to the DPA and is not exempt because it is affiliated.

Notices shall be sent to the contract addresses in the Order Form and [CONTACT_EMAIL]. Material legal notices are effective on confirmed delivery or the next business day after documented electronic receipt; incidental support messages are not a substitute. A failure to enforce a clause is not a waiver. If a provision is unenforceable, the remainder survives to the extent lawful; this clause does not authorize rewriting an illegal restraint to obtain a prohibited result. The parties are independent contractors. This Agreement is the entire agreement for its subject matter. Amendments must be agreed in writing; a material online change does not retroactively alter a paid term without Customer consent.

## Schedule A. Production hosted-service SLA

### A1. Scope and commencement

The SLA applies to the production hosted control-plane components identified in the Order Form after [PRODUCTION_ACCEPTANCE_DATE]. Covered components are authenticated UI access, contracted API read/write operations, and valid assigned-worker result acceptance in [CONTRACTED_REGIONS]. Preview features, customer-hosted availability, third-party monitored targets, and customer-selected external notification endpoints are excluded. Provider shall deploy measurement, incident, and credit procedures before promising this SLA.

### A2. Availability calculation

Monthly Availability Percentage equals `100 × (Eligible Minutes − Unavailable Minutes) / Eligible Minutes`. Eligible Minutes are the calendar-month minutes during the covered paid service period minus valid excluded minutes. Unavailable Minutes are non-overlapping eligible one-minute intervals when the contracted core operation cannot be completed by a valid authorized request within thirty seconds because of a Provider-controlled failure, confirmed by monitoring or credible Customer evidence. Failure of a covered UI component is assessed according to the Order Form's component scope, not dismissed solely because a health endpoint responds.

Overlapping incidents count once. Provider shall not exclude its own hosting/cloud/CDN subcontractor outage simply because a third party supplied the infrastructure. Where multiple contracted regions or components have separate availability terms, the Order Form shall identify the weighting and affected fees before measurement begins. Monitoring coverage gaps shall not automatically be treated as available minutes.

### A3. Commitment and exclusions

Provider commits to Monthly Availability Percentage of at least **99.9%**. A thirty-day month has 43.2 minutes of unavailability allowance before applying valid exclusions; this illustration does not alter the formula.

Exclusions are Customer-caused configuration or credential failures, Customer-controlled infrastructure/network failures outside Provider's responsibility, unauthorized use directly causing the failure, an expressly applicable force-majeure event despite reasonable mitigation, and scheduled maintenance notified at least forty-eight hours in advance and limited to two hours per month. Maintenance exceeding that allowance counts unless Customer expressly agrees otherwise. Emergency security maintenance is excluded only to the extent genuinely necessary, promptly notified, and reasonably minimized; a routine defect correction is not automatically emergency maintenance.

### A4. Credits and claim process

If Monthly Availability is at least 99.0% but below 99.9%, the credit is ten percent of the affected monthly recurring hosted-service fee. If availability is at least 95.0% but below 99.0%, the credit is twenty-five percent. If availability is below 95.0%, the credit is fifty percent. Total availability credits for a month shall not exceed fifty percent of that affected monthly recurring fee. One-time fees, taxes, and unrelated components are excluded from the credit base.

Customer shall submit a claim to [SLA_CONTACT_EMAIL] within thirty days after the affected month, identifying the account, component, interval, and reasonably available evidence. Provider shall acknowledge and investigate within ten business days and provide its decision and calculation within thirty days after sufficient information is received. Provider shall not demand access to unrelated Customer data. Approved credits apply to the next invoice or are refunded if no further invoice is due. Timely credible evidence may establish downtime where Provider monitoring failed.

### A5. Repeated failure and remedies

Customer may terminate the affected hosted service if it fails the 99.9% commitment in three months within any rolling six-month period, by notice within thirty days after the third failure. Provider shall refund prepaid unused affected-service fees. Service credits are the monetary remedy for ordinary availability failures alone; they do not extinguish independent claims for breach of confidentiality, the DPA, indemnity, fraud, willful misconduct, or mandatory legal rights. Customer shall not receive duplicate compensation for the same loss.

## Schedule B. Order Form and signature record

Customer legal name: [CUSTOMER_LEGAL_NAME]  
Customer address: [CUSTOMER_ADDRESS]  
Purchased deployment and version: [DEPLOYMENT_AND_VERSION]  
Subscription start/end: [SUBSCRIPTION_START_DATE] / [SUBSCRIPTION_END_DATE]  
Production acceptance date: [PRODUCTION_ACCEPTANCE_DATE]  
Fees, currency, and billing: [FEES_CURRENCY_BILLING]  
Capacity, burst, region, and retention: [CAPACITY_REGION_RETENTION_SCHEDULE]  
Support schedule and emergency contacts: [SUPPORT_SCHEDULE_AND_CONTACTS]  
Renewal election: [RENEWAL_TERMS_OR_NO_AUTOMATIC_RENEWAL]  
Negotiated amendments: [NEGOTIATED_AMENDMENTS_OR_NONE]  
DPA and security schedule version: [DPA_SECURITY_VERSION]

For [COMPANY_NAME]: [AUTHORIZED_SIGNATORY_NAME], [TITLE], signature [SIGNATURE], date [SIGNATURE_DATE].

For Customer: [AUTHORIZED_SIGNATORY_NAME], [TITLE], signature [SIGNATURE], date [SIGNATURE_DATE].
