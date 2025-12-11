from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx

from app.services.database import db_service
from app.services.n8n_client import N8NClient
from app.schemas.notification import (
    NotificationChannelCreate,
    NotificationChannelUpdate,
    NotificationChannelResponse,
    NotificationRuleCreate,
    NotificationRuleUpdate,
    NotificationRuleResponse,
    EventCreate,
    EventResponse,
    EventCatalogItem,
    EVENT_CATALOG,
    NotificationStatus,
)


class NotificationService:
    """Service for managing notification channels, rules, and event emission"""

    # Channel operations
    async def create_channel(
        self,
        tenant_id: str,
        data: NotificationChannelCreate
    ) -> NotificationChannelResponse:
        """Create a notification channel"""
        channel_data = {
            "tenant_id": tenant_id,
            "name": data.name,
            "type": data.type.value,
            "config_json": data.config_json,
            "is_enabled": data.is_enabled
        }

        result = await db_service.create_notification_channel(channel_data)

        return NotificationChannelResponse(
            id=result["id"],
            tenant_id=result["tenant_id"],
            name=result["name"],
            type=result["type"],
            config_json=result["config_json"],
            is_enabled=result["is_enabled"],
            created_at=result["created_at"],
            updated_at=result["updated_at"]
        )

    async def update_channel(
        self,
        tenant_id: str,
        channel_id: str,
        data: NotificationChannelUpdate
    ) -> Optional[NotificationChannelResponse]:
        """Update a notification channel"""
        update_data = {}
        if data.name is not None:
            update_data["name"] = data.name
        if data.config_json is not None:
            update_data["config_json"] = data.config_json
        if data.is_enabled is not None:
            update_data["is_enabled"] = data.is_enabled

        if not update_data:
            # Nothing to update
            channel = await db_service.get_notification_channel(channel_id, tenant_id)
            if not channel:
                return None
            return self._channel_to_response(channel)

        result = await db_service.update_notification_channel(channel_id, tenant_id, update_data)
        if not result:
            return None

        return self._channel_to_response(result)

    async def delete_channel(self, tenant_id: str, channel_id: str) -> bool:
        """Delete a notification channel"""
        return await db_service.delete_notification_channel(channel_id, tenant_id)

    async def get_channels(self, tenant_id: str) -> List[NotificationChannelResponse]:
        """Get all notification channels for a tenant"""
        channels = await db_service.get_notification_channels(tenant_id)
        return [self._channel_to_response(c) for c in channels]

    async def get_channel(
        self,
        tenant_id: str,
        channel_id: str
    ) -> Optional[NotificationChannelResponse]:
        """Get a specific notification channel"""
        channel = await db_service.get_notification_channel(channel_id, tenant_id)
        if not channel:
            return None
        return self._channel_to_response(channel)

    def _channel_to_response(self, channel: Dict[str, Any]) -> NotificationChannelResponse:
        """Convert database record to response model"""
        return NotificationChannelResponse(
            id=channel["id"],
            tenant_id=channel["tenant_id"],
            name=channel["name"],
            type=channel["type"],
            config_json=channel["config_json"],
            is_enabled=channel["is_enabled"],
            created_at=channel["created_at"],
            updated_at=channel["updated_at"]
        )

    # Rule operations
    async def create_rule(
        self,
        tenant_id: str,
        data: NotificationRuleCreate
    ) -> NotificationRuleResponse:
        """Create a notification rule"""
        rule_data = {
            "tenant_id": tenant_id,
            "event_type": data.event_type,
            "channel_ids": data.channel_ids,
            "is_enabled": data.is_enabled
        }

        result = await db_service.create_notification_rule(rule_data)

        return NotificationRuleResponse(
            id=result["id"],
            tenant_id=result["tenant_id"],
            event_type=result["event_type"],
            channel_ids=result["channel_ids"],
            is_enabled=result["is_enabled"],
            created_at=result["created_at"],
            updated_at=result["updated_at"]
        )

    async def update_rule(
        self,
        tenant_id: str,
        rule_id: str,
        data: NotificationRuleUpdate
    ) -> Optional[NotificationRuleResponse]:
        """Update a notification rule"""
        update_data = {}
        if data.channel_ids is not None:
            update_data["channel_ids"] = data.channel_ids
        if data.is_enabled is not None:
            update_data["is_enabled"] = data.is_enabled

        if not update_data:
            return None

        result = await db_service.update_notification_rule(rule_id, tenant_id, update_data)
        if not result:
            return None

        return self._rule_to_response(result)

    async def delete_rule(self, tenant_id: str, rule_id: str) -> bool:
        """Delete a notification rule"""
        return await db_service.delete_notification_rule(rule_id, tenant_id)

    async def get_rules(self, tenant_id: str) -> List[NotificationRuleResponse]:
        """Get all notification rules for a tenant"""
        rules = await db_service.get_notification_rules(tenant_id)
        return [self._rule_to_response(r) for r in rules]

    async def get_rule_by_event(
        self,
        tenant_id: str,
        event_type: str
    ) -> Optional[NotificationRuleResponse]:
        """Get notification rule for a specific event type"""
        rule = await db_service.get_notification_rule_by_event(tenant_id, event_type)
        if not rule:
            return None
        return self._rule_to_response(rule)

    def _rule_to_response(self, rule: Dict[str, Any]) -> NotificationRuleResponse:
        """Convert database record to response model"""
        return NotificationRuleResponse(
            id=rule["id"],
            tenant_id=rule["tenant_id"],
            event_type=rule["event_type"],
            channel_ids=rule["channel_ids"],
            is_enabled=rule["is_enabled"],
            created_at=rule["created_at"],
            updated_at=rule["updated_at"]
        )

    # Event operations
    async def emit_event(
        self,
        tenant_id: str,
        event_type: str,
        environment_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EventResponse:
        """
        Emit an event and trigger notifications based on rules.
        """
        # Create event record
        event_data = {
            "tenant_id": tenant_id,
            "event_type": event_type,
            "environment_id": environment_id,
            "metadata_json": metadata,
            "notification_status": NotificationStatus.PENDING.value
        }

        result = await db_service.create_event(event_data)
        event_id = result["id"]

        # Look up notification rule for this event type
        rule = await db_service.get_notification_rule_by_event(tenant_id, event_type)

        channels_notified = []
        notification_status = NotificationStatus.SKIPPED

        if rule and rule.get("is_enabled") and rule.get("channel_ids"):
            # Get channels and send notifications
            channels = await db_service.get_notification_channels(tenant_id)
            channel_map = {c["id"]: c for c in channels}

            all_success = True
            for channel_id in rule["channel_ids"]:
                channel = channel_map.get(channel_id)
                if channel and channel.get("is_enabled"):
                    try:
                        success = await self.send_notification(
                            channel,
                            event_type,
                            environment_id,
                            metadata
                        )
                        if success:
                            channels_notified.append(channel_id)
                        else:
                            all_success = False
                    except Exception as e:
                        print(f"Failed to send notification to channel {channel_id}: {e}")
                        all_success = False

            if channels_notified:
                notification_status = NotificationStatus.SENT if all_success else NotificationStatus.FAILED
            else:
                notification_status = NotificationStatus.FAILED

        # Update event with notification status
        await db_service.update_event_notification_status(
            event_id,
            notification_status.value,
            channels_notified
        )

        return EventResponse(
            id=result["id"],
            tenant_id=result["tenant_id"],
            event_type=result["event_type"],
            environment_id=result.get("environment_id"),
            timestamp=result["timestamp"],
            metadata_json=result.get("metadata_json"),
            notification_status=notification_status,
            channels_notified=channels_notified
        )

    async def get_recent_events(
        self,
        tenant_id: str,
        limit: int = 50,
        event_type: Optional[str] = None
    ) -> List[EventResponse]:
        """Get recent events for a tenant"""
        events = await db_service.get_events(tenant_id, limit, event_type)
        return [
            EventResponse(
                id=e["id"],
                tenant_id=e["tenant_id"],
                event_type=e["event_type"],
                environment_id=e.get("environment_id"),
                timestamp=e["timestamp"],
                metadata_json=e.get("metadata_json"),
                notification_status=e.get("notification_status"),
                channels_notified=e.get("channels_notified")
            )
            for e in events
        ]

    def get_event_catalog(self) -> List[EventCatalogItem]:
        """Get the static event catalog"""
        return EVENT_CATALOG

    async def send_notification(
        self,
        channel: Dict[str, Any],
        event_type: str,
        environment_id: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Send a notification to an n8n workflow channel.
        The channel config_json contains: environment_id, workflow_id, webhook_path
        """
        config = channel.get("config_json", {})

        # Get the environment for this channel to get the n8n base URL
        channel_env_id = config.get("environment_id")
        webhook_path = config.get("webhook_path", "")

        if not channel_env_id or not webhook_path:
            print(f"Channel {channel.get('name')} missing environment_id or webhook_path")
            return False

        # Get environment to construct webhook URL
        # Note: We need to get the environment for the channel, not the event
        env = await db_service.get_environment(channel_env_id, channel["tenant_id"])
        if not env:
            print(f"Environment {channel_env_id} not found for channel {channel.get('name')}")
            return False

        base_url = env.get("n8n_base_url", "").rstrip("/")
        if not base_url:
            print(f"No base_url for environment {channel_env_id}")
            return False

        # Construct webhook URL
        # webhook_path should be like "/webhook/abc123" or "webhook/abc123"
        if not webhook_path.startswith("/"):
            webhook_path = "/" + webhook_path
        webhook_url = f"{base_url}{webhook_path}"

        # Build payload
        payload = {
            "event_type": event_type,
            "environment_id": environment_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
            "channel_name": channel.get("name")
        }

        # Send POST request to webhook
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    timeout=10.0
                )
                return response.status_code in [200, 201, 202, 204]
        except Exception as e:
            print(f"Failed to send notification to {webhook_url}: {e}")
            return False

    async def test_channel(
        self,
        tenant_id: str,
        channel_id: str
    ) -> Dict[str, Any]:
        """Test a notification channel by sending a test event"""
        channel = await db_service.get_notification_channel(channel_id, tenant_id)
        if not channel:
            return {"success": False, "message": "Channel not found"}

        try:
            success = await self.send_notification(
                channel,
                "system.test",
                None,
                {"message": "This is a test notification from n8n-ops"}
            )

            if success:
                return {"success": True, "message": "Test notification sent successfully"}
            else:
                return {"success": False, "message": "Failed to send test notification"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}


# Global instance
notification_service = NotificationService()
