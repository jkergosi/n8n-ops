"""
Promotion Validation Service - Pre-flight validation for promotions.

This service validates all prerequisites before allowing a promotion to start,
including credential availability, target environment health, and drift policy compliance.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from app.services.database import db_service
from app.services.provider_registry import ProviderRegistry
from app.services.drift_policy_enforcement import (
    drift_policy_enforcement_service,
    EnforcementResult,
)

logger = logging.getLogger(__name__)


class PromotionValidator:
    """
    Service for running pre-flight validation checks on promotions.

    Validates:
    - Target environment health (reachability)
    - Credential availability (credentials referenced by workflow graph)
    - Drift policy compliance (blocking incidents)

    Implements fail-closed behavior for validation failures and fail-open
    behavior for internal errors with correlation ID logging.
    """

    def __init__(self):
        """Initialize the promotion validator."""
        self.provider_registry = ProviderRegistry()

    async def validate_target_environment_health(
        self,
        target_environment_id: str,
        tenant_id: str,
        timeout_seconds: float = 5.0
    ) -> Dict[str, Any]:
        """
        Validate that the target environment is reachable and healthy.

        Uses the existing test_connection method with configurable timeout.

        Args:
            target_environment_id: The target environment to validate
            tenant_id: The tenant ID (for database access control)
            timeout_seconds: Connection timeout in seconds (default: 5.0)

        Returns:
            Dict with validation result:
            {
                "passed": bool,
                "check": "target_environment_health",
                "message": str,
                "remediation": Optional[str],
                "details": Dict[str, Any]
            }
        """
        import asyncio
        import httpx
        from uuid import uuid4

        check_name = "target_environment_health"
        correlation_id = str(uuid4())

        try:
            # Fetch environment configuration from database
            environment = await db_service.get_environment(
                environment_id=target_environment_id,
                tenant_id=tenant_id
            )

            if not environment:
                logger.warning(
                    f"Environment validation failed: Environment not found "
                    f"(environment_id={target_environment_id}, correlation_id={correlation_id})"
                )
                return {
                    "passed": False,
                    "check": check_name,
                    "message": f"Target environment '{target_environment_id}' not found in database.",
                    "remediation": "Verify the environment ID and ensure the environment exists.",
                    "details": {
                        "environment_id": target_environment_id,
                        "correlation_id": correlation_id,
                        "error_type": "environment_not_found"
                    }
                }

            environment_name = environment.get("name") or environment.get("n8n_name", "Unknown")

            # Get provider adapter for the target environment
            try:
                adapter = self.provider_registry.get_adapter_for_environment(environment)
            except ValueError as e:
                logger.error(
                    f"Environment validation failed: Cannot create adapter "
                    f"(environment_id={target_environment_id}, error={str(e)}, "
                    f"correlation_id={correlation_id})"
                )
                return {
                    "passed": False,
                    "check": check_name,
                    "message": f"Target environment '{environment_name}' has invalid provider configuration.",
                    "remediation": "Navigate to Environments > Edit and verify provider settings (base_url, api_key).",
                    "details": {
                        "environment_id": target_environment_id,
                        "environment_name": environment_name,
                        "correlation_id": correlation_id,
                        "error_type": "invalid_provider_config",
                        "error": str(e)
                    }
                }

            # Test connection with timeout
            try:
                connection_healthy = await asyncio.wait_for(
                    adapter.test_connection(),
                    timeout=timeout_seconds
                )

                if connection_healthy:
                    logger.info(
                        f"Environment validation passed: Target environment is healthy "
                        f"(environment_id={target_environment_id}, environment_name={environment_name})"
                    )
                    return {
                        "passed": True,
                        "check": check_name,
                        "message": f"Target environment '{environment_name}' is reachable and healthy.",
                        "remediation": None,
                        "details": {
                            "environment_id": target_environment_id,
                            "environment_name": environment_name,
                            "connection_test_passed": True,
                            "timeout_seconds": timeout_seconds
                        }
                    }
                else:
                    logger.warning(
                        f"Environment validation failed: Connection test returned False "
                        f"(environment_id={target_environment_id}, environment_name={environment_name}, "
                        f"correlation_id={correlation_id})"
                    )
                    return {
                        "passed": False,
                        "check": check_name,
                        "message": f"Target environment '{environment_name}' is not reachable. Please verify environment configuration and connectivity.",
                        "remediation": "Navigate to Environments > Edit and verify base URL and API key. Check network connectivity and ensure the provider instance is running.",
                        "details": {
                            "environment_id": target_environment_id,
                            "environment_name": environment_name,
                            "correlation_id": correlation_id,
                            "error_type": "connection_failed",
                            "connection_test_passed": False
                        }
                    }

            except asyncio.TimeoutError:
                logger.warning(
                    f"Environment validation failed: Connection timeout "
                    f"(environment_id={target_environment_id}, environment_name={environment_name}, "
                    f"timeout={timeout_seconds}s, correlation_id={correlation_id})"
                )
                return {
                    "passed": False,
                    "check": check_name,
                    "message": f"Target environment '{environment_name}' connection timed out after {timeout_seconds}s. Please verify environment configuration and connectivity.",
                    "remediation": "Navigate to Environments > Edit and verify base URL is correct. Check if the provider instance is running and network latency is acceptable.",
                    "details": {
                        "environment_id": target_environment_id,
                        "environment_name": environment_name,
                        "correlation_id": correlation_id,
                        "error_type": "connection_timeout",
                        "timeout_seconds": timeout_seconds
                    }
                }

            except (httpx.HTTPError, Exception) as e:
                error_type = type(e).__name__
                logger.warning(
                    f"Environment validation failed: Connection error "
                    f"(environment_id={target_environment_id}, environment_name={environment_name}, "
                    f"error_type={error_type}, error={str(e)}, correlation_id={correlation_id})"
                )
                return {
                    "passed": False,
                    "check": check_name,
                    "message": f"Target environment '{environment_name}' is not reachable. Please verify environment configuration and connectivity.",
                    "remediation": "Navigate to Environments > Edit and verify base URL and API key. Ensure the provider instance is running and accessible.",
                    "details": {
                        "environment_id": target_environment_id,
                        "environment_name": environment_name,
                        "correlation_id": correlation_id,
                        "error_type": error_type,
                        "error": str(e)
                    }
                }

        except Exception as e:
            # Fail-open: Internal validation errors should not block promotion
            # but should be logged with correlation ID for monitoring
            error_type = type(e).__name__
            logger.warning(
                f"Environment validation internal error (fail-open): Unexpected exception "
                f"(environment_id={target_environment_id}, error_type={error_type}, "
                f"error={str(e)}, correlation_id={correlation_id})"
            )

            # Return passed=True for fail-open behavior, but include warning details
            return {
                "passed": True,  # Fail-open: allow promotion to proceed
                "check": check_name,
                "message": f"Environment health check encountered an internal error but allowing promotion to proceed (fail-open).",
                "remediation": None,
                "details": {
                    "environment_id": target_environment_id,
                    "correlation_id": correlation_id,
                    "error_type": error_type,
                    "error": str(e),
                    "fail_open": True,
                    "warning": "Internal validation error - check logs"
                }
            }

    async def validate_credentials_available(
        self,
        workflow_id: str,
        source_environment_id: str,
        target_environment_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Validate that all credentials referenced by the workflow are available in target.

        Wraps credential_preflight_check for single workflow only, checking only
        credentials referenced by the workflow graph (not deep dependency validation).

        Args:
            workflow_id: The workflow to validate credentials for
            source_environment_id: Source environment ID
            target_environment_id: Target environment ID
            tenant_id: The tenant ID (for database access control)

        Returns:
            Dict with validation result:
            {
                "passed": bool,
                "check": "credential_availability",
                "message": str,
                "remediation": Optional[str],
                "missing_credentials": List[str],
                "details": Dict[str, Any]
            }
        """
        from uuid import uuid4

        check_name = "credential_availability"
        correlation_id = str(uuid4())

        try:
            # Get environment configs
            source_env = await db_service.get_environment(source_environment_id, tenant_id)
            target_env = await db_service.get_environment(target_environment_id, tenant_id)

            if not source_env:
                logger.warning(
                    f"Credential validation failed: Source environment not found "
                    f"(environment_id={source_environment_id}, correlation_id={correlation_id})"
                )
                return {
                    "passed": False,
                    "check": check_name,
                    "message": f"Source environment '{source_environment_id}' not found in database.",
                    "remediation": "Verify the source environment ID and ensure the environment exists.",
                    "missing_credentials": [],
                    "details": {
                        "source_environment_id": source_environment_id,
                        "correlation_id": correlation_id,
                        "error_type": "source_environment_not_found"
                    }
                }

            if not target_env:
                logger.warning(
                    f"Credential validation failed: Target environment not found "
                    f"(environment_id={target_environment_id}, correlation_id={correlation_id})"
                )
                return {
                    "passed": False,
                    "check": check_name,
                    "message": f"Target environment '{target_environment_id}' not found in database.",
                    "remediation": "Verify the target environment ID and ensure the environment exists.",
                    "missing_credentials": [],
                    "details": {
                        "target_environment_id": target_environment_id,
                        "correlation_id": correlation_id,
                        "error_type": "target_environment_not_found"
                    }
                }

            source_env_name = source_env.get("name") or source_env.get("n8n_name", "Unknown")
            target_env_name = target_env.get("name") or target_env.get("n8n_name", "Unknown")
            provider = source_env.get("provider", "n8n") or "n8n"

            # Get target environment credentials
            try:
                target_adapter = self.provider_registry.get_adapter_for_environment(target_env)
                target_credentials = await target_adapter.get_credentials()
                target_cred_map = {(c.get("type"), c.get("name")): c for c in target_credentials}
            except Exception as e:
                logger.error(
                    f"Credential validation failed: Cannot fetch target credentials "
                    f"(environment_id={target_environment_id}, error={str(e)}, "
                    f"correlation_id={correlation_id})"
                )
                return {
                    "passed": False,
                    "check": check_name,
                    "message": f"Failed to fetch credentials from target environment '{target_env_name}'.",
                    "remediation": "Navigate to Environments > Edit and verify provider settings (base_url, api_key). Ensure the provider instance is running and accessible.",
                    "missing_credentials": [],
                    "details": {
                        "target_environment_id": target_environment_id,
                        "target_environment_name": target_env_name,
                        "correlation_id": correlation_id,
                        "error_type": "target_credentials_fetch_failed",
                        "error": str(e)
                    }
                }

            # Get workflow data from cache first
            workflow_record = await db_service.get_workflow(tenant_id, source_environment_id, workflow_id)

            # If not in cache, try GitHub
            if not workflow_record:
                from app.services.github_service import GitHubService

                source_env_type = source_env.get("n8n_type")
                if source_env.get("git_repo_url") and source_env.get("git_pat"):
                    if not source_env_type:
                        logger.warning(
                            f"Credential validation failed: Source environment missing type "
                            f"(environment_id={source_environment_id}, workflow_id={workflow_id}, "
                            f"correlation_id={correlation_id})"
                        )
                        return {
                            "passed": False,
                            "check": check_name,
                            "message": f"Source environment '{source_env_name}' is missing environment type configuration.",
                            "remediation": "Navigate to Environments > Edit and set the environment type.",
                            "missing_credentials": [],
                            "details": {
                                "source_environment_id": source_environment_id,
                                "source_environment_name": source_env_name,
                                "workflow_id": workflow_id,
                                "correlation_id": correlation_id,
                                "error_type": "missing_environment_type"
                            }
                        }

                    try:
                        repo_url = source_env.get("git_repo_url", "").rstrip('/').replace('.git', '')
                        repo_parts = repo_url.split("/")
                        source_github = GitHubService(
                            token=source_env.get("git_pat"),
                            repo_owner=repo_parts[-2] if len(repo_parts) >= 2 else "",
                            repo_name=repo_parts[-1] if len(repo_parts) >= 1 else "",
                            branch=source_env.get("git_branch", "main"),
                        )

                        if source_github.is_configured():
                            github_workflows = await source_github.get_all_workflows_from_github(environment_type=source_env_type)
                            github_wf = github_workflows.get(workflow_id)
                            if github_wf:
                                workflow_record = {
                                    "name": github_wf.get("name", "Unknown"),
                                    "workflow_data": github_wf
                                }
                    except Exception as e:
                        logger.warning(
                            f"Failed to fetch workflow from GitHub during credential validation "
                            f"(workflow_id={workflow_id}, error={str(e)}, correlation_id={correlation_id})"
                        )

            if not workflow_record:
                logger.warning(
                    f"Credential validation: Workflow not found in cache or GitHub "
                    f"(workflow_id={workflow_id}, correlation_id={correlation_id})"
                )
                # Not a blocking issue - might be a new workflow being deployed
                # Return passed=True with warning
                return {
                    "passed": True,
                    "check": check_name,
                    "message": f"Workflow '{workflow_id}' not found in source environment. Assuming new workflow deployment.",
                    "remediation": None,
                    "missing_credentials": [],
                    "details": {
                        "workflow_id": workflow_id,
                        "source_environment_id": source_environment_id,
                        "source_environment_name": source_env_name,
                        "correlation_id": correlation_id,
                        "warning": "workflow_not_found_in_source"
                    }
                }

            workflow_name = workflow_record.get("name", "Unknown")
            workflow_data = workflow_record.get("workflow_data", {})

            # Extract credentials from workflow nodes
            blocking_issues = []
            nodes = workflow_data.get("nodes", [])

            for node in nodes:
                node_credentials = node.get("credentials", {})
                for cred_type, cred_info in node_credentials.items():
                    if isinstance(cred_info, dict):
                        cred_name = cred_info.get("name", "Unknown")
                    else:
                        cred_name = str(cred_info) if cred_info else "Unknown"

                    logical_key = f"{cred_type}:{cred_name}"

                    # Try provider-aware logical mapping first
                    logical = await db_service.find_logical_credential_by_name(tenant_id, logical_key)
                    if logical:
                        mapping = await db_service.get_mapping_for_logical(
                            tenant_id,
                            target_environment_id,
                            provider,
                            logical.get("id"),
                        )
                        if not mapping:
                            blocking_issues.append({
                                "logical_credential_key": logical_key,
                                "issue_type": "missing_mapping",
                                "message": f"No mapping for '{logical_key}' in target environment '{target_env_name}'"
                            })
                            continue

                        # Check if mapped physical credential exists
                        mapped_key = (
                            mapping.get("physical_type") or cred_type,
                            mapping.get("physical_name") or cred_name,
                        )
                        if mapped_key not in target_cred_map:
                            blocking_issues.append({
                                "logical_credential_key": logical_key,
                                "issue_type": "mapped_missing_in_target",
                                "message": f"Mapped credential '{mapping.get('physical_name')}' (mapped from '{logical_key}') not found in target environment '{target_env_name}'"
                            })
                            continue
                    else:
                        # No logical credential defined - check direct match
                        cred_key = (cred_type, cred_name)
                        if cred_key not in target_cred_map:
                            # Blocking issue: credential not found and no logical mapping
                            blocking_issues.append({
                                "logical_credential_key": logical_key,
                                "issue_type": "credential_missing_in_target",
                                "message": f"Credential '{logical_key}' not found in target environment '{target_env_name}' and no logical credential mapping defined"
                            })

            # Return validation result
            if blocking_issues:
                missing_creds = [issue["logical_credential_key"] for issue in blocking_issues]
                issue_messages = [issue["message"] for issue in blocking_issues]

                logger.warning(
                    f"Credential validation failed: Missing credentials "
                    f"(workflow_id={workflow_id}, workflow_name={workflow_name}, "
                    f"missing_count={len(blocking_issues)}, correlation_id={correlation_id})"
                )

                return {
                    "passed": False,
                    "check": check_name,
                    "message": f"Workflow '{workflow_name}' requires {len(blocking_issues)} credential(s) that are missing in target environment '{target_env_name}'.",
                    "remediation": "Navigate to Credentials page and either: (1) Create the missing physical credentials in the target environment, or (2) Create logical credential mappings to map source credentials to existing target credentials.",
                    "missing_credentials": missing_creds,
                    "details": {
                        "workflow_id": workflow_id,
                        "workflow_name": workflow_name,
                        "source_environment_id": source_environment_id,
                        "source_environment_name": source_env_name,
                        "target_environment_id": target_environment_id,
                        "target_environment_name": target_env_name,
                        "correlation_id": correlation_id,
                        "blocking_issues": blocking_issues,
                        "issue_messages": issue_messages
                    }
                }
            else:
                logger.info(
                    f"Credential validation passed: All credentials available "
                    f"(workflow_id={workflow_id}, workflow_name={workflow_name}, "
                    f"target_environment={target_env_name})"
                )

                return {
                    "passed": True,
                    "check": check_name,
                    "message": f"All credentials required by workflow '{workflow_name}' are available in target environment '{target_env_name}'.",
                    "remediation": None,
                    "missing_credentials": [],
                    "details": {
                        "workflow_id": workflow_id,
                        "workflow_name": workflow_name,
                        "source_environment_id": source_environment_id,
                        "source_environment_name": source_env_name,
                        "target_environment_id": target_environment_id,
                        "target_environment_name": target_env_name,
                        "credentials_checked": len(nodes)
                    }
                }

        except Exception as e:
            # Fail-open: Internal validation errors should not block promotion
            # but should be logged with correlation ID for monitoring
            error_type = type(e).__name__
            logger.warning(
                f"Credential validation internal error (fail-open): Unexpected exception "
                f"(workflow_id={workflow_id}, source_environment_id={source_environment_id}, "
                f"target_environment_id={target_environment_id}, error_type={error_type}, "
                f"error={str(e)}, correlation_id={correlation_id})"
            )

            # Return passed=True for fail-open behavior, but include warning details
            return {
                "passed": True,  # Fail-open: allow promotion to proceed
                "check": check_name,
                "message": f"Credential availability check encountered an internal error but allowing promotion to proceed (fail-open).",
                "remediation": None,
                "missing_credentials": [],
                "details": {
                    "workflow_id": workflow_id,
                    "source_environment_id": source_environment_id,
                    "target_environment_id": target_environment_id,
                    "correlation_id": correlation_id,
                    "error_type": error_type,
                    "error": str(e),
                    "fail_open": True,
                    "warning": "Internal validation error - check logs"
                }
            }

    async def validate_drift_policy_compliance(
        self,
        target_environment_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Validate that no drift policy violations would block this promotion.

        Uses the DriftPolicyEnforcementService to check for active or expired drift
        incidents that would block deployment, including approval override support.

        Args:
            target_environment_id: The target environment to check
            tenant_id: The tenant ID (for database access control)

        Returns:
            Dict with validation result:
            {
                "passed": bool,
                "check": "drift_policy_compliance",
                "message": str,
                "remediation": Optional[str],
                "blocking_incidents": List[Dict[str, Any]],
                "details": Dict[str, Any]
            }
        """
        from uuid import uuid4

        check_name = "drift_policy_compliance"
        correlation_id = str(uuid4())

        try:
            # Fetch environment configuration from database
            environment = await db_service.get_environment(
                environment_id=target_environment_id,
                tenant_id=tenant_id
            )

            if not environment:
                logger.warning(
                    f"Drift policy validation failed: Environment not found "
                    f"(environment_id={target_environment_id}, correlation_id={correlation_id})"
                )
                return {
                    "passed": False,
                    "check": check_name,
                    "message": f"Target environment '{target_environment_id}' not found in database.",
                    "remediation": "Verify the environment ID and ensure the environment exists.",
                    "blocking_incidents": [],
                    "details": {
                        "environment_id": target_environment_id,
                        "correlation_id": correlation_id,
                        "error_type": "environment_not_found"
                    }
                }

            environment_name = environment.get("name") or environment.get("n8n_name", "Unknown")

            # Use the DriftPolicyEnforcementService with approval override support
            enforcement_decision = await drift_policy_enforcement_service.check_enforcement_with_override(
                tenant_id=tenant_id,
                environment_id=target_environment_id,
                correlation_id=correlation_id,
            )

            if not enforcement_decision.allowed:
                # Drift policy is blocking deployment
                incident_details = enforcement_decision.incident_details or {}
                incident_id = enforcement_decision.incident_id
                incident_title = incident_details.get("title", "Unknown")
                severity = incident_details.get("severity", "unknown")

                blocking_incidents = [{
                    "incident_id": incident_id,
                    "incident_title": incident_title,
                    "severity": severity,
                    "reason": enforcement_decision.result.value,
                    "status": incident_details.get("status"),
                    "expires_at": incident_details.get("expires_at"),
                }]

                # Generate user-friendly message based on enforcement result
                if enforcement_decision.result == EnforcementResult.BLOCKED_TTL_EXPIRED:
                    message = (
                        f"Deployment blocked: Drift incident has expired. "
                        f"Please resolve or extend the TTL for incident '{incident_title}' "
                        f"before deploying to environment '{environment_name}'."
                    )
                    remediation = (
                        f"Navigate to Drift Incidents and either: "
                        f"(1) Resolve incident '{incident_title}', "
                        f"(2) Extend the TTL if the drift is acceptable, or "
                        f"(3) Request a deployment override approval."
                    )
                elif enforcement_decision.result == EnforcementResult.BLOCKED_ACTIVE_DRIFT:
                    message = (
                        f"Deployment blocked: Active drift incident exists. "
                        f"Please resolve incident '{incident_title}' "
                        f"before deploying to environment '{environment_name}'."
                    )
                    remediation = (
                        f"Navigate to Drift Incidents and either: "
                        f"(1) Resolve incident '{incident_title}', "
                        f"(2) Acknowledge the incident, or "
                        f"(3) Request a deployment override approval."
                    )
                else:
                    message = enforcement_decision.reason or (
                        f"Deployment blocked by drift policy in environment '{environment_name}'."
                    )
                    remediation = (
                        "Navigate to Drift Incidents and resolve any active drift incidents "
                        "or request a deployment override approval."
                    )

                # Check for pending overrides to provide helpful context
                pending_overrides = []
                if incident_id:
                    pending_overrides = await drift_policy_enforcement_service.get_pending_overrides(
                        tenant_id=tenant_id,
                        incident_id=incident_id,
                    )
                    if pending_overrides:
                        remediation += (
                            f" Note: There are {len(pending_overrides)} pending override request(s) "
                            f"for this incident."
                        )

                logger.warning(
                    f"Drift policy validation failed: Deployment blocked "
                    f"(environment_id={target_environment_id}, environment_name={environment_name}, "
                    f"result={enforcement_decision.result.value}, incident_id={incident_id}, "
                    f"correlation_id={correlation_id})"
                )

                return {
                    "passed": False,
                    "check": check_name,
                    "message": message,
                    "remediation": remediation,
                    "blocking_incidents": blocking_incidents,
                    "details": {
                        "environment_id": target_environment_id,
                        "environment_name": environment_name,
                        "correlation_id": correlation_id,
                        "enforcement_result": enforcement_decision.result.value,
                        "reason": enforcement_decision.reason,
                        "incident_id": incident_id,
                        "incident_title": incident_title,
                        "severity": severity,
                        "policy_config": enforcement_decision.policy_config,
                        "pending_overrides": len(pending_overrides),
                        **incident_details,
                    }
                }
            else:
                # Enforcement check passed - either no blocking incidents or override approved
                incident_details = enforcement_decision.incident_details or {}
                override_info = {}

                # Check if this was allowed due to an override
                if incident_details.get("override_approval_id"):
                    override_info = {
                        "override_approved": True,
                        "override_approval_id": incident_details.get("override_approval_id"),
                        "override_approval_type": incident_details.get("override_approval_type"),
                        "override_approved_by": incident_details.get("override_approved_by"),
                        "override_approved_at": incident_details.get("override_approved_at"),
                    }
                    message = (
                        f"Drift policy check passed for environment '{environment_name}' "
                        f"(deployment approved via override)."
                    )
                    logger.info(
                        f"Drift policy validation passed via override "
                        f"(environment_id={target_environment_id}, environment_name={environment_name}, "
                        f"approval_id={incident_details.get('override_approval_id')}, "
                        f"correlation_id={correlation_id})"
                    )
                else:
                    message = (
                        f"No drift policy violations blocking deployment to environment '{environment_name}'."
                    )
                    logger.info(
                        f"Drift policy validation passed: No blocking incidents "
                        f"(environment_id={target_environment_id}, environment_name={environment_name}, "
                        f"reason={enforcement_decision.reason}, correlation_id={correlation_id})"
                    )

                return {
                    "passed": True,
                    "check": check_name,
                    "message": message,
                    "remediation": None,
                    "blocking_incidents": [],
                    "details": {
                        "environment_id": target_environment_id,
                        "environment_name": environment_name,
                        "correlation_id": correlation_id,
                        "enforcement_result": enforcement_decision.result.value,
                        "reason": enforcement_decision.reason,
                        "policy_config": enforcement_decision.policy_config,
                        **override_info,
                    }
                }

        except Exception as e:
            # Fail-open: Internal validation errors should not block promotion
            # but should be logged with correlation ID for monitoring
            error_type = type(e).__name__
            logger.warning(
                f"Drift policy validation internal error (fail-open): Unexpected exception "
                f"(environment_id={target_environment_id}, error_type={error_type}, "
                f"error={str(e)}, correlation_id={correlation_id})"
            )

            # Return passed=True for fail-open behavior, but include warning details
            return {
                "passed": True,  # Fail-open: allow promotion to proceed
                "check": check_name,
                "message": f"Drift policy check encountered an internal error but allowing promotion to proceed (fail-open).",
                "remediation": None,
                "blocking_incidents": [],
                "details": {
                    "environment_id": target_environment_id,
                    "correlation_id": correlation_id,
                    "error_type": error_type,
                    "error": str(e),
                    "fail_open": True,
                    "warning": "Internal validation error - check logs"
                }
            }

    async def run_preflight_validation(
        self,
        workflow_id: str,
        source_environment_id: str,
        target_environment_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Run all pre-flight validation checks with fail-fast behavior.

        Orchestrates all validation checks:
        1. Target environment health
        2. Credential availability
        3. Drift policy compliance

        Implements fail-closed for validation failures (blocks promotion) and
        fail-open for internal errors (allows promotion with warning log).

        Args:
            workflow_id: Workflow to promote
            source_environment_id: Source environment ID
            target_environment_id: Target environment ID
            tenant_id: The tenant ID (for database access control)

        Returns:
            Dict with complete validation result:
            {
                "validation_passed": bool,
                "validation_errors": List[Dict[str, Any]],
                "validation_warnings": List[Dict[str, Any]],
                "checks_run": List[str],
                "correlation_id": str,
                "timestamp": str
            }
        """
        from datetime import datetime
        from uuid import uuid4

        correlation_id = str(uuid4())
        timestamp = datetime.utcnow()
        checks_run = []
        validation_errors = []
        validation_warnings = []
        validation_passed = True

        logger.info(
            f"Starting pre-flight validation "
            f"(workflow_id={workflow_id}, source_env={source_environment_id}, "
            f"target_env={target_environment_id}, correlation_id={correlation_id})"
        )

        # Check 1: Target environment health
        try:
            checks_run.append("target_environment_health")
            health_result = await self.validate_target_environment_health(
                target_environment_id=target_environment_id,
                tenant_id=tenant_id,
                timeout_seconds=5.0
            )

            if health_result.get("passed"):
                # Check passed
                if health_result.get("details", {}).get("fail_open"):
                    # Fail-open scenario - add as warning
                    validation_warnings.append({
                        "check": health_result.get("check"),
                        "status": "warning",
                        "message": health_result.get("message"),
                        "remediation": health_result.get("remediation"),
                        "details": health_result.get("details", {})
                    })
                    logger.info(
                        f"Health check passed (fail-open) - continuing validation "
                        f"(correlation_id={correlation_id})"
                    )
            else:
                # Check failed - fail-closed, block promotion
                validation_errors.append({
                    "check": health_result.get("check"),
                    "status": "failed",
                    "message": health_result.get("message"),
                    "remediation": health_result.get("remediation"),
                    "details": health_result.get("details", {})
                })
                validation_passed = False
                logger.warning(
                    f"Health check failed - failing fast "
                    f"(correlation_id={correlation_id})"
                )
                # Fail-fast: stop validation on first failure
                return {
                    "validation_passed": validation_passed,
                    "validation_errors": validation_errors,
                    "validation_warnings": validation_warnings,
                    "checks_run": checks_run,
                    "correlation_id": correlation_id,
                    "timestamp": timestamp.isoformat()
                }

        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                f"Unexpected error in health check orchestration "
                f"(error_type={error_type}, error={str(e)}, correlation_id={correlation_id})"
            )
            # Fail-open for unexpected orchestration errors
            validation_warnings.append({
                "check": "target_environment_health",
                "status": "warning",
                "message": "Health check encountered an unexpected error but allowing promotion to proceed (fail-open).",
                "remediation": None,
                "details": {
                    "correlation_id": correlation_id,
                    "error_type": error_type,
                    "error": str(e),
                    "fail_open": True
                }
            })

        # Check 2: Credential availability
        try:
            checks_run.append("credential_availability")
            credential_result = await self.validate_credentials_available(
                workflow_id=workflow_id,
                source_environment_id=source_environment_id,
                target_environment_id=target_environment_id,
                tenant_id=tenant_id
            )

            if credential_result.get("passed"):
                # Check passed
                if credential_result.get("details", {}).get("fail_open"):
                    # Fail-open scenario - add as warning
                    validation_warnings.append({
                        "check": credential_result.get("check"),
                        "status": "warning",
                        "message": credential_result.get("message"),
                        "remediation": credential_result.get("remediation"),
                        "details": credential_result.get("details", {})
                    })
                    logger.info(
                        f"Credential check passed (fail-open) - continuing validation "
                        f"(correlation_id={correlation_id})"
                    )
            else:
                # Check failed - fail-closed, block promotion
                validation_errors.append({
                    "check": credential_result.get("check"),
                    "status": "failed",
                    "message": credential_result.get("message"),
                    "remediation": credential_result.get("remediation"),
                    "details": credential_result.get("details", {})
                })
                validation_passed = False
                logger.warning(
                    f"Credential check failed - failing fast "
                    f"(correlation_id={correlation_id})"
                )
                # Fail-fast: stop validation on first failure
                return {
                    "validation_passed": validation_passed,
                    "validation_errors": validation_errors,
                    "validation_warnings": validation_warnings,
                    "checks_run": checks_run,
                    "correlation_id": correlation_id,
                    "timestamp": timestamp.isoformat()
                }

        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                f"Unexpected error in credential check orchestration "
                f"(error_type={error_type}, error={str(e)}, correlation_id={correlation_id})"
            )
            # Fail-open for unexpected orchestration errors
            validation_warnings.append({
                "check": "credential_availability",
                "status": "warning",
                "message": "Credential check encountered an unexpected error but allowing promotion to proceed (fail-open).",
                "remediation": None,
                "details": {
                    "correlation_id": correlation_id,
                    "error_type": error_type,
                    "error": str(e),
                    "fail_open": True
                }
            })

        # Check 3: Drift policy compliance
        try:
            checks_run.append("drift_policy_compliance")
            drift_result = await self.validate_drift_policy_compliance(
                target_environment_id=target_environment_id,
                tenant_id=tenant_id
            )

            if drift_result.get("passed"):
                # Check passed
                if drift_result.get("details", {}).get("fail_open"):
                    # Fail-open scenario - add as warning
                    validation_warnings.append({
                        "check": drift_result.get("check"),
                        "status": "warning",
                        "message": drift_result.get("message"),
                        "remediation": drift_result.get("remediation"),
                        "details": drift_result.get("details", {})
                    })
                    logger.info(
                        f"Drift policy check passed (fail-open) - continuing validation "
                        f"(correlation_id={correlation_id})"
                    )
            else:
                # Check failed - fail-closed, block promotion
                validation_errors.append({
                    "check": drift_result.get("check"),
                    "status": "failed",
                    "message": drift_result.get("message"),
                    "remediation": drift_result.get("remediation"),
                    "details": drift_result.get("details", {})
                })
                validation_passed = False
                logger.warning(
                    f"Drift policy check failed - failing fast "
                    f"(correlation_id={correlation_id})"
                )
                # Fail-fast: stop validation on first failure
                return {
                    "validation_passed": validation_passed,
                    "validation_errors": validation_errors,
                    "validation_warnings": validation_warnings,
                    "checks_run": checks_run,
                    "correlation_id": correlation_id,
                    "timestamp": timestamp.isoformat()
                }

        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                f"Unexpected error in drift policy check orchestration "
                f"(error_type={error_type}, error={str(e)}, correlation_id={correlation_id})"
            )
            # Fail-open for unexpected orchestration errors
            validation_warnings.append({
                "check": "drift_policy_compliance",
                "status": "warning",
                "message": "Drift policy check encountered an unexpected error but allowing promotion to proceed (fail-open).",
                "remediation": None,
                "details": {
                    "correlation_id": correlation_id,
                    "error_type": error_type,
                    "error": str(e),
                    "fail_open": True
                }
            })

        # All checks completed successfully
        logger.info(
            f"Pre-flight validation completed successfully "
            f"(workflow_id={workflow_id}, checks_run={len(checks_run)}, "
            f"warnings={len(validation_warnings)}, correlation_id={correlation_id})"
        )

        return {
            "validation_passed": validation_passed,
            "validation_errors": validation_errors,
            "validation_warnings": validation_warnings,
            "checks_run": checks_run,
            "correlation_id": correlation_id,
            "timestamp": timestamp.isoformat()
        }
