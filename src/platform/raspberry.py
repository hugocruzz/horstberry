import os
from typing import Dict, Any
from .base import PlatformInterface
from ..configs.raspberry_config import CONNECTION_CONFIG

class RaspberryPlatform(PlatformInterface):
    """Raspberry Pi specific platform implementation"""
    
    def get_connection_settings(self):
        return CONNECTION_CONFIG
    
    def get_display_settings(self) -> Dict[str, Any]:
        return {
            'width': 1024,        # Reduced from 1280
            'height': 600,        # Reduced from 800
            'font_family': 'Helvetica',
            'font_size': 10,      # Smaller font
            'scaling': 0.8,       # Scale down UI elements
            'dpi': 96            # Force DPI setting
        }
    
    def setup_platform(self):
        # Raspberry Pi specific setup
        os.environ['DISPLAY'] = ':0'  # Ensure display is set
        os.environ['GDK_SCALE'] = '1'
        os.environ['GDK_DPI_SCALE'] = '0.8'
        
        # Set up touchscreen if needed
        try:
            os.system('xinput set-prop "FT5406 memory based driver" "Coordinate Transformation Matrix" 1 0 0 0 1 0 0 0 1')
        except:
            print("Warning: Could not configure touchscreen")