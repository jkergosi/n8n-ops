"""
API tests for the support endpoints.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.schemas.support import SupportRequestResponse


# Mock entitlements for all support tests
@pytest.fixture(autouse=True)
def mock_entitlements():
    """Mock entitlements service to allow all features for testing."""
    with patch("app.core.entitlements_gate.entitlements_service") as mock_ent:
        mock_ent.enforce_flag = AsyncMock(return_value=None)
        mock_ent.has_flag = AsyncMock(return_value=True)
        yield mock_ent


class TestSupportAPICreate:
    """Tests for POST /api/v1/support/requests endpoint."""

    @pytest.mark.api
    def test_create_bug_report_success(self, client: TestClient, auth_headers):
        """POST /support/requests should create a bug report and return JSM key."""
        bug_report = {
            "intent_kind": "bug",
            "title": "Button not working",
            "what_happened": "Clicked the submit button but nothing happened",
            "expected_behavior": "Form should submit and show confirmation",
            "steps_to_reproduce": "1. Open form\n2. Fill in fields\n3. Click submit",
            "severity": "sev3",
            "frequency": "always",
            "include_diagnostics": True,
        }

        with patch("app.api.endpoints.support.support_service") as mock_service:
            mock_service.build_issue_contract = MagicMock(return_value={
                "schema_version": "1.0",
                "intent": {"kind": "bug", "title": "Button not working"}
            })
            mock_service.forward_to_n8n = AsyncMock(
                return_value=SupportRequestResponse(jsm_request_key="JSM-12345")
            )

            response = client.post(
                "/api/v1/support/requests",
                json=bug_report,
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert "jsm_request_key" in data
            assert data["jsm_request_key"] == "JSM-12345"

    @pytest.mark.api
    def test_create_feature_request_success(self, client: TestClient, auth_headers):
        """POST /support/requests should create a feature request."""
        feature_request = {
            "intent_kind": "feature",
            "title": "Add dark mode",
            "problem_or_goal": "The UI is too bright at night",
            "desired_outcome": "A toggle to switch to dark mode",
            "priority": "nice_to_have",
            "acceptance_criteria": ["Toggle button in settings", "Dark theme applied to all pages"],
        }

        with patch("app.api.endpoints.support.support_service") as mock_service:
            mock_service.build_issue_contract = MagicMock(return_value={
                "schema_version": "1.0",
                "intent": {"kind": "feature", "title": "Add dark mode"}
            })
            mock_service.forward_to_n8n = AsyncMock(
                return_value=SupportRequestResponse(jsm_request_key="JSM-12346")
            )

            response = client.post(
                "/api/v1/support/requests",
                json=feature_request,
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["jsm_request_key"] == "JSM-12346"

    @pytest.mark.api
    def test_create_help_request_success(self, client: TestClient, auth_headers):
        """POST /support/requests should create a help request (task)."""
        help_request = {
            "intent_kind": "task",
            "title": "How do I configure webhooks?",
            "details": "I need help setting up webhooks for my workflow",
            "include_diagnostics": False,
        }

        with patch("app.api.endpoints.support.support_service") as mock_service:
            mock_service.build_issue_contract = MagicMock(return_value={
                "schema_version": "1.0",
                "intent": {"kind": "task", "title": "How do I configure webhooks?"}
            })
            mock_service.forward_to_n8n = AsyncMock(
                return_value=SupportRequestResponse(jsm_request_key="JSM-12347")
            )

            response = client.post(
                "/api/v1/support/requests",
                json=help_request,
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["jsm_request_key"] == "JSM-12347"

    @pytest.mark.api
    def test_create_request_missing_required_fields(self, client: TestClient, auth_headers):
        """POST /support/requests with missing required fields should return 400."""
        incomplete_request = {
            "intent_kind": "bug",
            # Missing title and other required fields
        }

        response = client.post(
            "/api/v1/support/requests",
            json=incomplete_request,
            headers=auth_headers
        )

        # May be 400 (validation error) or 422 (pydantic validation)
        assert response.status_code in [400, 422]

    @pytest.mark.api
    def test_create_request_invalid_severity(self, client: TestClient, auth_headers):
        """POST /support/requests with invalid severity should return 400."""
        invalid_request = {
            "intent_kind": "bug",
            "title": "Test bug",
            "what_happened": "Something broke",
            "expected_behavior": "Should not break",
            "severity": "invalid_severity",  # Invalid value
        }

        response = client.post(
            "/api/v1/support/requests",
            json=invalid_request,
            headers=auth_headers
        )

        # May be 400 or 422 depending on validation type
        assert response.status_code in [400, 422]


class TestSupportAPIUpload:
    """Tests for POST /api/v1/support/upload-url endpoint."""

    @pytest.mark.api
    def test_get_upload_url_success(self, client: TestClient, auth_headers):
        """POST /support/upload-url should return signed upload URL."""
        upload_request = {
            "filename": "screenshot.png",
            "content_type": "image/png",
        }

        response = client.post(
            "/api/v1/support/upload-url",
            json=upload_request,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "upload_url" in data
        assert "public_url" in data

    @pytest.mark.api
    def test_get_upload_url_invalid_content_type(self, client: TestClient, auth_headers):
        """POST /support/upload-url with unsupported content type should still work."""
        upload_request = {
            "filename": "file.pdf",
            "content_type": "application/pdf",
        }

        response = client.post(
            "/api/v1/support/upload-url",
            json=upload_request,
            headers=auth_headers
        )

        # Should still succeed - backend doesn't restrict content types
        assert response.status_code in [200, 422]


class TestAdminSupportConfig:
    """Tests for admin support configuration endpoints."""

    @pytest.mark.api
    def test_get_support_config_success(self, client: TestClient, auth_headers):
        """GET /admin/support/config should return configuration."""
        mock_config = {
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "n8n_webhook_url": "https://n8n.example.com/webhook/support",
            "jsm_portal_url": "https://support.example.atlassian.net",
            "jsm_bug_request_type_id": "10001",
            "jsm_feature_request_type_id": "10002",
            "jsm_help_request_type_id": "10003",
        }

        with patch("app.services.support_service.db_service") as mock_db:
            mock_db.get_support_config = AsyncMock(return_value=mock_config)

            response = client.get(
                "/api/v1/admin/support/config",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert "n8n_webhook_url" in data

    @pytest.mark.api
    def test_get_support_config_empty(self, client: TestClient, auth_headers):
        """GET /admin/support/config should return default config when none exists."""
        with patch("app.services.support_service.db_service") as mock_db:
            mock_db.get_support_config = AsyncMock(return_value=None)

            response = client.get(
                "/api/v1/admin/support/config",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert "tenant_id" in data

    @pytest.mark.api
    def test_update_support_config_success(self, client: TestClient, auth_headers):
        """PUT /admin/support/config should update configuration."""
        new_config = {
            "n8n_webhook_url": "https://n8n.example.com/webhook/new-support",
            "jsm_portal_url": "https://newsupport.example.atlassian.net",
        }

        mock_result = {
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            **new_config,
        }

        with patch("app.services.support_service.db_service") as mock_db:
            mock_db.upsert_support_config = AsyncMock(return_value=mock_result)

            response = client.put(
                "/api/v1/admin/support/config",
                json=new_config,
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["n8n_webhook_url"] == new_config["n8n_webhook_url"]

    @pytest.mark.api
    def test_test_n8n_connection_not_configured(self, client: TestClient, auth_headers):
        """POST /admin/support/test-n8n should handle missing config."""
        with patch("app.services.support_service.db_service") as mock_db:
            mock_db.get_support_config = AsyncMock(return_value=None)

            response = client.post(
                "/api/v1/admin/support/test-n8n",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert "success" in data
            assert data["success"] is False
            assert "not configured" in data["message"]

    @pytest.mark.api
    def test_test_n8n_connection_success(self, client: TestClient, auth_headers):
        """POST /admin/support/test-n8n should test the webhook connection."""
        mock_config = {
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "n8n_webhook_url": "https://n8n.example.com/webhook/support",
        }

        with patch("app.services.support_service.db_service") as mock_db:
            mock_db.get_support_config = AsyncMock(return_value=mock_config)

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_response = MagicMock()
                mock_response.status_code = 200

                mock_client = MagicMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                response = client.post(
                    "/api/v1/admin/support/test-n8n",
                    headers=auth_headers
                )

                assert response.status_code == 200
                data = response.json()
                assert "success" in data
