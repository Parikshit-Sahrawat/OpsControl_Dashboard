"""Native read-only HTTP and cloud execution adapters; target acceptance is separate."""

import asyncio, hashlib, json, socket, ssl
from datetime import datetime, timezone
from app.unified.transport import request
from app.unified.normalization import normalize, NormalizationError, lookup
from app.worker.egress import EgressDenied


class NativeAPIAdapter:
    async def collect(self, collector):
        from app.worker.collector_runtime import CollectionResult

        configuration = collector.configuration or {}

        try:
            evidence, _ = await asyncio.to_thread(
                request, configuration["url"], configuration
            )
            return CollectionResult(
                evidence["outcome"] == "SUCCESS",
                "Actual native endpoint observation",
                evidence,
            )
        except ssl.SSLCertVerificationError:
            return CollectionResult(
                False,
                "Native TLS trust verification failed",
                {"outcome": "CONFIGURATION_ERROR"},
            )
        except (socket.timeout, TimeoutError):
            return CollectionResult(
                False,
                "Native probe timeout",
                {"outcome": "TIMEOUT", "probe_location": "NATIVE_BACKEND"},
            )
        except (ValueError, KeyError, RuntimeError):
            return CollectionResult(
                False,
                "Native probe configuration/authentication reference is unavailable",
                {"outcome": "CONFIGURATION_ERROR"},
            )
        except EgressDenied:
            return CollectionResult(
                False,
                "Native probe destination is not approved",
                {"outcome": "CONFIGURATION_ERROR"},
            )
        except Exception:
            return CollectionResult(
                False,
                "Native endpoint transport unavailable",
                {"outcome": "NETWORK_ERROR", "probe_location": "NATIVE_BACKEND"},
            )


class IICSAdapter:
    async def collect(self, collector):
        from app.worker.collector_runtime import CollectionResult

        configuration = collector.configuration or {}

        try:
            evidence, body = await asyncio.to_thread(
                request, configuration["url"], configuration, True
            )
            records = lookup(body, configuration.get("records_field", "records"))
            if not isinstance(records, list) or len(records) > 1000:
                raise ValueError("Invalid provider execution inventory")
            parser = configuration["parser"]
            jobchain = configuration["jobchain"]
            events = []
            unresolved = 0
            for record in records:
                # Adapters accept the configured provider mapping; unknown
                # status codes are not guessed to mean success/failure.
                try:
                    event, instant = normalize(
                        record, parser, datetime.now(timezone.utc), jobchain
                    )
                except NormalizationError as error:
                    if str(error) != "OTHER_JOBCHAIN":
                        unresolved += 1
                    continue
                facts = []
                if event.get("started_at"):
                    facts.append(
                        {
                            **event,
                            "event_type": "START",
                            "status": "RUNNING",
                            "source_status": "RUNNING",
                            "timestamp": event["started_at"],
                            "ended_at": None,
                            "error": None,
                        }
                    )
                if event.get("ended_at"):
                    facts.append(
                        {**event, "event_type": "END", "timestamp": event["ended_at"]}
                    )
                if facts and event["status"] == "RUNNING":
                    facts.append(
                        {
                            **event,
                            "event_type": "STATUS",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "observed_provider_status": True,
                        }
                    )
                if not facts:
                    if not record.get("timestamp") and not lookup(
                        record,
                        parser.get("field_mapping", {}).get("timestamp", "timestamp"),
                    ):
                        unresolved += 1
                        continue
                    facts = [event]
                for fact in facts:
                    events.append(
                        {
                            "event": fact,
                            "observed_at": fact["timestamp"],
                            "key": "metadata:"
                            + hashlib.sha256(
                                json.dumps(fact, sort_keys=True).encode()
                            ).hexdigest(),
                        }
                    )
            return CollectionResult(
                True,
                "Read-only cloud execution inventory received",
                {
                    **evidence,
                    "provider": configuration.get("platform", "IICS"),
                    "inventory_complete": unresolved == 0
                    and not any(
                        body.get(key)
                        for key in ("hasMore", "nextPageToken", "next_url")
                    ),
                    "record_count": len(records),
                    "execution_records": events,
                    "unresolved_record_count": unresolved,
                },
            )
        except EgressDenied:
            return CollectionResult(
                False,
                "Cloud execution destination is not approved",
                {
                    "outcome": "CONFIGURATION_ERROR",
                    "provider": configuration.get("platform", "IICS"),
                },
            )
        except Exception:
            return CollectionResult(
                False,
                "Cloud execution metadata is unavailable or incompatible",
                {
                    "outcome": "PROVIDER_ERROR",
                    "provider": configuration.get("platform", "IICS"),
                    "inventory_complete": False,
                },
            )
