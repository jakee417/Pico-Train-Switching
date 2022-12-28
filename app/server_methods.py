import os
import ujson
from collections import OrderedDict

from app.train_switch import CLS_MAP, BinaryDevice

# Raspberry Pi Pico W RP2040 layout
GPIO_PINS: set[int] = set(range(29))

# container for holding our devices - load or initialize
devices: OrderedDict[str, BinaryDevice] = OrderedDict({})
pin_pool: set[int] = GPIO_PINS.copy()

PROFILE_PATH = "./app/profiles/"
DEFAULT_PATH = PROFILE_PATH + "cfg.json"

# TODO: Eventually, we want to send both the device type name and the required
# number of pins. But for now, just give the device type names.
DEVICE_TYPES: list[str] = list(
    {
        k: {
            "requirement": v.required_pins
        }
        for k, v in CLS_MAP.items()
    }.keys()
)

######################################################################
# API Methods
######################################################################


def get() -> dict[str, object]:
    """Retrives the current device container."""
    global devices
    global pin_pool
    return app_return_dict(devices, sort_pool(pin_pool), DEVICE_TYPES)


def save_json(name: str) -> dict[str, object]:
    """Saves a JSON profile."""
    global devices
    global pin_pool
    path: str = PROFILE_PATH + name.strip() + ".json"
    devices_json = devices_to_json(devices)
    order: list[str] = []

    # NOTE: Explicitly save the order of the keys since ujson
    # does not maintain order when decoding.
    for k in devices_json.keys():
        order += [k]

    devices_json["order"] = order  # type: ignore

    with open(path, "w") as f:
        ujson.dump(devices_json, f)
    print(f"++++ saved devices: {devices_json} as {path}")
    return app_return_dict(devices, sort_pool(pin_pool), DEVICE_TYPES)


def load_json(name: str) -> dict[str, object]:
    """Loads a JSON profile."""
    global devices
    global pin_pool
    path: str = PROFILE_PATH + name + ".json"

    # Load a json string from a file stream.
    print(f"++++ JSON path: {path}")
    with open(path, "r") as f:
        json_str: str = f.read()
        print(f"++++ Loading JSON: {json_str}")

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
    print(f"++++ loaded devices: {devices}")
    pin_pool = update_pin_pool(devices)
    return app_return_dict(devices, sort_pool(pin_pool), DEVICE_TYPES)


def remove_json(name: str) -> dict[str, object]:
    """Removes a JSON profile."""
    global devices
    global pin_pool
    path = PROFILE_PATH + name + ".json"
    os.remove(path)
    print(f"++++ Removed file: {path}")
    return app_return_dict(devices, sort_pool(pin_pool), DEVICE_TYPES)


def toggle_index(device: int) -> dict[str, object]:
    """Toggle the state of a device, or set to "self.on_state" by default."""
    global devices
    global pin_pool
    device -= 1  # user will see devices as 1-indexed, convert to 0-indexed
    order = [k for k, _ in devices.items()]  # get ordering of pins
    pins = order[device]
    on_state: str = devices[str(pins)].on_state
    off_state: str = devices[str(pins)].off_state
    if devices[pins].state == on_state:
        devices[str(pins)].action(off_state)
    else:
        devices[str(pins)].action(on_state)
    return app_return_dict(devices, sort_pool(pin_pool), DEVICE_TYPES)


def reset_index(device: int) -> dict[str, object]:
    """Resets the state of a device."""
    global devices
    global pin_pool
    device -= 1  # user will see devices as 1-indexed, convert to 0-indexed
    order = [k for k, _ in devices.items()]  # get ordering of pins
    pins = order[device]
    devices[pins].action(None) # type: ignore
    return app_return_dict(devices, sort_pool(pin_pool), DEVICE_TYPES)


def toggle_pins(pins: str) -> dict[str, object]:
    """Toggle the state of a device, or set to "self.on_state" by default."""
    global devices
    global pin_pool
    _pins = convert_csv_tuples(pins)
    on_state = devices[str(_pins)].on_state
    off_state = devices[str(_pins)].off_state
    if devices[str(_pins)].state == on_state:
        devices[str(_pins)].action(off_state)
    else:
        devices[str(_pins)].action(on_state)
    return app_return_dict(devices, sort_pool(pin_pool), DEVICE_TYPES)


def delete(pins: str) -> dict[str, object]:
    """Deletes a device."""
    global devices
    global pin_pool
    _pins = convert_csv_tuples(pins)
    deleted = devices.pop(str(_pins), None)
    if deleted:
        deleted.close()
        # add the pins back into the pool
        [pin_pool.add(p) for p in deleted.pin_list]
    return app_return_dict(devices, sort_pool(pin_pool), DEVICE_TYPES)


def post(pins: str, device_type: str) -> dict[str, object]:
    """Adds a new device."""
    global devices
    global pin_pool
    device_cls = CLS_MAP.get(device_type, None)
    # device type must be legal
    if device_cls is not None:
        _pins = convert_csv_tuples(pins)
        # pins must be available and not the same
        if all([p in pin_pool for p in _pins]) and len(set(_pins)) == len(_pins):
            added = device_cls(pin=_pins)
            devices.update({str(_pins): added})  # add to global container
            [pin_pool.remove(p) for p in added.pin_list]  # remove availability
    return app_return_dict(devices, sort_pool(pin_pool), DEVICE_TYPES)


######################################################################
# API Helper Methods
######################################################################
class PinNotInPinPool(Exception):
    """Raised when a pin is accessed that is not available for use."""
    pass


def close_devices(devices: OrderedDict[str, BinaryDevice]) -> None:
    """Close all connections in a dictionary of devices."""
    # close all pre existing connections
    for _, device in devices.items():
        device.close()
    del devices  # garbage collect


def close_devices_closure() -> None:
    close_devices(devices)


def construct_from_cfg(
    cfg: OrderedDict[str, dict[str, object]]
) -> OrderedDict[str, BinaryDevice]:
    """Constructs a new dictionary of devices from a configuration."""
    # construct switches from config
    devices: OrderedDict[str, BinaryDevice] = OrderedDict({})
    for _, v in cfg.items():
        _pins: tuple[int] = tuple(v["pins"])  # type: ignore
        _k: str = str(_pins)
        _v: BinaryDevice = CLS_MAP.get(v["name"])(pin=_pins)  # type: ignore
        devices.update({_k: _v})
    # Set states from configuration
    for k, v in devices.items():
        v.action(str(cfg[str(k)]["state"]))
    return devices


def convert_csv_tuples(inputs: str) -> tuple[int]:
    """Converts a comma seperated list of pins."""
    inputs_split: list[str] = inputs.split(",")
    inputs_int: list[int] = [int(input) for input in inputs_split]
    inputs_int.sort()
    return tuple(inputs_int)


def sort_pool(pool: set[int]) -> list[int]:
    l = list(pool)
    l.sort()
    return l


def devices_to_json(
    devices: OrderedDict[str, BinaryDevice]
) -> OrderedDict[str, dict[str, object]]:
    """Returns a serializiable {str(pins): str(device)} mapping of devices."""
    devices_json: OrderedDict[str, dict[str, object]] = OrderedDict({})
    # NOTE: Use __iter__ instead of list comprehension to maintain
    # ordering of OrderedDict.
    for pin, d in devices.items():
        devices_json.update(
            {str(pin): d.to_json()}
        )
    return devices_json


def get_all_profiles() -> list[str]:
    """Gets all of the profile names without file extension."""
    profiles = os.listdir(PROFILE_PATH)
    profiles = [i.split(".")[0] for i in profiles]
    profiles.sort()
    return profiles


def app_return_dict(
    devices: OrderedDict[str, BinaryDevice],
    pin_pool: list[int],
    device_types: list[str]
) -> dict[str, object]:
    """Returns a json-returnable dict for an app call."""
    devices_json = devices_to_json(devices)
    return {
        "devices": list(devices_json.values()),
        "pin_pool": pin_pool,
        # "device_types": device_types,
        "profiles": get_all_profiles()
    }


def update_pin_pool(devices: OrderedDict[str, BinaryDevice]) -> set[int]:
    """Update a pool of pins based off current devices."""
    pin_pool = GPIO_PINS.copy()
    for _, d in devices.items():
        for p in d.pin_list:
            if p not in pin_pool:
                raise PinNotInPinPool(
                    f"pin {p}, {type(p)} was not in pin pool: {pin_pool}."
                )
            pin_pool.remove(p)
    return pin_pool
