# Import this to avoid memory allocation failure.
import app.lib.picozero
from app.connect import connect
import app.microdot_server as microdot_server
from app.server_methods import post, shutdown


if __name__ == "__main__":
    # [1] Connect to wifi network
    connect()
    # [2] Setup pins
    post("1", "servo")
    for i in range(2, 28, 2):
        post(str(i) + "," + str(i+1), "relay")
    # [3] Start webserver
    try:
        microdot_server.run()
    except (OSError, KeyboardInterrupt) as e:
        print(e)
        shutdown()
