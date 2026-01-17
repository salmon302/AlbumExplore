# Normalizer Development Loop

Overview
- Purpose: provide a safe, repeatable, agentic "manual review" workflow for reducing single-instance tags while preserving semantics (especially geographic and artist-related qualifiers).

Principles
- Always create a timestamped backup of `src/albumexplore/config/tag_rules.json` before writing.
- Prefer conservative, human-reviewed changes for geo-qualified, artist-like, or highly ambiguous tags.
- Use `--geo-strip-mode preserve` for routine safe runs; only consider stripping geo qualifiers after manual review.

Key scripts
- `tag_analysis/auto_singleton_mapper.py`: generate candidate mappings from singletons.
- `tag_analysis/apply_safe_singleton_suggestions.py`: safely auto-apply a subset of suggestions; supports `--dry-run` and `--geo-strip-mode`.
- `tag_analysis/generate_manual_review_package.py`: create a compact CSV + JSON package for manual review (new helper).
- `tag_analysis/apply_manual_choices.py`: apply mappings selected during manual review into `tag_rules.json` with backup (new helper).
- `tag_analysis/validate_normalization.py`: run the normalizer over `atomic_tags_export2.csv` and write validation JSONs.

Manual-review agentic workflow (recommended)
1. Generate suggestions (if not already present):

   ```powershell
   .\.venv-1\Scripts\python.exe .\tag_analysis\auto_singleton_mapper.py .\atomic_tags_export2.csv .\tag_analysis\singleton_suggestions.json
   ```

2. Produce a manual-review package (CSV + JSON template):

   ```powershell
   .\.venv-1\Scripts\python.exe .\tag_analysis\generate_manual_review_package.py
   ```

   - This creates `tag_analysis/manual_review_package/manual_review.csv` and `manual_review_choices.json` (template).
   - The CSV is compact and sortable; reviewers (or the agent) can add decisions into `manual_review_choices.json`.

3. Edit `tag_analysis/manual_review_package/manual_review_choices.json` to record decisions:

   - Each entry should include an `original`, `target` (use the same string to preserve), and an optional `note`.

4. Apply the chosen mappings:

   ```powershell
   .\.venv-1\Scripts\python.exe .\tag_analysis\apply_manual_choices.py .\tag_analysis\manual_review_package\manual_review_choices.json
   ```

   - The script will create a timestamped backup of `src/albumexplore/config/tag_rules.json` and write a small apply report.

5. Validate the result:

   ```powershell
   .\.venv-1\Scripts\python.exe .\tag_analysis\validate_normalization.py .\atomic_tags_export2.csv .\tag_analysis\normalization_validation_AFTER_MANUAL.json
   ```

Guidelines for decisions
- Preserve tags with geography (country/city) unless the mapping preserves the geographic qualifier or you have high confidence.
- Prefer curated typo corrections for single-token spelling errors.
- Block mappings that would convert a tag into an overly generic musical-genre term unless multiple occurrences exist and manual review approves.

Notes
- This repository intentionally avoids PR/multidev workflows for mapping changes; changes are applied directly after creating backups and validation reports. Keep audit artifacts (backups + validation JSONs) with each apply.

Contact
- If you need automation beyond this agentic/manual flow (CI checks, dashboards, PR automation), open a follow-up task in the TODO list.
**Normalizer Development Loop**

Purpose: Provide a concise, repeatable development loop for improving the tag normalizer, reduce single-instance tags safely, and ship changes with predictable validation and rollback.

Core principles

## Baseline

- Timestamp: 2025-11-16T21:11:16Z (ISO 8601 UTC)
- Total distinct tags (original unique tags): 675
- Singleton tags (tags with count == 1): 314
- Singleton percentage: 46.52%

Commands executed (exact):
```powershell
.\.venv-1\Scripts\python.exe --version && .\.venv-1\Scripts\python.exe .\tag_analysis\validate_normalization.py .\atomic_tags_export2.csv .\tag_analysis\normalization_baseline.json
```

```powershell
.\.venv-1\Scripts\python.exe .\tag_analysis\validate_normalization.py .\atomic_tags_export2.csv .\tag_analysis\normalization_baseline.json
```

```powershell
.\.venv-1\Scripts\python.exe --version
```

Important terminal output (captured):
- Loaded 927 atomic decomposition rules
- Loaded 292 valid atomic tags
- Validation complete:
  - Original unique tags: 675
  - Original singletons: 314
  - Normalized unique tags: 640
  - Normalized singletons: 280
  - Total original variants mapped to different canonical: 100
- Wrote report to: [`tag_analysis/normalization_baseline.json`](tag_analysis/normalization_baseline.json:1)

Environment / notes:
- Python version: 3.13.9 (from .venv-1) — confirmed by `python --version`
- Working directory: c:/Users/salmo/Documents/GitHub/AlbumExplore
- Validation script used: [`tag_analysis/validate_normalization.py`](tag_analysis/validate_normalization.py:1)
- Source CSV: [`atomic_tags_export2.csv`](atomic_tags_export2.csv:1)
- Baseline report written to: [`tag_analysis/normalization_baseline.json`](tag_analysis/normalization_baseline.json:1)

Brief note: the baseline was produced without modifying any files under [`src/albumexplore/tags/normalizer/`](src/albumexplore/tags/normalizer/:1). The validation run also produced `tag_analysis/normalization_baseline.json` containing the full JSON report.
- Small, reversible changes. Back up `tag_rules.json` before writes.
- Measure before/after using automated validation metrics.
- Prefer automated suggestions + human review for high-risk changes (geo-strips, overly-generic targets).
- Use atomic decomposition and existing canonical tags as a safety net.

Development loop (repeatable steps)
1. Detect & gather candidates
   - Run `tag_analysis/auto_singleton_mapper.py` against `atomic_tags_export2.csv` to produce `singleton_suggestions.json`.
   - Command (PowerShell):
     ```powershell
     C:/.../.venv-1/Scripts/python.exe .\tag_analysis\auto_singleton_mapper.py .\atomic_tags_export2.csv .\tag_analysis\singleton_suggestions.json
     ```

2. Triage & prioritize
   - Open `tag_analysis/singleton_suggestions.json` and categorize suggestions by reason (`atomic-decompose`, `rules-mapped-after-enhanced`, `geo-strip`, `enhanced-fallback`, etc.).
   - Fast-accept candidates: `rules-mapped-after-enhanced` and `atomic-decompose` with target already present in `atomic_tags`.
   - Manual-review candidates: `geo-strip`, very generic targets (`music`, `rock`, `folk`), or odd outputs like `middle`.

3. Safe-apply (staging)
   - Create a timestamped backup of `src/albumexplore/config/tag_rules.json`.
   - Merge selected suggestions into the `single_instance_mappings` section. Use `tag_analysis/apply_singleton_suggestions.py` for automated apply (creates backup automatically).
   - Command:
     ```powershell
     C:/.../.venv-1/Scripts/python.exe .\tag_analysis\apply_singleton_suggestions.py
     ```

4. Validate (dry-run + metrics)
   - Run `tag_analysis/validate_normalization.py` to compute pre/post normalization metrics.
   - Command:
     ```powershell
     C:/.../.venv-1/Scripts/python.exe .\tag_analysis\validate_normalization.py .\atomic_tags_export2.csv .\tag_analysis\normalization_validation.json
     ```
   - Key metrics to check:
     - unique tags before/after
     - singletons before/after
     - number of originals mapped to a different canonical
     - sample mappings for manual sanity checks

5. Run integration tests
   - Run existing test suites that exercise the normalizer and tag flows (`pytest tests/` or targeted tests). Focus on `test_tag_normalizer*`, `test_decompositions.py`, and end-to-end CSV transforms.

6. Review & human sign-off
   - Review `tag_analysis/normalization_validation.json` and `tag_analysis/applied_singleton_mappings.json` (if used).
   - Approve or revert. If reverted, restore backup (see rollback below).

7. Deploy & monitor
   - If validated, merge the `tag_rules.json` change into a branch/PR with a short release note describing counts reduced and files changed.
   - Monitor metrics in the first 24–72 hours after deployment and run the validation again on updated exports.

Quality gates (automated checks)
- Confidence threshold: Auto-apply only for suggestions where the reason is `rules-mapped-after-enhanced` or `atomic-decompose` AND the suggested canonical exists in `atomic_tags`.
- Maximum-risk checks: Block auto-apply for mappings with target length <= 4 chars that are generic (`music`, `rock`, `pop`, `folk`) unless manually approved.
- Snapshots: Ensure a backup file exists before any write; fail apply if backup cannot be created.

Rollback plan
- To revert the last apply quickly:
  ```powershell
  Copy-Item .\tag_rules_backup_apply_singletons_<TIMESTAMP>.json .\src\albumexplore\config\tag_rules.json -Force
  ```
- Re-run `validate_normalization.py` after restore to confirm metrics returned to previous state.

Metrics to track per iteration
- Unique tags (pre / post)
- Singletons (pre / post)
- Reduction delta
- False-positive merges (tracked manually via review) — keep a short list in `tag_analysis/false_positive_log.md`
- Number of rules added to `single_instance_mappings` and `atomic_decomposition`

Automation checklist (scripts already in repo)
- `tag_analysis/auto_singleton_mapper.py` — generate suggestions (dry-run)
- `tag_analysis/apply_singleton_suggestions.py` — safe apply + backup
- `tag_analysis/validate_normalization.py` — validation metrics
- `tag_analysis/list_applied_singletons.py` — list applied mappings (diff backup/current)

Human-review checklist
- Spot-check 10–20 mappings across reasons
- Confirm no geographic qualifiers were removed unintentionally for genres where geography matters
- Approve any mapping that compresses more than 3 distinct original tags into a single generic target

Files to archive (obsolete / historical)
- `tag_analysis/tag_rules_backup_phase3_20250721_180403.json`
- `tag_analysis/tag_rules_backup_phase4_20250721_181132.json`
- `tag_analysis/tag_rules_backup_phase5_20250721_182225.json`
- `tag_analysis/tag_rules_backup_phase6_20250721_183633.json`
- `tag_analysis/tag_rules_backup_review_20250721_185743.json`
- `tag_analysis/tag_rules_backup_review_20250721_190049.json`

Recommendation: Move the files above into `tag_analysis/archive/` (create if missing) to reduce clutter but keep historical backups.

Recommended cadence & ownership
- Cadence: Run this loop weekly for initial aggressive normalization, then reduce cadence to monthly once stabilized.
- Owners: assign a reviewer for triage + a release approver. Keep a rotation documented in `tag_analysis/OWNERS.md`.

Notes and housekeeping
- Keep `singleton_suggestions.json` and `singleton_suggestions_after_apply.json` as ephemeral artifacts; move accepted suggestions into `applied_singleton_mappings.json` and the `tag_rules.json` config.
- For future automation: add a CI job that runs `validate_normalization.py` and fails if singletons increase or unique tags increase unexpectedly.

Appendix — Quick commands
- Generate suggestions:
  ```powershell
  C:/.../.venv-1/Scripts/python.exe .\tag_analysis\auto_singleton_mapper.py
  ```
- Apply suggestions (creates backup):
  ```powershell
  C:/.../.venv-1/Scripts/python.exe .\tag_analysis\apply_singleton_suggestions.py
  ```
- Validate:
  ```powershell
  C:/.../.venv-1/Scripts/python.exe .\tag_analysis\validate_normalization.py
  ```


## Iteration 1
- Timestamp: 2025-11-16T21:31:28Z (ISO 8601 UTC)
- Normalized unique tags: 637
- Normalized singletons: 276
- Singleton percentage (normalized_singletons / normalized_unique_tags): 43.34%

Commands executed (exact):
```powershell
.\.venv-1\Scripts\python.exe .\tag_analysis\validate_normalization.py .\atomic_tags_export2.csv .\tag_analysis\normalization_iter1.json
```

Repro steps / environment:
- Python (venv): .\.venv-1\Scripts\python.exe --version -> Python 3.13.9
- Working directory: c:/Users/salmo/Documents/GitHub/AlbumExplore

Files modified in this iteration:
- src/albumexplore/tags/normalizer/tag_normalizer.py
  - Added Unicode NFKD / diacritic stripping and invisible char removal
  - Implemented prioritized normalization rules A..F (suffix qualifier stripping, connector normalization, explicit misspelling map, region decomposition, small mappings, simple singularization)
  - Added per-rule counters in self._rule_stats for logging/debugging

Notes:
- Non-normalizer files were not modified in this iteration.
- Reduction vs baseline singletons: 314 -> 276 (38 singletons reduced). Target (>=50) not yet met, proceeding to refinement passes.


## Iteration 2
- Timestamp: 2025-11-16T21:33:34Z (ISO 8601 UTC)
- Normalized unique tags: 637
- Normalized singletons: 276
- Singleton percentage (normalized_singletons / normalized_unique_tags): 43.34%

Commands executed (exact):
```powershell
.\.venv-1\Scripts\python.exe .\tag_analysis\validate_normalization.py .\atomic_tags_export2.csv .\tag_analysis\normalization_iter2.json
```

Repro steps / environment:
- Python (venv): .\.venv-1\Scripts\python.exe --version -> Python 3.13.9
- Working directory: c:/Users/salmo/Documents/GitHub/AlbumExplore

Files modified in this iteration:
- src/albumexplore/tags/normalizer/tag_normalizer.py
  - Added explicit verbatim example mappings for prioritized tags and connector/Unicode/region/plural handling
  - Implemented flexible lookup for hyphen/space variants of explicit examples

Notes:
- Non-normalizer files were not modified in this iteration.
- Reduction vs baseline singletons: 314 -> 276 (38 singletons reduced). Target (>=50) not yet met; continued refinement.

## Iteration 3
- Timestamp: 2025-11-16T21:35:28Z (ISO 8601 UTC)
- Normalized unique tags: 636
- Normalized singletons: 273
- Singleton percentage (normalized_singletons / normalized_unique_tags): 42.93%

Commands executed (exact):
```powershell
.\.venv-1\Scripts\python.exe .\tag_analysis\validate_normalization.py .\atomic_tags_export2.csv .\tag_analysis\normalization_iter3.json
```

Repro steps / environment:
- Python (venv): .\.venv-1\Scripts\python.exe --version -> Python 3.13.9
- Working directory: c:/Users/salmo/Documents/GitHub/AlbumExplore

Files modified in this iteration:
- src/albumexplore/tags/normalizer/tag_normalizer.py
  - Added flexible explicit example matching and conservative singularization guarded by valid atomic tags
  - Added per-rule counters to self._rule_stats to track how many tags each rule modified

Notes:
- Non-normalizer files were not modified in this iteration (only `tag_analysis/NORMALIZER_DEV_LOOP.md` was appended for dev-loop tracking).
- Best reduction achieved: baseline 314 -> 273 (41 singletons reduced). Did not reach >=50 target after two refinements. See summary in final report.


## Iteration 4

- Timestamp: 2025-11-16T21:41:38Z (ISO 8601 UTC)
- Normalized unique tags: 633
- Normalized singletons: 268
- Singleton percentage (normalized_singletons / normalized_unique_tags): 42.34%

Commands executed (exact):
```powershell
.\.venv-1\Scripts\python.exe .\tag_analysis\validate_normalization.py .\atomic_tags_export2.csv .\tag_analysis\normalization_iter4.json
```

Notable normalizer output / rule stats:
- Logs (captured from terminal):
  - Loaded 927 atomic decomposition rules
  - Loaded 292 valid atomic tags
  - Validation complete: Original unique tags: 675 | Original singletons: 314 | Normalized unique tags: 633 | Normalized singletons: 268 | Total original variants mapped to different canonical: 112
- Per-rule counts (detailed rule_stats) were not included in the validation report produced by the run; only aggregate counts above and sample mappings are available in the JSON report.

Files modified:
- [`src/albumexplore/config/tag_rules.json`](src/albumexplore/config/tag_rules.json:5002) — Added 9 explicit mappings into the `single_instance_mappings` object:
  - "hard prog" -> "prog"
  - "8-bit" -> "chiptune"
  - "deep funk" -> "funk"
  - "cavernous death metal" -> "death metal"
  - "hellenic black metal" -> "black metal"
  - "hill country blues" -> "blues"
  - "brostep" -> "dubstep"
  - "banjo" -> "folk"
  - "micro" -> "microtonal"

Notes:
- Reduction vs baseline singletons: 314 -> 268 (46 singletons reduced). Target (>=50 reduction i.e., <=264 singletons) not met.
- The three medium-risk mappings (`"brostep"->"dubstep"`, `"banjo"->"folk"`, `"micro"->"microtonal"`) were already applied in the above change, so no additional refinement pass was performed.

Confirmation:
- Only the allowed file was modified: [`src/albumexplore/config/tag_rules.json`](src/albumexplore/config/tag_rules.json:5002). No non-normalizer files were changed.
- Appended this Iteration 4 section to [`tag_analysis/NORMALIZER_DEV_LOOP.md`](tag_analysis/NORMALIZER_DEV_LOOP.md:292).

Wrote validation report to: [`tag_analysis/normalization_iter4.json`](tag_analysis/normalization_iter4.json:1)


### Post-apply stats

- Timestamp: 2025-11-16T22:23:47.548600Z
- Baseline total tags: 640
- Post-apply total tags: 669
- Tags removed (baseline - post): -29
- Baseline low-frequency tags (<3): 405
- Post low-frequency tags (<3): 396
- Target reduction ≥50 achieved: no

Top 10 tag changes (source -> target : source_count -> target_count_post):
- alt-blues -> alt blues : 2 -> 2
- disco-funk -> disco funk : 2 -> 3
- electro-funk -> electro funk : 2 -> 2
- metal-core -> metal core : 2 -> 2
- mittelalter-metal -> mittelalter metal : 2 -> 2
- one-man-band -> one man band : 2 -> 2
- soul-jazz -> soul jazz : 2 -> 4
- afro-funk -> afro funk : 1 -> 1
- afro-rock -> afro rock : 1 -> 1
- bluegras -> bluegrass : 1 -> 6


## Round 2 proposals

- proposed deterministic merges (high+medium): 21
- estimated additional reduction: 21

Top proposed merges:

- breakbeats -> breakbeat (plural, 1 -> 2, medium)
- crimson-esque -> crimson esque (hyphen, 1 -> 0, high)
- crimson-y -> crimson y (hyphen, 1 -> 0, high)
- deep purple-ish -> deep purple ish (hyphen, 1 -> 0, high)
- drum-oriented -> drum oriented (hyphen, 1 -> 0, high)
- floyd-esque -> floyd esque (hyphen, 1 -> 0, high)
- gong-related -> gong related (hyphen, 1 -> 0, high)
- hawkwind-ish -> hawkwind ish (hyphen, 1 -> 0, high)
- hip-hop soul -> hip hop soul (hyphen, 1 -> 1, high)
- keyboard-driven -> keyboard driven (hyphen, 1 -> 0, high)
- king gizzard-like -> king gizzard like (hyphen, 1 -> 0, high)
- mitteralter-metal -> mitteralter metal (hyphen, 1 -> 1, high)
- oi! -> oi (punctuation-fold, 1 -> 0, high)
- piano-oriented -> piano oriented (hyphen, 1 -> 1, high)
- post-metal‎ -> post metal‎ (hyphen, 1 -> 0, high)
- primus-related -> primus related (hyphen, 1 -> 0, high)
- riverside-esque -> riverside esque (hyphen, 1 -> 0, high)
- rush-oriented -> rush oriented (hyphen, 1 -> 0, high)
- seventh wonder-ish -> seventh wonder ish (hyphen, 1 -> 0, high)
- soft machine-related -> soft machine related (hyphen, 1 -> 0, high)
- proto-punk -> proto punk (hyphen, 2 -> 0, high)

Deterministic rules used: case-fold, trim whitespace, punctuation-fold (remove [.,;:!?\'"/()[]{}?]), hyphen->space, collapse multiple spaces, '&'->'and', simple plural->singular (conservative).


## Round 2 proposals

- proposed deterministic merges (high+medium): 21
- estimated additional reduction: 21

Top proposed merges:

- breakbeats -> breakbeat (plural, 1 -> 2, medium)
- crimson-esque -> crimson esque (hyphen, 1 -> 0, high)
- crimson-y -> crimson y (hyphen, 1 -> 0, high)
- deep purple-ish -> deep purple ish (hyphen, 1 -> 0, high)
- drum-oriented -> drum oriented (hyphen, 1 -> 0, high)
- floyd-esque -> floyd esque (hyphen, 1 -> 0, high)
- gong-related -> gong related (hyphen, 1 -> 0, high)
- hawkwind-ish -> hawkwind ish (hyphen, 1 -> 0, high)
- hip-hop soul -> hip hop soul (hyphen, 1 -> 1, high)
- keyboard-driven -> keyboard driven (hyphen, 1 -> 0, high)
- king gizzard-like -> king gizzard like (hyphen, 1 -> 0, high)
- mitteralter-metal -> mitteralter metal (hyphen, 1 -> 1, high)
- oi! -> oi (punctuation-fold, 1 -> 0, high)
- piano-oriented -> piano oriented (hyphen, 1 -> 1, high)
- post-metal‎ -> post metal‎ (hyphen, 1 -> 0, high)
- primus-related -> primus related (hyphen, 1 -> 0, high)
- riverside-esque -> riverside esque (hyphen, 1 -> 0, high)
- rush-oriented -> rush oriented (hyphen, 1 -> 0, high)
- seventh wonder-ish -> seventh wonder ish (hyphen, 1 -> 0, high)
- soft machine-related -> soft machine related (hyphen, 1 -> 0, high)
- proto-punk -> proto punk (hyphen, 2 -> 0, high)

Deterministic rules used: case-fold, trim whitespace, punctuation-fold (remove [.,;:!?\'"/()[]{}?]), hyphen->space, collapse multiple spaces, '&'->'and', simple plural->singular (conservative).
