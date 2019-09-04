import asyncio
from tcprelay import TCPRelay
from utils.loggers import get_logger

log = get_logger("sslocal")

HOST = "127.0.0.1"
PORT = 1081

REMOTE_HOST = "127.0.0.1"
REMOTE_PORT = 8388

if __name__ == "__main__":
    loop_ = asyncio.get_event_loop()
    loop_.set_debug(True)
    log.info(
        "sslocal listen on local(%s:%u) remote(%s:%u)"
        % (HOST, PORT, REMOTE_HOST, REMOTE_PORT)
    )
    print("create tcprelay")
    relay_server = TCPRelay(loop_, True, HOST, PORT, REMOTE_HOST, REMOTE_PORT)
    loop_.run_until_complete(relay_server.accept())
