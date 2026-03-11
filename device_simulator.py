"""
device_simulator.py - Field device simulator with live destination changing.

The device travels its assigned route but after --divert-after seconds it
automatically announces a new destination. You will see the alert fire live
in the control center GUI.

Usage examples
--------------
# Normal journey — no diversion:
    py device_simulator.py --id DEV-0001 --name TOYOTA --type GROUND_VEHICLE

# Divert to (45,45) after 10 seconds of travel:
    py device_simulator.py --id DEV-0001 --name TOYOTA --type GROUND_VEHICLE --newdest 45,45 --divert-after 10

# Divert AND drift off-route (triggers deviation alert too):
    py device_simulator.py --id DEV-0001 --name TOYOTA --type GROUND_VEHICLE --newdest 45,45 --divert-after 10 --drift
"""

import argparse
import time
import threading
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from communication_client import DeviceClient
from movement_engine import MovementEngine

DEMO_PLANS = {
    "DEV-0001": {
        "start": [0, 0], "waypoints": [[10, 5], [15, 10], [20, 15]],
        "destination": [25, 20], "report_interval": 2.0, "speed": 3.0,
    },
    "DEV-0002": {
        "start": [50, 0], "waypoints": [[40, 8], [30, 12], [20, 18]],
        "destination": [10, 25], "report_interval": 2.0, "speed": 2.5,
    },
    "DEV-0003": {
        "start": [25, 0], "waypoints": [[25, 10], [15, 20], [10, 30]],
        "destination": [5, 40], "report_interval": 2.0, "speed": 2.0,
    },
}


class DeviceSimulator:
    def __init__(self, device_id, device_name, device_type,
                 auto_plan=False, new_destination=None,
                 divert_after=10.0, drift=False):
        self.device_id       = device_id
        self.device_name     = device_name
        self.device_type     = device_type
        self.auto_plan       = auto_plan
        self.new_destination = new_destination   # (x, y) to divert to, or None
        self.divert_after    = divert_after      # seconds after movement starts
        self.drift           = drift             # if True, also drift off-route

        self._client = DeviceClient(device_id, device_name, device_type)
        self._plan_event = threading.Event()
        self._plan = None
        self._engine = None
        self._dest_announced = False
        self._move_start_time = None

    # ------------------------------------------------------------------

    def run(self):
        print(f"[{self.device_name}] Starting simulator...")
        self._client.on_travel_plan = self._on_plan_received

        connected = False
        for attempt in range(10):
            if self._client.connect():
                connected = True
                break
            print(f"[{self.device_name}] Retry {attempt+1}/10 in 3s...")
            time.sleep(3)

        if not connected:
            print(f"[{self.device_name}] Could not connect. Exiting.")
            return

        if self.auto_plan:
            plan = DEMO_PLANS.get(self._client.device_id) or DEMO_PLANS.get(self.device_id)
            if plan:
                self._on_plan_received(plan)

        print(f"[{self.device_name}] Waiting for travel plan...")
        self._plan_event.wait(timeout=120)

        if not self._plan:
            print(f"[{self.device_name}] No plan received. Exiting.")
            self._client.disconnect()
            return

        self._move_start_time = time.time()

        self._engine = MovementEngine(
            device_id=self._client.device_id,
            travel_plan=self._plan,
            telemetry_cb=self._on_send_telemetry,
            on_complete_cb=self._on_complete,
        )
        self._engine.start()

        if self.new_destination:
            # Launch a timer thread that fires the diversion after N seconds
            t = threading.Thread(target=self._divert_timer, daemon=True)
            t.start()

        print(f"[{self.device_name}] Moving... "
              + (f"Will divert to {self.new_destination} in {self.divert_after}s"
                 if self.new_destination else ""))

        self._engine._thread.join()
        self._client.disconnect()

    # ------------------------------------------------------------------
    # Divert timer — fires after divert_after seconds
    # ------------------------------------------------------------------

    def _divert_timer(self):
        time.sleep(self.divert_after)
        if self._dest_announced:
            return

        new_x, new_y = self.new_destination
        self._dest_announced = True

        print(f"\n[{self.device_name}] *** DIVERTING to ({new_x},{new_y}) ***\n")

        # Re-route the movement engine to drive to the new destination
        if self._engine:
            self._engine._waypoints = [(float(new_x), float(new_y))]
            self._engine._wp_index  = 0

            if self.drift:
                # Add a sideways offset to also trigger a deviation alert
                self._engine._x += 5.0
                self._engine._y += 5.0
                print(f"[{self.device_name}] Also drifting off-route by 5 units")

    # ------------------------------------------------------------------
    # Telemetry intercept — inject new_destination once after diversion
    # ------------------------------------------------------------------

    def _on_send_telemetry(self, payload: dict):
        elapsed = time.time() - self._move_start_time if self._move_start_time else 0

        # Announce the destination change in the FIRST telemetry after divert_after
        if (self.new_destination
                and self._dest_announced
                and "new_destination" not in payload):
            # Only inject it once — first telemetry after the diversion
            payload["new_destination"] = list(self.new_destination)
            print(f"[{self.device_name}] Sending destination change in telemetry: "
                  f"{self.new_destination}")

        self._client.send_telemetry(payload)

    # ------------------------------------------------------------------

    def _on_plan_received(self, plan: dict):
        self._plan = plan
        self._plan_event.set()
        print(f"[{self.device_name}] Plan received. Destination: {plan.get('destination')}")

    def _on_complete(self):
        print(f"[{self.device_name}] Destination reached.")


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Field Device Simulator")
    parser.add_argument("--id",           default=None)
    parser.add_argument("--name",         default="Field Unit")
    parser.add_argument("--type",         default="FIELD_UNIT")
    parser.add_argument("--auto",         action="store_true",
                        help="Use built-in demo plan")
    parser.add_argument("--newdest",      default=None,
                        help="New destination to divert to, format: x,y  e.g. 45,45")
    parser.add_argument("--divert-after", type=float, default=10.0,
                        help="Seconds of travel before diverting (default: 10)")
    parser.add_argument("--drift",        action="store_true",
                        help="Also jump off-route when diverting (triggers deviation alert too)")
    args = parser.parse_args()

    new_dest = None
    if args.newdest:
        try:
            x, y = args.newdest.split(",")
            new_dest = (float(x), float(y))
        except (ValueError, IndexError):
            print(f"Invalid --newdest '{args.newdest}'. Use format x,y e.g. 45,45")
            sys.exit(1)

    DeviceSimulator(
        device_id=args.id,
        device_name=args.name,
        device_type=args.type,
        auto_plan=args.auto,
        new_destination=new_dest,
        divert_after=args.divert_after,
        drift=args.drift,
    ).run()


if __name__ == "__main__":
    main()
