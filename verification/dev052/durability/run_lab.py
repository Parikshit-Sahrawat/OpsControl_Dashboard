"""Checkpoint-to-delivery fixture using the existing scoped owner/cleanup wrapper."""

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "owned_collector_lab", HERE.parent / "collector_compat/run_lab.py"
)
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)
if __name__ == "__main__":
    lab.main(
        fixture_dir=HERE,
        validation_contract="guarded",
        project_prefix="dev052a3c-",
        api_fixture=HERE / "api_fixture.py",
        postcheck_after_fixture_failure=True,
    )
