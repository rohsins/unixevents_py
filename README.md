# UnixEvents Python

A Python port of the [unixevents](https://github.com/rohsins/unixevents) JavaScript library for inter-process communication on Unix systems.

UnixEvents provides a simple event-based API for communication between programs running on the same machine using Unix domain sockets.

## Installation

```bash
pip install unixevents-python
```

Or install from source:

```bash
git clone https://github.com/yourusername/unixevents-python.git
cd unixevents-python
pip install -e .
```

## Quick Start

### Basic Usage

**Program 1 (Server):**

```python
from unixevents import UnixEvents
import time

server = UnixEvents('server', 'Channel1')

def on_message(data):
    print('Message on server:', data)

server.receive('event-s-a', on_message)

# Send message after delay
import threading
def send_delayed():
    time.sleep(0.1)
    server.send('event-c-a', 'Message from server')

threading.Thread(target=send_delayed, daemon=True).start()

# Keep running
time.sleep(1)
client.close()
```

### Async Initialization

**Program 1 (Server):**

```python
import asyncio
from unixevents import UnixEvents

async def main():
    server = UnixEvents()
    result = await server.init('server', 'Channel2')
    print("Server initialized:", result)
    
    def on_message(data):
        print('Message on server:', data)
    
    server.receive('event-sa', on_message)
    server.send('event-ca', 'Message from server')
    
    await asyncio.sleep(0.5)
    server.close()

asyncio.run(main())
```

**Program 2 (Client):**

```python
import asyncio
from unixevents import UnixEvents

async def main():
    client = UnixEvents()
    result = await client.init('client', 'Channel2')
    print("Client initialized:", result)
    
    def on_message(data):
        print('Message on client:', data)
    
    client.receive('event-ca', on_message)
    client.send('event-sa', 'Message from client')
    
    await asyncio.sleep(0.5)
    client.close()

asyncio.run(main())
```

## API Reference

### Constructor

#### `UnixEvents(role=None, channel=None)`

Creates a new UnixEvents instance.

- `role` (optional): Either `'server'` or `'client'`. If not provided, use `init()` method.
- `channel` (optional): Channel name for communication. If not provided, use `init()` method.

```python
# Direct initialization
linker = UnixEvents('server', 'my-channel')

# Or initialize later
linker = UnixEvents()
await linker.init('server', 'my-channel')
```

### Methods

#### `async init(role, channel)`

Initialize the UnixEvents instance asynchronously.

- `role`: Either `'server'` or `'client'`
- `channel`: Channel name for communication
- **Returns**: `True` if successful, `False` otherwise

```python
linker = UnixEvents()
success = await linker.init('server', 'my-channel')
```

#### `receive(event, listener)`

Subscribe to an event.

- `event`: The event name to subscribe to
- `listener`: Callback function that receives event data

```python
def on_event(data):
    print("Received:", data)

linker.receive('my-event', on_event)
```

#### `receive_once(event, listener)`

Subscribe to an event once - automatically unsubscribes after first trigger.

- `event`: The event name to subscribe to
- `listener`: Callback function that receives event data

```python
def on_event_once(data):
    print("Received once:", data)

linker.receive_once('my-event', on_event_once)
```

#### `send(event, data, callback=None)`

Send an event asynchronously.

- `event`: The event name to send
- `data`: Data to send (can be string, dict, list, etc.)
- `callback` (optional): Callback function `(error, success) -> None`

```python
def send_callback(error, success):
    if error:
        print("Send failed:", error)
    else:
        print("Send successful:", success)

linker.send('my-event', {'message': 'hello'}, send_callback)
```

#### `async send_sync(event, data)`

Send an event synchronously.

- `event`: The event name to send
- `data`: Data to send (can be string, dict, list, etc.)
- **Returns**: `True` if successful, `False` otherwise

```python
success = await linker.send_sync('my-event', {'message': 'hello'})
print("Send result:", success)
```

#### `close()`

Close the UnixEvents instance and cleanup resources.

```python
linker.close()
```

## Features

### Thread Safety

The library is designed to be thread-safe and handles concurrent access to sockets and event handlers properly.

### Automatic Reconnection

Clients will attempt to reconnect to servers with exponential backoff if the initial connection fails.

### JSON Serialization

All data is automatically serialized/deserialized using JSON, supporting:
- Strings
- Numbers
- Booleans  
- Lists
- Dictionaries
- None values

### Error Handling

The library includes comprehensive error handling:
- Connection failures
- Socket errors
- Serialization errors
- Handler exceptions

## Examples

Run the included examples:

```bash
# Run all examples
python -m unixevents.examples

# Run specific example
python -m unixevents.examples 1  # Basic usage
python -m unixevents.examples 2  # Async initialization
python -m unixevents.examples 3  # Advanced features
python -m unixevents.examples 4  # Sync vs async sending
```

## Differences from JavaScript Version

1. **Threading**: Uses Python threading instead of Node.js event loop
2. **Async/Await**: Uses Python's `asyncio` for async operations
3. **Error Handling**: More explicit error handling with try/catch blocks
4. **Socket Implementation**: Uses Unix domain sockets directly instead of Node.js streams
5. **Naming**: Also provides `Linker` alias for compatibility

## Platform Support

- Linux
- macOS  
- Other Unix-like systems with Unix domain socket support

**Note**: Windows is not supported as it lacks Unix domain socket support.

## Development

### Setting up Development Environment

```bash
git clone https://github.com/yourusername/unixevents-python.git
cd unixevents-python
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black unixevents/
flake8 unixevents/
mypy unixevents/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Credits

This is a Python port of the original [unixevents](https://github.com/rohsins/unixevents) JavaScript library by [rohsins](https://github.com/rohsins).

## Changelog

### v1.0.0
- Initial release
- Full API compatibility with JavaScript version
- Thread-safe implementation
- Comprehensive error handling
- Unix domain socket backend
- Async/await supportThread(target=send_delayed, daemon=True).start()

# Keep running
time.sleep(1)
server.close()
```

**Program 2 (Client):**

```python
from unixevents import UnixEvents
import time

client = UnixEvents('client', 'Channel1')

def on_message(data):
    print('Message on client:', data)

client.receive('event-c-a', on_message)

# Send message after delay
import threading
def send_delayed():
    time.sleep(0.1)
    client.send('event-s-a', 'Message from client')
```
