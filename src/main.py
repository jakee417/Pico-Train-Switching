from .connect import connect
from .microdot_server import run as _run
from .server_methods import load_devices
from .logging import log_flush


def run() -> None:
    log_flush()
    # [1] Connect to wifi network
    connect()
    # [2] Setup pins
    load_devices()
    # [3] Start webserver
    _run()


if __name__ == "__main__":
    run()
