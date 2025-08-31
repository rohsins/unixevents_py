import os
import json
import socket
import threading
import time
import asyncio
from typing import Dict, Callable, Any, Optional
from collections import defaultdict
from enum import Enum


class Role(Enum):
    SERVER = 'server'
    CLIENT = 'client'


def UnixEventsError(Exception):
    print("Exception:", Exception)
    return Exception
    # pass


class Linker:
    PROTOCOL_VERSION = 1
    MESSAGE_DELIMITER = b';;'
    MAX_MESSAGE_SIZE = 1024 * 1024  # 1MB max message size

    def __init__(self, role: Optional[str] = None, channel: Optional[str] = None):
        self._role = None
        self._channel = None
        self._socket = None
        self._socket_path = None
        self._listener_thread = None
        self._running = False
        self._initialized = False
        self._event_handlers: Dict[str, list] = defaultdict(list)
        self._once_handlers: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
        self._receive_buffer = b''
        self._debug = False

        # Initialize if both parameters provided
        if role and channel:
            self._init_sync(role, channel)

    def enable_debug(self):
        self._debug = True

    def disable_debug(self):
        self._debug = False

    def log(self, *args):
        if self._debug:
            print(*args)

    def _init_sync(self, role: str, channel: str) -> bool:
        try:
            if role.lower() not in ['server', 'client']:
                raise UnixEventsError(f"Invalid role: {role}. Must be 'server' or 'client'")

            self._role = Role(role.lower())
            self._channel = channel
            self._running = True

            self._socket_path = (
                f"/tmp/{self._channel}.sock" if os.name != "nt"
                else f"\\\\.\\pipe\\{os.environ.get('TMP')}\\{self._channel}.sock"
            )

            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

            if self._role == Role.SERVER:
                if os.path.exists(self._socket_path):
                    # raise UnixEventsError(f"The channel name |{self._channel}| is already in use, choose a different channel name.")
                    os.unlink(self._socket_path)

                self._socket.bind(self._socket_path)
                self._socket.listen(5)

                self.log(f"Server listening on {self._socket_path}")

                self._start_server()

            else:
                max_retries = 10
                retry_delay = 0.1

                for i in range(max_retries):
                    try:
                        self._socket.connect(str(self._socket_path))
                        self.log(f"Client connected to {self._socket_path}")
                        break
                    except (FileNotFoundError, ConnectionRefusedError):
                        if i < max_retries - 1:
                            time.sleep(retry_delay)
                            retry_delay = min(retry_delay * 1.5, 2.0)  # Exponential backoff
                        else:
                            raise UnixEventsError(f"Failed to connect to server at {self._socket_path}")

                # Start receiving messages
                self._start_receiver()

            self._initialized = True
            return True

        except Exception as e:
            self.log(f"Initialization failed: {e}")
            return False

    async def init(self, role: str, channel: str) -> bool:
        return await asyncio.get_event_loop().run_in_executor(
            None, self._init_sync, role, channel
        )

    def _start_server(self):
        self._connections = []
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

    def _accept_loop(self):
        while self._running:
            try:
                self._socket.settimeout(0.5)
                conn, _ = self._socket.accept()
                self._connections.append(conn)

                # Start receiver thread for this connection
                thread = threading.Thread(
                    target=self._receive_loop,
                    args=(conn,),
                    daemon=True
                )
                thread.start()

            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    self.log(f"Accept error: {e}")

    def _start_receiver(self):
        """Start the message receiver thread (client mode)"""
        self._listener_thread = threading.Thread(
            target=self._receive_loop,
            args=(self._socket,),
            daemon=True
        )
        self._listener_thread.start()

    def _receive_loop(self, conn: socket.socket):
        buffer = b''

        while self._running:
            try:
                # Receive data in chunks
                data = conn.recv(4096)
                if not data:
                    self._connections.remove(conn)
                    break

                buffer += data

                while self.MESSAGE_DELIMITER in buffer:
                    message, buffer = buffer.split(self.MESSAGE_DELIMITER, 1)
                    self._process_message(message)

            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    self.log(f"Receive error: {e}")
                break

    def _process_message(self, message: bytes):
        try:
            # Decode and parse JSON message
            msg_data = json.loads(message.decode('utf-8'))

            # Validate message structure
            if not isinstance(msg_data, dict) or 'event' not in msg_data:
                self.log(f"Invalid message structure: {msg_data}")
                return

            event = msg_data['event']
            payload = msg_data.get('payload')

            # Call registered handlers
            self._dispatch_event(event, payload)

        except json.JSONDecodeError as e:
            self.log(f"Failed to decode message: {e}")
        except Exception as e:
            self.log(f"Message processing error: {e}")

    def _dispatch_event(self, event: str, payload: Any):
        with self._lock:
            # Handle once handlers
            if event in self._once_handlers:
                handlers = self._once_handlers.pop(event, [])
                for handler in handlers:
                    self._call_handler(handler, payload)

            # Handle regular handlers
            if event in self._event_handlers:
                for handler in self._event_handlers[event]:
                    self._call_handler(handler, payload)

    def _call_handler(self, handler: Callable, payload: Any):
        try:
            handler(payload)
        except Exception as e:
            self.log(f"Handler error: {e}")

    def receive(self, event: str, listener: Callable[[Any], None]):
        event_name = f"c-{event}" if self._role == Role.SERVER else f"s-{event}"

        with self._lock:
            self._event_handlers[event_name].append(listener)

    def receive_once(self, event: str, listener: Callable[[Any], None]):
        event_name = f"c-{event}" if self._role == Role.SERVER else f"s-{event}"

        with self._lock:
            self._once_handlers[event_name].append(listener)

    def send(self, event: str, data: Any, callback: Optional[Callable] = None) -> bool:
        try:
            if not self._initialized or not self._running:
                raise UnixEventsError("Linker not initialized or already closed")

            message = {
                'event': f"s-{event}" if self._role == Role.SERVER else f"c-{event}",
                'payload': json.dumps(data) if type(data) is dict else data
            }

            json_data = json.dumps(message, separators=(',', ':'))
            msg_bytes = json_data.encode('utf-8') + self.MESSAGE_DELIMITER

            if len(msg_bytes) > self.MAX_MESSAGE_SIZE:
                raise UnixEventsError(f"Message too large: {len(msg_bytes)} bytes")

            if self._role == Role.SERVER:
                # Server sends to all connected clients
                for conn in self._connections:
                    try:
                        conn.sendall(msg_bytes)
                    except Exception as e:
                        self.log(f"Failed to send to client: {e}")
            else:
                # Client sends to server
                self._socket.sendall(msg_bytes)

            if callback:
                callback(None, True)
            return True

        except Exception as e:
            self.log(f"Send error: {e}")
            if callback:
                callback(e, False)
            return False

    def send_sync(self, event: str, payload: Any) -> bool:
        return self.send(event, payload)

    async def send_async(self, event: str, payload: Any) -> bool:
        return await asyncio.get_event_loop().run_in_executor(
            None, self.send, event, payload
        )

    def close(self):
        if self._running or self._initialized:
            self._running = False

            # Close connections
            if self._role == Role.SERVER:
                for conn in getattr(self, '_connections', []):
                    try:
                        conn.close()
                    except Exception as e:
                        self.log("Server socket close error: ", e)
                        pass

            # Close main socket
            if self._socket:
                try:
                    self._socket.close()
                except Exception as e:
                    self.log("Main socket close error: ", e)
                    pass

            # Remove socket file if server
            if self._role == Role.SERVER:
                socket_path = self._get_socket_path()
                if os.path.exists(socket_path):
                    try:
                        os.unlink(socket_path)
                    except Exception as e:
                        self.log("Socket file removal exception: ", e)
                        pass

            self._initialized = False

            self.log(f"Linker closed for {self._role.value if self._role else 'uninitialized'}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()


def create_server(channel: str) -> Linker:
    return Linker('server', channel)


def create_client(channel: str) -> Linker:
    return Linker('client', channel)
