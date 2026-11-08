"""Validate existing package container shapes without inventing policy defaults."""


def require_template_package(value):
    if value is None:
        return value
    if not isinstance(value, dict):
        raise ValueError("Template package must be an object")
    if not isinstance(value.get("collector", {}), dict):
        raise ValueError("collector configuration must be an object")
    for key in ("attributes", "metrics", "alerts", "logs"):
        if not isinstance(value.get(key, []), list) or any(
            not isinstance(row, dict) for row in value.get(key, [])
        ):
            raise ValueError(f"{key} configuration must be an array of objects")
    return value
