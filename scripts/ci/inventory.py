"""Export workflow/job/command evidence without retiring or executing tests."""

import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


def inventory(root=ROOT):
    workflows = []
    for path in sorted((root / ".github/workflows").glob("*")):
        if path.suffix not in (".yml", ".yaml"):
            continue
        data = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        jobs = []
        for key, job in data.get("jobs", {}).items():
            jobs.append(
                {
                    "id": key,
                    "check_name": job.get("name", key),
                    "runner": job.get("runs-on"),
                    "permissions": job.get("permissions", data.get("permissions")),
                    "needs": job.get("needs", []),
                    "condition": job.get("if"),
                    "steps": [
                        {
                            "name": step.get("name"),
                            "uses": step.get("uses"),
                            "command": step.get("run"),
                            "working_directory": step.get("working-directory"),
                            "condition": step.get("if"),
                        }
                        for step in job.get("steps", [])
                    ],
                }
            )
        workflows.append(
            {
                "path": str(path.relative_to(root)),
                "name": data["name"],
                "triggers": data["on"],
                "jobs": jobs,
            }
        )
    return {
        "schema": 1,
        "workflows": workflows,
        "limits": "Commands and workflow definitions, not proof of execution or release clearance.",
    }


if __name__ == "__main__":
    print(json.dumps(inventory(), indent=2))
