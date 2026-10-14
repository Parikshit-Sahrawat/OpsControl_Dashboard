#!/usr/bin/env python3
"""Bundle an operator-approved, checksum-verified upstream runtime; no downloading shell code."""
import argparse, hashlib, json, zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("--os", choices=["linux", "windows"], required=True)
p.add_argument("--runtime", type=Path, required=True)
p.add_argument("--sha256", required=True)
p.add_argument("--output", type=Path, required=True)
args = p.parse_args()
runtime_data = args.runtime.read_bytes()
if args.os == "linux":
    import subprocess

    if not runtime_data.startswith(b"\x7fELF"):
        raise SystemExit("Linux runtime must be an ELF binary")
    result = subprocess.run(
        [str(args.runtime.resolve()), "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode or "0.123.0" not in result.stdout:
        raise SystemExit("Runtime version must be 0.123.0")
else:
    if not runtime_data.startswith(b"MZ"):
        raise SystemExit("Windows runtime must be an approved PE executable")
digest = hashlib.sha256(args.runtime.read_bytes()).hexdigest()
if digest != args.sha256:
    raise SystemExit("Runtime checksum does not match approved distribution")
name = "otelcol-contrib.exe" if args.os == "windows" else "otelcol-contrib"
args.output.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(args.output, "x", compression=zipfile.ZIP_DEFLATED) as z:
    for filename in ("opscontrol_agent.py", "service_health.py", "README.md") + (
        ("install-linux.sh", "uninstall-linux.sh")
        if args.os == "linux"
        else (
            "install-windows.ps1",
            "windows_service.py",
            "requirements-windows.txt",
            "uninstall-windows.ps1",
        )
    ):
        z.write(root / "agent" / filename, filename)
    z.write(args.runtime, name)
    z.writestr("runtime.sha256", digest + "  " + name + "\n")
    z.writestr(
        "manifest.json",
        json.dumps(
            {
                "runtime_version": "0.123.0",
                "agent_version": "1.5.0",
                "os": args.os,
                "sha256": digest,
            }
        ),
    )
print("Agent package built:", args.output)
