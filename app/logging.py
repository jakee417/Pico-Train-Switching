import os
import time

LOG_FILE = "log.txt"
MAX_LINES: int = 30


def log_record(record: str) -> None:
    year, month, mday, hour, minute, second, _, _ = time.localtime()
    header = f"{year}:{month}:{mday}::{hour}:{minute}:{second}@ "

    if LOG_FILE not in os.listdir():
        log_new_record(f"{header}{record}\n")

    with open(LOG_FILE, "r") as f_read:
        data = f_read.read().splitlines(True)
        data.append(f"{header}{record}\n")
    if len(data) > MAX_LINES:
        data = data[1:]
    with open(LOG_FILE, "w") as f_write:
        for line in data:
            f_write.write(line)


def log_new_record(record: str) -> None:
    with open(LOG_FILE, "w") as f_write:
        f_write.write(record)
    return


def log_dump():
    def generate_log_stream():
        with open(LOG_FILE, "r") as f:
            for line in f.readlines():
                yield str(line)

    return generate_log_stream()


def log_flush() -> None:
    if LOG_FILE in os.listdir():
        os.remove(LOG_FILE)
