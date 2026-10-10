"""Copy exact AI-005 successor files for the inherited negative hash tests."""
import shutil
from scripts.check_ai005_package import CHANGES,NEW_RUNTIME,EVIDENCE


def copy_job002_boundary(root, destination):
    if not (root/'docs/evidence/job-002/change_boundary.json').is_file():
        return
    from scripts.check_job002_package import (EVIDENCE as JOB002_EVIDENCE,
        EXISTING_RUNTIME, GUARD_CHANGES, NEW_RUNTIME as JOB002_NEW)
    for rel in EXISTING_RUNTIME | GUARD_CHANGES | JOB002_NEW | {
            JOB002_EVIDENCE, 'scripts/check_job002_package.py'}:
        target=destination/rel;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/rel,target)
    job003 = root/'docs/evidence/job-003/change_boundary.json'
    if job003.is_file():
        from scripts.check_job003_package import (AUTHORIZED_GUARD_CHANGES,
            NEW_RUNTIME as JOB003_NEW, REVIEWED_RUNTIME_CHANGES)
        for rel in REVIEWED_RUNTIME_CHANGES | AUTHORIZED_GUARD_CHANGES | JOB003_NEW | {
                'docs/evidence/job-003/change_boundary.json'}:
            target=destination/rel;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(root/rel,target)
    job004 = root/'docs/evidence/job-004/change_boundary.json'
    if job004.is_file():
        from scripts.check_job004_package import NEW_RUNTIME as JOB004_NEW, REVIEWED_RUNTIME as JOB004_REVIEWED, SUPPORT as JOB004_SUPPORT
        for rel in JOB004_REVIEWED | JOB004_NEW | JOB004_SUPPORT | {
                'docs/evidence/job-004/change_boundary.json', 'scripts/check_job004_package.py'}:
            target=destination/rel;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(root/rel,target)
    # The later M04B candidate is a separate successor: negative tests of
    # older packages must copy the entire attested 0024 boundary, not a partial
    # mix of 0024 guards with accepted 0023 files. A missing manifest retains
    # the old 0023 fixture unchanged.
    from scripts.ai004_m04b_successor import (
        MANIFEST_PATH, NEW_FILES, PREDECESSOR_HASHES, PRESERVED_FILES,
        successor_exists,
    )
    if successor_exists(root):
        for relative in (
            set(PREDECESSOR_HASHES) | NEW_FILES | PRESERVED_FILES | {MANIFEST_PATH}
        ):
            destination_path = destination / relative
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / relative, destination_path)

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

    if (root/'docs/evidence/ai-005-live-qa-001/change_boundary.json').is_file():
        from scripts.check_ai005_live_qa_boundary import (CHANGES as LIVE_CHANGES,
            DIAGNOSTIC_EVIDENCE, EVIDENCE as LIVE_EVIDENCE, GROUNDING_EVIDENCE,
            PROMPT_EVIDENCE)
        for rel in LIVE_CHANGES | {LIVE_EVIDENCE, DIAGNOSTIC_EVIDENCE, PROMPT_EVIDENCE,
                                   GROUNDING_EVIDENCE,
                                   'scripts/check_ai005_live_qa_boundary.py', 'domain/ai.py'}:
            target=destination/rel;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(root/rel,target)

    copy_job002_boundary(root, destination)
