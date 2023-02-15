from __future__ import annotations

import dataclasses
from typing import Callable
import threading


class MissingGPIOLibraryError(Exception):
    pass


try:
    from RPi import GPIO as gpio
except ImportError:
    raise MissingGPIOLibraryError(
        "Could not import RPi.GPIO. If this code is running on a raspberry pi, "
        "make sure that the rpi-gpio library is installed. You may install it "
        "by running `pip install rpi-gpio`."
    )


class NotInRestingStateError(Exception):
    pass


@dataclasses.dataclass
class RotaryEncoder:
    _clk_pin: int
    _dt_pin: int
    increment: Callable[[], None]
    decrement: Callable[[], None]

    def __post_init__(self) -> None:
        self._clk_state = False
        self._dt_state = False

        self._last_resting_state = False

        self._state_lock = threading.Lock()

    def __enter__(self) -> RotaryEncoder:
        gpio.setup(self._clk_pin, gpio.IN, pull_up_down=gpio.PUD_DOWN)
        gpio.setup(self._dt_pin, gpio.IN, pull_up_down=gpio.PUD_DOWN)

        self._clk_state = self._get_clk_state()
        self._dt_state = self._get_dt_state()

        self._last_resting_state = self._current_resting_state()

        gpio.add_event_detect(self._clk_pin, gpio.BOTH, callback=self._on_clk_changed)
        gpio.add_event_detect(self._dt_pin, gpio.BOTH, callback=self._on_dt_changed)
        
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        gpio.remove_event_detect(self._clk_pin)
        gpio.remove_event_detect(self._dt_pin)
        gpio.cleanup((self._clk_pin, self._dt_pin))

    def _get_clk_state(self) -> bool:
        return bool(gpio.input(self._clk_pin))
    
    def _get_dt_state(self) -> bool:
        return bool(gpio.input(self._dt_pin))
    
    def _is_resting_state(self) -> bool:
        return self._clk_state == self._dt_state

    def _current_resting_state(self) -> bool:
        if not self._is_resting_state():
            raise NotInRestingStateError()
        return self._clk_state
    
    def _did_dial_move(self) -> bool:
        if self._is_resting_state() and self._current_resting_state() != self._last_resting_state:
            self._last_resting_state = self._current_resting_state()
            return True
        return False

    def _on_clk_changed(self, channel: object) -> None:
        with self._state_lock:
            self._dt_state = self._get_dt_state()
            self._clk_state = self._get_clk_state()
            if not self._did_dial_move():
                return
        self.decrement()

    def _on_dt_changed(self, channel: object) -> None:
        with self._state_lock:
            self._dt_state = self._get_dt_state()
            self._clk_state = self._get_clk_state()
            if not self._did_dial_move():
                return
        self.increment()
