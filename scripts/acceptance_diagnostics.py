"""Export owned acceptance logs without exporting fixture secrets or DB dumps."""

import json
import re
from pathlib import Path


def export_logs(private, output, environment, secrets=()):
    private, output = Path(private), Path(output)
    sensitive = list(secrets)
    sensitive.extend(
        v
        for k, v in environment.items()
        if any(word in k.upper() for word in ("PASSWORD", "TOKEN", "SECRET")) and v
    )

    def collect(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if any(
                    word in key.lower() for word in ("password", "token", "secret")
                ) and isinstance(item, str):
                    sensitive.append(item)
                else:
                    collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    fixture = private / "fixture.json"
    if fixture.exists():
        collect(json.loads(fixture.read_text()))
    output.mkdir(parents=True, exist_ok=True)
    exported = []
    for log in private.glob("*.log"):
        text = log.read_text(errors="replace")
        for secret in sorted(set(sensitive), key=len, reverse=True):
            if secret:
                text = text.replace(secret, "[REDACTED]")
        text = re.sub(
            r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[REDACTED JWT]", text
        )
        text = re.sub(r"(?i)(Bearer )[A-Za-z0-9_.-]+", r"\1[REDACTED]", text)
        (output / log.name).write_text(text)
        exported.append(log.name)
    return sorted(exported)
