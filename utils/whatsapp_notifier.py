#!/usr/bin/env python3
"""
WhatsApp Notification Service using CallMeBot
Sends notifications via WhatsApp when events occur in the pipeline
"""

import os
import requests
import traceback
from urllib.parse import quote
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class WhatsAppNotifier:
    """Handle WhatsApp notifications using CallMeBot API"""

    def __init__(self):
        """Initialize WhatsApp notifier with CallMeBot configuration"""
        self.phone_number = os.getenv('WHATSAPP_PHONE_NUMBER')
        self.api_key = os.getenv('CALLMEBOT_API_KEY')
        self.enabled = os.getenv('WHATSAPP_NOTIFICATIONS_ENABLED', 'true').lower() == 'true'
        self.api_url = "https://api.callmebot.com/whatsapp.php"

        # Validate configuration
        if self.enabled and not all([self.phone_number, self.api_key]):
            print("⚠️  WhatsApp notifications are enabled but not fully configured")
            print("⚠️  Required: WHATSAPP_PHONE_NUMBER, CALLMEBOT_API_KEY")
            self.enabled = False

    def _send_message(self, message: str) -> bool:
        """
        Send a WhatsApp message via CallMeBot API

        Args:
            message: The message to send

        Returns:
            bool: True if message sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # URL encode the message
            encoded_message = quote(message)

            # Build the API URL
            url = f"{self.api_url}?phone={self.phone_number}&text={encoded_message}&apikey={self.api_key}"

            # Send the request
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                print(f"📱 WhatsApp notification sent successfully")
                return True
            else:
                print(f"❌ Failed to send WhatsApp notification: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"❌ Failed to send WhatsApp notification: {str(e)}")
            return False

    def send_error_notification(
        self,
        error_title: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        stack_trace: Optional[str] = None,
        upload_id: Optional[str] = None
    ) -> bool:
        """
        Send an error notification via WhatsApp

        Args:
            error_title: Brief error title/subject
            error_message: Main error message
            error_details: Additional error context (dict)
            stack_trace: Full stack trace if available
            upload_id: Upload ID if applicable

        Returns:
            bool: True if message sent successfully, False otherwise
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build the message
        message = f"""🚨 *AI TakeOff Error Alert*
━━━━━━━━━━━━━━━━━━━━
⏰ {timestamp}

*Error:* {error_title}

*Message:* {error_message}
"""

        if upload_id:
            message += f"\n*Upload ID:* `{upload_id}`"

        if error_details:
            message += "\n\n*Details:*"
            for key, value in error_details.items():
                # Truncate long values for WhatsApp
                str_value = str(value)
                if len(str_value) > 100:
                    str_value = str_value[:100] + "..."
                message += f"\n• {key}: {str_value}"

        # Note: Stack traces are too long for WhatsApp, just indicate there was one
        if stack_trace:
            # Get just the last line of the stack trace (the actual error)
            last_line = stack_trace.strip().split('\n')[-1] if stack_trace else ""
            if last_line:
                message += f"\n\n*Exception:* {last_line[:200]}"

        return self._send_message(message)

    def send_success_notification(
        self,
        upload_id: str,
        results: Dict[str, Any],
        logs: Optional[str] = None,
        duration: Optional[float] = None
    ) -> bool:
        """
        Send a success notification via WhatsApp when a takeoff is created

        Args:
            upload_id: Upload ID for the takeoff
            results: Results dictionary containing detection counts and URLs
            logs: Console logs from the processing (ignored for WhatsApp - too long)
            duration: Processing duration in seconds (optional)

        Returns:
            bool: True if message sent successfully, False otherwise
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Extract data from results
        step_results = results.get('step_results', {})

        # Calculate totals
        total_detections = sum(step_results.values())

        # Build the message
        message = f"""✅ *New AI TakeOff Created*
━━━━━━━━━━━━━━━━━━━━
⏰ {timestamp}

*Upload ID:* `{upload_id}`"""

        if duration:
            message += f"\n*Duration:* {duration:.2f}s"

        message += f"""

*Detection Results:*
• Blue X Shapes: {step_results.get('step5_blue_X_shapes', 0)}
• Red Squares: {step_results.get('step6_red_squares', 0)}
• Pink Shapes: {step_results.get('step7_pink_shapes', 0)}
• Green Rectangles: {step_results.get('step8_green_rectangles', 0)}
• Orange Rectangles: {step_results.get('step9_orange_rectangles', 0)}
━━━━━━━━━━━━━━━━━━━━
*Total:* {total_detections} detections"""

        # Add tracking URL if available
        if results.get('tracking_url'):
            message += f"\n\n🔗 *Report:* {results['tracking_url']}"

        return self._send_message(message)


# Global WhatsApp notifier instance
_whatsapp_notifier: Optional[WhatsAppNotifier] = None


def get_whatsapp_notifier() -> WhatsAppNotifier:
    """Get or create the global WhatsApp notifier instance"""
    global _whatsapp_notifier
    if _whatsapp_notifier is None:
        _whatsapp_notifier = WhatsAppNotifier()
    return _whatsapp_notifier


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
    notifier = get_whatsapp_notifier()

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


def notify_success(
    upload_id: str,
    results: Dict[str, Any],
    logs: Optional[str] = None,
    duration: Optional[float] = None
) -> bool:
    """
    Convenience function to send success notification

    Args:
        upload_id: Upload ID for the takeoff
        results: Results dictionary containing detection counts and URLs
        logs: Console logs from the processing (optional, ignored for WhatsApp)
        duration: Processing duration in seconds (optional)

    Returns:
        bool: True if notification sent successfully
    """
    notifier = get_whatsapp_notifier()
    return notifier.send_success_notification(upload_id, results, logs, duration)


if __name__ == "__main__":
    # Test the WhatsApp notifier
    print("Testing WhatsApp notification system...")

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
        print("✅ Test WhatsApp message sent successfully!")
    else:
        print("❌ Failed to send test message. Check configuration.")
