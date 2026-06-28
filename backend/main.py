from dataclasses import dataclass, field, asdict
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine, async_session, Base, get_db
from models import SensorData, Threshold, AlarmLog, ControlLog, User
from schemas import (
    ThresholdItem,
    ThresholdOut,
    ControlRequest,
    ModeRequest,
    PaginatedSensorData,
    PaginatedAlarmLog,
    SensorDataOut,
    AlarmLogOut,
    UserRegister,
    UserLogin,
    ChangePassword,
    UserOut,
    TokenOut,
)
from config import DEFAULT_THRESHOLDS, DEVICE_COMMAND_MAP
from ws_manager import manager
from control import check_and_control
from auth import hash_password, verify_password, create_access_token, get_current_user


@dataclass
class SystemState:
    mode: str = "auto"
    device_online: bool = False
    actuators: dict[str, bool] = field(
        default_factory=lambda: {"pump": False, "fertilizer": False, "skylight": False}
    )


app_state = SystemState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        result = await session.execute(select(func.count()).select_from(Threshold))
        count = result.scalar()
        if count == 0:
            for param_name, values in DEFAULT_THRESHOLDS.items():
                session.add(Threshold(
                    param_name=param_name,
                    min_value=values["min_value"],
                    max_value=values["max_value"],
                ))
            await session.commit()

    yield

    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def ingest_sensor_data(data: dict):
    now = datetime.utcnow()
    async with async_session() as session:
        session.add(SensorData(
            timestamp=now,
            temp=data["temp"],
            humi=data["humi"],
            light=data["light"],
            soil=data["soil"],
        ))
        await session.commit()

        await manager.broadcast_to_clients({
            "type": "sensor_data",
            "data": {
                "temp": data["temp"],
                "humi": data["humi"],
                "light": data["light"],
                "soil": data["soil"],
            },
            "timestamp": now.isoformat(),
        })

        await check_and_control(
            session,
            temperature=data["temp"],
            humidity=data["humi"],
            light=data["light"],
            soil_moisture=data["soil"],
            mode=app_state.mode,
            app_state=app_state,
        )


@app.websocket("/ws/bridge")
async def ws_bridge(ws: WebSocket):
    await manager.connect_bridge(ws)
    app_state.device_online = True
    await _broadcast_status()
    try:
        while True:
            raw = await ws.receive_json()
            if raw.get("type") == "sensor_data":
                await ingest_sensor_data(raw["data"])
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_bridge()
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
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(SensorData)
    count_query = select(func.count()).select_from(SensorData)

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
        items=[SensorDataOut.model_validate(i) for i in items],
    )


@app.get("/api/thresholds", response_model=list[ThresholdOut])
async def get_thresholds(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Threshold))
    return [ThresholdOut.model_validate(t) for t in result.scalars().all()]


@app.put("/api/thresholds", response_model=list[ThresholdOut])
async def update_thresholds(
    items: list[ThresholdItem],
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


@app.get("/api/alarms", response_model=PaginatedAlarmLog)
async def get_alarms(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(AlarmLog)
    count_query = select(func.count()).select_from(AlarmLog)

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
        items=[AlarmLogOut.model_validate(i) for i in items],
    )


@app.get("/api/status")
async def get_status():
    return asdict(app_state)


@app.post("/api/control")
async def manual_control(req: ControlRequest):
    await _handle_manual_control(req.device, req.action)
    return {"status": "ok"}


@app.put("/api/mode")
async def set_mode(req: ModeRequest):
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


async def _handle_manual_control(device: str, action: str):
    mapping = DEVICE_COMMAND_MAP.get(device)
    if not mapping:
        return
    command = mapping.get(action)
    if not command:
        return

    await manager.send_to_bridge({"type": "control", "command": command})

    app_state.actuators[device] = (action == "on")

    async with async_session() as session:
        session.add(ControlLog(
            timestamp=datetime.utcnow(),
            device=device,
            action=action,
            source="manual",
        ))
        await session.commit()

    await _broadcast_status()


async def _broadcast_status():
    await manager.broadcast_to_clients({
        "type": "status",
        "device_online": app_state.device_online,
        "mode": app_state.mode,
        "actuators": app_state.actuators,
    })
