from app.connect import connect
import app.microdot_server as microdot_server
from app.server_methods import post, shutdown
from app.logging import log_flush, log_record


def run() -> None:
    log_flush()
    # [1] Connect to wifi network
    connect()
    # [2] Setup pins
    for i in range(0, 29, 1):
        post(str(i), "singlerelay")
    # [3] Start webserver
    try:
        microdot_server.run()
    except (OSError, KeyboardInterrupt) as e:
        log_record(str(e))
        shutdown()


if __name__ == "__main__":
    run()
