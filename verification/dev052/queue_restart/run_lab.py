"""Checkpoint-to-delivery fixture using the existing scoped owner/cleanup wrapper."""

import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "owned_collector_lab", HERE.parent / "collector_compat/run_lab.py"
)
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)
if __name__ == "__main__":
    output = Path(sys.argv[sys.argv.index("--output") + 1]).resolve()
    with tempfile.TemporaryDirectory(prefix="dev052a3d-fixture-") as temp:
        frozen = Path(temp)
        for source in HERE.glob("*.py"):
            shutil.copy2(source, frozen / source.name)
        try:
            lab.main(
                fixture_dir=frozen,
                validation_contract="guarded",
                project_prefix="dev052a3d-",
                api_fixture=frozen / "api_fixture.py",
                postcheck_after_fixture_failure=True,
            )
        finally:
            if output.exists():
                shutil.copytree(frozen, output / "fixture-source", dirs_exist_ok=True)
