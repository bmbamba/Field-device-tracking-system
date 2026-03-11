# Field Device Tracking System
### SCADA-Style Real-Time Monitoring Platform

A professional device tracking system built with **Python 3** and **PySide6**,
resembling satellite tracking software / SCADA monitoring systems.

---

## Architecture

```
tracking_system/
├── client/
│   ├── main.py                 ← Run this first (GUI entry point)
│   ├── main_window.py          ← SCADA main window (PySide6)
│   ├── grid_map_widget.py      ← Custom QPainter 2D map
│   ├── device_registry.py      ← Device store (thread-safe)
│   ├── tracker_engine.py       ← Deviation detection logic
│   ├── communication_server.py ← TCP server for device connections
│   ├── route_planner.py        ← Travel plan builder
│   └── logger.py               ← File + in-memory logging
├── device/
│   ├── device_simulator.py     ← Standalone device simulator
│   ├── movement_engine.py      ← Smooth waypoint movement
│   └── communication_client.py ← TCP client for devices
├── common/
│   ├── protocol.py             ← Length-prefixed JSON over TCP
│   └── math_utils.py           ← Route deviation geometry
├── launch_demo.py              ← Launches 3 demo devices at once
└── README.md
```

---

## Requirements

```bash
pip install PySide6
```

Python 3.10+ recommended (uses `X | Y` union type hints).

---

## Quick Start — 3-Device Demo

### Step 1 — Start the Client GUI
```bash
cd tracking_system
python client/main.py
```

The dark SCADA window will open. The TCP server starts automatically on
`127.0.0.1:9000`.

### Step 2 — Register 3 devices in the GUI

In the **LEFT PANEL → DEVICE REGISTRATION**:

| Field | Device 1 | Device 2 | Device 3 |
|-------|----------|----------|----------|
| Name  | Alpha    | Bravo    | Charlie  |
| Type  | UAV      | GROUND_VEHICLE | SENSOR_NODE |

Click **► REGISTER DEVICE** for each one.

This creates IDs `DEV-0001`, `DEV-0002`, `DEV-0003`.

### Step 3 — Launch the demo devices
In a **new terminal**:
```bash
cd tracking_system
python launch_demo.py
```

The 3 simulated devices connect automatically, receive their built-in demo
travel plans, and start moving. Watch them on the live map!

---

## Manual Device Launch

```bash
# Single device with a specific ID
python device/device_simulator.py --id DEV-0001 --name Alpha --type UAV --auto

# Without --auto the device waits for you to assign a plan in the GUI
python device/device_simulator.py --name Bravo --type GROUND_VEHICLE
```

---

## Assigning Travel Plans via GUI

1. Select a device from the dropdown in **TRAVEL PLAN EDITOR**
2. Set Start X/Y, waypoints, destination, speed, and report interval
3. Click **► ASSIGN TRAVEL PLAN**

Waypoints format: `x1,y1; x2,y2; x3,y3`

Example: `10,5; 15,10; 20,15`

---

## Built-in Demo Travel Plans

| Device   | Start  | Waypoints              | Destination | Speed |
|----------|--------|------------------------|-------------|-------|
| DEV-0001 | (0,0)  | (10,5) (15,10) (20,15) | (25,20)     | 3.0   |
| DEV-0002 | (50,0) | (40,8) (30,12) (20,18) | (10,25)     | 2.5   |
| DEV-0003 | (25,0) | (25,10) (15,20) (10,30)| (5,40)      | 2.0   |

---

## Communication Protocol

All messages use **length-prefixed JSON over TCP**:

```
[4-byte big-endian length] [UTF-8 JSON body]
```

### Message Types

| Type          | Direction       | Purpose                  |
|---------------|-----------------|--------------------------|
| REGISTER      | Device → Server | Initial connection       |
| ACK           | Server → Device | Confirm registration     |
| TRAVEL_PLAN   | Server → Device | Assign movement plan     |
| TELEMETRY     | Device → Server | Position update          |
| DISCONNECT    | Device → Server | Clean shutdown           |

### Telemetry Example

```json
{
  "device_id": "DEV-0001",
  "x": 12.345,
  "y": 8.910,
  "distance": 32.5,
  "current_waypoint": 1,
  "speed": 3.0,
  "status": "ONLINE",
  "timestamp": "2026-03-10T12:00:00"
}
```

---

## Deviation Detection

The **TrackerEngine** computes the perpendicular distance from the device's
current position to the nearest segment on its planned route using the
formula for point-to-line-segment distance.

**Threshold**: 3.0 grid units

- Distance > 3.0 → `ALERT` status (red on map, logged to file)
- Distance 1.5–3.0 → yellow deviation readout in table
- Distance < 1.5 → normal operation

---

## Log File

All events are written to `tracking_log.txt` in the project root.

Log categories: `INFO`, `WARNING`, `ERROR`, `DEBUG`

The **SYSTEM LOG CONSOLE** at the bottom of the GUI shows live colored output:
- Green = normal events
- Yellow = warnings / alerts
- Red = errors
- Dark = debug messages

---

## GUI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  ● FIELD DEVICE TRACKING SYSTEM    REAL-TIME TELEMETRY …    │
├──────────────┬──────────────────────────┬───────────────────┤
│ DEVICE REG.  │                          │  DEVICE TELEMETRY │
│ TRAVEL PLAN  │    LIVE OPERATIONAL MAP  │  ┌───────────────┐ │
│ SERVER CTRL  │    (GridMapWidget)       │  │ Table: ID/X/Y │ │
│              │    QPainter 2D Grid      │  │ Dest/Dev/Stat │ │
│              │    Routes & Trails       │  └───────────────┘ │
│              │    Animated Markers      │                   │
├──────────────┴──────────────────────────┴───────────────────┤
│  SYSTEM LOG CONSOLE  (color-coded, auto-scroll)             │
└─────────────────────────────────────────────────────────────┘
```
