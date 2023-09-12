from json import dumps
from app.connect import reset_credentials
from app.connect import (
    save_credentials as _save_credentials,
    scan,
    NetworkInfo,
    nic_closure,
)
from app.config import ota
from app.lib.microdot import Microdot, Request
from app.logging import log_dump, log_flush
from app.server_methods import (
    StatusMessage,
    change_pins,
    get_devices,
    get_profiles,
    load_json,
    log_record,
    remove_json,
    reset_pins,
    toggle_pins,
    save_json,
    led_flash,
    app_reset,
)

app = Microdot()


@app.before_request
def server_log_request(request: Request):
    log_record(request.url)


######################################################################
# Server API Methods
######################################################################


@app.get("/")
@led_flash
def root(_: Request) -> str:
    return StatusMessage.SUCCESS


@app.get("/scan")
@led_flash
def server_scan(_: Request) -> str:
    return dumps(scan())


@app.get("/network")
@led_flash
def server_network(_: Request) -> str:
    return dumps(NetworkInfo(nic_closure()).json)


@app.get("/reset")
@led_flash
def server_app_reset(_: Request) -> str:
    app_reset()
    return StatusMessage.SUCCESS


######################################################################
# Devices API Methods
######################################################################


@app.get("/devices")
@led_flash
def devices(_: Request) -> str:
    return dumps(get_devices())


@app.put("/devices/toggle/<pins>")
@led_flash
def devices_toggle_pins(_: Request, pins: str) -> str:
    return dumps(toggle_pins(pins))


@app.put("/devices/reset/<pins>")
@led_flash
def devices_reset_pins(_: Request, pins: str) -> str:
    return dumps(reset_pins(pins))


@app.put("/devices/change/<pins>/<device_type>")
@led_flash
def devices_change(_: Request, pins: str, device_type: str) -> str:
    return dumps(change_pins(pins, device_type))


######################################################################
# Profiles API Methods
######################################################################


@app.get("/profiles")
@led_flash
def profiles(_: Request) -> str:
    return dumps(get_profiles())


@app.put("/profiles")
@led_flash
def devices_load_json(request: Request) -> str:
    if request.json is not None:
        return dumps(load_json(request.json))
    else:
        log_record("Found None in profile request")
        raise ValueError


@app.post("/profiles")
@led_flash
def profiles_save(request: Request) -> str:
    if request.json is not None:
        return dumps(save_json(request.json))
    else:
        log_record("Found None in profile request")
        raise ValueError


@app.delete("/profiles")
@led_flash
def profiles_delete(request: Request) -> str:
    if request.json is not None:
        return dumps(remove_json(request.json))
    else:
        log_record("Found None in profile request")
        raise ValueError


######################################################################
# Credentials API Methods
######################################################################


@app.post("/credentials")
@led_flash
def server_save_credentials(request: Request) -> str:
    json = request.json
    if json is None:
        log_record("Credentials were empty")
        return StatusMessage.FAILURE
    else:
        try:
            _save_credentials(json)
            return StatusMessage.SUCCESS
        except KeyError:
            log_record("Credentials had bad keys")
            return StatusMessage.FAILURE
        except Exception as e:
            log_record(f"Failed with {e}")
            return StatusMessage.FAILURE


@app.delete("/credentials")
@led_flash
def server_reset_credentials(_: Request) -> str:
    reset_credentials()
    return StatusMessage.SUCCESS


######################################################################
# Log API Methods
######################################################################


@app.get("/log")
@led_flash
def server_log(_: Request):
    return log_dump()


@app.delete("/log")
@led_flash
def server_log_flush(_: Request):
    log_flush()
    return StatusMessage.SUCCESS


def run() -> None:
    app.run(host="0.0.0.0", port=80)
    ota()
