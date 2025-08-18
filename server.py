from unixevents import Linker

server = Linker("server", "channel2")

server.receive("event2", lambda payload: (
    print("Python server got:", payload),
    server.send("replyEvent", {"msg": "Hello from Python!"})  # sends "s-reply"
))

while True:
    pass
