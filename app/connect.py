import network
from time import sleep

from app.constants import MAX_WAIT
from app.secrets import SSID, PASSWORD


def connect() -> None:
    print('Connecting to Network...')
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

    if wlan.status() != 3:
        raise RuntimeError('Network connection failed.')
    else:
        status = wlan.ifconfig()
        print(f"Connected:{status[0]}")
