import network
from time import sleep
from network import WLAN
import binascii
import json

MAX_WAIT: int = 10
AP_SSID = "RailYard"
AP_PASSWORD = "password"
CREDENTIAL_PATH = "./app/secrets.json"

sta: WLAN = network.WLAN(network.STA_IF)
ap: WLAN = network.WLAN(network.AP_IF)
sta.active(False)
ap.active(False)
ap.ifconfig(("192.168.4.1", "255.255.255.0", "192.168.0.1", "1.1.1.1"))


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
    return [ScanResult(*s).json for s in sta.scan()]


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
    if Credential.SSID in data and Credential.PASSWORD in data and len(data) == 2:
        with open(CREDENTIAL_PATH, "w") as f:
            json.dump(data, f)
        print("---- Credentials saved...")
    else:
        print("---- Unable to save credentials...")
        raise KeyError


def reset_credentials() -> None:
    with open(CREDENTIAL_PATH, "w") as f:
        json.dump({}, f)
    print("---- Credentials reset...")


def connect() -> None:
    """Connect to a WLAN network.

    First, attempt to connect as a station using provided credentials.
    If this fails, then default to an Access Point using default credentials.
    """
    connect_as_station()

    if sta.status() != 3:
        print("---- Could not connect as client...")
        sta.disconnect()
        sta.active(False)
        connect_as_access_point()
    else:
        ap.disconnect()
        ap.active(False)

    print_wlan_info(ap)
    print_wlan_info(sta)


def connect_as_access_point():
    print(f"---- Connecting as access point, SSID: {AP_SSID}")
    ap.config(essid=AP_SSID, password=AP_PASSWORD)
    ap.active(True)


def connect_as_station():
    print("---- Connecting as client...")
    sta.active(True)

    # Load the cached ssid/password.
    ssid_info = load_credentials()
    ssid = ssid_info.get(Credential.SSID, None)
    password = ssid_info.get(Credential.PASSWORD, None)

    if ssid is not None and password is not None:
        sta.connect(ssid, password)
        wait = MAX_WAIT
        while wait > 0:
            if sta.status() < 0 or sta.status() >= 3:
                break
            wait -= 1
            print("---- Waiting for connection...")
            sleep(1)


def wlan_shutdown() -> None:
    sta.disconnect()
    ap.disconnect()
    sta.active(False)
    ap.active(False)


def wlan_mac_address(wlan: WLAN) -> str:
    mac = wlan.config("mac")
    return binascii.hexlify(mac, ":").decode("utf-8")


def print_wlan_info(wlan: WLAN) -> None:
    print(f"\n{wlan}")
    print(f"++++ Connected: {wlan.isconnected()}")
    print(f"++++ Status: {wlan.status()}")
    print(f"++++ IP: {wlan.ifconfig()[0]}")
    print(f"++++ MAC: {wlan_mac_address(wlan)}")
