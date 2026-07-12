from ..models.key import Key
from evdev import InputDevice
from .window_context import WindowContextProviderInterface as WCPI, NO_CONTEXT_WAS_ERROR


class KeyContext:
    def __init__(self, device: InputDevice, window_context: WCPI):
        self._X_ctx = None
        self._device = device
        self._win_ctx_provider = window_context

    @classmethod
    def from_cache(cls, device, cached_ctx_data):
        """Create a KeyContext with pre-populated window context state.
        
        Used for release/repeat events where we don't need to query
        window context again — we use the state from the original press.
        """
        instance = cls.__new__(cls)
        instance._device = device
        instance._win_ctx_provider = None
        instance._X_ctx = cached_ctx_data
        return instance

    def _query_window_context(self):
        # Query window context only if we don't have one already
        if self._X_ctx is not None:
            return
        # Make sure that the window context provider is valid before query
        if self._win_ctx_provider is not None:
            self._X_ctx = self._win_ctx_provider.get_window_context()
        # No valid window context provider? Prevent crash, use context error
        else:
            self._X_ctx = NO_CONTEXT_WAS_ERROR

    @property
    def wm_class(self):
        self._query_window_context()
        # guarantee string type returned
        return self._X_ctx["wm_class"] or "ERR: KeyContext: NoneType in wm_class"

    @property
    def wm_name(self):
        self._query_window_context()
        # guarantee string type returned
        return self._X_ctx["wm_name"] or "ERR: KeyContext: NoneType in wm_name"

    @property
    def wndw_ctxt_error(self):
        self._query_window_context()
        return self._X_ctx["wndw_ctxt_error"]

    @property
    def device_name(self):
        # guarantee string type returned
        return self._device.name or "ERR: KeyContext: NoneType in device_name"

    @property
    def capslock_on(self):
        return Key.LED_CAPSL in self._device.leds()

    @property
    def numlock_on(self):
        return Key.LED_NUML in self._device.leds()
