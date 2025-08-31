import asyncio
import time
from unixevents import Linker


async def main():
    # server = Linker('server', 'channel', True)
    server = Linker(debug=False)
    await server.init_async('server', 'channel', False)
    # server.init_sync('server', 'channel', True)
    # server.enable_debug()

    def callback(payload):
        print(f"Message on server: {payload}")
        server.send('event2', 'Message from server')

    server.receive('event', callback)

    time.sleep(0.1)

    while True:
        time.sleep(10)

    server.close()

if __name__ == "__main__":
    asyncio.run(main())
