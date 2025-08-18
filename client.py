from unixevents import Linker
import time

# Create client linker
link = Linker('client', 'channel2')

link.init()
# Callback example
def on_ack(err, ack):
    if err:
        print("[CLIENT] Error:", err)
    else:
        print("[CLIENT] Ack from server:", ack)

# Send async message
link.send("event2", {"msg": "Hi from client!"})

time.sleep(1)  # Wait for callbacks before closing
link.close()

