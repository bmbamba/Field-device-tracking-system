"""
route_planner.py - Builds travel plan dictionaries.
"""


def make_plan(start: tuple, waypoints: list, destination: tuple,
              report_interval: float = 2.0, speed: float = 2.0) -> dict:
    return {
        "start": list(start),
        "waypoints": [list(wp) for wp in waypoints],
        "destination": list(destination),
        "report_interval": report_interval,
        "speed": speed,
    }


def all_points(plan: dict) -> list:
    pts = [tuple(plan["start"])]
    pts += [tuple(wp) for wp in plan.get("waypoints", [])]
    if plan.get("destination"):
        pts.append(tuple(plan["destination"]))
    return pts
