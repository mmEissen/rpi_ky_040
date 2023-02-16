from __future__ import annotations

import dataclasses
from typing import Callable, Optional
import threading
from contextlib import contextmanager


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


@contextmanager
def gpio_bcm_mode() -> None:
    original_mode = gpio.get_mode()
    gpio.set_mode(gpio.BCM)
    try:
        yield
    finally:
        if original_mode is not None:
            gpio.set_mode(original_mode)


@dataclasses.dataclass
class RotaryEncoderState:
    clk_state: bool = False
    dt_state: bool = False
    last_resting_state: bool = False
    state_lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)


@dataclasses.dataclass(frozen=True)
class RotaryEncoder:
    clk_pin: int
    dt_pin: int
    button_pin: Optional[int] = None
    on_clockwise_turn: Optional[Callable[[], None]] = None
    on_counter_clockwise_turn: Optional[Callable[[], None]] = None
    on_button_down: Optional[Callable[[], None]] = None
    on_button_up: Optional[Callable[[], None]] = None

    _state: RotaryEncoderState = dataclasses.field(default_factory=RotaryEncoderState, init=False)

    def __enter__(self) -> RotaryEncoder:
        with gpio_bcm_mode():
            gpio.setup(self.clk_pin, gpio.IN, pull_up_down=gpio.PUD_DOWN)
            gpio.setup(self.dt_pin, gpio.IN, pull_up_down=gpio.PUD_DOWN)

            self._state.clk_state = self._get_clk_state()
            self._state.dt_state = self._get_dt_state()

            self._state.last_resting_state = self._current_resting_state()

            gpio.add_event_detect(self.clk_pin, gpio.BOTH, callback=self._on_clk_changed)
            gpio.add_event_detect(self.dt_pin, gpio.BOTH, callback=self._on_dt_changed)
        
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        with gpio_bcm_mode():
            gpio.remove_event_detect(self.clk_pin)
            gpio.remove_event_detect(self.dt_pin)
            gpio.cleanup((self.clk_pin, self.dt_pin))

    def _get_clk_state(self) -> bool:
        with gpio_bcm_mode():
            return bool(gpio.input(self.clk_pin))
    
    def _get_dt_state(self) -> bool:
        with gpio_bcm_mode():
            return bool(gpio.input(self.dt_pin))
    
    def _is_resting_state(self) -> bool:
        return self._state.clk_state == self._state.dt_state

    def _current_resting_state(self) -> bool:
        if not self._is_resting_state():
            raise NotInRestingStateError()
        return self._state.clk_state
    
    def _did_dial_move(self) -> bool:
        if self._is_resting_state() and self._current_resting_state() != self._state.last_resting_state:
            self._state.last_resting_state = self._current_resting_state()
            return True
        return False

    def _on_clk_changed(self, channel: object) -> None:
        with self._state.state_lock:
            self._state.dt_state = self._get_dt_state()
            self._state.clk_state = self._get_clk_state()
            if not self._did_dial_move():
                return
        self.on_counter_clockwise_turn()

    def _on_dt_changed(self, channel: object) -> None:
        with self._state.state_lock:
            self._state.dt_state = self._get_dt_state()
            self._state.clk_state = self._get_clk_state()
            if not self._did_dial_move():
                return
        self.on_clockwise_turn()
