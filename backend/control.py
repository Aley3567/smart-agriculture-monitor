from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import PARAM_DEVICE_MAP, DEVICE_COMMAND_MAP
from models import Threshold, AlarmLog, ControlLog
from ws_manager import manager


@dataclass
class ThresholdDecision:
    param_name: str
    value: float
    threshold: float
    action: str
    device: str | None
    direction: str | None


def evaluate_thresholds(values: dict, thresholds: dict) -> list[ThresholdDecision]:
    decisions = []
    for param_name, value in values.items():
        th = thresholds.get(param_name)
        if not th:
            continue
        device = PARAM_DEVICE_MAP.get(param_name)

        if value < th.min_value:
            action = f"{device}_on" if device else f"{param_name}_low"
            direction = "on" if device else None
            decisions.append(ThresholdDecision(
                param_name=param_name, value=value, threshold=th.min_value,
                action=action, device=device, direction=direction,
            ))
        elif value > th.max_value:
            action = f"{device}_off" if device else f"{param_name}_high"
            direction = "off" if device else None
            decisions.append(ThresholdDecision(
                param_name=param_name, value=value, threshold=th.max_value,
                action=action, device=device, direction=direction,
            ))
    return decisions


async def execute_decisions(
    decisions: list[ThresholdDecision],
    session: AsyncSession,
    mode: str,
    app_state=None,
):
    for d in decisions:
        session.add(AlarmLog(
            timestamp=datetime.utcnow(),
            param_name=d.param_name,
            value=d.value,
            threshold=d.threshold,
            action=d.action,
        ))
        await manager.broadcast_to_clients({
            "type": "alarm",
            "param": d.param_name,
            "value": d.value,
            "threshold": d.threshold,
            "action": d.action,
        })

        if d.device and d.direction and mode == "auto":
            hw_command = DEVICE_COMMAND_MAP[d.device][d.direction]
            await manager.send_to_bridge({"type": "control", "command": hw_command})
            if app_state:
                app_state.actuators[d.device] = (d.direction == "on")
            session.add(ControlLog(
                timestamp=datetime.utcnow(),
                device=d.device,
                action=d.direction,
                source="auto",
            ))
    await session.commit()


async def check_and_control(
    session: AsyncSession,
    temperature: float,
    humidity: float,
    light: float,
    soil_moisture: float,
    mode: str,
    app_state: dict = None,
):
    result = await session.execute(select(Threshold))
    thresholds = {t.param_name: t for t in result.scalars().all()}

    values = {
        "temperature": temperature,
        "humidity": humidity,
        "light": light,
        "soil_moisture": soil_moisture,
    }
    decisions = evaluate_thresholds(values, thresholds)
    await execute_decisions(decisions, session, mode, app_state)
