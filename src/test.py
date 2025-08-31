import threading
import time
import asyncio
import tempfile
import logging
from typing import Dict, Callable, Any, Optional, Union
from collections import defaultdict
from enum import Enum
from unixevents import Linker

# Example usage
if __name__ == "__main__":
    # Setup logging for demo
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Example 1: Simple server
    def run_server():
        server = Linker('server', 'channel')

        server.receive('event', lambda data: print(f'Message on server: {data}'))

        time.sleep(0.1)
        server.send('event2', 'Message from server')

        while True:
            time.sleep(10)

        server.close()

    # Example 2: Simple client
    def run_client():
        time.sleep(2)  # Give server time to start
        client = Linker('client', 'channel')

        time.sleep(0.1)
        client.send('event', 'Message from client')
        client.receive('event2', lambda data: print(f'Message on client: {data}'))

        time.sleep(0.1)
        client.send('event', 'Message from client')

        time.sleep(10)
        client.close()

    # Run examples in threads
    import threading

    server_thread = threading.Thread(target=run_server)
    client_thread = threading.Thread(target=run_client)

    server_thread.start()
    client_thread.start()

    server_thread.join()
    client_thread.join()
