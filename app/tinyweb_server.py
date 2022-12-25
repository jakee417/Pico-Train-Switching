#!/usr/bin/env micropython
from json import dumps

# Import this to avoid memory allocation errors
import app.picozero as picozero
import app.tinyweb as tinyweb
from app.server_methods import (
    get,
    load_json,
    post,
    remove_json,
    toggle_pins,
    toggle_index,
    reset_index,
    save_json
)

app = tinyweb.webserver()

post("1,2", "relay")
post("4,5", "relay")


@app.route("/devices")
async def devices(request, response) -> None:
    picozero.pico_led.on()
    await response.start_html()
    await response.send(dumps(get()))
    picozero.pico_led.off()


@app.route("/devices/get")
async def devices_get(request, response) -> None:
    picozero.pico_led.on()
    await response.start_html()
    await response.send(dumps(get()))
    picozero.pico_led.off()


@app.route("/devices/toggle/pins/<pins>")
async def devices_toggle_pins(request, response, pins: str) -> None:
    await response.start_html()
    await response.send(
        dumps(
            toggle_pins(pins)
        )
    )


@app.route('/devices/toggle/<device>')
async def devices_toggle_index(request, response, device: str) -> None:
    await response.start_html()
    await response.send(
        dumps(
            toggle_index(int(device))
        )
    )


@app.route('/devices/reset/<device>')
async def devices_reset_index(request, response, device: str) -> None:
    await response.start_html()
    await response.send(
        dumps(
            reset_index(int(device))
        )
    )


@app.route("/devices/load/<name>")
async def devices_load_json(request, response, name: str) -> None:
    await response.start_html()
    await response.send(
        dumps(
            load_json(name)
        )
    )


@app.route('/devices/remove/<name>')
async def devices_remove_json(request, response, name: str) -> None:
    await response.start_html()
    await response.send(
        dumps(
            remove_json(name)
        )
    )


@app.route('/devices/save/<name>')
async def devices_save_json(request, response, name: str) -> None:
    await response.start_html()
    await response.send(
        dumps(
            save_json(name)
        )
    )


def run():
    app.run(host='0.0.0.0', port=80)


if __name__ == '__main__':
    run()
