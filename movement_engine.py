"""
movement_engine.py - Simulates smooth movement along a travel plan.
Ticks every 0.1s for fluid animation. Calls telemetry_cb at report_interval.
"""

import time
import threading
import math


def _distance(p1, p2):
    return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)


class MovementEngine:
    def __init__(self, device_id: str, travel_plan: dict,
                 telemetry_cb, on_complete_cb=None):
        self.device_id = device_id
        self.plan = travel_plan
        self._telemetry_cb = telemetry_cb
        self._on_complete = on_complete_cb

        self._waypoints = self._build_waypoints()
        self._wp_index = 0

        start = travel_plan.get("start", [0, 0])
        self._x = float(start[0])
        self._y = float(start[1])

        self._speed = float(travel_plan.get("speed", 2.0))
        self._report_interval = float(travel_plan.get("report_interval", 2.0))
        self._distance_travelled = 0.0
        self._last_report_time = time.time()

        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _build_waypoints(self):
        pts = []
        for wp in self.plan.get("waypoints", []):
            pts.append((float(wp[0]), float(wp[1])))
        dest = self.plan.get("destination")
        if dest:
            pts.append((float(dest[0]), float(dest[1])))
        return pts

    def _loop(self):
        dt = 0.1
        while self._running:
            if self._wp_index >= len(self._waypoints):
                if self._on_complete:
                    self._on_complete()
                self._running = False
                break

            target = self._waypoints[self._wp_index]
            dist_to_target = _distance((self._x, self._y), target)
            step = self._speed * dt

            if step >= dist_to_target:
                self._distance_travelled += dist_to_target
                self._x, self._y = target
                self._wp_index += 1
            else:
                dx = target[0] - self._x
                dy = target[1] - self._y
                ratio = step / dist_to_target
                self._x += dx * ratio
                self._y += dy * ratio
                self._distance_travelled += step

            now = time.time()
            if now - self._last_report_time >= self._report_interval:
                self._send_telemetry()
                self._last_report_time = now

            time.sleep(dt)

        self._send_telemetry(status="ARRIVED")

    def _send_telemetry(self, status="ONLINE"):
        from datetime import datetime
        payload = {
            "device_id": self.device_id,
            "x": round(self._x, 4),
            "y": round(self._y, 4),
            "distance": round(self._distance_travelled, 4),
            "current_waypoint": self._wp_index,
            "speed": self._speed,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
        try:
            self._telemetry_cb(payload)
        except Exception:
            pass
