# Email Notification System

This document describes the email notification system integrated into the AI TakeOff Server.

## Overview

The system automatically sends email notifications when errors occur during the PDF processing pipeline. Notifications include detailed error information, stack traces, and context to help diagnose issues quickly.

## Configuration

### Environment Variables

Add the following variables to your `.env` file:

```env
# Email Notification Configuration
EMAIL_NOTIFICATIONS_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=diego@ttfscaffolding.com
SMTP_PASSWORD=czbzsukklofnongn
NOTIFICATION_EMAIL=diego@ttfscaffolding.com
```

### Variable Descriptions

- **EMAIL_NOTIFICATIONS_ENABLED**: Set to `true` to enable email notifications, `false` to disable
- **SMTP_HOST**: SMTP server hostname (default: smtp.gmail.com for Gmail)
- **SMTP_PORT**: SMTP server port (default: 587 for TLS)
- **SMTP_USER**: Email address used to send notifications
- **SMTP_PASSWORD**: App-specific password for the sender email account
- **NOTIFICATION_EMAIL**: Email address that will receive error notifications

### Gmail Configuration

If using Gmail (recommended):

1. Enable 2-Factor Authentication on your Google account
2. Generate an App-Specific Password:
   - Go to Google Account Settings → Security
   - Under "Signing in to Google", select "App passwords"
   - Generate a new app password for "Mail"
   - Use this password in `SMTP_PASSWORD`

## Features

### Error Types Monitored

The system monitors and sends notifications for the following error types:

1. **PDF Download Failures**
   - Failed Google Drive downloads
   - Missing or invalid file paths
   - Network errors during download

2. **PDF to SVG Conversion Errors**
   - Convertio API failures
   - Timeout errors
   - Invalid file format issues

3. **Pipeline Processing Failures**
   - Individual step failures (Step1-Step10)
   - Processing exceptions
   - Data validation errors

4. **Unexpected System Errors**
   - Uncaught exceptions
   - System-level failures

### Email Content

Each error notification includes:

- **Error Title**: Brief description of the error
- **Error Message**: Detailed error message
- **Timestamp**: When the error occurred
- **Upload ID**: Identifier for the processing request (if available)
- **Error Details**: Additional context including:
  - Stage where error occurred
  - File paths involved
  - Exception type
  - Other relevant metadata
- **Stack Trace**: Full Python stack trace (if available)

### Email Format

Notifications are sent in both HTML and plain text formats:

- **HTML Version**: Styled with color-coded sections for easy reading
- **Plain Text Version**: Fallback for email clients that don't support HTML

## Usage

### Automatic Notifications

Notifications are sent automatically when errors occur in:

- **main.py**: All critical error points in the main processing flow
- **Processors**: Errors caught by the pipeline runner

No code changes are needed - the system is already integrated.

### Manual Notifications

You can also send custom error notifications from your code:

```python
from utils.email_notifier import notify_error

# Basic notification
notify_error(
    error_title="Custom Error",
    error_message="Something went wrong",
    upload_id="12345"
)

# Detailed notification with exception
try:
    # Your code here
    pass
except Exception as e:
    notify_error(
        error_title="Processing Failed",
        error_message="Failed to process data",
        error_details={
            "upload_id": upload_id,
            "stage": "Data Processing",
            "file_path": "/path/to/file"
        },
        exception=e,
        upload_id=upload_id
    )
```

## Testing

### Test the Email System

Run the test script to verify email notifications are working:

```bash
python3 utils/email_notifier.py
```

Expected output:
```
Testing email notification system...
📧 Error notification sent to diego@ttfscaffolding.com
✅ Test email sent successfully!
```

Check your inbox for a test error notification email.

### Disable Notifications for Testing

To temporarily disable email notifications during development:

```env
EMAIL_NOTIFICATIONS_ENABLED=false
```

## File Structure

```
server-AI_TakeOff/
├── utils/
│   └── email_notifier.py          # Email notification service
├── processors/
│   └── error_handler.py           # Error handler for processors
├── main.py                        # Main app (integrated notifications)
├── .env                           # Configuration (includes email settings)
└── EMAIL_NOTIFICATIONS.md         # This documentation
```

## Key Files

### utils/email_notifier.py

Main email notification service with:
- `EmailNotifier` class: Handles SMTP connection and email sending
- `notify_error()`: Convenience function for sending notifications
- HTML and plain text email template builders
- Automatic configuration from environment variables

### processors/error_handler.py

Helper module for processors:
- `handle_processor_error()`: Centralized error handling for processing steps
- Automatic email notification on processor errors

### main.py

Integration points:
- PDF download errors
- SVG conversion errors
- Pipeline processing errors
- Unexpected system errors

## Integration Points

The following error handlers in `main.py` include email notifications:

| Error Handler | Line Range | Error Type |
|---------------|------------|------------|
| PDF Download Failed | ~500-520 | Google Drive download failures |
| PDF Download Exception | ~527-545 | Download exceptions |
| Pipeline Failed | ~595-615 | Processing step failures |
| Pipeline Exception | ~629-648 | Pipeline execution exceptions |
| SVG Conversion Failed | ~663-681 | Convertio API failures |
| Unexpected Error | ~732-750 | Uncaught exceptions |

## Troubleshooting

### Emails Not Being Sent

1. **Check configuration**:
   ```bash
   # Verify .env file contains all required variables
   grep EMAIL_ .env
   ```

2. **Test SMTP connection**:
   ```python
   import smtplib

   server = smtplib.SMTP('smtp.gmail.com', 587)
   server.starttls()
   server.login('your-email@gmail.com', 'your-app-password')
   server.quit()
   ```

3. **Check email logs**:
   - Look for "📧 Error notification sent" messages in console
   - Look for "❌ Failed to send error notification" errors

4. **Common issues**:
   - Using regular password instead of app-specific password
   - 2FA not enabled on Gmail account
   - Incorrect SMTP host or port
   - Firewall blocking SMTP connections

### Gmail Blocking Emails

If Gmail is blocking your login attempts:

1. Enable "Less secure app access" (not recommended)
2. Use App-Specific Passwords (recommended - see Gmail Configuration above)
3. Check Google account security alerts
4. Verify the sender email has not exceeded sending limits

### Testing in Development

For development testing without sending real emails:

```python
# In utils/email_notifier.py, modify the __init__ method:
self.enabled = False  # Force disable for testing
```

Or use environment variable:
```env
EMAIL_NOTIFICATIONS_ENABLED=false
```

## Security Considerations

1. **Never commit .env file**: The `.env` file contains sensitive credentials
2. **Use App-Specific Passwords**: Don't use your main Gmail password
3. **Rotate passwords regularly**: Change app passwords periodically
4. **Limit email content**: Avoid including sensitive data in error messages
5. **Validate recipients**: Only send to authorized email addresses

## Performance Impact

- **Minimal overhead**: Email sending happens in the same thread
- **Non-blocking**: Email failures don't interrupt processing
- **No retries**: Failed email sends are logged but don't retry
- **Rate limiting**: Gmail has daily sending limits (~500 emails/day for free accounts)

## Future Enhancements

Potential improvements for the notification system:

1. **Async email sending**: Use background tasks to avoid blocking
2. **Email templates**: Customizable HTML templates
3. **Notification grouping**: Batch multiple errors into one email
4. **Severity levels**: Different notifications for warnings vs errors
5. **Multiple recipients**: Send to different teams based on error type
6. **Slack/Discord integration**: Alternative notification channels
7. **Error dashboards**: Web interface for viewing error history

## Support

For issues or questions:
- Check server logs for error details
- Review this documentation
- Test email configuration with the test script
- Verify Gmail/SMTP settings

## Version History

- **v1.0** (2025-01-04): Initial email notification system
  - Automatic error detection
  - HTML and plain text emails
  - Gmail SMTP integration
  - Configuration via environment variables
