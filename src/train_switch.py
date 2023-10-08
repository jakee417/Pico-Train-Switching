"""Train switch classes"""
import time
import sys
from machine import Timer
from micropython import const

from .lib.picozero import DigitalOutputDevice, AngularServo, Motor, Servo, PinsMixin


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


class ServoAngle(object):
    """Angle for a ServoTrainSwitch."""

    MIN_ANGLE: int = 0
    MAX_ANGLE: int = 80


class ServoTrainSwitch(StatefulBinaryDevice):
    required_pins = 1
    on_state = "straight"
    off_state = "turn"

    def __init__(
        self,
        # Optional[float]
        initial_angle: float = None,  # type: ignore
        min_angle: int = ServoAngle.MIN_ANGLE,
        max_angle: int = ServoAngle.MAX_ANGLE,
        **kwargs,
    ) -> None:
        """Servo class wrapping the gpiozero class for manual train switches.

        Args:
            initial_angle: intial angle of the servo
            min_angle: minimum angle of the angular servo
            max_angle: maximum angle of the angular servo

        References:
            https://gpiozero.readthedocs.io/en/stable/api_output.html#angularservo
            https://gpiozero.readthedocs.io/en/stable/recipes.html#servo
        """
        super(ServoTrainSwitch, self).__init__(**kwargs)

        if len(self.pin) != self.get_required_pins:
            raise ValueError(f"Expecting {self.required_pins} pins. Found {self.pin}")
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.initial_angle = initial_angle

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

    def custom_state_setter(self, state: str) -> None:
        pass

    @staticmethod
    def action_to_angle(action: str) -> float:
        """Maps an action to a legal action."""
        if action == ServoTrainSwitch.off_state:
            angle = ServoAngle.MIN_ANGLE
        elif action == ServoTrainSwitch.on_state:
            angle = ServoAngle.MAX_ANGLE
        elif action is None:
            return None  # type: ignore
        else:
            raise ValueError(
                "Invalid command to train switch." + f"\n Found action: {action}"
            )
        return angle

    def _action(self, action: str) -> str:
        # Optional[float]
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
    _DELAY: int = const(500)  # in microseconds.

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
            _time.sleep_us(_delay)
            self._step.on(value=0)
            _time.sleep_us(_delay)

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


class AsyncStepMotor(StepMotor):
    _step_count: int
    _timer: Timer

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._timer = Timer()

    def step_closure(self, steps: int):
        # Reset the timer and step count.
        self._step_count = 0
        _stop_condition: int = steps * 2

        def step(timer: Timer):
            self._step.toggle()
            self._step_count += 1
            if self._step_count >= _stop_condition:
                timer.deinit()

        return step

    def on(self, steps: int) -> None:
        self._timer.init(
            mode=Timer.PERIODIC,
            period=StepMotor._DELAY,
            callback=self.step_closure(steps=steps),
        )


class StepperMotor(StatelessBinaryDevice):
    required_pins = 2
    on_state = "next"
    off_state = "last"

    _STEPS: int = const(200)

    # Optional[float]
    def __init__(self, **kwargs) -> None:
        """Stepper Motor class wrapping the picozero StepMotor.

        References:
            https://picozero.readthedocs.io/en/latest/recipes.html#motor
        """
        super(StepperMotor, self).__init__(**kwargs)

        if len(self.pin) != self.get_required_pins:
            raise ValueError(f"Expecting {self.required_pins} pins. Found {self.pin}")

        self.motor = StepMotor(direction=self.pin[0], step=self.pin[1])

    def custom_state_setter(self, state: str) -> None:
        pass

    def _action(self, action: str) -> str:
        if action == DCMotor.on_state:
            self.motor.forward(steps=StepperMotor._STEPS)
        elif action == DCMotor.off_state:
            self.motor.backward(steps=StepperMotor._STEPS)
        elif action is None:
            # TODO: Implement a sleep function
            pass
        else:
            raise ValueError("Invalid command to motor." + f"\n Found action: {action}")
        return str(action)

    def __del__(self) -> None:
        self.motor.close()


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
        # print(f"\n {self}: \n" + f"++++ Background Thread: Checking for shutdown...")
        if self.relay.value == 1:
            # print(f"\n {self}: \n" + f"++++ Background Thread: auto-shutdown")
            self.relay.off()
            self.state = self.off_state

    def _action(self, action: str) -> str:
        if action is None or action == Disconnect.off_state:
            self.relay.off()
            # If we had a thread waiting to close, cancel it.
            if self.safe_stop is not None:
                self.safe_stop.deinit()
                self.safe_stop = None
        elif action == Disconnect.on_state:
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
