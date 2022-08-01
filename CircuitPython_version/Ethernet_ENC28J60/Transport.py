#!/usr/bin/env python
# -*- coding: utf8 -*-

#  MIT License

# Copyright (c) 2022 mehrdad
# Developed by mehrdad-mixtape https://github.com/mehrdad-mixtape

# This is version for circuitpython 7.2

# This file implements very simple Transport protocol.
# Supports:
# - UDPv4: rx and tx

from micropython import const
from time import sleep, mktime, localtime
import Network

__version__ = '1.2.8v'
__repo__ = 'https://github.com/mehrdad-mixtape'

# Status:
IDLE: int = const(0)
CONNECTING: int = const(1)
CONNECTED: int = const(2)
ERROR: int = const(3)

# Sending method:
UNICAST: str = 'U'
BROADCAST: str = 'B'

# Switch:
ON: bool = False
OFF: bool = True

# Stat:
ALIVE: bool = True
DEAD: bool = False

# Functions:

# Classes:
class UDP:
    """This class handle UDP packet, It can send or receive udp packets"""
    def __init__(self, spi, cs,
    src_addr: list, sub_net: list,
    tgt_addr: list, tgt_port: int,
    gateway_addr: list,
    src_port: int=10000, # source port for packets, cannot be letter than 1024!
    dos_conf: tuple=(50, 100, 200, 200), # ARP, ICMP, TCP, UDP limit to check dos attack
    ttc: int=10, # try to connect = ttc
    lcd=None, # add lcd16x2 to show status of functions
    buzzer=None,
    logger=None): # add buzzer to hear of functions
        # LCD:
        self._lcd = lcd
        # Buzzer:
        self._buzzer = buzzer
        # Logger:
        self._logger = logger
        # Target host:
        self._tgt_addr: bytes = bytes(tgt_addr)
        self._tgt_port: int = tgt_port
        # Source host:
        self._src_addr: list = src_addr
        self._src_port: int = src_port
        # Network config:
        self._network = Network.Network(spi, cs, dos_conf, logger=logger)
        self._network.setIPv4(src_addr, sub_net, gateway_addr)
        # Functional config:
        self._ttc: int = ttc
        self._kill_switch: bool = OFF
        self._stat: int = IDLE
        self._time: int = 0
        self._keep_alive_server: bool = False
    @property
    def kill_switch_stat(self) -> bool:
        return self._kill_switch
    @property
    def is_server_alive(self) -> bool:
        return self._keep_alive_server
    @property
    def q_stat(self) -> list:
        return self._network.UDP_Q
    @property
    def protection_stat(self) -> str:
        return self._network.dos.check_warning
    @property
    def is_link(self) -> int:
        return self._stat
    @is_link.setter
    def is_link(self, stat: int) -> None:
        self._stat = stat
    def event(self, priority: str, msg: str) -> None:
        try: self._logger.event_registrar('Transport', priority, msg)
        except AttributeError: pass
        finally: print(f"Transport: {msg}")
    def _show(self, data: str, op: str) -> None:
        try:
            self._lcd.LCD_clear()
            self._lcd.LCD_put_str(f"Eth: op={op}")
            self._lcd.LCD_move_to(0, 1)
            self._lcd.LCD_put_str(data)
            sleep(0.5)
        except AttributeError: self.event('WARNING', 'There is not lcd to show')
    def _beep(self, beep_number: int) -> None:
        try:
            self._buzzer.play(beep_number, speed=50)
        except AttributeError: self.event('WARNING', 'There is not buzzer to beep!')
    def _send_udp4_unicast(self, payload: str) -> int:
        """Unicast method to sending payload"""
        msg: list = []
        encoded_payload: bytes = payload.encode()

        if self._network.isLocalIp4(self._tgt_addr):
            tgtMac = self._network.getArpEntry(self._tgt_addr)
        else:
            tgtMac = self._network.getArpEntry(self._network.gwIp4Addr)

        if tgtMac is None:
            self.event('ERROR', f"{self._tgt_addr[0]}.{self._tgt_addr[1]}.{self._tgt_addr[2]}.{self._tgt_addr[3]} not in ARP table!")
            return -1

        if self._network.ip4TxCount == 255: self._network.ip4TxCount = 0
        msg.append(tgtMac)
        msg.append(self._network.myMacAddr)
        msg.append(bytearray([Network.ETH_TYPE_IP4 >> 8, Network.ETH_TYPE_IP4_S]))
        msg.append(Network.makeIp4Hdr(
            self._network.myIp4Addr,
            self._tgt_addr,
            self._network.ip4TxCount,
            Network.IP4_TYPE_UDP,
            8 + len(encoded_payload)))
        self._network.ip4TxCount += 1
        msg.append(Network.makeUdp4Hdr(
            self._network.myIp4Addr,
            self._src_port,
            self._tgt_addr,
            self._tgt_port,
            encoded_payload))
        msg.append(encoded_payload)
        result: int = self._network.txPkt(msg)
        return result
    def _send_udp4_broadcast(self, payload: str, src_ip4_addr=None) -> int:
        """Broadcast method to sending payload"""
        msg: list = []
        encoded_payload: bytes = payload.encode()

        tgt_ip4Addr: bytearray = Network.IP4_ADDR_BCAST

        if src_ip4_addr is None:
            src_ip4_addr = Network.IP4_ADDR_ZERO

        msg.append(bytearray([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]))
        msg.append(self._network.myMacAddr)
        msg.append(bytearray([Network.ETH_TYPE_IP4 >> 8, Network.ETH_TYPE_IP4_S]))
        msg.append(Network.makeIp4Hdr(
            src_ip4_addr,
            tgt_ip4Addr,
            self._network.ip4TxCount,
            Network.IP4_TYPE_UDP,
            8 + len(encoded_payload)))
        self._network.ip4TxCount += 1
        msg.append(Network.makeUdp4Hdr(
            src_ip4_addr,
            self._src_port,
            self._tgt_addr,
            self._tgt_port,
            encoded_payload))
        msg.append(encoded_payload)
        result: int = self._network.txPkt(msg)
        return result
    def _try_to_connect(self) -> None:
        """try to connect to the UDP-server"""
        while self.is_link != CONNECTED:
            self._ttc -= 1
            self._network.rxAllPkt()
            if self._ttc > 0:
                # State - IDLE
                if self.is_link == IDLE:
                    if not self._network.isIPv4Configured:
                        self.event('ERROR', 'Error IP configuration')
                        sleep(0.5) # that was so important delay!!!
                        self._show('ErrorIpConfig', 'Try')
                        self.is_link = ERROR
                        break
                    else:
                        self.event('DEBUG', 'Try to connecting')
                        sleep(0.5) # that was so important delay!!!
                        self._show('TryToConnecting', 'Try')
                        self._network.connectIp4(self._tgt_addr)
                        self.is_link = CONNECTING
                        self._ttc += 1
                # State - CONNECTING
                elif self.is_link == CONNECTING:
                    if self._network.isConnectedIp4(self._tgt_addr):
                        self.event('INFO', 'Ip is connected')
                        sleep(0.5) # that was so important delay!!!
                        self._show('IpIsConnected', 'Try')
                        self._beep(2)
                        self.is_link = CONNECTED
                        self._ttc += 1
                        break
                    else:
                        self.event('WARNING', 'Ip is not connected')
                        sleep(0.5) # that was so important delay!!!
                        self._show('IpIsNotConnected', 'Try')
                        self._network.connectIp4(self._tgt_addr)
                        self.is_link = CONNECTING
                        self._ttc -= 2
            else:
                self.is_link = IDLE
                self.event('WARNING', 'Connection failed')
                sleep(0.5) # that was so important delay!!!
                self._show('ConnectionFailed', 'Try')
                self._ttc = 10
                break
    def send_request(self, which: str='ntp', **kwargs) -> bool:
        """
        Manage to send requests to server
        if:
            which='ntp': Trying to update date&clock
            which='alive': Trying to find out if the server is online or not
                **kwargs >> waiting_for: int
                         >> data: str
            ...
        """
        if which == 'ntp': # get clock from software side, same as ntp
            self.tx_udp('req>>time')
            return True
        elif which == 'alive':
            self.tx_udp('req>>alive')
            self._beep(7)
            self._show('CheckConnection', 'Check')
            try: sleep(kwargs['waiting_for'] if kwargs['waiting_for'] <= 10 else 10)
            except (KeyError, TypeError): sleep(5)
            finally:
                self.rx_udp()
                if self.parse_udp():
                    self._show('ServerIsAlive', 'Check')
                    self.event('INFO', 'Server is Alive')
                    self._beep(8)
                    self._keep_alive_server = ALIVE
                    return True
                else:
                    self._show('ServerIsNotAlive', 'Check')
                    self.event('WARNING', 'Server is Dead')
                    self._beep(9)
                    self._keep_alive_server = DEAD
                    return False
        elif which == 'auth':
            self.tx_udp(kwargs['data'])
            self._beep(7)
            self._show('WaitForAuth', 'Auth')
            try: sleep(kwargs['waiting_for'] if kwargs['waiting_for'] <= 10 else 10)
            except (KeyError, TypeError): sleep(5)
            finally:
                self.rx_udp()
                if self.parse_udp():
                    self._show('AuthSuccessful', 'Auth')
                    self.event('INFO', 'Authentication successful')
                    self._beep(17)
                    return True
                else:
                    self._show('AuthFailed', 'Auth')
                    self.event('INFO', 'Authentication failed')
                    self._beep(18)
                    return False
        else: pass
    def date_and_time(self, event: bool=True) -> tuple:
        try:
            time = localtime(self._time)
            y: int = time[0]
            m: int = time[1]
            d: int = time[2]
            H: int = time[3]
            M: int = time[4] + 1
            if event:
                self._show(f"DateIs {y}/{m}/{d}", 'Date')
                print(f"Ethernet: Date is {y}/{m}/{d}")
                self._show(f"ClockIs {H}:{M}", 'Clock')
                print(f"Ethernet: Clock is {H}:{M}")
            return (y, m, d, H, M)
        except (OverflowError, IndexError):
            if event: self.event('WARNING', 'Date & Clock are not update')
            return (0, 0, 0, 0, 0)
    def parse_udp(self) -> bool:
        result: bool = False
        if not self._network.isEmptyUdpQ:
            payload: str = self._network.UDP_Q.pop()
            try:
                operation, content = payload.split('>>')
                if operation == 'time':
                    date, clock = content.split(' ')
                    Y, M, D = date.split('/')
                    HH, MM = clock.split(':')
                    self._time = mktime((int(Y), int(M), int(D), int(HH), int(MM), 0, 0, 0, 0))
                    result = True
                elif operation == 'alive':
                    self._keep_alive_server = ALIVE
                    result = True
                elif operation == 'ack':
                    result = True
                elif operation == 'auth':
                    if content == 'success': result = True
                    else: result = False # content = 'fail'
                elif operation == 'cmd':
                    result = content
                else:
                    result = False
            except ValueError:
                result = False
        return result
    def tx_udp(self, payload: str, method: str=UNICAST) -> None:
        """Send udp payloads to server"""
        if self.is_link != CONNECTED:
            self._try_to_connect()
        else:
            if method == UNICAST:
                if self.is_link == CONNECTED:
                    what_is_happen: int = self._send_udp4_unicast(payload)
                    if what_is_happen < 0:
                        self.event('ERROR', f"Fail to send data error={what_is_happen}")
                        self._show(f"FailToSendErr:{what_is_happen}", 'Send')
                        self.is_link = IDLE
                    else:
                        print('Ethernet: Data sent')
                        # self._show('DataSentSuccess', 'Send')
                else:
                    self.event('INFO', f"Stat is {'IDLE' if self.is_link == 0 else 'CONNECTING' if self.is_link == 1 else 'ERROR'}")
                    self._show(f"StatIs {'IDLE' if self.is_link == 0 else 'CONNECTING' if self.is_link == 1 else 'ERROR'}", 'Send')
                    self._beep(10)
            elif method == BROADCAST: pass
            else: pass
    def rx_udp(self) -> None:
        self._network.rxAllPkt()
        # self._show('DataRecvSuccess', 'Recv')
        # self.event('INFO', f"\n{self._network.dos.check_warning}")
        if not self._network.dos.flag_state:
            self._network.UDP_Q.clear()
            self._kill_switch = ON
    def cool_down(self, timer: int=60, msg: str='Loading...', op='Any') -> None:
        self._show(msg, op)
        self._beep(6)
        for _ in range(timer):
            self._show(f"Timer: {timer} s", op)
            sleep(0.5)
            print(f"Ethernet: Timer is {timer}s")
            self._beep(19)
            timer -= 1
        self._network.dos.reset_flag_state()
        self._kill_switch = OFF
    def reconnect(self, req: bool=True) -> None:
        self._network.arpTable.clear()
        self.is_link = IDLE
        self._try_to_connect()
        if req: self.send_request(which='alive', waiting_for=3)
    def refresh(self) -> None:
        self._network.nic.ENC28J60_Init()
        self._show('ResetEthernet', 'Reset')
        self.event('WARNING', 'Ethernet reset')
    def recent_stat(self) -> None:
        self._show(f"StatIs {'IDLE' if self.is_link == 0 else 'CONNECTING' if self.is_link == 1 else 'CONNECTED' if self.is_link == 2 else 'ERROR'}", 'Check')
        self._show(f"ServerIs {'Alive' if self.is_server_alive else 'Dead'}", 'Check')
