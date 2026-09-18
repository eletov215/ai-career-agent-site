"""Copy exact AI-005 successor files for the inherited negative hash tests."""
import shutil
from scripts.check_ai005_package import CHANGES,NEW_RUNTIME,EVIDENCE

def copy_ai005_boundary(root,destination):
    if not (root/'docs/evidence/ai-005/change_boundary.json').is_file():return
    for rel in CHANGES|NEW_RUNTIME|EVIDENCE:
        target=destination/rel;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/rel,target)
