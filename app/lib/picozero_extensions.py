from app.lib.picozero import Servo

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
            min_pulse_width: float = 1/1000,
            max_pulse_width: float = 2/1000,
            frame_width: float = 20/1000
        ):
        self._min_angle = min_angle
        self._angular_range = max_angle - min_angle
        if initial_angle is None:
            initial_value = None
        elif ((min_angle <= initial_angle <= max_angle) or
            (max_angle <= initial_angle <= min_angle)):
            initial_value = 2 * ((initial_angle - min_angle) / self._angular_range) - 1
        else:
            raise ValueError(
                "AngularServo angle must be between %s and %s, or None" %
                (min_angle, max_angle)
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
        elif ((self.min_angle <= angle <= self.max_angle) or
              (self.max_angle <= angle <= self.min_angle)):
            self.value = (
                self._value_range *
                ((angle - self._min_angle) / self._angular_range) +
                self._min_value)
        else:
            raise ValueError(
                "AngularServo angle must be between %s and %s, or None" %
                (self.min_angle, self.max_angle))