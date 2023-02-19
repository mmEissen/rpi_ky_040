# Rotary Encoder

A rotary encoder package for the Raspberry pi that "just works".

Tested with a [KY-040 Rotary Encoder](https://www.rcscomponents.kiev.ua/datasheets/ky-040-datasheet.pdf) on a Raspberry pi 3 B+

## Installation

Install via pip:
```
pip install rpi-rotary-encoder
```

## Example

```python
import rotary_encoder


counter = 0

def increment():
    global counter
    counter += 1
    print(counter)


def decrement():
    global counter
    counter -= 1
    print(counter)


def press():
    print("PRESS")


def release():
    print("RELEASE")


with rotary_encoder.connect(
    clk_pin=20,                           # required
    dt_pin=21,                            # required
    sw_pin=26,                            # optional
    on_clockwise_turn=increment,          # optional
    on_counter_clockwise_turn=decrement,  # optional
    on_button_down=press,                 # optional
    on_button_up=release,                 # optional
):
    input("press enter to quit\n")
```


## Advanced Usage

When calling `connect` you can pass in an optional `callback_handling` argument. This controls how the callbacks are executed. The options are:

- `CallbackHandling.GLOBAL_WORKER_THREAD`: The default. Callbacks are called in a global worker thread. This means all callbacks across all rotary encoders are called in the same thread. This ensures that all callbacks are executed sequentially. This is the least likely to cause problems with race conditions.
- `CallbackHandling.LOCAL_WORKER_THREAD`: Similar to the above, except that each individual rotary encoders callbacks are executed on a different thread. This means that sequential execution of the callbacks of one encoder is still guaranteed, but not across several encoders. The responsiveness of the individual encoders may be slightly improved.
- `CallbackHandling.SPAWN_THREAD`: Spawn a new thread for every callback. The execution of your callbacks is no longer sequential, and you will have to make sure that your callbacks are thread safe.
- `CallbackHandling.GPIO_INTERUPT_THREAD`:  Not recommended. Similar in behavior to `CallbackHandling.SPAWN_THREAD` except that the threads are spawned by the underlying C extension library.

## Similar Projects:

The [pigpio-encoder](https://pypi.org/project/pigpio-encoder/) is a similar library based on pigpio.
