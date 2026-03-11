"""
communication_server.py - TCP server. Accepts device connections and dispatches telemetry.
"""

import socket
import threading

from protocol import (
    recv_message, encode_message,
    MSG_REGISTER, MSG_TELEMETRY, MSG_DISCONNECT, MSG_ACK, MSG_TRAVEL_PLAN
)
from device_registry import DeviceRegistry
from tracker_engine import TrackerEngine
import logger

HOST = "127.0.0.1"
PORT = 9000


class CommunicationServer:
    def __init__(self, registry: DeviceRegistry, tracker: TrackerEngine):
        self.registry = registry
        self.tracker = tracker
        self._server_sock = None
        self._running = False
        self._client_sockets: dict = {}
        self._lock = threading.Lock()

    def start(self):
        self._running = True
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((HOST, PORT))
        self._server_sock.listen(20)
        self._server_sock.settimeout(1.0)
        logger.info(f"TCP server listening on {HOST}:{PORT}")
        t = threading.Thread(target=self._accept_loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False
        if self._server_sock:
            self._server_sock.close()
        logger.info("TCP server stopped.")

    def _accept_loop(self):
        while self._running:
            try:
                conn, addr = self._server_sock.accept()
                logger.info(f"New connection from {addr}")
                t = threading.Thread(target=self._handle_client,
                                     args=(conn, addr), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _handle_client(self, conn: socket.socket, addr):
        device_id = None
        try:
            while self._running:
                result = recv_message(conn)
                if result is None:
                    logger.info(f"Connection closed by {addr}")
                    break
                msg_type, payload = result
                if msg_type == MSG_REGISTER:
                    device_id = self._handle_register(conn, payload)
                elif msg_type == MSG_TELEMETRY:
                    self._handle_telemetry(payload)
                elif msg_type == MSG_DISCONNECT:
                    logger.info(f"Device {payload.get('device_id')} disconnected.")
                    break
        except Exception as e:
            logger.error(f"Error handling {addr}: {e}")
        finally:
            conn.close()
            if device_id:
                rec = self.registry.get(device_id)
                if rec:
                    rec.status = "OFFLINE"
                with self._lock:
                    self._client_sockets.pop(device_id, None)
                logger.info(f"Device {device_id} is now OFFLINE.")

    def _handle_register(self, conn: socket.socket, payload: dict) -> str:
        requested_id = payload.get("device_id")
        device_name  = payload.get("device_name", "Unknown")
        device_type  = payload.get("device_type", "FIELD_UNIT")

        if requested_id and self.registry.get(requested_id):
            rec = self.registry.get(requested_id)
            rec.status = "ONLINE"
            device_id = requested_id
        else:
            rec = self.registry.register(device_name, device_type)
            device_id = rec.device_id

        with self._lock:
            self._client_sockets[device_id] = conn

        logger.info(f"Device registered: {device_id} ({device_name} / {device_type})")
        conn.sendall(encode_message(MSG_ACK, {
            "device_id": device_id,
            "message": "Registration successful"
        }))

        if rec and rec.travel_plan:
            self.push_travel_plan(device_id, rec.travel_plan)

        return device_id

    def _handle_telemetry(self, payload: dict):
        device_id = payload.get("device_id")
        if device_id:
            self.tracker.process_telemetry(device_id, payload)

    def push_travel_plan(self, device_id: str, plan: dict):
        with self._lock:
            conn = self._client_sockets.get(device_id)
        if conn is None:
            logger.warning(f"Cannot push plan to {device_id}: not connected.")
            return
        try:
            conn.sendall(encode_message(MSG_TRAVEL_PLAN, plan))
            logger.info(f"Travel plan sent to {device_id}")
        except Exception as e:
            logger.error(f"Failed to send plan to {device_id}: {e}")
