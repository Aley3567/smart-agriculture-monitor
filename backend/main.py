from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine, async_session, Base, get_db
from models import Board, SensorData, Threshold, AlarmLog, ControlLog, ControlRule, User
from schemas import (
    BoardOut,
    ThresholdItem,
    ThresholdOut,
    ControlRequest,
    ControlRuleIn,
    ControlRuleOut,
    ModeRequest,
    PaginatedSensorData,
    PaginatedAlarmLog,
    PaginatedControlLog,
    SensorDataOut,
    TestSensorSampleIn,
    AlarmLogOut,
    ControlLogOut,
    UserRegister,
    UserLogin,
    ChangePassword,
    UserOut,
    TokenOut,
    AlarmSummary,
)
from config import (
    CONTROL_RULE_SOIL_MOISTURE_PUMP,
    DEFAULT_CONTROL_RULES,
    DEFAULT_THRESHOLDS,
    DEVICE_COMMAND_MAP,
    normalize_device,
)

BOARD_ONLINE_TTL_SECONDS = 15
from ws_manager import manager
from control import cancel_all_auto_watering_tasks, check_and_control, set_manual_suppress
from auth import hash_password, verify_password, create_access_token, get_current_user
from weather import router as weather_router
from sensor_facts import build_sensor_facts, sensor_field_catalog
from time_utils import utc_now


DEFAULT_BOARD_ID = "A"
DEFAULT_BOARD_NAME = "greenhouse-a"


@dataclass
class SystemState:
    mode: str = "auto"
    device_online: bool = False
    actuators: dict[str, bool] = field(
        default_factory=lambda: {"pump": False, "fertilizer": False, "pest_light": False}
    )
    boards: dict[str, dict] = field(default_factory=dict)
    auto_watering: dict[str, dict] = field(default_factory=dict)
    alarm_lights: dict[str, bool] = field(default_factory=dict)
    manual_until: dict[str, dict[str, str | None]] = field(default_factory=dict)
    debug_events: list[dict] = field(default_factory=list)


app_state = SystemState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_sqlite_compat_columns(conn)

    async with async_session() as session:
        await _ensure_default_thresholds(session)

        board_count = (await session.execute(select(func.count()).select_from(Board))).scalar()
        if board_count == 0:
            session.add(Board(board_id=DEFAULT_BOARD_ID, board_name=DEFAULT_BOARD_NAME))
            await session.commit()

        await _ensure_default_control_rules(session)

    yield

    cancel_all_auto_watering_tasks()
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(weather_router)


async def ingest_sensor_data(data: dict):
    now = utc_now()
    board_id = data.get("board_id", DEFAULT_BOARD_ID)
    board_name = data.get("board_name", f"greenhouse-{board_id.lower()}")
    bridge_mode = _normalize_bridge_mode(data.get("bridge_mode") or app_state.boards.get(board_id, {}).get("bridge_mode"))
    is_test = bridge_mode == "mock"
    values = data.get("data", data)
    facts = build_sensor_facts(values)
    model_soil = facts["soil"]["value"]
    async with async_session() as session:
        await _touch_board(session, board_id, board_name, now, bridge_mode=bridge_mode)
        sensor_data = SensorData(
            timestamp=now,
            board_id=board_id,
            temp=values["temp"],
            humi=values["humi"],
            light=values["light"],
            soil=model_soil,
            source="bridge",
            bridge_mode=bridge_mode,
            is_test=is_test,
        )
        session.add(sensor_data)
        await session.flush()

        await manager.broadcast_to_clients({
            "type": "sensor_data",
            "board_id": board_id,
            "board_name": board_name,
            "data": {
                "temp": values["temp"],
                "humi": values["humi"],
                "light": values["light"],
                "soil": model_soil,
            },
            "fields": sensor_field_catalog(),
            "facts": facts,
            "source": "bridge",
            "bridge_mode": bridge_mode,
            "is_test": is_test,
            "timestamp": now.isoformat(),
        })

        await check_and_control(
            session,
            temperature=values["temp"],
            humidity=values["humi"],
            light=values["light"],
            soil_moisture=model_soil,
            mode=app_state.mode,
            app_state=app_state,
            board_id=board_id,
            allow_control=not is_test,
            alarm_source="bridge",
            bridge_mode=bridge_mode,
            is_test=is_test,
            sensor_data_id=sensor_data.id,
        )


async def handle_bridge_debug(raw: dict):
    event = {
        "type": "bridge_debug",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "board_id": raw.get("board_id", DEFAULT_BOARD_ID),
        "event": raw.get("event", "unknown"),
        "level": raw.get("level", "info"),
        "details": raw.get("details", {}),
    }
    app_state.debug_events.insert(0, event)
    del app_state.debug_events[80:]
    await manager.broadcast_to_clients(event)


@app.websocket("/ws/bridge")
async def ws_bridge(ws: WebSocket):
    await manager.connect_bridge(ws)
    app_state.device_online = True
    await _broadcast_status()
    try:
        while True:
            raw = await ws.receive_json()
            if raw.get("type") == "bridge_hello":
                board_id = raw.get("board_id", DEFAULT_BOARD_ID)
                board_name = raw.get("board_name", DEFAULT_BOARD_NAME)
                bridge_mode = _normalize_bridge_mode(raw.get("bridge_mode"))
                manager.register_bridge(board_id, ws)
                async with async_session() as session:
                    await _touch_board(session, board_id, board_name, utc_now(), bridge_mode=bridge_mode)
                    await session.commit()
                await _broadcast_status()
            elif raw.get("type") == "sensor_data":
                await ingest_sensor_data({
                    "board_id": raw.get("board_id", DEFAULT_BOARD_ID),
                    "board_name": raw.get("board_name", DEFAULT_BOARD_NAME),
                    "bridge_mode": raw.get("bridge_mode"),
                    "data": raw["data"],
                })
            elif raw.get("type") == "bridge_debug":
                await handle_bridge_debug(raw)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_bridge(ws)
        app_state.device_online = False
        await _broadcast_status()


@app.websocket("/ws/data")
async def ws_data(ws: WebSocket):
    await manager.connect_client(ws)
    await _broadcast_status()
    try:
        while True:
            raw = await ws.receive_json()
            if raw.get("type") == "control":
                await _handle_manual_control(raw["device"], raw["action"])
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_client(ws)


@app.get("/api/history", response_model=PaginatedSensorData)
async def get_history(
    board_id: Optional[str] = Query(None),
    source: str = Query("all", pattern="^(real|test|all)$"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(SensorData)
    count_query = select(func.count()).select_from(SensorData)

    if board_id:
        query = query.where(SensorData.board_id == board_id)
        count_query = count_query.where(SensorData.board_id == board_id)
    if source == "real":
        query = query.where(SensorData.is_test.is_(False))
        count_query = count_query.where(SensorData.is_test.is_(False))
    elif source == "test":
        query = query.where(SensorData.is_test.is_(True))
        count_query = count_query.where(SensorData.is_test.is_(True))
    if start:
        start_dt = datetime.fromisoformat(start)
        query = query.where(SensorData.timestamp >= start_dt)
        count_query = count_query.where(SensorData.timestamp >= start_dt)
    if end:
        end_dt = datetime.fromisoformat(end)
        query = query.where(SensorData.timestamp <= end_dt)
        count_query = count_query.where(SensorData.timestamp <= end_dt)

    total = (await db.execute(count_query)).scalar()

    query = query.order_by(SensorData.timestamp.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedSensorData(
        total=total,
        page=page,
        page_size=page_size,
        fields=sensor_field_catalog(),
        items=[_sensor_data_out(i) for i in items],
    )


@app.get("/api/thresholds", response_model=list[ThresholdOut])
async def get_thresholds(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Threshold))
    return [ThresholdOut.model_validate(t) for t in result.scalars().all()]


@app.put("/api/thresholds", response_model=list[ThresholdOut])
async def update_thresholds(
    items: list[ThresholdItem],
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for item in items:
        result = await db.execute(
            select(Threshold).where(Threshold.param_name == item.param_name)
        )
        th = result.scalar_one_or_none()
        if th:
            th.min_value = item.min_value
            th.max_value = item.max_value
        else:
            db.add(Threshold(
                param_name=item.param_name,
                min_value=item.min_value,
                max_value=item.max_value,
            ))
    await db.commit()

    result = await db.execute(select(Threshold))
    return [ThresholdOut.model_validate(t) for t in result.scalars().all()]


@app.get("/api/control-rules/soil-moisture-pump", response_model=ControlRuleOut)
async def get_soil_moisture_pump_rule(db: AsyncSession = Depends(get_db)):
    return ControlRuleOut.model_validate(await _get_or_create_soil_moisture_pump_rule(db))


@app.put("/api/control-rules/soil-moisture-pump", response_model=ControlRuleOut)
async def update_soil_moisture_pump_rule(
    item: ControlRuleIn,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if item.stop_at_or_above <= item.start_below:
        raise HTTPException(
            status_code=400,
            detail="stop_at_or_above must be greater than start_below",
        )

    rule = await _get_or_create_soil_moisture_pump_rule(db)
    rule.enabled = item.enabled
    rule.start_below = item.start_below
    rule.stop_at_or_above = item.stop_at_or_above
    rule.consecutive_samples = item.consecutive_samples
    rule.max_run_sec = item.max_run_sec
    rule.cooldown_sec = item.cooldown_sec
    await db.commit()
    await db.refresh(rule)
    return ControlRuleOut.model_validate(rule)


@app.get("/api/alarms", response_model=PaginatedAlarmLog)
async def get_alarms(
    board_id: Optional[str] = Query(None),
    source: str = Query("all", pattern="^(real|test|all)$"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(AlarmLog)
    count_query = select(func.count()).select_from(AlarmLog)

    if board_id:
        query = query.where(AlarmLog.board_id == board_id)
        count_query = count_query.where(AlarmLog.board_id == board_id)
    if source == "real":
        query = query.where(AlarmLog.is_test.is_(False))
        count_query = count_query.where(AlarmLog.is_test.is_(False))
    elif source == "test":
        query = query.where(AlarmLog.is_test.is_(True))
        count_query = count_query.where(AlarmLog.is_test.is_(True))
    if start:
        start_dt = datetime.fromisoformat(start)
        query = query.where(AlarmLog.timestamp >= start_dt)
        count_query = count_query.where(AlarmLog.timestamp >= start_dt)
    if end:
        end_dt = datetime.fromisoformat(end)
        query = query.where(AlarmLog.timestamp <= end_dt)
        count_query = count_query.where(AlarmLog.timestamp <= end_dt)

    total = (await db.execute(count_query)).scalar()

    query = query.order_by(AlarmLog.timestamp.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedAlarmLog(
        total=total,
        page=page,
        page_size=page_size,
        items=[_alarm_log_out(i) for i in items],
    )


@app.get("/api/alarms/summary", response_model=AlarmSummary)
async def get_alarms_summary(db: AsyncSession = Depends(get_db)):
    now = utc_now()
    since_24h = now - timedelta(hours=24)
    today_start = datetime(now.year, now.month, now.day)

    total = (await db.execute(
        select(func.count()).select_from(AlarmLog)
    )).scalar()
    today = (await db.execute(
        select(func.count()).select_from(AlarmLog).where(AlarmLog.timestamp >= today_start)
    )).scalar()
    last_24h = (await db.execute(
        select(func.count()).select_from(AlarmLog).where(AlarmLog.timestamp >= since_24h)
    )).scalar()

    param_rows = await db.execute(
        select(AlarmLog.param_name, func.count()).group_by(AlarmLog.param_name)
    )
    by_param = {name: count for name, count in param_rows.all()}

    latest_row = (await db.execute(
        select(AlarmLog).order_by(AlarmLog.timestamp.desc()).limit(1)
    )).scalar_one_or_none()
    latest = _alarm_log_out(latest_row) if latest_row else None

    return AlarmSummary(
        total=total,
        today=today,
        last_24h=last_24h,
        by_param=by_param,
        latest=latest,
    )


@app.get("/api/control-log", response_model=PaginatedControlLog)
async def get_control_log(
    board_id: Optional[str] = Query(None),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(ControlLog)
    count_query = select(func.count()).select_from(ControlLog)

    if board_id:
        query = query.where(ControlLog.board_id == board_id)
        count_query = count_query.where(ControlLog.board_id == board_id)
    if start:
        start_dt = datetime.fromisoformat(start)
        query = query.where(ControlLog.timestamp >= start_dt)
        count_query = count_query.where(ControlLog.timestamp >= start_dt)
    if end:
        end_dt = datetime.fromisoformat(end)
        query = query.where(ControlLog.timestamp <= end_dt)
        count_query = count_query.where(ControlLog.timestamp <= end_dt)

    total = (await db.execute(count_query)).scalar()

    query = query.order_by(ControlLog.timestamp.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedControlLog(
        total=total,
        page=page,
        page_size=page_size,
        items=[ControlLogOut.model_validate(i) for i in items],
    )


@app.get("/api/boards", response_model=list[BoardOut])
async def get_boards(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Board).order_by(Board.board_id))
    return [_board_out(board) for board in result.scalars().all()]


@app.get("/api/boards/{board_id}", response_model=BoardOut)
async def get_board(board_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Board).where(Board.board_id == board_id))
    board = result.scalar_one_or_none()
    if not board:
        raise HTTPException(status_code=404, detail=f"board not found: {board_id}")
    return _board_out(board)


@app.get("/api/status")
async def get_status():
    return _status_payload()


@app.get("/api/debug-events")
async def get_debug_events(
    board_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=80),
):
    events = app_state.debug_events
    if board_id:
        events = [item for item in events if item.get("board_id") == board_id]
    return {"items": events[:limit]}


@app.get("/api/sensor-fields")
async def get_sensor_fields():
    return sensor_field_catalog()


@app.post("/api/test/sensor-sample", response_model=SensorDataOut)
async def create_test_sensor_sample(req: TestSensorSampleIn, _user: User = Depends(get_current_user)):
    now = utc_now()
    values = {
        "temp": req.temperature,
        "humi": req.humidity,
        "light": req.light,
    }
    facts = build_sensor_facts(values)
    model_soil = facts["soil"]["value"]

    async with async_session() as session:
        sensor_data = SensorData(
            timestamp=now,
            board_id=req.board_id,
            temp=values["temp"],
            humi=values["humi"],
            light=values["light"],
            soil=model_soil,
            source="demo_injection",
            is_test=True,
            bridge_mode="test_injection",
        )
        session.add(sensor_data)
        await session.flush()

        await manager.broadcast_to_clients({
            "type": "sensor_data",
            "board_id": req.board_id,
            "data": {
                "temp": values["temp"],
                "humi": values["humi"],
                "light": values["light"],
                "soil": model_soil,
            },
            "fields": sensor_field_catalog(),
            "facts": facts,
            "source": "demo_injection",
            "bridge_mode": "test_injection",
            "is_test": True,
            "timestamp": now.isoformat(),
        })

        await check_and_control(
            session,
            temperature=req.temperature,
            humidity=req.humidity,
            light=req.light,
            soil_moisture=model_soil,
            mode=app_state.mode,
            app_state=app_state,
            board_id=req.board_id,
            allow_control=req.allow_control,
            alarm_source="demo_injection",
            bridge_mode="test_injection",
            is_test=True,
            sensor_data_id=sensor_data.id,
        )

        await session.refresh(sensor_data)
        return _sensor_data_out(sensor_data)


@app.post("/api/control")
async def manual_control(req: ControlRequest, _user: User = Depends(get_current_user)):
    result = await _handle_manual_control(req.device, req.action, req.board_id)
    return {"status": "ok", **result}


@app.put("/api/mode")
async def set_mode(req: ModeRequest, _user: User = Depends(get_current_user)):
    if req.mode not in ("auto", "manual"):
        return {"error": "mode must be 'auto' or 'manual'"}
    app_state.mode = req.mode
    await _broadcast_status()
    return {"mode": app_state.mode}


@app.post("/api/auth/register", response_model=TokenOut)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=data.username,
        hashed_password=hash_password(data.password),
        display_name=data.display_name or data.username,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(user.id, user.username)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@app.post("/api/auth/login", response_model=TokenOut)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    token = create_access_token(user.id, user.username)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@app.get("/api/auth/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@app.put("/api/auth/password")
async def change_password(
    data: ChangePassword,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(data.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码错误")
    user.hashed_password = hash_password(data.new_password)
    await db.commit()
    return {"message": "密码修改成功"}


async def _handle_manual_control(device: str, action: str, board_id: str = DEFAULT_BOARD_ID):
    canonical_device = normalize_device(device)
    mapping = DEVICE_COMMAND_MAP.get(canonical_device)
    if not mapping:
        raise HTTPException(status_code=400, detail=f"unsupported control device: {device}")
    command = mapping.get(action)
    if not command:
        raise HTTPException(status_code=400, detail=f"unsupported control action for {device}: {action}")

    bridge_connected = manager.has_bridge(board_id)
    await manager.send_to_bridge({"type": "control", "board_id": board_id, "command": command})

    app_state.actuators[canonical_device] = (action == "on")
    board_state = app_state.boards.setdefault(board_id, {
        "board_name": f"greenhouse-{board_id.lower()}",
        "online": False,
        "last_seen": None,
        "actuators": {"pump": False, "fertilizer": False, "pest_light": False},
    })
    board_state["actuators"][canonical_device] = (action == "on")

    set_manual_suppress(app_state, board_id, canonical_device)

    async with async_session() as session:
        session.add(ControlLog(
            timestamp=utc_now(),
            board_id=board_id,
            device=canonical_device,
            action=action,
            source="manual",
            reason="manual_request",
        ))
        await session.commit()

    await _broadcast_status()
    return {
        "board_id": board_id,
        "device": canonical_device,
        "action": action,
        "command": command,
        "bridge_connected": bridge_connected,
    }


async def _broadcast_status():
    await manager.broadcast_to_clients({"type": "status", **_status_payload(include_debug_events=False)})


def _status_payload(include_debug_events: bool = True) -> dict:
    payload = asdict(app_state)
    boards = {}
    for board_id, state in payload.get("boards", {}).items():
        last_seen = _parse_status_time(state.get("last_seen"))
        boards[board_id] = {
            **state,
            "online": bool(manager.has_bridge(board_id) and _is_recent(last_seen)),
        }
    payload["boards"] = boards
    payload["device_online"] = bool(manager.has_bridge())
    if not include_debug_events:
        payload.pop("debug_events", None)
    payload["server_time"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return payload


def _parse_status_time(value):
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _normalize_bridge_mode(value) -> str:
    return "mock" if value == "mock" else "hardware"


def _is_recent(value: datetime | None) -> bool:
    if not value:
        return False
    return utc_now() - value <= timedelta(seconds=BOARD_ONLINE_TTL_SECONDS)


def _sensor_data_out(item: SensorData) -> SensorDataOut:
    out = SensorDataOut.model_validate(item)
    out.facts = build_sensor_facts({
        "temp": item.temp,
        "humi": item.humi,
        "light": item.light,
    })
    return out


def _alarm_log_out(item: AlarmLog) -> AlarmLogOut:
    out = AlarmLogOut.model_validate(item)
    field = next(
        (candidate for candidate in sensor_field_catalog().values() if candidate["param"] == item.param_name),
        None,
    )
    out.param_label = field["label"] if field else item.param_name
    out.unit = field["unit"] if field else ""
    out.direction = "low" if item.value < item.threshold else "high"
    return out


def _board_out(board: Board) -> dict:
    return {
        "id": board.id,
        "board_id": board.board_id,
        "board_name": board.board_name,
        "location": board.location,
        "role": board.role,
        "enabled": board.enabled,
        "online": bool(board.enabled and board.last_seen),
        "last_seen": board.last_seen,
        "note": board.note,
    }


async def _touch_board(session: AsyncSession, board_id: str, board_name: str, last_seen: datetime, bridge_mode: str = "hardware"):
    result = await session.execute(select(Board).where(Board.board_id == board_id))
    board = result.scalar_one_or_none()
    if not board:
        board = Board(board_id=board_id, board_name=board_name)
        session.add(board)
    elif board_name and board.board_name != board_name:
        board.board_name = board_name
    board.last_seen = last_seen
    app_state.boards[board_id] = {
        "board_name": board.board_name or board_name,
        "online": True,
        "last_seen": last_seen.isoformat(),
        "bridge_mode": _normalize_bridge_mode(bridge_mode),
        "actuators": app_state.boards.get(board_id, {}).get(
            "actuators",
            {"pump": False, "fertilizer": False, "pest_light": False},
        ),
    }


async def _ensure_default_thresholds(session: AsyncSession):
    changed = False
    for param_name, values in DEFAULT_THRESHOLDS.items():
        result = await session.execute(select(Threshold).where(Threshold.param_name == param_name))
        threshold = result.scalar_one_or_none()
        if not threshold:
            session.add(Threshold(
                param_name=param_name,
                min_value=values["min_value"],
                max_value=values["max_value"],
            ))
            changed = True
        elif param_name == "light" and (threshold.min_value > 100 or threshold.max_value > 100):
            threshold.min_value = values["min_value"]
            threshold.max_value = values["max_value"]
            changed = True
    if changed:
        await session.commit()


async def _ensure_default_control_rules(session: AsyncSession):
    for rule_key, values in DEFAULT_CONTROL_RULES.items():
        result = await session.execute(select(ControlRule).where(ControlRule.rule_key == rule_key))
        if not result.scalar_one_or_none():
            session.add(ControlRule(rule_key=rule_key, **values))
    await session.commit()


async def _get_or_create_soil_moisture_pump_rule(session: AsyncSession) -> ControlRule:
    result = await session.execute(
        select(ControlRule).where(ControlRule.rule_key == CONTROL_RULE_SOIL_MOISTURE_PUMP)
    )
    rule = result.scalar_one_or_none()
    if rule:
        return rule

    values = DEFAULT_CONTROL_RULES[CONTROL_RULE_SOIL_MOISTURE_PUMP]
    rule = ControlRule(rule_key=CONTROL_RULE_SOIL_MOISTURE_PUMP, **values)
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


async def _ensure_sqlite_compat_columns(conn):
    for table in ("alarm_log", "control_log"):
        rows = (await conn.execute(text(f"PRAGMA table_info({table})"))).mappings().all()
        if rows and "board_id" not in {row["name"] for row in rows}:
            await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN board_id VARCHAR DEFAULT 'A'"))

    rows = (await conn.execute(text("PRAGMA table_info(control_log)"))).mappings().all()
    control_columns = {row["name"] for row in rows}
    if rows and "reason" not in control_columns:
        await conn.execute(text("ALTER TABLE control_log ADD COLUMN reason TEXT DEFAULT ''"))
    if rows:
        await conn.execute(text("UPDATE control_log SET reason = '' WHERE reason IS NULL"))

    rows = (await conn.execute(text("PRAGMA table_info(alarm_log)"))).mappings().all()
    alarm_columns = {row["name"] for row in rows}
    if rows and "source" not in alarm_columns:
        await conn.execute(text("ALTER TABLE alarm_log ADD COLUMN source TEXT DEFAULT 'bridge'"))
    if rows and "bridge_mode" not in alarm_columns:
        await conn.execute(text("ALTER TABLE alarm_log ADD COLUMN bridge_mode TEXT DEFAULT 'unknown'"))
    if rows and "is_test" not in alarm_columns:
        await conn.execute(text("ALTER TABLE alarm_log ADD COLUMN is_test BOOLEAN DEFAULT 0"))
    if rows and "sensor_data_id" not in alarm_columns:
        await conn.execute(text("ALTER TABLE alarm_log ADD COLUMN sensor_data_id INTEGER"))
    if rows:
        await conn.execute(text("UPDATE alarm_log SET source = 'bridge' WHERE source IS NULL"))
        await conn.execute(text("UPDATE alarm_log SET bridge_mode = 'unknown' WHERE bridge_mode IS NULL"))
        await conn.execute(text("UPDATE alarm_log SET is_test = 0 WHERE is_test IS NULL"))

    rows = (await conn.execute(text("PRAGMA table_info(sensor_data)"))).mappings().all()
    if not rows:
        return

    columns = {row["name"] for row in rows}
    if "board_id" not in columns:
        await conn.execute(text("ALTER TABLE sensor_data ADD COLUMN board_id VARCHAR DEFAULT 'A'"))
    if "source" not in columns:
        await conn.execute(text("ALTER TABLE sensor_data ADD COLUMN source TEXT DEFAULT 'bridge'"))
    if "bridge_mode" not in columns:
        await conn.execute(text("ALTER TABLE sensor_data ADD COLUMN bridge_mode TEXT DEFAULT 'unknown'"))
    if "is_test" not in columns:
        await conn.execute(text("ALTER TABLE sensor_data ADD COLUMN is_test BOOLEAN DEFAULT 0"))
    await conn.execute(text("UPDATE sensor_data SET source = 'bridge' WHERE source IS NULL"))
    await conn.execute(text("UPDATE sensor_data SET bridge_mode = 'unknown' WHERE bridge_mode IS NULL"))
    await conn.execute(text("UPDATE sensor_data SET is_test = 0 WHERE is_test IS NULL"))
