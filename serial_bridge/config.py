import platform

DEFAULT_BAUD = 115200
DEFAULT_SERVER = "ws://localhost:8000/ws/bridge"
RECONNECT_INTERVAL = 3

SERIAL_BYTESIZE = 8
SERIAL_STOPBITS = 1
SERIAL_PARITY = "N"

_system = platform.system()
if _system == "Windows":
    DEFAULT_PORT = "COM3"
elif _system == "Darwin":
    DEFAULT_PORT = "/dev/tty.usbserial-0001"
else:
    DEFAULT_PORT = "/dev/ttyUSB0"
