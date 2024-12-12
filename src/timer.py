from machine import Timer

from .logging import log_record


_TIMER = Timer()
_timer_actions: dict[int, object] = {}

SECONDS_PER_ACTION: float = 2
SECONDS_TO_MILLISECONDS = const(1000)


def _timer_callback(timer: Timer) -> None:
    for _, v in _timer_actions.items():
        v(timer)  # type: ignore


def start_timer() -> None:
    if len(_timer_actions) > 0:
        period = int(SECONDS_PER_ACTION * SECONDS_TO_MILLISECONDS)
        period *= len(_timer_actions)
        log_record(
            f"Starting timer with {len(_timer_actions)} action(s) & period {period}"
        )
        _TIMER.init(
            mode=Timer.PERIODIC,
            period=period,
            callback=_timer_callback,
        )
    else:
        log_record("No timer actions found, skipping start timer")
        stop_timer()


def stop_timer() -> None:
    log_record("Stopping timer")
    _TIMER.deinit()


def enqueue_to_timer(id: int, callback) -> None:
    """Add an action to the timer.

    Notes:
        Ensure each action takes less than SECONDS_PER_ACTION seconds to
        avoid locking the thread.
    """
    stop_timer()
    _timer_actions[id] = callback
    start_timer()


def dequeue_from_timer(id: int) -> None:
    stop_timer()
    del _timer_actions[id]
    start_timer()
