"""Train switch classes"""
import time
from machine import Timer

from app.lib.picozero import DigitalOutputDevice
from app.lib.picozero_extensions import AngularServo


SLEEP: float = 0.5  # default sleep time to prevent jitter - half seconds
BLINK: float = 0.25  # default time to wait between blinking
SAFE_SHUTDOWN: int = 4  # how long to wait before shutting down disconnect


class BinaryDevice(object):
    required_pins: int = -1
    __pin: tuple[int] = tuple()
    # Optional[str]
    __state: str = None  # type: ignore
    on_state: str = ""
    off_state: str = ""

    def __init__(
        self,
        pin: tuple[int],
    ) -> None:
        """Base class for any device with two states, on_state & off_state.

        Notes:
            Allows the possibility of a None state i.e. uncontrolled.

        Args:
            pin: Unique number for a gpio pin on a raspberry pi.
                Alternatively a tuple of integers for multi-pin devices.
            verbose: Either True or False. Verbosity of object.

        Attributes:
            required_pins: Number of pins required.
            on_state: String representation of the "on" state.
            off_state: String representation of the "off" state.
        """
        self.__name__ = "Base Train Switch"
        pin = tuple(sorted(pin))  # always sort the pins
        self.__pin = pin

    @property
    def name(self) -> str:
        """Returns the name of the object."""
        return self.__name__

    @property
    def pin(self) -> tuple[int]:
        """Returns the pin number(s)."""
        return self.__pin

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
                f"Overwrite required_pins when extending BinaryDevice."
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

    # @abstractmethod
    def custom_state_setter(self, state: str) -> None:
        """Custom action upon setting the state."""
        raise NotImplementedError

    def __repr__(self):
        return f"{self.name} @ Pin : {self.pin}"

    def to_json(self) -> dict[str, object]:
        """Converts an object to a seralized representation.

        Returns:
            Serialized reprsentation including:
                - pin
                - state
                - name
        """
        return {
            "pins": self.pin,
            "state": self.state,
            "name": self.name
        }

    def log(
        self,
        initial_state: str,
        action: str,
        update: str
    ) -> None:
        """Logs update message"""
        print(
            f"{self}: \n" +
            f"++++ initial state: {initial_state} \n" +
            f"++++ action: {action} \n" +
            f"++++ update: {update}"
        )

    # @abstractmethod
    def _action(self, action: str) -> str:
        raise NotImplementedError

    def action(self, action: str) -> None:
        """Complete an action on a train switch.

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

    # @abstractmethod
    def __del__(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        """Close a connection with a switch."""
        self.__del__()
        print(f"++++ {self} is closed...")


class ServoAngle(object):
    """Angle for a ServoTrainSwitch."""
    MIN_ANGLE: int = 0
    MAX_ANGLE: int = 80


class ServoTrainSwitch(BinaryDevice):
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

        self.__name__ = "Servo Train Switch"
        if len(self.pin) != self.get_required_pins:
            raise ValueError(f"Expecting one pin. Found {self.pin}")
        self.pin_name = self.pin[0]
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.initial_angle = initial_angle

        self.servo = AngularServo(
            pin=self.pin_name,
            initial_angle=self.initial_angle,
            min_angle=self.min_angle,
            max_angle=self.max_angle,
        )

        print(f"++++ {self} is started...")

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
                "Invalid command to train switch." +
                f"\n Found action: {action}"
            )
        return angle

    def _action(self, action: str) -> str:
        # Optional[float]
        angle = self.action_to_angle(action)
        self.servo.angle = angle
        return str(angle)

    def __del__(self) -> None:
        self.servo.close()


class RelayTrainSwitch(BinaryDevice):
    required_pins: int = 2
    on_state: str = "straight"
    off_state: str = "turn"

    def __init__(
        self,
        active_high: bool = False,
        initial_value: bool = False,
        **kwargs
    ) -> None:
        """Relay switch wrapping the gpiozero class for remote train switches.

        References:
            https://picozero.readthedocs.io/en/latest/api.html#digitaloutputdevice
            https://www.electronicshub.org/control-a-relay-using-raspberry-pi/
        """
        super(RelayTrainSwitch, self).__init__(**kwargs)
        self.__name__ = "Relay Train Switch"

        if len(self.pin) != self.get_required_pins:
            raise ValueError(f"Expecting two pins. Found {self.pin}")

        _pins: list[int] = list(self.pin)

        # when active_high=False, on() seems to pass voltage and off() seems to pass no voltage.
        # We initially set to False.
        self.yg_relay = DigitalOutputDevice(
            pin=_pins[0],
            active_high=active_high,
            initial_value=initial_value
        )
        self.br_relay = DigitalOutputDevice(
            pin=_pins[1],
            active_high=active_high,
            initial_value=initial_value
        )

        print(f"++++ {self} is started...")

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
            time.sleep(BLINK)
            self.br_relay.off()
        elif action == RelayTrainSwitch.on_state:
            self.yg_relay.off()
            self.yg_relay.on()
            time.sleep(BLINK)
            self.yg_relay.off()
        elif action is None:
            pass
        else:
            raise ValueError(
                "Invalid command to train switch." +
                f"\n Found action: {action}"
            )
        return action

    def __del__(self) -> None:
        self.yg_relay.close()
        self.br_relay.close()


class OnOff(BinaryDevice):
    required_pins = 1
    on_state = "on"
    off_state = "off"

    def __init__(
        self,
        active_high: bool = False,
        initial_value: bool = False,
        **kwargs,
    ) -> None:
        """ OnOff wrapping the picozero class for generic devices.

        References:
            https://www.electronicshub.org/control-a-relay-using-raspberry-pi/
        """
        super(OnOff, self).__init__(**kwargs)
        self.__name__ = "On/Off"

        if len(self.pin) != self.get_required_pins:
            raise ValueError(f"Expecting one pin. Found {self.pin}")

        # when active_high=False, on() seems to pass voltage and off() seems to pass no voltage.
        # We initially set to False.
        self.relay = DigitalOutputDevice(
            pin=self.pin[0],
            active_high=active_high,
            initial_value=initial_value
        )

        print(f"++++ {self} is started...")

    def custom_state_setter(self, state: str) -> None:
        if not state:
            self.relay.off()

    def _action(self, action: str) -> str:
        if action == OnOff.off_state:
            self.relay.off()
        elif action == OnOff.on_state:
            self.relay.on()
        elif action is None:
            pass
        else:
            raise ValueError(
                "Invalid command to on/off device." +
                f"\n Found action: {action}"
            )
        return action

    def __del__(self) -> None:
        self.relay.close()


class Disconnect(OnOff):
    """Extension of On/Off for Disconnect accessory."""

    def __init__(self, active_high=False, **kwargs) -> None:
        super(Disconnect, self).__init__(active_high=active_high, **kwargs)
        self.__name__ = "Disconnect"
        self.safe_stop = None

    def safe_close_relay(self, timer: Timer) -> None:
        # If relay is on, turn it off
        print(
            f"\n {self}: \n" +
            f"++++ Background Thread: Checking for shutdown..."
        )
        if self.relay.value == 1:
            print(
                f"\n {self}: \n" +
                f"++++ Background Thread: auto-shutdown"
            )
            self.relay.off()
            self.state = self.off_state
        else:
            print(f"\n {self}: \n ++++ Background Thread: no action needed!")

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
                period=SAFE_SHUTDOWN * 1000,
                mode=Timer.ONE_SHOT,
                callback=self.safe_close_relay,
            )
        else:
            raise ValueError(
                "Invalid command to Disconnect device." +
                f"\n Found action: {action}"
            )
        return action

    def __del__(self) -> None:
        self.relay.off()
        if self.safe_stop is not None:
            self.safe_stop.deinit()
        super().__del__()


class Unloader(OnOff):
    """Extension of On/Off for Unloader accessory."""

    def __init__(self, **kwargs) -> None:
        super(Unloader, self).__init__(active_high=False, **kwargs)
        self.__name__ = "Unloader"


class InvertedDisconnect(Disconnect):
    """Extension of On/Off for Disconnect accessory w/ inverted active_high."""

    def __init__(self, **kwargs) -> None:
        super(InvertedDisconnect, self).__init__(active_high=True, **kwargs)
        self.__name__ = "Disconnect(i)"


class InvertedUnloader(OnOff):
    """Extension of On/Off for Unloader accessory w/ inverted active_high."""

    def __init__(self, **kwargs) -> None:
        super(InvertedUnloader, self).__init__(active_high=True, **kwargs)
        self.__name__ = "Unloader(i)"


class SpurTrainSwitch(RelayTrainSwitch):
    """Extension of Relay Switch that will optionally depower the track."""

    def __init__(self, active_high: bool = False, **kwargs) -> None:
        super(SpurTrainSwitch, self).__init__(
            active_high=active_high,
            **kwargs
        )
        self.__name__ = "Spur Train Switch"

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
                "Invalid command to train switch." +
                f"\n Found action: {action}"
            )
        return action


class InvertedSpurTrainSwitch(SpurTrainSwitch):
    """Extension of Spur Train Switch but with inverted active_high."""

    def __init__(self, **kwargs) -> None:
        super(InvertedSpurTrainSwitch, self).__init__(
            active_high=True,
            **kwargs
        )
        self.__name__ = "Spur(i) Train Switch"


class InvertedRelayTrainSwitch(RelayTrainSwitch):
    """Extension of Relay Train Switch but with inverted active_high."""

    def __init__(self, **kwargs) -> None:
        super(InvertedRelayTrainSwitch, self).__init__(
            active_high=True,
            **kwargs
        )
        self.__name__ = "Relay(i) Train Switch"


CLS_MAP: dict[str, type[BinaryDevice]] = {
    "relay": RelayTrainSwitch,
    "servo": ServoTrainSwitch,
    "spur": SpurTrainSwitch,
    "spuri": InvertedSpurTrainSwitch,
    "relayi": InvertedRelayTrainSwitch,
    "Relay Train Switch": RelayTrainSwitch,
    "Servo Train Switch": ServoTrainSwitch,
    "Spur Train Switch": SpurTrainSwitch,
    "Spur(i) Train Switch": InvertedSpurTrainSwitch,
    "Relay(i) Train Switch": InvertedRelayTrainSwitch,
    "On/Off": OnOff,
    "onoff": OnOff,
    "Disconnect": Disconnect,
    "disconnect": Disconnect,
    "Unloader": Unloader,
    "unloader": Unloader,
    "Disconnect(i)": InvertedDisconnect,
    "disconnecti": InvertedDisconnect,
    "Unloader(i)": InvertedUnloader,
    "unloaderi": InvertedUnloader,
}
