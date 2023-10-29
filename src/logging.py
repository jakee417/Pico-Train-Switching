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
    _new_record = f"{header}{record}\n"

    if Logging._LOG_FILE not in os.listdir():
        log_new_record(_new_record)
    else:
        add_record(record=_new_record)
        # delete_k_records(k=Logging._MAX_LINES)


def add_record(record: str) -> None:
    """Extend the log file by one record."""
    with open(Logging._LOG_FILE, "a") as f:
        f.write(record)
        f.flush()


def delete_k_records(k: int) -> None:
    """Deletes the first record in the log file."""
    with open(Logging._LOG_FILE, "r") as f:
        lines = f.readlines()
        _delete_lines = max(0, len(lines) - k)
        lines = lines[_delete_lines:]

    with open(Logging._LOG_FILE, "w") as f:
        for line in lines:
            f.write(line)


def log_new_record(record: str) -> None:
    with open(Logging._LOG_FILE, "w") as f:
        f.write(record)


def log_dump():
    def generate_log_stream():
        with open(Logging._LOG_FILE, "r") as f:
            for line in f.readlines():
                yield str(line)

    return generate_log_stream()


def log_flush() -> None:
    if Logging._LOG_FILE in os.listdir():
        os.remove(Logging._LOG_FILE)
