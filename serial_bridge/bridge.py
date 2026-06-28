import asyncio
import argparse
import json
import logging
import sys

import serial
import websockets

from config import (
    DEFAULT_BAUD,
    DEFAULT_PORT,
    DEFAULT_SERVER,
    RECONNECT_INTERVAL,
    SERIAL_BYTESIZE,
    SERIAL_PARITY,
    SERIAL_STOPBITS,
)
from mock_serial import MockSerial

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

FIELD_MAP = {
    "t": "temp",
    "h": "humi",
    "l": "light",
    "s": "soil",
}


def parse_serial_line(line: str) -> dict | None:
    try:
        parts = line.strip().split("-")
        data = {}
        for part in parts:
            key, value = part.split(":")
            if key in FIELD_MAP:
                data[FIELD_MAP[key]] = float(value)
        if len(data) == 4:
            return data
    except (ValueError, IndexError):
        pass
    return None


def open_serial(port: str, baud: int, mock: bool):
    if mock:
        return MockSerial(port=port, baudrate=baud)
    return serial.Serial(
        port=port,
        baudrate=baud,
        bytesize=SERIAL_BYTESIZE,
        stopbits=SERIAL_STOPBITS,
        parity=SERIAL_PARITY,
        timeout=1,
    )


async def serial_to_ws(ser, ws_send_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    while True:
        try:
            raw = await loop.run_in_executor(None, ser.read_until, b"\n")
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            data = parse_serial_line(line)
            if data is None:
                logger.warning("failed to parse: %s", line)
                continue
            msg = json.dumps({"type": "sensor_data", "data": data})
            await ws_send_queue.put(msg)
            logger.info("sensor >> %s", data)
        except (serial.SerialException, OSError) as e:
            logger.error("serial read error: %s", e)
            raise


async def ws_to_serial(ser, ws_recv_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    while True:
        raw_msg = await ws_recv_queue.get()
        try:
            msg = json.loads(raw_msg)
            if msg.get("type") == "control":
                command = msg["command"]
                cmd_bytes = (command + "\r\n").encode("utf-8")
                await loop.run_in_executor(None, ser.write, cmd_bytes)
                logger.info("command >> serial: %s", command)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("bad ws message: %s (%s)", raw_msg, e)


async def websocket_sender(ws, ws_send_queue: asyncio.Queue):
    while True:
        msg = await ws_send_queue.get()
        await ws.send(msg)


async def websocket_receiver(ws, ws_recv_queue: asyncio.Queue):
    async for message in ws:
        await ws_recv_queue.put(message)


async def run_bridge(port: str, baud: int, server: str, mock: bool):
    loop = asyncio.get_event_loop()

    while True:
        ser = None
        try:
            logger.info("opening serial port %s @ %d (mock=%s)", port, baud, mock)
            ser = open_serial(port, baud, mock)
            logger.info("serial port opened")
            break
        except (serial.SerialException, OSError) as e:
            logger.error("serial open failed: %s, retrying in %ds", e, RECONNECT_INTERVAL)
            if ser:
                try:
                    ser.close()
                except Exception:
                    pass
            await asyncio.sleep(RECONNECT_INTERVAL)

    while True:
        ws = None
        try:
            logger.info("connecting to %s", server)
            ws = await websockets.connect(server)
            logger.info("websocket connected")

            ws_send_queue = asyncio.Queue()
            ws_recv_queue = asyncio.Queue()

            tasks = [
                asyncio.create_task(serial_to_ws(ser, ws_send_queue, loop)),
                asyncio.create_task(ws_to_serial(ser, ws_recv_queue, loop)),
                asyncio.create_task(websocket_sender(ws, ws_send_queue)),
                asyncio.create_task(websocket_receiver(ws, ws_recv_queue)),
            ]

            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
            for t in pending:
                t.cancel()
            for t in done:
                if t.exception():
                    raise t.exception()

        except (
            websockets.ConnectionClosed,
            websockets.InvalidURI,
            websockets.InvalidHandshake,
            ConnectionRefusedError,
            OSError,
        ) as e:
            logger.error("websocket error: %s, reconnecting in %ds", e, RECONNECT_INTERVAL)
        except serial.SerialException as e:
            logger.error("serial error: %s, reopening in %ds", e, RECONNECT_INTERVAL)
            try:
                ser.close()
            except Exception:
                pass
            while True:
                try:
                    ser = open_serial(port, baud, mock)
                    logger.info("serial port reopened")
                    break
                except (serial.SerialException, OSError) as e2:
                    logger.error("serial reopen failed: %s, retrying in %ds", e2, RECONNECT_INTERVAL)
                    await asyncio.sleep(RECONNECT_INTERVAL)
        finally:
            if ws:
                try:
                    await ws.close()
                except Exception:
                    pass

        await asyncio.sleep(RECONNECT_INTERVAL)


def main():
    parser = argparse.ArgumentParser(description="Serial-WebSocket Bridge")
    parser.add_argument("--port", default=DEFAULT_PORT, help=f"serial port (default: {DEFAULT_PORT})")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help=f"baud rate (default: {DEFAULT_BAUD})")
    parser.add_argument("--server", default=DEFAULT_SERVER, help=f"websocket server (default: {DEFAULT_SERVER})")
    parser.add_argument("--mock", action="store_true", help="use mock serial data")
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("Smart Agriculture Serial Bridge")
    logger.info("  port   : %s", args.port)
    logger.info("  baud   : %d", args.baud)
    logger.info("  server : %s", args.server)
    logger.info("  mode   : %s", "MOCK" if args.mock else "HARDWARE")
    logger.info("=" * 50)

    try:
        asyncio.run(run_bridge(args.port, args.baud, args.server, args.mock))
    except KeyboardInterrupt:
        logger.info("bridge stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
