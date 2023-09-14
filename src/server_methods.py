import os
import gc
import ujson
from machine import reset, Timer
from collections import OrderedDict
from micropython import const

from .config import ota
from .lib.picozero import pico_led
from .train_switch import CLS_MAP, BinaryDevice


# Raspberry Pi Pico W RP2040 layout
GPIO_PINS: set[int] = set(range(29))

# container for holding our devices - load or initialize
devices: OrderedDict[str, BinaryDevice] = OrderedDict({})
pin_pool: set[int] = GPIO_PINS.copy()

# Upon shutdown, this will enable a ota update.
update_flag: bool = False

_PROFILE_FOLDER = const("profiles")
_PROFILE_PATH: str = const(f"./{_PROFILE_FOLDER}/")
if _PROFILE_FOLDER not in os.listdir():
    os.mkdir(_PROFILE_FOLDER)

# TODO: Eventually, we want to send both the device type name and the required
# number of pins. But for now, just give the device type names.
DEVICE_TYPES: list[str] = list(
    {k: {const("requirement"): v.required_pins} for k, v in CLS_MAP.items()}.keys()
)

APP_RESET_WAIT_TIME: int = 3


######################################################################
# API Return Types
######################################################################


class StatusMessage(object):
    SUCCESS: str = "success"
    FAILURE: str = "failure"


class ProfileRequest(object):
    NAME: str = "NAME"


class ResponseKey(object):
    DEVICES: str = "devices"
    PROFILES: str = "profiles"


######################################################################
# API Methods
######################################################################


def get_devices() -> dict[str, list[dict[str, object]]]:
    """Retrieve the current device container."""
    global devices
    return get_return_dict(devices)


def toggle_pins(pins: str) -> dict[str, list[dict[str, object]]]:
    """Toggle the state of a device, or set to "self.on_state" by default."""
    global devices
    _pins = convert_csv_tuples(pins)
    device = devices[str(_pins)]
    if device.state == device.on_state:
        devices[str(_pins)].action(device.off_state)
    else:
        devices[str(_pins)].action(device.on_state)
    return get_return_dict(OrderedDict({const(str(_pins)): devices[str(_pins)]}))


def reset_pins(pins: str) -> dict[str, list[dict[str, object]]]:
    """Reset the state of a device at a given set of pins."""
    global devices
    _pins = convert_csv_tuples(pins)
    devices[str(_pins)].action(None)  # type: ignore
    return get_return_dict(OrderedDict({const(str(_pins)): devices[str(_pins)]}))


def change_pins(pins: str, device_type: str) -> dict[str, list[dict[str, object]]]:
    """Change a device type for a set of pins.

    Notes
    -----
        The current amount of pins must match the new amount of pins.
    """
    global devices
    new_cls = CLS_MAP.get(device_type, None)
    _pins = convert_csv_tuples(pins)

    # Need the new class and ensure the pins were already being used.
    if new_cls is not None and str(_pins) in devices:
        current_device = devices[str(_pins)]
        current_pin_amount = current_device.required_pins

        # Needs the same amount of pins.
        if len(_pins) != new_cls.required_pins:
            raise ValueError(
                f"Not enough pins for {new_cls}. Found {len(_pins)} expected {new_cls.required_pins}"
            )

        # New pin amount should match old pin amount.
        if current_pin_amount != new_cls.required_pins:
            raise ValueError(
                f"Pin amounts do not match. Found {new_cls.required_pins} expected {current_pin_amount}."
            )

        # Perform the change.
        current_device.close()
        new_device = new_cls(pin=_pins)
        devices.update({const(str(_pins)): new_device})
        return get_return_dict(OrderedDict({const(str(_pins)): devices[str(_pins)]}))
    else:
        raise ValueError(
            f"Requested Device Type not found or pins {str(_pins)} were not already in use."
        )


def get_profiles() -> dict[str, list[str]]:
    """Get all the profile names without file extension."""
    profiles = os.listdir(_PROFILE_PATH)
    profiles = [i.split(".")[0] for i in profiles]
    profiles.sort()
    return {const(ResponseKey.PROFILES): profiles}


def load_json(json: dict[str, str]) -> dict[str, list[dict[str, object]]]:
    """Load a JSON profile."""
    global devices
    global pin_pool
    name = read_profile_json(json)
    path: str = _PROFILE_PATH + name + ".json"

    # Load a json string from a file stream.
    with open(path, "r") as f:
        json_str: str = f.read()

    # Load the config as an unordered dictionary.
    _cfg: dict[str, dict[str, object]] = ujson.loads(json_str)
    order = _cfg["order"]

    # Reorder the config with the saved order.
    cfg: OrderedDict[str, dict[str, object]] = OrderedDict({})
    for i in order:
        cfg[i] = _cfg[i]

    # Update the global devices.
    close_devices(devices)  # close out old devices
    devices = construct_from_cfg(cfg)  # start new devices
    pin_pool = update_pin_pool(devices)
    return get_return_dict(devices)


def remove_json(json: dict[str, str]) -> dict[str, list[str]]:
    """Remove a JSON profile."""
    global devices
    name = read_profile_json(json)
    path = _PROFILE_PATH + name + ".json"
    os.remove(path)
    return get_profiles()


def save_json(json: dict[str, str]) -> dict[str, list[str]]:
    """Save a JSON profile."""
    global devices
    name = read_profile_json(json)
    path: str = _PROFILE_PATH + name.strip() + ".json"
    devices_json = devices_to_json(devices)
    order: list[str] = []

    # NOTE: Explicitly save the order of the keys since ujson
    # does not maintain order when decoding.
    for k in devices_json.keys():
        order += [k]

    devices_json["order"] = order  # type: ignore
    with open(path, "w") as f:
        ujson.dump(devices_json, f)
    return get_profiles()


def post(pins: str, device_type: str) -> dict[str, list[dict[str, object]]]:
    """Add a new device."""
    global devices
    device_cls = CLS_MAP.get(device_type, None)
    # device type must be legal
    if device_cls is not None:
        _pins = convert_csv_tuples(pins)
        # pins must be available and not the same
        if all([p in pin_pool for p in _pins]) and len(set(_pins)) == len(_pins):
            added = device_cls(pin=_pins)
            devices.update({const(str(_pins)): added})  # add to global container
            [pin_pool.remove(p) for p in added.pin_list]  # remove availability
            return get_return_dict(devices)
        else:
            raise ValueError("Requested pins were not available or not unique.")
    else:
        raise ValueError("Requested Device Type not found.")


def app_shutdown() -> None:
    shutdown()


def app_reset() -> None:
    shutdown()
    Timer(
        period=APP_RESET_WAIT_TIME * 1000,
        mode=Timer.ONE_SHOT,
        callback=reset_closure,
    )


def app_ota() -> None:
    global update_flag
    shutdown()
    update_flag = True


######################################################################
# API Helper Methods
######################################################################


def get_return_dict(
    devices: OrderedDict[str, BinaryDevice]
) -> dict[str, list[dict[str, object]]]:
    """Return a json-returnable dict for an app call."""
    return {const(ResponseKey.DEVICES): list(devices_to_json(devices).values())}


def devices_to_json(
    devices: OrderedDict[str, BinaryDevice]
) -> OrderedDict[str, dict[str, object]]:
    """Return a serializiable {str(pins): str(device)} mapping of devices."""
    devices_json: OrderedDict[str, dict[str, object]] = OrderedDict({})
    # NOTE: Use __iter__ instead of list comprehension to maintain
    # ordering of OrderedDict.
    for pin, d in devices.items():
        devices_json.update({const(str(pin)): d.to_json()})
    return devices_json


def read_profile_json(json: dict[str, str]) -> str:
    name = json.get(ProfileRequest.NAME, None)
    if name is None:
        raise ValueError("Could not find NAME in profile request.")
    return name


def led_flash(func):
    async def wrapper(*args, **kwargs):
        pico_led.on()
        await func(*args, **kwargs)
        pico_led.off()

    return wrapper


def close_devices(devices: OrderedDict[str, BinaryDevice]) -> None:
    """Close all connections in a dictionary of devices."""
    global pin_pool
    # close all pre existing connections
    for _, device in devices.items():
        device.close()
    del devices
    # reset the pin pool
    pin_pool = update_pin_pool(OrderedDict({}))
    gc.collect()


def close_devices_closure() -> None:
    close_devices(devices)


def construct_from_cfg(
    cfg: OrderedDict[str, dict[str, object]]
) -> OrderedDict[str, BinaryDevice]:
    """Construct a new dictionary of devices from a configuration."""
    # construct switches from config
    devices: OrderedDict[str, BinaryDevice] = OrderedDict({})
    for _, v in cfg.items():
        _pins: tuple[int] = tuple(v["pins"])  # type: ignore
        _k: str = const(str(_pins))
        _v: BinaryDevice = CLS_MAP.get(v["name"])(pin=_pins)  # type: ignore
        devices.update({const(_k): _v})
    # Set states from configuration
    for k, v in devices.items():
        # NOTE: Actually passes an Optional[str]
        v.action(cfg[str(k)]["state"])  # type: ignore
    return devices


def convert_csv_tuples(inputs: str) -> tuple[int, ...]:
    """Convert a comma seperated list of pins."""
    inputs_split: list[str] = inputs.split(",")
    inputs_int: list[int] = [int(input) for input in inputs_split]
    inputs_int.sort()
    return tuple(inputs_int)


def sort_pool(pool: set[int]) -> list[int]:
    _pool = list(pool)
    _pool.sort()
    return _pool


def update_pin_pool(devices: OrderedDict[str, BinaryDevice]) -> set[int]:
    """Update a pool of pins based off current devices."""

    class PinNotInPinPool(Exception):
        """Raised when a pin is accessed that is not available for use."""

        pass

    pin_pool = GPIO_PINS.copy()
    for _, d in devices.items():
        for p in d.pin_list:
            if p not in pin_pool:
                raise PinNotInPinPool(
                    f"pin {p}, {type(p)} was not in pin pool: {pin_pool}."
                )
            pin_pool.remove(p)
    return pin_pool


def shutdown() -> None:
    """Shutdown all devices."""
    close_devices_closure()


def reset_closure(timer: Timer) -> None:
    reset()


def ota_closure() -> None:
    global update_flag
    if update_flag:
        ota()
        update_flag = False
