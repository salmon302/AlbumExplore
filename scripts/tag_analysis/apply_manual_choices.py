from pathlib import Path
import json
import shutil
from datetime import datetime
import sys
import argparse


def backup_file(src: Path, dst_dir: Path) -> Path:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dst = dst_dir / f"tag_rules_backup_manual_apply_{ts}.json"
    shutil.copy2(src, dst)
    return dst


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main(dry_run: bool = False):
    base = Path(__file__).resolve().parent
    default_choices = base / "manual_review_package" / "manual_review_choices.json"
    choices_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_choices

    if not choices_path.exists():
        print(f"Choices file not found: {choices_path}")
        return

    choices = load_json(choices_path)
    if not isinstance(choices, list):
        print("Choices file must be a JSON list of {original,target,note}")
        return

    rules_path = Path.cwd() / "src" / "albumexplore" / "config" / "tag_rules.json"
    if not rules_path.exists():
        rules = {}
        # ensure parent exists when we actually write
    else:
        rules = load_json(rules_path)

    backup_dir = Path.cwd()
    mapping = rules.get("single_instance_mappings") or {}
    applied = []
    skipped = []

    for entry in choices:
        original = entry.get("original") if isinstance(entry, dict) else None
        target = entry.get("target") if isinstance(entry, dict) else None
        if not original:
            skipped.append({"entry": entry, "reason": "missing original"})
            continue
        if target is None or (isinstance(target, str) and target.strip() == ""):
            skipped.append({"original": original, "reason": "no target specified"})
            continue
        if mapping.get(original) == target:
            skipped.append({"original": original, "reason": "already mapped"})
            continue
        mapping[original] = target
        applied.append({"original": original, "target": target})

    # If dry-run, do not write files; simulate backup and write a dry-run report
    if dry_run:
        simulated_backup = str(backup_dir / "(dry-run)tag_rules_backup_manual_apply.json")
        report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "choices_file": str(choices_path),
            "backup_file": simulated_backup,
            "applied_count": len(applied),
            "skipped_count": len(skipped),
            "applied": applied,
            "skipped": skipped,
            "dry_run": True,
        }

        out = base / "manual_review_package" / f"manual_apply_report_dryrun_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"Dry-run: would apply {len(applied)} mappings, would skip {len(skipped)}. Report: {out}")
        return

    # Non-dry-run: create backup, ensure directories, write mapping
    if rules_path.exists():
        backup = backup_file(rules_path, backup_dir)
        print(f"Created backup: {backup}")

    # ensure parent exists
    rules_path.parent.mkdir(parents=True, exist_ok=True)
    rules["single_instance_mappings"] = mapping

    rules_path.write_text(json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")

    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "choices_file": str(choices_path),
        "backup_file": str(backup) if 'backup' in locals() else None,
        "applied_count": len(applied),
        "skipped_count": len(skipped),
        "applied": applied,
        "skipped": skipped,
    }

    out = base / "manual_review_package" / f"manual_apply_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Applied {len(applied)} mappings, skipped {len(skipped)}. Report: {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("choices", nargs='?', help="Path to manual choices JSON")
    parser.add_argument("--dry-run", action='store_true', help="Simulate apply without writing files")
    args = parser.parse_args()

    # If a choices path is provided, place it as sys.argv[1] for backwards compatibility
    if args.choices:
        sys.argv[1] = args.choices

    main(dry_run=args.dry_run)
