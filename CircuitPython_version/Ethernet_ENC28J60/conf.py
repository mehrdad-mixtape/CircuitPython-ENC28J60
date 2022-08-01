#!/usr/bin/env python
# -*- coding: utf8 -*-

#  GPLv3 License

# Copyright (c) 2022 mehrdad
# Developed by mehrdad-mixtape https://github.com/mehrdad-mixtape/CircuitPython-ENC28J60

# This is version for circuitpython 7.2 or higher

# ----------------------------- Libraries and Modules ----------------------------- #
from busio import SPI, I2C
from microcontroller import Pin
from board import *

# ----------------------------- Variables and Constants ----------------------------- #
### PICO:
## ENC28J60:
# Set static IP address
CLIENT_IP: list = [192, 168, 1, 198]
CLIENT_PORT: int = 6000
SUB_NET: list = [255, 255, 255, 0]
GATEWAY: list = [192, 168, 1, 1]
# Server_address
SERVER_IP: list = [192, 168, 1, 200]
SERVER_PORT: int = 5000
# DoS_config
DOS_CONFIG: tuple = (50, 90, 150, 150) # ARP=50, ICMP=90, TCP=150, UDP=150

# ----------------------------- Pinout Configurations ----------------------------- #
## define and initialize SPI:
cs_10: Pin = GP13 # Ethernet
sck_1: Pin = GP10 # Ethernet
mosi_1: Pin = GP11 # Ethernet
miso_1: Pin = GP12 # Ethernet

spi_bus_1: SPI = SPI(sck_1, MOSI=mosi_1, MISO=miso_1) # Ethernet
