#!/usr/bin/env python3
"""
Error Handler for Processors
Provides centralized error handling and email notification for processing steps
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.email_notifier import notify_error


def handle_processor_error(
    step_name: str,
    error_message: str,
    exception: Exception = None,
    additional_details: dict = None
):
    """
    Handle errors in processing steps with email notification

    Args:
        step_name: Name of the step (e.g., "Step1", "Step2")
        error_message: Description of the error
        exception: Exception object if available
        additional_details: Additional context to include in notification
    """
    error_details = {
        "step": step_name,
        "stage": "Processing Pipeline"
    }

    if additional_details:
        error_details.update(additional_details)

    # Print error to console
    print(f"❌ Error in {step_name}: {error_message}")
    if exception:
        print(f"❌ Exception: {exception}")

    # Send email notification
    notify_error(
        error_title=f"{step_name} Failed",
        error_message=error_message,
        error_details=error_details,
        exception=exception
    )
