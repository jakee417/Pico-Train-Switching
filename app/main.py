from app.connect import connect
import app.microdot_server as microdot_server
from app.server_methods import post, shutdown
from app.logging import log_flush, log_record
from app.config import ota


def run() -> None:
    log_flush()
    # [1] Connect to wifi network
    connect()
    # [2] Setup pins
    post("0,1", "relay")  # 1
    post("2,3", "relay")  # 2
    post("4,5", "relay")  # 3
    post("6,7", "relay")  # 4
    post("8,9", "relay")  # 5
    post("10,11", "relay")  # 6
    post("12,13", "relay")  # 7
    post("14,15", "relay")  # 8
    post("16,17", "relay")  # 19
    post("18,19", "relay")  # 10
    post("20,21", "relay")  # 11
    post("22,26", "relay")  # 12
    post("27,28", "relay")  # 13
    ota()
    # [3] Start webserver
    try:
        microdot_server.run()
    except (OSError, KeyboardInterrupt) as e:
        log_record(str(e))
        shutdown()


if __name__ == "__main__":
    run()
