#!/usr/bin/env python3
"""
Log Capture Utility
Captures console output during takeoff processing for email notifications
"""

import sys
from io import StringIO
from typing import Optional
from datetime import datetime


class LogCapture:
    """Context manager to capture stdout and stderr for logging"""

    def __init__(self):
        self.log_buffer = StringIO()
        self.original_stdout = None
        self.original_stderr = None
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        """Start capturing logs"""
        self.start_time = datetime.now()
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        # Create a tee that writes to both original stdout and our buffer
        sys.stdout = TeeOutput(self.original_stdout, self.log_buffer)
        sys.stderr = TeeOutput(self.original_stderr, self.log_buffer)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop capturing logs and restore original stdout/stderr"""
        self.end_time = datetime.now()
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

    def get_logs(self) -> str:
        """Get the captured logs as a string"""
        return self.log_buffer.getvalue()

    def get_duration(self) -> Optional[float]:
        """Get the duration of the captured session in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def clear(self):
        """Clear the log buffer"""
        self.log_buffer = StringIO()


class TeeOutput:
    """Output stream that writes to multiple destinations"""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()

    def isatty(self):
        # Return False to indicate this is not a terminal
        return False


class LogStorage:
    """Simple storage for logs associated with upload IDs"""

    def __init__(self):
        self._logs = {}

    def store_log(self, upload_id: str, logs: str, duration: Optional[float] = None):
        """Store logs for a specific upload ID"""
        self._logs[upload_id] = {
            'logs': logs,
            'duration': duration,
            'timestamp': datetime.now()
        }

    def get_log(self, upload_id: str) -> Optional[dict]:
        """Retrieve logs for a specific upload ID"""
        return self._logs.get(upload_id)

    def clear_log(self, upload_id: str):
        """Clear logs for a specific upload ID"""
        if upload_id in self._logs:
            del self._logs[upload_id]

    def clear_all(self):
        """Clear all stored logs"""
        self._logs.clear()


# Global log storage instance
_log_storage = LogStorage()


def get_log_storage() -> LogStorage:
    """Get the global log storage instance"""
    return _log_storage


def parse_logs_to_json(logs: str, start_time: datetime) -> list:
    """
    Parse console logs into structured JSON format with timestamps

    Args:
        logs: Raw log string captured from console
        start_time: Start time of the processing

    Returns:
        List of log entries with timestamps
    """
    log_entries = []
    lines = logs.split('\n')
    current_timestamp = start_time

    for i, line in enumerate(lines):
        if line.strip():  # Only process non-empty lines
            # Calculate relative timestamp (each line gets a small increment)
            # This gives us approximate timing for each log line
            seconds_offset = i * 0.1  # Approximate 0.1 seconds per line
            log_timestamp = start_time.timestamp() + seconds_offset

            # Determine log level based on emoji or keywords
            log_level = "info"
            if any(indicator in line for indicator in ["❌", "Error", "ERROR", "Failed", "failed"]):
                log_level = "error"
            elif any(indicator in line for indicator in ["⚠️", "Warning", "WARNING", "warn"]):
                log_level = "warning"
            elif any(indicator in line for indicator in ["✅", "Success", "SUCCESS", "completed", "Completed"]):
                log_level = "success"
            elif any(indicator in line for indicator in ["🔄", "Processing", "Running", "Starting"]):
                log_level = "processing"

            log_entries.append({
                "timestamp": datetime.fromtimestamp(log_timestamp).isoformat(),
                "level": log_level,
                "message": line.strip()
            })

    return log_entries
