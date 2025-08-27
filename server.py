#!/usr/bin/env python3

import asyncio
import threading
import time
from unixevents import Linker


async def main():
    server = Linker('server', 'Channel1')

    def on_event(data):
        print(f'Message on server: {data}')
        server.send('clientEvent', "what is up from server, now unlinking")

    server.receive('serverEvent', on_event)

    while True:
        time.sleep(1)
        pass

if __name__ == "__main__":
    # run_example_1()
    asyncio.run(main())
