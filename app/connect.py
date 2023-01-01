import network
from time import sleep
from network import WLAN
import binascii
import json

MAX_WAIT: int = 10
AP_SSID = "RailYard"
AP_PASSWORD = "password"
CREDENTIAL_PATH = "./app/secrets.json"


class Credential(object):
    SSID: str = "SSID"
    PASSWORD: str = "PASSWORD"


class ScanResult(object):
    def __init__(
        self,
        ssid: bytes,
        bssid: bytes,
        channel: int,
        RSSI: int,
        security: int,
        hidden: int,
    ):
        self.ssid: str = ssid.decode("utf-8")
        self.bssid: str = binascii.hexlify(bssid).decode("utf-8")
        self.channel = str(channel)
        self.RSSI = str(RSSI)
        self.security = str(security)
        self.hidden = str(hidden)

    @property
    def json(self) -> dict[str, str]:
        return {
            "SSID": self.ssid,
            "BSSID": self.bssid,
            "CHANNEL": self.channel,
            "RSSI": self.RSSI,
            "SECURITY": self.security,
            "HIDDEN": self.hidden,
        }


def scan() -> list[dict[str, str]]:
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    return [
        ScanResult(*s).json for s in wlan.scan()
    ]


def load_credentials() -> dict[str, str]:
    """Load a password from a json file.

    Notes:
        JSON is a single dictionary with schema:
            {
                Credential.SSID: ...,
                Credential.PASSWORD: ...,
            }
    """
    with open(CREDENTIAL_PATH, "r") as f:
        json_str: str = f.read()
    return json.loads(json_str)


def save_credentials(data: dict[str, str]) -> None:
    """Save a ssid and password as a credential.

    Notes:
        See `load_credentials` for schema.
    """
    if (
        Credential.SSID in data
        and Credential.PASSWORD in data
        and len(data) == 2
    ):
        with open(CREDENTIAL_PATH, "w") as f:
            json.dump(data, f)
        print("---- Credentials saved...")
    else:
        print("---- Unable to save credentials...")
        raise KeyError


def connect() -> WLAN:
    wlan = connect_as_client()

    if wlan.status() != 3:
        print("---- Could not connect as client...")
        wlan = connect_as_access_point()

    status = wlan.ifconfig()
    print(f"---- Connected:")
    print(status[0])
    mac = binascii.hexlify(wlan.config("mac")).decode("utf-8")
    print(mac)
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

    # Load the cached ssid/password.
    ssid_info = load_credentials()

    ssid = ssid_info.get(Credential.SSID, None)
    password = ssid_info.get(Credential.PASSWORD, None)

    if ssid is None or password is None:
        return wlan
    else:
        wlan.connect(ssid, password)
        wait = MAX_WAIT
        while wait > 0:
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            wait -= 1
            print("---- Waiting for connection...")
            sleep(1)
        return wlan
