"""
sound_engine.py - Alert sounds using winsound (Windows built-in).
"""

import os, sys, threading, time

ALERT_SOUNDS = {
    "DEST_CHANGE": "alert_dest_change.wav",
    "WRONG_DEST":  "alert_dest_change.wav",
    "GEOFENCE":    "alert_geofence.wav",
    "DEVIATION":   "alert_deviation.wav",
    "SPEED_STOP":  "alert_speed.wav",
    "SPEED_SPIKE": "alert_speed.wav",
    "ARRIVED":     "alert_arrived.wav",
}

_muted      = False
_cooldown   = {}
_COOLDOWN_S = 3.0
_base_dir   = os.path.dirname(os.path.abspath(__file__))


def set_muted(muted: bool):
    global _muted
    _muted = muted


def play(alert_type: str, device_id: str = ""):
    """Play alert sound. Non-blocking. Safe to call from any thread."""
    if _muted:
        return
    now = time.monotonic()
    if _cooldown.get(alert_type, 0) + _COOLDOWN_S > now:
        return
    _cooldown[alert_type] = now

    wav_name = ALERT_SOUNDS.get(alert_type)
    if not wav_name:
        return

    # Build absolute Windows path with backslashes
    path = os.path.normpath(os.path.join(_base_dir, wav_name))
    if not os.path.isfile(path):
        return

    # Use a non-daemon thread so winsound isn't killed mid-play
    t = threading.Thread(target=_play, args=(path,), daemon=False)
    t.start()


def _play(path: str):
    try:
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(
                path,
                winsound.SND_FILENAME | winsound.SND_NODEFAULT | winsound.SND_NOSTOP
            )
        elif sys.platform == "darwin":
            os.system(f'afplay "{path}"')
        else:
            if os.system(f'paplay "{path}" 2>/dev/null') != 0:
                os.system(f'aplay -q "{path}" 2>/dev/null')
    except Exception:
        pass
