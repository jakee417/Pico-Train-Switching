from machine import Timer

from .logging import log_record


_TIMER = Timer()
_timer_actions: dict[int, object] = {}
_timer_times: dict[int, int] = {}

PERIOD_BUFFER = const(1500)


def _timer_callback(timer: Timer) -> None:
    for _, v in _timer_actions.items():
        v(timer)  # type: ignore


def _total_time() -> int:
    return sum([i for i in _timer_times.values()])


def start_timer() -> None:
    if len(_timer_actions) > 0:
        period = PERIOD_BUFFER + _total_time()
        log_record(
            f"Starting timer with {len(_timer_actions)} action(s)"
            + f" w/ period: {period}"
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


def enqueue_to_timer(id: int, callback_time: int, callback) -> None:
    """Add an action to the timer."""
    stop_timer()
    _timer_actions[id] = callback
    _timer_times[id] = callback_time
    start_timer()


def dequeue_from_timer(id: int) -> None:
    stop_timer()
    del _timer_actions[id]
    start_timer()
