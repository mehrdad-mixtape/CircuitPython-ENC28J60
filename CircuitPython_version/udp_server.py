#!/usr/bin/env python
# -*- coding: utf8 -*-

#  GPLv3 License

# Copyright (c) 2022 mehrdad
# Developed by mehrdad-mixtape https://github.com/mehrdad-mixtape/CircuitPython-ENC28J60

# Python 3.5 or higher

from os import kill, getpid
from signal import SIGTERM
from socket import socket, AF_INET, SOCK_DGRAM
from time import localtime
from subprocess import run
from platform import system

pid: int = getpid()

def get_date() -> tuple:
    """get localtime of server"""
    Y, M, D, HH, MM, *_ = localtime()
    return (Y, M, D, HH, MM)

class UDP_server:
    """UDP server"""
    def __init__(self, IP: str='0.0.0.0', PORT: int=5000, BUFFER: int=2048, ACK: bool=False):
        self._IP: str = IP
        self._PORT: int = PORT
        self._ACK: bool = ACK
        self._BUFFER: int = BUFFER
        self._udp_socket = socket(family=AF_INET, type=SOCK_DGRAM)

    def __str__(self) -> str:
        return f"""
        {UDP_server.__doc__}
        Running on: {self._IP}:{self._PORT}
        Version: {UDP_server.__version__()}
        Default IP address: 0.0.0.0
        Default PORT number: 5000
        Buffer size: {self._BUFFER} bytes
        Press Ctrl + C to shutdown server"""

    @staticmethod
    def __version__() -> str:
        __version__ = 'v1.1.0'
        return __version__

    @property
    def get_ip_port(self) -> tuple:
        return (self._IP, self._PORT)

    def send_msg(self, msg: str, dst_addr: str='', dev_id: str='') -> bool:
        try:
            byte_msg: bytes = msg.encode('utf-8')
            if dst_addr: self._udp_socket.sendto(byte_msg, dst_addr)
            elif dev_id: self._udp_socket.sendto(byte_msg, self.clients.get(dev_id, ('0.0.0.0', 65000)))
            return True
        except Exception as E:
            print(f"UDP_SERVER: WARNING > send_msg method has problem: {E}")
            return False

    def _parser(self, packet: tuple) -> tuple:
        """Payload parser"""
        payload, dst_addr = packet
        if '>>' in payload:
            operation, content = payload.split('>>')
            if operation == 'req':
                if content == 'time':
                    clock: str = ':'.join(map(str, get_date()[3:])).strip(':')
                    date: str = '/'.join(map(str, get_date()[0:3])).strip('/')
                    return (operation, content, f"time>>{date} {clock}")
                elif content == 'alive':
                    return (operation, content, 'alive>>yes')
                elif operation == 'id':
                    print(f"UDP_SERVER: INFO > device {content} connected to server")
                else: return ('Failed', content)
            elif operation == 'msg':
                return (operation, content, 'ack>>ok')
            else:
                return (operation, content, 'ack>>ok')
        else:
            return ('n/a', payload, 'ack>>ok')

    def recv_msg(self) -> tuple:
        try:
            payload: tuple = self._udp_socket.recvfrom(self._BUFFER)
            msg, dst_addr = payload
            result: tuple = self._parser((msg.decode('utf-8'), dst_addr))
            return (result, dst_addr)
        except Exception as E:
            print(f"UDP_SERVER: WARNING > recv_msg method has problem: {E}")
            return (('Failed', 'Failed'), 'Empty')

    def _connection_handler(self) -> None:
        while True:
            payload, dst_addr = self.recv_msg()
            if payload == 'Failed' or 'Failed' in payload:
                print(f"UDP_SERVER: WARNING > _connection_handler method received content {payload[1]} from {dst_addr}")
                continue
            if self._ACK:
                if self.send_msg(payload[2], dst_addr=dst_addr):
                    print(f"UDP_SERVER: INFO > receive {payload[0]}>>{payload[1]} from {dst_addr}")
                    print(f"UDP_SERVER: INFO > send {payload[2]} to {dst_addr}")
            else: continue

    def run_udp_server(self) -> None:
        try: self._udp_socket.bind((self._IP, self._PORT))
        except Exception as E:
            print(f"UDP_SERVER: ERROR > server has problem on ({self._IP}:{self._PORT}) {E}")
            kill(pid, SIGTERM)
        else:
            print(self.__str__())
            print(f"UDP_SERVER: DEBUG > server is running on ({self._IP}:{self._PORT})")
            self._connection_handler()

def main(*args, **kwargs) -> None:
    udp_server: UDP_server = UDP_server(
        IP=args[0], 
        PORT=kwargs.get('port', 5000), 
        ACK=kwargs.get('ack', True)
    )

    udp_server.run_udp_server()

if __name__ == '__main__':
    try:
        main('192.168.1.200', port=5000, ack=True)
    except KeyboardInterrupt:
        if system() == 'Windows': run(['cls'])
        elif system() == 'Linux': run(['clear'])
        kill(pid, SIGTERM)
