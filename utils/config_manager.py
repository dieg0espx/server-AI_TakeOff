import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

class ConfigManager:
    """Manages application configuration and state using JSON storage"""
    
    def __init__(self, config_file: str = "utils/config.json"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                # Create default config if file doesn't exist
                default_config = {
                    "app_config": {
                        "host": "0.0.0.0",
                        "port": 5001,
                        "title": "AI-Takeoff Server",
                        "description": "AI-Takeoff API server",
                        "version": "1.0.0"
                    },
                    "current_state": {
                        "google_drive_file_id": None,
                        "last_updated": None
                    }
                }
                self._save_config(default_config)
                return default_config
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to JSON file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get_file_id(self) -> Optional[str]:
        """Get current Google Drive file ID"""
        return self.config.get('current_state', {}).get('google_drive_file_id')
    
    def set_file_id(self, file_id: str) -> None:
        """Set current Google Drive file ID"""
        if 'current_state' not in self.config:
            self.config['current_state'] = {}
        
        self.config['current_state']['google_drive_file_id'] = file_id
        self.config['current_state']['last_updated'] = datetime.now().isoformat()
        
        self._save_config(self.config)
        print(f"📝 Google Drive file ID stored: {file_id}")
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current state"""
        return self.config.get('current_state', {})
    
    def get_app_config(self) -> Dict[str, Any]:
        """Get application configuration"""
        return self.config.get('app_config', {})

# Global config manager instance
config_manager = ConfigManager()
