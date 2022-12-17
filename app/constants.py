SERVING_ADDRESS: str = "0.0.0.0"
PORT: int = 80
MAX_WAIT: int = 10


class HTTPSignals(object):
    RESPONSE_200: str = 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'


class Signals(object):
    """Class containing key signals for pico webserver."""
    LIGHT_ON: str = "/light/on"
    LIGHT_OFF: str = "/light/off"
