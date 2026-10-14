# ARCH-001 V1.5 local verification evidence

These reports and Playwright screenshots come from actual controlled local tests on October 14, 2026. Runtime uses Agent 1.5 and digest-pinned Contrib 0.123.0 with verified TLS. `verification.json` records the aggregate gate result. Coverage is scoped to named critical modules, not the whole repository. Provider fixtures do not certify genuine provider connectivity; native Windows and privileged target-host installation remain separately gated. All fixture credentials and raw server diagnostics remain outside Git.

Reproduce with `make test-all` after the prerequisites in [Testing V1.5](../../TESTING_V15.md). See [the implementation ledger](../../../ARCH-001_IMPLEMENTATION_STATUS.md) for acceptance limits.
