"""
protocol.py - Shared message protocol.
Length-prefixed JSON over TCP.
"""

import json
import struct

MSG_REGISTER    = "REGISTER"
MSG_TRAVEL_PLAN = "TRAVEL_PLAN"
MSG_TELEMETRY   = "TELEMETRY"
MSG_ACK         = "ACK"
MSG_ALERT       = "ALERT"
MSG_DISCONNECT  = "DISCONNECT"

STATUS_ONLINE  = "ONLINE"
STATUS_OFFLINE = "OFFLINE"
STATUS_ALERT   = "ALERT"
STATUS_IDLE    = "IDLE"


def encode_message(msg_type: str, payload: dict) -> bytes:
    envelope = {"type": msg_type, "payload": payload}
    data = json.dumps(envelope).encode("utf-8")
    length = struct.pack(">I", len(data))
    return length + data


def decode_message(data: bytes) -> tuple:
    envelope = json.loads(data.decode("utf-8"))
    return envelope["type"], envelope["payload"]


def recv_message(sock):
    header = _recv_exactly(sock, 4)
    if header is None:
        return None
    length = struct.unpack(">I", header)[0]
    body = _recv_exactly(sock, length)
    if body is None:
        return None
    return decode_message(body)


def _recv_exactly(sock, n: int):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf
