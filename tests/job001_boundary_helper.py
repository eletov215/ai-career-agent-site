"""Copy the explicit successor scope for earlier negative boundary tests."""
from pathlib import Path
import shutil
from scripts.check_job001_package import CHANGES, NEW_RUNTIME, EVIDENCE


def copy_job001_boundary(root: Path, destination: Path):
    if not (root/'docs/evidence/job-001/change_boundary.json').is_file():
        return
    for relative in CHANGES | NEW_RUNTIME | EVIDENCE:
        target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/relative,target)

    from tests.ai005_boundary_helper import copy_ai005_boundary
    copy_ai005_boundary(root, destination)
