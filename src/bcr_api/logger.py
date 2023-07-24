import logging


logging.basicConfig(
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


def get_logger():
    return logging.getLogger("bcr_api")
