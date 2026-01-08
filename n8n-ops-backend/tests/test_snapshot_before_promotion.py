"""
Test that snapshot creation occurs before promotion execution.

This test verifies task T014: ensuring that PRE_PROMOTION snapshots are created
BEFORE any workflows are transferred during a promotion operation.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, call
from uuid import uuid4

from app.schemas.deployment import SnapshotType


@pytest.fixture(autouse=True)
def mock_entitlements():
    """Mock entitlements service to allow all features for testing."""
    with patch("app.core.entitlements_gate.entitlements_service") as mock_ent:
        mock_ent.enforce_flag = AsyncMock(return_value=None)
        mock_ent.has_flag = AsyncMock(return_value=True)
        yield mock_ent


class TestSnapshotBeforePromotion:
    """Tests to verify snapshot creation occurs before promotion execution."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_pre_promotion_snapshot_created_before_workflow_transfer(self):
        """
        Test that PRE_PROMOTION snapshot is created BEFORE any workflows are transferred.

        This test verifies the execution order by:
        1. Mocking the promotion service's create_pre_promotion_snapshot method
        2. Mocking the adapter's get_workflow and update_workflow methods
        3. Using a call_order list to track when each method is called
        4. Asserting that create_pre_promotion_snapshot is called before get_workflow
        """
        from app.services.promotion_service import promotion_service
        from app.services.database import db_service
        from app.services.provider_registry import ProviderRegistry
        from app.services.background_job_service import background_job_service, BackgroundJobStatus

        # Track call order
        call_order = []

        promotion_id = str(uuid4())
        deployment_id = str(uuid4())
        tenant_id = "00000000-0000-0000-0000-000000000000"
        source_env_id = str(uuid4())
        target_env_id = str(uuid4())

        # Mock environments
        source_env = {
            "id": source_env_id,
            "n8n_name": "Development",
            "n8n_type": "dev",
            "base_url": "http://localhost:5678",
            "api_key": "test-key-source",
            "provider": "n8n",
            "git_repo_url": "https://github.com/test/repo",
            "git_pat": "test-token",
            "git_branch": "main",
        }

        target_env = {
            "id": target_env_id,
            "n8n_name": "Production",
            "n8n_type": "production",
            "base_url": "http://localhost:5679",
            "api_key": "test-key-target",
            "provider": "n8n",
            "git_repo_url": "https://github.com/test/repo",
            "git_pat": "test-token",
            "git_branch": "main",
        }

        # Mock workflow selections
        workflow_selections = [
            {
                "workflow_id": "wf-1",
                "workflow_name": "Test Workflow",
                "selected": True,
                "change_type": "changed",
                "enabled_in_source": True
            }
        ]

        # Mock promotion data
        promotion_data = {
            "id": promotion_id,
            "tenant_id": tenant_id,
            "source_environment_id": source_env_id,
            "target_environment_id": target_env_id,
            "workflow_selections": workflow_selections,
            "status": "approved"
        }

        # Mock deployment data
        deployment_data = {
            "id": deployment_id,
            "promotion_id": promotion_id,
            "tenant_id": tenant_id,
            "source_environment_id": source_env_id,
            "target_environment_id": target_env_id,
            "status": "pending"
        }

        snapshot_id = str(uuid4())

        # Create mock adapters
        mock_source_adapter = MagicMock()
        mock_target_adapter = MagicMock()

        # Mock adapter methods with call tracking
        async def mock_test_connection():
            return True

        async def mock_get_workflow(wf_id):
            call_order.append(f"get_workflow:{wf_id}")
            return {
                "id": wf_id,
                "name": "Test Workflow",
                "active": True,
                "nodes": []
            }

        async def mock_update_workflow(wf_id, wf_data):
            call_order.append(f"update_workflow:{wf_id}")
            return True

        mock_source_adapter.test_connection = AsyncMock(side_effect=mock_test_connection)
        mock_target_adapter.test_connection = AsyncMock(side_effect=mock_test_connection)
        mock_source_adapter.get_workflow = AsyncMock(side_effect=mock_get_workflow)
        mock_target_adapter.update_workflow = AsyncMock(side_effect=mock_update_workflow)

        # Mock the create_pre_promotion_snapshot method with call tracking
        async def mock_create_pre_promotion_snapshot(tenant_id, target_env_id, promotion_id):
            call_order.append("create_pre_promotion_snapshot")
            return snapshot_id

        with patch.object(db_service, 'get_promotion', return_value=promotion_data):
            with patch.object(db_service, 'get_environment', side_effect=[source_env, target_env]):
                with patch.object(db_service, 'get_deployment', return_value=deployment_data):
                    with patch.object(db_service, 'update_deployment', AsyncMock(return_value=deployment_data)):
                        with patch.object(db_service, 'get_deployment_workflows', return_value=[]):
                            with patch.object(db_service, 'update_deployment_workflow', AsyncMock(return_value=None)):
                                with patch.object(ProviderRegistry, 'get_adapter_for_environment') as mock_registry:
                                    mock_registry.side_effect = [mock_source_adapter, mock_target_adapter]

                                    with patch.object(promotion_service, 'create_pre_promotion_snapshot', new_callable=AsyncMock) as mock_snapshot:
                                        mock_snapshot.side_effect = mock_create_pre_promotion_snapshot

                                        with patch.object(background_job_service, 'update_job_status', AsyncMock(return_value=None)):
                                            with patch.object(background_job_service, 'update_progress', AsyncMock(return_value=None)):
                                                # Import and call the promotion execution task
                                                from app.api.endpoints.promotions import _execute_promotion_background

                                                job_id = str(uuid4())
                                                await _execute_promotion_background(
                                                    job_id=job_id,
                                                    promotion_id=promotion_id,
                                                    deployment_id=deployment_id,
                                                    promotion=promotion_data,
                                                    source_env=source_env,
                                                    target_env=target_env,
                                                    selected_workflows=workflow_selections,
                                                    tenant_id=tenant_id
                                                )

        # Verify call order
        assert len(call_order) > 0, "No methods were called"

        # Find the index of snapshot creation and first workflow fetch
        snapshot_index = call_order.index("create_pre_promotion_snapshot")

        # Find all get_workflow calls
        get_workflow_calls = [i for i, call in enumerate(call_order) if call.startswith("get_workflow:")]

        # Verify snapshot was created
        assert "create_pre_promotion_snapshot" in call_order, "PRE_PROMOTION snapshot was not created"

        # Verify workflows were fetched
        assert len(get_workflow_calls) > 0, "No workflows were fetched"

        # Verify snapshot creation happened BEFORE first workflow fetch
        first_workflow_index = get_workflow_calls[0]
        assert snapshot_index < first_workflow_index, \
            f"Snapshot creation (index {snapshot_index}) must happen BEFORE workflow fetch (index {first_workflow_index})"

        # Verify the snapshot method was called with correct parameters
        mock_snapshot.assert_called_once_with(
            tenant_id=tenant_id,
            target_env_id=target_env_id,
            promotion_id=promotion_id
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_snapshot_contains_correct_metadata(self):
        """
        Test that the PRE_PROMOTION snapshot contains the correct metadata.

        Verifies:
        - Snapshot type is PRE_PROMOTION
        - Snapshot includes promotion_id in metadata
        - Snapshot is created for the target environment (not source)
        """
        from app.services.promotion_service import PromotionService
        from app.services.database import db_service
        from app.services.provider_registry import ProviderRegistry
        from app.services.github_service import GitHubService
        from app.services.notification_service import notification_service

        service = PromotionService()
        service.db = db_service

        tenant_id = "tenant-1"
        target_env_id = "env-target"
        promotion_id = "promo-123"

        # Mock environment
        target_env = {
            "id": target_env_id,
            "n8n_type": "production",
            "git_repo_url": "https://github.com/test/repo",
            "git_pat": "test-token",
            "git_branch": "main",
        }

        # Track what was passed to create_snapshot
        captured_snapshot_data = None

        async def mock_create_snapshot(snapshot_data):
            nonlocal captured_snapshot_data
            captured_snapshot_data = snapshot_data
            return None

        with patch.object(db_service, 'get_environment', AsyncMock(return_value=target_env)):
            with patch.object(db_service, 'create_snapshot', new_callable=AsyncMock) as mock_db_create:
                mock_db_create.side_effect = mock_create_snapshot

                with patch('app.services.promotion_service.ProviderRegistry') as mock_registry:
                    mock_adapter = MagicMock()
                    mock_adapter.get_workflows = AsyncMock(return_value=[
                        {"id": "wf-1", "name": "Workflow 1"}
                    ])
                    mock_adapter.get_workflow = AsyncMock(return_value={
                        "id": "wf-1",
                        "name": "Workflow 1",
                        "active": True
                    })
                    mock_registry.get_adapter_for_environment.return_value = mock_adapter

                    with patch('app.services.promotion_service.GitHubService') as mock_github:
                        mock_github_instance = MagicMock()
                        mock_github_instance.is_configured.return_value = True
                        mock_github_instance.sync_workflow_to_github = AsyncMock(return_value=None)
                        mock_github_instance.repo.get_commits.return_value = [MagicMock(sha="abc123")]
                        mock_github_instance.branch = "main"
                        mock_github_instance._sanitize_foldername = MagicMock(return_value="production")
                        mock_github.return_value = mock_github_instance

                        with patch('app.services.promotion_service.notification_service') as mock_notify:
                            mock_notify.emit_event = AsyncMock(return_value=None)

                            # Call create_pre_promotion_snapshot
                            snapshot_id = await service.create_pre_promotion_snapshot(
                                tenant_id=tenant_id,
                                target_env_id=target_env_id,
                                promotion_id=promotion_id
                            )

        # Verify snapshot was created
        assert captured_snapshot_data is not None, "Snapshot data was not captured"

        # Verify snapshot type
        assert captured_snapshot_data["type"] == SnapshotType.PRE_PROMOTION.value, \
            f"Expected snapshot type to be PRE_PROMOTION, got {captured_snapshot_data['type']}"

        # Verify environment_id is the target environment
        assert captured_snapshot_data["environment_id"] == target_env_id, \
            f"Expected environment_id to be {target_env_id}, got {captured_snapshot_data['environment_id']}"

        # Verify tenant_id
        assert captured_snapshot_data["tenant_id"] == tenant_id, \
            f"Expected tenant_id to be {tenant_id}, got {captured_snapshot_data['tenant_id']}"

        # Verify metadata contains promotion_id
        assert "metadata_json" in captured_snapshot_data, "Snapshot missing metadata_json"
        metadata = captured_snapshot_data["metadata_json"]
        assert "promotion_id" in metadata, "Metadata missing promotion_id"
        assert metadata["promotion_id"] == promotion_id, \
            f"Expected promotion_id to be {promotion_id}, got {metadata['promotion_id']}"

        # Verify metadata contains workflow information
        assert "workflows" in metadata, "Metadata missing workflows"
        assert len(metadata["workflows"]) > 0, "Metadata workflows list is empty"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_promotion_continues_if_snapshot_fails(self):
        """
        Test that promotion continues even if snapshot creation fails.

        This ensures backward compatibility - snapshot failures should not block promotions.
        """
        from app.services.promotion_service import promotion_service
        from app.services.database import db_service
        from app.services.provider_registry import ProviderRegistry
        from app.services.background_job_service import background_job_service

        promotion_id = str(uuid4())
        deployment_id = str(uuid4())
        tenant_id = "00000000-0000-0000-0000-000000000000"
        source_env_id = str(uuid4())
        target_env_id = str(uuid4())

        source_env = {
            "id": source_env_id,
            "base_url": "http://localhost:5678",
            "api_key": "test-key",
            "provider": "n8n"
        }

        target_env = {
            "id": target_env_id,
            "base_url": "http://localhost:5679",
            "api_key": "test-key",
            "provider": "n8n"
        }

        promotion_data = {
            "id": promotion_id,
            "tenant_id": tenant_id,
            "source_environment_id": source_env_id,
            "target_environment_id": target_env_id,
            "workflow_selections": [
                {
                    "workflow_id": "wf-1",
                    "workflow_name": "Test Workflow",
                    "selected": True,
                    "change_type": "changed"
                }
            ],
            "status": "approved"
        }

        deployment_data = {
            "id": deployment_id,
            "status": "pending"
        }

        # Track if workflow transfer was attempted
        workflow_fetched = False

        async def mock_get_workflow(wf_id):
            nonlocal workflow_fetched
            workflow_fetched = True
            return {"id": wf_id, "name": "Test Workflow", "active": True, "nodes": []}

        mock_adapter = MagicMock()
        mock_adapter.test_connection = AsyncMock(return_value=True)
        mock_adapter.get_workflow = AsyncMock(side_effect=mock_get_workflow)
        mock_adapter.update_workflow = AsyncMock(return_value=True)

        with patch.object(db_service, 'get_promotion', return_value=promotion_data):
            with patch.object(db_service, 'get_environment', side_effect=[source_env, target_env]):
                with patch.object(db_service, 'get_deployment', return_value=deployment_data):
                    with patch.object(db_service, 'update_deployment', AsyncMock(return_value=deployment_data)):
                        with patch.object(db_service, 'get_deployment_workflows', return_value=[]):
                            with patch.object(db_service, 'update_deployment_workflow', AsyncMock(return_value=None)):
                                with patch.object(ProviderRegistry, 'get_adapter_for_environment', return_value=mock_adapter):
                                    # Make snapshot creation fail
                                    with patch.object(promotion_service, 'create_pre_promotion_snapshot', new_callable=AsyncMock) as mock_snapshot:
                                        mock_snapshot.side_effect = Exception("Snapshot creation failed")

                                        with patch.object(background_job_service, 'update_job_status', AsyncMock(return_value=None)):
                                            with patch.object(background_job_service, 'update_progress', AsyncMock(return_value=None)):
                                                from app.api.endpoints.promotions import _execute_promotion_background

                                                job_id = str(uuid4())

                                                # Promotion should NOT raise an exception even though snapshot failed
                                                await _execute_promotion_background(
                                                    job_id=job_id,
                                                    promotion_id=promotion_id,
                                                    deployment_id=deployment_id,
                                                    promotion=promotion_data,
                                                    source_env=source_env,
                                                    target_env=target_env,
                                                    selected_workflows=promotion_data["workflow_selections"],
                                                    tenant_id=tenant_id
                                                )

        # Verify that workflow was still fetched despite snapshot failure
        assert workflow_fetched, "Workflow transfer should continue even if snapshot creation fails"

        # Verify snapshot creation was attempted
        mock_snapshot.assert_called_once()
