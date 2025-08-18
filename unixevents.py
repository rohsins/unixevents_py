import os
import socket
import json
import threading


class Linker:
    def __init__(self, role=None, channel=None, debug=False):
        self.role = role
        self.channel = channel
        self.sock = None
        self.client_conn = None
        self.debug = debug
        self.handlers = {}

        if role is not None and channel is not None:
            self.sock_path = (
                f"/tmp/{channel}.sock" if os.name != "nt"
                else f"\\\\.\\pipe\\{os.environ.get('TMP')}\\{channel}.sock"
            )
            self.start()

    def init(self, role, channel, debug=None):
        self.role = role
        self.channel = channel
        self.debug = debug if debug is not None else self.debug

        if role is not None and channel is not None:
            self.sock_path = (
                f"/tmp/{channel}.sock" if os.name != "nt"
                else f"\\\\.\\pipe\\{os.environ.get('TMP')}\\{channel}.sock"
            )
            self.start()

    def log(self, *args):
        if self.debug:
            print(*args)

    def _handle_data(self, raw_data):
        packets = raw_data.decode().split(";;")
        packets = [p for p in packets if p.strip()]
        for packet in packets:
            try:
                event_obj = json.loads(packet)
                event = event_obj["event"]
                payload = event_obj["payload"]
                if event in self.handlers:
                    for cb in self.handlers[event]:
                        cb(payload)
            except Exception as e:
                self.log("Error parsing packet:", e)

    def receive(self, event, func):
        event_name = f"c-{event}" if self.role == "server" else f"s-{event}"
        self.handlers.setdefault(event_name, []).append(func)

        if self.role == "server":
            def accept_loop():
                while True:
                    conn, _ = self.sock.accept()
                    self.client_conn = conn
                    self.log("Client connected")
                    threading.Thread(
                        target=self._recv_loop,
                        args=(conn,),
                        daemon=True
                    ).start()
            threading.Thread(target=accept_loop, daemon=True).start()

        elif self.role == "client":
            threading.Thread(
                target=self._recv_loop,
                args=(self.sock,),
                daemon=True
            ).start()

    def receive_once(self, event, func):
        event_name = f"c-{event}" if self.role == "server" else f"s-{event}"

        def wrapper(payload):
            func(payload)
            self.handlers[event_name].remove(wrapper)

        self.receive(event_name, wrapper)

    def send(self, event, payload):
        event_name = f"s-{event}" if self.role == "server" else f"c-{event}"

        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)

        packet = json.dumps({"event": event_name, "payload": payload}) + ";;"
        target = self.client_conn if self.role == "server" else self.sock

        if target:
            target.sendall(packet.encode())
        else:
            self.log("Socket not connected")

    def start(self):
        if self.role == "server":
            if os.path.exists(self.sock_path):
                self.log("The channel is already taken")
                # return
                os.remove(self.sock_path)
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.bind(self.sock_path)
            self.sock.listen(1)
            self.log("Server listening on", self.sock_path)

        elif self.role == "client":
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            while True:
                try:
                    self.sock.connect(self.sock_path)
                    self.log("Connected to server")
                    break
                except socket.error:
                    self.log("Retrying connection...")
                    import time
                    time.sleep(1)

    def _recv_loop(self, conn):
        while True:
            try:
                data = conn.recv(4096)
                if not data:
                    self.log("Connection closed")
                    break
                self._handle_data(data)
            except Exception as e:
                self.log("Receive error:", e)
                break

    def close(self):
        if self.sock:
            self.sock.close()
        if self.client_conn:
            self.client_conn.close()
