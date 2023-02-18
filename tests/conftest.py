import sys
import gpio_mock as gpio_mock_module
import pytest


def pytest_sessionstart(session):
    sys.modules["RPi"] = gpio_mock_module


@pytest.fixture()
def gpio_mock():
    gpio_mock_module.reset()
    return gpio_mock_module
