import tkinter as tk
from src.views.main_window import MainWindow
from src.controllers.flow_controller import FlowController
from src.platform.platform import get_platform
def main():
    root = tk.Tk()
    root.title("Flow Controller")
    
    platform_interface = get_platform()
    settings = platform_interface.get_display_settings()
    root.geometry(f"{settings['width']}x{settings['height']}")
    
    connection_settings = platform_interface.get_connection_settings()
    flow_controller = FlowController(
        port=connection_settings['port'],
        addresses=connection_settings['addresses']
    )
    
    app = MainWindow(root, flow_controller, settings)
    root.mainloop()


if __name__ == "__main__":
    main()