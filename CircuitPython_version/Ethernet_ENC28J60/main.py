#!/usr/bin/env python
# -*- coding: utf8 -*-

#  GPLv3 License

# Copyright (c) 2022 mehrdad
# Developed by mehrdad-mixtape https://github.com/mehrdad-mixtape/CircuitPython-ENC28J60

# This is version for circuitpython 7.2 or higher

# ----------------------------- Libraries and Modules ----------------------------- #
# builtin libs:
from gc import collect
from time import sleep, time
from random import choice
from conf import *

# external libs:
from Transport import UDP, DEAD

__version__ = '1.0.0v'
__repo__ = 'https://github.com/mehrdad-mixtape/CircuitPython-ENC28J60'

# ----------------------------- Device Initialization ----------------------------- #
## Initial Ethernet:
ethernet: UDP = UDP(spi_bus_1, cs_10, CLIENT_IP, SUB_NET, SERVER_IP, SERVER_PORT, GATEWAY,
src_port=CLIENT_PORT, dos_conf=DOS_CONFIG, ttc=10)

# ----------------------------- Start ----------------------------- #
def main() -> None:
    """Main function to drive all sensors"""
    for _ in range(0, 5):
        ethernet.send_request(which='alive', waiting_for=2)
        if ethernet.is_server_alive:
            ethernet.tx_packet(f"id>>I'm Pico"); break
    ethernet.send_request(which='ntp') # request localtime
    ethernet.date_and_time()

    start: int = time()
    threshold: int = 0

    while True:
        if ethernet.kill_switch_stat:
            # Ready for ARP, ICMP, IP, UDP, ... ---------------------------------------------
            ethernet.rx_packet()
            # Threshold: ---------------------------------------------
            threshold = time() - start
            print(f"Threshold is {threshold}")
            print(f"Server is {'Alive' if ethernet.is_server_alive else 'Dead'}")
            print(f"UDP_Q={ethernet.udp_q_stat}")
            ethernet.date_and_time()
            # Update Clock: ---------------------------------------------
            if threshold % 10 == 0: # send random udp packet
                ethernet.tx_packet(choice(['msg>>Hello Pico', 'MixTape', 'ENC28J60 with CircuitPython']))
            elif 59 <= threshold < 60: # update date and time
                ethernet.send_request(which='ntp')
            elif 79 <= threshold < 80: # check the connection and is server alive?
                ethernet.send_request(which='alive', waiting_for=3)
            elif 89 <= threshold < 90: # renew threshold and empty UDP_Q, ICMP_Q, ARP_Q, TCP_Q
                ethernet.cool_down(timer=0)
                start = time()
            if ethernet.is_server_alive:
                ethernet.parse_udp()
            # Cycle Speed: ---------------------------------------------
            sleep(1); collect() # free up memory space

        else: # Under Attack
            print('Pico Under Attack! CoolDown ...')
            ethernet.tx_packet('Critical DOS Attack!')
            ethernet.cool_down(timer=30, msg='UnderDOSAttack', op='CoolDown')
            collect() # free up memory space
            start = time()

if __name__ == '__main__':
    main()
