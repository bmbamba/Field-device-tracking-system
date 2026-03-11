"""
device_registry.py - Thread-safe store of all registered devices.
Generates TLE-style IDs: DEV-0001, DEV-0002, ...
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class DeviceRecord:
    device_id: str
    device_name: str
    device_type: str
    initial_position: tuple
    status: str = "IDLE"
    travel_plan: Optional[dict] = None
    current_x: float = 0.0
    current_y: float = 0.0
    distance_travelled: float = 0.0
    current_waypoint: int = 0
    speed: float = 0.0
    last_update: Optional[datetime] = None
    deviation: float = 0.0
    color: str = "#00FF41"
    trail: list = field(default_factory=list)


class DeviceRegistry:
    _COLORS = [
        "#00FF41", "#FF6B35", "#00D4FF", "#FFD700", "#FF4081",
        "#7CFC00", "#FF8C00", "#DA70D6", "#00CED1", "#FF6347",
    ]

    def __init__(self):
        self._lock = threading.Lock()
        self._devices: dict = {}
        self._counter = 0

    def register(self, name: str, device_type: str,
                 initial_position: tuple = (0, 0)) -> DeviceRecord:
        with self._lock:
            self._counter += 1
            dev_id = f"DEV-{self._counter:04d}"
            color = self._COLORS[(self._counter - 1) % len(self._COLORS)]
            record = DeviceRecord(
                device_id=dev_id,
                device_name=name,
                device_type=device_type,
                initial_position=initial_position,
                current_x=initial_position[0],
                current_y=initial_position[1],
                color=color,
            )
            self._devices[dev_id] = record
            return record

    def get(self, device_id: str) -> Optional[DeviceRecord]:
        with self._lock:
            return self._devices.get(device_id)

    def all_devices(self) -> list:
        with self._lock:
            return list(self._devices.values())

    def update_telemetry(self, device_id: str, telemetry: dict, deviation: float = 0.0):
        with self._lock:
            rec = self._devices.get(device_id)
            if rec is None:
                return
            rec.current_x = telemetry.get("x", rec.current_x)
            rec.current_y = telemetry.get("y", rec.current_y)
            rec.distance_travelled = telemetry.get("distance", rec.distance_travelled)
            rec.current_waypoint = telemetry.get("current_waypoint", rec.current_waypoint)
            rec.speed = telemetry.get("speed", rec.speed)
            rec.deviation = deviation
            rec.last_update = datetime.now()
            rec.status = telemetry.get("status", "ONLINE")
            rec.trail.append((rec.current_x, rec.current_y))
            if len(rec.trail) > 200:
                rec.trail.pop(0)

    def set_travel_plan(self, device_id: str, plan: dict):
        with self._lock:
            rec = self._devices.get(device_id)
            if rec:
                rec.travel_plan = plan

    def remove(self, device_id: str):
        with self._lock:
            self._devices.pop(device_id, None)
