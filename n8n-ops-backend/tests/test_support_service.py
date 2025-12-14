"""
Unit tests for the support service - issue contract building, n8n forwarding, and config management.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from app.services.support_service import SupportService
from app.schemas.support import (
    SupportRequestCreate,
    BugReportCreate,
    FeatureRequestCreate,
    HelpRequestCreate,
    IntentKind,
    Severity,
    Frequency,
    SupportConfigUpdate,
)


@pytest.fixture
def support_service():
    """Create a SupportService instance."""
    return SupportService()


@pytest.fixture
def mock_db():
    """Mock database service."""
    with patch("app.services.support_service.db_service") as mock:
        yield mock


# ============ Build Issue Contract Tests ============


class TestBuildIssueContract:
    """Tests for building Issue Contract v1 from support requests."""

    @pytest.mark.unit
    def test_build_bug_report_contract(self, support_service):
        """Should build a valid Issue Contract from a bug report."""
        bug_report = BugReportCreate(
            title="Button not working",
            what_happened="Clicked the submit button but nothing happened",
            expected_behavior="Form should submit",
            steps_to_reproduce="1. Open form\n2. Click submit",
            severity=Severity.SEV3,
            frequency=Frequency.ALWAYS,
            include_diagnostics=True,
        )

        request = SupportRequestCreate(
            intent_kind=IntentKind.BUG,
            bug_report=bug_report,
        )

        contract = support_service.build_issue_contract(
            request=request,
            user_email="test@example.com",
            user_id="user-123",
            tenant_id="tenant-456",
        )

        assert contract.schema_version == "1.0"
        assert contract.intent.kind == IntentKind.BUG
        assert contract.intent.title == "Button not working"
        assert "What happened" in contract.intent.description
        assert "Expected behavior" in contract.intent.description
        assert contract.context.tenant_id == "tenant-456"
        assert contract.source.actor.email == "test@example.com"
        assert contract.impact.severity == Severity.SEV3
        assert contract.impact.frequency == Frequency.ALWAYS

    @pytest.mark.unit
    def test_build_feature_request_contract(self, support_service):
        """Should build a valid Issue Contract from a feature request."""
        feature_request = FeatureRequestCreate(
            title="Add dark mode",
            problem_goal="UI too bright at night",
            desired_outcome="Toggle for dark theme",
            priority="high",
            acceptance_criteria=["Toggle in settings", "Dark theme on all pages"],
            who_is_this_for="All users",
        )

        request = SupportRequestCreate(
            intent_kind=IntentKind.FEATURE,
            feature_request=feature_request,
        )

        contract = support_service.build_issue_contract(
            request=request,
            user_email="test@example.com",
            user_id="user-123",
            tenant_id="tenant-456",
        )

        assert contract.schema_version == "1.0"
        assert contract.intent.kind == IntentKind.FEATURE
        assert contract.intent.title == "Add dark mode"
        assert "Problem/Goal" in contract.intent.description
        assert "Desired outcome" in contract.intent.description
        assert contract.intent.acceptance_criteria == ["Toggle in settings", "Dark theme on all pages"]
        assert contract.impact is None  # Feature requests don't have severity

    @pytest.mark.unit
    def test_build_help_request_contract(self, support_service):
        """Should build a valid Issue Contract from a help request (task)."""
        help_request = HelpRequestCreate(
            title="How do I configure webhooks?",
            details="Need help setting up webhook integration",
            include_diagnostics=False,
        )

        request = SupportRequestCreate(
            intent_kind=IntentKind.TASK,
            help_request=help_request,
        )

        contract = support_service.build_issue_contract(
            request=request,
            user_email="test@example.com",
            user_id="user-123",
            tenant_id="tenant-456",
        )

        assert contract.schema_version == "1.0"
        assert contract.intent.kind == IntentKind.TASK
        assert contract.intent.title == "How do I configure webhooks?"
        assert contract.intent.description == "Need help setting up webhook integration"

    @pytest.mark.unit
    def test_build_contract_with_diagnostics(self, support_service):
        """Should include diagnostics in the contract when provided."""
        bug_report = BugReportCreate(
            title="Error on page",
            what_happened="Got an error",
            expected_behavior="No error",
            include_diagnostics=True,
        )

        request = SupportRequestCreate(
            intent_kind=IntentKind.BUG,
            bug_report=bug_report,
        )

        diagnostics = {
            "app_env": "production",
            "app_version": "1.2.3",
            "git_sha": "abc123",
            "route": "/dashboard",
            "correlation_id": "corr-456",
        }

        contract = support_service.build_issue_contract(
            request=request,
            user_email="test@example.com",
            user_id="user-123",
            tenant_id="tenant-456",
            diagnostics=diagnostics,
        )

        assert contract.app.app_env == "production"
        assert contract.app.app_version == "1.2.3"
        assert contract.app.git_sha == "abc123"
        assert contract.context.route == "/dashboard"
        assert contract.context.correlation_id == "corr-456"

    @pytest.mark.unit
    def test_build_contract_missing_data_raises_error(self, support_service):
        """Should raise ValueError when intent_kind doesn't match provided data."""
        # Bug request but no bug_report data
        request = SupportRequestCreate(
            intent_kind=IntentKind.BUG,
            bug_report=None,
        )

        with pytest.raises(ValueError) as exc_info:
            support_service.build_issue_contract(
                request=request,
                user_email="test@example.com",
                user_id="user-123",
                tenant_id="tenant-456",
            )

        assert "missing corresponding data" in str(exc_info.value)

    @pytest.mark.unit
    def test_build_contract_includes_unique_ids(self, support_service):
        """Should generate unique event_id and created_at timestamp."""
        bug_report = BugReportCreate(
            title="Test bug",
            what_happened="Something",
            expected_behavior="Something else",
            include_diagnostics=False,
        )

        request = SupportRequestCreate(
            intent_kind=IntentKind.BUG,
            bug_report=bug_report,
        )

        contract1 = support_service.build_issue_contract(
            request=request,
            user_email="test@example.com",
            user_id="user-123",
            tenant_id="tenant-456",
        )

        contract2 = support_service.build_issue_contract(
            request=request,
            user_email="test@example.com",
            user_id="user-123",
            tenant_id="tenant-456",
        )

        # Each contract should have unique IDs
        assert contract1.event_id != contract2.event_id
        assert contract1.created_at is not None
        assert contract2.created_at is not None


# ============ Forward to n8n Tests ============


class TestForwardToN8n:
    """Tests for forwarding Issue Contracts to n8n webhook."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_forward_returns_mock_key_when_no_webhook_configured(self, support_service, mock_db):
        """Should return a mock JSM key when no webhook URL is configured."""
        mock_db.get_support_config = AsyncMock(return_value=None)

        bug_report = BugReportCreate(
            title="Test bug",
            what_happened="Something",
            expected_behavior="Something else",
            include_diagnostics=False,
        )

        request = SupportRequestCreate(
            intent_kind=IntentKind.BUG,
            bug_report=bug_report,
        )

        contract = support_service.build_issue_contract(
            request=request,
            user_email="test@example.com",
            user_id="user-123",
            tenant_id="tenant-456",
        )

        response = await support_service.forward_to_n8n(contract, "tenant-456")

        assert response.jsm_request_key.startswith("SUP-")
        assert len(response.jsm_request_key) == 10  # SUP- + 6 hex chars

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_forward_calls_webhook_when_configured(self, support_service, mock_db):
        """Should POST to n8n webhook when URL is configured."""
        mock_db.get_support_config = AsyncMock(return_value={
            "tenant_id": "tenant-456",
            "n8n_webhook_url": "https://n8n.example.com/webhook/support",
        })

        bug_report = BugReportCreate(
            title="Test bug",
            what_happened="Something",
            expected_behavior="Something else",
            include_diagnostics=False,
        )

        request = SupportRequestCreate(
            intent_kind=IntentKind.BUG,
            bug_report=bug_report,
        )

        contract = support_service.build_issue_contract(
            request=request,
            user_email="test@example.com",
            user_id="user-123",
            tenant_id="tenant-456",
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"jsmRequestKey": "JSM-12345"}
            mock_response.raise_for_status = MagicMock()

            mock_client = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = await support_service.forward_to_n8n(contract, "tenant-456")

            assert response.jsm_request_key == "JSM-12345"
            mock_client.post.assert_called_once()


# ============ Config Management Tests ============


class TestConfigManagement:
    """Tests for support configuration management."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_config_returns_none_when_not_found(self, support_service, mock_db):
        """Should return None when no config exists for tenant."""
        mock_db.get_support_config = AsyncMock(return_value=None)

        config = await support_service.get_config("tenant-456")

        assert config is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_config_returns_response_model(self, support_service, mock_db):
        """Should return SupportConfigResponse when config exists."""
        mock_db.get_support_config = AsyncMock(return_value={
            "tenant_id": "tenant-456",
            "n8n_webhook_url": "https://n8n.example.com/webhook",
            "jsm_portal_url": "https://support.atlassian.net",
        })

        config = await support_service.get_config("tenant-456")

        assert config is not None
        assert config.tenant_id == "tenant-456"
        assert config.n8n_webhook_url == "https://n8n.example.com/webhook"
        assert config.jsm_portal_url == "https://support.atlassian.net"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_config_upserts_data(self, support_service, mock_db):
        """Should upsert configuration data."""
        mock_db.upsert_support_config = AsyncMock(return_value={
            "tenant_id": "tenant-456",
            "n8n_webhook_url": "https://new-webhook.example.com",
            "updated_at": datetime.utcnow().isoformat(),
        })

        update_data = SupportConfigUpdate(
            n8n_webhook_url="https://new-webhook.example.com",
        )

        config = await support_service.update_config("tenant-456", update_data)

        assert config.n8n_webhook_url == "https://new-webhook.example.com"
        mock_db.upsert_support_config.assert_called_once()


# ============ Test n8n Connection Tests ============


class TestN8nConnection:
    """Tests for n8n webhook connection testing."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_connection_fails_when_not_configured(self, support_service, mock_db):
        """Should return failure when no webhook URL configured."""
        mock_db.get_support_config = AsyncMock(return_value=None)

        result = await support_service.test_n8n_connection("tenant-456")

        assert result["success"] is False
        assert "not configured" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_connection_success(self, support_service, mock_db):
        """Should return success when webhook responds."""
        mock_db.get_support_config = AsyncMock(return_value={
            "tenant_id": "tenant-456",
            "n8n_webhook_url": "https://n8n.example.com/webhook",
        })

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_client = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await support_service.test_n8n_connection("tenant-456")

            assert result["success"] is True
            assert "successful" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_connection_failure_on_error(self, support_service, mock_db):
        """Should return failure when webhook returns error."""
        mock_db.get_support_config = AsyncMock(return_value={
            "tenant_id": "tenant-456",
            "n8n_webhook_url": "https://n8n.example.com/webhook",
        })

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 500

            mock_client = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await support_service.test_n8n_connection("tenant-456")

            assert result["success"] is False
            assert "failed" in result["message"]
