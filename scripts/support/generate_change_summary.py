#!/usr/bin/env python3
"""
Git-native change summary generator.

Uses:
- git diff --numstat
- git diff --name-status

Accurate for large releases.
"""

import subprocess
from collections import defaultdict


def run_git(cmd):
    return subprocess.check_output(cmd, text=True).strip().splitlines()

def get_numstat():
    """
    Returns:
      { file_path: (added, deleted) }

    """
    stats = {}
    for line in run_git(["git", "diff", "--numstat"]):
        added, deleted, path = line.split("\t", 2)
        stats[path] = (
            int(added) if added.isdigit() else 0,
            int(deleted) if deleted.isdigit() else 0,
        )
    return stats

def get_name_status():
    """
    Returns:
      { file_path: status }

    """
    status_map = {}
    for line in run_git(["git", "diff", "--name-status"]):
        parts = line.split("\t")
        status = parts[0]

        if status.startswith("R"):  # rename
            _old, new = parts[1], parts[2]
            status_map[new] = "Renamed"
        else:
            status_map[parts[1]] = {
                "A": "Added",
                "M": "Modified",
                "D": "Deleted",
            }.get(status, "Changed")

    return status_map

def generate_summary():
    numstat = get_numstat()
    status_map = get_name_status()

    summary = []
    totals = defaultdict(int)

    for path, change_type in sorted(status_map.items()):
        added, deleted = numstat.get(path, (0, 0))

        summary.append({
            "file": path,
            "type": change_type,
            "added": added,
            "deleted": deleted,
        })

        totals["files"] += 1
        totals["added"] += added
        totals["deleted"] += deleted
        totals[change_type] += 1

    return summary, totals

def print_markdown(summary, totals):
    print("\n📦 **File-level summary**\n")

    for item in summary:
        line = f"• `{item['file']}` — {item['type']}"
        if item["added"] or item["deleted"]:
            line += f" (+{item['added']} / -{item['deleted']})"
        print(line)

    print("\n📊 **Change breakdown**\n")
    print(f"- Files changed: {totals['files']}")
    print(f"- Insertions: +{totals['added']}")
    print(f"- Deletions: -{totals['deleted']}\n")

    for key in ["Added", "Modified", "Deleted", "Renamed"]:
        if totals[key]:
            print(f"- {key}: {totals[key]}")

if __name__ == "__main__":
    summary, totals = generate_summary()
    print_markdown(summary, totals)


# import re

# def summarize_diff(file_path):
#     with open(file_path, 'r') as f:
#         content = f.read()

#     file_diffs = re.split(r'diff --git a/(.*?) b/', content)[1:]  # Split diff output
#     summaries = []

#     for i in range(0, len(file_diffs), 2):
#         file_path = file_diffs[i].strip()
#         diff = file_diffs[i+1]

#         if 'deleted file mode' in diff:
#             change_type = 'Deleted'
#         elif 'new file mode' in diff:
#             change_type = 'Added'
#         elif '+class' in diff or '+def' in diff:
#             change_type = 'Modified structure'
#         elif '+' in diff or '-' in diff:
#             change_type = 'Modified content'
#         else:
#             change_type = 'Changed'

#         summaries.append(f"{file_path} – {change_type}")

#     return summaries

# summaries = summarize_diff("change-summary.txt")
# for summary in summaries:
#     print(summary)
