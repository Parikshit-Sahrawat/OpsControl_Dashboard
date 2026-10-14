#!/usr/bin/env python3
"""Generate private, verifiable development TLS material without replacing keys."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def command(*args):
    result = subprocess.run(["openssl", *args], capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(
            "Local TLS generation/verification failed; no credentials printed"
        )
    return result.stdout


def initialize(directory, dns_names=()):
    directory = Path(directory).resolve()
    names = ["localhost", "ingestion-gateway", *dns_names]
    if any(
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}", name) for name in names
    ):
        raise ValueError("DNS SANs must be literal hostname identities")
    files = ("ca.crt", "ca.key", "tls.crt", "tls.key")
    existing = [name for name in files if (directory / name).exists()]
    if existing:
        if len(existing) != len(files):
            raise RuntimeError(
                "Partial TLS material exists; preserve it and restore a complete backup"
            )
        command(
            "verify", "-CAfile", str(directory / "ca.crt"), str(directory / "tls.crt")
        )
        command(
            "x509", "-in", str(directory / "tls.crt"), "-checkend", "86400", "-noout"
        )
        if command("pkey", "-in", str(directory / "tls.key"), "-pubout") != command(
            "x509", "-in", str(directory / "tls.crt"), "-pubkey", "-noout"
        ):
            raise RuntimeError(
                "Existing certificate/key mismatch; restore verified backup"
            )
        for name in names:
            result = command(
                "x509", "-in", str(directory / "tls.crt"), "-checkhost", name, "-noout"
            )
            if b"does NOT match" in result:
                raise RuntimeError(
                    "Existing TLS certificate lacks requested DNS SAN; preserve keys and renew explicitly"
                )
        return directory
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    directory.chmod(0o700)
    temporary = Path(tempfile.mkdtemp(prefix=".tls-build-", dir=directory))
    temporary.chmod(0o700)
    try:
        command(
            "req",
            "-x509",
            "-newkey",
            "rsa:3072",
            "-nodes",
            "-days",
            "3650",
            "-keyout",
            str(temporary / "ca.key"),
            "-out",
            str(temporary / "ca.crt"),
            "-subj",
            "/CN=OpsControl Local Development CA",
            "-addext",
            "basicConstraints=critical,CA:TRUE",
            "-addext",
            "keyUsage=critical,keyCertSign,cRLSign",
        )
        command(
            "req",
            "-new",
            "-newkey",
            "rsa:3072",
            "-nodes",
            "-keyout",
            str(temporary / "tls.key"),
            "-out",
            str(temporary / "server.csr"),
            "-subj",
            "/CN=localhost",
        )
        san = ",".join(
            [
                *("DNS:" + name for name in dict.fromkeys(names)),
                "IP:127.0.0.1",
                "IP:::1",
            ]
        )
        (temporary / "extensions.conf").write_text(
            "basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectAltName="
            + san
            + "\n"
        )
        command(
            "x509",
            "-req",
            "-in",
            str(temporary / "server.csr"),
            "-CA",
            str(temporary / "ca.crt"),
            "-CAkey",
            str(temporary / "ca.key"),
            "-CAcreateserial",
            "-days",
            "365",
            "-out",
            str(temporary / "tls.crt"),
            "-extfile",
            str(temporary / "extensions.conf"),
        )
        command(
            "verify", "-CAfile", str(temporary / "ca.crt"), str(temporary / "tls.crt")
        )
        for name in files:
            (temporary / name).chmod(0o600 if name.endswith(".key") else 0o644)
            os.replace(temporary / name, directory / name)
    finally:
        shutil.rmtree(temporary)
    return directory


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default=".demo-private/gateway")
    parser.add_argument("--dns-name", action="append", default=[])
    args = parser.parse_args()
    initialize(args.directory, args.dns_name)
    print(
        "Local gateway TLS material verified; trust only ca.crt, never copy private keys"
    )
