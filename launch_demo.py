"""
launch_demo.py - Launches 3 simulated devices with built-in demo plans.
Run this AFTER starting main.py (the GUI).

    py launch_demo.py
"""

import threading
import time
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from device_simulator import DeviceSimulator

DEVICES = [
    {"id": "DEV-0001", "name": "Alpha",   "type": "UAV"},
    {"id": "DEV-0002", "name": "Bravo",   "type": "GROUND_VEHICLE"},
    {"id": "DEV-0003", "name": "Charlie", "type": "SENSOR_NODE"},
]


def run_device(cfg):
    DeviceSimulator(cfg["id"], cfg["name"], cfg["type"], auto_plan=True).run()


if __name__ == "__main__":
    print("=" * 55)
    print("  TRACKING SYSTEM — DEMO LAUNCHER")
    print("  Make sure py main.py is already running!")
    print("=" * 55)

    threads = []
    for cfg in DEVICES:
        t = threading.Thread(target=run_device, args=(cfg,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.5)

    print("\n3 devices launched. Press Ctrl+C to stop.\n")
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\nStopped.")
