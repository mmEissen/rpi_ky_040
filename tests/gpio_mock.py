import collections
from typing import Callable, Optional


class GPIO:
    IN = 1
    PUD_DOWN = 21
    RISING = 31
    FALLING = 32
    BOTH = 33
    BCM = 11

    @staticmethod
    def setup(pin: int, direction: object, pull_up_down: object) -> None:
        return
    
    @staticmethod
    def input(pin: int) -> int:
        return _pins[pin]

    @staticmethod
    def add_event_detect(pin: int, condition: str, callback: Optional[Callable[[int], None]] = None) -> None:
        if callback is None:
            return
        if condition == GPIO.RISING:
            encoded_condition = True
        elif condition == GPIO.FALLING:
            encoded_condition = False
        else:
            encoded_condition = None
        _callbacks[pin] = (encoded_condition, callback)
    
    @staticmethod
    def remove_event_detect(pin: int) -> None:
        del _callbacks[pin]
    
    @staticmethod
    def cleanup(pins: object = None) -> None:
        return
    
    @staticmethod
    def getmode() -> None:
        return None

    @staticmethod
    def setmode(mode: int) -> None:
        return

_pins: collections.defaultdict[int, int]
_callbacks: dict[int, tuple[Optional[bool], Callable[[int], None]]]

def reset():
    global _pins, _callbacks
    _pins = collections.defaultdict(int)
    _callbacks = {}

def set_pin(pin: int, state: bool) -> None:
    value = int(state)
    if value == _pins[pin]:
        return
    is_rising = state > _pins[pin]
    _pins[pin] = value
    try:
        condition, callback = _callbacks[pin]
    except KeyError:
        pass
    else:
        if condition is is_rising or condition is None:
            callback(pin)
        return

def run_sequence(pins: tuple[int, ...], sequences: tuple[str, ...]):
    assert len(pins) == len(sequences)
    assert all(len(sequence) == len(sequences[0]) for sequence in sequences)

    for states in zip(*sequences):
        for pin, state in zip(pins, states):
            set_pin(pin, state == "1")
