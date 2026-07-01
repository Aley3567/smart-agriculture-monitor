import asyncio
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from serial_bridge.bridge import build_sensor_message, parse_serial_payload, should_apply_control


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

db_fd, db_path = tempfile.mkstemp(prefix="smart-agri-test-", suffix=".db")
os.close(db_fd)

import config  # noqa: E402

config.DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"

from database import Base, async_session, engine  # noqa: E402
from main import app, app_state, ingest_sensor_data  # noqa: E402
from control import cancel_all_auto_watering_tasks, evaluate_thresholds  # noqa: E402
from models import AlarmLog, Board, ControlLog, ControlRule, SensorData, Threshold, User  # noqa: E402
from auth import hash_password, create_access_token  # noqa: E402
from sqlalchemy import select  # noqa: E402
from ws_manager import WSManager, manager  # noqa: E402


class FakeWebSocket:
    def __init__(self):
        self.sent = []
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def send_json(self, data):
        self.sent.append(data)


class SensorFactsContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        app_state.mode = "auto"
        app_state.actuators = {"pump": False, "fertilizer": False, "pest_light": False}
        app_state.boards = {}
        app_state.auto_watering = {}
        app_state.alarm_lights = {}
        cancel_all_auto_watering_tasks()
        manager.disconnect_bridge()

        async with async_session() as session:
            for param_name, values in config.DEFAULT_THRESHOLDS.items():
                session.add(Threshold(
                    param_name=param_name,
                    min_value=values["min_value"],
                    max_value=values["max_value"],
                ))
            for rule_key, values in config.DEFAULT_CONTROL_RULES.items():
                session.add(ControlRule(rule_key=rule_key, **values))
            session.add(SensorData(
                timestamp=datetime(2026, 6, 29, 9, 0, 0),
                temp=26.0,
                humi=61.0,
                light=50.0,
                soil=47.0,
            ))
            test_user = User(
                username="testuser",
                hashed_password=hash_password("testpass123"),
                display_name="Test User",
            )
            session.add(test_user)
            await session.commit()

            await session.refresh(test_user)
            token = create_access_token(test_user.id, test_user.username)
            self._auth_headers = {"Authorization": f"Bearer {token}"}

    async def asyncTearDown(self):
        cancel_all_auto_watering_tasks()
        await asyncio.sleep(0)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def test_history_returns_sensor_facts_with_source_truth(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/history?page_size=1")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertIn("fields", payload)
        self.assertEqual(payload["fields"]["temp"]["source"], "measured")
        self.assertEqual(payload["fields"]["light"]["source"], "measured")
        self.assertEqual(payload["fields"]["light"]["unit"], "相对值")
        self.assertIn("GL5516 P0.7 ADC", payload["fields"]["light"]["detail"])
        self.assertEqual(payload["fields"]["soil"]["source"], "computed_backend")

        row = payload["items"][0]
        self.assertEqual(row["temp"], 26.0)
        self.assertEqual(row["source"], "bridge")
        self.assertEqual(row["bridge_mode"], "hardware")
        self.assertFalse(row["is_test"])
        self.assertEqual(row["facts"]["temp"]["value"], 26.0)
        self.assertEqual(row["facts"]["temp"]["source"], "measured")
        self.assertEqual(row["facts"]["light"]["source"], "measured")
        self.assertEqual(row["facts"]["light"]["unit"], "相对值")
        self.assertIn("GL5516 P0.7 ADC", row["facts"]["light"]["detail"])
        self.assertEqual(row["facts"]["soil"]["source"], "computed_backend")
        self.assertTrue(row["facts"]["soil"]["available"])

    async def test_history_source_filter_splits_real_and_test_rows(self):
        async with async_session() as session:
            session.add(SensorData(
                timestamp=datetime(2026, 6, 29, 10, 0, 0),
                board_id="A",
                temp=99.0,
                humi=1.0,
                light=2.0,
                soil=3.0,
                source="fixture",
                is_test=True,
            ))
            await session.commit()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            default_response = await client.get("/api/history")
            real_response = await client.get("/api/history", params={"source": "real"})
            test_response = await client.get("/api/history", params={"source": "test"})

        self.assertEqual(default_response.status_code, 200)
        default_payload = default_response.json()
        self.assertEqual(default_payload["total"], 2)
        self.assertEqual({row["source"] for row in default_payload["items"]}, {"bridge", "fixture"})

        self.assertEqual(real_response.status_code, 200)
        real_payload = real_response.json()
        self.assertEqual(real_payload["total"], 1)
        self.assertEqual(real_payload["items"][0]["source"], "bridge")
        self.assertEqual(real_payload["items"][0]["bridge_mode"], "hardware")
        self.assertFalse(real_payload["items"][0]["is_test"])

        self.assertEqual(test_response.status_code, 200)
        test_payload = test_response.json()
        self.assertEqual(test_payload["total"], 1)
        self.assertEqual(test_payload["items"][0]["source"], "fixture")
        self.assertEqual(test_payload["items"][0]["bridge_mode"], "hardware")
        self.assertTrue(test_payload["items"][0]["is_test"])

    async def test_mock_bridge_samples_are_marked_as_test_data(self):
        await ingest_sensor_data({
            "board_id": "A",
            "board_name": "greenhouse-a",
            "bridge_mode": "mock",
            "data": {"temp": 39.5, "humi": 55.0, "light": 500.0, "soil": 45.0},
        })

        async with async_session() as session:
            rows = (await session.execute(select(SensorData).order_by(SensorData.id.desc()))).scalars().all()
            alarms = (await session.execute(select(AlarmLog).order_by(AlarmLog.id.desc()))).scalars().all()

        self.assertEqual(rows[0].bridge_mode, "mock")
        self.assertTrue(rows[0].is_test)
        self.assertGreaterEqual(len(alarms), 1)
        self.assertEqual(alarms[0].bridge_mode, "mock")
        self.assertTrue(alarms[0].is_test)

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            real_response = await client.get("/api/history", params={"source": "real"})
            test_response = await client.get("/api/history", params={"source": "test"})

        self.assertEqual(real_response.status_code, 200)
        self.assertEqual(test_response.status_code, 200)
        self.assertNotIn("mock", {row["bridge_mode"] for row in real_response.json()["items"]})
        self.assertIn("mock", {row["bridge_mode"] for row in test_response.json()["items"]})

    async def test_sensor_fields_exposes_backend_model_outputs(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/sensor-fields")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["co2"]["source"], "simulated_backend")
        self.assertTrue(payload["co2"]["available"])
        self.assertEqual(payload["soil_ec"]["source"], "computed_backend")
        self.assertEqual(payload["soil_tds"]["source"], "computed_backend")
        self.assertEqual(payload["soil_fertility"]["source"], "computed_backend")
        self.assertTrue(payload["infrared"]["available"])
        self.assertNotIn("value", payload["co2"])

    async def test_status_exposes_server_time_for_clock_diagnostics(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("server_time", payload)
        self.assertTrue(payload["server_time"].endswith("Z"))

    async def test_control_rejects_unknown_device_without_logging(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/control",
                json={"device": "fan", "action": "on"},
                headers=self._auth_headers,
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "unsupported control device: fan")

        async with async_session() as session:
            rows = (await session.execute(select(ControlLog))).scalars().all()
        self.assertEqual(rows, [])

    async def test_control_rejects_unknown_action_without_logging(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/control",
                json={"device": "pump", "action": "toggle"},
                headers=self._auth_headers,
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "unsupported control action for pump: toggle")

        async with async_session() as session:
            rows = (await session.execute(select(ControlLog))).scalars().all()
        self.assertEqual(rows, [])

    async def test_control_does_not_expose_alarm_light_as_manual_device(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/control",
                json={"device": "alarm_light", "action": "on"},
                headers=self._auth_headers,
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "unsupported control device: alarm_light")

        async with async_session() as session:
            rows = (await session.execute(select(ControlLog))).scalars().all()
        self.assertEqual(rows, [])

    async def test_soil_moisture_pump_rule_get_and_put(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            get_response = await client.get("/api/control-rules/soil-moisture-pump")
            put_response = await client.put(
                "/api/control-rules/soil-moisture-pump",
                json={
                    "enabled": False,
                    "start_below": 32.0,
                    "stop_at_or_above": 44.0,
                    "consecutive_samples": 2,
                    "max_run_sec": 15,
                    "cooldown_sec": 5,
                },
                headers=self._auth_headers,
            )
            get_after_response = await client.get("/api/control-rules/soil-moisture-pump")

        self.assertEqual(get_response.status_code, 200)
        default_rule = get_response.json()
        self.assertEqual(default_rule["rule_key"], "soil-moisture-pump")
        self.assertTrue(default_rule["enabled"])
        self.assertEqual(default_rule["start_below"], 35.0)
        self.assertEqual(default_rule["stop_at_or_above"], 45.0)
        self.assertEqual(default_rule["consecutive_samples"], 5)
        self.assertEqual(default_rule["max_run_sec"], 20)
        self.assertEqual(default_rule["cooldown_sec"], 30)

        self.assertEqual(put_response.status_code, 200)
        updated_rule = put_response.json()
        self.assertFalse(updated_rule["enabled"])
        self.assertEqual(updated_rule["start_below"], 32.0)
        self.assertEqual(updated_rule["consecutive_samples"], 2)
        self.assertEqual(get_after_response.json()["cooldown_sec"], 5)

    async def test_valid_control_logs_manual_action_when_bridge_is_absent(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/control",
                json={"device": "pump", "action": "on"},
                headers=self._auth_headers,
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["device"], "pump")
        self.assertEqual(payload["action"], "on")
        self.assertEqual(payload["command"], "BLEGLED1")
        self.assertFalse(payload["bridge_connected"])

        async with async_session() as session:
            rows = (await session.execute(select(ControlLog))).scalars().all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].device, "pump")
        self.assertEqual(rows[0].action, "on")
        self.assertEqual(rows[0].source, "manual")
        self.assertEqual(rows[0].reason, "manual_request")

    async def test_pest_light_control_uses_blegled3_command(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/control",
                json={"device": "pest_light", "action": "on"},
                headers=self._auth_headers,
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["device"], "pest_light")
        self.assertEqual(payload["command"], "BLEGLED3")

        async with async_session() as session:
            rows = (await session.execute(select(ControlLog))).scalars().all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].device, "pest_light")

    async def test_legacy_skylight_control_alias_is_recorded_as_pest_light(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/control",
                json={"device": "skylight", "action": "off"},
                headers=self._auth_headers,
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["device"], "pest_light")
        self.assertEqual(payload["command"], "BLEKLED3")

        async with async_session() as session:
            rows = (await session.execute(select(ControlLog))).scalars().all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].device, "pest_light")

    def test_light_threshold_alarm_does_not_auto_control_pest_light(self):
        class ThresholdStub:
            min_value = 10.0
            max_value = 90.0

        decisions = evaluate_thresholds({"light": 95.0}, {"light": ThresholdStub()})

        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].action, "light_high")
        self.assertIsNone(decisions[0].device)
        self.assertIsNone(decisions[0].direction)

    async def test_real_bridge_threshold_alarm_turns_alarm_light_on(self):
        bridge = FakeWebSocket()
        await manager.connect_bridge(bridge, board_id="R1")

        try:
            await ingest_sensor_data({
                "board_id": "R1",
                "board_name": "greenhouse-r1",
                "data": {
                    "temp": 36.0,
                    "humi": 75.0,
                    "light": 30.0,
                },
            })
        finally:
            manager.disconnect_bridge(bridge)

        self.assertEqual(bridge.sent, [
            {"type": "control", "board_id": "R1", "command": "BLEALARM1"},
        ])
        self.assertTrue(app_state.alarm_lights["R1"])

        async with async_session() as session:
            alarms = (await session.execute(select(AlarmLog))).scalars().all()
            controls = (await session.execute(select(ControlLog))).scalars().all()

        self.assertEqual(len(alarms), 1)
        self.assertEqual(alarms[0].board_id, "R1")
        self.assertEqual(alarms[0].param_name, "temperature")
        self.assertEqual(alarms[0].source, "bridge")
        self.assertFalse(alarms[0].is_test)
        self.assertEqual(controls, [])

    async def test_real_bridge_threshold_recovery_turns_alarm_light_off(self):
        bridge = FakeWebSocket()
        await manager.connect_bridge(bridge, board_id="R1")

        try:
            await ingest_sensor_data({
                "board_id": "R1",
                "board_name": "greenhouse-r1",
                "data": {
                    "temp": 40.0,
                    "humi": 60.0,
                    "light": 50.0,
                    "soil": 45.0,
                },
            })
            await ingest_sensor_data({
                "board_id": "R1",
                "board_name": "greenhouse-r1",
                "data": {
                    "temp": 26.0,
                    "humi": 60.0,
                    "light": 50.0,
                    "soil": 45.0,
                },
            })
        finally:
            manager.disconnect_bridge(bridge)

        self.assertEqual(bridge.sent, [
            {"type": "control", "board_id": "R1", "command": "BLEALARM1"},
            {"type": "control", "board_id": "R1", "command": "BLEALARM0"},
        ])
        self.assertFalse(app_state.alarm_lights["R1"])

    async def test_control_log_returns_real_rows_with_pagination_and_time_filter(self):
        base_time = datetime(2026, 6, 29, 10, 0, 0)
        async with async_session() as session:
            session.add(ControlLog(
                timestamp=base_time - timedelta(hours=2),
                board_id="B",
                device="pump",
                action="off",
                source="manual",
            ))
            session.add(ControlLog(
                timestamp=base_time,
                board_id="A",
                device="pest_light",
                action="on",
                source="auto",
            ))
            await session.commit()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/control-log",
                params={
                    "board_id": "A",
                    "start": (base_time - timedelta(minutes=1)).isoformat(),
                    "page": 1,
                    "page_size": 10,
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["page_size"], 10)
        self.assertEqual(len(payload["items"]), 1)
        row = payload["items"][0]
        self.assertEqual(row["board_id"], "A")
        self.assertEqual(row["device"], "pest_light")
        self.assertEqual(row["action"], "on")
        self.assertEqual(row["source"], "auto")
        self.assertTrue(row["timestamp"].endswith("Z"))

    async def test_history_can_filter_by_board_id(self):
        async with async_session() as session:
            session.add(SensorData(
                timestamp=datetime(2026, 6, 29, 11, 0, 0),
                board_id="B",
                temp=30.0,
                humi=50.0,
                light=50.0,
                soil=40.0,
            ))
            await session.commit()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/history", params={"board_id": "B"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["board_id"], "B")
        self.assertEqual(payload["items"][0]["temp"], 30.0)

    async def test_control_accepts_board_id_and_records_it(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/control",
                json={"board_id": "A", "device": "pump", "action": "on"},
                headers=self._auth_headers,
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["board_id"], "A")

        async with async_session() as session:
            rows = (await session.execute(select(ControlLog))).scalars().all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].board_id, "A")

    async def test_control_for_unconnected_target_board_does_not_fallback_to_default_bridge(self):
        bridge_a = FakeWebSocket()
        await manager.connect_bridge(bridge_a, board_id="A")

        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/control",
                    json={"board_id": "B", "device": "pump", "action": "on"},
                    headers=self._auth_headers,
                )
        finally:
            manager.disconnect_bridge(bridge_a)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["board_id"], "B")
        self.assertFalse(payload["bridge_connected"])
        self.assertEqual(bridge_a.sent, [])

        async with async_session() as session:
            rows = (await session.execute(select(ControlLog))).scalars().all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].board_id, "B")

    def test_bridge_hello_replaces_default_registration_for_same_socket(self):
        manager.disconnect_bridge()

        with TestClient(app) as client:
            with client.websocket_connect("/ws/bridge") as ws:
                self.assertTrue(manager.has_bridge("A"))
                ws.send_json({
                    "type": "bridge_hello",
                    "board_id": "B",
                    "board_name": "greenhouse-b",
                })
                self.assertTrue(self._eventually(lambda: manager.has_bridge("B")))
                self.assertFalse(manager.has_bridge("A"))

        manager.disconnect_bridge()

    def test_sensor_data_board_id_does_not_register_control_bridge_without_hello(self):
        manager.disconnect_bridge()

        with TestClient(app) as client:
            with client.websocket_connect("/ws/bridge") as ws:
                self.assertTrue(manager.has_bridge("A"))
                ws.send_json({
                    "type": "sensor_data",
                    "board_id": "B",
                    "board_name": "greenhouse-b",
                    "data": {"temp": 25.0, "humi": 60.0, "light": 50.0, "soil": 45.0},
                })
                time.sleep(0.05)
                self.assertTrue(manager.has_bridge("A"))
                self.assertFalse(manager.has_bridge("B"))

        manager.disconnect_bridge()

    def _eventually(self, condition, timeout=1.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if condition():
                return True
            time.sleep(0.01)
        return condition()

    async def test_boards_endpoint_reports_last_seen(self):
        seen_at = datetime(2026, 6, 29, 12, 0, 0)
        async with async_session() as session:
            session.add(Board(
                board_id="A",
                board_name="greenhouse-a",
                last_seen=seen_at,
            ))
            await session.commit()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/boards")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload[0]["board_id"], "A")
        self.assertEqual(payload[0]["board_name"], "greenhouse-a")
        self.assertTrue(payload[0]["online"])
        self.assertTrue(payload[0]["last_seen"].endswith("Z"))

    async def test_alarms_include_derived_trace_fields_without_fake_status(self):
        async with async_session() as session:
            session.add(AlarmLog(
                timestamp=datetime(2026, 6, 29, 13, 0, 0),
                board_id="A",
                param_name="temperature",
                value=38.0,
                threshold=35.0,
                action="pump_off",
            ))
            await session.commit()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/alarms", params={"board_id": "A"})

        self.assertEqual(response.status_code, 200)
        row = response.json()["items"][0]
        self.assertEqual(row["board_id"], "A")
        self.assertEqual(row["param_label"], "温度")
        self.assertEqual(row["unit"], "°C")
        self.assertEqual(row["source"], "bridge")
        self.assertFalse(row["is_test"])
        self.assertIsNone(row["sensor_data_id"])
        self.assertEqual(row["direction"], "high")
        self.assertNotIn("status", row)

    async def test_alarms_source_filter_splits_real_and_test_rows(self):
        async with async_session() as session:
            session.add(AlarmLog(
                timestamp=datetime(2026, 6, 29, 13, 0, 0),
                board_id="A",
                param_name="temperature",
                value=38.0,
                threshold=35.0,
                action="pump_off",
                source="bridge",
                is_test=False,
            ))
            session.add(AlarmLog(
                timestamp=datetime(2026, 6, 29, 13, 5, 0),
                board_id="A",
                param_name="soil_moisture",
                value=12.0,
                threshold=30.0,
                action="pump_on",
                source="demo_injection",
                is_test=True,
                sensor_data_id=42,
            ))
            await session.commit()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            default_response = await client.get("/api/alarms", params={"board_id": "A"})
            real_response = await client.get("/api/alarms", params={"board_id": "A", "source": "real"})
            test_response = await client.get("/api/alarms", params={"board_id": "A", "source": "test"})

        self.assertEqual(default_response.status_code, 200)
        default_payload = default_response.json()
        self.assertEqual(default_payload["total"], 2)
        self.assertEqual(
            {row["source"] for row in default_payload["items"]},
            {"bridge", "demo_injection"},
        )

        self.assertEqual(real_response.status_code, 200)
        real_payload = real_response.json()
        self.assertEqual(real_payload["total"], 1)
        self.assertEqual(real_payload["items"][0]["source"], "bridge")
        self.assertFalse(real_payload["items"][0]["is_test"])

        self.assertEqual(test_response.status_code, 200)
        test_payload = test_response.json()
        self.assertEqual(test_payload["total"], 1)
        self.assertEqual(test_payload["items"][0]["source"], "demo_injection")
        self.assertTrue(test_payload["items"][0]["is_test"])
        self.assertEqual(test_payload["items"][0]["sensor_data_id"], 42)

    async def test_test_sensor_sample_writes_test_history_without_board_online_or_control_log(self):
        async with async_session() as session:
            session.add(Board(
                board_id="T1",
                board_name="test-board",
                last_seen=None,
            ))
            await session.commit()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/test/sensor-sample",
                json={
                    "board_id": "T1",
                    "temperature": 36.0,
                    "humidity": 75.0,
                    "light": 30.0,
                },
                headers=self._auth_headers,
            )
            history_response = await client.get(
                "/api/history",
                params={"board_id": "T1", "source": "test"},
            )
            boards_response = await client.get("/api/boards")
            alarms_response = await client.get("/api/alarms", params={"board_id": "T1"})
            control_response = await client.get("/api/control-log", params={"board_id": "T1"})

        self.assertEqual(response.status_code, 200)
        sample = response.json()
        self.assertEqual(sample["board_id"], "T1")
        self.assertEqual(sample["source"], "demo_injection")
        self.assertTrue(sample["is_test"])
        self.assertEqual(sample["temp"], 36.0)
        self.assertEqual(sample["facts"]["temp"]["value"], 36.0)

        self.assertEqual(history_response.status_code, 200)
        history = history_response.json()
        self.assertEqual(history["total"], 1)
        self.assertEqual(history["items"][0]["id"], sample["id"])
        self.assertEqual(history["items"][0]["source"], "demo_injection")
        self.assertTrue(history["items"][0]["is_test"])

        self.assertEqual(boards_response.status_code, 200)
        board = next(row for row in boards_response.json() if row["board_id"] == "T1")
        self.assertFalse(board["online"])
        self.assertIsNone(board["last_seen"])

        self.assertEqual(alarms_response.status_code, 200)
        alarms = alarms_response.json()
        self.assertEqual(alarms["total"], 1)
        alarm = alarms["items"][0]
        self.assertEqual(alarm["board_id"], "T1")
        self.assertEqual(alarm["param_name"], "temperature")
        self.assertEqual(alarm["source"], "demo_injection")
        self.assertTrue(alarm["is_test"])
        self.assertEqual(alarm["sensor_data_id"], sample["id"])

        self.assertEqual(control_response.status_code, 200)
        self.assertEqual(control_response.json()["total"], 0)

    async def test_high_temperature_test_sample_no_longer_auto_controls_pump(self):
        bridge = FakeWebSocket()
        await manager.connect_bridge(bridge, board_id="T1")

        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/test/sensor-sample",
                    json={
                        "board_id": "T1",
                        "temperature": 40.0,
                        "humidity": 60.0,
                        "light": 50.0,
                        "allow_control": True,
                    },
                    headers=self._auth_headers,
                )
                control_response = await client.get("/api/control-log", params={"board_id": "T1"})
        finally:
            manager.disconnect_bridge(bridge)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(control_response.status_code, 200)
        self.assertEqual(control_response.json()["total"], 0)
        self.assertEqual(bridge.sent, [])

    async def test_manual_mode_low_soil_only_alarms_without_auto_control(self):
        bridge = FakeWebSocket()
        await manager.connect_bridge(bridge, board_id="T1")

        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                await client.put("/api/mode", json={"mode": "manual"}, headers=self._auth_headers)
                for _ in range(3):
                    response = await client.post(
                        "/api/test/sensor-sample",
                        json={
                            "board_id": "T1",
                            "temperature": 28.0,
                            "humidity": 40.0,
                            "light": 70.0,
                            "allow_control": True,
                        },
                        headers=self._auth_headers,
                    )
                    self.assertEqual(response.status_code, 200)
                alarms_response = await client.get("/api/alarms", params={"board_id": "T1"})
                control_response = await client.get("/api/control-log", params={"board_id": "T1"})
        finally:
            manager.disconnect_bridge(bridge)

        self.assertEqual(alarms_response.status_code, 200)
        payload = alarms_response.json()
        self.assertEqual(payload["total"], 3)
        self.assertEqual(
            sorted({item["param_name"] for item in payload["items"]}),
            ["soil_moisture"],
        )
        self.assertEqual(control_response.status_code, 200)
        self.assertEqual(control_response.json()["total"], 0)
        self.assertEqual(bridge.sent, [])

    async def test_test_sensor_sample_allow_control_false_does_not_auto_control_low_soil(self):
        bridge = FakeWebSocket()
        await manager.connect_bridge(bridge, board_id="T1")

        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                for _ in range(3):
                    response = await client.post(
                        "/api/test/sensor-sample",
                        json={
                            "board_id": "T1",
                            "temperature": 28.0,
                            "humidity": 40.0,
                            "light": 70.0,
                            "allow_control": False,
                        },
                        headers=self._auth_headers,
                    )
                    self.assertEqual(response.status_code, 200)
                control_response = await client.get("/api/control-log", params={"board_id": "T1"})
        finally:
            manager.disconnect_bridge(bridge)

        self.assertEqual(control_response.status_code, 200)
        self.assertEqual(control_response.json()["total"], 0)
        self.assertEqual(bridge.sent, [])

    async def test_test_sensor_sample_three_low_soil_samples_auto_turns_pump_on(self):
        bridge = FakeWebSocket()
        await manager.connect_bridge(bridge, board_id="T1")

        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                for index in range(5):
                    response = await client.post(
                        "/api/test/sensor-sample",
                        json={
                            "board_id": "T1",
                            "temperature": 28.0,
                            "humidity": 40.0,
                            "light": 70.0,
                            "allow_control": True,
                        },
                        headers=self._auth_headers,
                    )
                    self.assertEqual(response.status_code, 200)

                    control_response = await client.get("/api/control-log", params={"board_id": "T1"})
                    expected_total = 0 if index < 4 else 1
                    self.assertEqual(control_response.json()["total"], expected_total)
                status_response = await client.get("/api/status")
        finally:
            manager.disconnect_bridge(bridge)

        self.assertEqual(status_response.status_code, 200)
        auto_state = status_response.json()["auto_watering"]["T1"]
        self.assertTrue(auto_state["active"])
        self.assertIsNotNone(auto_state["started_at"])
        self.assertIsNone(auto_state["cooldown_until"])
        self.assertEqual(bridge.sent, [{"type": "control", "board_id": "T1", "command": "BLEGLED1"}])
        async with async_session() as session:
            rows = (await session.execute(select(ControlLog))).scalars().all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].board_id, "T1")
        self.assertEqual(rows[0].device, "pump")
        self.assertEqual(rows[0].action, "on")
        self.assertEqual(rows[0].source, "auto")
        self.assertEqual(rows[0].reason, "soil_moisture_below_start")

    async def test_auto_soil_moisture_recovery_turns_pump_off_before_timeout(self):
        bridge = FakeWebSocket()
        await manager.connect_bridge(bridge, board_id="T1")

        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                await client.put(
                    "/api/control-rules/soil-moisture-pump",
                    json={
                        "enabled": True,
                        "start_below": 35.0,
                        "stop_at_or_above": 45.0,
                        "consecutive_samples": 3,
                        "max_run_sec": 10,
                        "cooldown_sec": 5,
                    },
                    headers=self._auth_headers,
                )
                for _ in range(3):
                    response = await client.post(
                        "/api/test/sensor-sample",
                        json={
                            "board_id": "T1",
                            "temperature": 28.0,
                            "humidity": 40.0,
                            "light": 70.0,
                            "allow_control": True,
                        },
                        headers=self._auth_headers,
                    )
                    self.assertEqual(response.status_code, 200)
                recovered_response = await client.post(
                    "/api/test/sensor-sample",
                    json={
                        "board_id": "T1",
                        "temperature": 22.0,
                        "humidity": 70.0,
                        "light": 20.0,
                        "allow_control": True,
                    },
                    headers=self._auth_headers,
                )
                status_response = await client.get("/api/status")
        finally:
            manager.disconnect_bridge(bridge)

        self.assertEqual(recovered_response.status_code, 200)
        self.assertEqual(bridge.sent, [
            {"type": "control", "board_id": "T1", "command": "BLEGLED1"},
            {"type": "control", "board_id": "T1", "command": "BLEKLED1"},
        ])
        auto_state = status_response.json()["auto_watering"]["T1"]
        self.assertFalse(auto_state["active"])
        self.assertIsNone(auto_state["started_at"])
        self.assertIsNotNone(auto_state["cooldown_until"])
        async with async_session() as session:
            rows = (await session.execute(select(ControlLog).order_by(ControlLog.id))).scalars().all()
        self.assertEqual([row.action for row in rows], ["on", "off"])
        self.assertEqual(rows[1].reason, "soil_moisture_recovered")

    async def test_auto_soil_moisture_max_run_turns_pump_off(self):
        bridge = FakeWebSocket()
        await manager.connect_bridge(bridge, board_id="T1")

        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                await client.put(
                    "/api/control-rules/soil-moisture-pump",
                    json={
                        "enabled": True,
                        "start_below": 35.0,
                        "stop_at_or_above": 45.0,
                        "consecutive_samples": 3,
                        "max_run_sec": 1,
                        "cooldown_sec": 2,
                    },
                    headers=self._auth_headers,
                )
                for _ in range(3):
                    response = await client.post(
                        "/api/test/sensor-sample",
                        json={
                            "board_id": "T1",
                            "temperature": 28.0,
                            "humidity": 40.0,
                            "light": 70.0,
                            "allow_control": True,
                        },
                        headers=self._auth_headers,
                    )
                    self.assertEqual(response.status_code, 200)
                await asyncio.sleep(1.1)
                status_response = await client.get("/api/status")
        finally:
            manager.disconnect_bridge(bridge)

        self.assertEqual(bridge.sent, [
            {"type": "control", "board_id": "T1", "command": "BLEGLED1"},
            {"type": "control", "board_id": "T1", "command": "BLEKLED1"},
        ])
        auto_state = status_response.json()["auto_watering"]["T1"]
        self.assertFalse(auto_state["active"])
        self.assertIsNone(auto_state["started_at"])
        self.assertIsNotNone(auto_state["cooldown_until"])
        async with async_session() as session:
            rows = (await session.execute(select(ControlLog).order_by(ControlLog.id))).scalars().all()
        self.assertEqual([row.action for row in rows], ["on", "off"])
        self.assertEqual(rows[1].reason, "max_run_time_reached")

    async def test_auto_soil_moisture_cooldown_blocks_repeated_pump_on(self):
        bridge = FakeWebSocket()
        await manager.connect_bridge(bridge, board_id="T1")

        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                await client.put(
                    "/api/control-rules/soil-moisture-pump",
                    json={
                        "enabled": True,
                        "start_below": 35.0,
                        "stop_at_or_above": 45.0,
                        "consecutive_samples": 3,
                        "max_run_sec": 10,
                        "cooldown_sec": 30,
                    },
                    headers=self._auth_headers,
                )
                low_sample = {"board_id": "T1", "temperature": 28.0, "humidity": 40.0, "light": 70.0, "allow_control": True}
                recovered_sample = {"board_id": "T1", "temperature": 22.0, "humidity": 70.0, "light": 20.0, "allow_control": True}
                for sample in [low_sample, low_sample, low_sample, recovered_sample, low_sample, low_sample, low_sample]:
                    response = await client.post("/api/test/sensor-sample", json=sample, headers=self._auth_headers)
                    self.assertEqual(response.status_code, 200)
                control_response = await client.get("/api/control-log", params={"board_id": "T1"})
        finally:
            manager.disconnect_bridge(bridge)

        self.assertEqual(bridge.sent, [
            {"type": "control", "board_id": "T1", "command": "BLEGLED1"},
            {"type": "control", "board_id": "T1", "command": "BLEKLED1"},
        ])
        self.assertEqual(control_response.status_code, 200)
        self.assertEqual(control_response.json()["total"], 2)
        async with async_session() as session:
            rows = (await session.execute(select(ControlLog).order_by(ControlLog.id))).scalars().all()
        self.assertEqual([row.reason for row in rows], [
            "soil_moisture_below_start",
            "soil_moisture_recovered",
        ])

    def test_bridge_injects_board_identity_and_filters_control_targets(self):
        payload = build_sensor_message(
            {"temp": 25.0, "humi": 60.0, "light": 50.0, "soil": 45.0},
            board_id="A",
            board_name="greenhouse-a",
        )

        self.assertEqual(payload["type"], "sensor_data")
        self.assertEqual(payload["board_id"], "A")
        self.assertEqual(payload["board_name"], "greenhouse-a")
        self.assertEqual(payload["bridge_mode"], "hardware")
        self.assertEqual(payload["data"]["temp"], 25.0)

        self.assertTrue(should_apply_control({"type": "control", "command": "BLEGLED1"}, "A"))
        self.assertTrue(should_apply_control({"type": "control", "board_id": "A", "command": "BLEGLED1"}, "A"))
        self.assertFalse(should_apply_control({"type": "control", "board_id": "B", "command": "BLEGLED1"}, "A"))

    def test_bridge_serial_payload_can_override_board_identity_from_firmware(self):
        legacy = parse_serial_payload(
            "t:25-h:60-l:800-s:45",
            default_board_id="A",
            default_board_name="greenhouse-a",
        )
        self.assertEqual(legacy["board_id"], "A")
        self.assertEqual(legacy["board_name"], "greenhouse-a")
        self.assertEqual(legacy["data"]["soil"], 45.0)

        identified = parse_serial_payload(
            "id:B-t:26-h:61-l:810-s:46",
            default_board_id="A",
            default_board_name="greenhouse-a",
        )
        self.assertEqual(identified["board_id"], "B")
        self.assertEqual(identified["board_name"], "greenhouse-b")
        self.assertEqual(identified["data"]["temp"], 26.0)

    async def test_ws_manager_routes_control_to_target_board_bridge(self):
        manager = WSManager()
        bridge_a = FakeWebSocket()
        bridge_b = FakeWebSocket()

        await manager.connect_bridge(bridge_a, board_id="A")
        await manager.connect_bridge(bridge_b, board_id="B")
        await manager.send_to_bridge({"type": "control", "board_id": "B", "command": "BLEGLED2"})

        self.assertEqual(bridge_a.sent, [])
        self.assertEqual(bridge_b.sent, [{"type": "control", "board_id": "B", "command": "BLEGLED2"}])

    async def test_auto_soil_moisture_rule_sends_command_to_target_board(self):
        bridge_a = FakeWebSocket()
        bridge_b = FakeWebSocket()
        await manager.connect_bridge(bridge_a, board_id="A")
        await manager.connect_bridge(bridge_b, board_id="B")

        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                for _ in range(5):
                    response = await client.post(
                        "/api/test/sensor-sample",
                        json={
                            "board_id": "B",
                            "temperature": 28.0,
                            "humidity": 40.0,
                            "light": 70.0,
                            "allow_control": True,
                        },
                        headers=self._auth_headers,
                    )
                    self.assertEqual(response.status_code, 200)
        finally:
            manager.disconnect_bridge(bridge_a)
            manager.disconnect_bridge(bridge_b)

        self.assertEqual(bridge_a.sent, [])
        self.assertEqual(bridge_b.sent, [{"type": "control", "board_id": "B", "command": "BLEGLED1"}])


if __name__ == "__main__":
    unittest.main()
