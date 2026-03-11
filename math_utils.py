"""
math_utils.py - Geometry helpers for route deviation calculations.
"""

import math


def distance(p1: tuple, p2: tuple) -> float:
    return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)


def point_to_segment_distance(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq == 0:
        return distance((px, py), (ax, ay))
    t = ((px - ax) * dx + (py - ay) * dy) / seg_len_sq
    t = max(0.0, min(1.0, t))
    return distance((px, py), (ax + t * dx, ay + t * dy))


def route_deviation(position: tuple, waypoints: list) -> float:
    if len(waypoints) < 2:
        return 0.0
    min_dist = float("inf")
    for i in range(len(waypoints) - 1):
        ax, ay = waypoints[i]
        bx, by = waypoints[i + 1]
        d = point_to_segment_distance(position[0], position[1], ax, ay, bx, by)
        if d < min_dist:
            min_dist = d
    return min_dist
