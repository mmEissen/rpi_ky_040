# RPi KY-040

This package makes it easy to use a [KY-040 Rotary Encoder](https://www.rcscomponents.kiev.ua/datasheets/ky-040-datasheet.pdf) with a raspberry pi.

## Installation

Install via pip:
```
pip install rpi-ky-040
```

## Example

```python
from rpi_ky_040 import rotary_encoder


counter = 0

def increment():
    global counter
    counter += 1
    print(counter)


def decrement():
    global counter
    counter -= 1
    print(counter)


with rotary_encoder(
    clk_pin=20,
    dt_pin=21,
    on_clockwise_turn=increment,
    on_counter_clockwise_turn=decrement,
):
    input("press enter to quit\n")
```


## Advanced Usage

The `rotary_encoder` context manager can take an optional `callback_handling` argument. This controls how the callbacks are executed. The options are:

- `CallbackHandling.GLOBAL_WORKER_THREAD`: The default. Callbacks are called in a global worker thread. This means all callbacks across all rotary encoders are called in the same thread. This ensures that all callbacks are executed sequentially. This is the least likely to cause problems with race conditions.
- `CallbackHandling.LOCAL_WORKER_THREAD`: Similar to the above, except that each individual rotary encoders callbacks are executed on a different thread. This means that sequential execution of the callbacks of one encoder is still guaranteed, but not across several encoders.
- `CallbackHandling.SPAWN_THREAD`: Spawn a new thread for every callback. The execution of your callbacks is no longer sequential, and you will have to make sure that your callbacks are thread safe.
- `CallbackHandling.GPIO_INTERUPT_THREAD`:  Not recommended. The callbacks are executed on the thread spawned by the underlying `RPi.GPIO` library. If your callbacks execution takes too long, some callback calls might get skipped.


## Similar Projects:

The [pigpio-encoder](https://pypi.org/project/pigpio-encoder/) is a similar library based on pigpio.
