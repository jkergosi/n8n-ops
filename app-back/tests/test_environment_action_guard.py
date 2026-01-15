"""
Tests for environment action guard service.
"""
import pytest
from fastapi import HTTPException

from app.services.environment_action_guard import (
    environment_action_guard,
    EnvironmentAction,
    ActionGuardError
)
from app.schemas.environment import EnvironmentClass


class TestEnvironmentActionGuard:
    """Test suite for environment action guard"""
    
    def test_sync_status_allowed_all_environments(self):
        """Sync status should be allowed in all environments"""
        for env_class in [EnvironmentClass.DEV, EnvironmentClass.STAGING, EnvironmentClass.PRODUCTION]:
            assert environment_action_guard.can_perform_action(
                env_class=env_class,
                action=EnvironmentAction.SYNC_STATUS,
                user_role="user"
            ) is True
    
    def test_backup_blocked_in_staging_prod(self):
        """Backup should be blocked in staging and prod"""
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.STAGING,
            action=EnvironmentAction.BACKUP,
            user_role="user"
        ) is False
        
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.PRODUCTION,
            action=EnvironmentAction.BACKUP,
            user_role="user"
        ) is False
        
        # But allowed in dev
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.DEV,
            action=EnvironmentAction.BACKUP,
            user_role="user"
        ) is True
    
    def test_manual_snapshot_blocked_in_prod(self):
        """Manual snapshot should be blocked in prod"""
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.PRODUCTION,
            action=EnvironmentAction.MANUAL_SNAPSHOT,
            user_role="user"
        ) is False
        
        # Allowed in dev by default
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.DEV,
            action=EnvironmentAction.MANUAL_SNAPSHOT,
            user_role="user"
        ) is True
    
    def test_manual_snapshot_policy_dependent_in_staging(self):
        """Manual snapshot in staging is policy-dependent (default OFF)"""
        # Default (no policy flag) = blocked
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.STAGING,
            action=EnvironmentAction.MANUAL_SNAPSHOT,
            user_role="user",
            org_policy_flags={}
        ) is False
        
        # With policy flag = allowed
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.STAGING,
            action=EnvironmentAction.MANUAL_SNAPSHOT,
            user_role="user",
            org_policy_flags={"allow_manual_snapshot_in_staging": True}
        ) is True
    
    def test_deploy_outbound_blocked_from_prod(self):
        """Deploy outbound should be blocked from prod"""
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.PRODUCTION,
            action=EnvironmentAction.DEPLOY_OUTBOUND,
            user_role="user"
        ) is False
        
        # But allowed from dev/staging
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.DEV,
            action=EnvironmentAction.DEPLOY_OUTBOUND,
            user_role="user"
        ) is True
        
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.STAGING,
            action=EnvironmentAction.DEPLOY_OUTBOUND,
            user_role="user"
        ) is True
    
    def test_deploy_inbound_blocked_to_dev(self):
        """Deploy inbound should be blocked to dev"""
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.DEV,
            action=EnvironmentAction.DEPLOY_INBOUND,
            user_role="user",
            target_env_class=EnvironmentClass.DEV
        ) is False
        
        # But allowed to staging
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.STAGING,
            action=EnvironmentAction.DEPLOY_INBOUND,
            user_role="user",
            target_env_class=EnvironmentClass.STAGING
        ) is True
    
    def test_deploy_inbound_to_prod_requires_admin(self):
        """Deploy inbound to prod requires admin role"""
        # User role = blocked
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.STAGING,
            action=EnvironmentAction.DEPLOY_INBOUND,
            user_role="user",
            target_env_class=EnvironmentClass.PRODUCTION
        ) is False
        
        # Admin role = allowed
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.STAGING,
            action=EnvironmentAction.DEPLOY_INBOUND,
            user_role="admin",
            target_env_class=EnvironmentClass.PRODUCTION
        ) is True
        
        # Superuser role = allowed
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.STAGING,
            action=EnvironmentAction.DEPLOY_INBOUND,
            user_role="superuser",
            target_env_class=EnvironmentClass.PRODUCTION
        ) is True
    
    def test_restore_rollback_policy_dependent_in_dev(self):
        """Restore/rollback in dev is policy-dependent (default OFF)"""
        # Default (no policy flag) = blocked
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.DEV,
            action=EnvironmentAction.RESTORE_ROLLBACK,
            user_role="user",
            org_policy_flags={}
        ) is False
        
        # With policy flag = allowed
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.DEV,
            action=EnvironmentAction.RESTORE_ROLLBACK,
            user_role="user",
            org_policy_flags={"allow_restore_in_dev": True}
        ) is True
    
    def test_restore_rollback_in_prod_requires_admin(self):
        """Restore/rollback in prod requires admin role"""
        # User role = blocked
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.PRODUCTION,
            action=EnvironmentAction.RESTORE_ROLLBACK,
            user_role="user"
        ) is False
        
        # Admin role = allowed
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.PRODUCTION,
            action=EnvironmentAction.RESTORE_ROLLBACK,
            user_role="admin"
        ) is True
    
    def test_restore_rollback_allowed_in_staging(self):
        """Restore/rollback should be allowed in staging"""
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.STAGING,
            action=EnvironmentAction.RESTORE_ROLLBACK,
            user_role="user"
        ) is True
    
    def test_edit_in_n8n_blocked_in_staging_prod(self):
        """Edit in N8N should be blocked in staging/prod"""
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.STAGING,
            action=EnvironmentAction.EDIT_IN_N8N,
            user_role="user"
        ) is False
        
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.PRODUCTION,
            action=EnvironmentAction.EDIT_IN_N8N,
            user_role="user"
        ) is False
        
        # But allowed in dev
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.DEV,
            action=EnvironmentAction.EDIT_IN_N8N,
            user_role="user"
        ) is True
    
    def test_assert_can_perform_action_raises_on_blocked(self):
        """assert_can_perform_action should raise ActionGuardError when blocked"""
        with pytest.raises(ActionGuardError) as exc_info:
            environment_action_guard.assert_can_perform_action(
                env_class=EnvironmentClass.PRODUCTION,
                action=EnvironmentAction.BACKUP,
                user_role="user"
            )
        
        assert exc_info.value.status_code == 403
        assert "action_not_allowed" in str(exc_info.value.detail)
    
    def test_assert_can_perform_action_passes_on_allowed(self):
        """assert_can_perform_action should not raise when allowed"""
        # Should not raise
        environment_action_guard.assert_can_perform_action(
            env_class=EnvironmentClass.DEV,
            action=EnvironmentAction.BACKUP,
            user_role="user"
        )

    def test_upload_workflow_only_allowed_in_dev(self):
        """Upload workflow should only be allowed in DEV environments"""
        # Allowed in DEV
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.DEV,
            action=EnvironmentAction.UPLOAD_WORKFLOW,
            user_role="user"
        ) is True

        # Blocked in STAGING
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.STAGING,
            action=EnvironmentAction.UPLOAD_WORKFLOW,
            user_role="user"
        ) is False

        # Blocked in PRODUCTION
        assert environment_action_guard.can_perform_action(
            env_class=EnvironmentClass.PRODUCTION,
            action=EnvironmentAction.UPLOAD_WORKFLOW,
            user_role="user"
        ) is False

    def test_upload_workflow_blocked_for_all_roles_in_non_dev(self):
        """Upload workflow should be blocked in non-DEV even for admin/superuser"""
        for role in ["user", "admin", "superuser"]:
            # Blocked in STAGING for all roles
            assert environment_action_guard.can_perform_action(
                env_class=EnvironmentClass.STAGING,
                action=EnvironmentAction.UPLOAD_WORKFLOW,
                user_role=role
            ) is False

            # Blocked in PRODUCTION for all roles
            assert environment_action_guard.can_perform_action(
                env_class=EnvironmentClass.PRODUCTION,
                action=EnvironmentAction.UPLOAD_WORKFLOW,
                user_role=role
            ) is False

    def test_upload_workflow_error_message(self):
        """Upload workflow should return correct error message when blocked"""
        with pytest.raises(ActionGuardError) as exc_info:
            environment_action_guard.assert_can_perform_action(
                env_class=EnvironmentClass.STAGING,
                action=EnvironmentAction.UPLOAD_WORKFLOW,
                user_role="user",
                environment_name="Staging Environment"
            )

        assert exc_info.value.status_code == 403
        error_detail = exc_info.value.detail
        assert error_detail["error"] == "action_not_allowed"
        assert error_detail["action"] == "upload_workflow"
        assert "only allowed in DEV" in error_detail["reason"]

