#!/usr/bin/env micropython
from json import dumps

# Import this to avoid memory allocation errors
import app.lib.picozero as picozero
import app.lib.tinyweb as tinyweb
from app.lib.tinyweb import request as Request
from app.lib.tinyweb import response as Response
from app.connect import scan, save_credentials
from app.server_methods import (
    StatusMessage,
    get,
    load_json,
    remove_json,
    toggle_pins,
    toggle_index,
    reset_index,
    save_json,
    led_flash,
)


SERVING_IP: str = "0.0.0.0"
SERVING_PORT: int = 80

app = tinyweb.webserver()

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
    await response.redirect("/devices")


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


@app.route("/devices/toggle/<device>")
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


@app.route("/devices/reset/<device>")
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


@app.route("/devices/remove/<name>")
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


@app.route("/devices/save/<name>")
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


@app.route("/scan")
@led_flash
async def wlan_scan(
    _: Request,
    response: Response,
) -> None:
    await response.start_html()
    await response.send(
        dumps(
            scan()
        )
    )


@app.resource("/credentials", method="POST")
@led_flash
def credentials(data: dict[str, str]) -> dict[str, str]:
    if data is None:
        return {StatusMessage.FAILURE: "empty"}
    else:
        try:
            save_credentials(data)
            return {StatusMessage.SUCCESS: "created"}
        except KeyError as _:
            return {StatusMessage.FAILURE: "incorrect"}
        except Exception as e:
            return {StatusMessage.FAILURE: f"{e}"}


def run() -> None:
    app.run(
        host=SERVING_IP,
        port=SERVING_PORT
    )
