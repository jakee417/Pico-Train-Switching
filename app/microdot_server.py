from json import dumps
from app.connect import reset_credentials
from app.connect import (
    save_credentials as _save_credentials,
    scan,
    NetworkInfo,
    nic_closure,
)
import app.lib.logging as logging
from app.lib.microdot import Microdot, Request
from app.server_methods import (
    StatusMessage,
    change,
    get,
    load_json,
    remove_json,
    reset_pins,
    toggle_pins,
    toggle_index,
    reset_index,
    save_json,
    led_flash,
    app_reset,
    server_log,
)

app = Microdot()
logger = logging.getLogger()


@app.get("/devices")
@server_log
@led_flash
def devices(_: Request) -> str:
    return dumps(get())


@app.get("/devices/toggle/pins/<pins>")
@server_log
@led_flash
def devices_toggle_pins(_: Request, pins: str) -> str:
    return dumps(toggle_pins(pins))


@app.get("/devices/reset/pins/<pins>")
@server_log
@led_flash
def devices_reset_pins(_: Request, pins: str) -> str:
    return dumps(reset_pins(pins))


@app.get("/devices/toggle/<device>")
@server_log
@led_flash
def devices_toggle_index(_: Request, device: str) -> str:
    return dumps(toggle_index(int(device)))


@app.get("/devices/reset/<device>")
@server_log
@led_flash
def devices_reset_index(_: Request, device: str) -> str:
    return dumps(reset_index(int(device)))


@app.get("/devices/change/<pins>/<device_type>")
@server_log
@led_flash
def devices_change(_: Request, pins: str, device_type: str) -> str:
    return dumps(change(pins, device_type))


@app.get("/devices/load/<name>")
@server_log
@led_flash
def devices_load_json(_: Request, name: str) -> str:
    return dumps(load_json(name))


@app.get("/devices/remove/<name>")
@server_log
@led_flash
def devices_remove_json(_: Request, name: str) -> str:
    return dumps(remove_json(name))


@app.get("/devices/save/<name>")
@server_log
@led_flash
def devices_save_json(_: Request, name: str) -> str:
    return dumps(save_json(name))


@app.get("/scan")
@server_log
@led_flash
def server_scan(_: Request) -> str:
    return dumps(scan())


@app.get("/network")
@server_log
@led_flash
def server_network(_: Request) -> str:
    return dumps(NetworkInfo(nic_closure()).json)


@app.post("/credentials")
@server_log
@led_flash
def server_save_credentials(request: Request) -> str:
    json = request.json
    if json is None:
        logger.info("++++ Credentials were empty...")
        return StatusMessage.FAILURE
    else:
        try:
            _save_credentials(json)
            return StatusMessage.SUCCESS
        except KeyError as _:
            logger.error("++++ Credentials had bad keys...")
            return StatusMessage.FAILURE
        except Exception as e:
            logger.error(f"++++ Failed with {e}...")
            return StatusMessage.FAILURE


@app.get("/credentials/reset")
@server_log
@led_flash
def server_reset_credentials(_: Request) -> str:
    reset_credentials()
    return StatusMessage.SUCCESS


@app.get("/reset")
@server_log
@led_flash
def server_app_reset(_: Request) -> str:
    app_reset()
    return StatusMessage.SUCCESS


def run() -> None:
    app.run(
        host="0.0.0.0",
        port=80,
        debug=True,
    )
