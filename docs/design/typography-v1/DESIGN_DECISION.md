# Design decision — proposed / pending owner approval

## Observed baseline

TYPOGRAPHY_AUDIT.json inventories384 literal CSS/inline declarations with exact source paths, lines and offsets, including shorthand and dynamic inline expressions. This is a source inventory, not an AST/cascade proof for every runtime state. There are no bundled font binaries or source font-loading declarations in the inspected frontend. styles.css declares Inter; later/global/component rules also specify system stacks and distinct monospace stacks. A declared family is not proof that it renders.

The actual React/Vite login observation renders **Noto Sans Bold/Regular** on this Linux Chromium environment, with no loaded FontFace or font link. Its computed body stack starts `-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif`, body14px. Therefore the initial styles.css Inter declaration is not the only cascade authority. Windows/macOS fallback may differ; those platforms are NOT TESTED here. Screenshot font identity cannot be inferred reliably from appearance alone.

Inconsistencies include hard-coded9/10/11/12px labels mixed with13/15/20/26/28/30px, multiple body/monospace stacks, mixed heading weights and uppercase tracking, variable line heights and page-local overrides. Resource-v2 and inline React styles contribute beyond styles.css. Very small dense metadata, unbounded hostnames and synthetic bold fallback need deliberate review. The accepted Resource Management layout remains accepted; typography changes are a new decision.

## Candidate comparison

| Candidate | Strengths to review | Trade-offs / limits |
|---|---|---|
|Inter|Neutral, familiar UI rhythm; variable optical size/weight; strong compact interface baseline|Less distinctive than Plex; no evidence it is currently shipped/loaded; exact optical-size and numeric settings must be controlled|
|IBM Plex Sans + Plex Mono|Distinctive enterprise character; coherent sans/technical family; readable identifiers and tabular values in the specimen|Different word widths and texture may alter density; owner review needed at1366px; use normal width axis, no unapproved condensed mode|
|Source Sans3|Professional Adobe Source family; open body/table appearance; variable weights|A separate technical font is still needed; owner must compare layout rhythm and compact navigation labels|

These are design judgements, not objective user-study scores. All three actual candidate fonts render as custom platform fonts in Chromium; RESULTS.json retains actual names. IBM Plex Sans is a **recommendation**, not the owner's selection.

## Proposed roles

Default browser root size remains user-controlled; use rem for roles. Body15px, control/label14px, metadata13px, card17px, section20px, page28px, KPI32px at a16px root. Weight400 body,500 labels/navigation,600 headings/KPI. Line heights1.5 body,1.2 headings,1.6 technical. Heading tracking−.015em only; no global all-caps/tracking. Tables14px, header13px/600; long IDs13px mono. Proposed lower bounds are design defaults, not new product-authority requirements or universal accessibility guarantees.

Apply tabular numerals to KPI values, durations, counters, timestamps and comparable table columns. Do not monospace all prose. Preserve raw IDs and evidence; use semantic code/pre with safe bidi isolation where appropriate. Keep existing navigation hierarchy/routes; the same navigation role applies to the approved single-panel Feature Directory, not a new navigation layout.

## Loading, licences and performance

Official unmodified files are pinned to Google Fonts source commit5bb28733cec313b63fbd415b574b5ae35c8aa8b8. All four source families include exact SIL OFL1.1 texts and copyright in the recorded files. Retain licence/copyright with redistribution, respect Reserved Font Names and font-software resale restrictions; review the exact OFL and modifications before shipping. No font files were renamed internally or modified. CSS aliases do not constitute a new licensed font asset. No independent legal signature is claimed.

Prototype uses full variable TTFs: Inter876,576B; Plex Sans537,244B; Source Sans3646,340B; Plex Mono135,580B. These are **prototype bytes, not a production WOFF2 budget**. On approval, create/recover reviewed WOFF2 builds with hashes and licence notices; limit to selected family/weights, immutable same-origin asset paths, `font-display:swap`, matching fallback metrics and carefully scoped preload. Avoid runtime third-party font CDNs. Do not preload every weight or all candidates. Record actual transfer, cold/warm loading and CLS on the real app before rollout; local specimen CLS is not production performance certification.

Linux fallback observations for the sample corpus include Noto CJK/Devanagari and DejaVu Sans Mono. Those are OS fonts, not bundled product assets. Required scripts/locales, fallback packaging and Windows/macOS rendering remain owner/platform decisions. Missing glyphs or platform font availability must never become assumed multilingual support.

## Validation limits

24 desktop/theme/font cases plus8 CSS-zoom cases passed;8 exact token contrast pairs meet4.5:1; three numeric-width cases show equal tabular advances; keyboard candidate/theme and table focus checks pass. Font loading is verified by CDP actual platform-font records, not merely computed font-family strings. No page errors or external runtime requests were observed.

Native browser100/125/150/200% zoom is BLOCKED: both attempts to start the isolated Chromium extension worker timed out. Failed logs/results are retained. No timeout increase or artificial PASS. CSS zoom tests and screenshots are explicitly emulation; native Chrome/Firefox/Edge, Windows and macOS, comprehensive accessibility and all product routes require further execution before a production-wide typography change.

Owner decisions: TYP-01 family pairing; TYP-02 exact scale/density; TYP-03 WOFF2/fallback and required scripts; TYP-04 platform/native-zoom acceptance and rollout scope. All PENDING.
