import os
import time

LOG_FILE = "log.txt"


def log_record(record: str) -> None:
    f = open(LOG_FILE, "a")
    year, month, mday, hour, minute, second, _, _ = time.localtime()
    f.write(f"{year}:{month}:{mday}::{hour}:{minute}:{second}@ {record}\n")
    f.close()


def log_dump():
    def generate_log_stream():
        with open(LOG_FILE) as f:
            for line in f.readlines():
                yield str(line)

    return generate_log_stream()


def log_flush() -> None:
    if LOG_FILE in os.listdir():
        os.remove(LOG_FILE)
