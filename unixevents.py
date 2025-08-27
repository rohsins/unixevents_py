# import asyncio
import json
import os
import socket
import tempfile
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Union
# from pathlib import Path


class Linker:
    def __init__(self, role: Optional[str] = None, channel: Optional[str] = None):
        """
        Initialize UnixEvents instance.

        Args:
            role: Either 'server' or 'client'. If None, call init() later.
            channel: Channel name for communication. If None, call init() later.
        """
        self.role = role
        self.channel = channel
        self.socket = None
        self.server_socket = None
        self.client_connections: List[socket.socket] = []
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.once_handlers: Dict[str, List[Callable]] = {}
        self.running = False
        self.socket_path = None
        self._lock = threading.Lock()
        self._listen_thread = None

        if role and channel:
            self._initialize()

    def _initialize(self) -> None:
        """Internal initialization method."""
        if not self.role or not self.channel:
            raise ValueError("Role and channel must be specified")

        if self.role not in ['server', 'client']:
            raise ValueError("Role must be 'server' or 'client'")

            # Create socket path in temp directory
        self.socket_path = (
            f"/tmp/{self.channel}.sock" if os.name != "nt"
            else f"\\\\.\\pipe\\{os.environ.get('TMP')}\\{self.channel}.sock"
        )

        print("the path: ", self.socket_path)

        if self.role == 'server':
            self._start_server()
        else:
            self._connect_client()

    async def init(self, role: str, channel: str) -> bool:
        """
        Initialize the UnixEvents instance asynchronously.

        Args:
            role: Either 'server' or 'client'
            channel: Channel name for communication

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.role = role
            self.channel = channel
            self._initialize()
            return True
        except Exception as e:
            print(f"Initialization failed: {e}")
            return False

    def _start_server(self) -> None:
        """Start Unix domain socket server."""
        try:
            # Remove existing socket file if it exists
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)

            self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.server_socket.bind(self.socket_path)
            self.server_socket.listen(5)
            self.running = True

            # Start listening thread
            self._listen_thread = threading.Thread(target=self._accept_connections, daemon=True)
            self._listen_thread.start()

        except Exception as e:
            print(f"Failed to start server: {e}")
            raise

    def _connect_client(self) -> None:
        """Connect as client to server."""
        max_retries = 10
        retry_delay = 0.1

        for attempt in range(max_retries):
            try:
                self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.socket.connect(self.socket_path)
                self.running = True

                # Start listening thread for incoming messages
                self._listen_thread = threading.Thread(target=self._listen_client, daemon=True)
                self._listen_thread.start()
                return

            except (FileNotFoundError, ConnectionRefusedError):
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise ConnectionError(f"Could not connect to server after {max_retries} attempts")

    def _accept_connections(self) -> None:
        """Accept incoming client connections (server only)."""
        while self.running and self.server_socket:
            try:
                client_socket, _ = self.server_socket.accept()
                with self._lock:
                    self.client_connections.append(client_socket)

                # Start thread to handle this client
                client_thread = threading.Thread(
                    target=self._handle_client, 
                    args=(client_socket,), 
                    daemon=True
                )
                client_thread.start()

            except OSError:
                break  # Socket was closed

    def _handle_client(self, client_socket: socket.socket) -> None:
        """Handle messages from a client connection."""
        try:
            while self.running:
                data = self._receive_message(client_socket)
                if data is None:
                    break
                self._process_message(data)
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            with self._lock:
                if client_socket in self.client_connections:
                    self.client_connections.remove(client_socket)
            try:
                client_socket.close()
            except:
                pass

    def _listen_client(self) -> None:
        """Listen for messages from server (client only)."""
        try:
            while self.running and self.socket:
                data = self._receive_message(self.socket)
                if data is None:
                    break
                self._process_message(data)
        except Exception as e:
            print(f"Error in client listener: {e}")

    def _receive_message(self, sock: socket.socket) -> Optional[Dict]:
        """Receive a complete message from socket."""
        try:
            # First, read the length prefix (4 bytes)
            length_data = b''
            while len(length_data) < 4:
                chunk = sock.recv(4 - len(length_data))
                if not chunk:
                    return None
                length_data += chunk

            message_length = int.from_bytes(length_data, byteorder='big')

            # Then read the message
            message_data = b''
            while len(message_data) < message_length:
                chunk = sock.recv(message_length - len(message_data))
                if not chunk:
                    return None
                message_data += chunk

            return json.loads(message_data.decode('utf-8'))

        except Exception as e:
            print(f"Error receiving message: {e}")
            return None

    def _send_message(self, sock: socket.socket, message: Dict) -> bool:
        """Send a message to socket with length prefix."""
        try:
            message_json = json.dumps(message).encode('utf-8')
            length_prefix = len(message_json).to_bytes(4, byteorder='big')
            sock.sendall(length_prefix + message_json)
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False

    def _process_message(self, message: Dict) -> None:
        """Process incoming message and trigger event handlers."""
        if 'event' not in message:
            return

        event_name = message['event']
        event_data = message.get('data')

        # Handle regular event handlers
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name][:]:  # Copy to avoid modification issues
                try:
                    handler(event_data)
                except Exception as e:
                    print(f"Error in event handler: {e}")

        # Handle once-only event handlers
        if event_name in self.once_handlers:
            handlers = self.once_handlers[event_name][:]
            self.once_handlers[event_name].clear()  # Remove after first use

            for handler in handlers:
                try:
                    handler(event_data)
                except Exception as e:
                    print(f"Error in once handler: {e}")

    def receive(self, event: str, listener: Callable[[Any], None]) -> None:
        """
        Subscribe to an event.

        Args:
            event: The event name to subscribe to
            listener: Callback function that receives event data
        """
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(listener)

    def receive_once(self, event: str, listener: Callable[[Any], None]) -> None:
        """
        Subscribe to an event once - automatically unsubscribes after first trigger.

        Args:
            event: The event name to subscribe to
            listener: Callback function that receives event data
        """
        if event not in self.once_handlers:
            self.once_handlers[event] = []
        self.once_handlers[event].append(listener)

    def send(self, event: str, data: Any, callback: Optional[Callable[[Optional[Exception], bool], None]] = None) -> None:
        """
        Send an event asynchronously.

        Args:
            event: The event name to send
            data: Data to send with the event
            callback: Optional callback function called when send completes
        """
        def _send_async():
            try:
                success = self._send_message_to_all({
                    'event': event,
                    'data': data
                })
                if callback:
                    callback(None, success)
            except Exception as e:
                if callback:
                    callback(e, False)

        thread = threading.Thread(target=_send_async, daemon=True)
        thread.start()

    async def send_sync(self, event: str, data: Any) -> bool:
        """
        Send an event synchronously.

        Args:
            event: The event name to send
            data: Data to send with the event

        Returns:
            True if send was successful, False otherwise
        """
        try:
            return self._send_message_to_all({
                'event': event,
                'data': data
            })
        except Exception:
            return False

    def _send_message_to_all(self, message: Dict) -> bool:
        """Send message to all connected peers."""
        if not self.running:
            return False

        success = True

        if self.role == 'server':
            # Send to all connected clients
            with self._lock:
                disconnected = []
                for client_socket in self.client_connections[:]:
                    if not self._send_message(client_socket, message):
                        disconnected.append(client_socket)
                        success = False

                # Remove disconnected clients
                for client_socket in disconnected:
                    if client_socket in self.client_connections:
                        self.client_connections.remove(client_socket)
                    try:
                        client_socket.close()
                    except:
                        pass

        elif self.role == 'client' and self.socket:
            # Send to server
            success = self._send_message(self.socket, message)

        return success

    def close(self) -> None:
        """Close the UnixEvents instance and cleanup resources."""
        self.running = False

        # Close client connections
        with self._lock:
            for client_socket in self.client_connections[:]:
                try:
                    client_socket.close()
                except:
                    pass
            self.client_connections.clear()

        # Close main socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None

        # Remove socket file
        if self.socket_path and os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except:
                pass

        # Wait for threads to finish
        if self._listen_thread and self._listen_thread.is_alive():
            self._listen_thread.join(timeout=1.0)

    def __del__(self):
        """Cleanup when object is garbage collected."""
        self.close()
