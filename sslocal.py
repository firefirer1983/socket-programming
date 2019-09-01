import asyncio
from tcprelay import TCPRelay

HOST = "127.0.0.1"
PORT = 1090

if __name__ == "__main__":
    loop_ = asyncio.get_event_loop()
    relay_server = TCPRelay(loop_, True, HOST, PORT)
    loop_.run_until_complete(relay_server.accept())
