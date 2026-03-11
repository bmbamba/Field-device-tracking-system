"""
tracker_engine.py - Enhanced tracking with:
  - Route deviation alerts
  - Destination change detection
  - Speed change alerts (sudden stop / acceleration)
  - Geofence breach alerts
  - Arrival detection
"""

import math
from math_utils import route_deviation, distance
from device_registry import DeviceRegistry
import logger

DEVIATION_THRESHOLD  = 3.0
ARRIVAL_THRESHOLD    = 1.5
SPEED_SPIKE_FACTOR   = 2.5    # alert if speed jumps by this multiplier
SPEED_DROP_THRESHOLD = 0.2    # alert if speed drops to near zero mid-journey


class TrackerEngine:
    def __init__(self, registry: DeviceRegistry, alert_callback=None):
        self.registry = registry
        self.alert_callback = alert_callback
        self._prev_speed: dict = {}     # device_id -> last known speed
        self._geofences: list = []      # list of (x1,y1,x2,y2,label)
        self._inside_fence: dict = {}   # device_id -> set of fence indices inside

    def add_geofence(self, x1, y1, x2, y2, label="EXCLUSION ZONE"):
        self._geofences.append((min(x1,x2), min(y1,y2),
                                max(x1,x2), max(y1,y2), label))

    def clear_geofences(self):
        self._geofences.clear()
        self._inside_fence.clear()

    # ── Main entry ────────────────────────────────────────────────────

    def process_telemetry(self, device_id: str, telemetry: dict):
        rec = self.registry.get(device_id)
        if rec is None:
            logger.warning(f"Telemetry from unknown device: {device_id}")
            return

        position = (telemetry.get("x", 0), telemetry.get("y", 0))
        deviation = 0.0

        # 1. Destination change
        new_dest = telemetry.get("new_destination")
        if new_dest and rec.travel_plan:
            old_dest = rec.travel_plan.get("destination")
            if old_dest and tuple(new_dest) != tuple(old_dest):
                self._handle_destination_change(rec, old_dest, new_dest)

        # 2. Route deviation
        if rec.travel_plan:
            wps = self._plan_to_waypoints(rec.travel_plan)
            if len(wps) >= 2:
                deviation = route_deviation(position, wps)

        # 3. Update registry
        self.registry.update_telemetry(device_id, telemetry, deviation)

        # 4. Deviation alert
        if deviation > DEVIATION_THRESHOLD:
            logger.warning(
                f"DEVIATION ALERT: {device_id} is {deviation:.2f} units "
                f"off-route at ({position[0]:.1f},{position[1]:.1f})"
            )
            rec.status = "ALERT"
            self._fire(device_id, "DEVIATION", f"{deviation:.2f} units off-route")
        else:
            logger.debug(f"OK {device_id} pos=({position[0]:.1f},{position[1]:.1f}) dev={deviation:.2f}")

        # 5. Speed change
        self._check_speed(device_id, rec, telemetry)

        # 6. Geofence
        self._check_geofence(device_id, rec, position)

        # 7. Arrival
        if telemetry.get("status") == "ARRIVED":
            self._handle_arrival(rec, position)

    # ── Destination change ────────────────────────────────────────────

    def _handle_destination_change(self, rec, old_dest, new_dest):
        old_s = f"({old_dest[0]:.1f},{old_dest[1]:.1f})"
        new_s = f"({new_dest[0]:.1f},{new_dest[1]:.1f})"
        logger.warning(
            f"DESTINATION CHANGE: {rec.device_id} [{rec.device_name}] "
            f"{old_s} -> {new_s}"
        )
        rec.travel_plan["destination"] = list(new_dest)
        rec.status = "ALERT"
        self._fire(rec.device_id, "DEST_CHANGE", f"Was {old_s} -> Now {new_s}")

    # ── Speed alerts ──────────────────────────────────────────────────

    def _check_speed(self, device_id, rec, telemetry):
        current_speed = telemetry.get("speed", 0)
        prev = self._prev_speed.get(device_id)

        if prev is not None and prev > 0.5:
            # Sudden stop mid-journey
            if current_speed < SPEED_DROP_THRESHOLD and rec.status not in ("ARRIVED",):
                logger.warning(
                    f"SPEED ALERT: {device_id} [{rec.device_name}] "
                    f"suddenly stopped (was {prev:.1f}, now {current_speed:.1f})"
                )
                self._fire(device_id, "SPEED_STOP",
                           f"Stopped unexpectedly (was {prev:.1f} u/s)")

            # Sudden acceleration
            elif current_speed > prev * SPEED_SPIKE_FACTOR and current_speed > 2:
                logger.warning(
                    f"SPEED ALERT: {device_id} [{rec.device_name}] "
                    f"accelerated sharply ({prev:.1f} -> {current_speed:.1f})"
                )
                self._fire(device_id, "SPEED_SPIKE",
                           f"Speed jumped {prev:.1f} -> {current_speed:.1f} u/s")

        self._prev_speed[device_id] = current_speed

    # ── Geofence ──────────────────────────────────────────────────────

    def _check_geofence(self, device_id, rec, position):
        if not self._geofences:
            return
        px, py = position
        inside_now = set()
        for i, (x1, y1, x2, y2, label) in enumerate(self._geofences):
            if x1 <= px <= x2 and y1 <= py <= y2:
                inside_now.add(i)

        prev_inside = self._inside_fence.get(device_id, set())

        # Entered new zone
        for i in inside_now - prev_inside:
            _, _, _, _, label = self._geofences[i]
            logger.warning(
                f"GEOFENCE BREACH: {device_id} [{rec.device_name}] "
                f"entered '{label}' at ({px:.1f},{py:.1f})"
            )
            rec.status = "ALERT"
            self._fire(device_id, "GEOFENCE",
                       f"Entered '{label}' at ({px:.1f},{py:.1f})")

        # Left a zone
        for i in prev_inside - inside_now:
            _, _, _, _, label = self._geofences[i]
            logger.info(
                f"GEOFENCE CLEAR: {device_id} [{rec.device_name}] "
                f"exited '{label}'"
            )

        self._inside_fence[device_id] = inside_now

    # ── Arrival ───────────────────────────────────────────────────────

    def _handle_arrival(self, rec, position):
        planned = rec.travel_plan.get("destination") if rec.travel_plan else None
        if not planned:
            return
        dist = distance(position, tuple(planned))
        if dist <= ARRIVAL_THRESHOLD:
            logger.info(
                f"ARRIVED: {rec.device_id} [{rec.device_name}] reached "
                f"({planned[0]:.1f},{planned[1]:.1f})"
            )
            rec.status = "ARRIVED"
            self._fire(rec.device_id, "ARRIVED",
                       f"({planned[0]:.1f},{planned[1]:.1f})")
        else:
            logger.warning(
                f"WRONG DESTINATION: {rec.device_id} stopped at "
                f"({position[0]:.1f},{position[1]:.1f}), "
                f"{dist:.1f} units from planned dest"
            )
            rec.status = "ALERT"
            self._fire(rec.device_id, "WRONG_DEST",
                       f"Stopped {dist:.1f} units from planned destination")

    # ── Helpers ───────────────────────────────────────────────────────

    def _fire(self, device_id, alert_type, detail):
        if self.alert_callback:
            self.alert_callback(device_id, alert_type, detail)

    def _plan_to_waypoints(self, plan):
        pts = [tuple(plan.get("start", [0, 0]))]
        for wp in plan.get("waypoints", []):
            pts.append(tuple(wp))
        dest = plan.get("destination")
        if dest:
            pts.append(tuple(dest))
        return pts
