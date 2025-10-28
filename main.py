import tkinter as tk
from src.views.main_window import MainWindow
from src.controllers.flow_controller import FlowController
from src.platform.platform import get_platform

def main():
    root = tk.Tk()
    root.title("Flow Controller")
    
    platform_interface = get_platform()
    settings = platform_interface.get_display_settings()
    
    # Set initial window size
    root.geometry(f"{settings['width']}x{settings['height']}+0+0")
    root.update_idletasks()
    
    # Set minimum window size
    root.minsize(800, 600)
    
    # Allow window resizing
    root.resizable(True, True)
    
    # Set DPI scaling
    root.tk.call('tk', 'scaling', settings.get('scaling', 1.0))
    
    connection_settings = platform_interface.get_connection_settings()
    
    # Initialize FlowController with default port from settings (COM13)
    default_port = connection_settings.get('port', 'COM13')
    flow_controller = FlowController(
        port=default_port,  # Use default port from settings
        addresses=None  # Don't initialize with addresses until scan
    )
    
    # Store connection settings for reference
    settings['port'] = default_port
    settings['default_addresses'] = connection_settings.get('addresses', [None, None])
    
    app = MainWindow(root, flow_controller, settings)
    root.mainloop()


if __name__ == "__main__":
    main()