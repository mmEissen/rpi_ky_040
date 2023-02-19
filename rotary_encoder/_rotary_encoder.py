from __future__ import annotations
import collections

import dataclasses
import enum
import traceback
from typing import Callable, Iterator, Optional
import threading
from contextlib import contextmanager


class MissingGPIOLibraryError(Exception):
    pass


try:
    import rotary_encoder_gpio_core as gpio  # type: ignore
except ImportError as e:
    raise MissingGPIOLibraryError(
        "Could not import RPi.GPIO. If this code is running on a raspberry pi, "
        "make sure that the rpi-gpio library is installed. You may install it "
        "by running `pip install rpi-gpio`."
    ) from e


BOUNCETIME_MS = 50


class NotInRestingStateError(Exception):
    pass


gpio.setmode(gpio.BCM)


Callback = Callable[[], object]


def gpio_thread_callback_handler(callback: Callback) -> None:
    callback()


def spawn_thread_callback_handler(callback: Callback) -> None:
    thread = threading.Thread(target=callback, daemon=True)
    thread.start()


@dataclasses.dataclass()
class RotaryEncoder:
    clk_pin: int
    dt_pin: int
    sw_pin: Optional[int] = None
    on_clockwise_turn: Optional[Callback] = None
    on_counter_clockwise_turn: Optional[Callback] = None
    on_button_down: Optional[Callback] = None
    on_button_up: Optional[Callback] = None

    clk_state: bool = False
    dt_state: bool = False
    last_resting_state: bool = False

    callback_handler: Callable[[Callback], object] = gpio_thread_callback_handler

    def __post_init__(self) -> None:
        if (self.on_button_down is not None or self.on_button_up is not None) and self.sw_pin is None:
            raise ValueError("You must set the `sw_pin` to add a button callback.")
    
    def start(self) -> None:
        gpio.setup(self.clk_pin, gpio.IN, pull_up_down=gpio.PUD_DOWN)
        gpio.setup(self.dt_pin, gpio.IN, pull_up_down=gpio.PUD_DOWN)

        self.clk_state = self._get_clk_state()
        self.dt_state = self._get_dt_state()

        self.last_resting_state = self._current_resting_state()

        gpio.add_event_detect(self.clk_pin, gpio.BOTH, callback=self._on_clk_changed)
        gpio.add_event_detect(self.dt_pin, gpio.BOTH, callback=self._on_dt_changed)
        
        if self.sw_pin is not None:
            gpio.setup(self.sw_pin, gpio.IN, pull_up_down=gpio.PUD_UP)
            gpio.add_event_detect(self.sw_pin, gpio.BOTH, callback=self._on_sw_changed, bouncetime=BOUNCETIME_MS)


    def stop(self) -> None:
        gpio.remove_event_detect(self.clk_pin)
        gpio.remove_event_detect(self.dt_pin)
        gpio.cleanup((self.clk_pin, self.dt_pin))
        if self.sw_pin is not None:
            gpio.remove_event_detect(self.sw_pin)
            gpio.cleanup((self.sw_pin,))

    def _get_clk_state(self) -> bool:
        return bool(gpio.input(self.clk_pin))
    
    def _get_dt_state(self) -> bool:
        return bool(gpio.input(self.dt_pin))
    
    def _is_resting_state(self) -> bool:
        return self.clk_state == self.dt_state

    def _current_resting_state(self) -> bool:
        if not self._is_resting_state():
            raise NotInRestingStateError()
        return self.clk_state
    
    def _did_dial_move(self) -> bool:
        if self._is_resting_state() and self._current_resting_state() != self.last_resting_state:
            self.last_resting_state = self._current_resting_state()
            return True
        return False

    def _on_clk_changed(self, channel: object, is_on: int) -> None:
        self.clk_state = bool(is_on)
        if  self._did_dial_move() and self.on_counter_clockwise_turn is not None:
            self.callback_handler(self.on_counter_clockwise_turn)  # type: ignore

    def _on_dt_changed(self, channel: object, is_on: int) -> None:
        self.dt_state = bool(is_on)
        if self._did_dial_move() and self.on_clockwise_turn is not None:
            self.callback_handler(self.on_clockwise_turn)  # type: ignore
    
    def _on_sw_changed(self, channel: object, is_on: int) -> None:
        # Here the is_on is unreliable because it's too fast, and the button
        # might still be in the transition.
        is_on = gpio.input(self.sw_pin)
        if not is_on and self.on_button_down is not None:
            self.callback_handler(self.on_button_down)  # type: ignore
        if is_on and self.on_button_up is not None:
            self.callback_handler(self.on_button_up)  # type: ignore


class CallbackHandling(enum.Enum):
    GPIO_INTERUPT_THREAD = enum.auto()
    GLOBAL_WORKER_THREAD = enum.auto()
    LOCAL_WORKER_THREAD = enum.auto()
    SPAWN_THREAD = enum.auto()


@contextmanager
def connect(
    *,
    clk_pin: int,
    dt_pin: int,
    sw_pin: Optional[int] = None,
    on_clockwise_turn: Optional[Callback] = None,
    on_counter_clockwise_turn: Optional[Callback] = None,
    on_button_down: Optional[Callback] = None,
    on_button_up: Optional[Callback] = None,
    callback_handling: CallbackHandling = CallbackHandling.GLOBAL_WORKER_THREAD,
) -> Iterator[None]:
    encoder = RotaryEncoder(
        clk_pin=clk_pin,
        dt_pin=dt_pin,
        sw_pin=sw_pin,
        on_clockwise_turn=on_clockwise_turn,
        on_counter_clockwise_turn=on_counter_clockwise_turn,
        on_button_down=on_button_down,
        on_button_up=on_button_up,
    )

    if callback_handling == CallbackHandling.GLOBAL_WORKER_THREAD:
        thread: CallbackThread
        with global_callback_thread() as thread:
            encoder.callback_handler = thread.queue.appendleft  # type: ignore
            encoder.start()
            try:
                yield
            finally:
                encoder.stop()
    elif callback_handling == CallbackHandling.LOCAL_WORKER_THREAD:
        worker_thread = CallbackThread()
        worker_thread.start()
        encoder.callback_handler = worker_thread.queue.appendleft  # type: ignore
        encoder.start()
        try:
            yield
        finally:
            encoder.stop()
            worker_thread.stop()
    else:
        if callback_handling == CallbackHandling.GPIO_INTERUPT_THREAD:
            handler = gpio_thread_callback_handler
        else:
            handler = spawn_thread_callback_handler
        encoder.callback_handler = handler  # type: ignore
        encoder.start()
        try:
            yield
        finally:
            encoder.stop()


class CallbackThread(threading.Thread):
    def __init__(self) -> None:
        self._stop_flag = threading.Event()
        self.queue: collections.deque[Callback] = collections.deque()
        super().__init__(name="ky-040-callback-handler", daemon=True)

    def run(self) -> None:
        while not self._stop_flag.is_set():
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
        self._stop_flag.set()
        self.join()


_global_callback_thread: Optional[CallbackThread] = None
_usage_counter = 0
_usage_counter_lock = threading.Lock()


@contextmanager
def global_callback_thread() -> Iterator[CallbackThread]:
    global _callback_queue, _global_callback_thread, _usage_counter
    with _usage_counter_lock:
        _usage_counter += 1
    if _global_callback_thread is None:
        _global_callback_thread = CallbackThread()
        _global_callback_thread.start()
    assert _global_callback_thread is not None
    try:
        yield _global_callback_thread
    finally:
        with _usage_counter_lock:
            _usage_counter -= 1
            if _usage_counter == 0:
                _global_callback_thread.stop()
                _global_callback_thread = None
