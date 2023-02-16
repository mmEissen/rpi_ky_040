from __future__ import annotations
import collections

import dataclasses
import enum
import traceback
from typing import Callable, Iterable, Optional
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
def gpio_bcm_mode() -> Iterable[None]:
    original_mode = gpio.getmode()
    gpio.setmode(gpio.BCM)
    try:
        yield
    finally:
        if original_mode is not None:
            gpio.setmode(original_mode)


@dataclasses.dataclass
class RotaryEncoderState:
    clk_state: bool = False
    dt_state: bool = False
    last_resting_state: bool = False
    state_lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)


Callback = Callable[[], None]


def same_thread_callback_handler(callback: Callback) -> None:
    callback()


def spawn_thread_callback_handler(callback: Callback) -> None:
    thread = threading.Thread(target=callback, daemon=True)
    thread.start()


@dataclasses.dataclass(frozen=True)
class RotaryEncoder:
    clk_pin: int
    dt_pin: int
    sw_pin: Optional[int] = None
    on_clockwise_turn: Optional[Callback] = None
    on_counter_clockwise_turn: Optional[Callback] = None
    on_button_down: Optional[Callback] = None
    on_button_up: Optional[Callback] = None

    _callback_handler: Callable[[Callback], object] = same_thread_callback_handler
    _state: RotaryEncoderState = dataclasses.field(default_factory=RotaryEncoderState, init=False)
    
    def start(self) -> None:
        with gpio_bcm_mode():
            gpio.setup(self.clk_pin, gpio.IN, pull_up_down=gpio.PUD_DOWN)
            gpio.setup(self.dt_pin, gpio.IN, pull_up_down=gpio.PUD_DOWN)

            self._state.clk_state = self._get_clk_state()
            self._state.dt_state = self._get_dt_state()

            self._state.last_resting_state = self._current_resting_state()

            gpio.add_event_detect(self.clk_pin, gpio.BOTH, callback=self._on_clk_changed)
            gpio.add_event_detect(self.dt_pin, gpio.BOTH, callback=self._on_dt_changed)

    def stop(self) -> None:
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
        if self.on_counter_clockwise_turn is not None:
            self._callback_handler(self.on_counter_clockwise_turn)

    def _on_dt_changed(self, channel: object) -> None:
        with self._state.state_lock:
            self._state.dt_state = self._get_dt_state()
            self._state.clk_state = self._get_clk_state()
            if not self._did_dial_move():
                return
        if self.on_clockwise_turn is not None:
            self._callback_handler(self.on_clockwise_turn)


class CallbackHandling(enum.Enum):
    SAME_THREAD = enum.auto()
    GLOBAL_WORKER_THREAD = enum.auto()
    LOCAL_WORKER_THREAD = enum.auto()
    SPAWN_THREAD = enum.auto()


@contextmanager
def rotary_encoder(
    *,
    clk_pin: int,
    dt_pin: int,
    sw_pin: Optional[int] = None,
    on_clockwise_turn: Optional[Callback] = None,
    on_counter_clockwise_turn: Optional[Callback] = None,
    on_button_down: Optional[Callback] = None,
    on_button_up: Optional[Callback] = None,
    callback_handling: CallbackHandling = CallbackHandling.SPAWN_THREAD,
) -> Iterable[RotaryEncoder]:
    kwargs = dict(
        clk_pin=clk_pin,
        dt_pin=dt_pin,
        sw_pin=sw_pin,
        on_clockwise_turn=on_clockwise_turn,
        on_counter_clockwise_turn=on_counter_clockwise_turn,
        on_button_down=on_button_down,
        on_button_up=on_button_up,
    )

    if callback_handling == CallbackHandling.GLOBAL_WORKER_THREAD:
        with callback_queue() as queue:
            encoder = RotaryEncoder(
                _callback_handler=queue.appendleft,
                **kwargs
            )
            encoder.start()
            try:
                yield encoder
            finally:
                encoder.stop()
    elif callback_handling == CallbackHandling.LOCAL_WORKER_THREAD:
        worker_thread = CallbackThread()
        worker_thread.start()
        encoder = RotaryEncoder(
            _callback_handler=worker_thread.queue.appendleft,
            **kwargs
        )
        encoder.start()
        try:
            yield encoder
        finally:
            encoder.stop()
            worker_thread.stop()
    else:
        if callback_handling == CallbackHandling.SAME_THREAD:
            handler = same_thread_callback_handler
        else:
            handler = spawn_thread_callback_handler
        encoder = RotaryEncoder(
            _callback_handler=handler,
            **kwargs
        )
        encoder.start()
        try:
            yield encoder
        finally:
            encoder.stop()


class CallbackThread(threading.Thread):
    def __init__(self) -> None:
        self._is_running = True
        self.queue: collections.deque[Callback] = collections.deque()
        super().__init__(name="ky-040-callback-handler", daemon=True)

    def run(self) -> None:
        while self._is_running:
            try:
                callback = self.queue.pop()
            except IndexError:
                pass
            else:
                try:
                    callback()
                except Exception:
                    traceback.print_exc()
        while True:
            try:
                callback = self.queue.pop()
            except IndexError:
                return
            else:
                try:
                    callback()
                except Exception:
                    traceback.print_exc()
    
    def stop(self) -> None:
        self._is_running = False
        self.join()


_global_callback_thread: Optional[CallbackThread] = None
_usage_counter = 0
_usage_counter_lock = threading.Lock()


@contextmanager
def callback_queue() -> Iterable[collections.deque[Callback]]:
    global _callback_queue, _global_callback_thread, _usage_counter
    with _usage_counter_lock:
        _usage_counter += 1
    if _global_callback_thread is None:
        _global_callback_thread = CallbackThread()
        _global_callback_thread.start()
    assert _global_callback_thread is not None
    try:
        yield _global_callback_thread.queue
    finally:
        with _usage_counter_lock:
            _usage_counter -= 1
            if _usage_counter == 0:
                _global_callback_thread.stop()
                _global_callback_thread = None
