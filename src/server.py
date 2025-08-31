import time
import logging
from unixevents import Linker

# Example usage
if __name__ == "__main__":
    # Setup logging for demo
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    server = Linker('server', 'channel')

    def callback(payload):
        print(f"Message on server: {payload}")
        server.send('event2', 'Message from server')

    server.receive('event', callback)

    time.sleep(0.1)

    while True:
        time.sleep(10)

    server.close()
