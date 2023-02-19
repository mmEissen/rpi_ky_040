

from setuptools import Extension
from setuptools.command.build_ext import build_ext


ext_modules = [
    Extension(
        'rotary_encoder_gpio_core._gpio', 
        [
            'source/py_gpio.c', 
            'source/c_gpio.c', 
            'source/cpuinfo.c', 
            'source/event_gpio.c', 
            'source/soft_pwm.c', 
            'source/py_pwm.c', 
            'source/common.c', 
            'source/constants.c',
        ]
    )
]


def build(setup_kwargs: dict[str, object]) -> None:
    """
    This function is mandatory in order to build the extensions.
    """
    setup_kwargs.update(
        {
            "ext_modules": ext_modules, 
            "cmdclass": {"build_ext": build_ext},
            "zip_safe": False,
        }
    )
