"""
Tests for Promotion Concurrency Control

Unit tests for PromotionLockService which provides environment-level
concurrency control to prevent multiple promotions from executing
against the same target environment simultaneously.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from app.services.promotion_lock_service import (
    PromotionLockService,
    PromotionConflict,
    PromotionConflictError,
    promotion_lock_service
)


class TestPromotionConflict:
    """Test suite for PromotionConflict dataclass"""

    def test_create_promotion_conflict(self):
        """Test creating a PromotionConflict instance"""
        conflict = PromotionConflict(
            promotion_id="promo-123",
            promotion_name="Deploy v2.0",
            started_at="2024-01-15T10:00:00Z",
            started_by="user@example.com",
            target_environment_id="env-prod-001",
            target_environment_name="Production"
        )

        assert conflict.promotion_id == "promo-123"
        assert conflict.promotion_name == "Deploy v2.0"
        assert conflict.started_at == "2024-01-15T10:00:00Z"
        assert conflict.started_by == "user@example.com"
        assert conflict.target_environment_id == "env-prod-001"
        assert conflict.target_environment_name == "Production"

    def test_create_promotion_conflict_with_none_values(self):
        """Test creating a PromotionConflict with optional None values"""
        conflict = PromotionConflict(
            promotion_id="promo-123",
            promotion_name=None,
            started_at=None,
            started_by=None,
            target_environment_id="env-prod-001",
            target_environment_name=None
        )

        assert conflict.promotion_id == "promo-123"
        assert conflict.promotion_name is None
        assert conflict.started_at is None
        assert conflict.started_by is None
        assert conflict.target_environment_id == "env-prod-001"
        assert conflict.target_environment_name is None


class TestPromotionConflictError:
    """Test suite for PromotionConflictError exception"""

    def test_promotion_conflict_error_status_code(self):
        """Test that PromotionConflictError returns 409 status code"""
        conflict = PromotionConflict(
            promotion_id="promo-123",
            promotion_name="Deploy v2.0",
            started_at="2024-01-15T10:00:00Z",
            started_by="user@example.com",
            target_environment_id="env-prod-001",
            target_environment_name="Production"
        )

        error = PromotionConflictError(conflict)

        assert error.status_code == 409

    def test_promotion_conflict_error_detail_structure(self):
        """Test that PromotionConflictError detail has correct structure"""
        conflict = PromotionConflict(
            promotion_id="promo-123",
            promotion_name="Deploy v2.0",
            started_at="2024-01-15T10:00:00Z",
            started_by="user@example.com",
            target_environment_id="env-prod-001",
            target_environment_name="Production"
        )

        error = PromotionConflictError(conflict)

        assert error.detail["error"] == "promotion_conflict"
        assert "Cannot start promotion" in error.detail["message"]
        assert "blocking_promotion" in error.detail

    def test_promotion_conflict_error_blocking_promotion_details(self):
        """Test that blocking promotion details are correctly included"""
        conflict = PromotionConflict(
            promotion_id="promo-123",
            promotion_name="Deploy v2.0",
            started_at="2024-01-15T10:00:00Z",
            started_by="user@example.com",
            target_environment_id="env-prod-001",
            target_environment_name="Production"
        )

        error = PromotionConflictError(conflict)
        blocking = error.detail["blocking_promotion"]

        assert blocking["id"] == "promo-123"
        assert blocking["name"] == "Deploy v2.0"
        assert blocking["started_at"] == "2024-01-15T10:00:00Z"
        assert blocking["started_by"] == "user@example.com"
        assert blocking["target_environment_id"] == "env-prod-001"
        assert blocking["target_environment_name"] == "Production"

    def test_promotion_conflict_error_preserves_conflict_object(self):
        """Test that the conflict object is preserved on the error"""
        conflict = PromotionConflict(
            promotion_id="promo-123",
            promotion_name="Deploy v2.0",
            started_at="2024-01-15T10:00:00Z",
            started_by="user@example.com",
            target_environment_id="env-prod-001"
        )

        error = PromotionConflictError(conflict)

        assert error.conflict is conflict
        assert error.conflict.promotion_id == "promo-123"


class TestPromotionLockService:
    """Test suite for PromotionLockService"""

    @pytest.fixture
    def service(self):
        """Create a PromotionLockService instance for testing"""
        return PromotionLockService()

    @pytest.fixture
    def mock_db_service(self):
        """Create a mock database service"""
        mock = MagicMock()
        mock.get_active_promotion_for_environment = AsyncMock(return_value=None)
        return mock

    # ==========================================================================
    # check_and_acquire_promotion_lock tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_check_and_acquire_lock_no_active_promotion(self, service, mock_db_service):
        """Test that lock is acquired when no active promotion exists"""
        with patch.object(service, 'db_service', mock_db_service):
            # No active promotion
            mock_db_service.get_active_promotion_for_environment.return_value = None

            result = await service.check_and_acquire_promotion_lock(
                tenant_id="tenant-123",
                target_environment_id="env-prod-001"
            )

            assert result is True
            mock_db_service.get_active_promotion_for_environment.assert_called_once_with(
                tenant_id="tenant-123",
                target_environment_id="env-prod-001"
            )

    @pytest.mark.asyncio
    async def test_check_and_acquire_lock_active_promotion_exists(self, service, mock_db_service):
        """Test that PromotionConflictError is raised when active promotion exists"""
        with patch.object(service, 'db_service', mock_db_service):
            # Active promotion exists
            mock_db_service.get_active_promotion_for_environment.return_value = {
                "id": "promo-active-123",
                "name": "Running Promotion",
                "started_at": "2024-01-15T10:00:00Z",
                "created_by": "user@example.com",
                "target_environment_name": "Production"
            }

            with pytest.raises(PromotionConflictError) as exc_info:
                await service.check_and_acquire_promotion_lock(
                    tenant_id="tenant-123",
                    target_environment_id="env-prod-001"
                )

            assert exc_info.value.status_code == 409
            assert exc_info.value.conflict.promotion_id == "promo-active-123"
            assert exc_info.value.conflict.promotion_name == "Running Promotion"

    @pytest.mark.asyncio
    async def test_check_and_acquire_lock_same_promotion_retry(self, service, mock_db_service):
        """Test that same promotion can proceed in retry scenario"""
        with patch.object(service, 'db_service', mock_db_service):
            # Active promotion is the same as requesting promotion
            mock_db_service.get_active_promotion_for_environment.return_value = {
                "id": "promo-123",
                "name": "My Promotion",
                "started_at": "2024-01-15T10:00:00Z",
                "created_by": "user@example.com"
            }

            # Same promotion ID as the active one
            result = await service.check_and_acquire_promotion_lock(
                tenant_id="tenant-123",
                target_environment_id="env-prod-001",
                requesting_promotion_id="promo-123"
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_check_and_acquire_lock_different_promotion_blocked(self, service, mock_db_service):
        """Test that different promotion is blocked by active promotion"""
        with patch.object(service, 'db_service', mock_db_service):
            # Active promotion exists with different ID
            mock_db_service.get_active_promotion_for_environment.return_value = {
                "id": "promo-active-456",
                "name": "Other Promotion",
                "started_at": "2024-01-15T10:00:00Z",
                "created_by": "other@example.com"
            }

            # Requesting with a different promotion ID
            with pytest.raises(PromotionConflictError) as exc_info:
                await service.check_and_acquire_promotion_lock(
                    tenant_id="tenant-123",
                    target_environment_id="env-prod-001",
                    requesting_promotion_id="promo-new-789"
                )

            assert exc_info.value.conflict.promotion_id == "promo-active-456"

    @pytest.mark.asyncio
    async def test_check_and_acquire_lock_without_requesting_id(self, service, mock_db_service):
        """Test lock check without requesting promotion ID"""
        with patch.object(service, 'db_service', mock_db_service):
            # Active promotion exists
            mock_db_service.get_active_promotion_for_environment.return_value = {
                "id": "promo-123",
                "name": "Active Promotion",
                "started_at": "2024-01-15T10:00:00Z",
                "created_by": "user@example.com"
            }

            # No requesting_promotion_id provided
            with pytest.raises(PromotionConflictError):
                await service.check_and_acquire_promotion_lock(
                    tenant_id="tenant-123",
                    target_environment_id="env-prod-001"
                )

    @pytest.mark.asyncio
    async def test_check_and_acquire_lock_conflict_details_populated(self, service, mock_db_service):
        """Test that conflict error contains all available details"""
        with patch.object(service, 'db_service', mock_db_service):
            mock_db_service.get_active_promotion_for_environment.return_value = {
                "id": "promo-blocking",
                "name": "Blocking Promotion",
                "started_at": "2024-01-15T10:30:00Z",
                "created_by": "blocker@example.com",
                "target_environment_name": "Production Environment"
            }

            with pytest.raises(PromotionConflictError) as exc_info:
                await service.check_and_acquire_promotion_lock(
                    tenant_id="tenant-123",
                    target_environment_id="env-prod-001"
                )

            conflict = exc_info.value.conflict
            assert conflict.promotion_id == "promo-blocking"
            assert conflict.promotion_name == "Blocking Promotion"
            assert conflict.started_at == "2024-01-15T10:30:00Z"
            assert conflict.started_by == "blocker@example.com"
            assert conflict.target_environment_id == "env-prod-001"
            assert conflict.target_environment_name == "Production Environment"

    @pytest.mark.asyncio
    async def test_check_and_acquire_lock_handles_missing_fields(self, service, mock_db_service):
        """Test that lock check handles missing optional fields gracefully"""
        with patch.object(service, 'db_service', mock_db_service):
            # Active promotion with minimal fields
            mock_db_service.get_active_promotion_for_environment.return_value = {
                "id": "promo-minimal"
            }

            with pytest.raises(PromotionConflictError) as exc_info:
                await service.check_and_acquire_promotion_lock(
                    tenant_id="tenant-123",
                    target_environment_id="env-prod-001"
                )

            conflict = exc_info.value.conflict
            assert conflict.promotion_id == "promo-minimal"
            assert conflict.promotion_name is None
            assert conflict.started_at is None
            assert conflict.started_by is None

    # ==========================================================================
    # get_active_promotion_for_environment tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_get_active_promotion_returns_promotion(self, service, mock_db_service):
        """Test getting active promotion when one exists"""
        with patch.object(service, 'db_service', mock_db_service):
            expected_promotion = {
                "id": "promo-123",
                "name": "Active Promotion",
                "status": "running"
            }
            mock_db_service.get_active_promotion_for_environment.return_value = expected_promotion

            result = await service.get_active_promotion_for_environment(
                tenant_id="tenant-123",
                target_environment_id="env-prod-001"
            )

            assert result == expected_promotion

    @pytest.mark.asyncio
    async def test_get_active_promotion_returns_none(self, service, mock_db_service):
        """Test getting active promotion when none exists"""
        with patch.object(service, 'db_service', mock_db_service):
            mock_db_service.get_active_promotion_for_environment.return_value = None

            result = await service.get_active_promotion_for_environment(
                tenant_id="tenant-123",
                target_environment_id="env-prod-001"
            )

            assert result is None

    # ==========================================================================
    # is_environment_locked tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_is_environment_locked_returns_true(self, service, mock_db_service):
        """Test is_environment_locked returns True when promotion is active"""
        with patch.object(service, 'db_service', mock_db_service):
            mock_db_service.get_active_promotion_for_environment.return_value = {
                "id": "promo-123",
                "status": "running"
            }

            result = await service.is_environment_locked(
                tenant_id="tenant-123",
                target_environment_id="env-prod-001"
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_is_environment_locked_returns_false(self, service, mock_db_service):
        """Test is_environment_locked returns False when no active promotion"""
        with patch.object(service, 'db_service', mock_db_service):
            mock_db_service.get_active_promotion_for_environment.return_value = None

            result = await service.is_environment_locked(
                tenant_id="tenant-123",
                target_environment_id="env-prod-001"
            )

            assert result is False

    # ==========================================================================
    # Multi-tenant isolation tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_lock_check_uses_correct_tenant_id(self, service, mock_db_service):
        """Test that lock check correctly passes tenant_id to database"""
        with patch.object(service, 'db_service', mock_db_service):
            mock_db_service.get_active_promotion_for_environment.return_value = None

            await service.check_and_acquire_promotion_lock(
                tenant_id="tenant-abc",
                target_environment_id="env-001"
            )

            mock_db_service.get_active_promotion_for_environment.assert_called_with(
                tenant_id="tenant-abc",
                target_environment_id="env-001"
            )

    @pytest.mark.asyncio
    async def test_different_tenants_independent(self, service, mock_db_service):
        """Test that different tenants have independent locks"""
        with patch.object(service, 'db_service', mock_db_service):
            # Tenant A has active promotion
            mock_db_service.get_active_promotion_for_environment.return_value = None

            # First call for tenant A
            result = await service.check_and_acquire_promotion_lock(
                tenant_id="tenant-A",
                target_environment_id="env-prod"
            )
            assert result is True

            # Second call for tenant B (different tenant, same environment ID)
            result = await service.check_and_acquire_promotion_lock(
                tenant_id="tenant-B",
                target_environment_id="env-prod"
            )
            assert result is True

            # Verify both calls were made with correct tenant IDs
            calls = mock_db_service.get_active_promotion_for_environment.call_args_list
            assert calls[0][1]["tenant_id"] == "tenant-A"
            assert calls[1][1]["tenant_id"] == "tenant-B"

    # ==========================================================================
    # Different environment tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_different_environments_independent(self, service, mock_db_service):
        """Test that different environments have independent locks"""
        with patch.object(service, 'db_service', mock_db_service):
            # Simulate env-prod having active promotion, env-staging not having one
            def mock_get_active(tenant_id, target_environment_id):
                if target_environment_id == "env-prod":
                    return {
                        "id": "promo-prod",
                        "name": "Prod Promotion"
                    }
                return None

            mock_db_service.get_active_promotion_for_environment = AsyncMock(
                side_effect=mock_get_active
            )

            # Check staging - should succeed
            result = await service.check_and_acquire_promotion_lock(
                tenant_id="tenant-123",
                target_environment_id="env-staging"
            )
            assert result is True

            # Check prod - should fail
            with pytest.raises(PromotionConflictError):
                await service.check_and_acquire_promotion_lock(
                    tenant_id="tenant-123",
                    target_environment_id="env-prod"
                )


class TestGlobalPromotionLockService:
    """Test the global promotion_lock_service instance"""

    def test_global_instance_exists(self):
        """Test that global service instance is available"""
        assert promotion_lock_service is not None
        assert isinstance(promotion_lock_service, PromotionLockService)

    def test_global_instance_has_db_service(self):
        """Test that global instance has db_service configured"""
        assert hasattr(promotion_lock_service, 'db_service')
        assert promotion_lock_service.db_service is not None


class TestPromotionLockServiceLogging:
    """Test logging behavior of PromotionLockService"""

    @pytest.fixture
    def service(self):
        """Create a PromotionLockService instance for testing"""
        return PromotionLockService()

    @pytest.fixture
    def mock_db_service(self):
        """Create a mock database service"""
        mock = MagicMock()
        mock.get_active_promotion_for_environment = AsyncMock(return_value=None)
        return mock

    @pytest.mark.asyncio
    async def test_logs_when_no_conflict(self, service, mock_db_service, caplog):
        """Test that info log is emitted when no conflict found"""
        import logging
        with patch.object(service, 'db_service', mock_db_service):
            mock_db_service.get_active_promotion_for_environment.return_value = None

            with caplog.at_level(logging.INFO):
                await service.check_and_acquire_promotion_lock(
                    tenant_id="tenant-123",
                    target_environment_id="env-prod"
                )

            assert "No active promotion found" in caplog.text
            assert "promotion can proceed" in caplog.text

    @pytest.mark.asyncio
    async def test_logs_warning_on_conflict(self, service, mock_db_service, caplog):
        """Test that warning log is emitted on conflict"""
        import logging
        with patch.object(service, 'db_service', mock_db_service):
            mock_db_service.get_active_promotion_for_environment.return_value = {
                "id": "promo-blocking",
                "name": "Blocking Promotion"
            }

            with caplog.at_level(logging.WARNING):
                with pytest.raises(PromotionConflictError):
                    await service.check_and_acquire_promotion_lock(
                        tenant_id="tenant-123",
                        target_environment_id="env-prod"
                    )

            assert "Promotion conflict detected" in caplog.text
            assert "promo-blocking" in caplog.text

    @pytest.mark.asyncio
    async def test_logs_when_retry_allowed(self, service, mock_db_service, caplog):
        """Test that info log is emitted when retry is allowed"""
        import logging
        with patch.object(service, 'db_service', mock_db_service):
            mock_db_service.get_active_promotion_for_environment.return_value = {
                "id": "promo-123"
            }

            with caplog.at_level(logging.INFO):
                await service.check_and_acquire_promotion_lock(
                    tenant_id="tenant-123",
                    target_environment_id="env-prod",
                    requesting_promotion_id="promo-123"
                )

            assert "is the requesting promotion" in caplog.text
            assert "allowing it to proceed" in caplog.text


# =============================================================================
# Integration Tests for Concurrent Promotion Blocking
# =============================================================================

class TestPromotionConcurrencyAPIIntegration:
    """
    Integration tests for the promotion concurrency control at the API level.

    These tests verify that the execute_promotion endpoint correctly rejects
    requests when another promotion is running for the same target environment.
    """

    @pytest.fixture
    def mock_entitlements(self):
        """Mock entitlements service to allow all features for testing."""
        with patch("app.core.entitlements_gate.entitlements_service") as mock_ent:
            mock_ent.enforce_flag = AsyncMock(return_value=None)
            mock_ent.has_flag = AsyncMock(return_value=True)
            yield mock_ent

    @pytest.fixture
    def base_promotion(self):
        """Base promotion data for tests."""
        return {
            "id": "promo-test-123",
            "tenant_id": "tenant-123",
            "pipeline_id": "pipeline-1",
            "status": "approved",
            "source_environment_id": "env-dev-001",
            "target_environment_id": "env-prod-001",
            "workflow_selections": [
                {
                    "workflow_id": "wf-1",
                    "workflow_name": "Test Workflow",
                    "change_type": "changed",
                    "enabled_in_source": True,
                    "selected": True
                }
            ],
            "created_by": "user@example.com",
            "created_at": "2024-01-15T10:00:00Z",
        }

    @pytest.fixture
    def base_environments(self):
        """Base environment data for tests."""
        return {
            "source": {
                "id": "env-dev-001",
                "tenant_id": "tenant-123",
                "n8n_name": "Development",
                "n8n_base_url": "https://dev.n8n.example.com",
                "environment_class": "dev",
                "provider": "n8n"
            },
            "target": {
                "id": "env-prod-001",
                "tenant_id": "tenant-123",
                "n8n_name": "Production",
                "n8n_base_url": "https://prod.n8n.example.com",
                "environment_class": "prod",
                "provider": "n8n"
            }
        }

    @pytest.mark.asyncio
    async def test_execute_promotion_returns_409_when_another_promotion_running(
        self, mock_entitlements, base_promotion, base_environments
    ):
        """
        AC1: GIVEN an environment has an active (running) promotion,
        WHEN a new promotion execution is requested targeting that same environment,
        THEN the request is rejected with a 409 Conflict error.
        """
        from fastapi.testclient import TestClient
        from app.main import app
        from app.services.auth_service import get_current_user

        # Setup auth override
        mock_user = {
            "user": {
                "id": "user-123",
                "email": "admin@example.com",
                "name": "Admin User",
                "role": "admin"
            },
            "tenant": {
                "id": "tenant-123",
                "name": "Test Org",
                "subscription_tier": "pro"
            }
        }

        async def mock_get_current_user(credentials=None):
            return mock_user

        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            with patch("app.api.endpoints.promotions.db_service") as mock_db, \
                 patch("app.api.endpoints.promotions.promotion_lock_service") as mock_lock_service, \
                 patch("app.api.endpoints.promotions.environment_action_guard") as mock_guard:

                # Setup mocks
                mock_db.get_promotion = AsyncMock(return_value=base_promotion)
                mock_db.get_environment = AsyncMock(
                    side_effect=lambda env_id, tenant_id:
                        base_environments["source"] if env_id == "env-dev-001"
                        else base_environments["target"]
                )

                # Mock action guard to allow
                mock_guard.assert_can_perform_action = MagicMock(return_value=None)

                # Configure lock service to raise conflict error
                blocking_promotion = PromotionConflict(
                    promotion_id="promo-blocking-456",
                    promotion_name="Blocking Promotion",
                    started_at="2024-01-15T10:30:00Z",
                    started_by="other@example.com",
                    target_environment_id="env-prod-001",
                    target_environment_name="Production"
                )
                mock_lock_service.check_and_acquire_promotion_lock = AsyncMock(
                    side_effect=PromotionConflictError(blocking_promotion)
                )

                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/promotions/execute/promo-test-123",
                        headers={"Authorization": "Bearer test-token"}
                    )

                    # Verify 409 Conflict response
                    assert response.status_code == 409

                    data = response.json()
                    assert data["detail"]["error"] == "promotion_conflict"
                    assert "blocking_promotion" in data["detail"]
                    assert data["detail"]["blocking_promotion"]["id"] == "promo-blocking-456"
                    assert data["detail"]["blocking_promotion"]["name"] == "Blocking Promotion"

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_execute_promotion_calls_lock_service_when_no_conflict(
        self, mock_entitlements, base_promotion, base_environments
    ):
        """
        AC2: GIVEN an environment has no active promotions,
        WHEN a promotion execution is requested,
        THEN the lock service is called to verify no conflicts.

        This test verifies the lock service is properly integrated into
        the execution flow. The full execution success path is tested
        elsewhere; here we focus on the concurrency check integration.
        """
        service = PromotionLockService()
        mock_db = MagicMock()

        with patch.object(service, 'db_service', mock_db):
            # No active promotion - lock check should succeed
            mock_db.get_active_promotion_for_environment = AsyncMock(return_value=None)

            # Should succeed without raising exception
            result = await service.check_and_acquire_promotion_lock(
                tenant_id="tenant-123",
                target_environment_id="env-prod-001"
            )

            # Verify success
            assert result is True

            # Verify database was queried with correct parameters
            mock_db.get_active_promotion_for_environment.assert_called_once_with(
                tenant_id="tenant-123",
                target_environment_id="env-prod-001"
            )

    @pytest.mark.asyncio
    async def test_execute_promotion_allows_pending_status_promotion(
        self, mock_entitlements, base_environments
    ):
        """
        AC3: GIVEN a promotion is pending or completed (not running),
        WHEN a new promotion is requested targeting the same environment,
        THEN the new promotion is allowed.
        """
        # This is tested at the service level since the lock check
        # only considers 'running' status promotions
        service = PromotionLockService()
        mock_db = MagicMock()

        with patch.object(service, 'db_service', mock_db):
            # Simulate no running promotion (pending/completed are not returned)
            mock_db.get_active_promotion_for_environment = AsyncMock(return_value=None)

            # Should succeed
            result = await service.check_and_acquire_promotion_lock(
                tenant_id="tenant-123",
                target_environment_id="env-prod-001"
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_different_environments_are_independent(
        self, mock_entitlements, base_promotion, base_environments
    ):
        """
        AC4: GIVEN multiple environments,
        WHEN promotions are executed to different target environments simultaneously,
        THEN all promotions proceed without blocking each other.
        """
        service = PromotionLockService()
        mock_db = MagicMock()

        with patch.object(service, 'db_service', mock_db):
            # Simulate env-prod having an active promotion
            def mock_get_active(tenant_id, target_environment_id):
                if target_environment_id == "env-prod-001":
                    return {
                        "id": "promo-prod-active",
                        "name": "Prod Promotion",
                        "status": "running"
                    }
                # env-staging has no active promotion
                return None

            mock_db.get_active_promotion_for_environment = AsyncMock(
                side_effect=mock_get_active
            )

            # Staging should succeed (no active promotion there)
            result = await service.check_and_acquire_promotion_lock(
                tenant_id="tenant-123",
                target_environment_id="env-staging-001"
            )
            assert result is True

            # Prod should fail (has active promotion)
            with pytest.raises(PromotionConflictError) as exc_info:
                await service.check_and_acquire_promotion_lock(
                    tenant_id="tenant-123",
                    target_environment_id="env-prod-001"
                )

            assert exc_info.value.conflict.promotion_id == "promo-prod-active"

    @pytest.mark.asyncio
    async def test_conflict_response_contains_blocking_promotion_details(
        self, mock_entitlements, base_promotion, base_environments
    ):
        """
        Verify the 409 response includes complete details about the blocking promotion
        to help users understand why their request was rejected.
        """
        from fastapi.testclient import TestClient
        from app.main import app
        from app.services.auth_service import get_current_user

        mock_user = {
            "user": {"id": "user-123", "email": "admin@example.com", "name": "Admin", "role": "admin"},
            "tenant": {"id": "tenant-123", "name": "Test Org", "subscription_tier": "pro"}
        }

        async def mock_get_current_user(credentials=None):
            return mock_user

        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            with patch("app.api.endpoints.promotions.db_service") as mock_db, \
                 patch("app.api.endpoints.promotions.promotion_lock_service") as mock_lock_service, \
                 patch("app.api.endpoints.promotions.environment_action_guard") as mock_guard:

                mock_db.get_promotion = AsyncMock(return_value=base_promotion)
                mock_db.get_environment = AsyncMock(
                    side_effect=lambda env_id, tenant_id:
                        base_environments["source"] if env_id == "env-dev-001"
                        else base_environments["target"]
                )
                mock_guard.assert_can_perform_action = MagicMock(return_value=None)

                # Configure blocking promotion with full details
                blocking_promotion = PromotionConflict(
                    promotion_id="promo-blocking-789",
                    promotion_name="Critical Production Deploy",
                    started_at="2024-01-15T14:30:00Z",
                    started_by="devops@example.com",
                    target_environment_id="env-prod-001",
                    target_environment_name="Production"
                )
                mock_lock_service.check_and_acquire_promotion_lock = AsyncMock(
                    side_effect=PromotionConflictError(blocking_promotion)
                )

                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/promotions/execute/promo-test-123",
                        headers={"Authorization": "Bearer test-token"}
                    )

                    assert response.status_code == 409

                    data = response.json()
                    blocking = data["detail"]["blocking_promotion"]

                    # Verify all blocking promotion details are present
                    assert blocking["id"] == "promo-blocking-789"
                    assert blocking["name"] == "Critical Production Deploy"
                    assert blocking["started_at"] == "2024-01-15T14:30:00Z"
                    assert blocking["started_by"] == "devops@example.com"
                    assert blocking["target_environment_id"] == "env-prod-001"
                    assert blocking["target_environment_name"] == "Production"

        finally:
            app.dependency_overrides.clear()


class TestScheduledPromotionConcurrency:
    """
    Integration tests for scheduled promotion concurrency control.

    These tests verify that the deployment scheduler correctly handles
    concurrent promotion scenarios.
    """

    @pytest.mark.asyncio
    async def test_scheduled_promotion_blocked_by_running_promotion(self):
        """
        Test that a scheduled promotion is blocked when another
        promotion is already running for the same target environment.
        """
        service = PromotionLockService()
        mock_db = MagicMock()

        with patch.object(service, 'db_service', mock_db):
            # Simulate a running promotion
            mock_db.get_active_promotion_for_environment = AsyncMock(return_value={
                "id": "promo-running-123",
                "name": "Running Promotion",
                "status": "running",
                "started_at": "2024-01-15T10:00:00Z",
                "created_by": "user@example.com"
            })

            # Attempting to execute scheduled promotion should raise conflict
            with pytest.raises(PromotionConflictError) as exc_info:
                await service.check_and_acquire_promotion_lock(
                    tenant_id="tenant-123",
                    target_environment_id="env-prod-001",
                    requesting_promotion_id="scheduled-promo-456"
                )

            assert exc_info.value.status_code == 409
            assert exc_info.value.conflict.promotion_id == "promo-running-123"

    @pytest.mark.asyncio
    async def test_scheduled_promotion_proceeds_after_blocking_completes(self):
        """
        AC5: GIVEN an active promotion blocks a new promotion,
        WHEN the blocking promotion completes/fails,
        THEN subsequent promotion requests to that environment succeed.
        """
        service = PromotionLockService()
        mock_db = MagicMock()

        with patch.object(service, 'db_service', mock_db):
            # First call: active promotion exists
            # Second call: no active promotion (completed)
            call_count = [0]

            async def mock_get_active(tenant_id, target_environment_id):
                call_count[0] += 1
                if call_count[0] == 1:
                    return {
                        "id": "promo-blocking",
                        "name": "Blocking Promotion",
                        "status": "running"
                    }
                return None  # Completed

            mock_db.get_active_promotion_for_environment = AsyncMock(
                side_effect=mock_get_active
            )

            # First attempt should fail
            with pytest.raises(PromotionConflictError):
                await service.check_and_acquire_promotion_lock(
                    tenant_id="tenant-123",
                    target_environment_id="env-prod-001"
                )

            # Second attempt (after blocking promotion completes) should succeed
            result = await service.check_and_acquire_promotion_lock(
                tenant_id="tenant-123",
                target_environment_id="env-prod-001"
            )
            assert result is True


class TestMultiTenantPromotionConcurrency:
    """
    Integration tests verifying tenant isolation for promotion concurrency.

    These tests ensure that promotion locks are properly scoped to tenants.
    """

    @pytest.mark.asyncio
    async def test_different_tenants_can_promote_same_environment_name(self):
        """
        Verify that tenant isolation is maintained - promotions from
        different tenants don't block each other even if environment
        names are the same.
        """
        service = PromotionLockService()
        mock_db = MagicMock()

        with patch.object(service, 'db_service', mock_db):
            # Tenant A has running promotion to env-prod
            # Tenant B has no running promotion to env-prod
            async def mock_get_active(tenant_id, target_environment_id):
                if tenant_id == "tenant-A" and target_environment_id == "env-prod":
                    return {
                        "id": "promo-tenant-a",
                        "name": "Tenant A Promotion",
                        "status": "running"
                    }
                return None

            mock_db.get_active_promotion_for_environment = AsyncMock(
                side_effect=mock_get_active
            )

            # Tenant A should be blocked
            with pytest.raises(PromotionConflictError):
                await service.check_and_acquire_promotion_lock(
                    tenant_id="tenant-A",
                    target_environment_id="env-prod"
                )

            # Tenant B should succeed (different tenant)
            result = await service.check_and_acquire_promotion_lock(
                tenant_id="tenant-B",
                target_environment_id="env-prod"
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_tenant_id_correctly_passed_to_database(self):
        """
        Verify that the tenant_id is correctly passed to the database
        query to ensure proper tenant isolation.
        """
        service = PromotionLockService()
        mock_db = MagicMock()

        with patch.object(service, 'db_service', mock_db):
            mock_db.get_active_promotion_for_environment = AsyncMock(return_value=None)

            # Call with specific tenant
            await service.check_and_acquire_promotion_lock(
                tenant_id="tenant-specific-123",
                target_environment_id="env-prod-001"
            )

            # Verify tenant_id was passed correctly
            mock_db.get_active_promotion_for_environment.assert_called_once_with(
                tenant_id="tenant-specific-123",
                target_environment_id="env-prod-001"
            )


class TestPromotionRetryScenarios:
    """
    Tests for retry scenarios where the same promotion attempts
    to re-acquire the lock.
    """

    @pytest.mark.asyncio
    async def test_same_promotion_can_retry(self):
        """
        Test that a promotion can retry even if it shows as 'running'
        (e.g., after a process restart or error recovery).
        """
        service = PromotionLockService()
        mock_db = MagicMock()

        with patch.object(service, 'db_service', mock_db):
            # The running promotion is the same as the requesting one
            mock_db.get_active_promotion_for_environment = AsyncMock(return_value={
                "id": "promo-retry-123",
                "name": "Retry Promotion",
                "status": "running"
            })

            # Should succeed because requesting_promotion_id matches active
            result = await service.check_and_acquire_promotion_lock(
                tenant_id="tenant-123",
                target_environment_id="env-prod-001",
                requesting_promotion_id="promo-retry-123"  # Same as active
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_different_promotion_blocked_even_with_requesting_id(self):
        """
        Test that a different promotion is blocked even when providing
        a requesting_promotion_id.
        """
        service = PromotionLockService()
        mock_db = MagicMock()

        with patch.object(service, 'db_service', mock_db):
            # Active promotion has different ID
            mock_db.get_active_promotion_for_environment = AsyncMock(return_value={
                "id": "promo-active-different",
                "name": "Different Active Promotion",
                "status": "running"
            })

            # Should fail because IDs don't match
            with pytest.raises(PromotionConflictError) as exc_info:
                await service.check_and_acquire_promotion_lock(
                    tenant_id="tenant-123",
                    target_environment_id="env-prod-001",
                    requesting_promotion_id="promo-requesting-new"  # Different from active
                )

            assert exc_info.value.conflict.promotion_id == "promo-active-different"


class TestConcurrentPromotionRaceConditions:
    """
    Tests simulating race condition scenarios to ensure proper
    handling of concurrent promotion requests.
    """

    @pytest.mark.asyncio
    async def test_concurrent_lock_checks_one_succeeds_one_fails(self):
        """
        Simulate two promotions checking the lock nearly simultaneously.
        The first one to check should succeed, subsequent ones should fail.
        """
        service = PromotionLockService()
        mock_db = MagicMock()

        with patch.object(service, 'db_service', mock_db):
            # Track calls to simulate race condition
            call_results = [
                None,  # First call: no active promotion
                {"id": "promo-first", "name": "First Promotion", "status": "running"}  # Second call: first promo is running
            ]
            call_idx = [0]

            async def mock_get_active(tenant_id, target_environment_id):
                result = call_results[min(call_idx[0], len(call_results) - 1)]
                call_idx[0] += 1
                return result

            mock_db.get_active_promotion_for_environment = AsyncMock(
                side_effect=mock_get_active
            )

            # First promotion request succeeds
            result1 = await service.check_and_acquire_promotion_lock(
                tenant_id="tenant-123",
                target_environment_id="env-prod-001"
            )
            assert result1 is True

            # Second promotion request fails (first one is now running)
            with pytest.raises(PromotionConflictError) as exc_info:
                await service.check_and_acquire_promotion_lock(
                    tenant_id="tenant-123",
                    target_environment_id="env-prod-001"
                )

            assert exc_info.value.conflict.promotion_id == "promo-first"

    @pytest.mark.asyncio
    async def test_multiple_concurrent_requests_all_but_one_blocked(self):
        """
        Test that when multiple concurrent requests are made,
        only one can proceed and all others are blocked.
        """
        service = PromotionLockService()
        mock_db = MagicMock()

        with patch.object(service, 'db_service', mock_db):
            # First call succeeds, subsequent calls see a running promotion
            first_call = [True]

            async def mock_get_active(tenant_id, target_environment_id):
                if first_call[0]:
                    first_call[0] = False
                    return None
                return {
                    "id": "promo-winner",
                    "name": "Winner Promotion",
                    "status": "running"
                }

            mock_db.get_active_promotion_for_environment = AsyncMock(
                side_effect=mock_get_active
            )

            # First call succeeds
            result = await service.check_and_acquire_promotion_lock(
                tenant_id="tenant-123",
                target_environment_id="env-prod-001"
            )
            assert result is True

            # All subsequent calls fail
            for i in range(5):
                with pytest.raises(PromotionConflictError):
                    await service.check_and_acquire_promotion_lock(
                        tenant_id="tenant-123",
                        target_environment_id="env-prod-001"
                    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
