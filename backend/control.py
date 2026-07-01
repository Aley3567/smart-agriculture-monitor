import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    ALARM_LIGHT_COMMAND_MAP,
    CONTROL_RULE_SOIL_MOISTURE_PUMP,
    DEFAULT_CONTROL_RULES,
    DEVICE_COMMAND_MAP,
    PARAM_DEVICE_MAP,
    normalize_device,
)
from database import async_session
from models import Threshold, AlarmLog, ControlLog, ControlRule, SensorData
from sensor_facts import compute_model_values
from time_utils import utc_now
from ws_manager import manager


_pump_timeout_tasks: dict[str, asyncio.Task] = {}
_alarm_light_state: dict[str, bool] = {}


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
    board_id: str = "A",
    allow_control: bool = True,
    alarm_source: str = "bridge",
    bridge_mode: str = "hardware",
    is_test: bool = False,
    sensor_data_id: int | None = None,
):
    for d in decisions:
        session.add(AlarmLog(
            timestamp=utc_now(),
            board_id=board_id,
            param_name=d.param_name,
            value=d.value,
            threshold=d.threshold,
            action=d.action,
            source=alarm_source,
            bridge_mode=bridge_mode,
            is_test=is_test,
            sensor_data_id=sensor_data_id,
        ))
        await manager.broadcast_to_clients({
            "type": "alarm",
            "board_id": board_id,
            "param": d.param_name,
            "value": d.value,
            "threshold": d.threshold,
            "action": d.action,
            "source": alarm_source,
            "bridge_mode": bridge_mode,
            "is_test": is_test,
            "sensor_data_id": sensor_data_id,
        })

    await session.commit()


async def check_and_control(
    session: AsyncSession,
    temperature: float,
    humidity: float,
    light: float,
    soil_moisture: float,
    mode: str,
    app_state: dict = None,
    board_id: str = "A",
    allow_control: bool = True,
    alarm_source: str = "bridge",
    bridge_mode: str = "hardware",
    is_test: bool = False,
    sensor_data_id: int | None = None,
    model_values: dict | None = None,
):
    result = await session.execute(select(Threshold))
    thresholds = {t.param_name: t for t in result.scalars().all()}

    model = model_values or compute_model_values({
        "temp": temperature,
        "humi": humidity,
        "light": light,
    })
    values = {
        "temperature": temperature,
        "humidity": humidity,
        "light": light,
        "soil_moisture": soil_moisture,
    }
    values["soil_fertility"] = model["soil_fertility"]
    decisions = evaluate_thresholds(values, thresholds)
    await execute_decisions(
        decisions,
        session,
        mode,
        app_state,
        board_id,
        allow_control=allow_control,
        alarm_source=alarm_source,
        bridge_mode=bridge_mode,
        is_test=is_test,
        sensor_data_id=sensor_data_id,
    )
    await _apply_alarm_light_state(
        decisions=decisions,
        app_state=app_state,
        board_id=board_id,
        allow_control=allow_control,
        alarm_source=alarm_source,
        is_test=is_test,
    )
    await _apply_soil_moisture_pump_rule(
        session=session,
        soil_moisture=soil_moisture,
        mode=mode,
        app_state=app_state,
        board_id=board_id,
        allow_control=allow_control,
        is_test=is_test,
    )
    fert_th = thresholds.get("soil_fertility")
    fert_low = fert_th.min_value if fert_th else 60.0
    await _apply_auto_device(
        app_state=app_state, board_id=board_id, device="fertilizer",
        should_on=model["soil_fertility"] < fert_low,
        allow_control=allow_control, is_test=is_test, mode=mode,
    )
    await _apply_auto_device(
        app_state=app_state, board_id=board_id, device="pest_light",
        should_on=model["infrared"] > 0,
        allow_control=allow_control, is_test=is_test, mode=mode,
    )


async def _apply_auto_device(
    app_state, board_id: str, device: str, should_on: bool,
    allow_control: bool, is_test: bool, mode: str,
):
    if not allow_control or mode != "auto" or is_test:
        return
    if _is_manual_suppressed(app_state, board_id, device):
        return
    canonical = normalize_device(device)
    current = app_state.actuators.get(canonical, False) if app_state else False
    if current == should_on:
        return
    action = "on" if should_on else "off"
    hw_command = DEVICE_COMMAND_MAP[canonical][action]
    await manager.send_to_bridge({"type": "control", "board_id": board_id, "command": hw_command})
    if app_state:
        app_state.actuators[canonical] = should_on
        board_state = app_state.boards.get(board_id, {})
        if "actuators" in board_state:
            board_state["actuators"][canonical] = should_on


async def _apply_alarm_light_state(
    decisions: list[ThresholdDecision],
    app_state=None,
    board_id: str = "A",
    allow_control: bool = True,
    alarm_source: str = "bridge",
    bridge_mode: str = "hardware",
    is_test: bool = False,
):
    if not allow_control or is_test or alarm_source != "bridge":
        return

    if _is_manual_suppressed(app_state, board_id, "alarm_light"):
        return

    next_active = bool(decisions)
    state = _get_alarm_light_state(app_state)
    current_active = state.get(board_id)
    if current_active == next_active:
        return
    if current_active is None and not next_active:
        state[board_id] = False
        return

    action = "on" if next_active else "off"
    await manager.send_to_bridge({
        "type": "control",
        "board_id": board_id,
        "command": ALARM_LIGHT_COMMAND_MAP[action],
    })
    state[board_id] = next_active


def _get_alarm_light_state(app_state) -> dict[str, bool]:
    if app_state is None:
        return _alarm_light_state
    if not hasattr(app_state, "alarm_lights"):
        app_state.alarm_lights = {}
    return app_state.alarm_lights


async def _apply_soil_moisture_pump_rule(
    session: AsyncSession,
    soil_moisture: float,
    mode: str,
    app_state=None,
    board_id: str = "A",
    allow_control: bool = True,
    is_test: bool = False,
):
    if not allow_control or mode != "auto":
        return

    if _is_manual_suppressed(app_state, board_id, "pump"):
        return

    rule = await _get_or_create_soil_moisture_pump_rule(session)
    if not rule.enabled:
        await session.commit()
        return

    pump_on = await _pump_is_on(session, app_state, board_id)
    if pump_on and soil_moisture >= rule.stop_at_or_above:
        await _write_pump_control(
            session=session,
            app_state=app_state,
            board_id=board_id,
            action="off",
            reason="soil_moisture_recovered",
            cooldown_sec=rule.cooldown_sec,
        )
        await session.commit()
        await _broadcast_auto_status(app_state)
        return

    if pump_on or soil_moisture >= rule.start_below:
        await session.commit()
        return

    if not await _has_consecutive_low_soil_samples(session, board_id, rule, is_test=is_test):
        await session.commit()
        return

    if not await _cooldown_elapsed(session, app_state, board_id, rule.cooldown_sec):
        await session.commit()
        return

    await _write_pump_control(
        session=session,
        app_state=app_state,
        board_id=board_id,
        action="on",
        reason="soil_moisture_below_start",
        max_run_sec=rule.max_run_sec,
    )
    await session.commit()
    await _broadcast_auto_status(app_state)


async def _get_or_create_soil_moisture_pump_rule(session: AsyncSession) -> ControlRule:
    result = await session.execute(
        select(ControlRule).where(ControlRule.rule_key == CONTROL_RULE_SOIL_MOISTURE_PUMP)
    )
    rule = result.scalar_one_or_none()
    if rule:
        return rule

    defaults = DEFAULT_CONTROL_RULES[CONTROL_RULE_SOIL_MOISTURE_PUMP]
    rule = ControlRule(rule_key=CONTROL_RULE_SOIL_MOISTURE_PUMP, **defaults)
    session.add(rule)
    await session.flush()
    return rule


async def _has_consecutive_low_soil_samples(
    session: AsyncSession,
    board_id: str,
    rule: ControlRule,
    is_test: bool = False,
) -> bool:
    result = await session.execute(
        select(SensorData)
        .where(SensorData.board_id == board_id, SensorData.is_test.is_(is_test))
        .order_by(SensorData.timestamp.desc(), SensorData.id.desc())
        .limit(rule.consecutive_samples)
    )
    rows = result.scalars().all()
    return (
        len(rows) >= rule.consecutive_samples
        and all(row.soil < rule.start_below for row in rows)
    )


async def _cooldown_elapsed(
    session: AsyncSession,
    app_state,
    board_id: str,
    cooldown_sec: int,
) -> bool:
    if cooldown_sec <= 0:
        return True
    state = _get_auto_watering_state(app_state, board_id, create=False)
    if state and state.get("cooldown_until"):
        cooldown_until = _parse_timestamp(state["cooldown_until"])
        if cooldown_until and utc_now() < cooldown_until:
            return False

    result = await session.execute(
        select(ControlLog)
        .where(
            ControlLog.board_id == board_id,
            ControlLog.device == "pump",
            ControlLog.source == "auto",
            ControlLog.action == "off",
        )
        .order_by(ControlLog.timestamp.desc(), ControlLog.id.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    if not latest:
        return True
    return (utc_now() - latest.timestamp).total_seconds() >= cooldown_sec


async def _pump_is_on(session: AsyncSession, app_state, board_id: str) -> bool:
    if app_state:
        auto_state = _get_auto_watering_state(app_state, board_id, create=False)
        if auto_state and auto_state.get("active") is True:
            return True
        board_state = app_state.boards.get(board_id, {})
        actuators = board_state.get("actuators", {})
        if "pump" in actuators and actuators["pump"]:
            return bool(actuators["pump"])

    result = await session.execute(
        select(ControlLog)
        .where(ControlLog.board_id == board_id, ControlLog.device == "pump")
        .order_by(ControlLog.timestamp.desc(), ControlLog.id.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    return bool(latest and latest.action == "on")


async def _write_pump_control(
    session: AsyncSession,
    app_state,
    board_id: str,
    action: str,
    reason: str,
    max_run_sec: int | None = None,
    cooldown_sec: int | None = None,
):
    canonical_device = normalize_device("pump")
    hw_command = DEVICE_COMMAND_MAP[canonical_device][action]
    await manager.send_to_bridge({"type": "control", "board_id": board_id, "command": hw_command})
    now = utc_now()
    if app_state:
        app_state.actuators[canonical_device] = (action == "on")
        board_state = app_state.boards.setdefault(board_id, {
            "board_name": f"greenhouse-{board_id.lower()}",
            "online": False,
            "last_seen": None,
            "actuators": {"pump": False, "fertilizer": False, "pest_light": False},
        })
        board_state["actuators"][canonical_device] = (action == "on")
        auto_state = _get_auto_watering_state(app_state, board_id)
        if action == "on":
            started_at = _format_timestamp(now)
            auto_state.update({
                "active": True,
                "started_at": started_at,
                "cooldown_until": None,
            })
            if max_run_sec is not None:
                _schedule_pump_timeout(board_id, started_at, max_run_sec, app_state)
        else:
            _cancel_pump_timeout_task(board_id)
            auto_state["active"] = False
            auto_state["started_at"] = None
            if cooldown_sec is not None and cooldown_sec > 0:
                auto_state["cooldown_until"] = _format_timestamp(now + timedelta(seconds=cooldown_sec))
            else:
                auto_state["cooldown_until"] = None
    session.add(ControlLog(
        timestamp=now,
        board_id=board_id,
        device=canonical_device,
        action=action,
        source="auto",
        reason=reason,
    ))


async def _max_run_timeout(board_id: str, started_at: str, max_run_sec: int, app_state):
    try:
        await asyncio.sleep(max_run_sec)
        state = _get_auto_watering_state(app_state, board_id, create=False)
        if not state or not state.get("active") or state.get("started_at") != started_at:
            return

        async with async_session() as session:
            rule = await _get_or_create_soil_moisture_pump_rule(session)
            await _write_pump_control(
                session=session,
                app_state=app_state,
                board_id=board_id,
                action="off",
                reason="max_run_time_reached",
                cooldown_sec=rule.cooldown_sec,
            )
            await session.commit()
        await _broadcast_auto_status(app_state)
    except asyncio.CancelledError:
        raise
    finally:
        task = _pump_timeout_tasks.get(board_id)
        if task is asyncio.current_task():
            _pump_timeout_tasks.pop(board_id, None)


def _schedule_pump_timeout(board_id: str, started_at: str, max_run_sec: int, app_state):
    _cancel_pump_timeout_task(board_id)
    _pump_timeout_tasks[board_id] = asyncio.create_task(
        _max_run_timeout(board_id, started_at, max_run_sec, app_state)
    )


def _cancel_pump_timeout_task(board_id: str):
    task = _pump_timeout_tasks.pop(board_id, None)
    if task and task is not asyncio.current_task() and not task.done():
        task.cancel()


def cancel_all_auto_watering_tasks():
    for task in list(_pump_timeout_tasks.values()):
        if not task.done():
            task.cancel()
    _pump_timeout_tasks.clear()


def _get_auto_watering_state(app_state, board_id: str, create: bool = True) -> dict | None:
    if not app_state:
        return None
    if not hasattr(app_state, "auto_watering"):
        app_state.auto_watering = {}
    if not create:
        return app_state.auto_watering.get(board_id)
    return app_state.auto_watering.setdefault(board_id, {
        "active": False,
        "started_at": None,
        "cooldown_until": None,
    })


def _format_timestamp(value):
    return f"{value.isoformat()}Z"


def _parse_timestamp(value: str):
    try:
        normalized = value[:-1] if value.endswith("Z") else value
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


MANUAL_SUPPRESS_SECONDS = 60


def set_manual_suppress(app_state, board_id: str, device: str):
    if not app_state:
        return
    if not hasattr(app_state, "manual_until"):
        app_state.manual_until = {}
    board = app_state.manual_until.setdefault(board_id, {})
    board[device] = _format_timestamp(utc_now() + timedelta(seconds=MANUAL_SUPPRESS_SECONDS))


def _is_manual_suppressed(app_state, board_id: str, device: str) -> bool:
    if not app_state or not hasattr(app_state, "manual_until"):
        return False
    until_str = app_state.manual_until.get(board_id, {}).get(device)
    if not until_str:
        return False
    until = _parse_timestamp(until_str)
    return bool(until and utc_now() < until)


async def _broadcast_auto_status(app_state):
    if not app_state:
        return
    await manager.broadcast_to_clients({
        "type": "status",
        "device_online": app_state.device_online,
        "mode": app_state.mode,
        "actuators": app_state.actuators,
        "boards": app_state.boards,
        "auto_watering": app_state.auto_watering,
    })
