import machine
import uasyncio as asyncio

from app.asyncio_server import main
from app.connect import connect

if __name__ == "__main__":
    connect()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        machine.reset()
    finally:
        asyncio.new_event_loop()