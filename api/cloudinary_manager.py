import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import requests
import ftplib
from datetime import datetime
from typing import Optional

# FTP storage for uploaded SVGs (bypasses the Vercel 4.5MB function-body limit).
# The previous Vercel proxy at server-employess-ttf.vercel.app/api/ai-takeoff-upload
# did the same FTP upload internally; we now do it directly from Python.
FTP_HOST = os.getenv("TTF_FTP_HOST", "151.106.98.244")
FTP_USER = os.getenv("TTF_FTP_USER", "u969084943.ftpImages")
FTP_PASSWORD = os.getenv("TTF_FTP_PASSWORD", "ftpImages2020?")
FTP_REMOTE_DIR = "/AI-takeOff"
PUBLIC_URL_BASE = "https://ftp-images.ttfconstruction.com/AI-takeOff"

# Database update API configuration
UPDATE_SVG_API_URL = "https://ttfconstruction.com/ai-takeoff-results/update_svg.php"


def update_svg_in_database(tracking_url: str, svg_url: str) -> bool:
    """
    Update the SVG URL in the database for a given tracking URL

    Args:
        tracking_url: The tracking URL of the record to update
        svg_url: The URL of the uploaded SVG file

    Returns:
        True if update was successful, False otherwise
    """
    try:
        print(f"📝 Updating database with SVG URL for tracking: {tracking_url}")

        response = requests.post(
            UPDATE_SVG_API_URL,
            json={
                'tracking_url': tracking_url,
                'svg_url': svg_url
            },
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Database updated with SVG URL successfully")
                return True
            else:
                print(f"❌ Database update failed: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ Database update failed with status {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error updating SVG in database: {str(e)}")
        return False


def upload_svg_to_api(file_path: str) -> Optional[str]:
    """
    Upload an SVG file directly to the TTF FTP server, returning the public URL.

    Replaces the previous HTTP upload to a Vercel proxy, which had a 4.5MB
    function-body limit. FTP has no such limit.
    """
    if not os.path.exists(file_path):
        print(f"❌ SVG file not found: {file_path}")
        return None

    timestamp = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
    remote_filename = f"{timestamp}.svg"
    remote_path = f"{FTP_REMOTE_DIR}/{remote_filename}"
    size = os.path.getsize(file_path)
    print(f"📤 Uploading {file_path} ({size/1024/1024:.2f} MB) to FTP as {remote_path}...")

    try:
        with ftplib.FTP(FTP_HOST, timeout=120) as ftp:
            ftp.login(user=FTP_USER, passwd=FTP_PASSWORD)
            try:
                ftp.cwd(FTP_REMOTE_DIR)
            except ftplib.error_perm:
                ftp.mkd(FTP_REMOTE_DIR)
                ftp.cwd(FTP_REMOTE_DIR)
            with open(file_path, 'rb') as f:
                ftp.storbinary(f"STOR {remote_filename}", f)

        url = f"{PUBLIC_URL_BASE}/{remote_filename}"
        print(f"✅ SVG uploaded successfully: {url}")
        return url
    except Exception as e:
        print(f"❌ FTP upload failed: {e}")
        return None
