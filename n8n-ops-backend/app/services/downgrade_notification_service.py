"""
Downgrade Notification Service

Handles sending notifications for downgrade-related events including:
- Grace period warnings (7, 3, 1 days before expiry)
- Grace period expiry notifications
- Grace period cancellation notifications
- Resource enforcement actions

This service integrates with the email service to send transactional emails
to tenant administrators about their grace period status.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.services.database import db_service
from app.services.email_service import email_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class DowngradeNotificationService:
    """
    Service for managing notifications related to downgrade grace periods.

    Sends emails to tenant admins for:
    - Grace period warnings at 7, 3, and 1 days before expiry
    - Grace period expiry and enforcement actions
    - Grace period cancellations (when tenant upgrades or manually fixes issues)
    """

    def __init__(self):
        self.email_service = email_service
        self.db_service = db_service
        self.frontend_url = settings.FRONTEND_URL

    async def _get_tenant_admin_emails(self, tenant_id: str) -> List[str]:
        """
        Get all admin email addresses for a tenant.

        Args:
            tenant_id: The tenant ID

        Returns:
            List of admin email addresses
        """
        try:
            # Get tenant information
            tenant = await self.db_service.get_tenant(tenant_id)
            if not tenant:
                logger.warning(f"Tenant {tenant_id} not found")
                return []

            # Primary contact is the tenant email
            admin_emails = []
            if tenant.get("email"):
                admin_emails.append(tenant["email"])

            # TODO: Add support for multiple admin users when team member functionality is expanded
            # For now, we use the tenant's primary email address

            return admin_emails
        except Exception as e:
            logger.error(f"Failed to get admin emails for tenant {tenant_id}: {e}")
            return []

    async def send_grace_period_warning(
        self,
        tenant_id: str,
        grace_period: Dict[str, Any],
        days_remaining: int
    ) -> bool:
        """
        Send a warning notification that a grace period is expiring soon.

        Args:
            tenant_id: The tenant ID
            grace_period: Grace period record
            days_remaining: Number of days until expiry (7, 3, or 1)

        Returns:
            True if at least one email was sent successfully
        """
        try:
            admin_emails = await self._get_tenant_admin_emails(tenant_id)
            if not admin_emails:
                logger.warning(f"No admin emails found for tenant {tenant_id}")
                return False

            # Get tenant name
            tenant = await self.db_service.get_tenant(tenant_id)
            tenant_name = tenant.get("name", "Your organization") if tenant else "Your organization"

            # Format resource details
            resource_type = grace_period.get("resource_type", "resource").replace("_", " ")
            resource_id = grace_period.get("resource_id", "unknown")
            action = grace_period.get("action", "action").replace("_", " ")
            expires_at = grace_period.get("expires_at")

            # Format expiry date
            if isinstance(expires_at, datetime):
                expiry_date_str = expires_at.strftime("%B %d, %Y at %H:%M UTC")
            elif isinstance(expires_at, str):
                try:
                    expiry_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    expiry_date_str = expiry_dt.strftime("%B %d, %Y at %H:%M UTC")
                except:
                    expiry_date_str = str(expires_at)
            else:
                expiry_date_str = "unknown"

            # Build urgency messaging
            urgency_class = "warning" if days_remaining > 3 else "urgent"
            urgency_color = "#ffc107" if days_remaining > 3 else "#dc3545"

            subject = f"⚠️ Action Required: Grace Period Expiring in {days_remaining} Day{'s' if days_remaining != 1 else ''}"

            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{subject}</title>
            </head>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">WorkflowOps</h1>
                </div>
                <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px;">
                    <div style="background: {urgency_color}; color: white; padding: 15px; border-radius: 6px; margin-bottom: 20px; text-align: center;">
                        <strong>⚠️ Grace Period Expiring in {days_remaining} Day{'s' if days_remaining != 1 else ''}</strong>
                    </div>

                    <h2 style="color: #333; margin-top: 0;">Action Required for {tenant_name}</h2>

                    <p>Your grace period for a <strong>{resource_type}</strong> is expiring soon. If no action is taken, the following will occur:</p>

                    <div style="background: #f5f5f5; padding: 20px; border-radius: 6px; margin: 20px 0;">
                        <p style="margin: 0;"><strong>Resource Type:</strong> {resource_type.title()}</p>
                        <p style="margin: 5px 0;"><strong>Resource ID:</strong> {resource_id}</p>
                        <p style="margin: 5px 0;"><strong>Action on Expiry:</strong> {action.title()}</p>
                        <p style="margin: 5px 0;"><strong>Expires At:</strong> {expiry_date_str}</p>
                    </div>

                    <h3 style="color: #333;">What You Can Do</h3>
                    <ul style="line-height: 1.8;">
                        <li><strong>Upgrade your plan</strong> to increase your limits and automatically cancel this grace period</li>
                        <li><strong>Remove excess resources</strong> to bring your usage within plan limits</li>
                        <li><strong>Contact support</strong> if you need assistance or have questions</li>
                    </ul>

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{self.frontend_url}/settings/billing" style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 600; margin-right: 10px;">Upgrade Plan</a>
                        <a href="{self.frontend_url}/downgrades/grace-periods" style="background: #6c757d; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 600;">View Grace Periods</a>
                    </div>

                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                    <p style="color: #666; font-size: 12px; margin: 0;">
                        This is an automated notification from WorkflowOps. If you believe this is an error, please contact support.
                    </p>
                </div>
                <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                    <p>© {datetime.now().year} WorkflowOps. All rights reserved.</p>
                </div>
            </body>
            </html>
            """

            text_body = f"""
Grace Period Expiring in {days_remaining} Day{'s' if days_remaining != 1 else ''}

Action Required for {tenant_name}

Your grace period for a {resource_type} is expiring soon. If no action is taken, the following will occur:

Resource Type: {resource_type.title()}
Resource ID: {resource_id}
Action on Expiry: {action.title()}
Expires At: {expiry_date_str}

What You Can Do:
- Upgrade your plan to increase your limits and automatically cancel this grace period
- Remove excess resources to bring your usage within plan limits
- Contact support if you need assistance or have questions

Manage Your Account:
- Upgrade Plan: {self.frontend_url}/settings/billing
- View Grace Periods: {self.frontend_url}/downgrades/grace-periods

This is an automated notification from WorkflowOps. If you believe this is an error, please contact support.

© {datetime.now().year} WorkflowOps. All rights reserved.
            """

            # Send to all admin emails
            success_count = 0
            for email_address in admin_emails:
                try:
                    sent = await self.email_service.send_email(
                        to_email=email_address,
                        subject=subject,
                        html_body=html_body,
                        text_body=text_body.strip()
                    )
                    if sent:
                        success_count += 1
                        logger.info(f"Grace period warning sent to {email_address} for tenant {tenant_id}")
                except Exception as e:
                    logger.error(f"Failed to send warning email to {email_address}: {e}")

            return success_count > 0

        except Exception as e:
            logger.error(f"Failed to send grace period warning for tenant {tenant_id}: {e}")
            return False

    async def send_grace_period_expired_notification(
        self,
        tenant_id: str,
        grace_period: Dict[str, Any],
        action_taken: str
    ) -> bool:
        """
        Send notification that a grace period has expired and action was taken.

        Args:
            tenant_id: The tenant ID
            grace_period: Grace period record
            action_taken: Description of the action that was taken

        Returns:
            True if at least one email was sent successfully
        """
        try:
            admin_emails = await self._get_tenant_admin_emails(tenant_id)
            if not admin_emails:
                logger.warning(f"No admin emails found for tenant {tenant_id}")
                return False

            # Get tenant name
            tenant = await self.db_service.get_tenant(tenant_id)
            tenant_name = tenant.get("name", "Your organization") if tenant else "Your organization"

            # Format resource details
            resource_type = grace_period.get("resource_type", "resource").replace("_", " ")
            resource_id = grace_period.get("resource_id", "unknown")
            action = grace_period.get("action", "action").replace("_", " ")

            subject = f"🔒 Grace Period Expired: Action Taken on {resource_type.title()}"

            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{subject}</title>
            </head>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">WorkflowOps</h1>
                </div>
                <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px;">
                    <div style="background: #dc3545; color: white; padding: 15px; border-radius: 6px; margin-bottom: 20px; text-align: center;">
                        <strong>🔒 Grace Period Expired - Action Taken</strong>
                    </div>

                    <h2 style="color: #333; margin-top: 0;">Grace Period Expired for {tenant_name}</h2>

                    <p>The grace period for your <strong>{resource_type}</strong> has expired. The following action has been taken:</p>

                    <div style="background: #f5f5f5; padding: 20px; border-radius: 6px; margin: 20px 0;">
                        <p style="margin: 0;"><strong>Resource Type:</strong> {resource_type.title()}</p>
                        <p style="margin: 5px 0;"><strong>Resource ID:</strong> {resource_id}</p>
                        <p style="margin: 5px 0;"><strong>Action Taken:</strong> {action_taken}</p>
                        <p style="margin: 5px 0;"><strong>Expired At:</strong> {datetime.now().strftime("%B %d, %Y at %H:%M UTC")}</p>
                    </div>

                    <h3 style="color: #333;">Next Steps</h3>
                    <p>To restore full functionality:</p>
                    <ul style="line-height: 1.8;">
                        <li><strong>Upgrade your plan</strong> to increase your limits and regain access to affected resources</li>
                        <li><strong>Review your usage</strong> and remove excess resources to comply with your current plan limits</li>
                        <li><strong>Contact support</strong> if you need assistance or have questions about this action</li>
                    </ul>

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{self.frontend_url}/settings/billing" style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 600; margin-right: 10px;">Upgrade Plan</a>
                        <a href="{self.frontend_url}/downgrades/grace-periods" style="background: #6c757d; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 600;">View Grace Periods</a>
                    </div>

                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                    <p style="color: #666; font-size: 12px; margin: 0;">
                        This is an automated notification from WorkflowOps. If you believe this is an error, please contact support immediately.
                    </p>
                </div>
                <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                    <p>© {datetime.now().year} WorkflowOps. All rights reserved.</p>
                </div>
            </body>
            </html>
            """

            text_body = f"""
Grace Period Expired - Action Taken

Grace Period Expired for {tenant_name}

The grace period for your {resource_type} has expired. The following action has been taken:

Resource Type: {resource_type.title()}
Resource ID: {resource_id}
Action Taken: {action_taken}
Expired At: {datetime.now().strftime("%B %d, %Y at %H:%M UTC")}

Next Steps:

To restore full functionality:
- Upgrade your plan to increase your limits and regain access to affected resources
- Review your usage and remove excess resources to comply with your current plan limits
- Contact support if you need assistance or have questions about this action

Manage Your Account:
- Upgrade Plan: {self.frontend_url}/settings/billing
- View Grace Periods: {self.frontend_url}/downgrades/grace-periods

This is an automated notification from WorkflowOps. If you believe this is an error, please contact support immediately.

© {datetime.now().year} WorkflowOps. All rights reserved.
            """

            # Send to all admin emails
            success_count = 0
            for email_address in admin_emails:
                try:
                    sent = await self.email_service.send_email(
                        to_email=email_address,
                        subject=subject,
                        html_body=html_body,
                        text_body=text_body.strip()
                    )
                    if sent:
                        success_count += 1
                        logger.info(f"Grace period expiry notification sent to {email_address} for tenant {tenant_id}")
                except Exception as e:
                    logger.error(f"Failed to send expiry email to {email_address}: {e}")

            return success_count > 0

        except Exception as e:
            logger.error(f"Failed to send grace period expiry notification for tenant {tenant_id}: {e}")
            return False

    async def send_grace_period_cancelled_notification(
        self,
        tenant_id: str,
        grace_period: Dict[str, Any],
        cancellation_reason: str
    ) -> bool:
        """
        Send notification that a grace period has been cancelled.

        This is sent when the user upgrades their plan or manually fixes
        the over-limit situation, automatically cancelling the grace period.

        Args:
            tenant_id: The tenant ID
            grace_period: Grace period record
            cancellation_reason: Reason for cancellation (e.g., "Plan upgraded", "Resource removed")

        Returns:
            True if at least one email was sent successfully
        """
        try:
            admin_emails = await self._get_tenant_admin_emails(tenant_id)
            if not admin_emails:
                logger.warning(f"No admin emails found for tenant {tenant_id}")
                return False

            # Get tenant name
            tenant = await self.db_service.get_tenant(tenant_id)
            tenant_name = tenant.get("name", "Your organization") if tenant else "Your organization"

            # Format resource details
            resource_type = grace_period.get("resource_type", "resource").replace("_", " ")
            resource_id = grace_period.get("resource_id", "unknown")

            subject = f"✅ Grace Period Cancelled for {resource_type.title()}"

            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{subject}</title>
            </head>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">WorkflowOps</h1>
                </div>
                <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px;">
                    <div style="background: #28a745; color: white; padding: 15px; border-radius: 6px; margin-bottom: 20px; text-align: center;">
                        <strong>✅ Grace Period Cancelled</strong>
                    </div>

                    <h2 style="color: #333; margin-top: 0;">Good News for {tenant_name}!</h2>

                    <p>The grace period for your <strong>{resource_type}</strong> has been automatically cancelled. No enforcement action will be taken.</p>

                    <div style="background: #f5f5f5; padding: 20px; border-radius: 6px; margin: 20px 0;">
                        <p style="margin: 0;"><strong>Resource Type:</strong> {resource_type.title()}</p>
                        <p style="margin: 5px 0;"><strong>Resource ID:</strong> {resource_id}</p>
                        <p style="margin: 5px 0;"><strong>Reason:</strong> {cancellation_reason}</p>
                        <p style="margin: 5px 0;"><strong>Cancelled At:</strong> {datetime.now().strftime("%B %d, %Y at %H:%M UTC")}</p>
                    </div>

                    <p>Your resource is now fully compliant with your plan limits and will continue to operate normally.</p>

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{self.frontend_url}/downgrades/grace-periods" style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 600;">View Grace Periods</a>
                    </div>

                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                    <p style="color: #666; font-size: 12px; margin: 0;">
                        This is an automated notification from WorkflowOps.
                    </p>
                </div>
                <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                    <p>© {datetime.now().year} WorkflowOps. All rights reserved.</p>
                </div>
            </body>
            </html>
            """

            text_body = f"""
Grace Period Cancelled

Good News for {tenant_name}!

The grace period for your {resource_type} has been automatically cancelled. No enforcement action will be taken.

Resource Type: {resource_type.title()}
Resource ID: {resource_id}
Reason: {cancellation_reason}
Cancelled At: {datetime.now().strftime("%B %d, %Y at %H:%M UTC")}

Your resource is now fully compliant with your plan limits and will continue to operate normally.

View Grace Periods: {self.frontend_url}/downgrades/grace-periods

This is an automated notification from WorkflowOps.

© {datetime.now().year} WorkflowOps. All rights reserved.
            """

            # Send to all admin emails
            success_count = 0
            for email_address in admin_emails:
                try:
                    sent = await self.email_service.send_email(
                        to_email=email_address,
                        subject=subject,
                        html_body=html_body,
                        text_body=text_body.strip()
                    )
                    if sent:
                        success_count += 1
                        logger.info(f"Grace period cancellation notification sent to {email_address} for tenant {tenant_id}")
                except Exception as e:
                    logger.error(f"Failed to send cancellation email to {email_address}: {e}")

            return success_count > 0

        except Exception as e:
            logger.error(f"Failed to send grace period cancellation notification for tenant {tenant_id}: {e}")
            return False

    async def send_bulk_grace_period_summary(
        self,
        tenant_id: str,
        grace_periods: List[Dict[str, Any]]
    ) -> bool:
        """
        Send a summary notification about multiple active grace periods.

        Useful for sending a consolidated notification when multiple resources
        are affected by a downgrade.

        Args:
            tenant_id: The tenant ID
            grace_periods: List of grace period records

        Returns:
            True if at least one email was sent successfully
        """
        try:
            if not grace_periods:
                return False

            admin_emails = await self._get_tenant_admin_emails(tenant_id)
            if not admin_emails:
                logger.warning(f"No admin emails found for tenant {tenant_id}")
                return False

            # Get tenant name
            tenant = await self.db_service.get_tenant(tenant_id)
            tenant_name = tenant.get("name", "Your organization") if tenant else "Your organization"

            # Count by resource type
            by_type: Dict[str, int] = {}
            for gp in grace_periods:
                rt = gp.get("resource_type", "unknown")
                by_type[rt] = by_type.get(rt, 0) + 1

            subject = f"📊 Grace Period Summary: {len(grace_periods)} Active Grace Period{'s' if len(grace_periods) != 1 else ''}"

            # Build grace period list HTML
            gp_list_html = ""
            for gp in grace_periods[:10]:  # Limit to first 10
                resource_type = gp.get("resource_type", "resource").replace("_", " ")
                resource_id = gp.get("resource_id", "unknown")
                expires_at = gp.get("expires_at")

                # Calculate days remaining
                try:
                    if isinstance(expires_at, str):
                        expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    else:
                        expires_dt = expires_at
                    days_remaining = (expires_dt - datetime.now(expires_dt.tzinfo)).days
                    expiry_str = f"{days_remaining} day{'s' if days_remaining != 1 else ''} remaining"
                except:
                    expiry_str = "Unknown expiry"

                gp_list_html += f"""
                <div style="border-left: 3px solid #667eea; padding-left: 15px; margin-bottom: 15px;">
                    <p style="margin: 5px 0;"><strong>{resource_type.title()}</strong> - {resource_id}</p>
                    <p style="margin: 5px 0; color: #666; font-size: 14px;">{expiry_str}</p>
                </div>
                """

            if len(grace_periods) > 10:
                gp_list_html += f"<p style='color: #666; font-style: italic;'>...and {len(grace_periods) - 10} more</p>"

            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{subject}</title>
            </head>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">WorkflowOps</h1>
                </div>
                <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px;">
                    <h2 style="color: #333; margin-top: 0;">Grace Period Summary for {tenant_name}</h2>

                    <p>You currently have <strong>{len(grace_periods)}</strong> active grace period{'s' if len(grace_periods) != 1 else ''}:</p>

                    <div style="background: #f5f5f5; padding: 20px; border-radius: 6px; margin: 20px 0;">
                        {''.join([f"<p style='margin: 5px 0;'><strong>{rt.replace('_', ' ').title()}:</strong> {count}</p>" for rt, count in by_type.items()])}
                    </div>

                    <h3 style="color: #333;">Active Grace Periods</h3>
                    {gp_list_html}

                    <h3 style="color: #333;">What You Can Do</h3>
                    <ul style="line-height: 1.8;">
                        <li><strong>Upgrade your plan</strong> to increase your limits and automatically cancel all grace periods</li>
                        <li><strong>Remove excess resources</strong> to bring your usage within plan limits</li>
                        <li><strong>Review each grace period</strong> to prioritize which resources to keep</li>
                    </ul>

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{self.frontend_url}/settings/billing" style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 600; margin-right: 10px;">Upgrade Plan</a>
                        <a href="{self.frontend_url}/downgrades/grace-periods" style="background: #6c757d; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 600;">View All Grace Periods</a>
                    </div>

                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                    <p style="color: #666; font-size: 12px; margin: 0;">
                        This is an automated notification from WorkflowOps.
                    </p>
                </div>
                <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                    <p>© {datetime.now().year} WorkflowOps. All rights reserved.</p>
                </div>
            </body>
            </html>
            """

            # Send to all admin emails
            success_count = 0
            for email_address in admin_emails:
                try:
                    sent = await self.email_service.send_email(
                        to_email=email_address,
                        subject=subject,
                        html_body=html_body
                    )
                    if sent:
                        success_count += 1
                        logger.info(f"Grace period summary sent to {email_address} for tenant {tenant_id}")
                except Exception as e:
                    logger.error(f"Failed to send summary email to {email_address}: {e}")

            return success_count > 0

        except Exception as e:
            logger.error(f"Failed to send grace period summary for tenant {tenant_id}: {e}")
            return False


# Global instance
downgrade_notification_service = DowngradeNotificationService()
