import rpi_ky_040
import pytest
from unittest import mock


@pytest.fixture
def clk_pin():
    return 1


@pytest.fixture
def dt_pin():
    return 2


@pytest.fixture
def rotary_encoder(gpio_mock, clk_pin, dt_pin):
    with rpi_ky_040.RotaryEncoder(
        clk_pin=clk_pin,
        dt_pin=dt_pin,
        on_clockwise_turn=mock.MagicMock(), 
        on_counter_clockwise_turn=mock.MagicMock(),
    ) as rotary_encoder:
        yield rotary_encoder


@pytest.mark.parametrize(
    "clk_pin_states, dt_pin_states, clockwise_turns, counter_clockwise_turns",
    [
        pytest.param(
            "011", 
            "001", 
            1, 0, id="one increment"
        ),
        pytest.param(
            "001", 
            "011", 
            0, 1, id="one decrement"
        ),
        pytest.param(
            "00001", 
            "01011", 
            0, 1, id="one decrement with decrement flicker"
        ),
        pytest.param(
            "00011", 
            "01001", 
            1, 0, id="one increment with decrement flicker"
        ),
        pytest.param(
            "011000110", 
            "001101100", 
            2, 2, id="two increments two decrements"
        ),
    ],
)
def test_increment_decrement(
    gpio_mock,
    rotary_encoder: rpi_ky_040.RotaryEncoder,
    clk_pin,
    dt_pin,
    clk_pin_states,
    dt_pin_states,
    clockwise_turns,
    counter_clockwise_turns,
):
    gpio_mock.run_sequence((clk_pin, dt_pin), (clk_pin_states, dt_pin_states))

    assert rotary_encoder.on_clockwise_turn.call_count == clockwise_turns
    assert rotary_encoder.on_counter_clockwise_turn.call_count == counter_clockwise_turns
