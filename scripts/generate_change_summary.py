import re


def summarize_diff(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    file_diffs = re.split(r'diff --git a/(.*?) b/', content)[1:]  # Split diff output
    summaries = []

    for i in range(0, len(file_diffs), 2):
        file_path = file_diffs[i].strip()
        diff = file_diffs[i+1]

        if 'deleted file mode' in diff:
            change_type = 'Deleted'
        elif 'new file mode' in diff:
            change_type = 'Added'
        elif '+class' in diff or '+def' in diff:
            change_type = 'Modified structure'
        elif '+' in diff or '-' in diff:
            change_type = 'Modified content'
        else:
            change_type = 'Changed'

        summaries.append(f"{file_path} – {change_type}")

    return summaries

summaries = summarize_diff("change-summary.txt")
for summary in summaries:
    print(summary)
