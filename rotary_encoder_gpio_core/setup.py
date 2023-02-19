# -*- coding: utf-8 -*-
from setuptools import setup

packages = \
['rotary_encoder_gpio_core']

package_data = \
{'': ['*']}

setup_kwargs = {
    'name': 'rotary-encoder-gpio-core',
    'version': '0.1.0',
    'description': '',
    'long_description': '# Fork of RPi.GPIO\n\nFor the original repo go to:\nhttp://sourceforge.net/p/raspberry-gpio-python/\n\nThis package provides a Python module to control the GPIO on a Raspberry Pi.\n\nNote that this module is unsuitable for real-time or timing critical applications.  This is because you\ncan not predict when Python will be busy garbage collecting.  It also runs under the Linux kernel which\nis not suitable for real time applications - it is multitasking O/S and another process may be given\npriority over the CPU, causing jitter in your program.  If you are after true real-time performance and\npredictability, buy yourself an Arduino http://www.arduino.cc !\n\nNote that the current release does not support SPI, I2C, hardware PWM or serial functionality on the RPi yet.\nThis is planned for the near future - watch this space!  One-wire functionality is also planned.\n\nAlthough hardware PWM is not available yet, software PWM is available to use on all channels.\n\nFor examples and documentation, visit http://sourceforge.net/p/raspberry-gpio-python/wiki/Home/\n\n',
    'author': 'None',
    'author_email': 'None',
    'maintainer': 'None',
    'maintainer_email': 'None',
    'url': 'None',
    'packages': packages,
    'package_data': package_data,
    'python_requires': '>=3.9,<4.0',
}
from build import *
build(setup_kwargs)

setup(**setup_kwargs)
