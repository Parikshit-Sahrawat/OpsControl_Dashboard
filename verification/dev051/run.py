#!/usr/bin/env python3
"""Run unmodified PR #65 assertions against an explicit, committed product revision.

The original runner's default baseline and all original evidence stay unchanged.
Only its in-memory product archive SHA is overridden in this separate adapter.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "f617cc653a965c2ad1bb7edf9e20237e40044b97"
HARNESS = "0e237026c7f1f293d2b0d0e8c94255ed4597c0dc"


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    product = (
        git("rev-parse", "--verify", args.product_commit + "^{commit}").decode().strip()
    )
    subprocess.run(
        ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", BASELINE, product],
        check=True,
    )
    output = args.output.resolve()
    # Extract only immutable harness files, never the original evidence tree.
    with tempfile.TemporaryDirectory(prefix="dev051-adapter-") as directory:
        stage = Path(directory)
        archive = stage / "harness.tar"
        archive.write_bytes(git("archive", HARNESS, "verification/dev05"))
        with tarfile.open(archive) as source:
            source.extractall(stage, filter="data")
        hashes = {
            str(p.relative_to(stage)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (stage / "verification/dev05").rglob("*")
            if p.is_file()
        }
        spec = importlib.util.spec_from_file_location(
            "original_dev05", stage / "verification/dev05/run.py"
        )
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        assert runner.BASELINE == BASELINE
        runner.BASELINE = product
        # Allow original read-only git archive commands in the external harness
        # staging directory to resolve objects from this checkout. No worktree,
        # reset, checkout, source replacement or original-runner edit is needed.
        old_git_dir = os.environ.get("GIT_DIR")
        old_argv = sys.argv
        os.environ["GIT_DIR"] = git("rev-parse", "--absolute-git-dir").decode().strip()
        sys.argv = [str(stage / "verification/dev05/run.py"), "--output", str(output)]
        try:
            result = runner.main()
        finally:
            sys.argv = old_argv
            if old_git_dir is None:
                os.environ.pop("GIT_DIR", None)
            else:
                os.environ["GIT_DIR"] = old_git_dir
        for name, expected in hashes.items():
            assert (
                hashlib.sha256((stage / name).read_bytes()).hexdigest() == expected
            ), name
        provenance = {
            "original_baseline": BASELINE,
            "product_commit": product,
            "harness_commit": HARNESS,
            "original_harness_files_unchanged": True,
            "harness_sha256": hashes,
            "runner_exit_code": result,
        }
        (output / "remediation-provenance.json").write_text(
            json.dumps(provenance, indent=2) + "\n"
        )
        return result


if __name__ == "__main__":
    sys.exit(main())
