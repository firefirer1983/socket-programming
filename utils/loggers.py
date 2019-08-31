import sys
from logging import StreamHandler
import logging


def logger_cache(f):
    loggers = {}
    
    def _func(name):
        if name not in loggers:
            loggers[name] = logging.getLogger(name)
            loggers[name].addHandler(StreamHandler(stream=sys.stdout))
            loggers[name].setLevel(logging.DEBUG)
        return loggers[name]
    return _func


@logger_cache
def get_logger():
    pass
