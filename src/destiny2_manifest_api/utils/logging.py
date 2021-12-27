import sys

from aiologger import Logger
from aiologger.formatters.base import Formatter
from aiologger.handlers.files import AsyncFileHandler
from aiologger.handlers.streams import AsyncStreamHandler


def create_logger(name="destiny_manifest_api", filename="app.log"):
    from ..config import LOG_FILE_PATH, LOG_LEVEL

    logger = Logger(name=name, level=LOG_LEVEL)
    formatter = Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    filehandler = AsyncFileHandler(str((LOG_FILE_PATH / filename).absolute()))
    filehandler.formatter = formatter
    streamhandler = AsyncStreamHandler(sys.stdout)
    streamhandler.formatter = formatter
    logger.add_handler(filehandler)
    logger.add_handler(streamhandler)
    return logger
