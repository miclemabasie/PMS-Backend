#!/usr/bin/env python3
"""
Check synchronization between .env.example and environment documentation.
Exits with code 0 if in sync, 1 if discrepancies are found.
Designed for pre-commit hooks, CI pipelines, and make docs-check.
"""
import re
import sys
from pathlib import Path

# Configurable paths (adjust if your project structure differs)
ENV_EXAMPLE_PATH = Path("app/.env.example")
ENV_DOCS_PATH = Path("docs/GETTING_STARTED/env-variables.md")


def parse_env_file(path: Path) -> set[str]:
    """Extract variable names from .env.example"""
    if not path.exists():
        print(f"⚠️  Warning: {path} not found. Skipping env parsing.")
        return set()

    vars_found = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Match: KEY= or KEY = value
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
            if match:
                vars_found.add(match.group(1))
    return vars_found


def parse_env_docs(path: Path) -> set[str]:
    """Extract variable names from markdown documentation."""
    if not path.exists():
        print(f"⚠️  Warning: {path} not found. Skipping docs parsing.")
        return set()

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    vars_found = set()

    # Match markdown table cells: | `VAR_NAME` | or | VAR_NAME |
    table_pattern = re.compile(r"\|\s*`?([A-Z_][A-Z0-9_]*)`?\s*\|")
    vars_found.update(table_pattern.findall(content))

    # Match inline code references: `VAR_NAME`
    inline_pattern = re.compile(r"`([A-Z_][A-Z0-9_]*)`")
    vars_found.update(inline_pattern.findall(content))

    # Filter out common false positives & short strings
    vars_found = {v for v in vars_found if len(v) > 3 and not v.startswith("_")}
    return vars_found


def main() -> int:
    print("🔍 Checking environment variable documentation sync...")

    env_vars = parse_env_file(ENV_EXAMPLE_PATH)
    doc_vars = parse_env_docs(ENV_DOCS_PATH)

    missing_in_docs = env_vars - doc_vars
    missing_in_env = doc_vars - env_vars

    if not missing_in_docs and not missing_in_env:
        print("✅ Environment variables are fully synchronized.")
        return 0

    print("\n⚠️  Synchronization issues found:")
    exit_code = 1

    if missing_in_docs:
        print("\n📝 Missing in documentation:")
        for var in sorted(missing_in_docs):
            print(f"  • {var}")

    if missing_in_env:
        print("\n📁 Missing in .env.example:")
        for var in sorted(missing_in_env):
            print(f"  • {var}")

    print(f"\n💡 Paths checked:")
    print(f"  • Code: {ENV_EXAMPLE_PATH}")
    print(f"  • Docs: {ENV_DOCS_PATH}")
    print("\nUpdate the missing references before merging.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
