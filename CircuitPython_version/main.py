#!/usr/bin/env python
# -*- coding: utf8 -*-

#  MIT License

# Copyright (c) 2022 mehrdad
# Developed by mehrdad-mixtape https://github.com/mehrdad-mixtape

# This is version for circuitpython 7.2

# ----------------------------- Libraries and Modules ----------------------------- #

# builtin libs:
from gc import collect
from time import sleep, time
from random import choice
from sys import exit
from conf import *

# external libs:
from Transport import UDP, DEAD
from LCD import LCD
from MH_FMG import BUZZER
from IR import Door, Fire
from RFID import RFID
from SW180 import SW_180
from MQx import MQx
from HC_SR505 import HC_SR505
from TTP229 import TTP229
from AM2302 import AM2302
from SD_Card import SD_Card
from log4pico import logging
from Relay_2ch import Relay, ACTIVE, INACTIVE
from Fan import Fan

__version__ = '15.0.0v'
__repo__ = 'https://github.com/mehrdad-mixtape'

# ----------------------------- Device Initialization ----------------------------- #
## Initial LCD-I2C:
lcd: LCD = LCD(i2c_bus_1, I2C_NUM_ROWS, I2C_NUM_COLS)
lcd.LCD_show("System Boot", 'Boot'); sleep(1)
## Initial Buzzer:
buzzer: BUZZER = BUZZER(pwm_1)
## Initial SD-Card:
sd_card: SD_Card = SD_Card(spi_bus_0, cs_00, lcd=lcd, buzzer=buzzer)
## Initial Logger:
logger: logging = logging(sd_card)
## Initial Door:
door: Door = Door(input_0, lcd=lcd, logger=logger)
## Initial Fire:
fire: Fire = Fire(input_2, lcd=lcd, logger=logger)
## Initial Vibrate:
vibrate: SW_180 = SW_180(adc_0, lcd=lcd, logger=logger)
## Initial Movement:
move: HC_SR505 = HC_SR505(input_1, lcd=lcd, limit=L_MOVE, logger=logger)
## Initial Gas:
gas: MQx = MQx(adc_1, lcd=lcd, limit=L_GAS, logger=logger)
## Initial AM2302:
temp_and_humid: AM2302 = AM2302(am2302_pin, lcd=lcd, limit=L_TH, logger=logger)
## Initial RFID:
rfid: RFID = RFID(spi_bus_1, cs_11, lcd=lcd, buzzer=buzzer, logger=logger)
## Initial Ethernet:
ethernet: UDP = UDP(spi_bus_1, cs_10, CLIENT_IP, SUB_NET, SERVER_IP, SERVER_PORT, GATEWAY,
src_port=CLIENT_PORT, dos_conf=DOS_CONFIG, ttc=10, lcd=lcd, buzzer=buzzer, logger=logger)
## Initial KeyPad:
keypad: TTP229 = TTP229(scl, sdo, mode=KEYPAD_MODE, logger=logger)
## Initial Relay:
relay: Relay = Relay(output_0, output_1, logger=logger)
## Initial Fan:
fan: Fan = Fan(pwm_0, duty_cycle=60000, freq=500, lcd=lcd, limit=L_FAN, logger=logger)
## Add attrib to logger
logger.date = ethernet.date_and_time

# ----------------------------- Functions ----------------------------- #
def set_priority(sensor_id: str, data: str) -> str:
    priority: str = ''
    if sensor_id == '00': # Door
        if data == 'OPEN': priority = 'WARNING'
        elif data == 'CLOSE': priority = 'INFO'
    elif sensor_id == '01': # vibrate
        raw: float = float(data.split('G')[0])
        if 1 <= raw <= 2: priority = 'INFO'
        elif 3 <= raw <= 4: priority = 'WARNING'
        elif 5 <= raw <= 7: priority = 'ERROR'
        elif 8 <= raw <= 10:
            priority = 'CRITICAL'
            buzzer.play(20, speed=50, volume=60000)
    elif sensor_id == '02': # temperature
        raw: float = float(data.split('C')[0])
        if 0 <= raw <= 9 or 71 <= raw:
            priority = 'CRITICAL'
            buzzer.play(20, speed=50, volume=60000)
        elif 10 <= raw <= 40: priority = 'INFO'
        elif 41 <= raw <= 50: priority = 'WARNING'
        elif 51 <= raw <= 70: priority = 'ERROR'
    elif sensor_id == '03': # humidity
        raw: float = float(data.split('%')[0])
        if 0 <= raw <= 40: priority = 'INFO'
        elif 41 <= raw <= 50: priority = 'WARNING'
        elif 61 <= raw <= 70: priority = 'ERROR'
        elif 81 <= raw <= 100:
            priority = 'CRITICAL'
            buzzer.play(20, speed=50, volume=60000)
    elif sensor_id == '04': # fan
        raw: float = float(data.split('%')[0])
        if 0 <= raw <= 40: priority = 'INFO'
        elif 41 <= raw <= 50: priority = 'WARNING'
        elif 61 <= raw <= 70: priority = 'ERROR'
        elif 81 <= raw <= 100:
            priority = 'CRITICAL'
            buzzer.play(20, speed=50, volume=60000)
    elif sensor_id == '06': # gas
        try: raw: float = float(data.split('%')[0])
        except ValueError: raw: float = float(data.split()[1].split('%')[0])
        if 0 <= raw <= 20: priority = 'INFO'
        elif 21 <= raw <= 30: priority = 'WARNING'
        elif 31 <= raw <= 50: priority = 'ERROR'
        elif 51 <= raw <= 100:
            priority = 'CRITICAL'
            buzzer.play(20, speed=50, volume=60000)
    elif sensor_id == '07': # move
        if data == 'DETECT': priority = 'WARNING'
        elif data == 'UnDETECT': priority = 'INFO'
    elif sensor_id == '08': # fire
        if data == 'DETECT':
            priority = 'CRITICAL'
            buzzer.play(20, speed=50, volume=60000)
        elif data == 'UnDETECT': priority = 'INFO'
    else: priority = 'INFO'
    return priority

def event(msg: str, priority: str='INFO', log_it: bool=True) -> None:
    try:
        if log_it: logger.event_registrar('PICO', priority, msg)
    except AttributeError: pass
    finally: print(f"PICO: {msg}")

def send_payload(sensor_id: str, data: str) -> None:
    ethernet.tx_udp(
        payload.format(
            'log',
            set_priority(sensor_id, data),
            sensor_id,
            f"{sensors.get(sensor_id, 'n/a')}_status: {data}"
        ).strip('\n')
    )
    ethernet.rx_udp()
    sleep(DELAY)

def store_payload(sensor_id: str, data: str) -> None:
    sd_card.write(
        payload.format(
            'log',
            set_priority(sensor_id, data),
            sensor_id,
            f"{sensors.get(sensor_id, 'n/a')}_status: {data}"
        ),
        name=DATA_LOGGER
    )

def SEoST(show_op: bool=True) -> None:
    # Ethernet: ---------------------------------------------
    if ethernet.is_server_alive: # online mode
        event('Start sending data', 'INFO')
        if show_op: ethernet._show('StartSendingData', 'Send')
        buzzer.play(11, speed=50)
        while len(STACK) > 0:
            for sensor_id, data in stack_manage(STACK, method='pop').items(): send_payload(sensor_id, data)
        try:
            file = sd_card.read(name=DATA_LOGGER)
            while True: # if SD Card had log file
                try: data: str = next(file)
                except StopIteration:
                    try: sd_card.close_file(DATA_LOGGER)
                    finally: break
                else:
                    ethernet.tx_udp(data)
                    ethernet.rx_udp()
        except OSError: pass 
    # SD Card: ---------------------------------------------
    else: # offline mode
        try:
            event('Start storing data', 'INFO')
            if show_op: sd_card._show('StartStoringData', 'Store')
            buzzer.play(12, speed=50)
            while len(STACK) > 0:
                for sensor_id, data in stack_manage(STACK, method='pop').items(): store_payload(sensor_id, data)
        except OSError: pass

def cool_down_after_attack() -> None:
    ethernet.tx_udp(payload.format('log', 'critical', 'n/a', 'DOS Attack!'))
    buzzer.play(20, speed=50, volume=60000)
    ethernet.cool_down(timer=COOL_DOWN_PERIOD, msg='UnderDOSAttack', op='CoolDown')
    lcd.loading_demo(speed=0.05, demo=2); sleep(1)
    rfid.refresh(); sleep(1)
    ethernet.refresh(); sleep(1)
    lcd.refresh(); sleep(1)
    ethernet.tx_udp(payload.format('log', 'info', 'n/a','Hi I refresh myself!'))
    lcd.LCD_show('LoadingComplete', 'refresh')
    buzzer.play(2, speed=50)
    collect() # free up memory space

def stack_manage(stack: list, sensor_id: str='n/a', data: tuple=(None, None), method='push') -> dict:
    if method == 'push':
        if None not in data:
            status: str = ' '.join(data).strip(' ')
            if set_priority(sensor_id, status) in ('WARNING', 'ERROR', 'CRITICAL'):
                if ethernet.is_server_alive: send_payload(sensor_id, status)
                else: stack.append({sensor_id: status})
            else: stack.append({sensor_id: status})
        else: pass
    elif method == 'pop': return stack.pop()
    else: raise Exception('method should be [push] or [pop]')

def shutdown() -> None:
    ethernet.tx_udp(payload.format('log', 'WARNING', 'n/a', 'pico_status: shutdown'))
    ethernet._keep_alive_server = DEAD
    SEoST(show_op=False)
    event('Shutdown system', 'INFO')
    buzzer.play(20, speed=100, volume=60000)
    lcd.LCD_show('ShutdownSystem', 'Shut')
    exit()

tasks: dict = {
    1: ethernet.recent_stat,
    2: ethernet.reconnect,
    3: SEoST,
    4: ethernet.date_and_time,
    5: door.recent_stat,
    6: vibrate.recent_stat,
    7: move.recent_stat,
    8: gas.recent_stat,
    9: gas.recent_density,
    10: temp_and_humid.recent_temperature,
    11: temp_and_humid.recent_humidity,
    12: fire.recent_stat,
    13: fan.recent_stat,
    14: sd_card.mount_sd,
    15: sd_card.umount_sd,
    16: shutdown
}

# ----------------------------- Start ----------------------------- #
def main() -> None:
    """Main function to drive all sensors"""
    relay.channel_1, relay.channel_2 = ACTIVE, ACTIVE # Door, Fan
    sleep(0.05); relay.channel_1 = INACTIVE # Door
    lcd.LCD_clear()
    lcd.LCD_show("MixTape Tech", 'Loading')
    lcd.loading_demo(speed=0.02, demo=1)
    buzzer.play(1, speed=30); sleep(0.5)

    for _ in range(0, KEEP_ALIVE // 10):
        ethernet.send_request(which='alive', waiting_for=2)
        if ethernet.is_server_alive: ethernet.tx_udp(f"id>>{DEVICE_ID}"); break
    ethernet.send_request(which='ntp') # request localtime
    ethernet.date_and_time()

    start: int = time()
    threshold: int = 0

    while True:
        if ethernet.kill_switch_stat:
            # Ready for ARP, ICMP, IP, UDP, ... ---------------------------------------------
            ethernet.rx_udp()
            # RFID: ---------------------------------------------
            # stack_manage(STACK, sensor_id=RFID_RW, data=rfid.operation(op=R), method='push')
            read = rfid.operation()
            if read is not None:
                if ethernet.send_request(which='auth', data=payload.format('auth', 'INFO', '05', f"rfid_status: {read}").strip('\n')):
                    # open the door
                    lcd.LCD_show('DoorWillOpen', 'Auth')
                    event('Door will open')
                    relay.channel_1 = ACTIVE
                    sleep(OFFSET_TIME * 4)
                    relay.channel_1 = INACTIVE
                else:
                    lcd.LCD_show('DoorWillNotOpen', 'Auth')
                    event('Door will not open', priority='WARNING')
                    relay.channel_1 = INACTIVE
            # rfid.operation(op=W, data_to_write=choice(("d9ol6mu3e8kvsgbr", "17tv0243qaj9nzme", "8a1lswxd2gek7r04")))
            # KEYPAD: ---------------------------------------------
            keypad.do_task(tasks)
            # DOOR: ---------------------------------------------
            stack_manage(STACK, sensor_id=DOOR, data=(door.status(),), method='push')
             # VIBRATE: ---------------------------------------------
            stack_manage(STACK, sensor_id=VIBRATE, data=(vibrate.status(),), method='push')
            # MOVE: ---------------------------------------------
            stack_manage(STACK, sensor_id=MOVE, data=(move.status(),), method='push')
            # GAS: ---------------------------------------------
            gS, gD = gas.status()
            stack_manage(STACK, sensor_id=GAS, data=(gS, gD), method='push')
            # Temp&humid: ---------------------------------------------
            t, h = temp_and_humid.status()
            stack_manage(STACK, sensor_id=TEMPERATURE, data=(t,), method='push')
            stack_manage(STACK, sensor_id=HUMIDITY, data=(h,), method='push')
            # Fan: ---------------------------------------------
            fan.speed = int(temp_and_humid._am2302.temperature)
            stack_manage(STACK, sensor_id=FAN, data=(fan.status(),), method='push')
            # FIRE: ---------------------------------------------
            stack_manage(STACK, sensor_id=FIRE, data=(fire.status(),), method='push')
            # Threshold: ---------------------------------------------
            threshold = time() - start
            # event(f"Threshold is {threshold}", log_it=False)
            # event(f"Server is {'Alive' if ethernet.is_server_alive else 'Dead'}", log_it=False)
            # event(f"UDP_Q={ethernet.q_stat}", log_it=False)
            # event(f"STACK={STACK}", log_it=False)
            # Update Clock: ---------------------------------------------
            if UPDATE_CLOCK_PERIOD_1 - 1 <= threshold < UPDATE_CLOCK_PERIOD_1 + OFFSET_TIME or \
               UPDATE_CLOCK_PERIOD_2 - 1 <= threshold < UPDATE_CLOCK_PERIOD_2 + OFFSET_TIME:
                ethernet.send_request(which='ntp')
                ethernet.date_and_time()
            # Keep alive: ---------------------------------------------
            if KEEP_ALIVE - 1 <= threshold < KEEP_ALIVE + OFFSET_TIME:
                ethernet.send_request(which='alive', waiting_for=3)
                ethernet.tx_udp(f"id>>{DEVICE_ID}")
            # Link: ---------------------------------------------
            if SEND_OR_STORE_PERIOD - 1 <= threshold < SEND_OR_STORE_PERIOD + OFFSET_TIME:
                SEoST()
            # Clear cache: ---------------------------------------------
            if CLEAR_PERIOD - 1 <= threshold < CLEAR_PERIOD + OFFSET_TIME:
                event(ethernet.protection_stat)
                logger.event_registrar('Ethernet', 'INFO', ethernet.protection_stat)
                ethernet.cool_down(timer=0, msg='ClearCache', op='Clear')
            # Check SD: ---------------------------------------------
            if CHECK_SD - 1 <= threshold < CHECK_SD + OFFSET_TIME:
                if not sd_card.is_mounted: sd_card.mount_sd()
            # Fresh Connection: ---------------------------------------------
            if RECONNECT_PERIOD - 1 <= threshold < RECONNECT_PERIOD + OFFSET_TIME:
                ethernet.refresh()
                ethernet.reconnect(req=False)
            # Break threshold: ---------------------------------------------
            if RECONNECT_PERIOD <= threshold:
                start = time()

            # Process ACK: ---------------------------------------------
            if ethernet.is_server_alive:
                msg: str = ethernet.parse_udp()
                if msg == 'door': send_payload('00', door._recent)
                elif msg == 'vibrate': send_payload('01', vibrate._recent)
                elif msg == 'temp':
                    temp_and_humid._counter = L_TH
                    send_payload('02', temp_and_humid.status()[0])
                elif msg == 'humid':
                    temp_and_humid._counter = L_TH
                    send_payload('03', temp_and_humid.status()[1])
                elif msg == 'fan':
                    fan._counter = L_FAN
                    send_payload('04', fan.status())
                elif msg == 'gas':
                    gas._counter = L_GAS
                    gS, gD = gas.status()
                    send_payload('06', f"{gS} {gD}")
                elif msg == 'move':
                    move._counter = L_MOVE
                    send_payload('07', move.status())
                elif msg == 'fire': send_payload('08', fire._recent)
                else: pass
            # Cycle Speed: ---------------------------------------------
            sleep(DELAY); collect() # free up memory space
            # print(gas._counter, temp_and_humid._counter, move._counter, fan._counter)
        else: # Under Attack
            event('Pico Under Attack! CoolDown ...', priority='CRITICAL')
            cool_down_after_attack()
            start = time()

if __name__ == '__main__':
    main()
