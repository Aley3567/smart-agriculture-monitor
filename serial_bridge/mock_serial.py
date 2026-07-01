import random
import time
import logging

logger = logging.getLogger(__name__)


class MockSerial:
    def __init__(self, port=None, baudrate=115200, **kwargs):
        self.port = port or "MOCK"
        self.baudrate = baudrate
        self.is_open = True
        self._last_time = 0
        self._interval = 2
        logger.info("MockSerial initialized on port=%s baud=%d", self.port, self.baudrate)

    def open(self):
        self.is_open = True

    def close(self):
        self.is_open = False

    def read_until(self, expected=b"\n", size=None):
        elapsed = time.time() - self._last_time
        if elapsed < self._interval:
            time.sleep(self._interval - elapsed)
        self._last_time = time.time()

        t = round(random.uniform(18, 35), 1)
        h = round(random.uniform(30, 80), 1)
        l = round(random.uniform(0, 100), 1)
        line = f"t:{t}-h:{h}-l:{l}\r\n"
        return line.encode("utf-8")

    def write(self, data):
        text = data.decode("utf-8", errors="replace").strip()
        logger.info("[MockSerial] command received: %s", text)
        return len(data)

    @property
    def in_waiting(self):
        return 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
