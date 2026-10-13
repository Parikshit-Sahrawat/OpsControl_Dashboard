"""Bounded normalized execution facts; ambiguous identifiers stay unresolved."""

import hashlib, json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import regex
from app.unified.schemas import LogParser


class NormalizationError(ValueError):
    pass


def timestamp(value, parser):
    if not value:
        raise NormalizationError("MISSING_SOURCE_TIMESTAMP")
    try:
        if parser.timestamp_format in {"epoch_millis", "epoch_seconds"}:
            return datetime.fromtimestamp(
                float(value)
                / (1000 if parser.timestamp_format == "epoch_millis" else 1),
                timezone.utc,
            )
        result = (
            datetime.strptime(str(value), parser.timestamp_format)
            if parser.timestamp_format
            else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        )
        if result.tzinfo is None:
            local = result.replace(tzinfo=ZoneInfo(parser.timezone), fold=0)
            if (
                local.astimezone(timezone.utc)
                .astimezone(ZoneInfo(parser.timezone))
                .replace(tzinfo=None)
                != result
            ):
                raise ValueError()
            result = local
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        raise NormalizationError("INVALID_SOURCE_TIMESTAMP") from None


def lookup(data, path):
    value = data
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def normalize(message, configuration, observed_at, jobchain):
    parser = LogParser.model_validate(configuration)
    try:
        if isinstance(message, dict):
            raw = message
        elif parser.format == "JSON":
            raw = json.loads(message)
        else:
            match = regex.search(parser.pattern, message, timeout=0.05)
            if not match:
                raise NormalizationError("PARSER_NOT_MATCHED")
            raw = match.groupdict()
    except TimeoutError:
        raise NormalizationError("PARSER_TIMEOUT") from None
    except (json.JSONDecodeError, TypeError, RecursionError):
        raise NormalizationError("INVALID_EXECUTION_DOCUMENT") from None
    if not isinstance(raw, dict):
        raise NormalizationError("EXECUTION_OBJECT_REQUIRED")
    data = {
        key: lookup(raw, parser.field_mapping.get(key, key))
        for key in (
            "execution_id",
            "order_id",
            "jobchain",
            "event_type",
            "status",
            "step_id",
            "step_name",
            "attempt",
            "timestamp",
            "duration_seconds",
            "error",
            "execution_type",
            "scheduled_at",
            "started_at",
            "ended_at",
        )
    }
    if data["jobchain"] and str(data["jobchain"]) != jobchain:
        raise NormalizationError("OTHER_JOBCHAIN")
    identity = data["order_id"] or data["execution_id"]
    if (
        not identity
        and "scheduled_at" in parser.execution_identity_fields
        and data["scheduled_at"]
    ):
        identity = (
            "internal:"
            + hashlib.sha256(
                (jobchain + "|" + str(data["scheduled_at"])).encode()
            ).hexdigest()[:40]
        )
    if not identity:
        raise NormalizationError("EXECUTION_IDENTITY_REQUIRED")
    if len(str(identity)) > 200:
        raise NormalizationError("EXECUTION_IDENTITY_TOO_LONG")
    source_status = str(data["status"] or "").upper()
    status = parser.status_mapping.get(source_status, "UNKNOWN")
    raw_type = str(data["event_type"] or raw.get("event") or "").upper()
    event_type = parser.event_mapping.get(raw_type, raw_type)
    if event_type not in {
        "START",
        "END",
        "STEP_START",
        "STEP_END",
        "STEP_FAILED",
        "STATUS",
    }:
        event_type = (
            "STEP_END"
            if data["step_name"] and status in {"SUCCESS", "FAILED"}
            else (
                "STEP_START"
                if data["step_name"]
                else (
                    "START"
                    if status == "RUNNING"
                    else "END" if status in {"SUCCESS", "FAILED"} else "STATUS"
                )
            )
        )
    instant = timestamp(data["timestamp"], parser) if data["timestamp"] else observed_at
    try:
        attempt = int(data["attempt"] or 1)
    except (ValueError, TypeError):
        raise NormalizationError("INVALID_ATTEMPT") from None
    if not 1 <= attempt <= 10000:
        raise NormalizationError("INVALID_ATTEMPT")
    step_id = str(data["step_id"] or data["step_name"] or "")[:200]
    if event_type.startswith("STEP") and not step_id:
        raise NormalizationError("STEP_IDENTITY_REQUIRED")
    event = {
        "execution_id": str(identity),
        "native_order_id": str(data["order_id"]) if data["order_id"] else None,
        "jobchain": jobchain,
        "event_type": event_type,
        "status": status,
        "timestamp": instant.isoformat(),
        "step_id": step_id,
        "step_name": str(data["step_name"] or step_id)[:200],
        "attempt": attempt,
        "error": str(data["error"])[:2000] if data["error"] else None,
        "execution_type": (
            parser.execution_type_mapping.get(
                str(data["execution_type"]).upper(), parser.default_execution_type
            )
            if data["execution_type"] is None
            or str(data["execution_type"]).upper() in parser.execution_type_mapping
            else None
        ),
        "scheduled_at": data["scheduled_at"],
        "started_at": (
            timestamp(data["started_at"], parser).isoformat()
            if data.get("started_at")
            else None
        ),
        "ended_at": (
            timestamp(data["ended_at"], parser).isoformat()
            if data.get("ended_at")
            else None
        ),
        "source_status": source_status,
    }
    if event["execution_type"] is None:
        raise NormalizationError("UNMAPPED_EXECUTION_TYPE")
    return event, instant
