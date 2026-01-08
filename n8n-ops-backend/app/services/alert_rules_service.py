"""
Alert Rules Service

Provides customizable alert rules based on error rate thresholds, error types,
or specific workflow failures. Supports multiple notification channels and
escalation policies for critical errors that remain unresolved.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from app.services.database import db_service
from app.services.notification_service import notification_service
from app.schemas.notification import (
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    AlertRuleHistoryEntry,
    AlertRuleHistoryResponse,
    AlertRuleEvaluationResult,
    AlertRuleSummary,
    AlertRuleType,
    AlertRuleTypeCatalogItem,
    ALERT_RULE_TYPE_CATALOG,
    AlertRuleHistoryEventType,
    AlertSeverity,
)

logger = logging.getLogger(__name__)


class AlertRulesService:
    """Service for managing alert rules and their evaluation"""

    # ============================================
    # CRUD Operations
    # ============================================

    async def create_rule(
        self,
        tenant_id: str,
        data: AlertRuleCreate
    ) -> AlertRuleResponse:
        """Create a new alert rule"""
        rule_data = {
            "tenant_id": tenant_id,
            "name": data.name,
            "description": data.description,
            "rule_type": data.rule_type.value if isinstance(data.rule_type, AlertRuleType) else data.rule_type,
            "threshold_config": data.threshold_config,
            "environment_id": data.environment_id,
            "channel_ids": data.channel_ids,
            "escalation_config": data.escalation_config,
            "is_enabled": data.is_enabled,
        }

        result = await db_service.create_alert_rule(rule_data)
        return self._rule_to_response(result)

    async def update_rule(
        self,
        tenant_id: str,
        rule_id: str,
        data: AlertRuleUpdate
    ) -> Optional[AlertRuleResponse]:
        """Update an existing alert rule"""
        update_data = {}
        if data.name is not None:
            update_data["name"] = data.name
        if data.description is not None:
            update_data["description"] = data.description
        if data.threshold_config is not None:
            update_data["threshold_config"] = data.threshold_config
        if data.environment_id is not None:
            update_data["environment_id"] = data.environment_id if data.environment_id else None
        if data.channel_ids is not None:
            update_data["channel_ids"] = data.channel_ids
        if data.escalation_config is not None:
            update_data["escalation_config"] = data.escalation_config
        if data.is_enabled is not None:
            update_data["is_enabled"] = data.is_enabled

        if not update_data:
            # Nothing to update, return current rule
            rule = await db_service.get_alert_rule(rule_id, tenant_id)
            if not rule:
                return None
            return self._rule_to_response(rule)

        result = await db_service.update_alert_rule(rule_id, tenant_id, update_data)
        if not result:
            return None

        return self._rule_to_response(result)

    async def delete_rule(self, tenant_id: str, rule_id: str) -> bool:
        """Delete an alert rule"""
        return await db_service.delete_alert_rule(rule_id, tenant_id)

    async def get_rule(
        self,
        tenant_id: str,
        rule_id: str
    ) -> Optional[AlertRuleResponse]:
        """Get a specific alert rule"""
        rule = await db_service.get_alert_rule(rule_id, tenant_id)
        if not rule:
            return None
        return self._rule_to_response(rule)

    async def get_rules(
        self,
        tenant_id: str,
        include_disabled: bool = False
    ) -> List[AlertRuleResponse]:
        """Get all alert rules for a tenant"""
        rules = await db_service.get_alert_rules(tenant_id, include_disabled)
        return [self._rule_to_response(r) for r in rules]

    async def get_rules_summary(self, tenant_id: str) -> AlertRuleSummary:
        """Get summary statistics for alert rules"""
        rules = await db_service.get_alert_rules(tenant_id, include_disabled=True)

        total_rules = len(rules)
        enabled_rules = sum(1 for r in rules if r.get("is_enabled", False))
        firing_rules = sum(1 for r in rules if r.get("is_firing", False))
        muted_rules = sum(
            1 for r in rules
            if r.get("muted_until") and datetime.fromisoformat(str(r["muted_until"]).replace("Z", "+00:00")) > datetime.utcnow().replace(tzinfo=None)
        )

        rules_by_type: Dict[str, int] = {}
        for r in rules:
            rule_type = r.get("rule_type", "unknown")
            rules_by_type[rule_type] = rules_by_type.get(rule_type, 0) + 1

        return AlertRuleSummary(
            total_rules=total_rules,
            enabled_rules=enabled_rules,
            firing_rules=firing_rules,
            muted_rules=muted_rules,
            rules_by_type=rules_by_type
        )

    # ============================================
    # Mute/Unmute Operations
    # ============================================

    async def mute_rule(
        self,
        tenant_id: str,
        rule_id: str,
        mute_duration_minutes: int,
        reason: Optional[str] = None
    ) -> Optional[AlertRuleResponse]:
        """Mute an alert rule for a specified duration"""
        mute_until = datetime.utcnow() + timedelta(minutes=mute_duration_minutes)

        result = await db_service.update_alert_rule(rule_id, tenant_id, {
            "muted_until": mute_until.isoformat(),
            "mute_reason": reason
        })

        if result:
            # Log the mute event
            await db_service.create_alert_rule_history({
                "tenant_id": tenant_id,
                "alert_rule_id": rule_id,
                "event_type": AlertRuleHistoryEventType.MUTED.value,
                "evaluation_result": {
                    "mute_duration_minutes": mute_duration_minutes,
                    "reason": reason,
                    "muted_until": mute_until.isoformat()
                }
            })

        return self._rule_to_response(result) if result else None

    async def unmute_rule(
        self,
        tenant_id: str,
        rule_id: str
    ) -> Optional[AlertRuleResponse]:
        """Unmute an alert rule"""
        result = await db_service.update_alert_rule(rule_id, tenant_id, {
            "muted_until": None,
            "mute_reason": None
        })

        if result:
            # Log the unmute event
            await db_service.create_alert_rule_history({
                "tenant_id": tenant_id,
                "alert_rule_id": rule_id,
                "event_type": AlertRuleHistoryEventType.UNMUTED.value,
                "evaluation_result": {}
            })

        return self._rule_to_response(result) if result else None

    # ============================================
    # History Operations
    # ============================================

    async def get_rule_history(
        self,
        tenant_id: str,
        rule_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> AlertRuleHistoryResponse:
        """Get history for a specific alert rule"""
        history, total = await db_service.get_alert_rule_history(
            rule_id, tenant_id, limit, offset
        )

        items = [
            AlertRuleHistoryEntry(
                id=h["id"],
                tenant_id=h["tenant_id"],
                alert_rule_id=h["alert_rule_id"],
                event_type=h["event_type"],
                evaluation_result=h.get("evaluation_result"),
                escalation_level=h.get("escalation_level"),
                channels_notified=h.get("channels_notified"),
                notification_success=h.get("notification_success"),
                created_at=h["created_at"]
            )
            for h in history
        ]

        return AlertRuleHistoryResponse(
            items=items,
            total=total,
            has_more=(offset + limit) < total
        )

    # ============================================
    # Rule Evaluation
    # ============================================

    async def evaluate_rule(
        self,
        tenant_id: str,
        rule_id: str
    ) -> AlertRuleEvaluationResult:
        """Evaluate a single alert rule and return the result"""
        rule = await db_service.get_alert_rule(rule_id, tenant_id)
        if not rule:
            raise ValueError(f"Alert rule {rule_id} not found")

        return await self._evaluate_single_rule(rule)

    async def evaluate_all_rules(self, tenant_id: str) -> List[AlertRuleEvaluationResult]:
        """Evaluate all enabled alert rules for a tenant"""
        rules = await db_service.get_alert_rules(tenant_id, include_disabled=False)
        results = []

        for rule in rules:
            try:
                # Skip muted rules
                if rule.get("muted_until"):
                    muted_until = datetime.fromisoformat(str(rule["muted_until"]).replace("Z", "+00:00"))
                    if muted_until > datetime.utcnow().replace(tzinfo=None):
                        continue

                result = await self._evaluate_single_rule(rule)
                results.append(result)

                # Process the result (trigger/resolve alerts, handle escalation)
                await self._process_evaluation_result(rule, result)

            except Exception as e:
                logger.error(f"Error evaluating alert rule {rule['id']}: {e}")
                results.append(AlertRuleEvaluationResult(
                    rule_id=rule["id"],
                    rule_name=rule.get("name", "Unknown"),
                    is_triggered=False,
                    message=f"Evaluation error: {str(e)}",
                    evaluated_at=datetime.utcnow()
                ))

        return results

    async def _evaluate_single_rule(
        self,
        rule: Dict[str, Any]
    ) -> AlertRuleEvaluationResult:
        """Evaluate a single rule based on its type"""
        rule_type = rule.get("rule_type")
        threshold_config = rule.get("threshold_config", {})
        tenant_id = rule["tenant_id"]
        environment_id = rule.get("environment_id")

        now = datetime.utcnow()

        if rule_type == AlertRuleType.ERROR_RATE.value:
            return await self._evaluate_error_rate(rule, threshold_config, tenant_id, environment_id, now)
        elif rule_type == AlertRuleType.ERROR_TYPE.value:
            return await self._evaluate_error_type(rule, threshold_config, tenant_id, environment_id, now)
        elif rule_type == AlertRuleType.WORKFLOW_FAILURE.value:
            return await self._evaluate_workflow_failure(rule, threshold_config, tenant_id, environment_id, now)
        elif rule_type == AlertRuleType.CONSECUTIVE_FAILURES.value:
            return await self._evaluate_consecutive_failures(rule, threshold_config, tenant_id, environment_id, now)
        elif rule_type == AlertRuleType.EXECUTION_DURATION.value:
            return await self._evaluate_execution_duration(rule, threshold_config, tenant_id, environment_id, now)
        else:
            return AlertRuleEvaluationResult(
                rule_id=rule["id"],
                rule_name=rule.get("name", "Unknown"),
                is_triggered=False,
                message=f"Unknown rule type: {rule_type}",
                evaluated_at=now
            )

    async def _evaluate_error_rate(
        self,
        rule: Dict[str, Any],
        config: Dict[str, Any],
        tenant_id: str,
        environment_id: Optional[str],
        now: datetime
    ) -> AlertRuleEvaluationResult:
        """Evaluate error rate threshold"""
        threshold_percent = config.get("threshold_percent", 10)
        time_window_minutes = config.get("time_window_minutes", 60)
        min_executions = config.get("min_executions", 10)

        # Get error rate from database
        metrics = await db_service.evaluate_error_rate(
            tenant_id, environment_id, time_window_minutes
        )

        total_executions = metrics.get("total_executions", 0)
        error_count = metrics.get("error_count", 0)
        error_rate = metrics.get("error_rate", 0)

        is_triggered = (
            total_executions >= min_executions and
            error_rate > threshold_percent
        )

        message = (
            f"Error rate is {error_rate:.1f}% ({error_count}/{total_executions} executions) "
            f"in the last {time_window_minutes} minutes"
        )

        if total_executions < min_executions:
            message = f"Insufficient executions ({total_executions}/{min_executions} required)"

        return AlertRuleEvaluationResult(
            rule_id=rule["id"],
            rule_name=rule.get("name", "Unknown"),
            is_triggered=is_triggered,
            current_value=error_rate,
            threshold_value=threshold_percent,
            message=message,
            details={
                "total_executions": total_executions,
                "error_count": error_count,
                "error_rate": error_rate,
                "time_window_minutes": time_window_minutes
            },
            evaluated_at=now
        )

    async def _evaluate_error_type(
        self,
        rule: Dict[str, Any],
        config: Dict[str, Any],
        tenant_id: str,
        environment_id: Optional[str],
        now: datetime
    ) -> AlertRuleEvaluationResult:
        """Evaluate error type matching"""
        error_types = config.get("error_types", [])
        time_window_minutes = config.get("time_window_minutes", 60)
        min_occurrences = config.get("min_occurrences", 1)

        # Get error intelligence from database
        errors = await db_service.get_error_intelligence_for_alert(
            tenant_id, environment_id, time_window_minutes
        )

        matching_errors = [
            e for e in errors
            if e.get("error_type") in error_types
        ]

        total_matching = sum(e.get("count", 0) for e in matching_errors)
        is_triggered = total_matching >= min_occurrences

        message = (
            f"Found {total_matching} occurrences of error types: {', '.join(error_types)} "
            f"in the last {time_window_minutes} minutes"
        )

        return AlertRuleEvaluationResult(
            rule_id=rule["id"],
            rule_name=rule.get("name", "Unknown"),
            is_triggered=is_triggered,
            current_value=float(total_matching),
            threshold_value=float(min_occurrences),
            message=message,
            details={
                "matching_errors": matching_errors,
                "total_matching": total_matching,
                "error_types_monitored": error_types
            },
            evaluated_at=now
        )

    async def _evaluate_workflow_failure(
        self,
        rule: Dict[str, Any],
        config: Dict[str, Any],
        tenant_id: str,
        environment_id: Optional[str],
        now: datetime
    ) -> AlertRuleEvaluationResult:
        """Evaluate workflow failure detection"""
        workflow_ids = config.get("workflow_ids", [])
        canonical_ids = config.get("canonical_ids", [])
        any_workflow = config.get("any_workflow", False)

        # Get recent failures
        failures = await db_service.get_recent_workflow_failures(
            tenant_id, environment_id, workflow_ids, canonical_ids, any_workflow
        )

        is_triggered = len(failures) > 0

        if is_triggered:
            failure_names = [f.get("workflow_name", f.get("workflow_id", "Unknown")) for f in failures[:5]]
            message = f"Workflow failures detected: {', '.join(failure_names)}"
            if len(failures) > 5:
                message += f" and {len(failures) - 5} more"
        else:
            message = "No matching workflow failures detected"

        return AlertRuleEvaluationResult(
            rule_id=rule["id"],
            rule_name=rule.get("name", "Unknown"),
            is_triggered=is_triggered,
            current_value=float(len(failures)),
            threshold_value=1.0,
            message=message,
            details={
                "failures": failures[:10],  # Limit details
                "total_failures": len(failures)
            },
            evaluated_at=now
        )

    async def _evaluate_consecutive_failures(
        self,
        rule: Dict[str, Any],
        config: Dict[str, Any],
        tenant_id: str,
        environment_id: Optional[str],
        now: datetime
    ) -> AlertRuleEvaluationResult:
        """Evaluate consecutive failure count"""
        failure_count_threshold = config.get("failure_count", 3)
        workflow_ids = config.get("workflow_ids", [])

        # Get consecutive failure counts
        max_consecutive = 0
        failing_workflow = None

        if workflow_ids:
            for wf_id in workflow_ids:
                count = await db_service.count_consecutive_failures(
                    tenant_id, wf_id, environment_id
                )
                if count > max_consecutive:
                    max_consecutive = count
                    failing_workflow = wf_id
        else:
            # Check all workflows (get the worst case)
            result = await db_service.get_max_consecutive_failures(tenant_id, environment_id)
            max_consecutive = result.get("max_consecutive", 0)
            failing_workflow = result.get("workflow_id")

        is_triggered = max_consecutive >= failure_count_threshold

        message = (
            f"Consecutive failures: {max_consecutive} "
            f"(threshold: {failure_count_threshold})"
        )
        if failing_workflow:
            message += f" for workflow {failing_workflow}"

        return AlertRuleEvaluationResult(
            rule_id=rule["id"],
            rule_name=rule.get("name", "Unknown"),
            is_triggered=is_triggered,
            current_value=float(max_consecutive),
            threshold_value=float(failure_count_threshold),
            message=message,
            details={
                "max_consecutive_failures": max_consecutive,
                "failing_workflow": failing_workflow
            },
            evaluated_at=now
        )

    async def _evaluate_execution_duration(
        self,
        rule: Dict[str, Any],
        config: Dict[str, Any],
        tenant_id: str,
        environment_id: Optional[str],
        now: datetime
    ) -> AlertRuleEvaluationResult:
        """Evaluate execution duration threshold"""
        max_duration_ms = config.get("max_duration_ms", 60000)
        workflow_ids = config.get("workflow_ids", [])

        # Get recent long-running executions
        long_running = await db_service.get_long_running_executions(
            tenant_id, environment_id, max_duration_ms, workflow_ids
        )

        is_triggered = len(long_running) > 0

        if is_triggered:
            max_duration = max(e.get("duration_ms", 0) for e in long_running)
            message = (
                f"Found {len(long_running)} executions exceeding {max_duration_ms}ms "
                f"(max: {max_duration}ms)"
            )
        else:
            message = f"No executions exceeding {max_duration_ms}ms duration"

        return AlertRuleEvaluationResult(
            rule_id=rule["id"],
            rule_name=rule.get("name", "Unknown"),
            is_triggered=is_triggered,
            current_value=float(max(e.get("duration_ms", 0) for e in long_running) if long_running else 0),
            threshold_value=float(max_duration_ms),
            message=message,
            details={
                "long_running_executions": long_running[:10],
                "total_count": len(long_running)
            },
            evaluated_at=now
        )

    async def _process_evaluation_result(
        self,
        rule: Dict[str, Any],
        result: AlertRuleEvaluationResult
    ) -> None:
        """Process the evaluation result and handle state transitions"""
        rule_id = rule["id"]
        tenant_id = rule["tenant_id"]
        was_firing = rule.get("is_firing", False)
        is_firing = result.is_triggered

        # Log the evaluation
        await db_service.create_alert_rule_history({
            "tenant_id": tenant_id,
            "alert_rule_id": rule_id,
            "event_type": AlertRuleHistoryEventType.EVALUATION.value,
            "evaluation_result": {
                "is_triggered": is_firing,
                "current_value": result.current_value,
                "threshold_value": result.threshold_value,
                "message": result.message
            }
        })

        if is_firing and not was_firing:
            # Alert just triggered
            await self._handle_alert_triggered(rule, result)
        elif is_firing and was_firing:
            # Alert continues firing - check for escalation
            await self._handle_alert_continuing(rule, result)
        elif not is_firing and was_firing:
            # Alert resolved
            await self._handle_alert_resolved(rule, result)

        # Update rule state
        now = datetime.utcnow()
        update_data: Dict[str, Any] = {
            "is_firing": is_firing,
            "last_evaluated_at": now.isoformat()
        }

        if is_firing:
            update_data["last_violation_at"] = now.isoformat()
            if not was_firing:
                update_data["first_violation_at"] = now.isoformat()
                update_data["consecutive_violations"] = 1
                update_data["current_escalation_level"] = 0
            else:
                update_data["consecutive_violations"] = rule.get("consecutive_violations", 0) + 1
        else:
            update_data["consecutive_violations"] = 0
            update_data["first_violation_at"] = None
            update_data["current_escalation_level"] = 0

        await db_service.update_alert_rule(rule_id, tenant_id, update_data)

    async def _handle_alert_triggered(
        self,
        rule: Dict[str, Any],
        result: AlertRuleEvaluationResult
    ) -> None:
        """Handle when an alert first triggers"""
        rule_id = rule["id"]
        tenant_id = rule["tenant_id"]

        # Log triggered event
        await db_service.create_alert_rule_history({
            "tenant_id": tenant_id,
            "alert_rule_id": rule_id,
            "event_type": AlertRuleHistoryEventType.TRIGGERED.value,
            "evaluation_result": {
                "current_value": result.current_value,
                "threshold_value": result.threshold_value,
                "message": result.message
            },
            "escalation_level": 0
        })

        # Send initial notification
        await self._send_alert_notification(
            rule, result, escalation_level=0, event_type="triggered"
        )

    async def _handle_alert_continuing(
        self,
        rule: Dict[str, Any],
        result: AlertRuleEvaluationResult
    ) -> None:
        """Handle when an alert continues firing - check for escalation"""
        escalation_config = rule.get("escalation_config")
        if not escalation_config:
            return

        levels = escalation_config.get("levels", [])
        current_level = rule.get("current_escalation_level", 0)
        first_violation_at = rule.get("first_violation_at")

        if not first_violation_at or current_level >= len(levels) - 1:
            return

        # Calculate time since first violation
        try:
            first_violation = datetime.fromisoformat(str(first_violation_at).replace("Z", "+00:00"))
            minutes_firing = (datetime.utcnow().replace(tzinfo=None) - first_violation.replace(tzinfo=None)).total_seconds() / 60
        except Exception:
            return

        # Check if we should escalate
        next_level = current_level + 1
        if next_level < len(levels):
            next_level_config = levels[next_level]
            delay_minutes = next_level_config.get("delay_minutes", 0)

            if minutes_firing >= delay_minutes:
                # Escalate
                await self._escalate_alert(rule, result, next_level, next_level_config)

        # Check repeat notification
        repeat_interval = escalation_config.get("repeat_interval_minutes")
        if repeat_interval:
            last_notification = rule.get("last_notification_at")
            if last_notification:
                try:
                    last_notif = datetime.fromisoformat(str(last_notification).replace("Z", "+00:00"))
                    minutes_since = (datetime.utcnow().replace(tzinfo=None) - last_notif.replace(tzinfo=None)).total_seconds() / 60
                    if minutes_since >= repeat_interval:
                        await self._send_alert_notification(
                            rule, result, current_level, "reminder"
                        )
                except Exception:
                    pass

    async def _escalate_alert(
        self,
        rule: Dict[str, Any],
        result: AlertRuleEvaluationResult,
        new_level: int,
        level_config: Dict[str, Any]
    ) -> None:
        """Escalate an alert to the next level"""
        rule_id = rule["id"]
        tenant_id = rule["tenant_id"]

        # Log escalation
        await db_service.create_alert_rule_history({
            "tenant_id": tenant_id,
            "alert_rule_id": rule_id,
            "event_type": AlertRuleHistoryEventType.ESCALATED.value,
            "evaluation_result": {
                "from_level": rule.get("current_escalation_level", 0),
                "to_level": new_level,
                "severity": level_config.get("severity", "warning")
            },
            "escalation_level": new_level
        })

        # Update rule escalation level
        await db_service.update_alert_rule(rule_id, tenant_id, {
            "current_escalation_level": new_level,
            "last_escalation_at": datetime.utcnow().isoformat()
        })

        # Send escalation notification
        await self._send_alert_notification(
            rule, result, new_level, "escalated",
            override_channels=level_config.get("channel_ids"),
            severity=level_config.get("severity", "warning")
        )

    async def _handle_alert_resolved(
        self,
        rule: Dict[str, Any],
        result: AlertRuleEvaluationResult
    ) -> None:
        """Handle when an alert resolves"""
        rule_id = rule["id"]
        tenant_id = rule["tenant_id"]

        # Log resolved event
        await db_service.create_alert_rule_history({
            "tenant_id": tenant_id,
            "alert_rule_id": rule_id,
            "event_type": AlertRuleHistoryEventType.RESOLVED.value,
            "evaluation_result": {
                "was_firing_for_violations": rule.get("consecutive_violations", 0),
                "message": result.message
            }
        })

        # Check if we should notify on resolve
        escalation_config = rule.get("escalation_config", {})
        if escalation_config.get("notify_on_resolve", True):
            await self._send_alert_notification(
                rule, result, escalation_level=0, event_type="resolved"
            )

    async def _send_alert_notification(
        self,
        rule: Dict[str, Any],
        result: AlertRuleEvaluationResult,
        escalation_level: int,
        event_type: str,
        override_channels: Optional[List[str]] = None,
        severity: str = "warning"
    ) -> None:
        """Send notification for an alert event"""
        rule_id = rule["id"]
        tenant_id = rule["tenant_id"]
        rule_name = rule.get("name", "Unknown Alert")

        # Determine channels
        channel_ids = override_channels or rule.get("channel_ids", [])
        if not channel_ids:
            return

        # Build notification metadata
        metadata = {
            "rule_id": rule_id,
            "rule_name": rule_name,
            "rule_type": rule.get("rule_type"),
            "event_type": event_type,
            "escalation_level": escalation_level,
            "severity": severity,
            "current_value": result.current_value,
            "threshold_value": result.threshold_value,
            "message": result.message,
            "details": result.details
        }

        # Map event type to notification event
        if event_type == "triggered":
            notification_event = "alert.rule_triggered"
        elif event_type == "resolved":
            notification_event = "alert.rule_resolved"
        elif event_type == "escalated":
            notification_event = "alert.escalated"
        else:
            notification_event = "alert.rule_triggered"

        # Send via notification service
        try:
            await notification_service.emit_event(
                tenant_id=tenant_id,
                event_type=notification_event,
                environment_id=rule.get("environment_id"),
                metadata=metadata
            )

            # Log notification sent
            await db_service.create_alert_rule_history({
                "tenant_id": tenant_id,
                "alert_rule_id": rule_id,
                "event_type": AlertRuleHistoryEventType.NOTIFIED.value,
                "channels_notified": channel_ids,
                "notification_success": True,
                "escalation_level": escalation_level
            })

            # Update last notification time
            await db_service.update_alert_rule(rule_id, tenant_id, {
                "last_notification_at": datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"Failed to send alert notification for rule {rule_id}: {e}")
            await db_service.create_alert_rule_history({
                "tenant_id": tenant_id,
                "alert_rule_id": rule_id,
                "event_type": AlertRuleHistoryEventType.NOTIFIED.value,
                "channels_notified": channel_ids,
                "notification_success": False,
                "evaluation_result": {"error": str(e)}
            })

    # ============================================
    # Catalog
    # ============================================

    def get_rule_type_catalog(self) -> List[AlertRuleTypeCatalogItem]:
        """Get the catalog of available rule types"""
        return ALERT_RULE_TYPE_CATALOG

    # ============================================
    # Helpers
    # ============================================

    def _rule_to_response(self, rule: Dict[str, Any]) -> AlertRuleResponse:
        """Convert database record to response model"""
        return AlertRuleResponse(
            id=rule["id"],
            tenant_id=rule["tenant_id"],
            name=rule["name"],
            description=rule.get("description"),
            rule_type=rule["rule_type"],
            threshold_config=rule.get("threshold_config", {}),
            environment_id=rule.get("environment_id"),
            channel_ids=rule.get("channel_ids", []),
            escalation_config=rule.get("escalation_config"),
            is_enabled=rule.get("is_enabled", True),
            current_escalation_level=rule.get("current_escalation_level", 0),
            last_escalation_at=rule.get("last_escalation_at"),
            is_firing=rule.get("is_firing", False),
            consecutive_violations=rule.get("consecutive_violations", 0),
            first_violation_at=rule.get("first_violation_at"),
            last_violation_at=rule.get("last_violation_at"),
            last_evaluated_at=rule.get("last_evaluated_at"),
            last_notification_at=rule.get("last_notification_at"),
            muted_until=rule.get("muted_until"),
            mute_reason=rule.get("mute_reason"),
            created_at=rule["created_at"],
            updated_at=rule["updated_at"]
        )


# Global instance
alert_rules_service = AlertRulesService()
