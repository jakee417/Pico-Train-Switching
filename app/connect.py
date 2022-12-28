import network
from time import sleep
from network import WLAN

from app.secrets import (
    AP_SSID,
    AP_PASSWORD,
    SSID,
    PASSWORD,
)

MAX_WAIT: int = 10


def connect() -> WLAN:
    wlan = connect_as_client()

    if wlan.status() != 3:
        print("---- Could not connect as client...")
        wlan = connect_as_access_point()

    status = wlan.ifconfig()
    print(f"---- Connected:")
    print(status[0])
    print(wlan.config("mac"))

    return wlan


def connect_as_access_point() -> WLAN:
    print(f"---- Connecting as access point, SSID: {AP_SSID}")
    wlan = network.WLAN(network.AP_IF)
    wlan.config(essid=AP_SSID, password=AP_PASSWORD)
    wlan.active(True)
    return wlan


def connect_as_client() -> WLAN:
    print("---- Connecting as client...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)

    wait = MAX_WAIT
    while wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        wait -= 1
        print("---- Waiting for connection...")
        sleep(1)

    return wlan
