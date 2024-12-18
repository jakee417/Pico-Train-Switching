"""Device classes"""

from collections import deque
from neopixel import NeoPixel as _NeoPixel
import time
import sys
from machine import Pin, Timer
from micropython import const

from .timer import (
    dequeue_from_timer,
    enqueue_to_timer,
    start_timer,
    stop_timer,
)

from .lib.picozero import (
    DigitalOutputDevice,
    AngularServo,
    Motor,
    Servo,
    PinsMixin,
)


class BinaryDevice(object):
    # default time to wait between blinking
    _BLINK: float = const(0.1)
    # how long to wait before shutting down disconnect
    _SAFE_SHUTDOWN: int = const(4)

    # Public attributes
    required_pins: int = -1
    on_state: str = ""
    off_state: str = ""

    # Private attributes
    __pin: tuple[int, ...] = tuple()
    # Optional[str]
    __state: str = None  # type: ignore

    def __init__(self, pin: tuple[int, ...], verbose: bool = False) -> None:
        """Base class for any device with two states, on_state & off_state.

        Notes:
            Allows the possibility of a None state i.e. uncontrolled.

        Args:
            pin: GPIO pin number i.e. GP0 is passed as 0.
                Alternatively a tuple of integers for multi-pin devices.
            verbose: Either True or False. Verbosity of object.

        Attributes:
            required_pins: Number of pins required.
            on_state: String representation of the "on" state.
            off_state: String representation of the "off" state.
        """
        pin = tuple(sorted(pin))  # always sort the pins
        self.__pin = pin
        self.verbose = verbose

    @property
    def pin(self) -> tuple[int, ...]:
        """Returns the pin number(s)."""
        return self.__pin

    def __repr__(self):
        return f"{type(self).__name__} @ Pin : {self.pin}"

    @property
    def pin_list(self) -> list[int]:
        """Returns a list of used pin(s) i.e. [2, 4]."""
        return list(self.__pin)

    @property
    def pin_string(self) -> str:
        """Returns a csv seperated string of pin(s) i.e. "2,4"."""
        return ",".join(str(s) for s in self.__pin)

    @property
    def get_required_pins(self) -> int:
        # Subclasses must change this attribute.
        if self.required_pins == -1:
            raise NotImplementedError(
                "Overwrite required_pins when extending BinaryDevice."
            )
        return self.required_pins

    @property
    def state(self) -> str:
        """Returns the active state."""
        return self.__state

    @state.setter
    def state(self, state: str) -> None:
        self.custom_state_setter(state)
        self.__state = state

    def custom_state_setter(self, state: str) -> None:
        """Custom action upon setting the state."""
        raise NotImplementedError("Implement this method.")

    def to_json(self) -> dict[str, object]:
        """Converts an object to a seralized representation.

        Returns:
            Serialized reprsentation including:
                - pin
                - state
                - name
        """
        return {
            const("pins"): self.pin,
            const("state"): self.state,
            const("name"): type(self).__name__,
        }

    def log(self, initial_state: str, action: str, update: str) -> None:
        """Logs update message"""
        if self.verbose:
            print(
                f"{self}: \n"
                + f"++++ initial state: {initial_state} \n"
                + f"++++ action: {action} \n"
                + f"++++ update: {update}"
            )

    def _action(self, action: str) -> str:
        """Subclass's subaction on an action.

        Args:
            action: One of either `self.on_state` or `self.off_state`.

        Returns:
            Serialized representation of the action result.
        """
        raise NotImplementedError("Implement this method.")

    def action(self, action: str) -> None:
        """Complete an action.

        Args:
            action: One of either `self.on_state` or `self.off_state`.
        """
        raise NotImplementedError("Implement this method.")

    def __del__(self) -> None:
        raise NotImplementedError("Implement this method.")

    def close(self) -> None:
        """Close a connection with a switch."""
        self.__del__()


class StatefulBinaryDevice(BinaryDevice):
    def action(self, action: str) -> None:
        """Complete an action on the state.

        If an ordered action is the same as the previous state, then do nothing.
        Otherwise, perform the action.

        Args:
            action: One of either `self.on_state` or `self.off_state`.
        """
        if self.state == action:
            self.log(self.state, action, "skipped")
        else:
            initial_state = self.state
            self.state = action
            update = self._action(action)
            self.log(
                initial_state=initial_state,
                action=action,
                update=update,
            )


class StatelessBinaryDevice(BinaryDevice):
    def action(self, action: str) -> None:
        """Complete an action, irregardless of state.

        Args:
            action: One of either `self.on_state` or `self.off_state`.
        """
        update = self._action(action)
        self.log(
            initial_state=self.state,
            action=action,
            update=update,
        )


class EmptySwitch(StatefulBinaryDevice):
    required_pins = 2
    on_state = None  # type: ignore
    off_state = None  # type: ignore

    def __init__(
        self,
        **kwargs,
    ) -> None:
        """Dummy device to indicate nothing is being used."""
        super(EmptySwitch, self).__init__(**kwargs)

        if len(self.pin) != self.get_required_pins:
            raise ValueError(f"Expecting two pins. Found {self.pin}")

    def custom_state_setter(self, state: str) -> None:
        pass

    def _action(self, action: str) -> str:
        return action

    def __del__(self) -> None:
        pass


class ServoTrainSwitch(StatefulBinaryDevice):
    required_pins = 1
    on_state = "straight"
    off_state = "turn"

    _MIN_ANGLE: int = const(0)
    _MAX_ANGLE: int = const(80)
    max_angle: int
    min_angle: int

    def __init__(self, **kwargs) -> None:
        """Servo class wrapping the gpiozero class for manual train switches.

        Args:
            initial_angle: intial angle of the servo

        References:
            https://gpiozero.readthedocs.io/en/stable/api_output.html#angularservo
            https://gpiozero.readthedocs.io/en/stable/recipes.html#servo
        """
        super(ServoTrainSwitch, self).__init__(**kwargs)

        if len(self.pin) != self.get_required_pins:
            raise ValueError(f"Expecting {self.required_pins} pins. Found {self.pin}")
        self.min_angle = ServoTrainSwitch._MIN_ANGLE
        self.max_angle = ServoTrainSwitch._MAX_ANGLE
        self.initial_angle = None

        # Supporting math:
        # params for SG90 micro servo:
        # 50Hz normal operation
        # 2% duty cycle = 0°
        # 12% duty cycle = 12°
        # => frame_width (s) = 1 / 50 (Hz) = 0.02 (s)
        # _min_dc = min_pulse_width / frame_width = 0.02%
        # => min_pulse = 4 / 10,000
        # _dc_range = (max_pulse_width - min_pulse_width) / frame_width = 0.12%
        # => max_pulse_width = 24 / 10,000
        self.servo = AngularServo(
            pin=self.pin[0],
            initial_angle=self.initial_angle,
            min_angle=self.min_angle,
            max_angle=self.max_angle,
            frame_width=1 / 50,  # 1/50Hz corresponds to 20/1000s default
            min_pulse_width=4 / 10000,  # corresponds to 2% duty cycle
            max_pulse_width=24 / 10000,  # correponds to 12% duty cycle
        )

    @property
    def steps(self) -> int:
        return int(self.max_angle - self.min_angle)

    @steps.setter
    def steps(self, steps: int) -> None:
        self.max_angle = steps
        self.min_angle = ServoTrainSwitch._MIN_ANGLE

    def custom_state_setter(self, state: str) -> None:
        pass

    def action_to_angle(self, action: str) -> float | None:
        """Maps an action to a legal action."""
        if action == ServoTrainSwitch.off_state:
            angle = self.min_angle
        elif action == ServoTrainSwitch.on_state:
            angle = self.max_angle
        elif action is None:
            return None
        else:
            raise ValueError(
                "Invalid command to train switch." + f"\n Found action: {action}"
            )
        return angle

    def _action(self, action: str) -> str:
        angle = self.action_to_angle(action)
        self.servo.angle = angle
        return str(angle)

    def __del__(self) -> None:
        self.servo.close()


class DoubleServoTrainSwitch(ServoTrainSwitch):
    required_pins = 2

    def __init__(self, **kwargs) -> None:
        super(DoubleServoTrainSwitch, self).__init__(**kwargs)


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


class ContinuousServoMotor(StatelessBinaryDevice):
    required_pins = 1
    on_state = "next"
    off_state = "last"

    t: float = 1.0
    # value = 0.5 +/- speed \in (0, 1)
    speed: float = 0.45

    # Optional[float]
    def __init__(self, **kwargs) -> None:  # type: ignore
        """Continuous Servo class wrapping the picozero Servo.

        References:
            https://picozero.readthedocs.io/en/latest/recipes.html#servo
        """
        super(ContinuousServoMotor, self).__init__(**kwargs)

        if len(self.pin) != self.get_required_pins:
            raise ValueError(f"Expecting {self.required_pins} pins. Found {self.pin}")
        self.servo = ContinousServo(pin=self.pin[0])

    def custom_state_setter(self, state: str) -> None:
        pass

    def _action(self, action: str) -> str:
        _no_speed: float = 0.5
        if action == ContinuousServoMotor.on_state:
            self.servo.on(speed=_no_speed - self.speed, t=self.t, wait=True)
        elif action == ContinuousServoMotor.off_state:
            self.servo.on(speed=_no_speed + self.speed, t=self.t, wait=True)
        elif action is None:
            self.servo.off()
        else:
            raise ValueError("Invalid command to servo." + f"\n Found action: {action}")
        return str(action)

    def __del__(self) -> None:
        self.servo.close()


class DoubleContinuousServoMotor(ContinuousServoMotor):
    required_pins = 2

    def __init__(self, **kwargs) -> None:
        super(DoubleContinuousServoMotor, self).__init__(**kwargs)


class DCMotor(StatelessBinaryDevice):
    required_pins = 2
    on_state = "next"
    off_state = "last"

    t: float = 1.0

    # Optional[float]
    def __init__(self, **kwargs) -> None:
        """DC Motor class wrapping the picozero Motor.

        References:
            https://picozero.readthedocs.io/en/latest/recipes.html#motor
        """
        super(DCMotor, self).__init__(**kwargs)

        if len(self.pin) != self.get_required_pins:
            raise ValueError(f"Expecting {self.required_pins} pins. Found {self.pin}")

        self.motor = Motor(forward=self.pin[0], backward=self.pin[1], pwm=True)

    def custom_state_setter(self, state: str) -> None:
        pass

    def _action(self, action: str) -> str:
        if action == DCMotor.on_state:
            self.motor.on(speed=1, t=self.t, wait=True)
        elif action == DCMotor.off_state:
            self.motor.on(speed=-1, t=self.t, wait=True)
        elif action is None:
            self.motor.off()
        else:
            raise ValueError("Invalid command to motor." + f"\n Found action: {action}")
        return str(action)

    def __del__(self) -> None:
        self.motor.close()


class StepMotor(PinsMixin):
    _direction: DigitalOutputDevice
    _step: DigitalOutputDevice
    _DELAY: int = const(66)

    def __init__(self, direction: int, step: int):
        """
        Represents a stepper motor connected to a motor controller that has a
        two-pin input. One pin controls the logic to create "steps" and the
        other controls the direction of the motor's motion.

        :type direction: int
        :param direction:
            The GP pin that controls the steps of the motor.

        :type step: int
        :param step:
            The GP pin that controls the direction of the motion of the motor.
        """
        self._pin_nums = (direction, step)
        self._direction = DigitalOutputDevice(pin=direction)
        self._step = DigitalOutputDevice(pin=step)

    def on(self, steps: int) -> None:
        _delay = StepMotor._DELAY
        _time = time
        for _ in range(steps):
            self._step.on(value=1)
            _time.sleep_ms(_delay)
            self._step.on(value=0)
            _time.sleep_ms(_delay)

    def forward(self, steps: int) -> None:
        self._direction.on(value=1)
        self.on(steps=steps)

    def backward(self, steps: int) -> None:
        self._direction.on(value=0)
        self.on(steps=steps)

    def close(self):
        """
        Closes the device and releases any resources. Once closed, the device
        can no longer be used.
        """
        self._direction.close()
        self._step.close()


class StepperMotor(StatelessBinaryDevice):
    required_pins = 2
    on_state = "next"
    off_state = "last"

    _STEPS: int = const(30)
    _steps: int

    def __init__(self, **kwargs) -> None:
        """Stepper Motor class wrapping the picozero StepMotor.

        References:
            https://picozero.readthedocs.io/en/latest/recipes.html#motor
        """
        super(StepperMotor, self).__init__(**kwargs)

        if len(self.pin) != self.get_required_pins:
            raise ValueError(f"Expecting {self.required_pins} pins. Found {self.pin}")

        self.motor = StepMotor(direction=self.pin[0], step=self.pin[1])
        self.steps = StepperMotor._STEPS

    @property
    def steps(self) -> int:
        return self._steps

    @steps.setter
    def steps(self, steps: int) -> None:
        self._steps = steps

    def custom_state_setter(self, state: str) -> None:
        pass

    def _action(self, action: str) -> str:
        if action == DCMotor.on_state:
            self.motor.forward(steps=self.steps)
        elif action == DCMotor.off_state:
            self.motor.backward(steps=self.steps)
        elif action is None:
            # TODO: Implement a sleep function
            pass
        else:
            raise ValueError("Invalid command to motor." + f"\n Found action: {action}")
        return str(action)

    def __del__(self) -> None:
        self.motor.close()


class LightBeam(StatefulBinaryDevice):
    r: int
    g: int
    b: int
    n: int
    delay: int
    beam_length: int
    reverse_at_end: bool
    required_pins = 1
    on_state = "on"
    off_state = "off"
    DARK = (0, 0, 0)

    def __init__(
        self,
        n: int,
        r: int = 10,
        g: int = 0,
        b: int = 0,
        delay: int = 10,
        beam_length: int = 3,
        reverse_at_end: int = 0,
        **kwargs,
    ) -> None:
        """An on/off light beam for controlling a NeoPixel (WS2812b) LED.

        References:
            https://docs.micropython.org/en/latest/library/neopixel.html
        """
        super(LightBeam, self).__init__(**kwargs)

        if len(self.pin) != self.get_required_pins:
            raise ValueError(f"Expecting one pin. Found {self.pin}")

        self._pin = Pin(self.pin[0], Pin.OUT)
        self.n = int(n)
        self.r = int(r)
        self.g = int(g)
        self.b = int(b)
        self.delay = int(delay)
        self.beam_length = int(beam_length)
        _reverse_at_end = int(reverse_at_end)

        if self.delay < 0:
            raise ValueError(f"delay must be positive, found {self.delay}")

        if self.beam_length > self.n:
            raise ValueError(f"{self.beam_length} must be <= {self.n}")

        if _reverse_at_end not in [0, 1]:
            raise ValueError(
                f"reverse_at_end must be either 0 or 1. Found {reverse_at_end}"
            )

        self.reverse_at_end = bool(_reverse_at_end)
        self.pixels = _NeoPixel(pin=self._pin, n=self.n)

    def _pixels_clear(self) -> None:
        self.pixels.fill(self.DARK)

    def _pixel_set(self, i: int, color: tuple[int, ...]) -> None:
        self.pixels[i] = color

    def _pixel_write(self) -> None:
        self.pixels.write()

    def pixels_reset(self) -> None:
        self._pixels_clear()
        self._pixel_write()

    def pixels_cycle(
        self,
        color: tuple[int, ...],
        reverse: bool,
        measure_time: bool,
    ) -> int:
        total_time = 0
        n = len(self.pixels)
        queue = deque([], self.beam_length + 1)
        loop = reversed(range(n)) if reverse else range(n)
        for i in loop:
            # Light new pixel
            queue.append(i)
            if not measure_time:
                self._pixel_set(i=i, color=color)
                self._pixel_write()
                # `beam_length` lights are on.
                time.sleep_ms(self.delay)
            else:
                total_time += self.delay
            # Enforce beam length
            if self.beam_length <= len(queue):
                j = queue.popleft()
                if not measure_time:
                    self._pixel_set(i=j, color=self.DARK)
                    self._pixel_write()
            if not measure_time:
                # `beam_length - 1` lights are on.
                time.sleep_ms(self.delay)
            else:
                total_time += self.delay
        # Turn off any remaining pixels.
        remainder = reversed(queue) if reverse else queue
        for j in remainder:
            if not measure_time:
                self._pixel_set(i=j, color=self.DARK)
                self._pixel_write()
                time.sleep_ms(self.delay)
            else:
                total_time += self.delay
        return total_time

    def custom_state_setter(self, state: str) -> None:
        pass

    def _on_action(self, measure_time: bool) -> int:
        total_time = 0
        total_time += self.pixels_cycle(
            color=(self.r, self.g, self.b),
            reverse=False,
            measure_time=measure_time,
        )
        if self.reverse_at_end:
            total_time += self.pixels_cycle(
                color=(self.r, self.g, self.b),
                reverse=True,
                measure_time=measure_time,
            )
        return total_time

    def on_action(self, timer: Timer) -> None:
        self._on_action(measure_time=False)

    def _action(self, action: str) -> str:
        if action == LightBeam.on_state:
            enqueue_to_timer(
                id=id(self),
                callback_time=self._on_action(measure_time=True),
                callback=self.on_action,
            )
            return LightBeam.on_state
        elif action == LightBeam.off_state:
            dequeue_from_timer(id=id(self))
            self.pixels_reset()
            return LightBeam.off_state
        elif action is None:
            dequeue_from_timer(id=id(self))
            self.pixels_reset()
            return
        raise ValueError("Invalid command to NeoPixel." + f"\n Found action: {action}")

    def __del__(self) -> None:
        self.pixels_reset()
        self._pin = None


class DoubleLightBeam(LightBeam):
    required_pins = 2

    def __init__(self, **kwargs) -> None:
        super(DoubleLightBeam, self).__init__(**kwargs)


class RelayTrainSwitch(StatefulBinaryDevice):
    required_pins: int = 2
    on_state: str = "straight"
    off_state: str = "turn"

    def __init__(
        self, active_high: bool = False, initial_value: bool = False, **kwargs
    ) -> None:
        """Relay switch wrapping the gpiozero class for remote train switches.

        References:
            https://picozero.readthedocs.io/en/latest/api.html#digitaloutputdevice
            https://www.electronicshub.org/control-a-relay-using-raspberry-pi/
        """
        super(RelayTrainSwitch, self).__init__(**kwargs)

        if len(self.pin) != self.get_required_pins:
            raise ValueError(f"Expecting two pins. Found {self.pin}")

        _pins: list[int] = list(self.pin)

        # when active_high=False, on() seems to pass voltage and off() seems to pass no voltage.
        # We initially set to False.
        self.yg_relay = DigitalOutputDevice(
            pin=_pins[0], active_high=active_high, initial_value=initial_value
        )
        self.br_relay = DigitalOutputDevice(
            pin=_pins[1], active_high=active_high, initial_value=initial_value
        )

    def custom_state_setter(self, state: str) -> None:
        if state is None:
            self.br_relay.off()
            self.yg_relay.off()

    def _action(self, action: str) -> str:
        # We only want to blink one pair at a time
        # otherwise, leave both relays as low - sending no action
        # Now we `BLINK` a single device once for 1/2 second.
        if action == RelayTrainSwitch.off_state:
            self.br_relay.off()
            self.br_relay.on()
            time.sleep(self._BLINK)
            self.br_relay.off()
        elif action == RelayTrainSwitch.on_state:
            self.yg_relay.off()
            self.yg_relay.on()
            time.sleep(self._BLINK)
            self.yg_relay.off()
        elif action is None:
            pass
        else:
            raise ValueError(
                "Invalid command to train switch." + f"\n Found action: {action}"
            )
        return action

    def __del__(self) -> None:
        self.yg_relay.close()
        self.br_relay.close()


class OnOff(StatefulBinaryDevice):
    required_pins = 1
    on_state = "on"
    off_state = "off"

    def __init__(
        self,
        active_high: bool = False,
        initial_value: bool = False,
        **kwargs,
    ) -> None:
        """OnOff wrapping the picozero class for generic devices.

        References:
            https://www.electronicshub.org/control-a-relay-using-raspberry-pi/
        """
        super(OnOff, self).__init__(**kwargs)

        if len(self.pin) != self.get_required_pins:
            raise ValueError(f"Expecting one pin. Found {self.pin}")

        # when active_high=False, on() seems to pass voltage and off() seems to pass no voltage.
        # We initially set to False.
        self.relay = DigitalOutputDevice(
            pin=self.pin[0], active_high=active_high, initial_value=initial_value
        )

    def custom_state_setter(self, state: str) -> None:
        if not state:
            self.relay.off()

    def _action(self, action: str) -> str:
        if action == self.off_state:
            self.relay.off()
        elif action == self.on_state:
            self.relay.on()
        elif action is None:
            pass
        else:
            raise ValueError(
                "Invalid command to on/off device." + f"\n Found action: {action}"
            )
        return action

    def __del__(self) -> None:
        self.relay.close()


class DoubleOnOff(OnOff):
    required_pins = 2

    def __init__(self, **kwargs) -> None:
        super(DoubleOnOff, self).__init__(**kwargs)


class Disconnect(OnOff):
    """Extension of On/Off for Disconnect accessory."""

    def __init__(self, active_high=False, **kwargs) -> None:
        super(Disconnect, self).__init__(active_high=active_high, **kwargs)
        self.safe_stop = None

    def safe_close_relay(self, timer: Timer) -> None:
        # If relay is on, turn it off
        if self.relay.value == 1:
            self.relay.off()
            self.state = self.off_state
        # Now its safe to restart other timer work.
        start_timer()

    def _action(self, action: str) -> str:
        if action is None or action == Disconnect.off_state:
            self.relay.off()
            # If we had a thread waiting to close, cancel it.
            if self.safe_stop is not None:
                self.safe_stop.deinit()
                self.safe_stop = None
        elif action == Disconnect.on_state:
            # Give this action priority and temporarily pause all other timers.
            stop_timer()
            self.relay.on()
            # Wait for 10 seconds, then turn off.
            self.safe_stop = Timer(
                # period is in milliseconds.
                period=self._SAFE_SHUTDOWN * 1000,
                mode=Timer.ONE_SHOT,
                callback=self.safe_close_relay,
            )
        else:
            raise ValueError(
                "Invalid command to Disconnect device." + f"\n Found action: {action}"
            )
        return action

    def __del__(self) -> None:
        self.relay.off()
        if self.safe_stop is not None:
            self.safe_stop.deinit()
        super().__del__()


class DoubleDisconnect(Disconnect):
    required_pins = 2

    def __init__(self, **kwargs) -> None:
        super(DoubleDisconnect, self).__init__(**kwargs)


class Unloader(OnOff):
    """Extension of On/Off for Unloader accessory."""

    def __init__(self, **kwargs) -> None:
        super(Unloader, self).__init__(active_high=False, **kwargs)


class DoubleUnloader(Unloader):
    required_pins = 2

    def __init__(self, **kwargs) -> None:
        super(DoubleUnloader, self).__init__(**kwargs)


class InvertedDisconnect(Disconnect):
    """Extension of On/Off for Disconnect accessory w/ inverted active_high."""

    def __init__(self, **kwargs) -> None:
        super(InvertedDisconnect, self).__init__(active_high=True, **kwargs)


class InvertedUnloader(OnOff):
    """Extension of On/Off for Unloader accessory w/ inverted active_high."""

    def __init__(self, **kwargs) -> None:
        super(InvertedUnloader, self).__init__(active_high=True, **kwargs)


class SingleRelayTrainSwitch(OnOff):
    """Relay Train Switch using only one DigitalOutputDevice."""

    on_state: str = "straight"
    off_state: str = "turn"

    def __init__(self, active_high=False, **kwargs) -> None:
        super(SingleRelayTrainSwitch, self).__init__(active_high=active_high, **kwargs)

    def custom_state_setter(self, state: str) -> None:
        pass


class InvertedSingleRelayTrainSwitch(SingleRelayTrainSwitch):
    """Inverted Relay Train Switch using only one DigitalOutputDevice."""

    def __init__(self, **kwargs) -> None:
        super(InvertedSingleRelayTrainSwitch, self).__init__(active_high=True, **kwargs)


class SpurTrainSwitch(RelayTrainSwitch):
    """Extension of Relay Switch that will optionally depower the track."""

    def __init__(self, active_high: bool = False, **kwargs) -> None:
        super(SpurTrainSwitch, self).__init__(active_high=active_high, **kwargs)

    def _action(self, action: str) -> str:
        # leave the pins on in an alternating fashion
        if action == SpurTrainSwitch.off_state:
            self.yg_relay.off()
            self.br_relay.on()
        elif action == SpurTrainSwitch.on_state:
            self.br_relay.off()
            self.yg_relay.on()
        elif action is None:
            pass
        else:
            raise ValueError(
                "Invalid command to train switch." + f"\n Found action: {action}"
            )
        return action


class InvertedSpurTrainSwitch(SpurTrainSwitch):
    """Extension of Spur Train Switch but with inverted active_high."""

    def __init__(self, **kwargs) -> None:
        super(InvertedSpurTrainSwitch, self).__init__(active_high=True, **kwargs)


class InvertedRelayTrainSwitch(RelayTrainSwitch):
    """Extension of Relay Train Switch but with inverted active_high."""

    def __init__(self, **kwargs) -> None:
        super(InvertedRelayTrainSwitch, self).__init__(active_high=True, **kwargs)


CLS_MAP: dict[str, type[BinaryDevice]] = {
    k: v
    for k, v in sys.modules[__name__].__dict__.items()
    # For space considerations, only offer devices requiring 2 pins.
    if hasattr(v, "required_pins") and v.required_pins == 2
}

DEFAULT_DEVICE: str = const(RelayTrainSwitch.__name__)
