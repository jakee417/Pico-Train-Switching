from json import dumps
from app.connect import reset_credentials
from app.connect import (
    save_credentials as _save_credentials,
    scan,
    NetworkInfo,
    nic_closure,
)
from app.lib.microdot import Microdot, Request, Response, redirect
from app.server_methods import (
    StatusMessage,
    change,
    get,
    load_json,
    remove_json,
    toggle_pins,
    toggle_index,
    reset_index,
    save_json,
    led_flash,
    app_reset,
)

app = Microdot()


@app.get("/devices")
@led_flash
def devices(_: Request) -> str:
    return dumps(get())


@app.get("/devices/get")
def devices_get(
    _: Request,
) -> Response:
    return redirect("/devices")


@app.get("/devices/toggle/pins/<pins>")
@led_flash
def devices_toggle_pins(_: Request, pins: str) -> str:
    return dumps(toggle_pins(pins))


@app.get("/devices/toggle/<device>")
@led_flash
def devices_toggle_index(_: Request, device: str) -> str:
    return dumps(toggle_index(int(device)))


@app.get("/devices/reset/<device>")
@led_flash
def devices_reset_index(_: Request, device: str) -> str:
    return dumps(reset_index(int(device)))


@app.get("/devices/change/<pins>/<device_type>")
@led_flash
def devices_change(_: Request, pins: str, device_type: str) -> str:
    return dumps(change(pins, device_type))


@app.get("/devices/load/<name>")
@led_flash
def devices_load_json(_: Request, name: str) -> str:
    return dumps(load_json(name))


@app.get("/devices/remove/<name>")
@led_flash
def devices_remove_json(_: Request, name: str) -> str:
    return dumps(remove_json(name))


@app.get("/devices/save/<name>")
@led_flash
def devices_save_json(_: Request, name: str) -> str:
    return dumps(save_json(name))


@app.get("/scan")
@led_flash
def server_scan(_: Request) -> str:
    return dumps(scan())


@app.get("/network")
@led_flash
def server_network(_: Request) -> str:
    return dumps(NetworkInfo(nic_closure()).json)


@app.post("/credentials")
@led_flash
def server_save_credentials(request: Request) -> str:
    json = request.json
    if json is None:
        print("++++ Credentials were empty...")
        return StatusMessage.FAILURE
    else:
        try:
            _save_credentials(json)
            return StatusMessage.SUCCESS
        except KeyError as _:
            print("++++ Credentials had bad keys...")
            return StatusMessage.FAILURE
        except Exception as e:
            print(f"++++ Failed with {e}...")
            return StatusMessage.FAILURE


@app.get("/credentials/reset")
def server_reset_credentials(_: Request) -> str:
    reset_credentials()
    return StatusMessage.SUCCESS


@app.get("/reset")
def server_app_reset(_: Request) -> str:
    app_reset()
    return StatusMessage.SUCCESS


def run() -> None:
    app.run(
        host="0.0.0.0",
        port=80,
    )
