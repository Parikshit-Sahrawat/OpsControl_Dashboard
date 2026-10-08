from copy import deepcopy
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DataSource, MonitoringTemplate, MonitoringTemplateAttachment, MonitoringTemplateVersion


_COMPONENT_KEYS = ("attributes", "metrics", "alerts", "logs")


def _deep_merge(base: dict, overlay: dict) -> dict:
    result = deepcopy(base)
    for key, value in (overlay or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _merge_named_rows(rows: list[dict], incoming: list[dict], identity: str) -> list[dict]:
    result = deepcopy(rows)
    positions = {str(row.get(identity)): i for i, row in enumerate(result) if row.get(identity)}
    for row in incoming or []:
        key = row.get(identity)
        if not key:
            result.append(deepcopy(row))
            continue
        key = str(key)
        if key in positions:
            result[positions[key]] = _deep_merge(result[positions[key]], row)
        else:
            positions[key] = len(result)
            result.append(deepcopy(row))
    return result


def _apply_package(effective: dict, package: dict) -> dict:
    package = package or {}
    effective["collector"] = _deep_merge(effective.get("collector", {}), package.get("collector", {}))
    effective["attributes"] = _merge_named_rows(effective.get("attributes", []), package.get("attributes", []), "key")
    effective["metrics"] = _merge_named_rows(effective.get("metrics", []), package.get("metrics", []), "metric")
    effective["alerts"] = _merge_named_rows(effective.get("alerts", []), package.get("alerts", []), "name")
    effective["logs"] = _merge_named_rows(effective.get("logs", []), package.get("logs", []), "name")
    return effective


def _template_version(db: Session, attachment: MonitoringTemplateAttachment) -> tuple[MonitoringTemplate, MonitoringTemplateVersion]:
    template = db.get(MonitoringTemplate, attachment.template_id)
    if not template:
        raise HTTPException(status_code=409, detail=f"Monitoring template {attachment.template_id} not found")
    version = db.scalar(
        select(MonitoringTemplateVersion).where(
            MonitoringTemplateVersion.template_id == attachment.template_id,
            MonitoringTemplateVersion.version == attachment.template_version,
            MonitoringTemplateVersion.status == "COMMITTED",
        )
    )
    if not version:
        raise HTTPException(
            status_code=409,
            detail=f"Template '{template.name}' version {attachment.template_version} is no longer available",
        )
    return template, version


def list_template_attachments(db: Session, data_source_id: UUID, enabled_only: bool = False):
    stmt = (
        select(MonitoringTemplateAttachment)
        .where(MonitoringTemplateAttachment.data_source_id == data_source_id)
        .order_by(MonitoringTemplateAttachment.priority.asc(), MonitoringTemplateAttachment.id.asc())
    )
    if enabled_only:
        stmt = stmt.where(MonitoringTemplateAttachment.enabled.is_(True))
    return list(db.scalars(stmt).all())


def resolve_data_source_configuration(db: Session, data_source_id: UUID) -> dict:
    source = db.get(DataSource, data_source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    attachments = list_template_attachments(db, data_source_id, enabled_only=True)
    effective = {
        "data_source_id": str(source.id),
        "templates": [],
        "collector": {},
        "attributes": [],
        "metrics": [],
        "alerts": [],
        "logs": [],
        "conflicts": [],
        "valid": True,
    }

    for attachment in attachments:
        template, version = _template_version(db, attachment)
        before = deepcopy(effective)
        _apply_package(effective, version.package_config or {})
        if attachment.overrides:
            _apply_package(effective, attachment.overrides)

        effective["templates"].append({
            "template_id": str(template.id),
            "template_name": template.name,
            "version": attachment.template_version,
            "priority": attachment.priority,
            "overrides_applied": bool(attachment.overrides),
        })

        # A collector conflict is intentional and deterministic: higher priority
        # wins because attachments are applied from low to high priority.
        previous_type = before.get("collector", {}).get("type")
        current_type = effective.get("collector", {}).get("type")
        if previous_type and current_type and previous_type != current_type:
            effective["conflicts"].append({
                "component": "collector",
                "field": "type",
                "message": f"Collector type '{previous_type}' was replaced by '{current_type}' by template '{template.name}' v{attachment.template_version}",
                "winner": template.name,
                "winner_version": attachment.template_version,
            })

    opscontrol = {}
    if isinstance(source.connection_config, dict):
        opscontrol = source.connection_config.get("opscontrol") or {}
    source_overrides = opscontrol.get("monitoring_overrides") or {}
    if source_overrides:
        _apply_package(effective, source_overrides)
        effective["source_overrides_applied"] = True
    else:
        effective["source_overrides_applied"] = False

    # Surface unresolved required attributes without inventing values.
    effective["missing_required_attributes"] = [
        item["key"]
        for item in effective["attributes"]
        if item.get("required") and item.get("defaultValue") in (None, "")
        and opscontrol.get("attributes", {}).get(item.get("key")) in (None, "")
    ]
    effective["valid"] = not bool(effective["missing_required_attributes"])
    return effective


def attach_template(
    db: Session,
    data_source_id: UUID,
    template_id: UUID,
    template_version: int | None = None,
    priority: int = 100,
    overrides: dict | None = None,
):
    source = db.get(DataSource, data_source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")
    template = db.get(MonitoringTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Monitoring template not found")
    if source.organization_id and template.scope is None:
        raise HTTPException(status_code=409, detail="Template scope is invalid")

    version_number = int(template_version or template.version)
    version = db.scalar(
        select(MonitoringTemplateVersion).where(
            MonitoringTemplateVersion.template_id == template_id,
            MonitoringTemplateVersion.version == version_number,
            MonitoringTemplateVersion.status == "COMMITTED",
        )
    )
    if not version:
        raise HTTPException(status_code=409, detail=f"Template version {version_number} is not available")

    existing = db.scalar(
        select(MonitoringTemplateAttachment).where(
            MonitoringTemplateAttachment.data_source_id == data_source_id,
            MonitoringTemplateAttachment.template_id == template_id,
        )
    )
    if existing:
        existing.template_version = version_number
        existing.priority = priority
        existing.overrides = overrides
        existing.enabled = True
        db.commit()
        db.refresh(existing)
        return existing

    attachment = MonitoringTemplateAttachment(
        data_source_id=data_source_id,
        template_id=template_id,
        template_version=version_number,
        priority=priority,
        overrides=overrides,
        enabled=True,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def detach_template(db: Session, data_source_id: UUID, template_id: UUID):
    attachment = db.scalar(
        select(MonitoringTemplateAttachment).where(
            MonitoringTemplateAttachment.data_source_id == data_source_id,
            MonitoringTemplateAttachment.template_id == template_id,
        )
    )
    if not attachment:
        raise HTTPException(status_code=404, detail="Template attachment not found")
    db.delete(attachment)
    db.commit()
