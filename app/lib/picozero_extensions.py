from app.lib.picozero import Servo

class AngularServo(Servo):
    """
    Extends :class:`Servo` and represents a rotational PWM-controlled servo
    motor which can be set to particular angles (assuming valid minimum and
    maximum angles are provided to the constructor).

    Connect a power source (e.g. a battery pack or the 5V pin) to the power
    cable of the servo (this is typically colored red); connect the ground
    cable of the servo (typically colored black or brown) to the negative of
    your battery pack, or a GND pin; connect the final cable (typically colored
    white or orange) to the GPIO pin you wish to use for controlling the servo.

    Next, calibrate the angles that the servo can rotate to. In an interactive
    Python session, construct a :class:`Servo` instance. The servo should move
    to its mid-point by default. Set the servo to its minimum value, and
    measure the angle from the mid-point. Set the servo to its maximum value,
    and again measure the angle::

        >>> from gpiozero import Servo
        >>> s = Servo(17)
        >>> s.min() # measure the angle
        >>> s.max() # measure the angle

    You should now be able to construct an :class:`AngularServo` instance
    with the correct bounds::

        >>> from gpiozero import AngularServo
        >>> s = AngularServo(17, min_angle=-42, max_angle=44)
        >>> s.angle = 0.0
        >>> s.angle
        0.0
        >>> s.angle = 15
        >>> s.angle
        15.0

    .. note::

        You can set *min_angle* greater than *max_angle* if you wish to reverse
        the sense of the angles (e.g. ``min_angle=45, max_angle=-45``). This
        can be useful with servos that rotate in the opposite direction to your
        expectations of minimum and maximum.

    :type pin: int or str
    :param pin:
        The GPIO pin that the servo is connected to. See :ref:`pin-numbering`
        for valid pin numbers. If this is :data:`None` a :exc:`GPIODeviceError`
        will be raised.

    :param float initial_angle:
        Sets the servo's initial angle to the specified value. The default is
        0. The value specified must be between *min_angle* and *max_angle*
        inclusive. :data:`None` means to start the servo un-controlled (see
        :attr:`value`).

    :param float min_angle:
        Sets the minimum angle that the servo can rotate to. This defaults to
        -90, but should be set to whatever you measure from your servo during
        calibration.

    :param float max_angle:
        Sets the maximum angle that the servo can rotate to. This defaults to
        90, but should be set to whatever you measure from your servo during
        calibration.

    :param float min_pulse_width:
        The pulse width corresponding to the servo's minimum position. This
        defaults to 1ms.

    :param float max_pulse_width:
        The pulse width corresponding to the servo's maximum position. This
        defaults to 2ms.

    :param float frame_width:
        The length of time between servo control pulses measured in seconds.
        This defaults to 20ms which is a common value for servos.

    :type pin_factory: Factory or None
    :param pin_factory:
        See :doc:`api_pins` for more information (this is an advanced feature
        which most users can ignore).
    """
    def __init__(
            self, pin=None, initial_angle=0.0,
            min_angle=-90, max_angle=90,
            min_pulse_width=1/1000, max_pulse_width=2/1000,
            frame_width=20/1000, pin_factory=None):
        self._min_angle = min_angle
        self._angular_range = max_angle - min_angle
        if initial_angle is None:
            initial_value = None
        elif ((min_angle <= initial_angle <= max_angle) or
            (max_angle <= initial_angle <= min_angle)):
            initial_value = 2 * ((initial_angle - min_angle) / self._angular_range) - 1
        else:
            raise Exception(
                "AngularServo angle must be between %s and %s, or None" %
                (min_angle, max_angle))
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
        result = self._get_value()
        if result is None:
            return None
        else:
            # NOTE: Why round(n, 12) here instead of 14? Angle ranges can be
            # much larger than -1..1 so we need a little more rounding to
            # smooth off the rough corners!
            return round(
                self._angular_range *
                ((result - self._min_value) / self._value_range) +
                self._min_angle, 12)

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
            raise OutputDeviceBadValue(
                "AngularServo angle must be between %s and %s, or None" %
                (self.min_angle, self.max_angle))