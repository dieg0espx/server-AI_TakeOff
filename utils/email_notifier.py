#!/usr/bin/env python3
"""
Email Notification Service
Sends error notifications via SMTP when errors occur in the pipeline
"""

import os
import smtplib
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class EmailNotifier:
    """Handle email notifications for errors and alerts"""

    def __init__(self):
        """Initialize email notifier with SMTP configuration"""
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.notification_email = os.getenv('NOTIFICATION_EMAIL')
        self.enabled = os.getenv('EMAIL_NOTIFICATIONS_ENABLED', 'true').lower() == 'true'

        # Validate configuration
        if self.enabled and not all([self.smtp_user, self.smtp_password, self.notification_email]):
            print("⚠️  Email notifications are enabled but not fully configured")
            print("⚠️  Required: SMTP_USER, SMTP_PASSWORD, NOTIFICATION_EMAIL")
            self.enabled = False

    def send_error_notification(
        self,
        error_title: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        stack_trace: Optional[str] = None,
        upload_id: Optional[str] = None
    ) -> bool:
        """
        Send an error notification email

        Args:
            error_title: Brief error title/subject
            error_message: Main error message
            error_details: Additional error context (dict)
            stack_trace: Full stack trace if available
            upload_id: Upload ID if applicable

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[AI TakeOff Error] {error_title}"
            msg['From'] = self.smtp_user
            msg['To'] = self.notification_email

            # Build email body
            html_body = self._build_html_body(
                error_title=error_title,
                error_message=error_message,
                error_details=error_details,
                stack_trace=stack_trace,
                upload_id=upload_id
            )

            text_body = self._build_text_body(
                error_title=error_title,
                error_message=error_message,
                error_details=error_details,
                stack_trace=stack_trace,
                upload_id=upload_id
            )

            # Attach both plain text and HTML versions
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            print(f"📧 Error notification sent to {self.notification_email}")
            return True

        except Exception as e:
            print(f"❌ Failed to send error notification: {str(e)}")
            return False

    def _build_html_body(
        self,
        error_title: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]],
        stack_trace: Optional[str],
        upload_id: Optional[str]
    ) -> str:
        """Build HTML email body"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #d32f2f;
                    color: white;
                    padding: 20px;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f5f5f5;
                    padding: 20px;
                    border-radius: 0 0 5px 5px;
                }}
                .section {{
                    background-color: white;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                    border-left: 4px solid #d32f2f;
                }}
                .label {{
                    font-weight: bold;
                    color: #666;
                }}
                .code {{
                    background-color: #f5f5f5;
                    padding: 10px;
                    border-radius: 3px;
                    font-family: monospace;
                    overflow-x: auto;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }}
                .timestamp {{
                    color: #999;
                    font-size: 0.9em;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚨 AI TakeOff Error Alert</h1>
                <p class="timestamp">Timestamp: {timestamp}</p>
            </div>
            <div class="content">
                <div class="section">
                    <p class="label">Error Title:</p>
                    <h2 style="margin: 5px 0; color: #d32f2f;">{error_title}</h2>
                </div>

                <div class="section">
                    <p class="label">Error Message:</p>
                    <p>{error_message}</p>
                </div>
        """

        if upload_id:
            html += f"""
                <div class="section">
                    <p class="label">Upload ID:</p>
                    <p><code>{upload_id}</code></p>
                </div>
            """

        if error_details:
            html += """
                <div class="section">
                    <p class="label">Error Details:</p>
                    <div class="code">
            """
            for key, value in error_details.items():
                html += f"<strong>{key}:</strong> {value}<br>"
            html += """
                    </div>
                </div>
            """

        if stack_trace:
            html += f"""
                <div class="section">
                    <p class="label">Stack Trace:</p>
                    <div class="code">{stack_trace}</div>
                </div>
            """

        html += """
            </div>
        </body>
        </html>
        """

        return html

    def _build_text_body(
        self,
        error_title: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]],
        stack_trace: Optional[str],
        upload_id: Optional[str]
    ) -> str:
        """Build plain text email body"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        text = f"""
AI TakeOff Error Alert
{'=' * 60}

Timestamp: {timestamp}

ERROR TITLE:
{error_title}

ERROR MESSAGE:
{error_message}
"""

        if upload_id:
            text += f"""
UPLOAD ID:
{upload_id}
"""

        if error_details:
            text += "\nERROR DETAILS:\n"
            for key, value in error_details.items():
                text += f"  {key}: {value}\n"

        if stack_trace:
            text += f"""
STACK TRACE:
{stack_trace}
"""

        text += f"\n{'=' * 60}\n"

        return text


# Global email notifier instance
_email_notifier: Optional[EmailNotifier] = None


def get_email_notifier() -> EmailNotifier:
    """Get or create the global email notifier instance"""
    global _email_notifier
    if _email_notifier is None:
        _email_notifier = EmailNotifier()
    return _email_notifier


def notify_error(
    error_title: str,
    error_message: str,
    error_details: Optional[Dict[str, Any]] = None,
    exception: Optional[Exception] = None,
    upload_id: Optional[str] = None
) -> bool:
    """
    Convenience function to send error notification

    Args:
        error_title: Brief error title
        error_message: Main error message
        error_details: Additional context
        exception: Exception object (will extract stack trace)
        upload_id: Upload ID if applicable

    Returns:
        bool: True if notification sent successfully
    """
    notifier = get_email_notifier()

    stack_trace = None
    if exception:
        stack_trace = ''.join(traceback.format_exception(
            type(exception), exception, exception.__traceback__
        ))

    return notifier.send_error_notification(
        error_title=error_title,
        error_message=error_message,
        error_details=error_details,
        stack_trace=stack_trace,
        upload_id=upload_id
    )


if __name__ == "__main__":
    # Test the email notifier
    print("Testing email notification system...")

    success = notify_error(
        error_title="Test Error",
        error_message="This is a test error notification from the AI TakeOff system",
        error_details={
            "test_field": "test_value",
            "environment": "development"
        },
        upload_id="test_123"
    )

    if success:
        print("✅ Test email sent successfully!")
    else:
        print("❌ Failed to send test email. Check configuration.")
