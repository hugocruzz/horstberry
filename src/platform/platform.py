import platform as sys_platform
from .base import PlatformInterface
from .windows import WindowsPlatform
from .raspberry import RaspberryPlatform

def get_platform() -> PlatformInterface:
    system = sys_platform.system()
    if system == 'Windows':
        return WindowsPlatform()
    elif system == 'Linux':
        return RaspberryPlatform()
    else:
        raise NotImplementedError(f"Platform {system} not supported")

__all__ = ['get_platform', 'PlatformInterface', 'WindowsPlatform', 'RaspberryPlatform']
