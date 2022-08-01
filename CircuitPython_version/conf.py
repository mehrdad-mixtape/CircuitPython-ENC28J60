#!/usr/bin/env python
# -*- coding: utf8 -*-

#  MIT License

# Copyright (c) 2022 mehrdad
# Developed by mehrdad-mixtape https://github.com/mehrdad-mixtape

# This is version for circuitpython 7.2

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
# I2C_LCD:
I2C_NUM_ROWS: int = 2
I2C_NUM_COLS: int = 16

# TTP229 touch keypad
KEYPAD_MODE: int = 32

## Sensor_ID:
PICO = 'n/a'
DOOR = '00'
VIBRATE = '01'
TEMPERATURE = '02'
HUMIDITY = '03'
FAN = '04'
RFID_RW = '05'
GAS = '06'
MOVE = '07'
FIRE = '08'
sensors: dict = {
    DOOR: 'door',
    VIBRATE: 'vibrate',
    TEMPERATURE: 'temperature',
    HUMIDITY: 'humidity',
    FAN: 'fan',
    RFID_RW: 'RFID',
    GAS: 'gas',
    MOVE: 'move',
    FIRE: 'fire'
}
## rack_id:
RACK_ID: str = '0001'

## device_id:
DEVICE_ID: str = '001'

## payload
payload: str = "{}>>priority::{}__rack_id::" + RACK_ID + "__device_id::" + DEVICE_ID + "__sensor_id::{}__data::{}\n"

## Stack:
STACK: list = []

## Log files:
DATA_LOGGER: str = 'payload.log'
SYSTEM_LOGGER: str = 'system.log'

## Loop:
DELAY: float = 0.0001
COOL_DOWN_PERIOD: int = 30
KEEP_ALIVE: int = 50
UPDATE_CLOCK_PERIOD_1: int = 20
UPDATE_CLOCK_PERIOD_2: int = 80
SEND_OR_STORE_PERIOD: int = 70
CLEAR_PERIOD: int = 90
CHECK_SD: int = 100
RECONNECT_PERIOD: int = 120
OFFSET_TIME: int = 0.1

## Sensor limit:
L_MOVE: int = 150
L_GAS: int = 250
L_TH: int = 200
L_FAN: int = 200

# ----------------------------- Pinout Configurations ----------------------------- #
## define and initialize SPI:
cs_10: Pin = GP13 # Ethernet
cs_11: Pin = GP7 # RFID
cs_00: Pin = GP5 # SDcard
sck_1: Pin = GP10 # Ethernet, RFID
sck_0: Pin = GP2 # SDcard
mosi_1: Pin = GP11 # Ethernet, RFID
mosi_0: Pin = GP3 # SDcard
miso_1: Pin = GP12 # Ethernet, RFID
miso_0: Pin = GP4 # SDcard

spi_bus_1: SPI = SPI(sck_1, MOSI=mosi_1, MISO=miso_1) # Ethernet, RFID
spi_bus_0: SPI = SPI(sck_0, MOSI=mosi_0, MISO=miso_0) # SDcard

## define and initialize I2C:
scl_10: Pin = GP15 # I2C LCD
sda_10: Pin = GP14 # I2C LCD
i2c_bus_1: I2C = I2C(scl_10, sda_10, frequency=200_000)

## define and initialize ADC:
adc_0: Pin = GP26 # Vibrate
adc_1: Pin = GP27 # Gas density

## define and initialize GPIO_INPUT:
input_0: Pin = GP21 # Door
input_1: Pin = GP20 # Move
input_2: Pin = GP19 # Fire

## define and initialize GPIO_OUTPUT:
output_0: Pin = GP18 # Relay-module
output_1: Pin = GP17 # Relay-module

## define and initialize PWM:
pwm_0: Pin = GP28 # Fan
pwm_1: Pin = GP22 # Buzzer

## define and initial pins for other:
sdo: Pin = GP0 # Keypad
scl: Pin = GP1 # Keypad
am2302_pin: Pin = GP6 # AM2302
