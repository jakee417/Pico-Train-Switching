from machine import reset

# Import this to avoid memory allocation failure.
import app.lib.picozero
from app.connect import connect, wlan_shutdown
import app.microdot_server as microdot_server
from app.server_methods import close_devices_closure, post


def shutdown() -> None:
    close_devices_closure()
    wlan_shutdown()
    reset()


if __name__ == "__main__":
    # [1] Connect to wifi network
    connect()
    # [2] Setup pins
    post("1", "servo")
    post("2,3", "relay")
    # [3] Start webserver
    try:
        microdot_server.run()
    except (OSError, KeyboardInterrupt) as _:
        shutdown()
