#!/usr/bin/env python
# -*- coding: utf8 -*-

#  GPLv3 License

# Copyright (c) 2022 mehrdad
# Developed by mehrdad-mixtape https://github.com/mehrdad-mixtape/CircuitPython-ENC28J60

# This is version for circuitpython 7.2 or higher

# This file implements very simple IP stack for ENC28J60 ethernet.
# Supports:
# - ARP for IPv4 over Ethernet, simple ARP table
# - IPv4 for not fragmented packets only, single static IP address
# - ICMPv4: rx Echo Request and tx Echo Response

from micropython import const
import ENC28J60
from Protection import DOS
import struct

__version__ = '0.4.0v'
__repo__ = 'https://github.com/mehrdad-mixtape/CircuitPython-ENC28J60'

ETH_TYPE_IP4 = const(0x0800)
ETH_TYPE_IP4_S = const(0x00)
ETH_TYPE_ARP = const(0x0806)
ETH_TYPE_ARP_S = const(0x06)
ETH_80211Q_TAG = const(0x8100)
ETH_80211Q_TAG_S = const(0x00)

ARP_HEADER_LEN = const(28)
ARP_OP_REQUEST = const(1)
ARP_OP_REPLY = const(2)

IP4_TYPE_ICMP = const(1)
IP4_TYPE_TCP = const(6)
IP4_TYPE_UDP = const(17)
IP4_ADDR_BCAST = bytearray([255, 255, 255, 255])
IP4_ADDR_ZERO = bytearray([0, 0, 0, 0])

ICMP4_ECHO_REPLY = const(0)
ICMP4_UNREACHABLE = const(3)
ICMP4_ECHO_REQUEST = const(8)

class Network:
    """This class handle network protcol: ARP, ICMP, IP, UDP, TCP"""
    def __init__(self, nicSpi, nicCsPin, dosConf: tuple):
        self.rxBuff = bytearray(ENC28J60.ENC28J60_ETH_RX_BUFFER_SIZE)
        self.nic = ENC28J60.ENC28J60(nicSpi, nicCsPin)

        # Eth settings:
        self.myMacAddr = self.nic.ENC28J60_GetMacAddr

        # IPv4 settings:
        self.myIp4Addr: bytearray
        self.netIp4Mask: bytearray
        self.gwIp4Addr: bytearray
        self.configIp4Done: bool = False

        # Stats
        self.ip4TxCount: int = 0
        self.ip4RxCount: int = 0

        self.arpTable = {}
        self.udp4UniBind = {} # {port:callback(Pkt)}
        self.udp4BcastBind = {} # {port:callback(Pkt)}

        # Queues: mehrdad-mixtape
        self.ARP_Q = []
        self.ICMP_Q = []
        self.UDP_Q = []

        # Protection: mehrdad-mixtape
        self.dos: DOS = DOS(
            ARP_Limit=dosConf[0],
            ICMP_Limit=dosConf[1],
            TCP_Limit=dosConf[2],
            UDP_Limit=dosConf[3])

        # Initialize ENC28J60:
        self.nic.ENC28J60_Init()
        self.event('MAC ADDR is {}'.format(':'.join("{:02x}".format(c) for c in self.myMacAddr)))
        if self.nic.ENC28J60_GetRevId != 0x06: # mehrdad-mixtape
            self.event("""ENC28J60 revision ID is not readable!
            Check the:
            1. physical connection
                - ethernet cable
                - spi wires
                - pin configuration. CS
                - power supply problem
            2. client and server should be in same network
            3. power-off and power-on the system""")
        else: self.event("ENC28J60 revision ID: 0x{:02x}".format(self.nic.ENC28J60_GetRevId))
    def setIPv4(self, myIp4Addr: list, netIp4Mask: list, gwIp4Addr: list) -> None:
        self.myIp4Addr = bytearray(myIp4Addr)
        self.netIp4Mask = bytearray(netIp4Mask)
        self.gwIp4Addr = bytearray(gwIp4Addr)
        self.configIp4Done = True
    @property
    def isIPv4Configured(self) -> bool:
        return self.configIp4Done
    @property
    def isEmptyUdpQ(self) -> bool:
        if len(self.UDP_Q) == 0: return True
        else: return False
    def event(self, msg: str) -> None:
        print(f"Network: {msg}")
    def rxAllPkt(self) -> None:
        '''Function to rx and process all pending packets from NIC'''
        while True:
            if self.dos.flag_state: # dos protection
                ## lock
                rxPacketCnt = self.nic.ENC28J60_GetRxPacketCnt()
                if rxPacketCnt == 0:
                    ## unlock
                    break
                rxLen = self.nic.ENC28J60_ReceivePacket(self.rxBuff)
                ## unlock
                if rxLen <= 0:
                    self.event(f"Rx ERROR {rxLen}")
                    continue
                procEth(Packet(self, self.rxBuff, rxLen))
            else:
                break
    def txPkt(self, msg: list) -> int:
        '''Function to tx packet to NIC'''
        ## lock
        n = self.nic.ENC28J60_SendPacket(msg)
        ## unlock
        return n
    def registerUdp4Callback(self, port: int, cb) -> None:
        if cb is not None:
            self.udp4UniBind[port] = cb
        else:
            self.udp4UniBind.pop(port, None) # type: ignore
    def registerUdp4BcastCallback(self, port: int, cb) -> None:
        if cb is not None:
            self.udp4BcastBind[port] = cb
        else:
            self.udp4BcastBind.pop(port, None) # type: ignore
    def addArpEntry(self, ip: int | bytes, mac: bytes) -> None:
        if isinstance(ip, int):
            self.arpTable[ip] = bytearray(mac)
        else:
            self.arpTable[struct.unpack('!I',ip)[0]] = bytearray(mac)
    def getArpEntry(self, ip: int | bytes) -> None:
        if not isinstance(ip, int):
            ip = struct.unpack('!I',ip)[0]

        if ip in self.arpTable:
            return self.arpTable[ip]
        else:
            return None
    def sendArpRequest(self, ip4Addr: bytes) -> int:
        msg = makeArpRequest(self.myMacAddr, self.myIp4Addr, ip4Addr)
        n = self.txPkt(msg)
        return n
    def isLocalIp4(self, ip4Addr: bytes) -> bool:
        for i in range(4):
            if (ip4Addr[i] & self.netIp4Mask[i]) != (self.myIp4Addr[i] & self.netIp4Mask[i]):
                return False
        return True
    def connectIp4(self, ip4Addr: bytes) -> None:
        if self.isLocalIp4(ip4Addr):
            self.sendArpRequest(ip4Addr)
        elif False == self.isConnectedIp4(self.gwIp4Addr):
            self.sendArpRequest(self.gwIp4Addr)
    def isConnectedIp4(self, ip4Addr: bytes) -> bool:
        if self.isLocalIp4(ip4Addr):
            return self.getArpEntry(ip4Addr) is not None
        else:
            return self.getArpEntry(self.gwIp4Addr) is not None
class Packet:
    """This class stores received packet information"""
    def __init__(self, ntw: Network, frame: bytearray, frame_len: int):
        self.ntw: Network = ntw
        self.frame: memoryview = memoryview(frame)
        self.frame_len: int = frame_len

def makeArpReply(eth_dst: bytearray, eth_src: bytearray, ip_src: bytearray, ip_dst: bytes) -> list:
    rsp = []
    rsp.append(eth_dst)
    rsp.append(eth_src)
    rsp.append(bytearray([ETH_TYPE_ARP >> 8, ETH_TYPE_ARP_S, 0, 1, 8, 0, 6, 4, 0, ARP_OP_REPLY]))
    rsp.append(eth_src)
    rsp.append(ip_src)
    rsp.append(eth_dst)
    rsp.append(ip_dst)
    return rsp

def makeArpRequest(eth_src: bytearray, ip_src: bytearray, ip_dst: bytes) -> list:
    rsp = []
    rsp.append(bytearray([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]))
    rsp.append(eth_src)
    rsp.append(bytearray([ETH_TYPE_ARP >> 8, ETH_TYPE_ARP_S, 0, 1, 8, 0, 6, 4, 0, ARP_OP_REQUEST]))
    rsp.append(eth_src)
    rsp.append(ip_src)
    rsp.append(bytearray(6))
    rsp.append(ip_dst)
    return rsp

def procArp(pkt: Packet) -> None:
    pkt.ntw.dos.check_arp_limit() # ARP flood protection
    hrtype, prtype, hrlen, prlen, oper, sha, spa, tha, tpa = struct.unpack_from("!HHBBH6s4s6s4s", pkt.frame, pkt.eth_offset) # type: ignore
    pkt.ntw.event(f"Rx ARP oper={oper}")
    if ARP_OP_REQUEST == oper:
        if tpa == pkt.ntw.myIp4Addr:
            pkt.ntw.event(f"Rx ARP_REQUEST for my IP from IP {spa[0]}.{spa[1]}.{spa[2]}.{spa[3]}!")
            reply = makeArpReply(pkt.eth_src, pkt.ntw.myMacAddr, pkt.ntw.myIp4Addr, spa)
            n = pkt.ntw.txPkt(reply)
            if n < 0:
                pkt.ntw.event(f"Fail to send ARP REPLY {n}")

    elif ARP_OP_REPLY == oper:
        pkt.ntw.event(f"ARP {spa[0]}.{spa[1]}.{spa[2]}.{spa[3]} is at {sha[0]:02X}:{sha[1]:02X}:{sha[2]:02X}:{sha[3]:02X}:{sha[4]:02X}:{sha[5]:02X}")
        pkt.ntw.addArpEntry(spa, sha)

def makeIp4Hdr(src: bytearray, tgt: bytes, ident: int, proto: int, dataLen: int, ttl=128, dscp=0, ecn=0) -> bytearray:
    totlen = 20 + dataLen
    hdr = bytearray(20)
    hdr[0] = 0x45   # Version + IHL
    hdr[1] = (dscp << 2) | (ecn & 0x03)
    hdr[2] = totlen >> 8
    hdr[3] = totlen
    hdr[4] = ident >> 8
    hdr[5] = ident
    hdr[6] = 0      # Flags + Fragment Offset
    hdr[7] = 0      # Flags + Fragment Offset
    hdr[8] = ttl
    hdr[9] = proto
    hdr[10] = 0
    hdr[11] = 0
    hdr[12:16] = src
    hdr[16:20] = tgt

    chksm = calcChecksum(hdr)
    hdr[10] = (chksm >> 8) & 0xFF
    hdr[11] = chksm & 0xFF
    return hdr

def procIp4(pkt: Packet) -> None:
    ip_ver_len, _, pkt.ip_totlen, _, ip_flags_fragoffset, ip_ttl, pkt.ip_proto, ip_hdr_chksum, pkt.ip_src_addr, pkt.ip_dst_addr = struct.unpack_from("!BBHHHBBH4s4s", pkt.frame, pkt.eth_offset)  # type: ignore

    pkt.ip_ver = (ip_ver_len >> 4) & 0xF
    pkt.ip_hdrlen = (ip_ver_len & 0xF) << 2
    pkt.ip_offset = pkt.eth_offset + pkt.ip_hdrlen
    pkt.ip_maxoffset = pkt.eth_offset + pkt.ip_totlen

    # pkt.ntw.ip4RxCount += 1 # 

    if pkt.ip_ver != 4:
        pkt.ntw.event(f"ip_ver={pkt.ip_ver} not supported!")

    if pkt.ip_hdrlen != 20:
        pkt.ntw.event(f"ip_hdrlen={pkt.ip_hdrlen} not supported!")

    flags_mf = (ip_flags_fragoffset >> 13) & 0x01
    fragOffset = (ip_flags_fragoffset & 0x1FFF) << 3
    if (0 != flags_mf) or (0 != fragOffset):
        pkt.ntw.event(f"Fragmented IPv4 not supported: fragOffset={fragOffset}, flags_mf={flags_mf}")

    if pkt.ip_dst_addr == pkt.ntw.myIp4Addr:
        pkt.ntw.event(f"Rx my IP proto={pkt.ip_proto}")
        if pkt.ip_proto == IP4_TYPE_ICMP:
            procIcmp4(pkt)
        elif pkt.ip_proto == IP4_TYPE_UDP:
            procUdp4(pkt, bcast=False)
        elif pkt.ip_proto == IP4_TYPE_TCP:
            procTcp4(pkt)

    elif pkt.ip_dst_addr == IP4_ADDR_BCAST:
        if pkt.ip_proto == IP4_TYPE_UDP:
            procUdp4(pkt, bcast=True)

def sendIcmp4EchoReply(pkt: Packet) -> int:
    offset = pkt.ip_offset
    rsp= []

    # ICMP
    icmpRepl = bytearray(pkt.frame[offset:pkt.ip_maxoffset])
    icmpRepl[0] = ICMP4_ECHO_REPLY
    icmpRepl[1] = 0x00
    icmpRepl[2] = 0x00
    icmpRepl[3] = 0x00
    chksm = calcChecksum(icmpRepl)
    icmpRepl[2] = (chksm >> 8) & 0xFF
    icmpRepl[3] = chksm & 0xFF

    # IP
    if pkt.ntw.ip4TxCount == 255: pkt.ntw.ip4TxCount = 0
    ipHdr = makeIp4Hdr(pkt.ntw.myIp4Addr, pkt.ip_src_addr, pkt.ntw.ip4TxCount, IP4_TYPE_ICMP, len(icmpRepl))
    pkt.ntw.ip4TxCount += 1

    # Eth
    rsp.append(pkt.eth_src)
    rsp.append(pkt.ntw.myMacAddr)
    rsp.append(bytearray([ETH_TYPE_IP4 >> 8, ETH_TYPE_IP4_S]))

    rsp.append(ipHdr)
    rsp.append(icmpRepl)

    reply = pkt.ntw.txPkt(rsp)
    return reply

def procIcmp4(pkt: Packet) -> None:
    pkt.ntw.dos.check_icmp_limit() # ICMP flood protection
    offset = pkt.ip_offset
    if pkt.frame[offset] == ICMP4_ECHO_REQUEST:
        sendIcmp4EchoReply(pkt)
    else:
        pkt.ntw.event(f"Rx ICMP op={pkt.frame[offset]}")

def printEthPkt(pkt) -> None:
    print('DST:', ":".join("{:02x}".format(c) for c in pkt.frame[0:6]),
        'SRC:', ":".join("{:02x}".format(c) for c in pkt.frame[6:12]),
        'Type:', ":".join("{:02x}".format(c) for c in pkt.frame[12:14]),
        'len:', pkt.frame_len,
        'FCS', ":".join("{:02x}".format(c) for c in pkt.frame[pkt.frame_len:pkt.frame_len + 4]))

def procEth(pkt) -> None:
    pkt.eth_dst = pkt.frame[0:6]
    pkt.eth_src = pkt.frame[6:12]
    pkt.eth_type, = struct.unpack_from("!H", pkt.frame, 12)  # type: ignore
    pkt.eth_offset = 14

    if ETH_80211Q_TAG == pkt.eth_type:
        pkt.eth_type, = struct.unpack_from("!H", pkt.frame, 14)  # type: ignore
        pkt.eth_offset = 16

    if ETH_TYPE_IP4 == pkt.eth_type:
        procIp4(pkt)
    elif ETH_TYPE_ARP == pkt.eth_type:
        procArp(pkt)

def makeUdp4Hdr(srcIp: bytearray, srcPort: int, dstIp: bytes, dstPort: int, data: bytes) -> bytearray:
    udpHdr = bytearray(8)
    udpLen = len(data) + 8

    chksm = sum(struct.unpack('!HH', srcIp))
    chksm += sum(struct.unpack('!HH', dstIp))
    chksm += IP4_TYPE_UDP + 2*udpLen + srcPort + dstPort
    chksm = calcChecksum(data, chksm)

    udpHdr = bytearray(8)
    udpHdr[0] = srcPort >> 8
    udpHdr[1] = 0x10 # if srcPort == 10000 then > 0x10
    udpHdr[2] = dstPort >> 8
    udpHdr[3] = 0x88 # if dstPort == 5000 then > 0x88
    udpHdr[4] = udpLen >> 8
    udpHdr[5] = udpLen
    udpHdr[6] = chksm >> 8
    # udpHdr[7] = chksm
    udpHdr[6] = 0x00
    return udpHdr

def procUdp4(pkt: Packet, bcast: bool=False) -> None:
    pkt.ntw.dos.check_udp_limit() # UDP flood protection
    offset = pkt.ip_offset
    pkt.udp_srcPort, pkt.udp_dstPort, udpLen, chksm_rx = struct.unpack_from('!HHHH', pkt.frame, offset)  # type: ignore
    pkt.udp_dataLen = udpLen - 8
    pkt.udp_data = memoryview(pkt.frame[offset + 8:offset + udpLen])

    # # find UDP client
    # cb = None
    # if (False == bcast) and (pkt.udp_dstPort in pkt.ntw.udp4UniBind):
    #     cb = pkt.ntw.udp4UniBind[pkt.udp_dstPort]
    # elif (True == bcast) and (pkt.udp_dstPort in pkt.ntw.udp4BcastBind):
    #     cb = pkt.ntw.udp4BcastBind[pkt.udp_dstPort]

    # if cb is None:
    #     return None
    # verify checksum
    if (chksm_rx != 0):
        chksm = sum(struct.unpack('!HH', pkt.ip_src_addr))
        chksm += sum(struct.unpack('!HH', pkt.ip_dst_addr))
        chksm += IP4_TYPE_UDP + (2 * udpLen) + pkt.udp_srcPort + pkt.udp_dstPort
        chksm = calcChecksum(pkt.udp_data, chksm)
        if chksm == 0:
            chksm = 0xFFFF
        if (chksm != chksm_rx):
            pkt.ntw.event(f"Invalid UDP chksm: rx={chksm_rx:04X} calc=0x{chksm:04X}")
            return None

    # # call UDP client
    # cb(pkt)
    try:
        rxUdp = str(pkt.udp_data, 'utf-8')
        if len(rxUdp) > 0: pkt.ntw.UDP_Q.append(rxUdp)
    except UnicodeError: pass

def procTcp4(pkt: Packet) -> None:
    pkt.ntw.dos.check_tcp_limit()

def calcChecksum(data, startValue: int=0) -> int:
    chksm = startValue
    for idx in range(0, len(data)-1, 2):
        chksm += (data[idx] << 8) | data[idx+1]
    if len(data) & 0x1:
        chksm += data[-1] << 8
    chksm = (chksm >> 16) + (chksm & 0xffff)
    chksm += (chksm >> 16)
    return ~chksm & 0xffff
