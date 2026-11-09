"""Build Compose's own Bake plan with one explicit CA-file entitlement.

Compose's implicit Bake delegation cannot grant a file outside its contexts.
Do not disable Bake entitlement checks or TLS to work around that rejection.
"""
import json
import ssl
from pathlib import Path


def build_with_trust(compose, trust, private, run):
    trust = Path(trust).resolve(strict=True)
    if not trust.is_file():
        raise ValueError("Build trust must be a readable CA file")
    ssl.create_default_context(cafile=str(trust))
    plan = json.loads(run([*compose, "build", "--print"]))
    if not plan.get("target"):
        raise ValueError("Compose produced no build targets")
    # Resolve only the known public trust secret. Never grant a directory,
    # wildcard, secret contents, host network, or privileged build access.
    path = Path(private) / "compose-bake.json"
    path.write_text(json.dumps(plan))
    path.chmod(0o600)
    return run([
        "docker", "buildx", "bake", "--file", str(path),
        "--allow=fs.read=" + str(trust), "--load",
    ])
