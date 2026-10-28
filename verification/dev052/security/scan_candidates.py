"""Offline image-archive catalog/scan, pinned identity, no containers or deployment."""

import argparse, datetime, hashlib, json, os, pathlib, subprocess, tarfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/verification/dev052/security/2026-10-25"
TOOLS = pathlib.Path("/tmp/dev052a-tools")
SPECS = [
    ("backend-runtime", "dev052a-backend-runtime", "API/worker restricted runtime"),
    ("backend-uat", "dev052a-backend-uat", "UAT API/worker/migration candidate"),
    ("backend-demo", "dev052a-backend-demo", "Demo only; not production approved"),
    ("frontend", "dev052a-frontend", "Static frontend candidate"),
    ("postgres", "postgres:17", "Database ancillary"),
    ("postgres-alpine", "postgres:17-alpine", "UAT database ancillary"),
    (
        "postgres-ecr",
        "public.ecr.aws/docker/library/postgres:17",
        "Demo database mirror",
    ),
    ("gateway", "nginx:1.28-alpine", "Ingestion gateway"),
    (
        "contrib",
        "otel/opentelemetry-collector-contrib:0.123.0@sha256:e39311df1f3d941923c00da79ac7ba6269124a870ee87e3c3ad24d60f8aee4d2",
        "Collector/embedded demo distribution",
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
            row["repository_manifest_commit"] if ref.startswith("dev052a-") else None
        )
        row["upstream_source_commit"] = (
            "NOT ATTESTED"
            if not ref.startswith("dev052a-")
            else "repository source archive"
        )
        row.update(fields)
        image_id = fields["id"]
        archive = pathlib.Path("/tmp/dev052a-" + key + ".tar")
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
