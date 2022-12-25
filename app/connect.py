import network
from time import sleep
from network import WLAN

from app.secrets import SSID, PASSWORD

MAX_WAIT: int = 10

def connect() -> None:
    print('Connecting to network as:')
    wlan = connect_as_client()
    if wlan.status() != 3:
        raise RuntimeError('Network connection failed.')
    else:
        status = wlan.ifconfig()
        print(f"Connected: \n{status[0]}")

def connect_as_access_point() -> WLAN:
    print("access point")
    wlan = network.WLAN(network.AP_IF)
    wlan.config(essid=SSID, password=PASSWORD)
    wlan.active(True)
    return wlan

def connect_as_client() -> WLAN:
    print('client')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)

    max_wait = MAX_WAIT
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('Waiting for connection...')
        sleep(1)

    return wlan
