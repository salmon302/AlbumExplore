#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compute post-round1 normalization stats using explicit merges from
tag_analysis/applied_merges_round1.json and atomic_tags_export2.csv.
Writes:
 - tag_analysis/post_round1_stats.json
 - tag_analysis/round1_comparison.json
 - appends a "Post-apply stats" section to tag_analysis/NORMALIZER_DEV_LOOP.md
 - tag_analysis/normalizer_post_run.log
"""
import csv
import json
import sys
import traceback
from collections import Counter, defaultdict
from datetime import datetime

ROOT = "."
CSV_PATH = "atomic_tags_export2.csv"
APPLIED_MERGES = "tag_analysis/applied_merges_round1.json"
BASELINE = "tag_analysis/normalization_baseline.json"
POST_STATS = "tag_analysis/post_round1_stats.json"
ROUND_COMP = "tag_analysis/round1_comparison.json"
DEV_LOOP = "tag_analysis/NORMALIZER_DEV_LOOP.md"
LOG = "tag_analysis/normalizer_post_run.log"

def load_csv(path):
    counts = {}
    try:
        with open(path, newline='', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                tag = row.get("Tag") or row.get("tag") or row.get("Tag,Count,Matching Count,Is Single,Filter State")
                if tag is None:
                    continue
                tag = tag.strip()
                # Some CSVs contain leading quotes/apostrophes in tag field (e.g. "'n'")
                tag = tag.strip()
                try:
                    cnt = int(row.get("Count", "").strip())
                except Exception:
                    # fallback: try splitting by comma if DictReader failed for header
                    try:
                        parts = row[list(row.keys())[0]].split(",")
                        tag = parts[0].strip().strip("'\"")
                        cnt = int(parts[1]) if len(parts) > 1 else 0
                    except Exception:
                        cnt = 0
                counts[tag] = counts.get(tag, 0) + cnt
    except Exception:
        raise
    return counts

def load_applied_merges(path):
    with open(path, encoding='utf-8') as fh:
        arr = json.load(fh)
    mapping = {}
    for e in arr:
        src = e.get("source_tag", "").strip()
        tgt = e.get("target_tag", "").strip()
        if src and tgt:
            mapping[src] = tgt
    return mapping, arr

def safe_write_json(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)

def append_dev_loop(md_path, summary_text):
    with open(md_path, "a", encoding="utf-8") as fh:
        fh.write("\n\n")
        fh.write("### Post-apply stats\n\n")
        fh.write(summary_text)
        fh.write("\n")

def main():
    start = datetime.utcnow().isoformat() + "Z"
    log_lines = []
    try:
        raw_counts = load_csv(CSV_PATH)
        log_lines.append(f"{datetime.utcnow().isoformat()}Z - Loaded {len(raw_counts)} unique tags from {CSV_PATH}")
        mapping, applied_list = load_applied_merges(APPLIED_MERGES)
        log_lines.append(f"{datetime.utcnow().isoformat()}Z - Loaded {len(mapping)} applied merges from {APPLIED_MERGES}")

        # Baseline metrics from CSV (pre-apply)
        baseline_unique = len(raw_counts)
        baseline_low_freq = sum(1 for v in raw_counts.values() if v < 3)

        # Apply deterministic merges: only explicit mapping entries
        final_counts = Counter()
        source_to_target = {}  # record which sources were remapped
        for tag, cnt in raw_counts.items():
            if tag in mapping:
                tgt = mapping[tag]
                final_counts[tgt] += cnt
                source_to_target[tag] = tgt
            else:
                final_counts[tag] += cnt

        post_total_tag_count = len(final_counts)
        total_tag_instances = sum(final_counts.values())
        number_of_low_freq_tags = sum(1 for v in final_counts.values() if v < 3)
        # top 20 tags
        top_20 = final_counts.most_common(20)
        top_20_list = [{"tag": t, "count": c} for t, c in top_20]
        low_freq_summary = {
            "freq_1": sum(1 for v in final_counts.values() if v == 1),
            "freq_2": sum(1 for v in final_counts.values() if v == 2)
        }

        # Prepare post_round1_stats.json
        post_stats = {
            "total_tag_count": post_total_tag_count,
            "total_tag_instances": total_tag_instances,
            "number_of_low_freq_tags_<3": number_of_low_freq_tags,
            "top_20_tags": top_20_list,
            "low_freq_tag_summary": low_freq_summary
        }
        safe_write_json(POST_STATS, post_stats)
        log_lines.append(f"{datetime.utcnow().isoformat()}Z - Wrote post-round1 stats to {POST_STATS}")

        # Baseline total tag count: prefer baseline normalized_unique_tags if present
        try:
            with open(BASELINE, encoding='utf-8') as fh:
                baseline_json = json.load(fh)
            baseline_total_tag_count = baseline_json.get("normalized_unique_tags", baseline_unique)
        except Exception:
            baseline_total_tag_count = baseline_unique

        tags_removed = baseline_total_tag_count - post_total_tag_count

        # Baseline low freq count: compute from raw CSV as tags with count <3
        baseline_low_freq_count = baseline_low_freq
        post_low_freq_count = number_of_low_freq_tags

        # list top 30 tags removed or merged (from applied merges).
        # We select applied merges where source existed in raw_counts.
        merged_entries = []
        for e in applied_list:
            src = e.get("source_tag", "").strip()
            if src in raw_counts:
                src_count = raw_counts.get(src, 0)
                tgt = e.get("target_tag", "").strip()
                tgt_count_post = final_counts.get(tgt, 0)
                merged_entries.append({
                    "source": src,
                    "target": tgt,
                    "source_count": src_count,
                    "target_count_post": tgt_count_post,
                    "reason": e.get("reason"),
                    "confidence": e.get("confidence")
                })
        # sort by source_count desc
        merged_entries.sort(key=lambda x: x["source_count"], reverse=True)
        merged_top_30 = merged_entries[:30]

        round_comp = {
            "baseline_total_tag_count": baseline_total_tag_count,
            "post_total_tag_count": post_total_tag_count,
            "tags_removed": tags_removed,
            "baseline_low_freq_count": baseline_low_freq_count,
            "post_low_freq_count": post_low_freq_count,
            "top_30_merged_or_removed": merged_top_30
        }
        safe_write_json(ROUND_COMP, round_comp)
        log_lines.append(f"{datetime.utcnow().isoformat()}Z - Wrote round comparison to {ROUND_COMP}")

        # Append a "Post-apply stats" section into NORMALIZER_DEV_LOOP.md
        achieved = "yes" if tags_removed >= 50 else "no"
        summary_lines = []
        summary_lines.append(f"- Timestamp: {datetime.utcnow().isoformat()}Z")
        summary_lines.append(f"- Baseline total tags: {baseline_total_tag_count}")
        summary_lines.append(f"- Post-apply total tags: {post_total_tag_count}")
        summary_lines.append(f"- Tags removed (baseline - post): {tags_removed}")
        summary_lines.append(f"- Baseline low-frequency tags (<3): {baseline_low_freq_count}")
        summary_lines.append(f"- Post low-frequency tags (<3): {post_low_freq_count}")
        summary_lines.append(f"- Target reduction ≥50 achieved: {achieved}")
        summary_lines.append("")
        summary_lines.append("Top 10 tag changes (source -> target : source_count -> target_count_post):")
        for me in merged_top_30[:10]:
            summary_lines.append(f"- {me['source']} -> {me['target']} : {me['source_count']} -> {me['target_count_post']}")
        append_dev_loop(DEV_LOOP, "\n".join(summary_lines))
        log_lines.append(f"{datetime.utcnow().isoformat()}Z - Appended Post-apply stats to {DEV_LOOP}")

        # Write runtime log
        with open(LOG, "w", encoding="utf-8") as fh:
            fh.write(f"Run started: {start}\n")
            fh.write(f"Run completed: {datetime.utcnow().isoformat()}Z\n\n")
            fh.write("Actions:\n")
            fh.write("\n".join(log_lines) + "\n\n")
            fh.write("Summary:\n")
            fh.write(json.dumps(round_comp, indent=2, ensure_ascii=False))
        print("COMPUTE_OK")
    except Exception:
        tb = traceback.format_exc()
        with open(LOG, "w", encoding="utf-8") as fh:
            fh.write(f"Run started: {start}\n")
            fh.write(f"Error at: {datetime.utcnow().isoformat()}Z\n\n")
            fh.write("Traceback:\n")
            fh.write(tb)
        print("COMPUTE_FAIL")
        raise

if __name__ == "__main__":
    main()