import asyncio
import argparse
import json
import logging
import sys

import websockets

try:
    import serial
except ModuleNotFoundError:
    serial = None

try:
    from .config import (
        DEFAULT_BAUD,
        DEFAULT_PORT,
        DEFAULT_SERVER,
        RECONNECT_INTERVAL,
        SERIAL_BYTESIZE,
        SERIAL_PARITY,
        SERIAL_STOPBITS,
    )
    from .mock_serial import MockSerial
except ImportError:
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

SerialException = getattr(serial, "SerialException", OSError)

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
    payload = parse_serial_payload(line, default_board_id="A", default_board_name="greenhouse-a")
    return payload["data"] if payload else None


def parse_serial_payload(line: str, default_board_id: str, default_board_name: str) -> dict | None:
    try:
        parts = line.strip().split("-")
        data = {}
        board_id = default_board_id
        for part in parts:
            key, value = part.split(":", 1)
            if key == "id":
                board_id = value.strip() or default_board_id
            elif key in FIELD_MAP:
                data[FIELD_MAP[key]] = float(value)
        if len(data) >= 3:
            board_name = default_board_name
            if board_id != default_board_id:
                board_name = f"greenhouse-{board_id.lower()}"
            return {
                "board_id": board_id,
                "board_name": board_name,
                "data": data,
            }
    except (ValueError, IndexError):
        pass
    return None


def build_sensor_message(data: dict, board_id: str, board_name: str, bridge_mode: str = "hardware") -> dict:
    return {
        "type": "sensor_data",
        "board_id": board_id,
        "board_name": board_name,
        "bridge_mode": bridge_mode,
        "data": data,
    }


def build_debug_message(board_id: str, event: str, level: str = "info", **details) -> dict:
    return {
        "type": "bridge_debug",
        "board_id": board_id,
        "event": event,
        "level": level,
        "details": details,
    }


def should_apply_control(msg: dict, board_id: str) -> bool:
    target = msg.get("board_id")
    return msg.get("type") == "control" and (not target or target == board_id)


def open_serial(port: str, baud: int, mock: bool):
    if mock:
        return MockSerial(port=port, baudrate=baud)
    if serial is None:
        raise RuntimeError("pyserial is required for real serial mode")
    return serial.Serial(
        port=port,
        baudrate=baud,
        bytesize=SERIAL_BYTESIZE,
        stopbits=SERIAL_STOPBITS,
        parity=SERIAL_PARITY,
        timeout=1,
    )


async def serial_to_ws(
    ser,
    ws_send_queue: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
    board_id: str,
    board_name: str,
    bridge_mode: str,
):
    while True:
        try:
            raw = await loop.run_in_executor(None, ser.read_until, b"\n")
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            await ws_send_queue.put(json.dumps(build_debug_message(
                board_id,
                "serial_raw_line",
                raw_line=line,
            )))
            payload = parse_serial_payload(line, board_id, board_name)
            if payload is None:
                logger.warning("failed to parse: %s", line)
                await ws_send_queue.put(json.dumps(build_debug_message(
                    board_id,
                    "serial_parse_failed",
                    level="warn",
                    raw_line=line,
                )))
                continue
            data = payload["data"]
            msg = json.dumps(build_sensor_message(data, payload["board_id"], payload["board_name"], bridge_mode))
            await ws_send_queue.put(msg)
            await ws_send_queue.put(json.dumps(build_debug_message(
                payload["board_id"],
                "sensor_parsed",
                data=data,
            )))
            logger.info("sensor >> board=%s %s", payload["board_id"], data)
        except (SerialException, OSError) as e:
            logger.error("serial read error: %s", e)
            raise


async def ws_to_serial(
    ser,
    ws_recv_queue: asyncio.Queue,
    ws_send_queue: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
    board_id: str,
):
    while True:
        raw_msg = await ws_recv_queue.get()
        try:
            msg = json.loads(raw_msg)
            if should_apply_control(msg, board_id):
                command = msg["command"]
                await ws_send_queue.put(json.dumps(build_debug_message(
                    board_id,
                    "control_received",
                    command=command,
                    target_board_id=msg.get("board_id"),
                )))
                cmd_bytes = (command + "\r\n").encode("utf-8")
                await loop.run_in_executor(None, ser.write, cmd_bytes)
                await ws_send_queue.put(json.dumps(build_debug_message(
                    board_id,
                    "control_written_serial",
                    command=command,
                )))
                logger.info("command >> serial: %s", command)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("bad ws message: %s (%s)", raw_msg, e)
            await ws_send_queue.put(json.dumps(build_debug_message(
                board_id,
                "ws_message_invalid",
                level="warn",
                raw_message=raw_msg,
                error=str(e),
            )))


async def websocket_sender(ws, ws_send_queue: asyncio.Queue):
    while True:
        msg = await ws_send_queue.get()
        await ws.send(msg)


async def websocket_receiver(ws, ws_recv_queue: asyncio.Queue):
    async for message in ws:
        await ws_recv_queue.put(message)


async def run_bridge(port: str, baud: int, server: str, mock: bool, board_id: str, board_name: str):
    loop = asyncio.get_event_loop()
    bridge_mode = "mock" if mock else "hardware"

    while True:
        ser = None
        try:
            logger.info("opening serial port %s @ %d (mock=%s)", port, baud, mock)
            ser = open_serial(port, baud, mock)
            logger.info("serial port opened")
            break
        except (SerialException, OSError, RuntimeError) as e:
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
            await ws.send(json.dumps({
                "type": "bridge_hello",
                "board_id": board_id,
                "board_name": board_name,
                "bridge_mode": bridge_mode,
            }))

            ws_send_queue = asyncio.Queue()
            ws_recv_queue = asyncio.Queue()
            await ws_send_queue.put(json.dumps(build_debug_message(
                board_id,
                "bridge_connected",
                port=port,
                baud=baud,
                mock=mock,
                server=server,
            )))

            tasks = [
                asyncio.create_task(serial_to_ws(ser, ws_send_queue, loop, board_id, board_name, bridge_mode)),
                asyncio.create_task(ws_to_serial(ser, ws_recv_queue, ws_send_queue, loop, board_id)),
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
        except SerialException as e:
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
                except (SerialException, OSError, RuntimeError) as e2:
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
    parser.add_argument("--board-id", default="A", help="board id injected into websocket messages")
    parser.add_argument("--board-name", default="greenhouse-a", help="human-readable board name")
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("Smart Agriculture Serial Bridge")
    logger.info("  port   : %s", args.port)
    logger.info("  baud   : %d", args.baud)
    logger.info("  server : %s", args.server)
    logger.info("  mode   : %s", "MOCK" if args.mock else "HARDWARE")
    logger.info("  board  : %s (%s)", args.board_id, args.board_name)
    logger.info("=" * 50)

    try:
        asyncio.run(run_bridge(args.port, args.baud, args.server, args.mock, args.board_id, args.board_name))
    except KeyboardInterrupt:
        logger.info("bridge stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
