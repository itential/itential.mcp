#!/usr/bin/env python3
"""Generate CHANGELOG.md from git tags and commit messages."""

import subprocess
import sys


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def get_tags():
    try:
        output = run(["git", "tag", "--sort=-version:refname"])
        return [t for t in output.splitlines() if t]
    except subprocess.CalledProcessError:
        return []


def get_commits_between(start, end):
    ref = f"{start}..{end}" if start else end
    try:
        output = run(["git", "log", ref, "--pretty=format:%s", "--no-merges"])
        return [line for line in output.splitlines() if line]
    except subprocess.CalledProcessError:
        return []


def categorize(commits):
    features, fixes, other = [], [], []
    for msg in commits:
        lower = msg.lower()
        if any(lower.startswith(p) for p in ("feat", "add", "new")):
            features.append(msg)
        elif any(lower.startswith(p) for p in ("fix", "bug", "patch")):
            fixes.append(msg)
        else:
            other.append(msg)
    return features, fixes, other


def build_changelog(tags):
    lines = ["# Changelog\n"]
    for i, tag in enumerate(tags):
        prev = tags[i + 1] if i + 1 < len(tags) else None
        commits = get_commits_between(prev, tag)
        lines.append(f"## {tag}\n")
        features, fixes, rest = categorize(commits)
        if features:
            lines.append("### New Features\n")
            for c in features:
                lines.append(f"- {c}")
            lines.append("")
        if fixes:
            lines.append("### Bug Fixes\n")
            for c in fixes:
                lines.append(f"- {c}")
            lines.append("")
        if rest:
            lines.append("### Other Changes\n")
            for c in rest:
                lines.append(f"- {c}")
            lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    tags = get_tags()
    if not tags:
        print("# Changelog\n\nNo releases yet.")
        sys.exit(0)
    print(build_changelog(tags))
