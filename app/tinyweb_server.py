#!/usr/bin/env micropython
from json import dumps

# Import this to avoid memory allocation errors
import app.lib.picozero as picozero
import app.lib.tinyweb as tinyweb
from app.lib.tinyweb import request as Request
from app.lib.tinyweb import response as Response
from app.connect import connect
from app.server_methods import (
    get,
    load_json,
    post,
    remove_json,
    toggle_pins,
    toggle_index,
    reset_index,
    save_json,
    print_devices
)


SERVING_IP: str = "0.0.0.0"
SERVING_PORT: int = 80

app = tinyweb.webserver()


def led_flash(func):
    async def wrapper(*args, **kwargs):
        picozero.pico_led.on()
        await func(*args, **kwargs)
        picozero.pico_led.off()
    return wrapper


@app.route("/devices")
@led_flash
async def devices(_: Request, response: Response) -> None:
    await response.start_html()
    await response.send(
        dumps(
            get()
        )
    )


@app.route("/devices/get")
async def devices_get(
    _: Request,
    response: Response
) -> None:
    await response.redirect('/devices')


@app.route("/devices/toggle/pins/<pins>")
@led_flash
async def devices_toggle_pins(
    _: Request,
    response: Response,
    pins: str
) -> None:
    await response.start_html()
    await response.send(
        dumps(
            toggle_pins(pins)
        )
    )


@app.route('/devices/toggle/<device>')
@led_flash
async def devices_toggle_index(
    _: Request,
    response: Response,
    device: str
) -> None:
    await response.start_html()
    await response.send(
        dumps(
            toggle_index(int(device))
        )
    )


@app.route('/devices/reset/<device>')
@led_flash
async def devices_reset_index(
    _: Request,
    response: Response,
    device: str
) -> None:
    await response.start_html()
    await response.send(
        dumps(
            reset_index(int(device))
        )
    )


@app.route("/devices/load/<name>")
@led_flash
async def devices_load_json(
    _: Request,
    response: Response,
    name: str
) -> None:
    await response.start_html()
    await response.send(
        dumps(
            load_json(name)
        )
    )


@app.route('/devices/remove/<name>')
@led_flash
async def devices_remove_json(
    _: Request,
    response: Response,
    name: str
) -> None:
    await response.start_html()
    await response.send(
        dumps(
            remove_json(name)
        )
    )


@app.route('/devices/save/<name>')
@led_flash
async def devices_save_json(
    _: Request,
    response: Response,
    name: str
) -> None:
    await response.start_html()
    await response.send(
        dumps(
            save_json(name)
        )
    )


def run():
    post("1", "disconnect")
    post("2,3", "spur")
    print_devices()
    app.run(host=SERVING_IP, port=SERVING_PORT)
