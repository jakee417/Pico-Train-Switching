import os
import time
import network
from time import sleep
from network import WLAN
from micropython import const
import binascii
import json


_APP_VERSION = const("1.0")
_MAX_WAIT: int = const(10)
_AP_IP = const("192.168.4.1")
_AP_SUBNET = const("255.255.255.0")
_AP_GATEWAY = const("192.168.4.1")
_AP_DNS = const("0.0.0.0")
_AP_PASSWORD = const("getready2switchtrains")

_CREDENTIAL_FOLDER = const("secrets")
_CREDENTIAL_PATH = f"./{_CREDENTIAL_FOLDER}/secrets.json"
if _CREDENTIAL_FOLDER not in os.listdir():
    os.mkdir(_CREDENTIAL_FOLDER)

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
            const("SSID"): self.ssid,
            const("BSSID"): self.bssid,
            const("CHANNEL"): self.channel,
            const("RSSI"): self.RSSI,
            const("SECURITY"): self.security,
            const("HIDDEN"): self.hidden,
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
        self.hostname: str = f"Railyard{_hostname[-6:]}"
        self.connected: bool = wlan.isconnected()
        self.status: int = wlan.status()

    @staticmethod
    def wlan_mac_address(wlan: WLAN) -> str:
        mac = wlan.config("mac")
        return binascii.hexlify(mac, ":").decode("utf-8")

    @property
    def json(self) -> dict[str, str]:
        return {
            const("HOSTNAME"): self.hostname,
            const("IP"): self.ip,
            const("MAC"): self.mac,
            const("CONNECTED"): str(self.connected),
            const("STATUS"): str(self.status),
            const("VERSION"): _APP_VERSION,
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
    with open(_CREDENTIAL_PATH, "w") as f:
        json.dump(data, f)


def load_credentials() -> dict[str, str]:
    """Load a password from a json file.

    Notes
    -----
        JSON is a single dictionary with schema:
            {
                Credential.SSID: ...,
                Credential.PASSWORD: ...,
            }
    """
    json_str: str = "{}"
    try:
        with open(_CREDENTIAL_PATH, "r") as f:
            json_str: str = f.read()
    except OSError:
        _save_credentials({})
    return json.loads(json_str)


def save_credentials(data: dict[str, str]) -> None:
    """Save a ssid and password as a credential.

    Notes
    -----
        See `load_credentials` for schema.
    """
    if Credential.SSID in data and Credential.PASSWORD in data and len(data) == 2:
        _save_credentials(data)
    else:
        raise KeyError


def reset_credentials() -> None:
    with open(_CREDENTIAL_PATH, "w") as f:
        json.dump({}, f)


def connect() -> None:
    """Connect to a WLAN network.

    First, attempt to connect as a station using provided credentials.
    If this fails, then default to an Access Point using default credentials.
    """
    global NIC
    # Set the global hostname to be a combination of "RailYard" and the
    # devices MAC address to ensure uniqueness.
    network.hostname(NetworkInfo(sta).hostname)  # type: ignore
    connect_as_station()

    if sta.status() != 3:
        sta.disconnect()
        sta.active(False)
        connect_as_access_point()
        NIC = ap
    else:
        ap.disconnect()
        ap.active(False)
        NIC = sta


def connect_as_access_point() -> None:
    ap.config(
        ssid=NetworkInfo(ap).hostname,
        password=_AP_PASSWORD,
    )
    ap.active(True)
    time.sleep(0.1)
    # NOTE: These are the defaults for rp2 port of micropython.
    #   It doesn't seem possible to change these without side-effects.
    ap.ifconfig((_AP_IP, _AP_SUBNET, _AP_GATEWAY, _AP_DNS))
    time.sleep(0.1)


def connect_as_station() -> None:
    sta.config(ssid=NetworkInfo(ap).hostname)
    sta.active(True)

    # Load the cached ssid/password.
    ssid_info = load_credentials()
    ssid = ssid_info.get(Credential.SSID, None)
    password = ssid_info.get(Credential.PASSWORD, None)

    if ssid is not None and password is not None:
        sta.connect(ssid, password)
        wait = _MAX_WAIT
        while wait > 0:
            if sta.status() < 0 or sta.status() >= 3:
                break
            wait -= 1
            sleep(1)


def wlan_shutdown() -> None:
    sta.disconnect()
    ap.disconnect()
    sta.active(False)
    ap.active(False)
