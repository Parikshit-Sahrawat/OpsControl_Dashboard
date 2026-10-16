"""Versioned monitoring declarations, not Pentaho executors or runtime proofs.

ARCH-ETL-001 V1.6 sections 4 and 11 govern these declarations. Actual method
eligibility remains in data_pipelines.service.eligible; catalogue data cannot
certify an installed build or authorize collection.
"""

# Retain prior catalogue candidates; new families are also unverified candidates.
PENTAHO_VERSION_CANDIDATES = ("8.3", "9.3", "9.4", "10.2.x", "11.0.x")


def describe_pentaho_monitoring_contract() -> dict:
    """Return fresh JSON-compatible declarations without any provider I/O."""
    return {
        "version": 1,
        "architecture": "ARCH-ETL-001 V1.6",
        "monitoring_only": True,
        "version_families_are_candidates_only": True,
        "runtime_verified": False,
        "certification_requires": [
            "EXACT_INSTALLED_BUILD",
            "GENUINE_NATIVE_EVIDENCE",
            "CURRENT_READER_AND_SOURCE_GENERATION",
            "INDEPENDENT_APPROVAL",
        ],
        "surfaces": [
            {
                "surface": "KITCHEN_PAN",
                "read_only": True,
                "implementation_status": "PROPOSED",
                "runtime_verified": False,
                "implemented_observations": [],
                "proposed_observations": [
                    "Native process invocation/start/exit and redacted logs",
                    "Verified external scheduler retry identity where available",
                ],
                "identity_requirements": [
                    "Customer and resource-bound Agent",
                    "Host identity, native invocation and process start epoch",
                    "Scheduler authority for retry grouping; PID alone is insufficient",
                ],
                "limitations": [
                    "No ETL command execution or control",
                    "Exit code alone cannot prove downstream or scheduler outcome",
                ],
            },
            {
                "surface": "PENTAHO_SERVER",
                "read_only": True,
                "implementation_status": "PROPOSED",
                "runtime_verified": False,
                "implemented_observations": [],
                "proposed_observations": [
                    "Authorized repository/scheduler/execution-history reads",
                ],
                "identity_requirements": [
                    "Customer, server/repository/environment and native execution ID",
                ],
                "limitations": [
                    "No universal API endpoints or version compatibility claimed",
                    "Scheduled trigger status is not verified ETL execution outcome",
                ],
            },
            {
                "surface": "CARTE",
                "read_only": True,
                "implementation_status": "PARTIAL",
                "runtime_verified": False,
                "implemented_observations": [
                    "Allowlisted TLS GET job inventory/status",
                    "Embedded job-entry results and opt-in sanitized logs",
                ],
                "proposed_observations": [
                    "Exact-build-verified transformation status",
                    "Server/restart-epoch-qualified execution identity",
                ],
                "identity_requirements": [
                    "Customer, server/restart epoch and verified native execution ID",
                ],
                "limitations": [
                    "Running-status inventory is not a persistent job catalogue",
                    "Current legacy job-status support does not certify this full contract",
                    "No start/stop/remove or other control endpoints",
                ],
            },
        ],
    }
