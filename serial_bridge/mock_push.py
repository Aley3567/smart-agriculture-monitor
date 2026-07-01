"""本地验收用的 mock 数据推送器 —— 不依赖 pyserial。

当 serial_bridge 的 pyserial 装不上时,用它替代 `bridge.py --mock`:
连接后端的 /ws/bridge,按指定间隔推一条平滑变化(含偶发越界)的传感器数据,
让 Dashboard 实时曲线、报警、统计全部真实流动。

特性:禁用客户端 keepalive ping(避免 1011 ping timeout)+ 断线自动重连。

用法:
    python3 serial_bridge/mock_push.py
    python3 serial_bridge/mock_push.py --server ws://localhost:8000/ws/bridge --interval 1
"""
import argparse
import asyncio
import json
import math
import random

import websockets


async def run(server: str, interval: float):
    t = 0
    while True:
        try:
            async with websockets.connect(server, ping_interval=None) as ws:
                print(f"已连接 {server},每 {interval}s 推送一条(Ctrl+C 停止)")
                while True:
                    temp = round(26 + 6 * math.sin(t / 12) + random.uniform(-1.5, 1.5), 1)
                    humi = round(60 + 15 * math.sin(t / 18 + 1) + random.uniform(-3, 3), 1)
                    light = round(50 + 35 * math.sin(t / 20) + random.uniform(-3, 3))
                    if t % 37 == 15:
                        temp = 39.5
                    await ws.send(json.dumps({
                        "type": "sensor_data",
                        "bridge_mode": "mock",
                        "data": {"temp": temp, "humi": humi, "light": light},
                    }))
                    t += 1
                    await asyncio.sleep(interval)
        except (OSError, websockets.exceptions.WebSocketException) as e:
            print(f"连接中断({type(e).__name__}),3 秒后重连…")
            await asyncio.sleep(3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="ws://localhost:8000/ws/bridge")
    parser.add_argument("--interval", type=float, default=2.0, help="推送间隔(秒),默认 2")
    args = parser.parse_args()
    try:
        asyncio.run(run(args.server, args.interval))
    except KeyboardInterrupt:
        print("\n已停止")
