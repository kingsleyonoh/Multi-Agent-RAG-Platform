"""Batch 17 — Docker + Deployment RED phase tests.

Tests for:
  - docker-compose.prod.yml structure validation
  - Dockerfile multi-stage build validation
  - Deploy script structure validation
"""

import os

import pytest


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


# ── Docker Compose Validation ────────────────────────────────────────


class TestDockerCompose:
    """Tests for docker-compose.prod.yml."""

    def test_file_exists(self):
        """docker-compose.prod.yml must exist."""
        path = os.path.join(PROJECT_ROOT, "docker-compose.prod.yml")
        assert os.path.isfile(path), "docker-compose.prod.yml not found"

    def test_has_app_service(self):
        """Must define an 'app' service."""
        import yaml

        path = os.path.join(PROJECT_ROOT, "docker-compose.prod.yml")
        with open(path) as f:
            compose = yaml.safe_load(f)
        assert "app" in compose["services"]

    def test_has_postgres_service(self):
        """Must define a 'postgres' service."""
        import yaml

        path = os.path.join(PROJECT_ROOT, "docker-compose.prod.yml")
        with open(path) as f:
            compose = yaml.safe_load(f)
        assert "postgres" in compose["services"]

    def test_has_neo4j_service(self):
        """Must define a 'neo4j' service."""
        import yaml

        path = os.path.join(PROJECT_ROOT, "docker-compose.prod.yml")
        with open(path) as f:
            compose = yaml.safe_load(f)
        assert "neo4j" in compose["services"]

    def test_has_redis_service(self):
        """Must define a 'redis' service."""
        import yaml

        path = os.path.join(PROJECT_ROOT, "docker-compose.prod.yml")
        with open(path) as f:
            compose = yaml.safe_load(f)
        assert "redis" in compose["services"]

    def test_app_has_healthcheck(self):
        """App service must have a healthcheck."""
        import yaml

        path = os.path.join(PROJECT_ROOT, "docker-compose.prod.yml")
        with open(path) as f:
            compose = yaml.safe_load(f)
        assert "healthcheck" in compose["services"]["app"]


# ── Dockerfile Validation ────────────────────────────────────────────


class TestDockerfile:
    """Tests for Dockerfile."""

    def test_file_exists(self):
        """Dockerfile must exist."""
        path = os.path.join(PROJECT_ROOT, "Dockerfile")
        assert os.path.isfile(path), "Dockerfile not found"

    def test_multi_stage_build(self):
        """Dockerfile must use multi-stage build (multiple FROM)."""
        path = os.path.join(PROJECT_ROOT, "Dockerfile")
        with open(path) as f:
            content = f.read()
        from_count = content.upper().count("\nFROM ")
        # Account for first FROM at start of file
        if content.upper().startswith("FROM "):
            from_count += 1
        assert from_count >= 2, "Dockerfile must have at least 2 FROM stages"

    def test_non_root_user(self):
        """Dockerfile must switch to a non-root user."""
        path = os.path.join(PROJECT_ROOT, "Dockerfile")
        with open(path) as f:
            content = f.read()
        assert "USER " in content, "Dockerfile must define a non-root USER"


# ── Deploy Script Validation ─────────────────────────────────────────


class TestDeployScript:
    """Tests for scripts/deploy.sh."""

    def test_file_exists(self):
        """deploy.sh must exist."""
        path = os.path.join(PROJECT_ROOT, "scripts", "deploy.sh")
        assert os.path.isfile(path), "scripts/deploy.sh not found"

    def test_has_docker_compose_command(self):
        """Script must reference docker compose."""
        path = os.path.join(PROJECT_ROOT, "scripts", "deploy.sh")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "docker" in content.lower(), "Script must use docker commands"

    def test_has_error_handling(self):
        """Script must include set -e for error handling."""
        path = os.path.join(PROJECT_ROOT, "scripts", "deploy.sh")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "set -e" in content, "Script must include 'set -e'"
