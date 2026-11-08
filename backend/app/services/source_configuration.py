"""Data Source-owned configuration commands; no deployment or health authority."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, text

from app.models import (
    DataSource,
    MonitoringTemplate,
    MonitoringTemplateAttachment,
    MonitoringTemplateVersion,
)
from app.models.entities import SourceConfigurationRevision
from app.security.scope import current_principal
from app.security.secret_refs import require_safe_config, redact_config
from app.services.excluded_platforms import (
    require_supported_source,
    require_supported_configuration,
)


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Member(BaseModel):
    model_config = ConfigDict(extra="forbid")
    template_id: UUID
    template_version: int = Field(ge=1)
    priority: int = Field(ge=0, le=100000)
    enabled: bool = True
    overrides: dict = Field(default_factory=dict)

    @field_validator("overrides")
    @classmethod
    def safe(cls, value):
        from app.services.template_packages import require_template_package

        canonical(value)  # Reject non-finite JSON before hashing or persistence.
        return require_safe_config(
            require_supported_configuration(require_template_package(value))
        )


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0)
    attachments: list[Member] = Field(max_length=100)


class Rollback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0)
    target_revision: int = Field(ge=1)


def source_row(db, source_id, lock=False, write=False):
    source = (
        db.scalar(
            select(DataSource)
            .where(DataSource.id == source_id)
            .execution_options(populate_existing=True)
            .with_for_update()
        )
        if lock
        else db.get(DataSource, source_id)
    )
    if not source:
        raise HTTPException(404, "Data source not found")
    principal = current_principal.get()
    if not principal or not principal.allows(
        "templates.manage" if write else "templates.view", source.organization_id
    ):
        raise HTTPException(403, "Source template permission required")
    return source


def members(db, source_id):
    return [
        dict(
            template_id=str(x.template_id),
            template_version=x.template_version,
            priority=x.priority,
            enabled=x.enabled,
            overrides=x.overrides or {},
        )
        for x in db.scalars(
            select(MonitoringTemplateAttachment)
            .where(MonitoringTemplateAttachment.data_source_id == source_id)
            .order_by(
                MonitoringTemplateAttachment.priority,
                MonitoringTemplateAttachment.template_id,
            )
        )
    ]


def revision_row(db, source, number):
    row = db.scalar(
        select(SourceConfigurationRevision).where(
            SourceConfigurationRevision.data_source_id == source.id,
            SourceConfigurationRevision.revision == number,
        )
    )
    if not row:
        raise HTTPException(404, "Configuration revision not found")
    return row


def output(row):
    return redact_config(
        dict(
            revision=row.revision,
            previous_revision=row.previous_revision,
            restores_revision=row.restores_revision,
            kind=row.kind,
            actor_id=str(row.actor_id),
            actor=row.actor_name,
            created_at=row.created_at.isoformat(),
            content_hash=row.content_hash,
            request_hash=row.request_hash,
            document=row.document,
            application="NOT_REQUESTED",
            health="UNVERIFIED",
        )
    )


def evaluate(db, source, intent):
    from app.services.template_resolution import _apply_package
    from app.services.template_applicability import applicability

    seen, priorities, reasons, pins = set(), set(), [], []
    effective = dict(collector={}, attributes=[], metrics=[], alerts=[], logs=[])
    for member in intent:
        tid = UUID(member["template_id"])
        if tid in seen:
            raise HTTPException(422, "Duplicate template attachment")
        seen.add(tid)
        template = db.get(MonitoringTemplate, tid)
        version = db.scalar(
            select(MonitoringTemplateVersion).where(
                MonitoringTemplateVersion.template_id == tid,
                MonitoringTemplateVersion.version == member["template_version"],
            )
        )
        if not template or not version:
            raise HTTPException(409, "Pinned template dependency missing")
        pin = dict(member, package=redact_config(version.package_config))
        pins.append(pin)
        if not member["enabled"]:
            continue
        if template.status != "COMMITTED" or version.status != "COMMITTED":
            raise HTTPException(409, "Pinned template dependency retired")
        if member["priority"] in priorities:
            raise HTTPException(422, "Enabled templates require distinct priorities")
        priorities.add(member["priority"])
        package = deepcopy(version.package_config or {})
        reasons.extend(applicability(source, package, member["overrides"]))
        reasons.extend(
            applicability(
                source,
                package,
                (source.connection_config or {})
                .get("opscontrol", {})
                .get("monitoring_overrides", {}),
            )
        )
        # Conflicting named components must not silently replace one another.
        before = deepcopy(effective)
        _apply_package(effective, package)
        for key, identity in (
            ("metrics", "metric"),
            ("logs", "name"),
            ("alerts", "name"),
            ("attributes", "key"),
        ):
            prior = {r.get(identity): r for r in before[key]}
            for row in package.get(key, []):
                if row.get(identity) in prior and row != prior[row[identity]]:
                    reasons.append(
                        dict(
                            code="COMPATIBILITY_CONFLICT",
                            path=key + "/" + str(row.get(identity)),
                        )
                    )
        if (
            before["collector"]
            and package.get("collector")
            and before["collector"] != effective["collector"]
        ):
            reasons.append(dict(code="COMPATIBILITY_CONFLICT", path="collector"))
        _apply_package(effective, member["overrides"])
    config = source.connection_config or {}
    _apply_package(
        effective, config.get("opscontrol", {}).get("monitoring_overrides", {})
    )
    attributes = config.get("opscontrol", {}).get("attributes", {})
    for row in effective["attributes"]:
        if (
            row.get("required")
            and row.get("defaultValue") in (None, "")
            and attributes.get(row.get("key")) in (None, "")
        ):
            reasons.append(
                dict(code="REQUIRED_ATTRIBUTE_MISSING", path="attributes/" + row["key"])
            )
    return dict(
        attachments=intent,
        pins=pins,
        effective=effective,
        validation=dict(
            valid=not reasons,
            reasons=reasons,
            evaluator="source-policy-v1",
            evaluated_at=datetime.now(timezone.utc).isoformat(),
        ),
        source_context=dict(
            source_type=source.source_type,
            endpoint=redact_config(source.endpoint),
            configuration=redact_config(config),
        ),
        application="NOT_REQUESTED",
        health="UNVERIFIED",
    )


def current(db, source):
    return dict(
        revision=source.configuration_revision,
        attachments=members(db, source.id),
        legacy_import_required=bool(
            not source.configuration_revision and members(db, source.id)
        ),
        application="NOT_REQUESTED",
        health="UNVERIFIED",
    )


def commit(db, source_id, payload, key, kind="UPDATE", target=None, importing=False):
    source = source_row(db, source_id, lock=True, write=True)
    principal = current_principal.get()
    require_supported_source(source)
    request = dict(command=payload.model_dump(mode="json"), kind=kind, target=target)
    request_hash = digest(request)
    prior = db.scalar(
        select(SourceConfigurationRevision).where(
            SourceConfigurationRevision.data_source_id == source.id,
            SourceConfigurationRevision.actor_id == principal.user_id,
            SourceConfigurationRevision.command_key == key,
        )
    )
    if prior:
        if prior.request_hash != request_hash:
            raise HTTPException(409, "IDEMPOTENCY_KEY_REUSED")
        return dict(
            **output(prior),
            replayed=True,
            current_revision=source.configuration_revision
        )
    if payload.expected_revision != source.configuration_revision:
        raise HTTPException(
            409,
            dict(code="STALE_REVISION", current_revision=source.configuration_revision),
        )
    old_members = members(db, source.id)
    if old_members and source.configuration_revision == 0 and not importing:
        raise HTTPException(
            409,
            "LEGACY_IMPORT_REQUIRED: preserve existing configuration before replacement",
        )
    if importing:
        if source.configuration_revision:
            raise HTTPException(409, "Source is already revisioned")
        document = dict(
            attachments=old_members,
            validation=dict(
                valid=False, reasons=[dict(code="LEGACY_APPLICABILITY_UNVERIFIED")]
            ),
            application="NOT_REQUESTED",
            health="UNVERIFIED",
            provenance="Imported at current time; historical author/validation unknown",
        )
    else:
        intent = (
            payload.model_dump(mode="json")["attachments"]
            if target is None
            else deepcopy(revision_row(db, source, target).document["attachments"])
        )
        intent.sort(key=lambda m: (m["priority"], m["template_id"]))
        document = evaluate(db, source, intent)
        if not document["validation"]["valid"]:
            raise HTTPException(422, document["validation"])
    number = source.configuration_revision + 1
    # A transaction-local capability fences old binary/ORM writers. The DB
    # trigger also requires a matching revision before transaction commit.
    db.execute(
        text("SELECT set_config('opscontrol.configuration_source', :source, true)"),
        dict(source=str(source.id)),
    )
    if not importing:
        desired = {UUID(m["template_id"]): m for m in document["attachments"]}
        existing = {
            x.template_id: x
            for x in db.scalars(
                select(MonitoringTemplateAttachment).where(
                    MonitoringTemplateAttachment.data_source_id == source.id
                )
            )
        }
        for tid, row in existing.items():
            if tid not in desired:
                db.delete(row)
        for tid, member in desired.items():
            row = existing.get(tid)
            if row is None:
                row = MonitoringTemplateAttachment(
                    data_source_id=source.id, template_id=tid
                )
                db.add(row)
            for field in ("template_version", "priority", "enabled", "overrides"):
                setattr(row, field, member[field])
    document["events"] = dict(before=old_members, after=document["attachments"])
    safe = redact_config(document)
    canonical_document = canonical(safe)
    row = SourceConfigurationRevision(
        organization_id=source.organization_id,
        data_source_id=source.id,
        revision=number,
        previous_revision=source.configuration_revision or None,
        restores_revision=target,
        kind="IMPORT" if importing else kind,
        actor_id=principal.user_id,
        actor_name=principal.username,
        command_key=key,
        request_hash=request_hash,
        document=safe,
        canonical_document=canonical_document,
        content_hash=hashlib.sha256(canonical_document.encode()).hexdigest(),
    )
    db.add(row)
    source.configuration_revision = number
    db.commit()
    db.refresh(row)
    return dict(**output(row), replayed=False, current_revision=number)
