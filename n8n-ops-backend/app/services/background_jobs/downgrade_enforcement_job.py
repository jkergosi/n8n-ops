"""Scheduler for downgrade enforcement and over-limit detection."""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Set

from app.services.downgrade_service import downgrade_service
from app.services.downgrade_notification_service import downgrade_notification_service
from app.core.config import settings

logger = logging.getLogger(__name__)

_scheduler_running = False
_scheduler_task: Optional[asyncio.Task] = None

CHECK_INTERVAL_SECONDS = getattr(settings, "DOWNGRADE_ENFORCEMENT_INTERVAL_SECONDS", 3600)


async def _send_grace_period_warnings() -> Dict[str, Any]:
    """
    Send warning notifications for grace periods expiring at 7, 3, and 1 days.

    Tracks which warnings have been sent to avoid duplicate notifications.
    """
    warning_summary = {
        "warnings_sent": 0,
        "warnings_failed": 0,
        "by_threshold": {
            "7_days": 0,
            "3_days": 0,
            "1_day": 0,
        },
        "errors": [],
    }

    try:
        # Define warning thresholds (in days)
        warning_thresholds = [7, 3, 1]

        # Track which grace periods we've already notified to avoid duplicates
        notified_ids: Set[str] = set()

        for days_threshold in warning_thresholds:
            try:
                # Get grace periods expiring within this threshold
                expiring_grace_periods = await downgrade_service.get_expiring_grace_periods(
                    days_threshold=days_threshold
                )

                # Filter to only those expiring within a narrow window for this threshold
                # For example, for 7-day warning, only notify if between 6.5 and 7.5 days remaining
                now = datetime.now(timezone.utc)
                threshold_min = now + timedelta(days=days_threshold - 0.5)
                threshold_max = now + timedelta(days=days_threshold + 0.5)

                for grace_period in expiring_grace_periods:
                    gp_id = grace_period.get("id")

                    # Skip if already notified in this cycle
                    if gp_id in notified_ids:
                        continue

                    # Check if expiry is within our threshold window
                    expires_at_str = grace_period.get("expires_at")
                    try:
                        if isinstance(expires_at_str, str):
                            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                        else:
                            expires_at = expires_at_str

                        # Skip if outside our warning window
                        if not (threshold_min <= expires_at <= threshold_max):
                            continue

                    except Exception as e:
                        logger.warning(f"Failed to parse expiry date for grace period {gp_id}: {e}")
                        continue

                    # Send warning notification
                    tenant_id = grace_period.get("tenant_id")
                    try:
                        sent = await downgrade_notification_service.send_grace_period_warning(
                            tenant_id=tenant_id,
                            grace_period=grace_period,
                            days_remaining=days_threshold
                        )

                        if sent:
                            warning_summary["warnings_sent"] += 1
                            warning_summary["by_threshold"][f"{days_threshold}_day{'s' if days_threshold != 1 else ''}"] += 1
                            notified_ids.add(gp_id)
                            logger.info(
                                f"Sent {days_threshold}-day warning for grace period {gp_id} "
                                f"(tenant {tenant_id})"
                            )
                        else:
                            warning_summary["warnings_failed"] += 1
                            logger.warning(
                                f"Failed to send {days_threshold}-day warning for grace period {gp_id}"
                            )
                    except Exception as e:
                        warning_summary["warnings_failed"] += 1
                        warning_summary["errors"].append(str(e))
                        logger.error(
                            f"Error sending warning for grace period {gp_id}: {e}",
                            exc_info=True
                        )

            except Exception as e:
                logger.error(
                    f"Error processing {days_threshold}-day warnings: {e}",
                    exc_info=True
                )
                warning_summary["errors"].append(str(e))

    except Exception as e:
        logger.error(f"Error in warning notification cycle: {e}", exc_info=True)
        warning_summary["errors"].append(str(e))

    return warning_summary


async def _run_enforcement_cycle() -> Dict[str, Any]:
    """
    Run the complete enforcement cycle:
    1. Send warning notifications for expiring grace periods
    2. Enforce expired grace periods with expiry notifications
    3. Detect new over-limit situations across all tenants
    """
    # Send warning notifications
    warning_summary = await _send_grace_period_warnings()

    # Enforce expired grace periods with notifications
    expired_summary = await _enforce_expired_with_notifications()

    # Detect overlimit resources
    overlimit_summary = await downgrade_service.detect_overlimit_all_tenants()

    return {
        "warning_summary": warning_summary,
        "expired_summary": expired_summary,
        "overlimit_summary": overlimit_summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def _enforce_expired_with_notifications() -> Dict[str, Any]:
    """
    Enforce expired grace periods and send expiry notifications.
    """
    enforcement_summary = {
        "enforced_count": 0,
        "notifications_sent": 0,
        "notifications_failed": 0,
        "errors": [],
    }

    try:
        # Get expired grace periods
        expired_periods = await downgrade_service.get_expired_grace_periods()

        for grace_period in expired_periods:
            gp_id = grace_period.get("id")
            tenant_id = grace_period.get("tenant_id")

            try:
                # Execute the enforcement action
                action_success = await downgrade_service.execute_downgrade_action(grace_period)

                if not action_success:
                    enforcement_summary["errors"].append(gp_id)
                    logger.error(f"Failed to execute enforcement action for grace period {gp_id}")
                    continue

                # Mark as expired
                from app.core.downgrade_policy import GracePeriodStatus
                metadata = grace_period.get("metadata") or {}
                if not isinstance(metadata, dict):
                    metadata = {}

                metadata.update({
                    "enforced_at": datetime.now(timezone.utc).isoformat(),
                    "enforced_action": grace_period.get("action"),
                })

                updated = await downgrade_service._update_grace_period_status(
                    grace_period_id=gp_id,
                    status=GracePeriodStatus.EXPIRED,
                    metadata=metadata,
                )

                if updated:
                    enforcement_summary["enforced_count"] += 1
                    logger.info(f"Enforced grace period {gp_id} for tenant {tenant_id}")

                    # Send expiry notification
                    try:
                        action_description = grace_period.get("action", "enforcement action").replace("_", " ").title()
                        notification_sent = await downgrade_notification_service.send_grace_period_expired_notification(
                            tenant_id=tenant_id,
                            grace_period=grace_period,
                            action_taken=action_description
                        )

                        if notification_sent:
                            enforcement_summary["notifications_sent"] += 1
                            logger.info(f"Sent expiry notification for grace period {gp_id}")
                        else:
                            enforcement_summary["notifications_failed"] += 1
                            logger.warning(f"Failed to send expiry notification for grace period {gp_id}")

                    except Exception as e:
                        enforcement_summary["notifications_failed"] += 1
                        logger.error(f"Error sending expiry notification for {gp_id}: {e}", exc_info=True)
                else:
                    enforcement_summary["errors"].append(gp_id)
                    logger.error(f"Failed to mark grace period {gp_id} as expired")

            except Exception as e:
                enforcement_summary["errors"].append(gp_id)
                logger.error(f"Error enforcing grace period {gp_id}: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"Error in enforcement cycle: {e}", exc_info=True)
        enforcement_summary["errors"].append(str(e))

    return enforcement_summary


async def _scheduler_loop() -> None:
    global _scheduler_running
    logger.info(
        "Downgrade enforcement scheduler started (interval=%ss)",
        CHECK_INTERVAL_SECONDS,
    )

    while _scheduler_running:
        try:
            result = await _run_enforcement_cycle()
            warning = result.get("warning_summary", {})
            expired = result.get("expired_summary", {})
            overlimit = result.get("overlimit_summary", {})
            logger.info(
                "Downgrade enforcement cycle complete: "
                "warnings_sent=%s enforced=%s notifications=%s created_grace=%s errors=%s",
                warning.get("warnings_sent", 0),
                expired.get("enforced_count", 0),
                expired.get("notifications_sent", 0),
                overlimit.get("grace_periods_created", 0),
                len((warning.get("errors") or [])) +
                len((expired.get("errors") or [])) +
                len((overlimit.get("errors") or [])),
            )
        except Exception as e:
            logger.error("Error in downgrade enforcement cycle: %s", e, exc_info=True)

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)

    logger.info("Downgrade enforcement scheduler stopped")


def start_downgrade_enforcement_scheduler() -> None:
    global _scheduler_running, _scheduler_task
    if _scheduler_running:
        logger.warning("Downgrade enforcement scheduler already running")
        return

    _scheduler_running = True
    _scheduler_task = asyncio.create_task(_scheduler_loop())
    logger.info("Downgrade enforcement scheduler task created and started")


async def stop_downgrade_enforcement_scheduler() -> None:
    global _scheduler_running, _scheduler_task
    if not _scheduler_running:
        return

    _scheduler_running = False
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass

    _scheduler_task = None
    logger.info("Downgrade enforcement scheduler stopped")


async def get_downgrade_scheduler_status() -> Dict[str, Any]:
    return {
        "running": _scheduler_running,
        "interval_seconds": CHECK_INTERVAL_SECONDS,
        "task_created": _scheduler_task is not None,
    }

