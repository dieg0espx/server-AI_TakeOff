#!/usr/bin/env python3
"""
Test script for error notification email
Simulates a pipeline error with sample error details
"""

from utils.email_notifier import notify_error
from datetime import datetime

# Simulate error details
test_upload_id = f"test_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Sample error information
error_title = "Pipeline Failed at Step 7"
error_message = """
Error processing pink frames detection.

Technical Details:
- Failed to read input SVG file: files/Step6.svg
- File exists but appears to be corrupted
- Size: 0 bytes (expected: >100KB)
- Last modified: 2025-11-18 15:30:45

Possible causes:
1. Previous step (Step 6) did not complete successfully
2. Disk space issue preventing file write
3. File permissions issue
4. Process was interrupted during Step 6 execution

Recommended actions:
- Check server logs for Step 6 completion
- Verify disk space availability
- Review file permissions on files/ directory
- Check if process was killed or timed out
"""

error_details = {
    "upload_id": test_upload_id,
    "failed_step": "Step7",
    "stage": "AI Processing Pipeline - Pink Frame Detection",
    "pdf_path": "files/original.pdf",
    "svg_path": "files/Step6.svg",
    "error_type": "FileReadError",
    "timestamp": datetime.now().isoformat()
}

print("=" * 60)
print("Testing Error Notification Email")
print("=" * 60)
print(f"\nUpload ID: {test_upload_id}")
print(f"Error Title: {error_title}")
print(f"\nError Message:")
print(error_message)
print(f"\nError Details:")
for key, value in error_details.items():
    print(f"  {key}: {value}")
print(f"\nSending error notification email...")
print("=" * 60)

# Send the error notification
success = notify_error(
    error_title=error_title,
    error_message=error_message,
    error_details=error_details,
    upload_id=test_upload_id
)

if success:
    print("\n✅ Error notification email sent!")
    print(f"Check your inbox for: [AI TakeOff Error] {error_title}")
else:
    print("\n❌ Failed to send error notification email.")
    print("Please check your email configuration in .env file")
