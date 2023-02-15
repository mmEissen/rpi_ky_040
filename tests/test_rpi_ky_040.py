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
        clk_pin, dt_pin, mock.MagicMock(), mock.MagicMock()
    ) as rotary_encoder:
        yield rotary_encoder


@pytest.mark.parametrize(
    "clk_pin_states, dt_pin_states, increments, decrements",
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
    increments,
    decrements,
):
    gpio_mock.run_sequence((clk_pin, dt_pin), (clk_pin_states, dt_pin_states))

    assert rotary_encoder.increment.call_count == increments
    assert rotary_encoder.decrement.call_count == decrements
