#!/usr/bin/env python
# -*- coding: utf8 -*-

#  GPLv3 License

# Copyright (c) 2022 mehrdad
# Developed by mehrdad-mixtape https://github.com/mehrdad-mixtape/CircuitPython-ENC28J60

# This is version for circuitpython 7.2 or higher

# This file implements protection methods.
# Supports:
# - DoS protection (ARP, ICMP, TCP, UDP) flood

__version__ = '0.1.1v'
__repo__ = 'https://github.com/mehrdad-mixtape/CircuitPython-ENC28J60'

class DOS: # pico could be down after 00:58.19s under dos attack. 2971242 udp packet!
    def __init__(self, ARP_Limit: int=50, ICMP_Limit: int=100, TCP_Limit: int=200, UDP_Limit: int=200):
        # Flags:
        self._arp_flag: bool = True
        self._icmp_flag: bool = True
        self._udp_flag: bool = True
        self._tcp_flag: bool = True

        # WARNING:
        self._arp_w: int = 0
        self._arp_limit: int = ARP_Limit
        self._icmp_w: int = 0
        self._icmp_limit: int = ICMP_Limit
        self._tcp_w: int = 0
        self._tcp_limit: int = TCP_Limit
        self._udp_w: int = 0
        self._udp_limit: int = UDP_Limit
    @property
    def flag_state(self) -> bool:
        return self._arp_flag and self._icmp_flag and self._udp_flag and self._tcp_flag
    @property
    def check_warning(self) -> str:
        return f"""
    ARP: {self._arp_flag} {self._arp_w}/{self._arp_limit}
    ICMP: {self._icmp_flag} {self._icmp_w}/{self._icmp_limit}
    UDP: {self._udp_flag} {self._udp_w}/{self._tcp_limit}
    TCP: {self._tcp_flag} {self._tcp_w}/{self._udp_limit}"""
    def check_arp_limit(self) -> None: # Avoid ARP flood Attack
        if self._arp_w >= self._arp_limit: self._arp_flag = False # ARP request after this will not process, mehrdad-mixtape
        else: self._arp_w += 1
    def check_icmp_limit(self) -> None: # Avoid ICMP flood Attack
        if self._icmp_w >= self._icmp_limit: self._icmp_flag = False # ICMP request after this will not process, mehrdad-mixtape
        else: self._icmp_w += 1
    def check_tcp_limit(self) -> None: # Avoid TCP flood Attack
        if self._tcp_w >= self._tcp_limit: self._tcp_flag = False # TCP packet after this will not process, mehrdad-mixtape
        else: self._tcp_w += 1
    def check_udp_limit(self) -> None: # Avoid UDP flood Attack
        if self._udp_w >= self._udp_limit: self._udp_flag = False  # UDP packet after this will not process, mehrdad-mixtape
        else: self._udp_w += 1
    def reset_flag_state(self) -> None:
        self._arp_flag: bool = True
        self._icmp_flag: bool = True
        self._udp_flag: bool = True
        self._tcp_flag: bool = True
        self._arp_w: int = 0
        self._icmp_w: int = 0
        self._tcp_w: int = 0
        self._udp_w: int = 0
