from unixevents import Linker# your ported class file

server = Linker("server", "channel2", debug=False)
server.init()

server.receive("event2", lambda payload: (
    print("Python server got:", payload),
    server.send("reply", {"msg": "Hello from Python!"})  # sends "s-reply"
))

while True:
    pass 

