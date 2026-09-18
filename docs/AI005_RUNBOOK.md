# AI-005 rollout and checks / 1.0 r1

The delivery is local only. Do not upload/deploy without the owner's next instruction. The r1 document workflow is not the complete live AI-005. No new keys/Render variables or paid Alice benchmark are needed for these tests.

## 1. Before deployment

Recheck main against the exact baseline c095bfb70bad5b1ba22cd9b1aeac1795a0b59c4c. Apply one PATCH or FULL, not both, without overlaying old JOB/AI final patches. Review the missing JOB-001 closure synchronization bundled here. Create and verify a real recovery point before migration; earlier Neon backup creation is not evidenced. Do not upload secrets, exports, runtime data, backups or caches. Run ordinary branch/PR CI including the new AI-005 step; old CI283 is not new evidence. Merge only after the required full new CI is green and the recovery prerequisite has been confirmed.

## 2. Technical acceptance

After deployment health/ready must have current=expected=20260917_0020, migrations.ok=true, persistent PostgreSQL and the exact new commit. /api/ai/status remains generation_available=false, mode=manual, reason=runtime_not_activated. No account/admin review switch is required for the ordinary private letter editor. The generator remains unavailable even if unrelated synthetic flags are on.

## 3. Document workflow

In an existing verified account, open a saved vacancy and the new letters link. Inspect the source preview and create with explicit confirmation. No profile is required for a blank manual draft; local composition needs confirmed facts. Fill subject/body/preferences, confirm and save version1. Refresh/relogin: it persists. Save unchanged: no version2. Material edit: version2, old version unchanged. Compare1/2 and export each TXT; texts and preferences must match. A download or local composition must never send an email or an application.

Open EXACTLY the same letter in two tabs before saving. Save tab1 then submit old tab2:409 with both texts and no overwrite. A stale deletion must also fail. A newly opened form must allow a new deliberate edit. Keep actual personal data out of screenshots/logs sent to the assistant.

## 4. Source/template behavior

Use a disposable test letter and profile facts. Select one or two facts and make a LOCAL proposal. It must be explicitly labelled non-AI; chosen source wording is preserved, no extra numbers or achievements appear, and current letter text is unchanged before confirmation. Review/edit then confirm; origin distinguishes unchanged template from user edits. Replayed pending proposal forms do not create duplicates. Rejecting deletes only the proposal. Change the profile after preparing a proposal: stale warning, no silent source replacement and no application of the old proposal; existing manual versions remain. Do not replace real profile contents just for testing.

RU/EN, short/full and tone all work; untranslated source excerpts are disclosed, not magically translated. No synthetic67/71 match score appears on real letters. The supplied offline model contract is NOT proof of live semantic writing quality; no paid call is authorized.

## 5. Privacy/deletion/regression

Download own privacy export privately; inspect cover_letters, cover_letter_versions and cover_letter_proposals. Do not send the archive. Delete an old non-current version with confirmation; its URL/export404 and the next version number is not reused. Current-version deletion alone must fail. Delete the whole letter only with confirmation; other letters, vacancy, profile and resume remain. While a letter exists, deleting its saved vacancy must fail with explanation; after explicit deletion of linked letters, ordinary JOB-001 deletion works again. Do not delete the real account; cascades are disposable-database tests.

Logout: private pages go to login and API401; another active account's detail/edit/compare/export/delete must be404. Without a second account record manual isolation NOT RUN, separately from automated tests. Verify JOB-001 notes/dedup/export, resume autosave/PDF, profile/search/dashboard/admin and existing closed AI003/004 histories. Review Render logs for unexpected500, database errors and leaked text/secrets. Keep public AI disabled.

## 6. Rollback and completion

A0020->0019 downgrade destroys ONLY letter tables and their contents. Preserve a verified populated backup, stop writes and coordinate application/schema rollback; old exact-head checks must not be hidden with stamp/reset. This is not an ordinary manual test. Real recovery remains operational work.

Record exact new CI and owner observations for the document tranche. Do NOT mark the entire planned AI-005 COMPLETE: approved general-input provider/consent/runtime integration and live-quality evidence are still required, as stated in AI005_SCOPE.md.
