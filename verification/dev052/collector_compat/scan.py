"""Offline image-archive catalog/scan, pinned identity, no containers or deployment."""

import argparse, datetime, hashlib, json, os, pathlib, subprocess, tarfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/verification/dev052/security/2026-10-25-collector"
TOOLS = pathlib.Path("/tmp/dev052a-tools")
SPECS = [
    (
        "contrib",
        "otel/opentelemetry-collector-contrib:0.163.2@sha256:7f22d2a6748110ffb6a59bc0df448bccbf501cdb667d610ede4c61d3863d5849",
        "experimental candidate; not promoted",
    ),
    (
        "contrib-guarded",
        "otel/opentelemetry-collector-contrib:0.123.0@sha256:e39311df1f3d941923c00da79ac7ba6269124a870ee87e3c3ad24d60f8aee4d2",
        "production guard retained; unresolved vulnerabilities",
    ),
]
EXPECTED_BINARY = {
    "contrib": "dbd12d55073b70add777895457040f8ede59fc1ee7198d6ae179a37087eea8bb",
    "contrib-guarded": "6bca4ddd928b4b0880f7ec6c16511922f740c497b4efa4b33915b2d54a729213",
}

env = os.environ.copy()
env.update(
    GRYPE_DB_CACHE_DIR="/tmp/dev052a-grype-db",
    GRYPE_DB_AUTO_UPDATE="false",
    SYFT_CHECK_FOR_APP_UPDATE="false",
    XDG_CACHE_HOME="/tmp/dev052a-cache",
)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--only")
options = parser.parse_args()
rows = (
    json.loads((OUT / "image-inventory.json").read_text())
    if (OUT / "image-inventory.json").exists()
    else []
)
for key, ref, role in SPECS:
    if options.only and key != options.only:
        continue
    prior = [r for r in rows if r["name"] == key]
    rows[:] = [r for r in rows if r["name"] != key]
    row = {
        "previous_attempts": prior,
        "name": key,
        "requested_reference": ref,
        "role": role,
        "repository_manifest_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    rows.append(row)
    archive = None
    try:
        # Select only non-secret identity fields; never dump image/process environments.
        fields = json.loads(
            subprocess.check_output(
                [
                    "docker",
                    "image",
                    "inspect",
                    "--format",
                    '{"id":{{json .Id}},"architecture":{{json .Architecture}},"os":{{json .Os}},"repoDigests":{{json .RepoDigests}}}',
                    ref,
                ],
                stderr=subprocess.DEVNULL,
            )
        )
        row["source_commit"] = None
        row["source_status"] = (
            "Local working-tree candidate; exact committed-source attestation unavailable"
            if ref.startswith("dev052a2-")
            else "Prior immutable candidate/upstream image; see prior provenance"
        )
        row["upstream_source_commit"] = (
            "NOT ATTESTED"
            if not ref.startswith("dev052a2-")
            else "repository source archive"
        )
        row.update(fields)
        image_id = fields["id"]
        archive = pathlib.Path("/tmp/dev052a3-" + key + ".tar")
        subprocess.run(["docker", "save", "-o", str(archive), image_id], check=True)
        with archive.open("rb") as stream:
            row["archive_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        with tarfile.open(archive) as tar:
            manifest = json.load(tar.extractfile("manifest.json"))
            config = tar.extractfile(manifest[0]["Config"]).read()
            assert "sha256:" + hashlib.sha256(config).hexdigest() == image_id
            binary_hashes = []
            for layer in manifest[0]["Layers"]:
                with tarfile.open(fileobj=tar.extractfile(layer)) as contents:
                    for member in contents:
                        if (
                            member.isfile()
                            and member.name.lstrip("./") == "otelcol-contrib"
                        ):
                            binary_hashes.append(
                                hashlib.file_digest(
                                    contents.extractfile(member), "sha256"
                                ).hexdigest()
                            )
            assert binary_hashes and binary_hashes[-1] == EXPECTED_BINARY[key]
            row["image_binary_sha256"] = binary_hashes[-1]

        for tool, args, suffix in [
            (
                "syft",
                ["docker-archive:" + str(archive), "-o", "cyclonedx-json"],
                "sbom",
            ),
            ("grype", ["docker-archive:" + str(archive), "-o", "json"], "scan"),
        ]:
            with (OUT / (key + "." + suffix + ".json")).open("w") as out, (
                OUT / (key + "." + suffix + ".log")
            ).open("w") as log:
                result = subprocess.run(
                    [str(TOOLS / tool), *args], env=env, stdout=out, stderr=log
                )
            row[suffix + "_exit_code"] = result.returncode
        row["status"] = (
            "SCANNED"
            if row["sbom_exit_code"] == row["scan_exit_code"] == 0
            else "BLOCKED"
        )
        archive.unlink()
    except Exception as error:
        row.update(status="BLOCKED", error=str(error))
    finally:
        if archive is not None:
            archive.unlink(missing_ok=True)
    (OUT / "image-inventory.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(key, row["status"], flush=True)
