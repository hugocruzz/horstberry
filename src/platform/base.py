from abc import ABC, abstractmethod
from typing import Dict, Any

class PlatformInterface(ABC):
    """Abstract base class for platform-specific implementations"""
    
    @abstractmethod
    def get_connection_settings(self) -> Dict[str, Any]:
        """Get platform-specific connection settings"""
        pass
    
    @abstractmethod
    def get_display_settings(self) -> Dict[str, Any]:
        """Get platform-specific display settings"""
        pass
    
    @abstractmethod
    def setup_platform(self) -> None:
        """Perform any platform-specific initialization"""
        pass