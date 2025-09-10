# Linker

A Python library for event-driven communication between processes using Unix domain sockets.

## Installation

```bash
pip install unixevents
```

## Quick Start

### Basic Server-Client Communication

**Server (server.py):**
```python
from unixevents import Linker

server = Linker('server', 'channel')

def handle_greeting(data):
    print(f"Received greeting: {data}")
    server.send('welcome', {'message': 'Hello from server!'})

server.receive('greeting', handle_greeting)

print("Server is running... Press Ctrl+C to stop")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    server.close()
```

**Client (client.py):**
```python
from unixevents import Linker

client = Linker('client', 'channel')

def handle_welcome(data):
    print(f"Server says: {data['message']}")

client.receive('welcome', handle_welcome)

client.send('greeting', {'name': 'Alice', 'message': 'Hello!'})

time.sleep(2)
client.close()
```

## API Reference

### Creating Instances

#### `Linker(role, channel, debug=False)`
Create a new Linker instance.

- `role` (str): Either 'server' or 'client'
- `channel` (str): Unique channel name for communication
- `debug` (bool): Enable debug logging (optional)

### Sending Events

#### `send(event, data, callback=None)`
Send an event with data.

- `event` (str): Event name
- `data` (Any): Data to send (will be JSON serialized)
- `callback` (Callable): Optional callback function(error, success)

```python

linker.send('message', {'text': 'Hello'})

def on_sent(error, success):
    if success:
        print("Message sent successfully")
    else:
        print(f"Failed to send: {error}")

linker.send('message', {'text': 'Hello'}, on_sent)
```

#### `send_sync(event, payload)`
Synchronous version of send.

```python
success = linker.send_sync('message', {'text': 'Hello'})
```

#### `send_async(event, payload)`
Asynchronous version of send.

```python
import asyncio

async def main():
    success = await linker.send_async('message', {'text': 'Hello'})
    
asyncio.run(main())
```

### Receiving Events

#### `receive(event, listener)`
Register an event handler that will be called every time the event is received.

- `event` (str): Event name to listen for
- `listener` (Callable): Function to handle the event

```python
def handle_message(data):
    print(f"Received: {data}")

linker.receive('message', handle_message)
```

#### `receive_once(event, listener)`
Register an event handler that will be called only once.

```python
def handle_init(data):
    print(f"Initialization data: {data}")

linker.receive_once('init', handle_init)
```

### Initialization

#### `init_sync(role, channel, debug=None)`
Initialize the Linker synchronously (called automatically if role and channel provided to constructor).

```python
linker = Linker()
success = linker.init_sync('server', 'mychannel', debug=True)
```

#### `init_async(role, channel, debug=None)`
Initialize the Linker asynchronously.

```python
async def setup():
    linker = Linker()
    success = await linker.init_async('client', 'mychannel')
```

### Lifecycle Management

#### `close()`
Close the connection and clean up resources.

```python
linker.close()
```
### Debug Methods

#### `enable_debug()`
Enable debug logging.

```python
linker.enable_debug()
```

#### `disable_debug()`
Disable debug logging.

```python
linker.disable_debug()
```

## Advanced Examples

### Request-Response Pattern

**Server:**
```python
from unixevents import Linker
import uuid

server = Linker('server', 'rpc-channel')

def handle_request(data):
    request_id = data.get('id')
    method = data.get('method')
    params = data.get('params', {})
    
    if method == 'add':
        result = params.get('a', 0) + params.get('b', 0)
    elif method == 'multiply':
        result = params.get('a', 0) * params.get('b', 0)
    else:
        result = None
        
    server.send('response', {
        'id': request_id,
        'result': result
    })

server.receive('request', handle_request)
```

**Client:**
```python
from unixevents import Linker
import uuid
import threading

client = Linker('client', 'rpc-channel')
pending_requests = {}

def handle_response(data):
    request_id = data.get('id')
    if request_id in pending_requests:
        event = pending_requests[request_id]
        event.result = data.get('result')
        event.set()

client.receive('response', handle_response)

def rpc_call(method, params):
    request_id = str(uuid.uuid4())
    event = threading.Event()
    pending_requests[request_id] = event
    
    client.send('request', {
        'id': request_id,
        'method': method,
        'params': params
    })
    
    event.wait(timeout=5)
    result = getattr(event, 'result', None)
    del pending_requests[request_id]
    return result

result = rpc_call('add', {'a': 5, 'b': 3})
print(f"5 + 3 = {result}")

result = rpc_call('multiply', {'a': 4, 'b': 7})
print(f"4 * 7 = {result}")
```

### Broadcasting to Multiple Clients

**Server:**
```python
from unixevents import Linker
import time
import threading

server = Linker('server', 'broadcast-channel')
clients = []

def handle_join(data):
    client_name = data.get('name')
    clients.append(client_name)
    print(f"{client_name} joined")
    
    server.send('user_joined', {'name': client_name})

server.receive('join', handle_join)

def broadcast_time():
    while True:
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        server.send('time_update', {'time': current_time})
        time.sleep(1)

broadcast_thread = threading.Thread(target=broadcast_time, daemon=True)
broadcast_thread.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    server.close()
```

**Client:**
```python
from unixevents import Linker
import time

client = Linker('client', 'broadcast-channel')

def handle_time_update(data):
    print(f"Server time: {data['time']}")

def handle_user_joined(data):
    print(f"New user joined: {data['name']}")

client.receive('time_update', handle_time_update)
client.receive('user_joined', handle_user_joined)

client.send('join', {'name': 'Client1'})

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    client.close()
```

### Async/Await Support

```python
import asyncio
from unixevents import Linker

async def async_server():
    server = Linker()
    await server.init_async('server', 'async-channel')
    
    def handle_async_event(data):
        print(f"Received async: {data}")
        server.send_sync('processed', {'status': 'done'})
    
    server.receive('process', handle_async_event)
    
    await asyncio.sleep(60)
    server.close()

async def async_client():
    client = Linker()
    await client.init_async('client', 'async-channel')
    
    success = await client.send_async('process', {'data': 'test'})
    print(f"Sent: {success}")
    
    await asyncio.sleep(2)
    client.close()

async def main():
    await asyncio.gather(
        async_server(),
        async_client()
    )

asyncio.run(main())
```

### Debug Mode

Enable debug mode to see detailed logs:

```python

linker = Linker('server', 'mychannel', debug=True)

linker.enable_debug()
linker.disable_debug()
```

