from .base import PlatformInterface
from ..configs.windows_config import DISPLAY_CONFIG, CONNECTION_CONFIG

class WindowsPlatform(PlatformInterface):
    """Windows-specific platform implementation"""
    
    def get_connection_settings(self):
        return CONNECTION_CONFIG
    
    def get_display_settings(self):
        return DISPLAY_CONFIG
    
    def setup_platform(self):
        # Windows-specific setup if needed
        pass