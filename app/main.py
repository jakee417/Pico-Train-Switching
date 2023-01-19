# Import this to avoid memory allocation failure.
import app.lib.picozero
from app.connect import connect, setup_logging
import app.microdot_server as microdot_server
from app.server_methods import post, shutdown


if __name__ == "__main__":
    # [1] Setup stream and file logging
    logger = setup_logging()
    # [2] Connect to wifi network
    connect()
    # [3] Setup pins
    for i in range(1, 28, 2):
        post(str(i) + "," + str(i + 1), "relay")
    # [4] Start webserver
    try:
        microdot_server.run()
    except (OSError, KeyboardInterrupt) as e:
        logger.error(e)
        shutdown()
    except Exception as e:
        logger.error(e)
        shutdown()
