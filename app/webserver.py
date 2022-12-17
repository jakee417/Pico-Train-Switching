"""Web server for a Raspberry Pi Pico W."""
import network
from time import sleep
import machine
import uasyncio as asyncio

from app.secrets import SSID, PASSWORD
from app.constants import Signals, MAX_WAIT, HTTPSignals, SERVING_ADDRESS, PORT
from app.picozero import pico_temp_sensor, pico_led


def connect() -> None:
    print('Connecting to Network...')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)

    max_wait = MAX_WAIT
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('Waiting for connection...')
        sleep(1)

    if wlan.status() != 3:
        raise RuntimeError('Network connection failed.')
    else:
        status = wlan.ifconfig()
        print(f"Connected:{status[0]}")


async def serve_client(reader, writer):
    print("Client connected")
    request_line = await reader.readline()
    print("Request:", request_line)
    # We are not interested in HTTP request headers, skip them
    while await reader.readline() != b"\r\n":
        pass

    request = str(request_line)
    led_on = request.find(Signals.LIGHT_ON)
    led_off = request.find(Signals.LIGHT_OFF)
    print('led on = ' + str(led_on))
    print('led off = ' + str(led_off))

    state = ""
    if led_on == 6:
        pico_led.on()
        state = "LED is ON"

    if led_off == 6:
        pico_led.off()
        state = "LED is OFF"

    response = webpage(state=state)
    writer.write(HTTPSignals.RESPONSE_200)
    writer.write(response)

    await writer.drain()
    await writer.wait_closed()
    print("Client disconnected")


def webpage(state: str) -> str:
    # Template HTML
    html = f"""
        <!DOCTYPE html>
        <html>
        <form action=".{Signals.LIGHT_ON}">
        <input type="submit" value="Light on" />
        </form>
        <form action=".{Signals.LIGHT_OFF}">
        <input type="submit" value="Light off" />
        </form>
        <p>LED is {state}</p>
        <p>Temperature is {str(pico_temp_sensor.temp)}</p>
        </body>
        </html>
    """
    return str(html)


async def main():
    connect()
    asyncio.create_task(
        asyncio.start_server(serve_client, SERVING_ADDRESS, PORT)
    )
    beat = 0
    while True:
        pico_led.toggle()
        print(f"heartbeat: {beat}")
        await asyncio.sleep(0.25)
        pico_led.toggle()
        await asyncio.sleep(5)
        beat += 1

try:
    asyncio.run(main())
except KeyboardInterrupt:
    machine.reset()
finally:
    asyncio.new_event_loop()
