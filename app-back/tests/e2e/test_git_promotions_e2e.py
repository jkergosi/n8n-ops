"""
E2E tests for Git-Based Promotions API.

Tests the complete Git-based promotion system:
1. Promotion flow (DEV → STAGING, STAGING → PROD with approval)
2. Rollback flow (with PROD approval gate)
3. Backup flow (snapshot without pointer update)
4. Snapshot listing and current pointer

These tests mock the service layer to test API request/response handling.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.auth_service import get_current_user
from app.services.git_promotion_service import PromotionResult, RollbackResult, PromotionStatus

pytestmark = pytest.mark.asyncio


# ============== TEST AUTH/ENTITLEMENTS FIXTURES ==============

# Use valid UUIDs for all test IDs (database expects UUID format)
MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000001"
MOCK_USER_ID = "00000000-0000-0000-0000-000000000002"
MOCK_DEV_ENV_ID = "00000000-0000-0000-0000-000000000010"
MOCK_STAGING_ENV_ID = "00000000-0000-0000-0000-000000000011"
MOCK_PROD_ENV_ID = "00000000-0000-0000-0000-000000000012"


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user response."""
    return {
        "user": {
            "id": MOCK_USER_ID,
            "email": "test@example.com",
            "name": "Test User",
            "role": "admin",
        },
        "tenant": {
            "id": MOCK_TENANT_ID,
            "name": "Test Tenant",
            "subscription_tier": "pro",
        }
    }


def create_auth_override(user_data):
    """Create auth override function."""
    async def mock_get_current_user():
        return user_data
    return mock_get_current_user


@pytest.fixture
async def test_client(mock_auth_user):
    """Create async test client with auth and entitlement mocks."""
    # Override auth dependency
    app.dependency_overrides[get_current_user] = create_auth_override(mock_auth_user)

    # Mock entitlements service to allow access
    with patch('app.services.entitlements_service.entitlements_service.enforce_flag', new_callable=AsyncMock) as mock_enforce:
        mock_enforce.return_value = None  # No exception = allowed

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    # Clean up
    app.dependency_overrides.clear()


# ============== ENVIRONMENT FIXTURES ==============

@pytest.fixture
def dev_environment():
    """Development environment config."""
    return {
        "id": MOCK_DEV_ENV_ID,
        "tenant_id": MOCK_TENANT_ID,
        "n8n_name": "Development",
        "n8n_type": "development",
        "n8n_base_url": "https://dev.n8n.example.com",
        "n8n_api_key": "dev-api-key",
        "git_repo_url": "https://github.com/test/workflows",
        "git_pat": "ghp_test_token",
        "git_branch": "main",
        "environment_class": "DEV",
        "is_active": True,
    }


@pytest.fixture
def staging_environment():
    """Staging environment config."""
    return {
        "id": MOCK_STAGING_ENV_ID,
        "tenant_id": MOCK_TENANT_ID,
        "n8n_name": "Staging",
        "n8n_type": "staging",
        "n8n_base_url": "https://staging.n8n.example.com",
        "n8n_api_key": "staging-api-key",
        "git_repo_url": "https://github.com/test/workflows",
        "git_pat": "ghp_test_token",
        "git_branch": "main",
        "environment_class": "STAGING",
        "is_active": True,
    }


@pytest.fixture
def prod_environment():
    """Production environment config."""
    return {
        "id": MOCK_PROD_ENV_ID,
        "tenant_id": MOCK_TENANT_ID,
        "n8n_name": "Production",
        "n8n_type": "production",
        "n8n_base_url": "https://prod.n8n.example.com",
        "n8n_api_key": "prod-api-key",
        "git_repo_url": "https://github.com/test/workflows",
        "git_pat": "ghp_test_token",
        "git_branch": "main",
        "environment_class": "PROD",
        "is_active": True,
    }


# ============== PROMOTION TESTS ==============

class TestGitPromotionInitiate:
    """Tests for promotion initiation endpoint."""

    async def test_initiate_dev_to_staging_success(
        self,
        test_client,
        dev_environment,
        staging_environment,
    ):
        """Test initiating promotion from DEV to STAGING completes immediately."""
        # Mock the service method directly
        mock_result = PromotionResult(
            success=True,
            promotion_id="00000000-0000-0000-0000-000000000100",
            snapshot_id="snap-new-123",
            commit_sha="commit-abc",
            status=PromotionStatus.COMPLETED,
            workflows_promoted=2,
            requires_approval=False,
            verification_passed=True,
            pointer_updated=True,
        )

        with patch('app.api.endpoints.git_promotions.git_promotion_service.initiate_promotion',
                   new_callable=AsyncMock, return_value=mock_result):
            response = await test_client.post(
                "/api/v1/git-promotions/initiate",
                json={
                    "source_environment_id": dev_environment["id"],
                    "target_environment_id": staging_environment["id"],
                    "workflow_ids": [],
                    "reason": "Test promotion",
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "completed"
            assert data["requires_approval"] is False

    async def test_initiate_staging_to_prod_requires_approval(
        self,
        test_client,
        staging_environment,
        prod_environment,
    ):
        """Test initiating promotion from STAGING to PROD returns PENDING_APPROVAL."""
        mock_result = PromotionResult(
            success=True,
            promotion_id="00000000-0000-0000-0000-000000000101",
            snapshot_id="snap-prod-001",
            commit_sha="commit-prod",
            status=PromotionStatus.PENDING_APPROVAL,
            workflows_promoted=0,
            requires_approval=True,
            verification_passed=False,
            pointer_updated=False,
        )

        with patch('app.api.endpoints.git_promotions.git_promotion_service.initiate_promotion',
                   new_callable=AsyncMock, return_value=mock_result):
            response = await test_client.post(
                "/api/v1/git-promotions/initiate",
                json={
                    "source_environment_id": staging_environment["id"],
                    "target_environment_id": prod_environment["id"],
                    "workflow_ids": [],
                    "reason": "Deploy to production",
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "pending_approval"
            assert data["requires_approval"] is True

    async def test_initiate_promotion_validation_error(
        self,
        test_client,
    ):
        """Test that missing required fields return 422."""
        response = await test_client.post(
            "/api/v1/git-promotions/initiate",
            json={}  # Missing required fields
        )

        assert response.status_code == 422


class TestGitPromotionApproval:
    """Tests for promotion approval endpoint."""

    async def test_approve_pending_promotion_success(
        self,
        test_client,
    ):
        """Test approving a pending promotion executes deployment."""
        promotion_id = "00000000-0000-0000-0000-000000000100"

        mock_result = PromotionResult(
            success=True,
            promotion_id=promotion_id,
            snapshot_id="snap-prod-001",
            commit_sha="commit-123",
            status=PromotionStatus.COMPLETED,
            workflows_promoted=2,
            requires_approval=False,
            verification_passed=True,
            pointer_updated=True,
        )

        with patch('app.api.endpoints.git_promotions.git_promotion_service.approve_and_execute',
                   new_callable=AsyncMock, return_value=mock_result):
            response = await test_client.post(
                f"/api/v1/git-promotions/{promotion_id}/approve"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "completed"

    async def test_reject_pending_promotion(
        self,
        test_client,
    ):
        """Test rejecting a pending promotion."""
        promotion_id = "00000000-0000-0000-0000-000000000100"

        # Reject endpoint directly updates DB, so we mock db_service
        with patch('app.api.endpoints.git_promotions.db_service') as mock_db:
            mock_db.client = MagicMock()
            mock_db.client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data={"id": promotion_id, "status": "rejected"}
            )

            response = await test_client.post(
                f"/api/v1/git-promotions/{promotion_id}/reject",
                json={"reason": "Not ready for production"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


# ============== ROLLBACK TESTS ==============

class TestGitRollback:
    """Tests for rollback endpoints."""

    async def test_rollback_staging_immediate(
        self,
        test_client,
        staging_environment,
    ):
        """Test rollback on STAGING executes immediately without approval."""
        mock_result = RollbackResult(
            success=True,
            rollback_id="00000000-0000-0000-0000-000000000200",
            snapshot_id="snap-001",
            commit_sha="commit-rollback",
            status=PromotionStatus.COMPLETED,
            workflows_deployed=2,
            requires_approval=False,
            verification_passed=True,
            pointer_updated=True,
        )

        with patch('app.api.endpoints.git_promotions.git_promotion_service.initiate_rollback',
                   new_callable=AsyncMock, return_value=mock_result):
            response = await test_client.post(
                "/api/v1/git-promotions/rollback/initiate",
                json={
                    "environment_id": staging_environment["id"],
                    "snapshot_id": "snap-001",
                    "reason": "Rollback due to issues",
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["requires_approval"] is False

    async def test_rollback_prod_requires_approval(
        self,
        test_client,
        prod_environment,
    ):
        """Test rollback on PROD returns PENDING_APPROVAL."""
        mock_result = RollbackResult(
            success=True,
            rollback_id="00000000-0000-0000-0000-000000000201",
            snapshot_id="snap-prod-old",
            commit_sha=None,
            status=PromotionStatus.PENDING_APPROVAL,
            workflows_deployed=0,
            requires_approval=True,
            verification_passed=False,
            pointer_updated=False,
        )

        with patch('app.api.endpoints.git_promotions.git_promotion_service.initiate_rollback',
                   new_callable=AsyncMock, return_value=mock_result):
            response = await test_client.post(
                "/api/v1/git-promotions/rollback/initiate",
                json={
                    "environment_id": prod_environment["id"],
                    "snapshot_id": "snap-prod-old",
                    "reason": "Emergency rollback",
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "pending_approval"
            assert data["requires_approval"] is True

    async def test_approve_rollback(
        self,
        test_client,
    ):
        """Test approving a pending rollback."""
        rollback_id = "00000000-0000-0000-0000-000000000201"

        mock_result = RollbackResult(
            success=True,
            rollback_id=rollback_id,
            snapshot_id="snap-prod-old",
            commit_sha="commit-rollback",
            status=PromotionStatus.COMPLETED,
            workflows_deployed=5,
            requires_approval=False,
            verification_passed=True,
            pointer_updated=True,
        )

        with patch('app.api.endpoints.git_promotions.git_promotion_service.approve_and_execute_rollback',
                   new_callable=AsyncMock, return_value=mock_result):
            response = await test_client.post(
                f"/api/v1/git-promotions/rollback/{rollback_id}/approve"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "completed"


# ============== BACKUP TESTS ==============

class TestGitBackup:
    """Tests for backup endpoints."""

    async def test_create_backup_success(
        self,
        test_client,
        staging_environment,
    ):
        """Test creating a backup snapshot."""
        with patch('app.api.endpoints.git_promotions.git_promotion_service.create_backup',
                   new_callable=AsyncMock, return_value={
                       "success": True,
                       "backup_id": "00000000-0000-0000-0000-000000000300",
                       "snapshot_id": "snap-backup-001",
                       "commit_sha": "commit-backup",
                   }):
            response = await test_client.post(
                "/api/v1/git-promotions/backup/create",
                json={
                    "environment_id": staging_environment["id"],
                    "reason": "Pre-deployment backup",
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "snapshot_id" in data
            assert "commit_sha" in data

    async def test_list_backups(
        self,
        test_client,
        staging_environment,
    ):
        """Test listing backup records."""
        with patch('app.api.endpoints.git_promotions.git_promotion_service.list_backups',
                   new_callable=AsyncMock, return_value=[
                       {"id": "backup-1", "snapshot_id": "snap-001", "created_at": "2025-01-01T00:00:00Z"},
                       {"id": "backup-2", "snapshot_id": "snap-002", "created_at": "2025-01-10T00:00:00Z"},
                   ]):
            response = await test_client.get(
                f"/api/v1/git-promotions/backups?environment_id={staging_environment['id']}"
            )

            assert response.status_code == 200
            data = response.json()
            assert "backups" in data
            assert data["count"] == 2


# ============== SNAPSHOT INFO TESTS ==============

class TestSnapshotInfo:
    """Tests for snapshot info endpoints."""

    async def test_list_environment_snapshots(
        self,
        test_client,
        staging_environment,
    ):
        """Test listing available snapshots for an environment."""
        with patch('app.api.endpoints.git_promotions.git_promotion_service.get_available_snapshots',
                   new_callable=AsyncMock, return_value=[
                       {"snapshot_id": "snap-001", "kind": "onboarding", "created_at": "2025-01-01"},
                       {"snapshot_id": "snap-002", "kind": "promotion", "created_at": "2025-01-10"},
                       {"snapshot_id": "snap-003", "kind": "backup", "created_at": "2025-01-15"},
                   ]):
            response = await test_client.get(
                f"/api/v1/git-promotions/environments/{staging_environment['id']}/snapshots"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["environment_id"] == staging_environment["id"]
            assert data["count"] == 3
            assert len(data["snapshots"]) == 3

    async def test_get_current_snapshot(
        self,
        test_client,
        staging_environment,
    ):
        """Test getting current snapshot info for an environment."""
        with patch('app.api.endpoints.git_promotions.git_promotion_service.get_current_snapshot_info',
                   new_callable=AsyncMock, return_value={
                       "current_snapshot_id": "snap-002",
                       "snapshot_commit": "commit-123",
                       "updated_at": "2025-01-10T00:00:00Z",
                       "updated_by": "user-001",
                   }):
            response = await test_client.get(
                f"/api/v1/git-promotions/environments/{staging_environment['id']}/current"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["environment_id"] == staging_environment["id"]
            assert data["is_onboarded"] is True
            assert data["current_snapshot_id"] == "snap-002"

    async def test_get_current_snapshot_new_environment(
        self,
        test_client,
        staging_environment,
    ):
        """Test getting current snapshot for a NEW (not onboarded) environment."""
        with patch('app.api.endpoints.git_promotions.git_promotion_service.get_current_snapshot_info',
                   new_callable=AsyncMock, return_value=None):
            response = await test_client.get(
                f"/api/v1/git-promotions/environments/{staging_environment['id']}/current"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_onboarded"] is False
            assert data["current_snapshot_id"] is None


# ============== PROMOTION LIST/GET TESTS ==============

class TestPromotionListGet:
    """Tests for listing and getting promotions."""

    async def test_list_promotions(self, test_client):
        """Test listing promotions."""
        with patch('app.api.endpoints.git_promotions.db_service') as mock_db:
            mock_db.client = MagicMock()
            mock_db.client.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
                data=[
                    {"id": "promo-1", "status": "completed", "created_at": "2025-01-01T00:00:00Z"},
                    {"id": "promo-2", "status": "pending_approval", "created_at": "2025-01-10T00:00:00Z"},
                ]
            )

            response = await test_client.get("/api/v1/git-promotions/")

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert len(data["items"]) == 2

    async def test_get_promotion_details(self, test_client):
        """Test getting promotion details."""
        promotion_id = "00000000-0000-0000-0000-000000000100"

        with patch('app.api.endpoints.git_promotions.db_service') as mock_db:
            mock_db.client = MagicMock()
            mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={
                    "id": promotion_id,
                    "status": "completed",
                    "source_environment_id": MOCK_DEV_ENV_ID,
                    "target_environment_id": MOCK_STAGING_ENV_ID,
                    "snapshot_id": "snap-123",
                    "workflows_count": 5,
                }
            )

            response = await test_client.get(f"/api/v1/git-promotions/{promotion_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == promotion_id
            assert data["status"] == "completed"


# ============== ERROR HANDLING TESTS ==============

class TestErrorHandling:
    """Tests for error handling."""

    async def test_initiate_promotion_service_error(
        self,
        test_client,
        dev_environment,
        staging_environment,
    ):
        """Test that service errors are handled properly."""
        mock_result = PromotionResult(
            success=False,
            promotion_id="00000000-0000-0000-0000-000000000999",
            status=PromotionStatus.FAILED,
            error="Source environment not onboarded",
        )

        with patch('app.api.endpoints.git_promotions.git_promotion_service.initiate_promotion',
                   new_callable=AsyncMock, return_value=mock_result):
            response = await test_client.post(
                "/api/v1/git-promotions/initiate",
                json={
                    "source_environment_id": dev_environment["id"],
                    "target_environment_id": staging_environment["id"],
                    "workflow_ids": [],
                    "reason": "Test promotion",
                }
            )

            # Service errors return 400
            assert response.status_code == 400
            data = response.json()
            assert "error" in data or "detail" in data
