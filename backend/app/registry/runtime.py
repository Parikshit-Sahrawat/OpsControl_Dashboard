"""Scheduled platform collection with transactionally persisted cursor state."""

import asyncio, hashlib, json
from copy import deepcopy
from datetime import datetime, timezone
from sqlalchemy import select
from app.pipeline_adapters import PLATFORM_ADAPTERS, AdapterError
from app.pipeline_adapters.core import redact_provider_record
from app.registry.models import CollectorRuntimeState


async def collect_pipeline(db, collector, data_source):
    from app.worker.collector_runtime import CollectionResult

    configuration = collector.configuration or {}
    platform = configuration.get("platform")
    state = db.get(CollectorRuntimeState, collector.id)
    checkpoint = deepcopy(state.checkpoint) if state else {}
    # Scope failures must stop before any provider read or checkpoint disclosure.
    if state and state.organization_id != data_source.organization_id:
        return CollectionResult(
            False,
            "Platform collection failed: AUTHORIZATION",
            {
                "outcome": "CONFIGURATION_ERROR",
                "provider": platform,
                "inventory_complete": False,
            },
        )
    try:
        adapter = PLATFORM_ADAPTERS[platform](
            configuration["integration_configuration"]
        )
        batch = await asyncio.to_thread(adapter.collect_with_retry, checkpoint)
        if (
            not isinstance(batch.checkpoint, dict)
            or len(json.dumps(batch.checkpoint, default=str)) > 65536
            or len(batch.events) > 10000
        ):
            raise AdapterError(
                "SCHEMA", "Provider checkpoint or batch exceeds bounded limits"
            )
        observed = datetime.now(timezone.utc).isoformat()
        records = []
        for fact in batch.events:
            if not isinstance(fact, dict) or not isinstance(fact.get("event"), dict):
                raise AdapterError("SCHEMA", "Normalized execution event required")
            if (
                not isinstance(fact.get("key"), str)
                or not fact["key"]
                or len(fact["key"]) > 500
            ):
                raise AdapterError("SCHEMA", "Normalized execution identity required")
            original = dict(fact["event"])
            is_step = str(original.get("event_type", "")).startswith("STEP")
            actual_jobchain = original.get("jobchain")
            original["provider_jobchain"] = actual_jobchain
            original["jobchain"] = configuration["jobchain"]
            original["provider_evidence"] = redact_provider_record(
                fact.get("evidence", {})
            )
            record = {
                **fact,
                "event": original,
                "evidence": redact_provider_record(fact.get("evidence", {})),
            }
            records.append(record)
            # Expand genuine provider summaries without fabricating start/end.
            if original.get("started_at") and original.get("event_type") not in {
                "START",
                "STEP_START",
            }:
                records.append(
                    {
                        **record,
                        "key": fact["key"] + ":start",
                        "observed_at": original["started_at"],
                        "event": {
                            **original,
                            "event_type": "STEP_START" if is_step else "START",
                            "status": "RUNNING",
                            "timestamp": original["started_at"],
                            "ended_at": None,
                            "terminal_status_observed": False,
                            "timestamp_provenance": "SOURCE",
                        },
                    }
                )
            if original.get("status") == "RUNNING" and not str(
                original.get("event_type", "")
            ).startswith("STEP"):
                snapshot = {
                    **original,
                    "event_type": "STATUS",
                    "timestamp": observed,
                    "observed_provider_status": True,
                    "timestamp_provenance": "RECEIVED_OBSERVATION",
                }
                records.append(
                    {
                        **record,
                        "key": fact["key"]
                        + ":observed:"
                        + hashlib.sha256(observed.encode()).hexdigest()[:20],
                        "observed_at": observed,
                        "event": snapshot,
                    }
                )
        if (
            len(records) > 20000
            or len(json.dumps(records, default=str)) > 8 * 1024 * 1024
        ):
            raise AdapterError(
                "SCHEMA", "Expanded provider evidence exceeds bounded limits"
            )
        if state is None:
            state = CollectorRuntimeState(
                collector_id=collector.id,
                organization_id=data_source.organization_id,
                checkpoint={},
                revision=0,
            )
            db.add(state)
        if state.organization_id != data_source.organization_id:
            raise AdapterError("AUTHORIZATION", "Provider cursor scope mismatch")
        state.checkpoint = batch.checkpoint
        state.revision += 1
        state.last_error = None
        return CollectionResult(
            True,
            "Actual read-only " + platform + " provider evidence",
            {
                "outcome": "SUCCESS",
                "provider": platform,
                "inventory_complete": batch.complete,
                "record_count": len(batch.events),
                "resource_id": configuration.get("resource_id"),
                "execution_records": records,
                "provider_evidence": redact_provider_record(batch.evidence),
            },
        )
    except AdapterError as error:
        if state:
            state.last_error = error.kind
        return CollectionResult(
            False,
            "Platform collection failed: " + error.kind,
            {
                "outcome": (
                    "CONFIGURATION_ERROR"
                    if error.kind
                    in {
                        "CONFIGURATION",
                        "AUTHENTICATION",
                        "AUTHORIZATION",
                        "TLS",
                        "DEPENDENCY_UNAVAILABLE",
                    }
                    else "PROVIDER_ERROR"
                ),
                "provider": platform,
                "inventory_complete": False,
            },
        )
    except Exception:
        if state:
            state.last_error = "RUNTIME_ERROR"
        return CollectionResult(
            False,
            "Platform collection failed safely",
            {
                "outcome": "PROVIDER_ERROR",
                "provider": platform,
                "inventory_complete": False,
            },
        )
