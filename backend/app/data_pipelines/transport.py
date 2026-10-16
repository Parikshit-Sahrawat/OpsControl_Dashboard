"""Optional V1.6 structured-log transport. VM Agent installation is unchanged.

A lease is obtained BEFORE opening a source. Server acceptance owns checkpoints;
this client never advances a local cursor before durable backend acknowledgement.
Rotation/truncation fail closed and require an explicit continuity/recovery plan.
"""

import argparse
import glob
import hashlib
import json
import os
import ssl
import stat
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlsplit


class PipelineTransport:
    def __init__(self, backend, identity_file, ca_file=None):
        target = urlsplit(backend)
        if (
            target.scheme != "https"
            or not target.hostname
            or target.username
            or target.password
            or target.query
            or target.fragment
        ):
            raise ValueError("Verified HTTPS required")
        path = Path(identity_file)
        if os.name != "nt" and stat.S_IMODE(path.stat().st_mode) & 0o077:
            raise ValueError("Private Agent identity file required")
        self.identity = json.loads(path.read_text())
        self.backend = backend.rstrip("/")
        self.context = ssl.create_default_context(cafile=ca_file)

    def request(self, path, payload):
        req = Request(
            self.backend + "/api/v1/agent/" + path,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.identity["access_token"],
            },
        )
        with urlopen(req, context=self.context, timeout=15) as r:
            return json.load(r)

    def collect(self, source_id, verification=False, recovery_operation_id=None):
        result = self.request(
            "pipeline-claim",
            {
                "source_id": source_id,
                "verification": verification,
                "recovery_operation_id": recovery_operation_id,
            },
        )
        ticket = result["ticket"]
        checkpoint = ticket["checkpoint"]
        pattern = result["identity"]["path"]
        sources = dict(checkpoint.get("sources", {}))
        records = []
        deadline = time.monotonic() + 90
        discovered = sorted(glob.glob(pattern))
        complete = len(discovered) <= 100
        for path in discovered[:100]:
            if time.monotonic() > deadline:
                raise RuntimeError("Lease collection budget exceeded")
            with open(path, "rb") as stream:
                info = os.fstat(stream.fileno())
                previous = sources.get(path, {})
                if previous and (
                    previous.get("inode") != info.st_ino
                    or previous.get("device") != info.st_dev
                    or previous.get("offset", 0) > info.st_size
                ):
                    raise RuntimeError(
                        "SOURCE_GENERATION_OR_TRUNCATION_REQUIRES_RECOVERY"
                    )
                stream.seek(previous.get("offset", 0))
                offset = stream.tell()
                while len(records) < 1000:
                    if time.monotonic() > deadline:
                        raise RuntimeError("Lease collection budget exceeded")
                    start = stream.tell()
                    line = stream.readline(1048577)
                    if not line:
                        break
                    if len(line) > 1048576:
                        raise RuntimeError("Structured log record exceeds limit")
                    if not line.endswith(b"\n"):
                        stream.seek(start)
                        break
                    payload = json.loads(line)
                    if not isinstance(payload, dict) or not (
                        isinstance(payload.get("event"), dict)
                        or isinstance(payload.get("pentaho_observation"), dict)
                    ):
                        raise ValueError(
                            "Normalized structured pipeline event required"
                        )
                    key = hashlib.sha256(
                        json.dumps(
                            [
                                ticket["generation"],
                                path,
                                info.st_dev,
                                info.st_ino,
                                start,
                                stream.tell(),
                            ]
                        ).encode()
                    ).hexdigest()
                    observed_at = (
                        payload["pentaho_observation"].get("observed_at")
                        if "pentaho_observation" in payload
                        else payload["event"].get("timestamp")
                    )
                    recovery_range = result.get("recovery_range")
                    include = True
                    if recovery_range:
                        from datetime import datetime

                        observed = datetime.fromisoformat(
                            observed_at.replace("Z", "+00:00")
                        )
                        include = (
                            datetime.fromisoformat(recovery_range["start"])
                            <= observed
                            <= datetime.fromisoformat(recovery_range["end"])
                        )
                    if not include:
                        offset = stream.tell()
                        continue
                    records.append(
                        {
                            "key": key,
                            "native_job_id": payload.get("native_job_id"),
                            "evidence_origin": payload.get(
                                "evidence_origin", "UNKNOWN"
                            ),
                            **(
                                {"pentaho_observation": payload["pentaho_observation"]}
                                if "pentaho_observation" in payload
                                else {"event": payload["event"]}
                            ),
                            "observed_at": observed_at,
                            "evidence": {
                                "source_path": path,
                                "byte_offset": start,
                                "raw_record": payload,
                            },
                        }
                    )
                    offset = stream.tell()
                complete = complete and offset >= os.fstat(stream.fileno()).st_size
                sources[path] = {
                    "device": info.st_dev,
                    "inode": info.st_ino,
                    "offset": offset,
                }
        if not glob.glob(pattern):
            raise FileNotFoundError("Configured source pattern has no readable files")
        return self.request(
            "pipeline-evidence",
            {
                "source_id": source_id,
                "verification": verification,
                "recovery_operation_id": recovery_operation_id,
                "ticket": ticket,
                "records": records,
                "checkpoint": {"sources": sources},
                "complete": complete,
            },
        )

    def continuity(self, operation_id, paths):
        files = {}
        for path in paths:
            try:
                with open(path, "rb") as stream:
                    info = os.fstat(stream.fileno())
                    files[path] = {
                        "readable": True,
                        "device": info.st_dev,
                        "inode": info.st_ino,
                        "size": info.st_size,
                    }
            except OSError:
                files[path] = {"readable": False}
        return self.request(
            "pipeline-continuity", {"operation_id": operation_id, "files": files}
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True)
    parser.add_argument("--identity-file", required=True)
    parser.add_argument("--ca-file")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--verification", action="store_true")
    parser.add_argument("--recovery-operation-id")
    args = parser.parse_args()
    PipelineTransport(args.backend, args.identity_file, args.ca_file).collect(
        args.source_id, args.verification, args.recovery_operation_id
    )
