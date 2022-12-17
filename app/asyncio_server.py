"""Web server for a Raspberry Pi Pico W."""
import uasyncio as asyncio

from app.constants import Signals, HTTPSignals, SERVING_ADDRESS, PORT
from app.picozero import pico_temp_sensor, pico_led


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