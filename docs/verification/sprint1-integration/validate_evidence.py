"""Self-contained evidence integrity, not implementation/UAT/release certification."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

BASE = Path(__file__).resolve().parent


def verify_artifacts(directory, manifest):
    directory = directory.resolve()
    if manifest.get("schema") != 1:
        raise ValueError("Unsupported evidence manifest")
    for name, expected in manifest["files"].items():
        relative = Path(name)
        file = (directory / relative).resolve()
        if relative.is_absolute() or ".." in relative.parts or not file.is_relative_to(directory):
            raise ValueError("Evidence path traversal")
        if not re.fullmatch("[a-f0-9]{64}", expected) or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise ValueError("Evidence checksum mismatch: " + name)
    actual = {str(f.relative_to(directory)) for f in directory.rglob("*") if f.is_file() and f.name != "ARTIFACT_SHA256.json" and "__pycache__" not in f.parts}
    if actual != set(manifest["files"]):
        raise ValueError("Evidence inventory incomplete")


def validate():
    manifest = json.loads((BASE / "ARTIFACT_SHA256.json").read_text())
    verify_artifacts(BASE, manifest)
    for file in BASE.glob("*.json"):
        json.loads(file.read_text())
    metadata = json.loads((BASE / "VALIDATION.json").read_text())
    assert metadata["gates"] == {"CHK-001":"FAIL", "CHK-002":"BLOCKED", "SECURITY":"BLOCKED", "RELEASE":"NO-GO", "SPRINT1":"NOT_COMPLETE"}
    assert metadata["merge_authorized"] is False
    root = BASE.parents[2]
    # Current review documents only. Relocated historical branch blobs retain
    # their original-source relative references and are explicitly identified.
    for file in BASE.glob("*.md"):
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", file.read_text()):
            if target.startswith(("https://","http://","#")):
                continue
            path = (file.parent / unquote(target.split("#")[0])).resolve()
            if not path.is_relative_to(root) or not path.exists():
                raise ValueError("Broken/unsafe current documentation link: " + target)
    sources = json.loads((BASE / "TESTED_SOURCE_SHA256.json").read_text())
    sha = sources["final_implementation_sha"]
    if not re.fullmatch("[a-f0-9]{40}", sha):
        raise ValueError("Immutable source commit required")
    for path, expected in sources["files"].items():
        # Verify the identified historical source, not a later sprint's code.
        content = subprocess.check_output(["git","show",sha+":"+path],cwd=root)
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError("Source provenance mismatch: " + path)
    return True


if __name__ == "__main__":
    validate()
    print("Evidence integrity PASS: JSON, links, source provenance, artifact inventory/hashes and protected gate declarations; not release certification")
