#!/usr/bin/env python3
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

# -----------------------------
# Help / CLI
# -----------------------------

HELP_TEXT = """
git-release-summary.py

Structural, Git-first change summarizer.
No semantic assumptions. No hardcoded domain rules.

USAGE:
  git-release-summary.py [--json] [--summary] [--filestats]

FLAGS:
  --json           Emit JSON output (CI / automation friendly)
  --summary        Emit only TL;DR and final verdict
  --help           Show this help

STRUCTURAL METRICS (WHAT THEY MEAN):

- Avg path depth:
  Mean directory nesting level of affected files.
  Higher values indicate changes deeper in the repository structure,
  often corresponding to core or foundational components.

- Confidence:
  Strength of the structural signal derived from:
    - number of files changed
    - directory depth
    - domain spread (how many top-level directories are affected,
      e.g. changes touching `src/`, `apps/` etc.
      have wider impact than changes limited to a single directory)

  This does NOT evaluate correctness, logic, behavior, or runtime impact.

- Symbol-level analysis skipped:
  Indicates that files were deleted.
  Deleted files cannot be inspected for functions, classes, or signatures,
  so only structural (path-based) analysis is performed.

CRITICAL RISK EXPLANATIONS:

- Surface Area:
  Large number of files changed or removed.
  Increases regression risk and review complexity.

- Core Depth:
  Deeply nested paths affected.
  Indicates core internals being touched.

- Coupling Risk:
  High concentration of changes in one subtree.
  Suggests tightly coupled components or localized refactors.

- Change Dispersion:
  Many top-level domains affected.
  Indicates wide system impact.

All analysis is structure-only unless explicitly stated.
"""

ARGS = set(sys.argv[1:])

if "--help" in ARGS:
    print(HELP_TEXT)
    sys.exit(0)

OUTPUT_JSON = "--json" in ARGS
SUMMARY_ONLY = "--summary" in ARGS
LIST_FILES = "--filestats" in ARGS

# -----------------------------
# Git helpers
# -----------------------------

def git(cmd):
    return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()

def git_status_porcelain():
    """
    Returns list of (status, path)
    Uses -z to avoid quoted paths and parsing issues.
    """
    output = subprocess.check_output(
        ["git", "status", "--porcelain", "-z"],
        stderr=subprocess.DEVNULL
    )

    entries = output.decode().split("\0")
    results = []

    for entry in entries:
        if not entry:
            continue

        status = entry[:2].strip()
        path = entry[3:]
        results.append((status, path))

    return results


def git_deleted_files():
    return [p for s, p in git_status_porcelain() if s == "D"]

def git_modified_or_added_files():
    return [
        p for s, p in git_status_porcelain()
        if s in {"M", "A", "AM", "MM", "??"}
    ]

def git_file_actions():
    """
    Returns list of (path, action) tuples.
    Action ∈ {added, modified, deleted}
    """
    actions = []
    for status, path in git_status_porcelain():
        status = status.strip()

        if status == "D":
            actions.append((path, "deleted"))
        elif status in {"A", "??"}:
            actions.append((path, "added"))
        elif status in {"M", "AM", "MM"}:
            actions.append((path, "modified"))

    return actions


# -----------------------------
# Structural analysis
# -----------------------------

def path_depth(path):
    return len(Path(path).parts)

def file_extension(path):
    return Path(path).suffix or "<none>"

def top_domain(path):
    parts = Path(path).parts
    return parts[0] if len(parts) > 1 else "__root__"

def subtree(path, depth=3):
    return "/".join(Path(path).parts[:depth])

# -----------------------------
# Structural signature
# -----------------------------

def structural_signature(files):
    depths = [path_depth(f) for f in files]
    extensions = Counter(file_extension(f) for f in files)
    domains = Counter(top_domain(f) for f in files)
    subtrees = Counter(subtree(f) for f in files)

    avg_depth = round(sum(depths) / len(depths), 2) if depths else 0
    subtree_concentration = max(subtrees.values(), default=0)

    score = min(
        100,
        len(files) * 4 +
        len(domains) * 10 +
        len(extensions) * 5 +
        int(avg_depth * 3)
    )

    confidence = (
        "HIGH" if score >= 70 else
        "MEDIUM" if score >= 30 else
        "LOW"
    )

    return {
        "file_count": len(files),
        "avg_depth": avg_depth,
        "domains": dict(domains),
        "extensions": dict(extensions),
        "subtree_concentration": subtree_concentration,
        "score": score,
        "confidence": confidence,
    }

# -----------------------------
# Impact assessment (structural)
# -----------------------------

IMPACT_EXPLANATIONS = {
    "Surface Area": "Large number of files changed or removed",
    "Core Depth": "Deeply nested paths affected",
    "Coupling Risk": "High change concentration in a subtree",
    "Change Dispersion": "Many top-level domains affected",
}

def assess_impact(files):
    sig = structural_signature(files)

    return {
        "Surface Area": "CRITICAL" if sig["file_count"] > 50 else "NONE",
        "Core Depth": "CRITICAL" if sig["avg_depth"] >= 5 else "NONE",
        "Coupling Risk": "HIGH" if sig["subtree_concentration"] > 20 else "NONE",
        "Change Dispersion": "HIGH" if len(sig["domains"]) > 3 else "NONE",
    }

def merge_blocking_required(impact):
    return any(v == "CRITICAL" for v in impact.values())

# -----------------------------
# Area collapsing
# -----------------------------

def collapse_areas(files, depth=3):
    areas = defaultdict(int)
    for f in files:
        areas[subtree(f, depth)] += 1
    return dict(areas)

# -----------------------------
# JSON assembly
# -----------------------------

def build_json(deleted, modified, file_actions):
    combined = deleted + modified
    impact = assess_impact(combined)

    return {
        "summary": {
            "files_deleted": len(deleted),
            "files_modified_or_added": len(modified),
            "total_impacted": len(file_actions),
        },
        "files": [
            {"path": p, "action": a}
            for p, a in file_actions
        ] if LIST_FILES else None,
        "deleted": {
            "signature": structural_signature(deleted),
            "areas": collapse_areas(deleted),
        } if deleted else None,
        "modified": {
            "signature": structural_signature(modified),
            "areas": collapse_areas(modified),
            "impact": impact,
        } if modified else None,
        "verdict": {
            "merge_blocking": merge_blocking_required(impact),
            "critical_risks": [
                k for k, v in impact.items() if v == "CRITICAL"
            ],
        },
    }


# -----------------------------
# Markdown helpers
# -----------------------------

def print_section(title):
    print(f"\n## {title}")

def print_domain_breakdown(domains):
    print("- Domains affected:")
    for domain, count in sorted(domains.items()):
        print(f"  - `{domain}` ({count} files)")
    if "__root__" in domains:
        print("  - `__root__` indicates files located at repository root")

def print_metric_explanations():
    print("\n**Metric reference:**")
    print("- **Avg path depth**: Mean directory nesting of affected files.")
    print("  Higher values imply changes deeper in the system structure.")
    print("- **Confidence**: Strength of the structural signal based on volume, depth, and spread.")
    print("  This does NOT evaluate correctness, logic, or behavior.")
    print("- **Symbol-level analysis skipped**: Deleted files cannot be inspected for functions or classes.")

def format_area(area):
    return f"{area}/" if not Path(area).suffix else area

# -----------------------------
# Main
# -----------------------------

def main():
    deleted = git_deleted_files()
    modified = git_modified_or_added_files()
    combined = deleted + modified
    impact = assess_impact(combined)
    blocking = merge_blocking_required(impact)
    file_actions = git_file_actions()

    if OUTPUT_JSON:
        data = build_json(deleted, modified, file_actions)
        if SUMMARY_ONLY:
            data = {
                "summary": data["summary"],
                "verdict": data["verdict"],
            }
        print(json.dumps(data, indent=2))
        return

    # ---------- Markdown output ----------

    print("\n## 🔍 TL;DR")
    print(f"- Files deleted: {len(deleted)}")
    print(f"- Files modified/added: {len(modified)}")
    if LIST_FILES and not SUMMARY_ONLY:
            print_section("📄 Impacted Files")
            print(f"- Total files impacted: {len(file_actions)}\n")
            for path, action in sorted(file_actions):
                print(f"- {path} : {action}")

    if SUMMARY_ONLY:
        print_section("🧮 Merge Risk Verdict")
        print(
            "- Verdict: **🚫 MERGE BLOCKING**"
            if blocking else
            "- Verdict: **✅ NON-BLOCKING**"
        )
        return

    print_section("🧭 What Changed")

    if deleted:
        sig = structural_signature(deleted)
        print("\n### File Removals")
        print(f"- Files removed: {sig['file_count']}")
        print_domain_breakdown(sig["domains"])
        print(f"- Avg path depth: {sig['avg_depth']}")
        print(f"- Confidence: **{sig['confidence']}** (structure-only)")
        print("- Symbol-level analysis skipped (files deleted)")
        print_metric_explanations()

        print("\n**Affected areas:**")
        for area, count in collapse_areas(deleted).items():
            print(f"- `{format_area(area)}` ({count} files)")


    if modified:
        sig = structural_signature(modified)
        print("\n### Modified / Added Files")
        print(f"- Files changed: {sig['file_count']}")
        print_domain_breakdown(sig["domains"])
        print(f"- Avg path depth: {sig['avg_depth']}")
        print(f"- Confidence: **{sig['confidence']}** (structure-only)")
        print_metric_explanations()

        print("\n**Affected areas:**")
        for area, count in collapse_areas(modified).items():
            print(f"- `{format_area(area)}` ({count} files)")


        print("\n**Impact:**")
        for k, v in impact.items():
            print(f"- {k}: **{v}**")
            if v != "NONE":
                print(f"  ↳ {IMPACT_EXPLANATIONS[k]}")

    print_section("🧮 Merge Risk Verdict")
    print(
        "- Verdict: **🚫 MERGE BLOCKING**"
        if blocking else
        "- Verdict: **✅ NON-BLOCKING**"
    )

if __name__ == "__main__":
    main()
