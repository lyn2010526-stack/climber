from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.deployment_config


def test_dockerfile_runs_as_non_root_with_stdlib_healthcheck():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.11-slim AS builder" in dockerfile
    assert "useradd --uid 10001" in dockerfile
    assert "chown -R app:app /app/data /app/logs /app/workspace" in dockerfile
    assert "USER app" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "urllib.request.urlopen('http://127.0.0.1:8000/health'" in dockerfile


def test_dockerignore_excludes_secrets_dependencies_and_runtime_data():
    ignored_paths = {
        line.strip()
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }

    assert {
        ".env",
        ".git",
        "**/node_modules",
        "data",
        "logs",
        "agent-engine",
        "climber-repo",
        "climber_legacy_conflict",
    } <= ignored_paths


def test_compose_requires_credentials_and_keeps_datastores_internal():
    compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    compose = yaml.safe_load(compose_text)
    services = compose["services"]

    required_postgres_password = "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
    required_redis_password = "${REDIS_PASSWORD:?REDIS_PASSWORD is required}"

    assert services["postgres"]["environment"]["POSTGRES_PASSWORD"] == required_postgres_password
    assert services["redis"]["command"] == ["redis-server", "--requirepass", required_redis_password]
    api_environment = services["api"]["environment"]
    assert "DATABASE_URL" not in api_environment
    assert api_environment["DATABASE_HOST"] == "postgres"
    assert api_environment["DATABASE_PASSWORD"] == required_postgres_password
    assert "REDIS_URL" not in api_environment
    assert api_environment["REDIS_HOST"] == "redis"
    assert api_environment["REDIS_PASSWORD"] == required_redis_password
    assert "ports" not in services["postgres"]
    assert "ports" not in services["redis"]
    assert services["api"]["ports"] == ["8000:8000"]


def test_compose_services_have_healthchecks_restart_and_resource_limits():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))

    for service in compose["services"].values():
        assert service["restart"] == "unless-stopped"
        assert service["healthcheck"]["test"][0] == "CMD"
        limits = service["deploy"]["resources"]["limits"]
        assert limits["cpus"]
        assert limits["memory"]

    redis_healthcheck = compose["services"]["redis"]["healthcheck"]["test"]
    assert redis_healthcheck == ["CMD", "redis-cli", "ping"]
    assert compose["services"]["redis"]["environment"]["REDISCLI_AUTH"].startswith("${REDIS_PASSWORD:")


def test_production_compose_reuses_built_frontend_without_dev_server_or_runtime_install():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert "frontend" not in services
    api = services["api"]
    assert api["build"] == "."
    assert "npm install" not in str(api)
    assert "vite" not in str(api).lower()
    assert "frontend-react/dist" in (ROOT / "Dockerfile").read_text(encoding="utf-8")


def test_api_healthcheck_validates_health_status_payload():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    healthcheck = compose["services"]["api"]["healthcheck"]

    assert healthcheck["test"][0] == "CMD"
    healthcheck_command = " ".join(healthcheck["test"])
    assert "/health" in healthcheck_command
    assert "json.load" in healthcheck_command
    assert "payload.get('status')" in healthcheck_command
    assert "'ok'" in healthcheck_command


def test_chroma_configuration_matches_application_persistent_path():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    api = compose["services"]["api"]

    assert "chroma" not in compose["services"]
    assert "app_data:/app/data" in api["volumes"]
    assert "chroma_data" not in compose["volumes"]


def test_env_example_contains_only_credential_placeholders():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "POSTGRES_PASSWORD=replace-with-a-strong-postgres-password" in env_example
    assert "REDIS_PASSWORD=replace-with-a-strong-redis-password" in env_example


def test_ci_enforces_backend_frontend_and_container_quality_gates():
    workflow_path = ROOT / ".github" / "workflows" / "ci.yml"
    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)

    assert {"backend", "frontend", "deployment"} <= set(workflow["jobs"])
    assert "ruff check app/ tests/ --no-cache" in workflow_text
    assert "python -m pytest tests/" in workflow_text
    assert "npm run lint" in workflow_text
    assert "npx tsc -b --noEmit" in workflow_text
    assert "npm run test" in workflow_text
    assert "npm run build" in workflow_text
    assert "docker compose config --quiet" in workflow_text
    assert "docker build" in workflow_text
    assert "docker-compose" not in workflow_text


def test_runtime_requirements_include_direct_xml_parser_dependency():
    requirements = {
        line.strip().lower()
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }

    assert any(requirement.startswith("defusedxml") for requirement in requirements)
