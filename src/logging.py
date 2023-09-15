import os
import time
from micropython import const


class Logging:
    """Singleton for logging attributes/constants."""
    _LOG_FILE: str = const("log.txt")
    _MAX_LINES: int = const(30)


def log_record(record: str) -> None:
    year, month, mday, hour, minute, second, _, _ = time.localtime()
    header = f"{year}:{month}:{mday}::{hour}:{minute}:{second}@ "

    if Logging._LOG_FILE not in os.listdir():
        log_new_record(f"{header}{record}\n")

    with open(Logging._LOG_FILE, "r") as f_read:
        data = f_read.read().splitlines(True)
        data.append(f"{header}{record}\n")
    if len(data) > Logging._MAX_LINES:
        data = data[1:]
    with open(Logging._LOG_FILE, "w") as f_write:
        for line in data:
            f_write.write(line)


def log_new_record(record: str) -> None:
    with open(Logging._LOG_FILE, "w") as f_write:
        f_write.write(record)
    return


def log_dump():
    def generate_log_stream():
        with open(Logging._LOG_FILE, "r") as f:
            for line in f.readlines():
                yield str(line)

    return generate_log_stream()


def log_flush() -> None:
    if Logging._LOG_FILE in os.listdir():
        os.remove(Logging._LOG_FILE)
