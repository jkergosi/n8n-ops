"""
Unit tests for the promotion validation service - pre-flight validation checks.

Tests cover:
- Target environment health validation
- Credential availability validation
- Drift policy compliance validation
- Complete pre-flight validation orchestration
- Fail-open and fail-closed behavior
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from uuid import uuid4

from app.services.promotion_validation_service import PromotionValidator


# ============ Fixtures ============


@pytest.fixture
def validator():
    """Create a PromotionValidator instance with mocked dependencies."""
    return PromotionValidator()


@pytest.fixture
def mock_environment():
    """Create a mock environment configuration."""
    return {
        "id": "env-1",
        "name": "Development",
        "tenant_id": "tenant-1",
        "n8n_name": "Development",
        "n8n_type": "dev",
        "n8n_base_url": "https://dev.n8n.example.com",
        "n8n_api_key": "test-api-key",
        "git_repo_url": "https://github.com/test/repo",
        "git_pat": "test-token",
        "git_branch": "main",
        "is_active": True,
        "provider": "n8n",
    }


@pytest.fixture
def mock_target_environment():
    """Create a mock target environment configuration."""
    return {
        "id": "env-2",
        "name": "Production",
        "tenant_id": "tenant-1",
        "n8n_name": "Production",
        "n8n_type": "production",
        "n8n_base_url": "https://prod.n8n.example.com",
        "n8n_api_key": "test-api-key-prod",
        "git_repo_url": "https://github.com/test/repo",
        "git_pat": "test-token",
        "git_branch": "main",
        "is_active": True,
        "provider": "n8n",
    }


@pytest.fixture
def mock_workflow_with_credentials():
    """Create a mock workflow with credential dependencies."""
    return {
        "id": "wf-1",
        "name": "Test Workflow",
        "workflow_data": {
            "name": "Test Workflow",
            "nodes": [
                {
                    "id": "node-1",
                    "type": "n8n-nodes-base.httpRequest",
                    "name": "HTTP Request",
                    "credentials": {
                        "httpHeaderAuth": {"name": "my-api-key"}
                    }
                },
                {
                    "id": "node-2",
                    "type": "n8n-nodes-base.postgres",
                    "name": "PostgreSQL",
                    "credentials": {
                        "postgres": {"name": "db-connection"}
                    }
                }
            ]
        }
    }


@pytest.fixture
def mock_workflow_no_credentials():
    """Create a mock workflow without credential dependencies."""
    return {
        "id": "wf-2",
        "name": "Simple Workflow",
        "workflow_data": {
            "name": "Simple Workflow",
            "nodes": [
                {
                    "id": "node-1",
                    "type": "n8n-nodes-base.start",
                    "name": "Start"
                }
            ]
        }
    }


# ============ Target Environment Health Tests ============


@pytest.mark.asyncio
async def test_validate_environment_health_success(validator, mock_target_environment):
    """Test successful environment health validation."""
    with patch("app.services.promotion_validation_service.db_service") as mock_db, \
         patch.object(validator.provider_registry, "get_adapter_for_environment") as mock_adapter_factory:

        # Mock database response
        mock_db.get_environment = AsyncMock(return_value=mock_target_environment)

        # Mock adapter with successful connection test
        mock_adapter = MagicMock()
        mock_adapter.test_connection = AsyncMock(return_value=True)
        mock_adapter_factory.return_value = mock_adapter

        # Run validation
        result = await validator.validate_target_environment_health(
            target_environment_id="env-2",
            tenant_id="tenant-1",
            timeout_seconds=5.0
        )

        # Assertions
        assert result["passed"] is True
        assert result["check"] == "target_environment_health"
        assert "reachable and healthy" in result["message"]
        assert result["remediation"] is None
        assert result["details"]["connection_test_passed"] is True


@pytest.mark.asyncio
async def test_validate_environment_health_not_found(validator):
    """Test environment health validation when environment doesn't exist."""
    with patch("app.services.promotion_validation_service.db_service") as mock_db:
        # Mock database response - environment not found
        mock_db.get_environment = AsyncMock(return_value=None)

        # Run validation
        result = await validator.validate_target_environment_health(
            target_environment_id="nonexistent-env",
            tenant_id="tenant-1",
            timeout_seconds=5.0
        )

        # Assertions - Fail-closed
        assert result["passed"] is False
        assert result["check"] == "target_environment_health"
        assert "not found" in result["message"]
        assert "Verify the environment ID" in result["remediation"]
        assert result["details"]["error_type"] == "environment_not_found"


@pytest.mark.asyncio
async def test_validate_environment_health_connection_failed(validator, mock_target_environment):
    """Test environment health validation when connection test fails."""
    with patch("app.services.promotion_validation_service.db_service") as mock_db, \
         patch.object(validator.provider_registry, "get_adapter_for_environment") as mock_adapter_factory:

        # Mock database response
        mock_db.get_environment = AsyncMock(return_value=mock_target_environment)

        # Mock adapter with failed connection test
        mock_adapter = MagicMock()
        mock_adapter.test_connection = AsyncMock(return_value=False)
        mock_adapter_factory.return_value = mock_adapter

        # Run validation
        result = await validator.validate_target_environment_health(
            target_environment_id="env-2",
            tenant_id="tenant-1",
            timeout_seconds=5.0
        )

        # Assertions - Fail-closed
        assert result["passed"] is False
        assert result["check"] == "target_environment_health"
        assert "not reachable" in result["message"]
        assert "Navigate to Environments" in result["remediation"]
        assert result["details"]["error_type"] == "connection_failed"


@pytest.mark.asyncio
async def test_validate_environment_health_timeout(validator, mock_target_environment):
    """Test environment health validation when connection times out."""
    import asyncio

    with patch("app.services.promotion_validation_service.db_service") as mock_db, \
         patch.object(validator.provider_registry, "get_adapter_for_environment") as mock_adapter_factory:

        # Mock database response
        mock_db.get_environment = AsyncMock(return_value=mock_target_environment)

        # Mock adapter with timeout
        mock_adapter = MagicMock()
        mock_adapter.test_connection = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_adapter_factory.return_value = mock_adapter

        # Run validation
        result = await validator.validate_target_environment_health(
            target_environment_id="env-2",
            tenant_id="tenant-1",
            timeout_seconds=5.0
        )

        # Assertions - Fail-closed
        assert result["passed"] is False
        assert result["check"] == "target_environment_health"
        assert "timed out" in result["message"]
        assert result["details"]["error_type"] == "connection_timeout"
        assert result["details"]["timeout_seconds"] == 5.0


@pytest.mark.asyncio
async def test_validate_environment_health_invalid_provider_config(validator, mock_target_environment):
    """Test environment health validation when provider config is invalid."""
    with patch("app.services.promotion_validation_service.db_service") as mock_db, \
         patch.object(validator.provider_registry, "get_adapter_for_environment") as mock_adapter_factory:

        # Mock database response
        mock_db.get_environment = AsyncMock(return_value=mock_target_environment)

        # Mock adapter factory raising ValueError
        mock_adapter_factory.side_effect = ValueError("Invalid provider configuration")

        # Run validation
        result = await validator.validate_target_environment_health(
            target_environment_id="env-2",
            tenant_id="tenant-1",
            timeout_seconds=5.0
        )

        # Assertions - Fail-closed
        assert result["passed"] is False
        assert result["check"] == "target_environment_health"
        assert "invalid provider configuration" in result["message"]
        assert "verify provider settings" in result["remediation"]
        assert result["details"]["error_type"] == "invalid_provider_config"


@pytest.mark.asyncio
async def test_validate_environment_health_fail_open(validator, mock_target_environment):
    """Test environment health validation fail-open behavior on unexpected errors."""
    with patch("app.services.promotion_validation_service.db_service") as mock_db:

        # Mock database raising an unexpected exception
        mock_db.get_environment = AsyncMock(side_effect=RuntimeError("Database connection lost"))

        # Run validation
        result = await validator.validate_target_environment_health(
            target_environment_id="env-2",
            tenant_id="tenant-1",
            timeout_seconds=5.0
        )

        # Assertions - Fail-open (allows promotion to proceed)
        assert result["passed"] is True  # CRITICAL: fail-open behavior
        assert result["check"] == "target_environment_health"
        assert "fail-open" in result["message"]
        assert result["remediation"] is None
        assert result["details"]["fail_open"] is True
        assert result["details"]["error_type"] == "RuntimeError"
        assert "correlation_id" in result["details"]


# ============ Credential Availability Tests ============


@pytest.mark.asyncio
async def test_validate_credentials_success(validator, mock_environment, mock_target_environment, mock_workflow_with_credentials):
    """Test successful credential availability validation."""
    with patch("app.services.promotion_validation_service.db_service") as mock_db, \
         patch.object(validator.provider_registry, "get_adapter_for_environment") as mock_adapter_factory:

        # Mock database responses
        mock_db.get_environment = AsyncMock(side_effect=lambda env_id, tenant_id:
            mock_environment if env_id == "env-1" else mock_target_environment)
        mock_db.get_workflow = AsyncMock(return_value=mock_workflow_with_credentials)
        mock_db.find_logical_credential_by_name = AsyncMock(return_value=None)

        # Mock target adapter with credentials
        mock_target_adapter = MagicMock()
        mock_target_adapter.get_credentials = AsyncMock(return_value=[
            {"type": "httpHeaderAuth", "name": "my-api-key"},
            {"type": "postgres", "name": "db-connection"}
        ])
        mock_adapter_factory.return_value = mock_target_adapter

        # Run validation
        result = await validator.validate_credentials_available(
            workflow_id="wf-1",
            source_environment_id="env-1",
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions
        assert result["passed"] is True
        assert result["check"] == "credential_availability"
        assert "All credentials required" in result["message"]
        assert result["remediation"] is None
        assert result["missing_credentials"] == []


@pytest.mark.asyncio
async def test_validate_credentials_missing_in_target(validator, mock_environment, mock_target_environment, mock_workflow_with_credentials):
    """Test credential validation when credentials are missing in target."""
    with patch("app.services.promotion_validation_service.db_service") as mock_db, \
         patch.object(validator.provider_registry, "get_adapter_for_environment") as mock_adapter_factory:

        # Mock database responses
        mock_db.get_environment = AsyncMock(side_effect=lambda env_id, tenant_id:
            mock_environment if env_id == "env-1" else mock_target_environment)
        mock_db.get_workflow = AsyncMock(return_value=mock_workflow_with_credentials)
        mock_db.find_logical_credential_by_name = AsyncMock(return_value=None)

        # Mock target adapter with only one credential (missing one)
        mock_target_adapter = MagicMock()
        mock_target_adapter.get_credentials = AsyncMock(return_value=[
            {"type": "httpHeaderAuth", "name": "my-api-key"}
            # postgres:db-connection is missing
        ])
        mock_adapter_factory.return_value = mock_target_adapter

        # Run validation
        result = await validator.validate_credentials_available(
            workflow_id="wf-1",
            source_environment_id="env-1",
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions - Fail-closed
        assert result["passed"] is False
        assert result["check"] == "credential_availability"
        assert "missing in target environment" in result["message"]
        assert "Navigate to Credentials page" in result["remediation"]
        assert "postgres:db-connection" in result["missing_credentials"]
        assert len(result["details"]["blocking_issues"]) == 1


@pytest.mark.asyncio
async def test_validate_credentials_with_logical_mapping(validator, mock_environment, mock_target_environment, mock_workflow_with_credentials):
    """Test credential validation with logical credential mappings."""
    with patch("app.services.promotion_validation_service.db_service") as mock_db, \
         patch.object(validator.provider_registry, "get_adapter_for_environment") as mock_adapter_factory:

        # Mock database responses
        mock_db.get_environment = AsyncMock(side_effect=lambda env_id, tenant_id:
            mock_environment if env_id == "env-1" else mock_target_environment)
        mock_db.get_workflow = AsyncMock(return_value=mock_workflow_with_credentials)

        # Mock logical credential mapping for first credential
        mock_db.find_logical_credential_by_name = AsyncMock(side_effect=lambda tenant_id, key:
            {"id": "logical-1"} if key == "httpHeaderAuth:my-api-key" else None)
        mock_db.get_mapping_for_logical = AsyncMock(return_value={
            "physical_type": "httpHeaderAuth",
            "physical_name": "production-api-key"  # Different name in production
        })

        # Mock target adapter with mapped credential
        mock_target_adapter = MagicMock()
        mock_target_adapter.get_credentials = AsyncMock(return_value=[
            {"type": "httpHeaderAuth", "name": "production-api-key"},  # Mapped name
            {"type": "postgres", "name": "db-connection"}
        ])
        mock_adapter_factory.return_value = mock_target_adapter

        # Run validation
        result = await validator.validate_credentials_available(
            workflow_id="wf-1",
            source_environment_id="env-1",
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions
        assert result["passed"] is True
        assert result["check"] == "credential_availability"
        assert result["missing_credentials"] == []


@pytest.mark.asyncio
async def test_validate_credentials_missing_logical_mapping(validator, mock_environment, mock_target_environment, mock_workflow_with_credentials):
    """Test credential validation when logical mapping is missing."""
    with patch("app.services.promotion_validation_service.db_service") as mock_db, \
         patch.object(validator.provider_registry, "get_adapter_for_environment") as mock_adapter_factory:

        # Mock database responses
        mock_db.get_environment = AsyncMock(side_effect=lambda env_id, tenant_id:
            mock_environment if env_id == "env-1" else mock_target_environment)
        mock_db.get_workflow = AsyncMock(return_value=mock_workflow_with_credentials)

        # Mock logical credential exists but no mapping for target
        mock_db.find_logical_credential_by_name = AsyncMock(side_effect=lambda tenant_id, key:
            {"id": "logical-1"} if key == "httpHeaderAuth:my-api-key" else None)
        mock_db.get_mapping_for_logical = AsyncMock(return_value=None)  # No mapping

        # Mock target adapter
        mock_target_adapter = MagicMock()
        mock_target_adapter.get_credentials = AsyncMock(return_value=[
            {"type": "postgres", "name": "db-connection"}
        ])
        mock_adapter_factory.return_value = mock_target_adapter

        # Run validation
        result = await validator.validate_credentials_available(
            workflow_id="wf-1",
            source_environment_id="env-1",
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions - Fail-closed
        assert result["passed"] is False
        assert result["check"] == "credential_availability"
        assert "missing in target environment" in result["message"]
        assert any("missing_mapping" in issue["issue_type"] for issue in result["details"]["blocking_issues"])


@pytest.mark.asyncio
async def test_validate_credentials_workflow_not_found(validator, mock_environment, mock_target_environment):
    """Test credential validation when workflow is not found (new workflow deployment)."""
    with patch("app.services.promotion_validation_service.db_service") as mock_db, \
         patch.object(validator.provider_registry, "get_adapter_for_environment") as mock_adapter_factory:

        # Mock database responses
        mock_db.get_environment = AsyncMock(side_effect=lambda env_id, tenant_id:
            mock_environment if env_id == "env-1" else mock_target_environment)
        mock_db.get_workflow = AsyncMock(return_value=None)  # Workflow not found

        # Mock target adapter
        mock_target_adapter = MagicMock()
        mock_target_adapter.get_credentials = AsyncMock(return_value=[])
        mock_adapter_factory.return_value = mock_target_adapter

        # Run validation
        result = await validator.validate_credentials_available(
            workflow_id="new-wf",
            source_environment_id="env-1",
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions - Pass with warning (new workflow deployment)
        assert result["passed"] is True
        assert result["check"] == "credential_availability"
        assert "not found in source environment" in result["message"]
        assert "Assuming new workflow deployment" in result["message"]
        assert result["missing_credentials"] == []


@pytest.mark.asyncio
async def test_validate_credentials_source_env_not_found(validator):
    """Test credential validation when source environment doesn't exist."""
    with patch("app.services.promotion_validation_service.db_service") as mock_db:

        # Mock database response - source environment not found
        mock_db.get_environment = AsyncMock(return_value=None)

        # Run validation
        result = await validator.validate_credentials_available(
            workflow_id="wf-1",
            source_environment_id="nonexistent-env",
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions - Fail-closed
        assert result["passed"] is False
        assert result["check"] == "credential_availability"
        assert "Source environment" in result["message"]
        assert "not found" in result["message"]
        assert result["details"]["error_type"] == "source_environment_not_found"


@pytest.mark.asyncio
async def test_validate_credentials_fail_open(validator, mock_environment, mock_target_environment):
    """Test credential validation fail-open behavior on unexpected errors."""
    with patch("app.services.promotion_validation_service.db_service") as mock_db:

        # Mock database raising an unexpected exception
        mock_db.get_environment = AsyncMock(side_effect=RuntimeError("Unexpected database error"))

        # Run validation
        result = await validator.validate_credentials_available(
            workflow_id="wf-1",
            source_environment_id="env-1",
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions - Fail-open (allows promotion to proceed)
        assert result["passed"] is True  # CRITICAL: fail-open behavior
        assert result["check"] == "credential_availability"
        assert "fail-open" in result["message"]
        assert result["remediation"] is None
        assert result["details"]["fail_open"] is True
        assert result["details"]["error_type"] == "RuntimeError"
        assert "correlation_id" in result["details"]


# ============ Drift Policy Compliance Tests ============


@pytest.mark.asyncio
async def test_validate_drift_policy_no_blocking(validator, mock_target_environment):
    """Test drift policy validation when no blocking incidents exist."""
    with patch("app.services.promotion_validation_service.db_service") as mock_db, \
         patch("app.api.endpoints.promotions.check_drift_policy_blocking") as mock_drift_check:

        # Mock database response
        mock_db.get_environment = AsyncMock(return_value=mock_target_environment)

        # Mock drift check - no blocking (async function)
        mock_drift_check.return_value = {"blocked": False}

        # Run validation
        result = await validator.validate_drift_policy_compliance(
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions
        assert result["passed"] is True
        assert result["check"] == "drift_policy_compliance"
        assert "No drift policy violations" in result["message"]
        assert result["remediation"] is None
        assert result["blocking_incidents"] == []


@pytest.mark.asyncio
async def test_validate_drift_policy_active_incident_blocking(validator, mock_target_environment):
    """Test drift policy validation when active drift incident blocks deployment."""
    with patch("app.services.promotion_validation_service.db_service") as mock_db, \
         patch("app.api.endpoints.promotions.check_drift_policy_blocking") as mock_drift_check:

        # Mock database response
        mock_db.get_environment = AsyncMock(return_value=mock_target_environment)

        # Mock drift check - blocked by active incident (async function)
        mock_drift_check.return_value = {
            "blocked": True,
            "reason": "active_drift_incident",
            "details": {
                "incident_id": "drift-123",
                "incident_title": "Unexpected workflow modification",
                "severity": "high",
                "status": "active"
            }
        }

        # Run validation
        result = await validator.validate_drift_policy_compliance(
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions - Fail-closed
        assert result["passed"] is False
        assert result["check"] == "drift_policy_compliance"
        assert "Active drift incident exists" in result["message"]
        assert "Navigate to Drift Incidents" in result["remediation"]
        assert len(result["blocking_incidents"]) == 1
        assert result["blocking_incidents"][0]["incident_id"] == "drift-123"


@pytest.mark.asyncio
async def test_validate_drift_policy_expired_incident_blocking(validator, mock_target_environment):
    """Test drift policy validation when expired drift incident blocks deployment."""
    with patch("app.services.promotion_validation_service.db_service") as mock_db, \
         patch("app.api.endpoints.promotions.check_drift_policy_blocking") as mock_drift_check:

        # Mock database response
        mock_db.get_environment = AsyncMock(return_value=mock_target_environment)

        # Mock drift check - blocked by expired incident (async function)
        mock_drift_check.return_value = {
            "blocked": True,
            "reason": "drift_incident_expired",
            "details": {
                "incident_id": "drift-456",
                "incident_title": "Expired drift tracking",
                "severity": "medium",
                "status": "active",
                "expired_at": "2024-01-01T00:00:00Z"
            }
        }

        # Run validation
        result = await validator.validate_drift_policy_compliance(
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions - Fail-closed
        assert result["passed"] is False
        assert result["check"] == "drift_policy_compliance"
        assert "Drift incident has expired" in result["message"]
        assert "Extend the TTL" in result["remediation"]
        assert len(result["blocking_incidents"]) == 1


@pytest.mark.asyncio
async def test_validate_drift_policy_environment_not_found(validator):
    """Test drift policy validation when environment doesn't exist."""
    with patch("app.services.promotion_validation_service.db_service") as mock_db:

        # Mock database response - environment not found
        mock_db.get_environment = AsyncMock(return_value=None)

        # Run validation
        result = await validator.validate_drift_policy_compliance(
            target_environment_id="nonexistent-env",
            tenant_id="tenant-1"
        )

        # Assertions - Fail-closed
        assert result["passed"] is False
        assert result["check"] == "drift_policy_compliance"
        assert "not found" in result["message"]
        assert result["details"]["error_type"] == "environment_not_found"


@pytest.mark.asyncio
async def test_validate_drift_policy_fail_open(validator, mock_target_environment):
    """Test drift policy validation fail-open behavior on unexpected errors."""
    with patch("app.services.promotion_validation_service.db_service") as mock_db:

        # Mock database raising an unexpected exception
        mock_db.get_environment = AsyncMock(side_effect=RuntimeError("Database connection lost"))

        # Run validation
        result = await validator.validate_drift_policy_compliance(
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions - Fail-open (allows promotion to proceed)
        assert result["passed"] is True  # CRITICAL: fail-open behavior
        assert result["check"] == "drift_policy_compliance"
        assert "fail-open" in result["message"]
        assert result["remediation"] is None
        assert result["details"]["fail_open"] is True
        assert result["details"]["error_type"] == "RuntimeError"
        assert "correlation_id" in result["details"]


# ============ Complete Pre-flight Validation Tests ============


@pytest.mark.asyncio
async def test_run_preflight_validation_all_pass(validator):
    """Test complete pre-flight validation when all checks pass."""
    with patch.object(validator, "validate_target_environment_health") as mock_health, \
         patch.object(validator, "validate_credentials_available") as mock_credentials, \
         patch.object(validator, "validate_drift_policy_compliance") as mock_drift:

        # Mock all validations passing
        mock_health.return_value = {
            "passed": True,
            "check": "target_environment_health",
            "message": "Environment healthy",
            "remediation": None,
            "details": {}
        }
        mock_credentials.return_value = {
            "passed": True,
            "check": "credential_availability",
            "message": "All credentials available",
            "remediation": None,
            "details": {}
        }
        mock_drift.return_value = {
            "passed": True,
            "check": "drift_policy_compliance",
            "message": "No drift violations",
            "remediation": None,
            "details": {}
        }

        # Run validation
        result = await validator.run_preflight_validation(
            workflow_id="wf-1",
            source_environment_id="env-1",
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions
        assert result["validation_passed"] is True
        assert len(result["validation_errors"]) == 0
        assert len(result["validation_warnings"]) == 0
        assert len(result["checks_run"]) == 3
        assert "target_environment_health" in result["checks_run"]
        assert "credential_availability" in result["checks_run"]
        assert "drift_policy_compliance" in result["checks_run"]
        assert "correlation_id" in result
        assert "timestamp" in result


@pytest.mark.asyncio
async def test_run_preflight_validation_health_fails(validator):
    """Test pre-flight validation with environment health failure (fail-fast)."""
    with patch.object(validator, "validate_target_environment_health") as mock_health, \
         patch.object(validator, "validate_credentials_available") as mock_credentials, \
         patch.object(validator, "validate_drift_policy_compliance") as mock_drift:

        # Mock health check failing
        mock_health.return_value = {
            "passed": False,
            "check": "target_environment_health",
            "message": "Environment unreachable",
            "remediation": "Check network connectivity",
            "details": {"error_type": "connection_failed"}
        }

        # Run validation
        result = await validator.run_preflight_validation(
            workflow_id="wf-1",
            source_environment_id="env-1",
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions - Fail-fast behavior
        assert result["validation_passed"] is False
        assert len(result["validation_errors"]) == 1
        assert result["validation_errors"][0]["check"] == "target_environment_health"
        assert result["validation_errors"][0]["status"] == "failed"
        assert len(result["checks_run"]) == 1  # Only health check ran (fail-fast)

        # Credentials and drift checks should NOT have been called
        mock_credentials.assert_not_called()
        mock_drift.assert_not_called()


@pytest.mark.asyncio
async def test_run_preflight_validation_credentials_fail(validator):
    """Test pre-flight validation with credential failure (fail-fast)."""
    with patch.object(validator, "validate_target_environment_health") as mock_health, \
         patch.object(validator, "validate_credentials_available") as mock_credentials, \
         patch.object(validator, "validate_drift_policy_compliance") as mock_drift:

        # Mock health passing, credentials failing
        mock_health.return_value = {
            "passed": True,
            "check": "target_environment_health",
            "message": "Environment healthy",
            "remediation": None,
            "details": {}
        }
        mock_credentials.return_value = {
            "passed": False,
            "check": "credential_availability",
            "message": "Missing credentials",
            "remediation": "Create missing credentials",
            "details": {"blocking_issues": []}
        }

        # Run validation
        result = await validator.run_preflight_validation(
            workflow_id="wf-1",
            source_environment_id="env-1",
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions - Fail-fast behavior
        assert result["validation_passed"] is False
        assert len(result["validation_errors"]) == 1
        assert result["validation_errors"][0]["check"] == "credential_availability"
        assert len(result["checks_run"]) == 2  # Health and credentials ran

        # Drift check should NOT have been called (fail-fast)
        mock_drift.assert_not_called()


@pytest.mark.asyncio
async def test_run_preflight_validation_drift_fails(validator):
    """Test pre-flight validation with drift policy failure."""
    with patch.object(validator, "validate_target_environment_health") as mock_health, \
         patch.object(validator, "validate_credentials_available") as mock_credentials, \
         patch.object(validator, "validate_drift_policy_compliance") as mock_drift:

        # Mock health and credentials passing, drift failing
        mock_health.return_value = {
            "passed": True,
            "check": "target_environment_health",
            "message": "Environment healthy",
            "remediation": None,
            "details": {}
        }
        mock_credentials.return_value = {
            "passed": True,
            "check": "credential_availability",
            "message": "All credentials available",
            "remediation": None,
            "details": {}
        }
        mock_drift.return_value = {
            "passed": False,
            "check": "drift_policy_compliance",
            "message": "Active drift incident blocks deployment",
            "remediation": "Resolve drift incident",
            "details": {}
        }

        # Run validation
        result = await validator.run_preflight_validation(
            workflow_id="wf-1",
            source_environment_id="env-1",
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions
        assert result["validation_passed"] is False
        assert len(result["validation_errors"]) == 1
        assert result["validation_errors"][0]["check"] == "drift_policy_compliance"
        assert len(result["checks_run"]) == 3  # All checks ran


@pytest.mark.asyncio
async def test_run_preflight_validation_with_fail_open_warnings(validator):
    """Test pre-flight validation with fail-open warnings (still passes overall)."""
    with patch.object(validator, "validate_target_environment_health") as mock_health, \
         patch.object(validator, "validate_credentials_available") as mock_credentials, \
         patch.object(validator, "validate_drift_policy_compliance") as mock_drift:

        # Mock health passing with fail-open warning
        mock_health.return_value = {
            "passed": True,
            "check": "target_environment_health",
            "message": "Health check fail-open",
            "remediation": None,
            "details": {"fail_open": True, "correlation_id": "test-123"}
        }
        mock_credentials.return_value = {
            "passed": True,
            "check": "credential_availability",
            "message": "All credentials available",
            "remediation": None,
            "details": {}
        }
        mock_drift.return_value = {
            "passed": True,
            "check": "drift_policy_compliance",
            "message": "No drift violations",
            "remediation": None,
            "details": {}
        }

        # Run validation
        result = await validator.run_preflight_validation(
            workflow_id="wf-1",
            source_environment_id="env-1",
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions
        assert result["validation_passed"] is True  # Overall still passes
        assert len(result["validation_errors"]) == 0
        assert len(result["validation_warnings"]) == 1  # Fail-open recorded as warning
        assert result["validation_warnings"][0]["check"] == "target_environment_health"
        assert result["validation_warnings"][0]["status"] == "warning"


@pytest.mark.asyncio
async def test_run_preflight_validation_orchestration_error_fail_open(validator):
    """Test pre-flight validation when orchestration itself encounters errors (fail-open)."""
    with patch.object(validator, "validate_target_environment_health") as mock_health, \
         patch.object(validator, "validate_credentials_available") as mock_credentials, \
         patch.object(validator, "validate_drift_policy_compliance") as mock_drift:

        # Mock health passing
        mock_health.return_value = {
            "passed": True,
            "check": "target_environment_health",
            "message": "Environment healthy",
            "remediation": None,
            "details": {}
        }

        # Mock credentials check raising unexpected exception
        mock_credentials.side_effect = RuntimeError("Unexpected orchestration error")

        # Mock drift passing
        mock_drift.return_value = {
            "passed": True,
            "check": "drift_policy_compliance",
            "message": "No drift violations",
            "remediation": None,
            "details": {}
        }

        # Run validation
        result = await validator.run_preflight_validation(
            workflow_id="wf-1",
            source_environment_id="env-1",
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions - Fail-open behavior
        assert result["validation_passed"] is True  # Overall still passes
        assert len(result["validation_errors"]) == 0
        assert len(result["validation_warnings"]) == 1  # Orchestration error as warning
        assert result["validation_warnings"][0]["check"] == "credential_availability"
        assert "fail-open" in result["validation_warnings"][0]["message"]
        assert result["validation_warnings"][0]["details"]["error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_run_preflight_validation_correlation_id_present(validator):
    """Test that pre-flight validation always includes correlation ID for tracking."""
    with patch.object(validator, "validate_target_environment_health") as mock_health, \
         patch.object(validator, "validate_credentials_available") as mock_credentials, \
         patch.object(validator, "validate_drift_policy_compliance") as mock_drift:

        # Mock all validations passing
        mock_health.return_value = {
            "passed": True,
            "check": "target_environment_health",
            "message": "Environment healthy",
            "remediation": None,
            "details": {}
        }
        mock_credentials.return_value = {
            "passed": True,
            "check": "credential_availability",
            "message": "All credentials available",
            "remediation": None,
            "details": {}
        }
        mock_drift.return_value = {
            "passed": True,
            "check": "drift_policy_compliance",
            "message": "No drift violations",
            "remediation": None,
            "details": {}
        }

        # Run validation
        result = await validator.run_preflight_validation(
            workflow_id="wf-1",
            source_environment_id="env-1",
            target_environment_id="env-2",
            tenant_id="tenant-1"
        )

        # Assertions - Correlation ID for monitoring
        assert "correlation_id" in result
        assert result["correlation_id"] is not None
        assert len(result["correlation_id"]) > 0  # UUID format
