import asyncio
from tcprelay import TCPRelay
from utils.loggers import get_logger

log = get_logger("sslocal")

HOST = "0.0.0.0"
PORT = 8388


if __name__ == "__main__":
    loop_ = asyncio.get_event_loop()
    loop_.set_debug(True)
    log.info("ssserver listen on local(%s:%u)" % (HOST, PORT))
    print("create tcprelay")
    relay_server = TCPRelay(loop_, False, HOST, PORT)
    loop_.run_until_complete(relay_server.accept())
