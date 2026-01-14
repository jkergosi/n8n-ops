from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ChannelType(str, Enum):
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"


# Alert Rule Types
class AlertRuleType(str, Enum):
    ERROR_RATE = "error_rate"
    ERROR_TYPE = "error_type"
    WORKFLOW_FAILURE = "workflow_failure"
    CONSECUTIVE_FAILURES = "consecutive_failures"
    EXECUTION_DURATION = "execution_duration"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    PAGE = "page"


class AlertRuleHistoryEventType(str, Enum):
    EVALUATION = "evaluation"
    TRIGGERED = "triggered"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    NOTIFIED = "notified"
    MUTED = "muted"
    UNMUTED = "unmuted"


class EventType(str, Enum):
    # Promotion events
    PROMOTION_STARTED = "promotion.started"
    PROMOTION_SUCCESS = "promotion.success"
    PROMOTION_FAILURE = "promotion.failure"
    PROMOTION_BLOCKED = "promotion.blocked"
    # Sync/Drift events
    SYNC_FAILURE = "sync.failure"
    SYNC_DRIFT_DETECTED = "sync.drift_detected"
    # Environment events
    ENVIRONMENT_UNHEALTHY = "environment.unhealthy"
    ENVIRONMENT_CONNECTION_LOST = "environment.connection_lost"
    ENVIRONMENT_RECOVERED = "environment.recovered"
    # Snapshot events
    SNAPSHOT_CREATED = "snapshot.created"
    SNAPSHOT_RESTORE_SUCCESS = "snapshot.restore_success"
    SNAPSHOT_RESTORE_FAILURE = "snapshot.restore_failure"
    # Credential events
    CREDENTIAL_PLACEHOLDER_CREATED = "credential.placeholder_created"
    CREDENTIAL_MISSING = "credential.missing"
    # System events
    SYSTEM_ERROR = "system.error"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


# Channel Config Models
class SlackConfig(BaseModel):
    webhook_url: str  # Slack incoming webhook URL
    channel: Optional[str] = None  # Override channel (optional)
    username: Optional[str] = None  # Override username (optional)
    icon_emoji: Optional[str] = None  # Override icon (optional)


class EmailConfig(BaseModel):
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    from_address: str
    to_addresses: List[str]
    use_tls: bool = True


class WebhookConfig(BaseModel):
    url: str
    method: str = "POST"
    headers: Optional[Dict[str, str]] = None
    auth_type: Optional[str] = None  # "none", "basic", "bearer"
    auth_value: Optional[str] = None  # Basic auth credentials or bearer token


class NotificationChannelBase(BaseModel):
    name: str
    type: ChannelType
    config_json: Dict[str, Any]
    is_enabled: bool = True


class NotificationChannelCreate(NotificationChannelBase):
    pass


class NotificationChannelUpdate(BaseModel):
    name: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None


class NotificationChannelResponse(NotificationChannelBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime


# Rule Models
class NotificationRuleBase(BaseModel):
    event_type: str
    channel_ids: List[str]
    is_enabled: bool = True


class NotificationRuleCreate(NotificationRuleBase):
    pass


class NotificationRuleUpdate(BaseModel):
    channel_ids: Optional[List[str]] = None
    is_enabled: Optional[bool] = None


class NotificationRuleResponse(NotificationRuleBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime


# Event Models
class EventCreate(BaseModel):
    event_type: str
    environment_id: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class EventResponse(BaseModel):
    id: str
    tenant_id: str
    event_type: str
    environment_id: Optional[str] = None
    timestamp: datetime
    metadata_json: Optional[Dict[str, Any]] = None
    notification_status: Optional[NotificationStatus] = None
    channels_notified: Optional[List[str]] = None


# Event Catalog for UI
class EventCatalogItem(BaseModel):
    event_type: str
    display_name: str
    description: str
    category: str


# Static event catalog
EVENT_CATALOG: List[EventCatalogItem] = [
    # Promotion events
    EventCatalogItem(
        event_type="promotion.started",
        display_name="Promotion Started",
        description="A workflow promotion has been initiated",
        category="promotion"
    ),
    EventCatalogItem(
        event_type="promotion.success",
        display_name="Promotion Success",
        description="A workflow promotion completed successfully",
        category="promotion"
    ),
    EventCatalogItem(
        event_type="promotion.failure",
        display_name="Promotion Failed",
        description="A workflow promotion failed to complete",
        category="promotion"
    ),
    EventCatalogItem(
        event_type="promotion.blocked",
        display_name="Promotion Blocked",
        description="A workflow promotion was blocked by gates or approvals",
        category="promotion"
    ),
    # Sync/Drift events
    EventCatalogItem(
        event_type="sync.failure",
        display_name="Sync Failed",
        description="Environment synchronization failed",
        category="sync"
    ),
    EventCatalogItem(
        event_type="sync.drift_detected",
        display_name="Drift Detected",
        description="Workflow drift detected between environments",
        category="sync"
    ),
    # Environment events
    EventCatalogItem(
        event_type="environment.unhealthy",
        display_name="Environment Unhealthy",
        description="An environment health check failed",
        category="environment"
    ),
    EventCatalogItem(
        event_type="environment.connection_lost",
        display_name="Connection Lost",
        description="Connection to an n8n instance was lost",
        category="environment"
    ),
    EventCatalogItem(
        event_type="environment.recovered",
        display_name="Environment Recovered",
        description="A previously unhealthy environment has recovered",
        category="environment"
    ),
    # Snapshot events
    EventCatalogItem(
        event_type="snapshot.created",
        display_name="Snapshot Created",
        description="A new environment snapshot was created",
        category="snapshot"
    ),
    EventCatalogItem(
        event_type="snapshot.restore_success",
        display_name="Snapshot Restored",
        description="An environment was successfully restored from a snapshot",
        category="snapshot"
    ),
    EventCatalogItem(
        event_type="snapshot.restore_failure",
        display_name="Snapshot Restore Failed",
        description="Failed to restore an environment from a snapshot",
        category="snapshot"
    ),
    # Credential events
    EventCatalogItem(
        event_type="credential.placeholder_created",
        display_name="Credential Placeholder Created",
        description="A placeholder credential was created during promotion",
        category="credential"
    ),
    EventCatalogItem(
        event_type="credential.missing",
        display_name="Credential Missing",
        description="A required credential is missing in the target environment",
        category="credential"
    ),
    # System events
    EventCatalogItem(
        event_type="system.error",
        display_name="System Error",
        description="An unexpected system error occurred",
        category="system"
    ),
    # Alert rule events
    EventCatalogItem(
        event_type="alert.rule_triggered",
        display_name="Alert Rule Triggered",
        description="An alert rule threshold was exceeded",
        category="alert"
    ),
    EventCatalogItem(
        event_type="alert.rule_resolved",
        display_name="Alert Rule Resolved",
        description="An alert rule condition returned to normal",
        category="alert"
    ),
    EventCatalogItem(
        event_type="alert.escalated",
        display_name="Alert Escalated",
        description="An alert was escalated to higher severity",
        category="alert"
    ),
]


# ============================================
# Alert Rule Threshold Configuration Models
# ============================================

class ErrorRateThreshold(BaseModel):
    """Configuration for error rate threshold alerts"""
    threshold_percent: float = Field(..., ge=0, le=100, description="Error rate percentage threshold")
    time_window_minutes: int = Field(60, ge=1, le=1440, description="Time window in minutes to evaluate")
    min_executions: int = Field(10, ge=1, description="Minimum executions required before alerting")


class ErrorTypeThreshold(BaseModel):
    """Configuration for error type matching alerts"""
    error_types: List[str] = Field(..., min_length=1, description="List of error types to match")
    time_window_minutes: int = Field(60, ge=1, le=1440, description="Time window in minutes")
    min_occurrences: int = Field(1, ge=1, description="Minimum occurrences before alerting")


class WorkflowFailureThreshold(BaseModel):
    """Configuration for specific workflow failure alerts"""
    workflow_ids: Optional[List[str]] = Field(None, description="Specific n8n workflow IDs to monitor")
    canonical_ids: Optional[List[str]] = Field(None, description="Canonical workflow IDs to monitor")
    any_workflow: bool = Field(False, description="Alert on any workflow failure")


class ConsecutiveFailuresThreshold(BaseModel):
    """Configuration for consecutive failure alerts"""
    failure_count: int = Field(3, ge=1, le=100, description="Number of consecutive failures to trigger alert")
    workflow_ids: Optional[List[str]] = Field(None, description="Specific workflows to monitor (null = all)")


class ExecutionDurationThreshold(BaseModel):
    """Configuration for execution duration alerts"""
    max_duration_ms: int = Field(..., ge=1000, description="Maximum execution duration in milliseconds")
    workflow_ids: Optional[List[str]] = Field(None, description="Specific workflows to monitor (null = all)")


# ============================================
# Escalation Policy Models
# ============================================

class EscalationLevel(BaseModel):
    """Single level in an escalation policy"""
    delay_minutes: int = Field(0, ge=0, description="Minutes to wait before escalating to this level")
    channel_ids: List[str] = Field(..., min_length=1, description="Channels to notify at this level")
    severity: AlertSeverity = Field(AlertSeverity.WARNING, description="Severity level for notifications")
    message_template: Optional[str] = Field(None, description="Custom message template for this level")


class EscalationPolicy(BaseModel):
    """Complete escalation policy configuration"""
    levels: List[EscalationLevel] = Field(..., min_length=1, max_length=5, description="Escalation levels")
    auto_resolve_after_minutes: Optional[int] = Field(None, ge=1, description="Auto-resolve if condition clears")
    repeat_interval_minutes: Optional[int] = Field(None, ge=5, description="Repeat notification interval")
    notify_on_resolve: bool = Field(True, description="Send notification when alert resolves")


# ============================================
# Alert Rule CRUD Models
# ============================================

class AlertRuleBase(BaseModel):
    """Base model for alert rules"""
    name: str = Field(..., min_length=1, max_length=255, description="Rule name")
    description: Optional[str] = Field(None, max_length=1000, description="Rule description")
    rule_type: AlertRuleType = Field(..., description="Type of alert rule")
    threshold_config: Dict[str, Any] = Field(..., description="Threshold configuration (varies by rule_type)")
    environment_id: Optional[str] = Field(None, description="Environment scope (null = all environments)")
    channel_ids: List[str] = Field(default_factory=list, description="Notification channels")
    escalation_config: Optional[Dict[str, Any]] = Field(None, description="Escalation policy configuration")
    is_enabled: bool = Field(True, description="Whether the rule is active")


class AlertRuleCreate(AlertRuleBase):
    """Model for creating an alert rule"""
    pass


class AlertRuleUpdate(BaseModel):
    """Model for updating an alert rule"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    threshold_config: Optional[Dict[str, Any]] = None
    environment_id: Optional[str] = None
    channel_ids: Optional[List[str]] = None
    escalation_config: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None


class AlertRuleResponse(AlertRuleBase):
    """Response model for alert rules"""
    id: str
    tenant_id: str
    current_escalation_level: int = 0
    last_escalation_at: Optional[datetime] = None
    is_firing: bool = False
    consecutive_violations: int = 0
    first_violation_at: Optional[datetime] = None
    last_violation_at: Optional[datetime] = None
    last_evaluated_at: Optional[datetime] = None
    last_notification_at: Optional[datetime] = None
    muted_until: Optional[datetime] = None
    mute_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AlertRuleMuteRequest(BaseModel):
    """Request to mute an alert rule"""
    mute_duration_minutes: int = Field(..., ge=1, le=43200, description="Duration in minutes (max 30 days)")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for muting")


# ============================================
# Alert Rule History Models
# ============================================

class AlertRuleHistoryEntry(BaseModel):
    """Single history entry for an alert rule"""
    id: str
    tenant_id: str
    alert_rule_id: str
    event_type: AlertRuleHistoryEventType
    evaluation_result: Optional[Dict[str, Any]] = None
    escalation_level: Optional[int] = None
    channels_notified: Optional[List[str]] = None
    notification_success: Optional[bool] = None
    created_at: datetime


class AlertRuleHistoryResponse(BaseModel):
    """Paginated response for alert rule history"""
    items: List[AlertRuleHistoryEntry]
    total: int
    has_more: bool


# ============================================
# Alert Rule Evaluation Models
# ============================================

class AlertRuleEvaluationResult(BaseModel):
    """Result of evaluating an alert rule"""
    rule_id: str
    rule_name: str
    is_triggered: bool
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    message: str
    details: Optional[Dict[str, Any]] = None
    evaluated_at: datetime


class AlertRuleSummary(BaseModel):
    """Summary of all alert rules for dashboard"""
    total_rules: int
    enabled_rules: int
    firing_rules: int
    muted_rules: int
    rules_by_type: Dict[str, int]


# ============================================
# Alert Rule Catalog (for UI)
# ============================================

class AlertRuleTypeCatalogItem(BaseModel):
    """Catalog item for alert rule types"""
    rule_type: str
    display_name: str
    description: str
    config_schema: Dict[str, Any]  # JSON Schema for the threshold_config


ALERT_RULE_TYPE_CATALOG: List[AlertRuleTypeCatalogItem] = [
    AlertRuleTypeCatalogItem(
        rule_type="error_rate",
        display_name="Error Rate Threshold",
        description="Alert when the error rate exceeds a specified percentage",
        config_schema={
            "type": "object",
            "required": ["threshold_percent"],
            "properties": {
                "threshold_percent": {"type": "number", "minimum": 0, "maximum": 100, "description": "Error rate threshold (%)"},
                "time_window_minutes": {"type": "integer", "minimum": 1, "maximum": 1440, "default": 60, "description": "Time window (minutes)"},
                "min_executions": {"type": "integer", "minimum": 1, "default": 10, "description": "Minimum executions required"}
            }
        }
    ),
    AlertRuleTypeCatalogItem(
        rule_type="error_type",
        display_name="Error Type Matching",
        description="Alert when specific error types occur",
        config_schema={
            "type": "object",
            "required": ["error_types"],
            "properties": {
                "error_types": {"type": "array", "items": {"type": "string"}, "minItems": 1, "description": "Error types to match"},
                "time_window_minutes": {"type": "integer", "minimum": 1, "maximum": 1440, "default": 60, "description": "Time window (minutes)"},
                "min_occurrences": {"type": "integer", "minimum": 1, "default": 1, "description": "Minimum occurrences"}
            }
        }
    ),
    AlertRuleTypeCatalogItem(
        rule_type="workflow_failure",
        display_name="Workflow Failure",
        description="Alert when specific workflows fail",
        config_schema={
            "type": "object",
            "properties": {
                "workflow_ids": {"type": "array", "items": {"type": "string"}, "description": "n8n workflow IDs to monitor"},
                "canonical_ids": {"type": "array", "items": {"type": "string"}, "description": "Canonical workflow IDs to monitor"},
                "any_workflow": {"type": "boolean", "default": False, "description": "Alert on any workflow failure"}
            }
        }
    ),
    AlertRuleTypeCatalogItem(
        rule_type="consecutive_failures",
        display_name="Consecutive Failures",
        description="Alert after N consecutive workflow failures",
        config_schema={
            "type": "object",
            "required": ["failure_count"],
            "properties": {
                "failure_count": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Number of consecutive failures"},
                "workflow_ids": {"type": "array", "items": {"type": "string"}, "description": "Specific workflows to monitor (optional)"}
            }
        }
    ),
    AlertRuleTypeCatalogItem(
        rule_type="execution_duration",
        display_name="Execution Duration",
        description="Alert when workflow execution exceeds time limit",
        config_schema={
            "type": "object",
            "required": ["max_duration_ms"],
            "properties": {
                "max_duration_ms": {"type": "integer", "minimum": 1000, "description": "Maximum duration in milliseconds"},
                "workflow_ids": {"type": "array", "items": {"type": "string"}, "description": "Specific workflows to monitor (optional)"}
            }
        }
    ),
]
