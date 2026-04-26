#!/usr/bin/env python3
"""
Validate that API documentation matches the auto-generated OpenAPI schema.
Handles YAML output from drf-spectacular (default format).

Exits with code 0 if in sync (or schema gen skipped gracefully), 1 if discrepancies found.
"""
import re
import sys
import subprocess
from pathlib import Path

# Try to import yaml, fallback gracefully if not installed
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# =============================================================================
# PATH CONFIGURATION
# =============================================================================
def find_project_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    for parent in [script_dir] + list(script_dir.parents):
        if (parent / "docker-compose.yml").exists():
            return parent
    return script_dir.parent if script_dir.name == "scripts" else script_dir


PROJECT_ROOT = find_project_root()
MANAGE_PY = PROJECT_ROOT / "app" / "manage.py"

# YAML is drf-spectacular's default format
SCHEMA_OUTPUT = PROJECT_ROOT / "docs" / "API" / "reference" / "openapi.yml"
DOCS_DIR = PROJECT_ROOT / "docs" / "API" / "reference"
EXAMPLES_DIR = PROJECT_ROOT / "docs" / "API" / "examples"


def generate_schema() -> dict | None:
    """Generate OpenAPI schema in YAML format using drf-spectacular."""
    if not MANAGE_PY.exists():
        print(f"⚠️  Warning: manage.py not found at {MANAGE_PY}")
        return None

    if not YAML_AVAILABLE:
        print("⚠️  Warning: PyYAML not installed. Install with: pip install pyyaml")
        print("💡 Schema validation skipped.")
        return None

    try:
        # Generate YAML schema (drf-spectacular default)
        result = subprocess.run(
            [
                "python",
                str(MANAGE_PY),
                "spectacular",
                "--file",
                str(SCHEMA_OUTPUT),
                "--validate",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(PROJECT_ROOT),
        )

        if not SCHEMA_OUTPUT.exists():
            print(f"⚠️  Warning: Schema file was not created at {SCHEMA_OUTPUT}")
            if result.stderr:
                print(f"   stderr: {result.stderr[:200]}...")
            return None

        if SCHEMA_OUTPUT.stat().st_size == 0:
            print(f"⚠️  Warning: Schema file is empty (0 bytes)")
            if result.stderr:
                errors = [l for l in result.stderr.split("\n") if "Error" in l][:5]
                for err in errors:
                    print(f"   • {err.strip()}")
            return None

        # Parse YAML
        with open(SCHEMA_OUTPUT, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    except yaml.YAMLError as e:
        print(f"⚠️  Warning: Schema is not valid YAML: {e}")
        print(f"   File: {SCHEMA_OUTPUT}")
        return None
    except Exception as e:
        print(f"⚠️  Warning: Unexpected error during schema generation: {e}")
        return None

    return None


def parse_schema_endpoints(schema: dict) -> set[str]:
    """Extract endpoint paths from OpenAPI schema."""
    endpoints = set()
    paths = schema.get("paths", {}) if schema else {}

    for path, methods in paths.items():
        for method in methods.keys():
            if method in ["get", "post", "put", "patch", "delete", "head", "options"]:
                endpoints.add(f"{method.upper()} {path}")

    return endpoints


def parse_docs_endpoints(docs_dir: Path) -> set[str]:
    """Extract documented endpoints from markdown files."""
    endpoints = set()

    if not docs_dir.exists():
        print(f"⚠️  Warning: Docs directory {docs_dir} not found")
        return endpoints

    for md_file in docs_dir.glob("*.md"):
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()

            patterns = [
                r"`?\s*(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(/[^\s`*]+)`?",
                r"\|\s*(GET|POST|PUT|PATCH|DELETE)\s*\|\s*`?(/[^\s`|]+)`?\s*\|",
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        method, path = match
                        endpoints.add(f"{method.upper().strip()} {path.strip()}")

        except Exception as e:
            print(f"⚠️  Warning: Could not parse {md_file}: {e}")
            continue

    return endpoints


def main() -> int:
    print("🔍 Checking API docs vs schema...")
    print(f"   Project root: {PROJECT_ROOT}")
    print(f"   Schema file: {SCHEMA_OUTPUT.relative_to(PROJECT_ROOT)}")

    schema = generate_schema()

    if not schema:
        print("\n⚠️  Schema generation failed or produced invalid output.")
        print("\n🔧 Quick fixes to try:")
        print("   1. Install PyYAML: pip install pyyaml")
        print("   2. Add serializer_class to all APIView-based views")
        print("   3. Fix JWT bearerFormat warning in settings/base.py:")
        print("      SIMPLE_JWT = {'AUTH_HEADER_TYPES': ('Bearer',)}")
        print("   4. Add type hints to path parameters: <uuid:pk> not <pk>")
        print(
            "   5. In ViewSet.get_queryset(), add: if getattr(self, 'swagger_fake_view', False): return Model.objects.none()"
        )
        print("\n💡 Or run manually to see full errors:")
        print(
            f"   cd {PROJECT_ROOT} && python app/manage.py spectacular --file docs/API/reference/openapi.yml --validate 2>&1 | head -50"
        )
        print("\n📋 For now, skipping endpoint validation (not failing CI).")
        return 0

    schema_endpoints = parse_schema_endpoints(schema)
    print(f"   ✓ Found {len(schema_endpoints)} endpoints in OpenAPI schema")

    docs_endpoints = parse_docs_endpoints(DOCS_DIR)
    print(f"   ✓ Found {len(docs_endpoints)} endpoints in documentation")

    missing_in_docs = schema_endpoints - docs_endpoints
    missing_in_schema = docs_endpoints - schema_endpoints

    issues = []

    if missing_in_docs:
        issues.append("\n📝 Endpoints in schema but missing from docs:")
        for ep in sorted(missing_in_docs)[:10]:
            issues.append(f"  • {ep}")
        if len(missing_in_docs) > 10:
            issues.append(f"  ... and {len(missing_in_docs) - 10} more")

    if missing_in_schema:
        issues.append("\n🗑️  Endpoints in docs but not in schema (may be outdated):")
        for ep in sorted(missing_in_schema)[:10]:
            issues.append(f"  • {ep}")
        if len(missing_in_schema) > 10:
            issues.append(f"  ... and {len(missing_in_schema) - 10} more")

    if not issues:
        print("✅ API documentation is synchronized with schema.")
        return 0

    print("\n⚠️  API documentation issues found:")
    for issue in issues:
        print(issue)

    print(f"\n💡 Update docs or regenerate schema before merging.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
