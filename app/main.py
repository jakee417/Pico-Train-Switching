from machine import soft_reset

from app.connect import connect
import app.tinyweb_server as tinyweb_server
from app.server_methods import close_devices_closure


def shutdown() -> None:
    close_devices_closure()
    soft_reset()
    wlan.disconnect()


if __name__ == "__main__":
    wlan = connect()
    try:
        tinyweb_server.run()
    except OSError as os_error:
        shutdown()
    except KeyboardInterrupt as kb_inter:
        shutdown()
