"""Offline image-archive catalog/scan, pinned identity, no containers or deployment."""

import argparse, datetime, hashlib, json, os, pathlib, subprocess, tarfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/verification/dev052/security/2026-10-25-remediation"
TOOLS = pathlib.Path("/tmp/dev052a-tools")
SPECS = [
    ("backend-runtime", "dev052a1-backend", "production API/worker candidate"),
    (
        "migration",
        "dev052a1-migration",
        "production schema-maintenance candidate; not an API service",
    ),
    ("frontend", "dev052a1-frontend", "production static frontend candidate"),
    ("gateway", "dev052a1-gateway", "production TLS ingestion gateway candidate"),
    (
        "postgres-alpine",
        "postgres:17-alpine@sha256:eee6c6e1b0894fa4fe0075eb054af9fd1cf39a35321c2d4110626cfe506411fb",
        "production database candidate; migration/collation approval pending",
    ),
    (
        "contrib",
        "otel/opentelemetry-collector-contrib:0.163.2@sha256:7f22d2a6748110ffb6a59bc0df448bccbf501cdb667d610ede4c61d3863d5849",
        "collector evaluation candidate; version contract blocked, NOT promoted",
    ),
]

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
rows = json.loads((OUT / "image-inventory.json").read_text()) if options.only else []
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
        row["source_commit"] = (
            row["repository_manifest_commit"] if ref.startswith("dev052a1-") else None
        )
        row["upstream_source_commit"] = (
            "NOT ATTESTED"
            if not ref.startswith("dev052a1-")
            else "repository source archive"
        )
        row.update(fields)
        image_id = fields["id"]
        archive = pathlib.Path("/tmp/dev052a1-" + key + ".tar")
        subprocess.run(["docker", "save", "-o", str(archive), image_id], check=True)
        with archive.open("rb") as stream:
            row["archive_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        with tarfile.open(archive) as tar:
            manifest = json.load(tar.extractfile("manifest.json"))
            config = tar.extractfile(manifest[0]["Config"]).read()
            assert "sha256:" + hashlib.sha256(config).hexdigest() == image_id
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
    (OUT / "image-inventory.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(key, row["status"], flush=True)
