import time
from unixevents import Linker

if __name__ == "__main__":
    client = Linker('client', 'channel')

    client.receive('event2', lambda data: print(f'Message on client: {data}'))
    time.sleep(0.1)
    client.send('event', {"mesg": "Message from client"})
    time.sleep(0.1)
    client.close()
