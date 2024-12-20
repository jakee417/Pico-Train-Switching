from collections import deque
from machine import Pin
import time
from neopixel import NeoPixel as NeoPixel
from .lib.picozero import pico_led

INTENSITY = 10
MIRROR = (INTENSITY,) * 3
LIGHT = (INTENSITY, 0, 0)
LIGHT2 = (0, INTENSITY, 0)
DARK = (0, 0, 0)
RESET_TIME = 2000


def flash() -> None:
    pico_led.on()
    time.sleep_ms(100)
    pico_led.off()


def bounce_index(i: int, n: int) -> int:
    return n - 1 - abs((i % (2 * (n - 1))) - (n - 1))


def send_light_beams(
    longer: NeoPixel,
    shorter: NeoPixel,
    delay: int,
    beam_length: int,
) -> None:
    # Setup trackers
    i = 0
    q_1 = deque([], beam_length + 1)
    q_2 = deque([], beam_length + 1)
    # iterate through pixels with chaser.
    while q_1 or i == 0:
        # Enforce beam length
        if len(q_1) >= beam_length:
            j = q_1.popleft()
            if j is not None:
                longer[j] = DARK
                longer.write()
        if len(q_2) >= beam_length:
            j = q_2.popleft()
            if j is not None:
                shorter[j] = DARK
                shorter.write()

        # Preset mirror - may get overwritten
        shorter[shorter.n - 1] = MIRROR

        # Update longer light
        if i < longer.n + 1:
            # Proceed as normal.
            if i < 8:
                q_1.append(i)
                longer[i] = LIGHT2
                longer.write()
            # Jump to the shorter pixel to imitate a bounce.
            elif i == 8:
                q_1.append(None)
                shorter[shorter.n - 1] = LIGHT2
                shorter.write()
            # Account for the spot we skipped.
            else:
                q_1.append(i - 1)
                longer[i - 1] = LIGHT2
                longer.write()

        # Update shorter light
        if i < 13:
            k = bounce_index(i, shorter.n)
            q_2.append(k)
            shorter[k] = LIGHT
            shorter.write()

        # Flash this position for delay
        time.sleep_ms(delay)
        i += 1


def pre_warm(
    longer: NeoPixel,
    shorter: NeoPixel,
) -> None:
    longer.fill(LIGHT2)
    shorter.fill(LIGHT)
    shorter[shorter.n - 1] = MIRROR
    longer.write()
    shorter.write()


def clear(
    longer: NeoPixel,
    shorter: NeoPixel,
) -> None:
    longer.fill(DARK)
    shorter.fill(DARK)
    longer.write()
    shorter.write()


def run_light_beam() -> None:
    flash()
    pixels_1 = NeoPixel(pin=Pin(0, Pin.OUT), n=7)
    pixels_2 = NeoPixel(pin=Pin(2, Pin.OUT), n=16)
    flash()
    pre_warm(
        longer=pixels_2,
        shorter=pixels_1,
    )
    time.sleep_ms(RESET_TIME)
    while True:
        clear(
            longer=pixels_2,
            shorter=pixels_1,
        )
        send_light_beams(
            longer=pixels_2,
            shorter=pixels_1,
            delay=200,
            beam_length=1,
        )
        clear(
            longer=pixels_2,
            shorter=pixels_1,
        )
        time.sleep_ms(RESET_TIME)
        pre_warm(
            longer=pixels_2,
            shorter=pixels_1,
        )
        time.sleep_ms(RESET_TIME)
