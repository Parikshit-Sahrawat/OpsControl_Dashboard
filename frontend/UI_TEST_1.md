# UI Test 1 — monitoring workspace redesign

Branch: `feature/ui-test-1`. Base: main `02a9c25684ee9e7b267aaa3ecc2209aa7dea27bd`.

The redesign introduces obsidian dark and paper/slate light themes, persistent appearance controls, a responsive navigation sidebar, asymmetric Overview cards, consistent engineering typography, semantic status washes, refined data tables and investigation surfaces. Values and histories remain backed by the existing monitoring APIs. There are no invented chart traces, health values or operational counters.

## Scope and current instructions

Keep fetching, API payloads, monitoring calculations, tenant selection, alert transitions and existing application state architecture intact. Theme state is appearance-only. `opscontrol.theme` stores a validated `dark` or `light` preference. Before an explicit choice, appearance follows the browser color scheme. Theme changes update the root attribute immediately, synchronize across tabs and tolerate denied preference storage. The initial document applies the preference before first paint; a deployed strict frontend CSP must allow that bootstrap with its hash/nonce.

The user subsequently authorized backend and supporting-code adjustments required by the frontend. The only application-backend change here enables **PUT** in CORS alongside existing methods: existing frontend update requests already use PUT. Allowed origins and bearer/tenant checks are preserved. The security probe now asserts allowed PUT/PATCH and rejects unapproved origins and TRACE. No API endpoint, query or collector logic is changed.

Supporting acceptance changes run the new frontend browser script inside the existing disposable monitoring lab and its CI workflow. Navigation regression tests close modal investigations before using the workspace behind them. The new appearance checks exercise real password authentication, all eight primary tabs plus platform access, both themes, keyboard controls, reload persistence, system preferences, denied preference storage, status contrast, reduced motion and mobile layouts.

## Development and acceptance

From the repository root:

```bash
npm ci --prefix frontend --no-audit --no-fund
npm run build --prefix frontend
OPERATIONAL_EVIDENCE_DIR=/tmp/opscontrol-ui-evidence \
  backend/.venv/bin/python scripts/ui-acceptance.py
```

The acceptance wrapper uses the existing Python environment, Docker/OpenSSL and Playwright configuration documented in the operational lab. Ports 11432, 18800, 15174 and private-interface 443 must be free. It owns and cleans its disposable services and generates private synthetic credentials. Set `PLAYWRIGHT_MODULE` and `PLAYWRIGHT_CHROMIUM_EXECUTABLE` when using separately installed Playwright/system Chromium. The wrapper defaults to `/workspace/.golden-tools/node_modules/playwright/index.mjs` and available `/usr/bin/chromium` through the operational runner.

Theme PNGs and the redacted result ledger are emitted under `${OPERATIONAL_EVIDENCE_DIR}/ui-test-1/`; the surrounding directory contains the real HTTPS/ETL/incident regression evidence. GitHub's operational acceptance job includes the theme gate and uploads the complete artifact. The ledger distinguishes actual runtime/browser checks from source review.

## Review gate

Show actual dark/light browser screenshots and obtain the user's approval **after those samples are shown** before merging. Earlier permission to make supporting backend changes does not itself approve unseen final styling. Production release acceptance remains separate from this UI approval. The independent main audit identifies existing backend trust-boundary, concurrency, load and recovery work; this visual branch does not certify those defects as repaired.
