"""Actual OTLP/HTTP protobuf ingestion into existing logs and metrics plus spans."""

import zlib
import hashlib, json, math, uuid
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request, Response
from sqlalchemy import select
from google.protobuf.message import DecodeError
from google.protobuf.json_format import MessageToDict, ParseDict, ParseError
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
    ExportLogsServiceResponse,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
    ExportMetricsServiceResponse,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
)
from app.db.session import SessionLocal
from app.models import MetricDefinition, MetricSample, LogSource, LogEvent
from app.telemetry.models import TelemetryReceipt, TraceSpan
from app.telemetry.api import agent_router, authenticate, utc
from app.worker.alert_engine import evaluate_metric_sample

REQUESTS = {
    "logs": ExportLogsServiceRequest,
    "metrics": ExportMetricsServiceRequest,
    "traces": ExportTraceServiceRequest,
}
RESPONSES = {
    "logs": ExportLogsServiceResponse,
    "metrics": ExportMetricsServiceResponse,
    "traces": ExportTraceServiceResponse,
}


def timestamp(nanos):
    if not nanos:
        return utc()
    try:
        t = datetime.fromtimestamp(nanos / 1_000_000_000, timezone.utc)
    except (ValueError, OverflowError, OSError):
        raise HTTPException(422, "Invalid telemetry timestamp") from None
    if t > utc() + timedelta(minutes=5):
        raise HTTPException(422, "Future telemetry timestamp")
    return t


def value(v):
    kind = v.WhichOneof("value")
    if kind == "array_value":
        return [value(i) for i in v.array_value.values][:100]
    if kind == "kvlist_value":
        return attributes(v.kvlist_value.values)
    if kind == "bytes_value":
        return v.bytes_value.hex()
    return getattr(v, kind) if kind else None


def attributes(attrs):
    return {
        a.key[:200]: value(a.value)
        for a in list(attrs)[:100]
        if a.key not in ("organization_id", "customer_id", "agent_id")
    }


def name_key(name):
    return (
        name
        if len(name) <= 190
        else name[:150] + "-" + hashlib.sha256(name.encode()).hexdigest()[:32]
    )


@agent_router.post("/otlp/v1/{signal}")
async def ingest(signal: str, request: Request):
    if signal not in REQUESTS:
        raise HTTPException(404, "Unknown telemetry signal")
    from starlette.concurrency import run_in_threadpool

    await run_in_threadpool(authentication_gate, request)
    # Bound streaming input independently of client Content-Length.
    content = bytearray()
    async for part in request.stream():
        content.extend(part)
        if len(content) > 2 * 1024 * 1024:
            raise HTTPException(413, "Telemetry batch exceeds 2 MiB")
    encoding = request.headers.get("content-encoding", "identity")
    if encoding == "gzip":
        try:
            inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
            decoded = inflater.decompress(content, 2 * 1024 * 1024 + 1)
            if len(decoded) > 2 * 1024 * 1024 or inflater.unconsumed_tail:
                raise HTTPException(413, "Expanded telemetry batch exceeds limit")
            if not inflater.eof or inflater.unused_data:
                raise HTTPException(400, "Incomplete gzip telemetry")
            content = decoded
        except zlib.error:
            raise HTTPException(400, "Invalid gzip telemetry") from None
    elif encoding != "identity":
        raise HTTPException(415, "Unsupported telemetry encoding")
    obj = REQUESTS[signal]()
    content_type = request.headers.get("content-type", "").split(";")[0]
    try:
        if content_type == "application/x-protobuf":
            obj.ParseFromString(content)
        elif content_type == "application/json":
            ParseDict(json.loads(content), obj, ignore_unknown_fields=False)
        else:
            raise HTTPException(415, "OTLP protobuf or JSON required")
    except (DecodeError, ValueError, TypeError, ParseError, RecursionError):
        raise HTTPException(400, "Invalid OTLP envelope") from None
    # Sync DB and alert work runs off the ASGI event loop.
    from starlette.concurrency import run_in_threadpool

    await run_in_threadpool(
        store, obj, signal, request, hashlib.sha256(content).hexdigest()
    )
    reply = RESPONSES[signal]()
    if content_type == "application/json":
        return MessageToDict(reply)
    return Response(reply.SerializeToString(), media_type="application/x-protobuf")


def store(obj, signal, request, digest):
    with SessionLocal() as db:
        a, c, s, w = authenticate(db, request)
        if db.scalar(
            select(TelemetryReceipt.id).where(
                TelemetryReceipt.agent_id == a.id,
                TelemetryReceipt.signal == signal,
                TelemetryReceipt.payload_hash == digest,
            )
        ):
            return
        count = 0

        def increment():
            nonlocal count
            count += 1
            if count > 10000:
                raise HTTPException(413, "Telemetry batch exceeds 10000 records")

        if signal == "logs":
            source = db.scalar(
                select(LogSource).where(
                    LogSource.collector_id == c.id, LogSource.name == "OTLP host logs"
                )
            )
            if source is None:
                source = LogSource(
                    organization_id=a.organization_id,
                    data_source_id=s.id,
                    collector_id=c.id,
                    name="OTLP host logs",
                    source_type="OTLP",
                    resource_type="HOST",
                )
                db.add(source)
                db.flush()
            for resource in obj.resource_logs:
                for scope in resource.scope_logs:
                    for record in scope.log_records:
                        increment()
                        body = value(record.body)
                        message = (
                            body
                            if isinstance(body, str)
                            else json.dumps(body, ensure_ascii=False)
                        )
                        db.add(
                            LogEvent(
                                organization_id=a.organization_id,
                                log_source_id=source.id,
                                observed_at=timestamp(
                                    record.time_unix_nano
                                    or record.observed_time_unix_nano
                                ),
                                severity=record.severity_text[:30] or None,
                                message=message[:65536],
                                attributes={
                                    **attributes(resource.resource.attributes),
                                    **attributes(record.attributes),
                                },
                                event_type="OTLP",
                            )
                        )
        elif signal == "metrics":

            def sample(metric, point, v, suffix=""):
                increment()
                if not math.isfinite(float(v)):
                    raise HTTPException(422, "Non-finite metric value")
                series = attributes(point.attributes)
                resource_identity = {
                    key: value
                    for key, value in attributes(resource.resource.attributes).items()
                    if key.startswith(("service.", "host.", "deployment."))
                }
                if resource_identity:
                    series = {"resource": resource_identity, "point": series}
                name = name_key(
                    metric.name
                    + suffix
                    + (
                        " ["
                        + hashlib.sha256(
                            json.dumps(series, sort_keys=True).encode()
                        ).hexdigest()[:16]
                        + "]"
                        if series
                        else ""
                    )
                )
                utilization = (
                    suffix != ".count"
                    and metric.unit == "1"
                    and metric.name.endswith(".utilization")
                )
                if utilization:
                    v *= 100
                definition = db.scalar(
                    select(MetricDefinition).where(
                        MetricDefinition.collector_id == c.id,
                        MetricDefinition.name == name,
                    )
                )
                if definition is None:
                    definition = MetricDefinition(
                        organization_id=a.organization_id,
                        data_source_id=s.id,
                        collector_id=c.id,
                        name=name,
                        resource_type="HOST",
                        metric_type="OTLP",
                        description="OTLP series " + json.dumps(series, sort_keys=True),
                        query_config={
                            "otel_metric_name": metric.name,
                            "dimensions": series,
                        },
                        unit=(
                            "count"
                            if suffix == ".count"
                            else ("%" if utilization else metric.unit[:50] or None)
                        ),
                    )
                    db.add(definition)
                    db.flush()
                row = MetricSample(
                    organization_id=a.organization_id,
                    metric_definition_id=definition.id,
                    collector_id=c.id,
                    observed_at=timestamp(point.time_unix_nano),
                    value_numeric=v,
                    unit=definition.unit,
                    dimensions=attributes(point.attributes),
                )
                db.add(row)
                db.flush()
                evaluate_metric_sample(db, row)

            for resource in obj.resource_metrics:
                for scope in resource.scope_metrics:
                    for metric in scope.metrics:
                        kind = metric.WhichOneof("data")
                        if kind in ("gauge", "sum"):
                            for point in getattr(metric, kind).data_points:
                                numeric = point.WhichOneof("value")
                                if numeric:
                                    sample(metric, point, getattr(point, numeric))
                        elif kind in ("histogram", "exponential_histogram", "summary"):
                            for point in getattr(metric, kind).data_points:
                                sample(metric, point, point.count, ".count")
                                sample(metric, point, point.sum, ".sum")
        else:
            for resource in obj.resource_spans:
                for scope in resource.scope_spans:
                    for span in scope.spans:
                        increment()
                        if len(span.trace_id) != 16 or len(span.span_id) != 8:
                            raise HTTPException(422, "Invalid trace/span identity")
                        start = timestamp(span.start_time_unix_nano)
                        end = timestamp(span.end_time_unix_nano)
                        if end < start:
                            raise HTTPException(422, "Span ends before it starts")
                        db.add(
                            TraceSpan(
                                organization_id=a.organization_id,
                                agent_id=a.id,
                                trace_id=span.trace_id.hex(),
                                span_id=span.span_id.hex(),
                                name=span.name[:255],
                                started_at=start,
                                ended_at=end,
                                attributes={
                                    **attributes(resource.resource.attributes),
                                    **attributes(span.attributes),
                                },
                            )
                        )
        if count:
            db.add(
                TelemetryReceipt(
                    organization_id=a.organization_id,
                    agent_id=a.id,
                    signal=signal,
                    record_count=count,
                    payload_hash=digest,
                )
            )
        db.commit()


def authentication_gate(request):
    with SessionLocal() as db:
        authenticate(db, request)
