import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import requests
from typing import Optional

# SVG Upload API configuration
SVG_UPLOAD_URL = "https://server-employess-ttf.vercel.app/api/ai-takeoff-upload"

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
    Upload an SVG file to the TTF SVG API

    Args:
        file_path: Path to the SVG file

    Returns:
        URL of the uploaded SVG or None if upload failed
    """
    try:
        if not os.path.exists(file_path):
            print(f"❌ SVG file not found: {file_path}")
            return None

        print(f"📤 Uploading SVG {file_path} to TTF API...")

        # Open and upload the file
        with open(file_path, 'rb') as f:
            files = {'image': (os.path.basename(file_path), f, 'image/svg+xml')}
            response = requests.post(SVG_UPLOAD_URL, files=files, timeout=60)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                url = data.get('url')
                print(f"✅ SVG uploaded successfully: {url}")
                return url
            else:
                print(f"❌ SVG upload failed: {data.get('message', 'Unknown error')}")
                return None
        else:
            print(f"❌ SVG upload failed with status {response.status_code}: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error uploading SVG to API: {str(e)}")
        return None
