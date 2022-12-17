class GPIOZeroError(Exception):
    "Base class for all exceptions in GPIO Zero"

class GPIODeviceError(GPIOZeroError):
    "Base class for errors specific to the GPIODevice hierarchy"

class OutputDeviceError(GPIODeviceError):
    "Base class for errors specified to the OutputDevice hierarchy"

class OutputDeviceBadValue(OutputDeviceError, ValueError):
    "Error raised when ``value`` is set to an invalid value"