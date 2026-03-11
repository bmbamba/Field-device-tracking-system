"""
communication_client.py - TCP client for the device side.
Connects to the tracking server, registers, and sends/receives messages.
"""

import socket
import threading
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from protocol import (
    recv_message, encode_message,
    MSG_REGISTER, MSG_TELEMETRY, MSG_ACK, MSG_TRAVEL_PLAN, MSG_DISCONNECT
)

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9000


class DeviceClient:
    def __init__(self, device_id=None, device_name="Unknown", device_type="FIELD_UNIT"):
        self.device_id = device_id
        self.device_name = device_name
        self.device_type = device_type
        self.on_travel_plan = None
        self._sock = None
        self._connected = False

    def connect(self, host=SERVER_HOST, port=SERVER_PORT) -> bool:
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.connect((host, port))
            self._connected = True
            print(f"[{self.device_name}] Connected to {host}:{port}")
            self._sock.sendall(encode_message(MSG_REGISTER, {
                "device_id":   self.device_id,
                "device_name": self.device_name,
                "device_type": self.device_type,
            }))
            t = threading.Thread(target=self._recv_loop, daemon=True)
            t.start()
            return True
        except Exception as e:
            print(f"[{self.device_name}] Connection failed: {e}")
            return False

    def disconnect(self):
        if self._sock and self._connected:
            try:
                self._sock.sendall(encode_message(MSG_DISCONNECT,
                                                   {"device_id": self.device_id}))
            except Exception:
                pass
            self._sock.close()
        self._connected = False

    def send_telemetry(self, payload: dict):
        if not self._connected or not self._sock:
            return
        try:
            self._sock.sendall(encode_message(MSG_TELEMETRY, payload))
        except Exception as e:
            print(f"[{self.device_name}] Send error: {e}")
            self._connected = False

    def _recv_loop(self):
        while self._connected:
            try:
                result = recv_message(self._sock)
                if result is None:
                    print(f"[{self.device_name}] Server disconnected.")
                    self._connected = False
                    break
                msg_type, payload = result
                if msg_type == MSG_ACK:
                    self.device_id = payload.get("device_id", self.device_id)
                    print(f"[{self.device_name}] Registered as {self.device_id}")
                elif msg_type == MSG_TRAVEL_PLAN:
                    print(f"[{self.device_name}] Travel plan received.")
                    if self.on_travel_plan:
                        self.on_travel_plan(payload)
            except Exception as e:
                print(f"[{self.device_name}] Recv error: {e}")
                self._connected = False
                break
