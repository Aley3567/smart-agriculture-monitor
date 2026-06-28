from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Threshold, AlarmLog, ControlLog
from ws_manager import manager


async def check_and_control(
    session: AsyncSession,
    temperature: float,
    humidity: float,
    light: float,
    soil_moisture: float,
    mode: str,
):
    result = await session.execute(select(Threshold))
    thresholds = {t.param_name: t for t in result.scalars().all()}

    checks = [
        ("temperature", temperature, "pump"),
        ("humidity", humidity, "fertilizer"),
        ("light", light, "skylight"),
    ]

    for param_name, value, device in checks:
        th = thresholds.get(param_name)
        if not th:
            continue

        if value < th.min_value:
            alarm = AlarmLog(
                timestamp=datetime.utcnow(),
                param_name=param_name,
                value=value,
                threshold=th.min_value,
                action=_get_command(device, "on"),
            )
            session.add(alarm)

            await manager.broadcast_to_clients({
                "type": "alarm",
                "param": param_name,
                "value": value,
                "threshold": th.min_value,
                "action": _get_command(device, "on"),
            })

            if mode == "auto":
                command = _get_command(device, "on")
                await manager.send_to_bridge({"type": "control", "command": command})
                session.add(ControlLog(
                    timestamp=datetime.utcnow(),
                    device=device,
                    action="on",
                    source="auto",
                ))

        elif value > th.max_value:
            alarm = AlarmLog(
                timestamp=datetime.utcnow(),
                param_name=param_name,
                value=value,
                threshold=th.max_value,
                action=_get_command(device, "off"),
            )
            session.add(alarm)

            await manager.broadcast_to_clients({
                "type": "alarm",
                "param": param_name,
                "value": value,
                "threshold": th.max_value,
                "action": _get_command(device, "off"),
            })

            if mode == "auto":
                command = _get_command(device, "off")
                await manager.send_to_bridge({"type": "control", "command": command})
                session.add(ControlLog(
                    timestamp=datetime.utcnow(),
                    device=device,
                    action="off",
                    source="auto",
                ))

    soil_th = thresholds.get("soil_moisture")
    if soil_th:
        if soil_moisture < soil_th.min_value:
            session.add(AlarmLog(
                timestamp=datetime.utcnow(),
                param_name="soil_moisture",
                value=soil_moisture,
                threshold=soil_th.min_value,
                action="low",
            ))
            await manager.broadcast_to_clients({
                "type": "alarm",
                "param": "soil_moisture",
                "value": soil_moisture,
                "threshold": soil_th.min_value,
                "action": "low",
            })
        elif soil_moisture > soil_th.max_value:
            session.add(AlarmLog(
                timestamp=datetime.utcnow(),
                param_name="soil_moisture",
                value=soil_moisture,
                threshold=soil_th.max_value,
                action="high",
            ))
            await manager.broadcast_to_clients({
                "type": "alarm",
                "param": "soil_moisture",
                "value": soil_moisture,
                "threshold": soil_th.max_value,
                "action": "high",
            })

    await session.commit()


def _get_command(device: str, action: str) -> str:
    from config import DEVICE_COMMAND_MAP
    return DEVICE_COMMAND_MAP[device][action]
