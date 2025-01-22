"""Raspberry Pi specific configuration"""

DISPLAY_CONFIG = {
    'width': 800,
    'height': 480,  # RB-LCD-B10 resolution
    'font_size': 12,
    'font_family': 'Helvetica'
}

CONNECTION_CONFIG = {
    'port': '/dev/ttyUSB0',
    'addresses': [5, 8],
    'baudrate': 38400
}