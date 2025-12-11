"""Email service for sending transactional emails."""
import smtplib
import logging
from typing import Optional, Dict, Any, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending transactional emails like invitations, confirmations, etc."""

    def __init__(self):
        # Email configuration from environment variables
        # These should be set in .env file
        self.smtp_host = getattr(settings, 'SMTP_HOST', None)
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_user = getattr(settings, 'SMTP_USER', None)
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', None)
        self.from_email = getattr(settings, 'SMTP_FROM_EMAIL', 'noreply@n8nops.com')
        self.from_name = getattr(settings, 'SMTP_FROM_NAME', 'N8N Ops')

    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return all([self.smtp_host, self.smtp_user, self.smtp_password])

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        to_name: Optional[str] = None
    ) -> bool:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional, auto-generated if not provided)
            to_name: Recipient name (optional)
        
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Email service not configured. Skipping email send.")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email

            # Generate text body if not provided
            if not text_body:
                # Simple HTML to text conversion
                import re
                text_body = re.sub(r'<[^>]+>', '', html_body)
                text_body = text_body.replace('&nbsp;', ' ')
                text_body = text_body.strip()

            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            # Send email
            use_tls = self.smtp_port == 587 or self.smtp_port == 465
            if use_tls and self.smtp_port != 465:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            elif self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)

            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.from_email, [to_email], msg.as_string())
            server.quit()

            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    async def send_team_invitation(
        self,
        to_email: str,
        to_name: Optional[str],
        organization_name: str,
        inviter_name: str,
        role: str,
        invitation_token: Optional[str] = None,
        invitation_url: Optional[str] = None
    ) -> bool:
        """
        Send team invitation email.
        
        Args:
            to_email: Invitee email address
            to_name: Invitee name (optional)
            organization_name: Name of the organization
            inviter_name: Name of the person sending the invitation
            role: Role assigned (developer, viewer, etc.)
            invitation_token: Invitation token for acceptance (optional)
            invitation_url: Full invitation URL (optional)
        
        Returns:
            True if email sent successfully, False otherwise
        """
        # Build invitation URL
        if not invitation_url and invitation_token:
            base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
            invitation_url = f"{base_url}/accept-invitation?token={invitation_token}"

        subject = f"You've been invited to join {organization_name} on N8N Ops"

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
                <h1 style="color: white; margin: 0; font-size: 24px;">N8N Ops</h1>
            </div>
            <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px;">
                <h2 style="color: #333; margin-top: 0;">You've been invited!</h2>
                <p>Hello{(' ' + to_name) if to_name else ''},</p>
                <p><strong>{inviter_name}</strong> has invited you to join <strong>{organization_name}</strong> on N8N Ops as a <strong>{role}</strong>.</p>
                
                <div style="background: #f5f5f5; padding: 20px; border-radius: 6px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Organization:</strong> {organization_name}</p>
                    <p style="margin: 5px 0;"><strong>Role:</strong> {role.capitalize()}</p>
                    <p style="margin: 5px 0;"><strong>Invited by:</strong> {inviter_name}</p>
                </div>

                {"<p>Click the button below to accept the invitation and get started:</p>" if invitation_url else "<p>Please contact your administrator to complete your account setup.</p>"}
                
                {f'<div style="text-align: center; margin: 30px 0;"><a href="{invitation_url}" style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 600;">Accept Invitation</a></div>' if invitation_url else ''}
                
                {f'<p style="color: #666; font-size: 12px; margin-top: 30px;">Or copy and paste this link into your browser:<br><a href="{invitation_url}" style="color: #667eea; word-break: break-all;">{invitation_url}</a></p>' if invitation_url else ''}
                
                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                <p style="color: #666; font-size: 12px; margin: 0;">If you didn't expect this invitation, you can safely ignore this email.</p>
            </div>
            <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                <p>© {__import__('datetime').datetime.now().year} N8N Ops. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        text_body = f"""
You've been invited to join {organization_name} on N8N Ops

Hello{(' ' + to_name) if to_name else ''},

{inviter_name} has invited you to join {organization_name} on N8N Ops as a {role}.

Organization: {organization_name}
Role: {role.capitalize()}
Invited by: {inviter_name}

{f'Accept the invitation by visiting: {invitation_url}' if invitation_url else 'Please contact your administrator to complete your account setup.'}

If you didn't expect this invitation, you can safely ignore this email.

© {__import__('datetime').datetime.now().year} N8N Ops. All rights reserved.
        """

        return await self.send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body.strip(),
            to_name=to_name
        )


# Global instance
email_service = EmailService()

