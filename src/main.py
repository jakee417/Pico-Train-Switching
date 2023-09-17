from .connect import connect
from .microdot_server import run as _run
from .server_methods import post


def run() -> None:
    # [1] Connect to wifi network
    connect()
    # [2] Setup pins
    post("0,1", "relay")    # 1
    post("2,3", "relay")    # 2
    post("4,5", "relay")    # 3
    post("6,7", "relay")    # 4
    post("8,9", "relay")    # 5
    post("10,11", "relay")  # 6
    post("12,13", "relay")  # 7
    post("14,15", "relay")  # 8
    post("16,17", "relay")  # 19
    post("18,19", "relay")  # 10
    post("20,21", "relay")  # 11
    post("22,26", "relay")  # 12
    post("27,28", "relay")  # 13
    # [3] Start webserver
    _run()


if __name__ == "__main__":
    run()
