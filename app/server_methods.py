import os
import json
from collections import OrderedDict

from app.train_switch import CLS_MAP, BinaryDevice

# Raspberry Pi Pico W RP2040 layout
GPIO_PINS: set[int] = set(
    [
        1,  2,      4,  5,
        6,  7,  8,  9, 10,
        11, 12,     14, 15,
        16, 17,     19, 20,
        21, 22,     24, 25,
        26, 27, 29,
        31, 32,     34,
    ]
)

# container for holding our devices - load or initialize
devices: dict = OrderedDict({})
pin_pool: set = GPIO_PINS.copy()

PROFILE_PATH = './app/profiles/'
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


def get() -> dict:
    return app_return_dict(devices, sort_pool(pin_pool), DEVICE_TYPES)


def save_json(name: str) -> dict:
    global devices
    path: str = PROFILE_PATH + name.strip() + ".json"
    with open(path, 'w') as f:
        json.dump(devices, f)
    print(f'++++ saved devices: {devices} as {path}')
    return app_return_dict(devices, sort_pool(pin_pool), DEVICE_TYPES)


def load_json(name: str) -> dict:
    global devices
    global pin_pool
    path: str = PROFILE_PATH + name + ".json"
    cfg = None
    print(f"load {path}")
    with open(path, 'r') as f:
        cfg = json.load(f)
    if cfg is not None:
        close_devices(devices)  # close out old devices
        devices = construct_from_cfg(cfg)  # start new devices
        print(f'++++ loaded devices: {devices}')
        pin_pool = update_pin_pool(devices)
    return app_return_dict(devices, sort_pool(pin_pool), DEVICE_TYPES)


def close_devices(devices: dict) -> None:
    """Close all connections in a dictionary of devices."""
    # close all pre existing connections
    for _, device in devices.items():
        device.close()
    del devices  # garbage collect

def construct_from_cfg(cfg: OrderedDict) -> OrderedDict:
    """Constructs a new dictionary of devices from a configuration."""
    # construct switches from config
    devices = OrderedDict({
        str(v['pins']): CLS_MAP.get(v['name'])(pin=v['pins']) 
        for _, v 
        in cfg.items()
	})
    # Set states from configuration
    _ = [v.action(cfg[str(p)]['state']) for p, v in devices.items()]
    return devices


def remove_json(name: str) -> dict:
    path = PROFILE_PATH + name + ".json"
    os.remove(path)
    print(f"++++ Removed file: {path}")
    return app_return_dict(devices, sort_pool(pin_pool), DEVICE_TYPES)


def toggle_index(device: int) -> dict:
    """Toggle the state of a device, or set to 'self.on_state' by default."""
    global devices
    device -= 1  # user will see devices as 1-indexed, convert to 0-indexed
    order = [k for k, _ in devices.items()]  # get ordering of pins
    pins = order[device]
    on_state = devices[str(pins)].on_state
    off_state = devices[str(pins)].off_state
    if devices[pins].state == on_state:
        devices[str(pins)].action(off_state)
    else:
        devices[str(pins)].action(on_state)
    return app_return_dict(devices, sort_pool(pin_pool), DEVICE_TYPES)


def reset_index(device: int) -> dict:
    """Resets the state of a device."""
    global devices
    device -= 1  # user will see devices as 1-indexed, convert to 0-indexed
    order = [k for k, v in devices.items()]  # get ordering of pins
    pins = order[device]
    devices[pins].state = None
    return app_return_dict(devices, sort_pool(pin_pool), DEVICE_TYPES)


def toggle_pins(pins: str) -> dict:
    """Toggle the state of a device, or set to 'self.on_state' by default."""
    global devices
    _pins = convert_csv_tuples(pins)
    on_state = devices[str(_pins)].on_state
    off_state = devices[str(_pins)].off_state
    if devices[str(_pins)].state == on_state:
        devices[str(_pins)].action(off_state)
    else:
        devices[str(_pins)].action(on_state)
    return app_return_dict(devices, sort_pool(pin_pool), DEVICE_TYPES)


def delete(pins: str) -> dict:
    """Deletes a device."""
    _pins = convert_csv_tuples(pins)
    deleted = devices.pop(str(_pins), None)
    if deleted:
        deleted.close()
        # add the pins back into the pool
        [pin_pool.add(p) for p in deleted.pin_list]
    return app_return_dict(devices, sort_pool(pin_pool), DEVICE_TYPES)


def post(pins: str, device_type: str) -> dict:
    """Adds a new device."""
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


class PinNotInPinPool(Exception):
    """Raised when a pin is accessed that is not available for use."""
    pass


def convert_csv_tuples(inputs: str) -> tuple[int]:
    """Converts a comma seperated list of pins into a python object."""
    inputs_split: list[str] = inputs.split(',')
    inputs_int: list[int] = [int(input) for input in inputs_split]
    inputs_int.sort()
    return tuple(inputs_int)


def sort_pool(pool: set) -> list:
    l = list(pool)
    l.sort()
    return l


def devices_to_dict(devices: dict) -> dict:
    """Returns a serializiable {str(pins): str(device)} mapping of devices."""
    return OrderedDict({
        str(pin): d.to_json()
        for pin, d in devices.items()
    })


def get_all_profiles() -> list:
    """Gets all of the profile names without file extension."""
    profiles = os.listdir(PROFILE_PATH)
    profiles = [i.split('.')[0] for i in profiles]
    profiles.sort()
    return profiles


def app_return_dict(
    devices: dict,
    pin_pool: list,
    device_types: list[str]
) -> dict:
    """Returns a json-returnable dict for an app call."""
    device_map = devices_to_dict(devices)
    return {
        "devices": list(device_map.values()),
        "pin_pool": pin_pool,
        # "device_types": device_types,
        "profiles": get_all_profiles()
    }


def update_pin_pool(devices: dict) -> set:
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
