from machine import reset

from app.connect import connect
import app.tinyweb_server as tinyweb_server
import app.microdot_server as microdot_server
from app.server_methods import close_devices_closure, post


def shutdown() -> None:
    close_devices_closure()
    wlan.disconnect()
    wlan.active(False)
    reset()


if __name__ == "__main__":
    # [1] Connect to wifi network
    wlan = connect()
    # [2] Setup pins
    post("1", "servo")
    post("2,3", "relay")
    # [3] Start webserver
    try:
        microdot_server.run()
    except (OSError, KeyboardInterrupt) as _:
        shutdown()
