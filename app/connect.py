import os
import time
import network
from time import sleep
from network import WLAN
import binascii
import json

from app.logging import log_record

APP_VERSION = "1.0"
MAX_WAIT: int = 10
AP_IP = "192.168.4.1"
AP_SUBNET = "255.255.255.0"
AP_GATEWAY = "192.168.4.1"
AP_DNS = "0.0.0.0"
AP_PASSWORD = "getready2switchtrains"

CREDENTIAL_FOLDER = "secrets"
CREDENTIAL_PATH = f"./{CREDENTIAL_FOLDER}/secrets.json"
if CREDENTIAL_FOLDER not in os.listdir():
    os.mkdir(CREDENTIAL_FOLDER)

sta: WLAN = network.WLAN(network.STA_IF)
ap: WLAN = network.WLAN(network.AP_IF)

# NIC object that is found at runtime.
NIC: WLAN


def nic_closure() -> WLAN:
    """WLAN object that is being used after `connect()`."""
    global NIC
    return NIC


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


class NetworkInfo(object):
    def __init__(
        self,
        wlan: WLAN,
    ) -> None:
        self.wlan = wlan
        (self.ip, self.subnet_mask, self.gateway, self.dns) = wlan.ifconfig()
        self.mac = self.wlan_mac_address(wlan)
        _hostname: str = self.mac.replace(":", "")
        # NOTE: Hostname size is limited. Possibly need to lengthen
        # if collisions are occuring.
        self.hostname: str = f"Railyard{_hostname[:3]}"
        self.connected: bool = wlan.isconnected()
        self.status: int = wlan.status()

    @staticmethod
    def wlan_mac_address(wlan: WLAN) -> str:
        mac = wlan.config("mac")
        return binascii.hexlify(mac, ":").decode("utf-8")

    @property
    def json(self) -> dict[str, str]:
        return {
            "HOSTNAME": self.hostname,
            "IP": self.ip,
            "MAC": self.mac,
            "CONNECTED": str(self.connected),
            "STATUS": str(self.status),
            "VERSION": APP_VERSION,
        }

    def __repr__(self) -> str:
        return f"""\n
        {self.wlan}
        ++++ Connected: {self.connected}
        ++++ Status: {self.status}
        ++++ HOSTNAME: {self.hostname}
        ++++ IP: {self.ip}
        ++++ SUBNET: {self.subnet_mask}
        ++++ GATEWAY: {self.gateway}
        ++++ DNS: {self.dns}
        ++++ MAC: {self.mac}\n
        """


def scan() -> list[dict[str, str]]:
    return [ScanResult(*s).json for s in sta.scan()]


def _save_credentials(data: dict[str, str]) -> None:
    with open(CREDENTIAL_PATH, "w") as f:
        json.dump(data, f)


def load_credentials() -> dict[str, str]:
    """Load a password from a json file.

    Notes:
        JSON is a single dictionary with schema:
            {
                Credential.SSID: ...,
                Credential.PASSWORD: ...,
            }
    """
    json_str: str = "{}"
    try:
        with open(CREDENTIAL_PATH, "r") as f:
            json_str: str = f.read()
    except OSError as e:
        log_record(f"Found {e}, creating new credentials...")
        _save_credentials({})
    return json.loads(json_str)


def save_credentials(data: dict[str, str]) -> None:
    """Save a ssid and password as a credential.

    Notes:
        See `load_credentials` for schema.
    """
    if Credential.SSID in data and Credential.PASSWORD in data and len(data) == 2:
        _save_credentials(data)
        log_record("Credentials saved...")
    else:
        log_record("Unable to save credentials...")
        raise KeyError


def reset_credentials() -> None:
    with open(CREDENTIAL_PATH, "w") as f:
        json.dump({}, f)
    log_record("Credentials reset...")


def connect() -> None:
    """Connect to a WLAN network.

    First, attempt to connect as a station using provided credentials.
    If this fails, then default to an Access Point using default credentials.
    """
    global NIC
    # Set the global hostname to be a combination of "RailYard" and the
    # devices MAC address to ensure uniqueness.
    network.hostname(NetworkInfo(sta).hostname)
    connect_as_station()

    if sta.status() != 3:
        log_record("Could not connect as client...")
        sta.disconnect()
        sta.active(False)
        connect_as_access_point()
        NIC = ap
    else:
        ap.disconnect()
        ap.active(False)
        NIC = sta

    log_record(f"\n{NetworkInfo(ap)}\n")
    log_record(f"\n{NetworkInfo(sta)}\n")


def connect_as_access_point() -> None:
    log_record(f"Connecting as access point, SSID: {NetworkInfo(ap).hostname}")
    ap.config(
        ssid=NetworkInfo(ap).hostname,
        password=AP_PASSWORD,
    )
    ap.active(True)
    time.sleep(0.1)
    # NOTE: These are the defaults for rp2 port of micropython.
    #   It doesn't seem possible to change these without side-effects.
    ap.ifconfig((AP_IP, AP_SUBNET, AP_GATEWAY, AP_DNS))
    time.sleep(0.1)


def connect_as_station() -> None:
    log_record("Connecting as client...")
    sta.config(ssid=NetworkInfo(ap).hostname)
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
            log_record("Waiting for connection...")
            sleep(1)


def wlan_shutdown() -> None:
    sta.disconnect()
    ap.disconnect()
    sta.active(False)
    ap.active(False)
