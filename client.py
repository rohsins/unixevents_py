import asyncio
import time
import threading
from unixevents import Linker


async def main():
    client = Linker('client', 'Channel1')

    client.receive('clientEvent', lambda data: print(f'data on client: {data}'))
    client.send('serverEvent', 'requesting server to link up')
    time.sleep(10)
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
