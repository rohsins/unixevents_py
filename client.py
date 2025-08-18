from unixevents import Linker
import time

# Create client linker
client = Linker('client', 'channel2')
# link = Linker()
# link.init('client', 'channel2', True)


def on_ack(err, ack):
    if err:
        print("[CLIENT] Error:", err)
    else:
        print("[CLIENT] Ack from server:", ack)


# Send async message
client.receive("replyEvent", lambda data: (
    print("Receive from client: ", data)
))

client.send("event2", {"msg": "Hi from client stuff!"})

time.sleep(1)  # Wait for callbacks before closing
# link.close()
