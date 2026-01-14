from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List

from app.schemas.notification import (
    NotificationChannelCreate,
    NotificationChannelUpdate,
    NotificationChannelResponse,
    NotificationRuleCreate,
    NotificationRuleUpdate,
    NotificationRuleResponse,
    EventResponse,
    EventCatalogItem,
    # Alert rule schemas
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    AlertRuleMuteRequest,
    AlertRuleHistoryResponse,
    AlertRuleEvaluationResult,
    AlertRuleSummary,
    AlertRuleTypeCatalogItem,
)
from app.services.notification_service import notification_service
from app.services.alert_rules_service import alert_rules_service
from app.core.entitlements_gate import require_entitlement
from app.services.auth_service import get_current_user

router = APIRouter()


# Entitlement gates for notification/alerting features

def _tenant_id(user_info: dict) -> str:
    tenant = user_info.get("tenant")
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return tenant["id"]


# Channel endpoints
@router.get("/channels", response_model=List[NotificationChannelResponse])
async def get_notification_channels(
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """Get all notification channels for the tenant."""
    try:
        channels = await notification_service.get_channels(_tenant_id(user_info))
        return channels
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notification channels: {str(e)}"
        )


@router.post("/channels", response_model=NotificationChannelResponse)
async def create_notification_channel(
    data: NotificationChannelCreate,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """Create a new notification channel."""
    try:
        channel = await notification_service.create_channel(_tenant_id(user_info), data)
        return channel
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification channel: {str(e)}"
        )


@router.get("/channels/{channel_id}", response_model=NotificationChannelResponse)
async def get_notification_channel(
    channel_id: str,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """Get a specific notification channel."""
    channel = await notification_service.get_channel(_tenant_id(user_info), channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification channel not found"
        )
    return channel


@router.put("/channels/{channel_id}", response_model=NotificationChannelResponse)
async def update_notification_channel(
    channel_id: str,
    data: NotificationChannelUpdate,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """Update a notification channel."""
    channel = await notification_service.update_channel(_tenant_id(user_info), channel_id, data)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification channel not found"
        )
    return channel


@router.delete("/channels/{channel_id}")
async def delete_notification_channel(
    channel_id: str,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """Delete a notification channel."""
    await notification_service.delete_channel(_tenant_id(user_info), channel_id)
    return {"message": "Notification channel deleted"}


@router.post("/channels/{channel_id}/test")
async def test_notification_channel(
    channel_id: str,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """
    Test a notification channel by sending a test event.
    Returns success/failure status and message.
    """
    result = await notification_service.test_channel(_tenant_id(user_info), channel_id)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result


# Rule endpoints
@router.get("/rules", response_model=List[NotificationRuleResponse])
async def get_notification_rules(
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """Get all notification rules for the tenant."""
    try:
        rules = await notification_service.get_rules(_tenant_id(user_info))
        return rules
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notification rules: {str(e)}"
        )


@router.post("/rules", response_model=NotificationRuleResponse)
async def create_notification_rule(
    data: NotificationRuleCreate,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """Create a new notification rule."""
    try:
        rule = await notification_service.create_rule(_tenant_id(user_info), data)
        return rule
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification rule: {str(e)}"
        )


@router.get("/rules/{event_type}", response_model=NotificationRuleResponse)
async def get_notification_rule_by_event(
    event_type: str,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """Get the notification rule for a specific event type."""
    rule = await notification_service.get_rule_by_event(_tenant_id(user_info), event_type)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification rule not found for this event type"
        )
    return rule


@router.put("/rules/{rule_id}", response_model=NotificationRuleResponse)
async def update_notification_rule(
    rule_id: str,
    data: NotificationRuleUpdate,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """Update a notification rule."""
    rule = await notification_service.update_rule(_tenant_id(user_info), rule_id, data)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification rule not found"
        )
    return rule


@router.delete("/rules/{rule_id}")
async def delete_notification_rule(
    rule_id: str,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """Delete a notification rule."""
    await notification_service.delete_rule(_tenant_id(user_info), rule_id)
    return {"message": "Notification rule deleted"}


# Event endpoints
@router.get("/events", response_model=List[EventResponse])
async def get_alert_events(
    limit: int = 50,
    event_type: Optional[str] = None,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """
    Get recent alert events.

    - **limit**: Maximum number of events to return (default 50)
    - **event_type**: Filter by specific event type
    """
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be between 1 and 200"
        )

    try:
        events = await notification_service.get_recent_events(
            _tenant_id(user_info),
            limit,
            event_type
        )
        return events
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get events: {str(e)}"
        )


@router.get("/event-catalog", response_model=List[EventCatalogItem])
async def get_event_catalog(
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """
    Get the event catalog - a list of all available event types
    with their display names, descriptions, and categories.
    """
    return notification_service.get_event_catalog()


# ============================================
# Alert Rules Endpoints
# ============================================

@router.get("/alert-rules", response_model=List[AlertRuleResponse])
async def get_alert_rules(
    include_disabled: bool = False,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """
    Get all alert rules for the tenant.

    - **include_disabled**: Include disabled rules (default: false)
    """
    try:
        rules = await alert_rules_service.get_rules(
            _tenant_id(user_info),
            include_disabled=include_disabled
        )
        return rules
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert rules: {str(e)}"
        )


@router.get("/alert-rules/summary", response_model=AlertRuleSummary)
async def get_alert_rules_summary(
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """Get summary statistics for alert rules."""
    try:
        summary = await alert_rules_service.get_rules_summary(_tenant_id(user_info))
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert rules summary: {str(e)}"
        )


@router.get("/alert-rules/catalog", response_model=List[AlertRuleTypeCatalogItem])
async def get_alert_rule_type_catalog(
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """
    Get the alert rule type catalog - a list of available rule types
    with their configuration schemas.
    """
    return alert_rules_service.get_rule_type_catalog()


@router.post("/alert-rules", response_model=AlertRuleResponse)
async def create_alert_rule(
    data: AlertRuleCreate,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """Create a new alert rule."""
    try:
        rule = await alert_rules_service.create_rule(_tenant_id(user_info), data)
        return rule
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create alert rule: {str(e)}"
        )


@router.get("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: str,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """Get a specific alert rule."""
    rule = await alert_rules_service.get_rule(_tenant_id(user_info), rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )
    return rule


@router.put("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: str,
    data: AlertRuleUpdate,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """Update an alert rule."""
    rule = await alert_rules_service.update_rule(_tenant_id(user_info), rule_id, data)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )
    return rule


@router.delete("/alert-rules/{rule_id}")
async def delete_alert_rule(
    rule_id: str,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """Delete an alert rule."""
    await alert_rules_service.delete_rule(_tenant_id(user_info), rule_id)
    return {"message": "Alert rule deleted"}


@router.post("/alert-rules/{rule_id}/mute", response_model=AlertRuleResponse)
async def mute_alert_rule(
    rule_id: str,
    data: AlertRuleMuteRequest,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """
    Mute an alert rule for a specified duration.

    - **mute_duration_minutes**: Duration in minutes (1 to 43200 = 30 days)
    - **reason**: Optional reason for muting
    """
    rule = await alert_rules_service.mute_rule(
        _tenant_id(user_info),
        rule_id,
        data.mute_duration_minutes,
        data.reason
    )
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )
    return rule


@router.post("/alert-rules/{rule_id}/unmute", response_model=AlertRuleResponse)
async def unmute_alert_rule(
    rule_id: str,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """Unmute an alert rule."""
    rule = await alert_rules_service.unmute_rule(_tenant_id(user_info), rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )
    return rule


@router.get("/alert-rules/{rule_id}/history", response_model=AlertRuleHistoryResponse)
async def get_alert_rule_history(
    rule_id: str,
    limit: int = 50,
    offset: int = 0,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """
    Get history for a specific alert rule.

    - **limit**: Maximum number of entries to return (default 50)
    - **offset**: Offset for pagination (default 0)
    """
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be between 1 and 200"
        )

    try:
        history = await alert_rules_service.get_rule_history(
            _tenant_id(user_info),
            rule_id,
            limit,
            offset
        )
        return history
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert rule history: {str(e)}"
        )


@router.post("/alert-rules/{rule_id}/evaluate", response_model=AlertRuleEvaluationResult)
async def evaluate_alert_rule(
    rule_id: str,
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """
    Manually evaluate a specific alert rule.
    Returns the evaluation result without triggering notifications.
    """
    try:
        result = await alert_rules_service.evaluate_rule(_tenant_id(user_info), rule_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate alert rule: {str(e)}"
        )


@router.post("/alert-rules/evaluate-all", response_model=List[AlertRuleEvaluationResult])
async def evaluate_all_alert_rules(
    user_info: dict = Depends(get_current_user),
    _: dict = Depends(require_entitlement("observability_alerts")),
):
    """
    Evaluate all enabled alert rules for the tenant.
    This triggers notifications for rules that are in violation.
    """
    try:
        results = await alert_rules_service.evaluate_all_rules(_tenant_id(user_info))
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate alert rules: {str(e)}"
        )
