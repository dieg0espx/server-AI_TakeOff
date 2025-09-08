import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import cloudinary
import cloudinary.uploader
from pathlib import Path
from typing import Dict, Optional

class CloudinaryManager:
    def __init__(self):
        """Initialize Cloudinary configuration with hardcoded credentials"""
        # Hardcoded Cloudinary credentials
        self.cloud_name = "dvord9edi"
        self.api_key = "323184262698784"
        self.api_secret = "V92mnHScgdYhjeQMWI5Dw63e8Fg"
        
        if not all([self.cloud_name, self.api_key, self.api_secret]):
            raise ValueError("Missing Cloudinary credentials. Please update the hardcoded values in cloudinary_manager.py")
        
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=self.cloud_name,
            api_key=self.api_key,
            api_secret=self.api_secret
        )
        
        self.folder = "final_AI_TakeOff"
        
        print(f"✅ Cloudinary configured successfully for folder: {self.folder}")
    
    def upload_image(self, file_path: str, public_id: str) -> Optional[str]:
        """
        Upload an image to Cloudinary
        
        Args:
            file_path: Path to the image file
            public_id: Public ID for the image (will be prefixed with folder)
        
        Returns:
            URL of the uploaded image or None if upload failed
        """
        try:
            if not os.path.exists(file_path):
                
                print(f"❌ File not found: {file_path}", "error")
                return None
            
            # Create the full public ID with folder
            full_public_id = f"{self.folder}/{public_id}"
            
            
            print(f"📤 Uploading {file_path} to Cloudinary as {full_public_id}...")
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                file_path,
                public_id=full_public_id,
                folder=self.folder,
                overwrite=True
            )
            
            url = result.get('secure_url')
            if url:
                print(f"✅ Successfully uploaded to: {url}")
                return url
            else:
                print(f"❌ Upload failed - no URL returned", "error")
                return None
                
        except Exception as e:
            
            print(f"❌ Error uploading {file_path} to Cloudinary: {str(e)}", "error")
            return None
    
    def upload_processing_results(self, step_results: Dict[str, int]) -> Dict[str, str]:
        """
        Upload only PNG result images to Cloudinary
        
        Args:
            step_results: Dictionary containing step counts
            
        Returns:
            Dictionary mapping step names to Cloudinary URLs
        """
        uploaded_urls = {}
        files_dir = Path("files")
        
        # Only upload PNG result images
        png_files = {
            "step4_results": "Step4-results.png",
            "step5_results": "Step5-results.png", 
            "step6_results": "Step6-results.png",
            "step7_results": "Step7-results.png",
            "step8_results": "Step8-results.png"
        }
        
        # Upload PNG result files
        for step_name, filename in png_files.items():
            file_path = files_dir / filename
            if file_path.exists():
                url = self.upload_image(str(file_path), step_name)
                if url:
                    uploaded_urls[step_name] = url
            else:
                
                print(f"⚠️  File not found: {file_path}", "warning")
        
        
        print(f"📊 Uploaded {len(uploaded_urls)} PNG result images to Cloudinary")
        return uploaded_urls

# Global instance
cloudinary_manager = None

def get_cloudinary_manager() -> CloudinaryManager:
    """Get or create the global Cloudinary manager instance"""
    global cloudinary_manager
    if cloudinary_manager is None:
        try:
            cloudinary_manager = CloudinaryManager()
        except ValueError as e:
            
            print(f"⚠️  Cloudinary not configured: {e}", "warning")
            return None
    return cloudinary_manager
