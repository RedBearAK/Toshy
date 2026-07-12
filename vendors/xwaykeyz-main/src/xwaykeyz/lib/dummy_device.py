class DummyDevice:
    """
    A minimal dummy device that mimics the interface of evdev.InputDevice
    needed for proper state tracking during initialization.
    """
    def __init__(self, name="xwaykeyz-dummy-device"):
        self.name = name
        self.path = "dummy-device-path"  # Using 'path' instead of deprecated 'fn'
        self._leds = set()
    
    def leds(self):
        """Return empty set of LEDs - no CapsLock/NumLock active"""
        return self._leds
    
    def set_led(self, led_code, state=True):
        """Enable tracking LED states like CapsLock"""
        if state:
            self._leds.add(led_code)
        else:
            self._leds.discard(led_code)
