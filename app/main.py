from app.connect import connect
import app.microdot_server as microdot_server
from app.server_methods import post, shutdown
from app.logging import log_flush, log_record


def run() -> None:
    log_flush()
    # [1] Connect to wifi network
    connect()
    # [2] Setup pins
    post("0,1", "doubleservo")
    for i in range(2, 28, 2):
        post(f"{i},{i+1}", "relay")
    # [3] Start webserver
    try:
        microdot_server.run()
    except (OSError, KeyboardInterrupt) as e:
        log_record(str(e))
        shutdown()


if __name__ == "__main__":
    run()
