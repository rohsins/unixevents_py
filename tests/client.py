import asyncio
import time
from unixevents import Linker

async def main():
    client = Linker('client', 'channel')

    client.receive('event2', lambda data: print(f'Message on client: {data}'))
    await client.send_async('event', {"mesg": "Message from client"})
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
