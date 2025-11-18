"""
Django Starter Project Rename Command

Renames a Django project from ANY current name to ANY new name.
Perfect for starting new projects OR fixing a mistaken rename.

Usage:
    python manage.py rename_project <new_project_name> [--current-name CURRENT_NAME]

Examples:
    # Rename from default 'djangostarter' to 'myproject'
    python manage.py rename_project myproject

    # Rename from 'myproject' back to 'djangostarter'
    python manage.py rename_project djangostarter --current-name myproject

    # Rename from 'oldname' to 'newname' with cleanup
    python manage.py rename_project newname --current-name oldname --clean --force

This will:
    1. Rename the project directory from CURRENT_NAME to NEW_NAME
    2. Update ALL imports and references in ALL Python files
    3. Update Docker services, volumes, networks
    4. Update .env and .env.example
    5. Update docker-compose.yml
    6. Update Makefile
    7. Update pyproject.toml/setup.py if they exist
    8. Clean up pycache and staticfiles (optional)
"""

import os
import re
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = "Renames the Django project from any current name to any new name"

    def add_arguments(self, parser):
        parser.add_argument(
            "new_name",
            type=str,
            help="The new project name (must be a valid Python package name)",
        )
        parser.add_argument(
            "--current-name",
            "-c",
            type=str,
            default="djangostarter",
            help="The current project name (default: djangostarter)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Remove __pycache__, .pyc files, and staticfiles after rename",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force rename even if project name already exists",
        )
        parser.add_argument(
            "--no-input",
            action="store_true",
            help="Skip confirmation prompts",
        )

    def handle(self, *args, **options):
        new_name = options["new_name"].lower().strip()
        current_name = options["current_name"].lower().strip()
        clean = options["clean"]
        force = options["force"]
        no_input = options["no_input"]

        # Validate project names
        self._validate_project_name(new_name)
        self._validate_project_name(current_name)

        # Prevent renaming to same name
        if current_name == new_name:
            raise CommandError(
                f"Current name and new name are the same: '{current_name}'"
            )

        # Get project root
        project_root = Path(settings.BASE_DIR).parent  # Go up one level from /app
        old_project_path = project_root / "app" / current_name
        new_project_path = project_root / "app" / new_name

        # Check if current project directory exists
        if not old_project_path.exists():
            raise CommandError(
                f"Current project directory not found: {old_project_path}\n"
                f"Make sure you're in the correct directory and the current name is correct."
            )

        # Check if new project directory already exists
        if new_project_path.exists() and not force:
            raise CommandError(
                f"New project directory already exists: {new_project_path}\n"
                f"Use --force to overwrite."
            )

        self.stdout.write(f"📁 Project root: {project_root}")
        self.stdout.write(f"🔄 Renaming project from '{current_name}' to '{new_name}'")
        self.stdout.write("")

        if not force and not no_input:
            confirm = input(
                f"⚠️  This will rename the entire project. Are you sure? (yes/no): "
            )
            if confirm.lower() != "yes":
                raise CommandError("Rename cancelled.")

        # Track renamed files and directories
        renamed_count = 0
        updated_count = 0

        # ====================================================================
        # STEP 1: Rename the main project directory
        # ====================================================================
        self.stdout.write(
            f"📂 Renaming directory: {old_project_path} → {new_project_path}"
        )
        if new_project_path.exists():
            shutil.rmtree(new_project_path)
        shutil.move(str(old_project_path), str(new_project_path))
        renamed_count += 1

        # ====================================================================
        # STEP 2: Update manage.py
        # ====================================================================
        manage_py_path = project_root / "app" / "manage.py"
        if manage_py_path.exists():
            self._update_file_content(
                manage_py_path,
                [
                    (f"{current_name}.settings", f"{new_name}.settings"),
                    (f'"{current_name}.settings', f'"{new_name}.settings'),
                    (f"'{current_name}.settings", f"'{new_name}.settings"),
                ],
            )
            updated_count += 1
            self.stdout.write(f"📝 Updated: app/manage.py")

        # ====================================================================
        # STEP 3: Update WSGI/ASGI/Celery files
        # ====================================================================
        for file_name in ["wsgi.py", "asgi.py", "celery.py"]:
            file_path = new_project_path / file_name
            if file_path.exists():
                self._update_file_content(
                    file_path,
                    [
                        (f"{current_name}.settings", f"{new_name}.settings"),
                        (f'"{current_name}.settings', f'"{new_name}.settings'),
                        (f"'{current_name}.settings", f"'{new_name}.settings"),
                    ],
                )
                updated_count += 1
                self.stdout.write(f"📝 Updated: app/{new_name}/{file_name}")

        # ====================================================================
        # STEP 4: Update settings files
        # ====================================================================
        settings_dir = new_project_path / "settings"
        if settings_dir.exists():
            for settings_file in settings_dir.glob("*.py"):
                if settings_file.name != "__init__.py":
                    self._update_file_content(
                        settings_file,
                        [
                            (
                                f"ROOT_URLCONF = '{current_name}.urls'",
                                f"ROOT_URLCONF = '{new_name}.urls'",
                            ),
                            (
                                f"WSGI_APPLICATION = '{current_name}.wsgi.application'",
                                f"WSGI_APPLICATION = '{new_name}.wsgi.application'",
                            ),
                            (f"'{current_name}.',", f"'{new_name}',"),
                            (f"'{current_name}.users'", f"'{new_name}.users'"),
                            (f"'{current_name}.core'", f"'{new_name}.core'"),
                            (
                                f"'{current_name}.notifications'",
                                f"'{new_name}.notifications'",
                            ),
                        ],
                    )
            updated_count += 1
            self.stdout.write(f"📝 Updated: app/{new_name}/settings/")

        # ====================================================================
        # STEP 5: Update urls.py
        # ====================================================================
        urls_path = new_project_path / "urls.py"
        if urls_path.exists():
            self._update_file_content(
                urls_path,
                [
                    (f"from {current_name}", f"from {new_name}"),
                    (f"import {current_name}", f"import {new_name}"),
                ],
            )
            updated_count += 1
            self.stdout.write(f"📝 Updated: app/{new_name}/urls.py")

        # ====================================================================
        # STEP 6: Update ALL Python files recursively
        # ====================================================================
        self.stdout.write("\n🔍 Scanning for imports to update...")

        patterns = [
            (f"from {current_name}", f"from {new_name}"),
            (f"import {current_name}", f"import {new_name}"),
            (f"'{current_name}.", f"'{new_name}."),
            (f'"{current_name}.', f'"{new_name}.'),
            (f"`{current_name}.", f"`{new_name}."),
            (f"({current_name}.", f"({new_name}."),
            (f" {current_name}.", f" {new_name}."),
            (f":{current_name}.", f":{new_name}."),
        ]

        python_files = []
        for ext in ["*.py", "*.pyi", "*.pyx"]:
            python_files.extend(project_root.rglob(ext))

        exclude_dirs = [
            ".git",
            "__pycache__",
            "venv",
            "env",
            ".venv",
            "node_modules",
            "migrations",
            "staticfiles",
            "mediafiles",
            "app/staticfiles",
            "app/mediafiles",
        ]

        for file_path in python_files:
            # Skip excluded directories
            if any(excl in str(file_path) for excl in exclude_dirs):
                continue

            # Skip the current script itself
            if file_path.name == "rename_project.py":
                continue

            try:
                self._update_file_content(file_path, patterns)
                updated_count += 1
                self.stdout.write(
                    f"  ✅ {file_path.relative_to(project_root)}", ending="\r"
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠️  Could not update {file_path}: {e}")
                )

        self.stdout.write("")

        # ====================================================================
        # STEP 7: Update docker-compose.yml
        # ====================================================================
        docker_compose_path = project_root / "docker-compose.yml"
        if docker_compose_path.exists():
            docker_patterns = [
                (f"POSTGRES_DB={current_name}", f"POSTGRES_DB={new_name}"),
                (f"{current_name}-network", f"{new_name}-network"),
                (f"postgres_data", f"{new_name}_postgres_data"),
                (f"static_volume", f"{new_name}_static_volume"),
                (f"media_volume", f"{new_name}_media_volume"),
                (f"elastic_data", f"{new_name}_elastic_data"),
                (f"container_name: redis", f"container_name: {new_name}-redis"),
                (f"SITE_NAME={current_name}", f"SITE_NAME={new_name}"),
            ]
            self._update_file_content(docker_compose_path, docker_patterns)
            updated_count += 1
            self.stdout.write(f"📝 Updated: docker-compose.yml")

        # ====================================================================
        # STEP 8: Update .env and .env.example
        # ====================================================================
        env_path = project_root / "app" / ".env"
        env_example_path = project_root / "app" / ".env.example"

        env_patterns = [
            (f"POSTGRES_DB={current_name}", f"POSTGRES_DB={new_name}"),
            (f"SITE_NAME={current_name}", f"SITE_NAME={new_name}"),
        ]

        if env_path.exists():
            self._update_file_content(env_path, env_patterns)
            updated_count += 1
            self.stdout.write(f"📝 Updated: app/.env")

        if env_example_path.exists():
            self._update_file_content(env_example_path, env_patterns)
            updated_count += 1
            self.stdout.write(f"📝 Updated: app/.env.example")

        # ====================================================================
        # STEP 9: Update README.md
        # ====================================================================
        readme_path = project_root / "README.md"
        if readme_path.exists():
            self._update_file_content(
                readme_path,
                [
                    (f"# {current_name}", f"# {new_name}"),
                    (f"# {current_name.capitalize()}", f"# {new_name.capitalize()}"),
                    (f"{current_name}-network", f"{new_name}-network"),
                    (current_name, new_name),  # Replace all occurrences
                ],
            )
            updated_count += 1
            self.stdout.write(f"📝 Updated: README.md")

        # ====================================================================
        # STEP 10: Update Makefile
        # ====================================================================
        makefile_path = project_root / "Makefile"
        if makefile_path.exists():
            self._update_file_content(
                makefile_path,
                [
                    (f"PROJECT_NAME ?= {current_name}", f"PROJECT_NAME ?= {new_name}"),
                    (f"docker-compose.yml", f"docker-compose.yml"),  # Leave as is
                    (current_name, new_name),
                ],
            )
            updated_count += 1
            self.stdout.write(f"📝 Updated: Makefile")

        # ====================================================================
        # STEP 11: Update pyproject.toml / setup.py
        # ====================================================================
        pyproject_path = project_root / "pyproject.toml"
        if pyproject_path.exists():
            self._update_file_content(
                pyproject_path,
                [
                    (f'name = "{current_name}"', f'name = "{new_name}"'),
                ],
            )
            updated_count += 1
            self.stdout.write(f"📝 Updated: pyproject.toml")

        setup_py_path = project_root / "setup.py"
        if setup_py_path.exists():
            self._update_file_content(
                setup_py_path,
                [
                    (f"name='{current_name}'", f"name='{new_name}'"),
                    (f'name="{current_name}"', f'name="{new_name}"'),
                ],
            )
            updated_count += 1
            self.stdout.write(f"📝 Updated: setup.py")

        # ====================================================================
        # STEP 12: Clean up (optional)
        # ====================================================================
        if clean:
            self.stdout.write("\n🧹 Cleaning up...")

            # Remove all __pycache__ directories
            pycache_count = 0
            for pycache in project_root.rglob("__pycache__"):
                shutil.rmtree(pycache, ignore_errors=True)
                pycache_count += 1
            self.stdout.write(f"  ✅ Removed {pycache_count} __pycache__ directories")

            # Remove all .pyc files
            pyc_count = 0
            for pyc in project_root.rglob("*.pyc"):
                pyc.unlink()
                pyc_count += 1
            self.stdout.write(f"  ✅ Removed {pyc_count} .pyc files")

            # Remove staticfiles directory
            staticfiles_path = project_root / "app" / "staticfiles"
            if staticfiles_path.exists():
                shutil.rmtree(staticfiles_path, ignore_errors=True)
                self.stdout.write(f"  ✅ Removed staticfiles directory")

        # ====================================================================
        # STEP 13: Final instructions
        # ====================================================================
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Project successfully renamed from '{current_name}' to '{new_name}'!"
            )
        )
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write("")
        self.stdout.write("📋 Next steps:")
        self.stdout.write(
            f"  1. Update your database connection string (if not using Docker):"
        )
        self.stdout.write(f"     POSTGRES_DB={new_name}")
        self.stdout.write(f"  2. Rebuild Docker containers:")
        self.stdout.write(f"     docker-compose down -v")
        self.stdout.write(f"     docker-compose up --build")
        self.stdout.write(f"  3. If you're using Git, commit the changes:")
        self.stdout.write(f"     git add -A")
        self.stdout.write(
            f"     git commit -m 'Renamed project from {current_name} to {new_name}'"
        )
        self.stdout.write("")
        self.stdout.write("📚 Statistics:")
        self.stdout.write(f"  📁 Directories renamed: {renamed_count}")
        self.stdout.write(f"  📄 Files updated: {updated_count}")
        self.stdout.write("")

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _validate_project_name(self, name):
        """Validate that the project name is a valid Python package name."""
        if not name:
            raise CommandError("Project name cannot be empty.")

        if not re.match(r"^[a-z][a-z0-9_]+$", name):
            raise CommandError(
                "Project name must be a valid Python package name:\n"
                "  - Start with a letter\n"
                "  - Only lowercase letters, numbers, and underscores\n"
                "  - No spaces or hyphens\n"
                f"  '{name}' is invalid."
            )

    def _update_file_content(self, file_path, replacements):
        """Replace text in a file with multiple patterns."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            for old, new in replacements:
                content = content.replace(old, new)

            if content != original_content:
                with open(file_path, "w", encoding="utf-8", newline="") as f:
                    f.write(content)
                return True
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"  ⚠️  Error updating {file_path}: {e}")
            )
        return False
