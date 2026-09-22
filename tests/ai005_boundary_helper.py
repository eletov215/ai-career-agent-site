"""Copy exact AI-005 successor files for the inherited negative hash tests."""
import shutil
from scripts.check_ai005_package import CHANGES,NEW_RUNTIME,EVIDENCE

def copy_ai005_boundary(root,destination):
    if not (root/'docs/evidence/ai-005/change_boundary.json').is_file():return
    for rel in CHANGES|NEW_RUNTIME|EVIDENCE:
        target=destination/rel;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/rel,target)

    if (root/'docs/evidence/ai-005-r2/change_boundary.json').is_file():
        from scripts.check_ai005_r2_package import CHANGES as C2,NEW_RUNTIME as N2,EVIDENCE as E2
        for rel in C2|N2|E2:
            target=destination/rel;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(root/rel,target)


    if (root/'docs/evidence/legal-001/change_boundary.json').is_file():
        from scripts.legal001_boundary import EXPECTED_EXISTING
        for rel in set(EXPECTED_EXISTING) | {
            'docs/evidence/legal-001/change_boundary.json',
            'scripts/legal001_boundary.py',
        }:
            target=destination/rel;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(root/rel,target)
