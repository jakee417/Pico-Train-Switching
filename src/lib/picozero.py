from machine import Pin, PWM, Timer
from time import sleep

###############################################################################
# EXCEPTIONS
###############################################################################


class PWMChannelAlreadyInUse(Exception):
    pass


class EventFailedScheduleQueueFull(Exception):
    pass


###############################################################################
# SUPPORTING CLASSES
###############################################################################


def clamp(n, low, high):
    return max(low, min(n, high))


class PinMixin:
    """
    Mixin used by devices that have a single pin number.
    """

    _pin_num: int

    @property
    def pin(self):
        """
        Returns the pin number used by the device.
        """
        return self._pin_num

    def __str__(self):
        return "{} (pin {})".format(self.__class__.__name__, self._pin_num)


class PinsMixin:
    """
    Mixin used by devices that use multiple pins.
    """

    _pin_nums: tuple[int, ...]

    @property
    def pins(self):
        """
        Returns a tuple of pins used by the device.
        """
        return self._pin_nums

    def __str__(self):
        return "{} (pins - {})".format(self.__class__.__name__, self._pin_nums)


class ValueChange:
    """
    Internal class to control the value of an output device.

    :param OutputDevice output_device:
        The OutputDevice object you wish to change the value of.

    :param generator:
        A generator function that yields a 2d list of
        ((value, seconds), *).

        The output_device's value will be set for the number of
        seconds.

    :param int n:
        The number of times to repeat the sequence. If None, the
        sequence will repeat forever.

    :param bool wait:
        If True the ValueChange object will block (wait) until
        the sequence has completed.
    """

    def __init__(self, output_device, generator, n, wait):
        self._output_device = output_device
        self._generator = generator
        self._n = n

        self._gen = self._generator()

        self._timer = Timer()
        self._running = True
        self._wait = wait

        self._set_value()

    def _set_value(self, timer_obj=None):
        if self._wait:
            # wait for the exection to end
            next_seq = self._get_value()
            while next_seq is not None:
                value, seconds = next_seq

                self._output_device._write(value)
                sleep(seconds)

                next_seq = self._get_value()

        else:
            # run the timer
            next_seq = self._get_value()
            if next_seq is not None:
                value, seconds = next_seq

                self._output_device._write(value)
                self._timer.init(
                    period=int(seconds * 1000),
                    mode=Timer.ONE_SHOT,
                    callback=self._set_value,
                )

        if next_seq is None:
            # the sequence has finished, turn the device off
            self._output_device.off()
            self._running = False

    def _get_value(self):
        try:
            return next(self._gen)

        except StopIteration:
            self._n = self._n - 1 if self._n is not None else None
            if self._n == 0:
                # it's the end, return None
                return None
            else:
                # recreate the generator and start again
                self._gen = self._generator()
                return next(self._gen)

    def stop(self):
        """
        Stops the ValueChange object running.
        """
        self._running = False
        self._timer.deinit()


###############################################################################
# OUTPUT DEVICES
###############################################################################


class OutputDevice:
    """
    Base class for output devices.
    """

    def __init__(self, active_high=True, initial_value=False):
        self.active_high = active_high
        if initial_value is not None:
            self._write(initial_value)
        self._value_changer = None

    @property
    def active_high(self):
        """
        Sets or returns the active_high property. If :data:`True`, the
        :meth:`on` method will set the Pin to HIGH. If :data:`False`,
        the :meth:`on` method will set the Pin to LOW (the :meth:`off` method
        always does the opposite).
        """
        return self._active_state

    @active_high.setter
    def active_high(self, value):
        self._active_state = True if value else False
        self._inactive_state = False if value else True

    @property
    def value(self):
        """
        Sets or returns a value representing the state of the device: 1 is on, 0 is off.
        """
        return self._read()

    @value.setter
    def value(self, value):
        self._stop_change()
        self._write(value)

    def on(self, value=1, t=None, wait=False):
        """
        Turns the device on.

        :param float value:
            The value to set when turning on. Defaults to 1.

        :param float t:
            The time in seconds that the device should be on. If None is
            specified, the device will stay on. The default is None.

        :param bool wait:
           If True, the method will block until the time `t` has expired.
           If False, the method will return and the device will turn on in
           the background. Defaults to False. Only effective if `t` is not
           None.
        """
        if t is None:
            self.value = value
        else:
            self._start_change(
                lambda: iter(
                    [
                        (value, t),
                    ]
                ),
                1,
                wait,
            )

    def off(self):
        """
        Turns the device off.
        """
        self.value = 0

    @property
    def is_active(self):
        """
        Returns :data:`True` if the device is on.
        """
        return bool(self.value)

    def toggle(self):
        """
        If the device is off, turn it on. If it is on, turn it off.
        """
        if self.is_active:
            self.off()
        else:
            self.on()

    def blink(self, on_time=1, off_time=None, n=None, wait=False):
        """
        Makes the device turn on and off repeatedly.

        :param float on_time:
            The length of time in seconds that the device will be on. Defaults to 1.

        :param float off_time:
            The length of time in seconds that the device will be off. If `None`,
            it will be the same as ``on_time``. Defaults to `None`.

        :param int n:
            The number of times to repeat the blink operation. If None is
            specified, the device will continue blinking forever. The default
            is None.

        :param bool wait:
           If True, the method will block until the device stops turning on and off.
           If False, the method will return and the device will turn on and off in
           the background. Defaults to False.
        """
        off_time = on_time if off_time is None else off_time

        self.off()

        # is there anything to change?
        if on_time > 0 or off_time > 0:
            self._start_change(lambda: iter([(1, on_time), (0, off_time)]), n, wait)

    def _start_change(self, generator, n, wait):
        self._value_changer = ValueChange(self, generator, n, wait)

    def _stop_change(self):
        if self._value_changer is not None:
            self._value_changer.stop()
            self._value_changer = None

    def close(self):
        """
        Turns the device off.
        """
        self.value = 0


class DigitalOutputDevice(OutputDevice, PinMixin):
    """
    Represents a device driven by a digital pin.

    :param int pin:
        The pin that the device is connected to.

    :param bool active_high:
        If :data:`True` (the default), the :meth:`on` method will set the Pin
        to HIGH. If :data:`False`, the :meth:`on` method will set the Pin to
        LOW (the :meth:`off` method always does the opposite).

    :param bool initial_value:
        If :data:`False` (the default), the LED will be off initially. If
        :data:`True`, the LED will be switched on initially.
    """

    def __init__(self, pin, active_high=True, initial_value=False):
        self._pin_num = pin
        self._pin = Pin(pin, Pin.OUT)
        super().__init__(active_high, initial_value)

    def _value_to_state(self, value):
        return int(self._active_state if value else self._inactive_state)

    def _state_to_value(self, state):
        return int(bool(state) == self._active_state)

    def _read(self):
        return self._state_to_value(self._pin.value())

    def _write(self, value):
        self._pin.value(self._value_to_state(value))

    def close(self):
        """
        Closes the device and turns the device off. Once closed, the device
        can no longer be used.
        """
        super().close()
        self._pin = None


class PWMOutputDevice(OutputDevice, PinMixin):
    """
    Represents a device driven by a PWM pin.
    :param int pin:
        The pin that the device is connected to.
    :param int freq:
        The frequency of the PWM signal in hertz. Defaults to 100.
    :param int duty_factor:
        The duty factor of the PWM signal. This is a value between 0 and 65535.
        Defaults to 65535.
    :param bool active_high:
        If :data:`True` (the default), the :meth:`on` method will set the Pin
        to HIGH. If :data:`False`, the :meth:`on` method will set the Pin to
        LOW (the :meth:`off` method always does the opposite).
    :param bool initial_value:
        If :data:`False` (the default), the LED will be off initially. If
        :data:`True`, the LED will be switched on initially.
    """

    PIN_TO_PWM_CHANNEL = [
        "0A",
        "0B",
        "1A",
        "1B",
        "2A",
        "2B",
        "3A",
        "3B",
        "4A",
        "4B",
        "5A",
        "5B",
        "6A",
        "6B",
        "7A",
        "7B",
        "0A",
        "0B",
        "1A",
        "1B",
        "2A",
        "2B",
        "3A",
        "3B",
        "4A",
        "4B",
        "5A",
        "5B",
        "6A",
        "6B",
    ]
    _channels_used = {}

    def __init__(
        self, pin, freq=100, duty_factor=65535, active_high=True, initial_value=False
    ):
        self._check_pwm_channel(pin)
        self._pin_num = pin
        self._duty_factor = duty_factor
        self._pwm = PWM(Pin(pin))
        self._pwm.freq(freq)
        super().__init__(active_high, initial_value)

    def _check_pwm_channel(self, pin_num):
        channel = PWMOutputDevice.PIN_TO_PWM_CHANNEL[pin_num]
        if channel in PWMOutputDevice._channels_used.keys():
            raise PWMChannelAlreadyInUse(
                "PWM channel {} is already in use by {}. Use a different pin".format(
                    channel, str(PWMOutputDevice._channels_used[channel])
                )
            )
        else:
            PWMOutputDevice._channels_used[channel] = self

    def _state_to_value(self, state):
        return (
            state if self.active_high else self._duty_factor - state
        ) / self._duty_factor

    def _value_to_state(self, value):
        return int(self._duty_factor * (value if self.active_high else 1 - value))

    def _read(self):
        return self._state_to_value(self._pwm.duty_u16())

    def _write(self, value):
        self._pwm.duty_u16(self._value_to_state(value))

    @property
    def is_active(self):
        """
        Returns :data:`True` if the device is on.
        """
        return self.value != 0

    @property
    def freq(self):
        """
        Returns the current frequency of the device.
        """
        return self._pwm.freq()

    @freq.setter
    def freq(self, freq):
        """
        Sets the frequency of the device.
        """
        self._pwm.freq(freq)

    def blink(
        self,
        on_time=1,
        off_time=None,
        n=None,
        wait=False,
        fade_in_time=0,
        fade_out_time=None,
        fps=25,
    ):
        """
        Makes the device turn on and off repeatedly.

        :param float on_time:
            The length of time in seconds the device will be on. Defaults to 1.
        :param float off_time:
            The length of time in seconds the device will be off. If `None`,
            it will be the same as ``on_time``. Defaults to `None`.
        :param int n:
            The number of times to repeat the blink operation. If `None`, the
            device will continue blinking forever. The default is `None`.
        :param bool wait:
           If True, the method will block until the LED stops blinking. If False,
           the method will return and the LED will blink in the background.
           Defaults to False.
        :param float fade_in_time:
            The length of time in seconds to spend fading in. Defaults to 0.
        :param float fade_out_time:
            The length of time in seconds to spend fading out. If `None`,
            it will be the same as ``fade_in_time``. Defaults to `None`.
        :param int fps:
           The frames per second that will be used to calculate the number of
           steps between off/on states when fading. Defaults to 25.
        """
        self.off()

        off_time = on_time if off_time is None else off_time
        fade_out_time = fade_in_time if fade_out_time is None else fade_out_time

        def blink_generator():
            if fade_in_time > 0:
                for s in [
                    (i * (1 / fps) / fade_in_time, 1 / fps)
                    for i in range(int(fps * fade_in_time))
                ]:
                    yield s

            if on_time > 0:
                yield (1, on_time)

            if fade_out_time > 0:
                for s in [
                    (1 - (i * (1 / fps) / fade_out_time), 1 / fps)
                    for i in range(int(fps * fade_out_time))
                ]:
                    yield s

            if off_time > 0:
                yield (0, off_time)

        # is there anything to change?
        if on_time > 0 or off_time > 0 or fade_in_time > 0 or fade_out_time > 0:
            self._start_change(blink_generator, n, wait)

    def pulse(self, fade_in_time=1, fade_out_time=None, n=None, wait=False, fps=25):
        """
        Makes the device pulse on and off repeatedly.

        :param float fade_in_time:
            The length of time in seconds that the device will take to turn on.
            Defaults to 1.
        :param float fade_out_time:
           The length of time in seconds that the device will take to turn off.
           Defaults to 1.

        :param int fps:
           The frames per second that will be used to calculate the number of
           steps between off/on states. Defaults to 25.

        :param int n:
           The number of times to pulse the LED. If None, the LED will pulse
           forever. Defaults to None.

        :param bool wait:
           If True, the method will block until the LED stops pulsing. If False,
           the method will return and the LED will pulse in the background.
           Defaults to False.
        """
        self.blink(
            on_time=0,
            off_time=0,
            fade_in_time=fade_in_time,
            fade_out_time=fade_out_time,
            n=n,
            wait=wait,
            fps=fps,
        )

    def close(self):
        """
        Closes the device and turns the device off. Once closed, the device
        can no longer be used.
        """
        super().close()
        del PWMOutputDevice._channels_used[
            PWMOutputDevice.PIN_TO_PWM_CHANNEL[self._pin_num]
        ]
        self._pwm.deinit()
        self._pwm = None


class DigitalLED(DigitalOutputDevice):
    """
    Represents a simple LED, which can be switched on and off.
    :param int pin:
        The pin that the device is connected to.
    :param bool active_high:
        If :data:`True` (the default), the :meth:`on` method will set the Pin
        to HIGH. If :data:`False`, the :meth:`on` method will set the Pin to
        LOW (the :meth:`off` method always does the opposite).
    :param bool initial_value:
        If :data:`False` (the default), the LED will be off initially. If
        :data:`True`, the LED will be switched on initially.
    """

    pass


DigitalLED.is_lit = DigitalLED.is_active


def LED(pin, pwm=True, active_high=True, initial_value=False):
    """
    Returns an instance of :class:`DigitalLED` or :class:`PWMLED` depending on
    the value of the `pwm` parameter.
    ::
        from picozero import LED
        my_pwm_led = LED(1)
        my_digital_led = LED(2, pwm=False)
    :param int pin:
        The pin that the device is connected to.
    :param int pin:
        If `pwm` is :data:`True` (the default), a :class:`PWMLED` will be
        returned. If `pwm` is :data:`False`, a :class:`DigitalLED` will be
        returned. A :class:`PWMLED` can control the brightness of the LED but
        uses 1 PWM channel.
    :param bool active_high:
        If :data:`True` (the default), the :meth:`on` method will set the Pin
        to HIGH. If :data:`False`, the :meth:`on` method will set the Pin to
        LOW (the :meth:`off` method always does the opposite).
    :param bool initial_value:
        If :data:`False` (the default), the device will be off initially. If
        :data:`True`, the device will be switched on initially.
    """
    return DigitalLED(pin=pin, active_high=active_high, initial_value=initial_value)


pico_led = LED("LED", pwm=False)


class Servo(PWMOutputDevice):
    """
    Represents a PWM-controlled servo motor.

    Setting the `value` to 0 will move the servo to its minimum position,
    1 will move the servo to its maximum position. Setting the `value` to
    :data:`None` will turn the servo "off" (i.e. no signal is sent).

    :type pin: int
    :param pin:
        The pin the servo motor is connected to.

    :param bool initial_value:
        If :data:`0`, the servo will be set to its minimum position.  If
        :data:`1`, the servo will set to its maximum position. If :data:`None`
        (the default), the position of the servo will not change.

    :param float min_pulse_width:
        The pulse width corresponding to the servo's minimum position. This
        defaults to 1ms.

    :param float max_pulse_width:
        The pulse width corresponding to the servo's maximum position. This
        defaults to 2ms.

    :param float frame_width:
        The length of time between servo control pulses measured in seconds.
        This defaults to 20ms which is a common value for servos.

    :param int duty_factor:
        The duty factor of the PWM signal. This is a value between 0 and 65535.
        Defaults to 65535.
    """

    def __init__(
        self,
        pin,
        initial_value=None,
        min_pulse_width=1 / 1000,
        max_pulse_width=2 / 1000,
        frame_width=20 / 1000,
        duty_factor=65535,
    ):
        self._min_duty = int((min_pulse_width / frame_width) * duty_factor)
        self._max_duty = int((max_pulse_width / frame_width) * duty_factor)

        super().__init__(
            pin,
            freq=int(1 / frame_width),
            duty_factor=duty_factor,
            initial_value=initial_value,
        )

    def _state_to_value(self, state):
        return (
            None
            if state == 0
            else clamp(
                (state - self._min_duty) / (self._max_duty - self._min_duty), 0, 1
            )
        )

    def _value_to_state(self, value):
        return (
            0
            if value is None
            else int(self._min_duty + ((self._max_duty - self._min_duty) * value))
        )

    def min(self):
        """
        Set the servo to its minimum position.
        """
        self.value = 0

    def mid(self):
        """
        Set the servo to its mid-point position.
        """
        self.value = 0.5

    def max(self):
        """
        Set the servo to its maximum position.
        """
        self.value = 1

    def off(self):
        """
        Turn the servo "off" by setting the value to `None`.
        """
        self.value = None


class AngularServo(Servo):
    _min_value: int = 0
    _value_range: int = 1
    """Extends Servo into a rotational PWM-controlled servo.

    Notes:
        self.angle is a set only property.

    References:
        https://gpiozero.readthedocs.io/en/stable/api_output.html#angularservo
    """

    def __init__(
        self,
        pin: int,
        initial_angle: float = 0.0,
        min_angle: float = -90,
        max_angle: float = 90,
        min_pulse_width: float = 1 / 1000,
        max_pulse_width: float = 2 / 1000,
        frame_width: float = 20 / 1000,
    ):
        self._min_angle = min_angle
        self._angular_range = max_angle - min_angle
        if initial_angle is None:
            initial_value = None
        elif (min_angle <= initial_angle <= max_angle) or (
            max_angle <= initial_angle <= min_angle
        ):
            initial_value = 2 * ((initial_angle - min_angle) / self._angular_range) - 1
        else:
            raise ValueError(
                "AngularServo angle must be between %s and %s, or None"
                % (min_angle, max_angle)
            )
        super(AngularServo, self).__init__(
            pin, initial_value, min_pulse_width, max_pulse_width, frame_width
        )

    @property
    def min_angle(self):
        """
        The minimum angle that the servo will rotate to when :meth:`min` is
        called.
        """
        return self._min_angle

    @property
    def max_angle(self):
        """
        The maximum angle that the servo will rotate to when :meth:`max` is
        called.
        """
        return self._min_angle + self._angular_range

    @property
    def angle(self):
        """
        The position of the servo as an angle measured in degrees. This will
        only be accurate if :attr:`min_angle` and :attr:`max_angle` have been
        set appropriately in the constructor.

        This can also be the special value :data:`None` indicating that the
        servo is currently "uncontrolled", i.e. that no control signal is being
        sent.  Typically this means the servo's position remains unchanged, but
        that it can be moved by hand.
        """
        raise NotImplementedError("angle is a set only property.")

    @angle.setter
    def angle(self, angle):
        if angle is None:
            self.value = None
        elif (self.min_angle <= angle <= self.max_angle) or (
            self.max_angle <= angle <= self.min_angle
        ):
            self.value = (
                self._value_range * ((angle - self._min_angle) / self._angular_range)
                + self._min_value
            )
        else:
            raise ValueError(
                "AngularServo angle must be between %s and %s, or None"
                % (self.min_angle, self.max_angle)
            )


class Motor(PinsMixin):
    """
    Represents a motor connected to a motor controller that has a two-pin
    input. One pin drives the motor "forward", the other drives the motor
    "backward".

    :type forward: int
    :param forward:
        The GP pin that controls the "forward" motion of the motor.

    :type backward: int
    :param backward:
        The GP pin that controls the "backward" motion of the motor.

    :param bool pwm:
        If :data:`True` (the default), PWM pins are used to drive the motor.
        When using PWM pins, values between 0 and 1 can be used to set the
        speed.

    """

    def __init__(self, forward, backward, pwm=True):
        self._pin_nums = (forward, backward)
        self._forward = (
            PWMOutputDevice(forward) if pwm else DigitalOutputDevice(forward)
        )
        self._backward = (
            PWMOutputDevice(backward) if pwm else DigitalOutputDevice(backward)
        )

    def on(self, speed=1, t=None, wait=False):
        """
        Turns the motor on and makes it turn.

        :param float speed:
            The speed as a value between -1 and 1: 1 turns the motor at
            full speed in one direction, -1 turns the motor at full speed in
            the opposite direction. Defaults to 1.

        :param float t:
            The time in seconds that the motor should run for. If None is
            specified, the motor will stay on. The default is None.

        :param bool wait:
           If True, the method will block until the time `t` has expired.
           If False, the method will return and the motor will turn on in
           the background. Defaults to False. Only effective if `t` is not
           None.
        """
        if speed > 0:
            self._backward.off()
            self._forward.on(speed, t, wait)

        elif speed < 0:
            self._forward.off()
            self._backward.on(-speed, t, wait)

        else:
            self.off()

    def off(self):
        """
        Stops the motor turning.
        """
        self._backward.off()
        self._forward.off()

    @property
    def value(self):
        """
        Sets or returns the motor speed as a value between -1 and 1: -1 is full
        speed "backward", 1 is full speed "forward", 0 is stopped.
        """
        return self._forward.value + (-self._backward.value)

    @value.setter
    def value(self, value):
        if value != 0:
            self.on(value)
        else:
            self.stop()

    def forward(self, speed=1, t=None, wait=False):
        """
        Makes the motor turn "forward".

        :param float speed:
            The speed as a value between 0 and 1: 1 is full speed, 0 is stop. Defaults to 1.

        :param float t:
            The time in seconds that the motor should turn for. If None is
            specified, the motor will stay on. The default is None.

        :param bool wait:
           If True, the method will block until the time `t` has expired.
           If False, the method will return and the motor will turn on in
           the background. Defaults to False. Only effective if `t` is not
           None.
        """
        self.on(speed, t, wait)

    def backward(self, speed=1, t=None, wait=False):
        """
        Makes the motor turn "backward".

        :param float speed:
            The speed as a value between 0 and 1: 1 is full speed, 0 is stop. Defaults to 1.

        :param float t:
            The time in seconds that the motor should turn for. If None is
            specified, the motor will stay on. The default is None.

        :param bool wait:
           If True, the method will block until the time `t` has expired.
           If False, the method will return and the motor will turn on in
           the background. Defaults to False. Only effective if `t` is not
           None.
        """
        self.on(-speed, t, wait)

    def close(self):
        """
        Closes the device and releases any resources. Once closed, the device
        can no longer be used.
        """
        self._forward.close()
        self._backward.close()


Motor.start = Motor.on
Motor.stop = Motor.off


class ContinousServo(Servo):
    """Extends Servo into a continous PWM-controlled servo.

    Notes:
        Adds functionality of `Servo` to be similar to that of `Motor`.

    Refs:
        https://picozero.readthedocs.io/en/latest/api.html#motor
    """

    def on(self, speed: float, t: float, wait: bool):
        """Turns the motor on and makes it turn."""
        super(ContinousServo, self).on(value=speed, t=t, wait=wait)  # type: ignore
