"""
Centralized environment action guard service.

This is the single source of truth for environment action permissions.
All environment actions must be checked through this service.
"""
from enum import Enum
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
import logging

from app.schemas.environment import EnvironmentClass

logger = logging.getLogger(__name__)


class EnvironmentAction(str, Enum):
    """All possible environment actions"""
    SYNC_STATUS = "sync_status"
    BACKUP = "backup"
    MANUAL_SNAPSHOT = "manual_snapshot"
    DIFF_COMPARE = "diff_compare"
    DEPLOY_OUTBOUND = "deploy_outbound"
    DEPLOY_INBOUND = "deploy_inbound"
    RESTORE_ROLLBACK = "restore_rollback"
    EDIT_IN_N8N = "edit_in_n8n"


class ActionGuardError(HTTPException):
    """Custom exception for action guard violations"""
    def __init__(self, action: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "action_not_allowed",
                "action": action,
                "reason": reason,
                "details": details or {}
            }
        )


class EnvironmentActionGuard:
    """
    Centralized guard for environment actions.
    
    Implements the ground truth matrix from requirements:
    - Hard policies (server-side required)
    - Policy-dependent flags (org/env settings, default OFF)
    - Feature flags / plan gating
    """
    
    @staticmethod
    def can_perform_action(
        env_class: EnvironmentClass,
        action: EnvironmentAction,
        user_role: str = "user",
        org_policy_flags: Optional[Dict[str, bool]] = None,
        plan: str = "free",
        target_env_class: Optional[EnvironmentClass] = None
    ) -> bool:
        """
        Check if an action is allowed.
        
        Args:
            env_class: The environment class (dev/staging/production)
            action: The action to check
            user_role: User role (user/admin/superuser)
            org_policy_flags: Optional org/env policy flags (e.g., {"allow_restore_in_dev": False})
            plan: Subscription plan (free/pro/agency/enterprise)
            target_env_class: For deploy actions, the target environment class
            
        Returns:
            True if action is allowed, False otherwise
        """
        org_flags = org_policy_flags or {}
        is_admin = user_role in ["admin", "superuser"]
        
        # Ground truth matrix implementation
        if action == EnvironmentAction.SYNC_STATUS:
            # Allowed in all environments
            return True
            
        elif action == EnvironmentAction.BACKUP:
            # Block in staging/prod
            if env_class in [EnvironmentClass.STAGING, EnvironmentClass.PRODUCTION]:
                return False
            return True
            
        elif action == EnvironmentAction.MANUAL_SNAPSHOT:
            # Block in prod
            if env_class == EnvironmentClass.PRODUCTION:
                return False
            # Policy-dependent in staging (default OFF)
            if env_class == EnvironmentClass.STAGING:
                return org_flags.get("allow_manual_snapshot_in_staging", False)
            # Always allowed in dev
            return True
            
        elif action == EnvironmentAction.DIFF_COMPARE:
            # Allowed in all environments
            return True
            
        elif action == EnvironmentAction.DEPLOY_OUTBOUND:
            # Block deploy outbound from prod
            if env_class == EnvironmentClass.PRODUCTION:
                return False
            # Allowed from dev/staging
            return True
            
        elif action == EnvironmentAction.DEPLOY_INBOUND:
            # Block deploy inbound to dev
            if target_env_class == EnvironmentClass.DEV:
                return False
            # Require admin for prod
            if target_env_class == EnvironmentClass.PRODUCTION:
                return is_admin
            # Allowed to staging
            return True
            
        elif action == EnvironmentAction.RESTORE_ROLLBACK:
            # Policy-dependent in dev (default OFF)
            if env_class == EnvironmentClass.DEV:
                return org_flags.get("allow_restore_in_dev", False)
            # Require admin for prod
            if env_class == EnvironmentClass.PRODUCTION:
                return is_admin
            # Allowed in staging
            return True
            
        elif action == EnvironmentAction.EDIT_IN_N8N:
            # Block in staging/prod (UI-only, but we check for consistency)
            if env_class in [EnvironmentClass.STAGING, EnvironmentClass.PRODUCTION]:
                return False
            # Allowed in dev
            return True
            
        # Unknown action - deny by default
        logger.warning(f"Unknown action: {action}")
        return False
    
    @staticmethod
    def assert_can_perform_action(
        env_class: EnvironmentClass,
        action: EnvironmentAction,
        user_role: str = "user",
        org_policy_flags: Optional[Dict[str, bool]] = None,
        plan: str = "free",
        target_env_class: Optional[EnvironmentClass] = None,
        environment_name: Optional[str] = None
    ):
        """
        Assert that an action is allowed. Raises ActionGuardError if not allowed.
        
        Args:
            env_class: The environment class
            action: The action to check
            user_role: User role
            org_policy_flags: Optional org/env policy flags
            plan: Subscription plan
            target_env_class: For deploy actions, the target environment class
            environment_name: Optional environment name for error messages
            
        Raises:
            ActionGuardError if action is not allowed
        """
        allowed = EnvironmentActionGuard.can_perform_action(
            env_class=env_class,
            action=action,
            user_role=user_role,
            org_policy_flags=org_policy_flags,
            plan=plan,
            target_env_class=target_env_class
        )
        
        if not allowed:
            env_name = environment_name or "this environment"
            reason = EnvironmentActionGuard._get_reason(env_class, action, user_role, target_env_class)
            raise ActionGuardError(
                action=action.value,
                reason=reason,
                details={
                    "environment_class": env_class.value,
                    "environment_name": env_name,
                    "action": action.value,
                    "user_role": user_role,
                    "target_environment_class": target_env_class.value if target_env_class else None
                }
            )
    
    @staticmethod
    def _get_reason(
        env_class: EnvironmentClass,
        action: EnvironmentAction,
        user_role: str,
        target_env_class: Optional[EnvironmentClass]
    ) -> str:
        """Get human-readable reason for why action is blocked"""
        if action == EnvironmentAction.BACKUP:
            return f"Backup is not allowed in {env_class.value} environments"
        elif action == EnvironmentAction.MANUAL_SNAPSHOT:
            if env_class == EnvironmentClass.PRODUCTION:
                return "Manual snapshots are not allowed in production environments"
            elif env_class == EnvironmentClass.STAGING:
                return "Manual snapshots in staging require policy flag 'allow_manual_snapshot_in_staging'"
        elif action == EnvironmentAction.DEPLOY_OUTBOUND:
            return "Deployments outbound from production are not allowed"
        elif action == EnvironmentAction.DEPLOY_INBOUND:
            if target_env_class == EnvironmentClass.DEV:
                return "Deployments inbound to dev environments are not allowed"
            elif target_env_class == EnvironmentClass.PRODUCTION:
                return "Deployments to production require admin role"
        elif action == EnvironmentAction.RESTORE_ROLLBACK:
            if env_class == EnvironmentClass.DEV:
                return "Restore/rollback in dev requires policy flag 'allow_restore_in_dev'"
            elif env_class == EnvironmentClass.PRODUCTION:
                return "Restore/rollback in production requires admin role"
        elif action == EnvironmentAction.EDIT_IN_N8N:
            return f"Direct editing in N8N is not allowed in {env_class.value} environments"
        
        return "Action not allowed for this environment"


# Singleton instance
environment_action_guard = EnvironmentActionGuard()

