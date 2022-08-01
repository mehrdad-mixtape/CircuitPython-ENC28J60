#!/usr/bin/env python
# -*- coding: utf8 -*-

#   Port from C to Python by Przemyslaw Bereski https://github.com/przemobe/
#   based on https://www.oryx-embedded.com/doc/enc28j60__driver_8c_source.html
#
#   This implementation is for MicroPython v1.17 (RP2)

#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; either version 2
#   of the License, or (at your option) any later version.

# Attention! : new version of this code is under development by mehrdad-mixtape
# This implementation is for circuit-python 7.2

# ENC28J60 Ethernet
# SPI1
# SCK -> GP10 -> pin 14 -> SPI1 SCK
# MOSI -> GP11 -> pin 15 -> SPI1 TX
# MISO -> GP12 -> pin 16 -> SPI1 Rx
# SDA -> GP13 -> pin 17 -> SPI1 CSn
# VCC 3.3v -> pin 36
# GND GND -> pin 38

from busio import SPI
from digitalio import DigitalInOut, Direction
from adafruit_bus_device.spi_device import SPIDevice
from microcontroller import Pin
from micropython import const
from time import sleep
from sys import exit
import struct

__version__ = '0.2.0v'
__repo__ = 'https://github.com/mehrdad-mixtape'

# RX buffer size
ENC28J60_ETH_RX_BUFFER_SIZE = const(1536)
# RX error codes
ENC28J60_ETH_RX_ERR_UNSPECIFIED = const(-1)
# TX buffer size
ENC28J60_ETH_TX_BUFFER_SIZE = const(1536)
# TX error codes
ENC28J60_ETH_TX_ERR_MSGSIZE = const(-1)
ENC28J60_ETH_TX_ERR_LINKDOWN = const(-2)
# Receive and transmit buffers
ENC28J60_RX_BUFFER_START = const(0x0000)
ENC28J60_RX_BUFFER_STOP = const(0x17FF)
ENC28J60_TX_BUFFER_START = const(0x1800)
ENC28J60_TX_BUFFER_STOP = const(0x1FFF)
# SPI command set
ENC28J60_CMD_RCR = const(0x00)
ENC28J60_CMD_RBM = const(0x3A)
ENC28J60_CMD_WCR = const(0x40)
ENC28J60_CMD_WBM = const(0x7A)
ENC28J60_CMD_BFS = const(0x80)
ENC28J60_CMD_BFC = const(0xA0)
ENC28J60_CMD_SRC = const(0xFF)
# ENC28J60 register types
ETH_REG_TYPE = const(0x0000)
MAC_REG_TYPE = const(0x1000)
MII_REG_TYPE = const(0x2000)
PHY_REG_TYPE = const(0x3000)
# ENC28J60 banks
BANK_0 = const(0x0000)
BANK_1 = const(0x0100)
BANK_2 = const(0x0200)
BANK_3 = const(0x0300)
# Related masks
REG_TYPE_MASK = const(0xF000)
REG_BANK_MASK = const(0x0F00)
REG_ADDR_MASK = const(0x001F)
# ENC28J60 registers
ENC28J60_ERDPTL = const((ETH_REG_TYPE | BANK_0 | 0x00))
ENC28J60_ERDPTH = const((ETH_REG_TYPE | BANK_0 | 0x01))
ENC28J60_EWRPTL = const((ETH_REG_TYPE | BANK_0 | 0x02))
ENC28J60_EWRPTH = const((ETH_REG_TYPE | BANK_0 | 0x03))
ENC28J60_ETXSTL = const((ETH_REG_TYPE | BANK_0 | 0x04))
ENC28J60_ETXSTH = const((ETH_REG_TYPE | BANK_0 | 0x05))
ENC28J60_ETXNDL = const((ETH_REG_TYPE | BANK_0 | 0x06))
ENC28J60_ETXNDH = const((ETH_REG_TYPE | BANK_0 | 0x07))
ENC28J60_ERXSTL = const((ETH_REG_TYPE | BANK_0 | 0x08))
ENC28J60_ERXSTH = const((ETH_REG_TYPE | BANK_0 | 0x09))
ENC28J60_ERXNDL = const((ETH_REG_TYPE | BANK_0 | 0x0A))
ENC28J60_ERXNDH = const((ETH_REG_TYPE | BANK_0 | 0x0B))
ENC28J60_ERXRDPTL = const((ETH_REG_TYPE | BANK_0 | 0x0C))
ENC28J60_ERXRDPTH = const((ETH_REG_TYPE | BANK_0 | 0x0D))
ENC28J60_ERXWRPTL = const((ETH_REG_TYPE | BANK_0 | 0x0E))
ENC28J60_ERXWRPTH = const((ETH_REG_TYPE | BANK_0 | 0x0F))
ENC28J60_EDMASTL = const((ETH_REG_TYPE | BANK_0 | 0x10))
ENC28J60_EDMASTH = const((ETH_REG_TYPE | BANK_0 | 0x11))
ENC28J60_EDMANDL = const((ETH_REG_TYPE | BANK_0 | 0x12))
ENC28J60_EDMANDH = const((ETH_REG_TYPE | BANK_0 | 0x13))
ENC28J60_EDMADSTL = const((ETH_REG_TYPE | BANK_0 | 0x14))
ENC28J60_EDMADSTH = const((ETH_REG_TYPE | BANK_0 | 0x15))
ENC28J60_EDMACSL = const((ETH_REG_TYPE | BANK_0 | 0x16))
ENC28J60_EDMACSH = const((ETH_REG_TYPE | BANK_0 | 0x17))
ENC28J60_EIE = const((ETH_REG_TYPE | BANK_0 | 0x1B))
ENC28J60_EIR = const((ETH_REG_TYPE | BANK_0 | 0x1C))
ENC28J60_ESTAT = const((ETH_REG_TYPE | BANK_0 | 0x1D))
ENC28J60_ECON2 = const((ETH_REG_TYPE | BANK_0 | 0x1E))
ENC28J60_ECON1 = const((ETH_REG_TYPE | BANK_0 | 0x1F))
ENC28J60_EHT0 = const((ETH_REG_TYPE | BANK_1 | 0x00))
ENC28J60_EHT1 = const((ETH_REG_TYPE | BANK_1 | 0x01))
ENC28J60_EHT2 = const((ETH_REG_TYPE | BANK_1 | 0x02))
ENC28J60_EHT3 = const((ETH_REG_TYPE | BANK_1 | 0x03))
ENC28J60_EHT4 = const((ETH_REG_TYPE | BANK_1 | 0x04))
ENC28J60_EHT5 = const((ETH_REG_TYPE | BANK_1 | 0x05))
ENC28J60_EHT6 = const((ETH_REG_TYPE | BANK_1 | 0x06))
ENC28J60_EHT7 = const((ETH_REG_TYPE | BANK_1 | 0x07))
ENC28J60_EPMM0 = const((ETH_REG_TYPE | BANK_1 | 0x08))
ENC28J60_EPMM1 = const((ETH_REG_TYPE | BANK_1 | 0x09))
ENC28J60_EPMM2 = const((ETH_REG_TYPE | BANK_1 | 0x0A))
ENC28J60_EPMM3 = const((ETH_REG_TYPE | BANK_1 | 0x0B))
ENC28J60_EPMM4 = const((ETH_REG_TYPE | BANK_1 | 0x0C))
ENC28J60_EPMM5 = const((ETH_REG_TYPE | BANK_1 | 0x0D))
ENC28J60_EPMM6 = const((ETH_REG_TYPE | BANK_1 | 0x0E))
ENC28J60_EPMM7 = const((ETH_REG_TYPE | BANK_1 | 0x0F))
ENC28J60_EPMCSL = const((ETH_REG_TYPE | BANK_1 | 0x10))
ENC28J60_EPMCSH = const((ETH_REG_TYPE | BANK_1 | 0x11))
ENC28J60_EPMOL = const((ETH_REG_TYPE | BANK_1 | 0x14))
ENC28J60_EPMOH = const((ETH_REG_TYPE | BANK_1 | 0x15))
ENC28J60_EWOLIE = const((ETH_REG_TYPE | BANK_1 | 0x16))
ENC28J60_EWOLIR = const((ETH_REG_TYPE | BANK_1 | 0x17))
ENC28J60_ERXFCON = const((ETH_REG_TYPE | BANK_1 | 0x18))
ENC28J60_EPKTCNT = const((ETH_REG_TYPE | BANK_1 | 0x19))
ENC28J60_MACON1 = const((MAC_REG_TYPE | BANK_2 | 0x00))
ENC28J60_MACON2 = const((MAC_REG_TYPE | BANK_2 | 0x01))
ENC28J60_MACON3 = const((MAC_REG_TYPE | BANK_2 | 0x02))
ENC28J60_MACON4 = const((MAC_REG_TYPE | BANK_2 | 0x03))
ENC28J60_MABBIPG = const((MAC_REG_TYPE | BANK_2 | 0x04))
ENC28J60_MAIPGL = const((MAC_REG_TYPE | BANK_2 | 0x06))
ENC28J60_MAIPGH = const((MAC_REG_TYPE | BANK_2 | 0x07))
ENC28J60_MACLCON1 = const((MAC_REG_TYPE | BANK_2 | 0x08))
ENC28J60_MACLCON2 = const((MAC_REG_TYPE | BANK_2 | 0x09))
ENC28J60_MAMXFLL = const((MAC_REG_TYPE | BANK_2 | 0x0A))
ENC28J60_MAMXFLH = const((MAC_REG_TYPE | BANK_2 | 0x0B))
ENC28J60_MAPHSUP = const((MAC_REG_TYPE | BANK_2 | 0x0D))
ENC28J60_MICON = const((MII_REG_TYPE | BANK_2 | 0x11))
ENC28J60_MICMD = const((MII_REG_TYPE | BANK_2 | 0x12))
ENC28J60_MIREGADR = const((MII_REG_TYPE | BANK_2 | 0x14))
ENC28J60_MIWRL = const((MII_REG_TYPE | BANK_2 | 0x16))
ENC28J60_MIWRH = const((MII_REG_TYPE | BANK_2 | 0x17))
ENC28J60_MIRDL = const((MII_REG_TYPE | BANK_2 | 0x18))
ENC28J60_MIRDH = const((MII_REG_TYPE | BANK_2 | 0x19))
ENC28J60_MAADR1 = const((MAC_REG_TYPE | BANK_3 | 0x00))
ENC28J60_MAADR0 = const((MAC_REG_TYPE | BANK_3 | 0x01))
ENC28J60_MAADR3 = const((MAC_REG_TYPE | BANK_3 | 0x02))
ENC28J60_MAADR2 = const((MAC_REG_TYPE | BANK_3 | 0x03))
ENC28J60_MAADR5 = const((MAC_REG_TYPE | BANK_3 | 0x04))
ENC28J60_MAADR4 = const((MAC_REG_TYPE | BANK_3 | 0x05))
ENC28J60_EBSTSD = const((ETH_REG_TYPE | BANK_3 | 0x06))
ENC28J60_EBSTCON = const((ETH_REG_TYPE | BANK_3 | 0x07))
ENC28J60_EBSTCSL = const((ETH_REG_TYPE | BANK_3 | 0x08))
ENC28J60_EBSTCSH = const((ETH_REG_TYPE | BANK_3 | 0x09))
ENC28J60_MISTAT = const((MII_REG_TYPE | BANK_3 | 0x0A))
ENC28J60_EREVID = const((ETH_REG_TYPE | BANK_3 | 0x12))
ENC28J60_ECOCON = const((ETH_REG_TYPE | BANK_3 | 0x15))
ENC28J60_EFLOCON = const((ETH_REG_TYPE | BANK_3 | 0x17))
ENC28J60_EPAUSL = const((ETH_REG_TYPE | BANK_3 | 0x18))
ENC28J60_EPAUSH = const((ETH_REG_TYPE | BANK_3 | 0x19))
# ENC28J60 PHY registers
ENC28J60_PHCON1 = const((PHY_REG_TYPE | 0x00))
ENC28J60_PHSTAT1 = const((PHY_REG_TYPE | 0x01))
ENC28J60_PHID1 = const((PHY_REG_TYPE | 0x02))
ENC28J60_PHID2 = const((PHY_REG_TYPE | 0x03))
ENC28J60_PHCON2 = const((PHY_REG_TYPE | 0x10))
ENC28J60_PHSTAT2 = const((PHY_REG_TYPE | 0x11))
ENC28J60_PHIE = const((PHY_REG_TYPE | 0x12))
ENC28J60_PHIR = const((PHY_REG_TYPE | 0x13))
ENC28J60_PHLCON = const((PHY_REG_TYPE | 0x14))
# Ethernet Interrupt Enable register
ENC28J60_EIE_INTIE = const(0x80)
ENC28J60_EIE_PKTIE = const(0x40)
ENC28J60_EIE_DMAIE = const(0x20)
ENC28J60_EIE_LINKIE = const(0x10)
ENC28J60_EIE_TXIE = const(0x08)
ENC28J60_EIE_WOLIE = const(0x04)
ENC28J60_EIE_TXERIE = const(0x02)
ENC28J60_EIE_RXERIE = const(0x01)
# Ethernet Interrupt Request register
ENC28J60_EIR_PKTIF = const(0x40)
ENC28J60_EIR_DMAIF = const(0x20)
ENC28J60_EIR_LINKIF = const(0x10)
ENC28J60_EIR_TXIF = const(0x08)
ENC28J60_EIR_WOLIF = const(0x04)
ENC28J60_EIR_TXERIF = const(0x02)
ENC28J60_EIR_RXERIF = const(0x01)
# Ethernet Status register
ENC28J60_ESTAT_INT = const(0x80)
ENC28J60_ESTAT_R6 = const(0x40)
ENC28J60_ESTAT_R5 = const(0x20)
ENC28J60_ESTAT_LATECOL = const(0x10)
ENC28J60_ESTAT_RXBUSY = const(0x04)
ENC28J60_ESTAT_TXABRT = const(0x02)
ENC28J60_ESTAT_CLKRDY = const(0x01)
# Ethernet Control 2 register
ENC28J60_ECON2_AUTOINC = const(0x80)
ENC28J60_ECON2_PKTDEC = const(0x40)
ENC28J60_ECON2_PWRSV = const(0x20)
ENC28J60_ECON2_VRPS = const(0x08)
# Ethernet Control 1 register
ENC28J60_ECON1_TXRST = const(0x80)
ENC28J60_ECON1_RXRST = const(0x40)
ENC28J60_ECON1_DMAST = const(0x20)
ENC28J60_ECON1_CSUMEN = const(0x10)
ENC28J60_ECON1_TXRTS = const(0x08)
ENC28J60_ECON1_RXEN = const(0x04)
ENC28J60_ECON1_BSEL1 = const(0x02)
ENC28J60_ECON1_BSEL0 = const(0x01)
# Ethernet Wake-Up On LAN Interrupt Enable register
ENC28J60_EWOLIE_UCWOLIE = const(0x80)
ENC28J60_EWOLIE_AWOLIE = const(0x40)
ENC28J60_EWOLIE_PMWOLIE = const(0x10)
ENC28J60_EWOLIE_MPWOLIE = const(0x08)
ENC28J60_EWOLIE_HTWOLIE = const(0x04)
ENC28J60_EWOLIE_MCWOLIE = const(0x02)
ENC28J60_EWOLIE_BCWOLIE = const(0x01)
# Ethernet Wake-Up On LAN Interrupt Request register
ENC28J60_EWOLIR_UCWOLIF = const(0x80)
ENC28J60_EWOLIR_AWOLIF = const(0x40)
ENC28J60_EWOLIR_PMWOLIF = const(0x10)
ENC28J60_EWOLIR_MPWOLIF = const(0x08)
ENC28J60_EWOLIR_HTWOLIF = const(0x04)
ENC28J60_EWOLIR_MCWOLIF = const(0x02)
ENC28J60_EWOLIR_BCWOLIF = const(0x01)
# Receive Filter Control register
ENC28J60_ERXFCON_UCEN = const(0x80)
ENC28J60_ERXFCON_ANDOR = const(0x40)
ENC28J60_ERXFCON_CRCEN = const(0x20)
ENC28J60_ERXFCON_PMEN = const(0x10)
ENC28J60_ERXFCON_MPEN = const(0x08)
ENC28J60_ERXFCON_HTEN = const(0x04)
ENC28J60_ERXFCON_MCEN = const(0x02)
ENC28J60_ERXFCON_BCEN = const(0x01)
# MAC Control 1 register
ENC28J60_MACON1_LOOPBK = const(0x10)
ENC28J60_MACON1_TXPAUS = const(0x08)
ENC28J60_MACON1_RXPAUS = const(0x04)
ENC28J60_MACON1_PASSALL = const(0x02)
ENC28J60_MACON1_MARXEN = const(0x01)
# MAC Control 2 register
ENC28J60_MACON2_MARST = const(0x80)
ENC28J60_MACON2_RNDRST = const(0x40)
ENC28J60_MACON2_MARXRST = const(0x08)
ENC28J60_MACON2_RFUNRST = const(0x04)
ENC28J60_MACON2_MATXRST = const(0x02)
ENC28J60_MACON2_TFUNRST = const(0x01)
# MAC Control 3 register
ENC28J60_MACON3_PADCFG = const(0xE0)
ENC28J60_MACON3_PADCFG_NO = const(0x00)
ENC28J60_MACON3_PADCFG_60_BYTES = const(0x20)
ENC28J60_MACON3_PADCFG_64_BYTES = const(0x60)
ENC28J60_MACON3_PADCFG_AUTO = const(0xA0)
ENC28J60_MACON3_TXCRCEN = const(0x10)
ENC28J60_MACON3_PHDRLEN = const(0x08)
ENC28J60_MACON3_HFRMEN = const(0x04)
ENC28J60_MACON3_FRMLNEN = const(0x02)
ENC28J60_MACON3_FULDPX = const(0x01)
# MAC Control 4 register
ENC28J60_MACON4_DEFER = const(0x40)
ENC28J60_MACON4_BPEN = const(0x20)
ENC28J60_MACON4_NOBKOFF = const(0x10)
ENC28J60_MACON4_LONGPRE = const(0x02)
ENC28J60_MACON4_PUREPRE = const(0x01)
# Back-to-Back Inter-Packet Gap register
ENC28J60_MABBIPG_DEFAULT_HD = const(0x12)
ENC28J60_MABBIPG_DEFAULT_FD = const(0x15)
# Non-Back-to-Back Inter-Packet Gap Low Byte register
ENC28J60_MAIPGL_DEFAULT = const(0x12)
# Non-Back-to-Back Inter-Packet Gap High Byte register
ENC28J60_MAIPGH_DEFAULT = const(0x0C)
# Retransmission Maximum register
ENC28J60_MACLCON1_RETMAX = const(0x0F)
# Collision Window register
ENC28J60_MACLCON2_COLWIN = const(0x3F)
ENC28J60_MACLCON2_COLWIN_DEFAULT = const(0x37)
# MAC-PHY Support register
ENC28J60_MAPHSUP_RSTINTFC = const(0x80)
ENC28J60_MAPHSUP_R4 = const(0x10)
ENC28J60_MAPHSUP_RSTRMII = const(0x08)
ENC28J60_MAPHSUP_R0 = const(0x01)
# MII Control register
ENC28J60_MICON_RSTMII = const(0x80)
# MII Command register
ENC28J60_MICMD_MIISCAN = const(0x02)
ENC28J60_MICMD_MIIRD = const(0x01)
# MII Register Address register
ENC28J60_MIREGADR_VAL = const(0x1F)
# Self-Test Control register
ENC28J60_EBSTCON_PSV = const(0xE0)
ENC28J60_EBSTCON_PSEL = const(0x10)
ENC28J60_EBSTCON_TMSEL = const(0x0C)
ENC28J60_EBSTCON_TMSEL_RANDOM = const(0x00)
ENC28J60_EBSTCON_TMSEL_ADDR = const(0x04)
ENC28J60_EBSTCON_TMSEL_PATTERN_SHIFT = const(0x08)
ENC28J60_EBSTCON_TMSEL_RACE_MODE = const(0x0C)
ENC28J60_EBSTCON_TME = const(0x02)
ENC28J60_EBSTCON_BISTST = const(0x01)
# MII Status register
ENC28J60_MISTAT_R3 = const(0x08)
ENC28J60_MISTAT_NVALID = const(0x04)
ENC28J60_MISTAT_SCAN = const(0x02)
ENC28J60_MISTAT_BUSY = const(0x01)
# Ethernet Revision ID register
ENC28J60_EREVID_REV = const(0x1F)
ENC28J60_EREVID_REV_B1 = const(0x02)
ENC28J60_EREVID_REV_B4 = const(0x04)
ENC28J60_EREVID_REV_B5 = const(0x05)
ENC28J60_EREVID_REV_B7 = const(0x06)
# Clock Output Control register
ENC28J60_ECOCON_COCON = const(0x07)
ENC28J60_ECOCON_COCON_DISABLED = const(0x00)
ENC28J60_ECOCON_COCON_DIV1 = const(0x01)
ENC28J60_ECOCON_COCON_DIV2 = const(0x02)
ENC28J60_ECOCON_COCON_DIV3 = const(0x03)
ENC28J60_ECOCON_COCON_DIV4 = const(0x04)
ENC28J60_ECOCON_COCON_DIV8 = const(0x05)
# Ethernet Flow Control register
ENC28J60_EFLOCON_FULDPXS = const(0x04)
ENC28J60_EFLOCON_FCEN = const(0x03)
ENC28J60_EFLOCON_FCEN_OFF = const(0x00)
ENC28J60_EFLOCON_FCEN_ON_HD = const(0x01)
ENC28J60_EFLOCON_FCEN_ON_FD = const(0x02)
ENC28J60_EFLOCON_FCEN_SEND_PAUSE = const(0x03)
# PHY Control 1 register
ENC28J60_PHCON1_PRST = const(0x8000)
ENC28J60_PHCON1_PLOOPBK = const(0x4000)
ENC28J60_PHCON1_PPWRSV = const(0x0800)
ENC28J60_PHCON1_PDPXMD = const(0x0100)
# Physical Layer Status 1 register
ENC28J60_PHSTAT1_PFDPX = const(0x1000)
ENC28J60_PHSTAT1_PHDPX = const(0x0800)
ENC28J60_PHSTAT1_LLSTAT = const(0x0004)
ENC28J60_PHSTAT1_JBRSTAT = const(0x0002)
# PHY Identifier 1 register
ENC28J60_PHID1_PIDH = const(0xFFFF)
ENC28J60_PHID1_PIDH_DEFAULT = const(0x0083)
# PHY Identifier 2 register
ENC28J60_PHID2_PIDL = const(0xFC00)
ENC28J60_PHID2_PIDL_DEFAULT = const(0x1400)
ENC28J60_PHID2_PPN = const(0x03F0)
ENC28J60_PHID2_PPN_DEFAULT = const(0x0000)
ENC28J60_PHID2_PREV = const(0x000F)
# PHY Control 2 register
ENC28J60_PHCON2_FRCLNK = const(0x4000)
ENC28J60_PHCON2_TXDIS = const(0x2000)
ENC28J60_PHCON2_JABBER = const(0x0400)
ENC28J60_PHCON2_HDLDIS = const(0x0100)
# Physical Layer Status 2 register
ENC28J60_PHSTAT2_TXSTAT = const(0x2000)
ENC28J60_PHSTAT2_RXSTAT = const(0x1000)
ENC28J60_PHSTAT2_COLSTAT = const(0x0800)
ENC28J60_PHSTAT2_LSTAT = const(0x0400)
ENC28J60_PHSTAT2_DPXSTAT = const(0x0200)
ENC28J60_PHSTAT2_PLRITY = const(0x0010)
# PHY Interrupt Enable register
ENC28J60_PHIE_PLNKIE = const(0x0010)
ENC28J60_PHIE_PGEIE = const(0x0002)
# PHY Interrupt Request register
ENC28J60_PHIR_PLNKIF = const(0x0010)
ENC28J60_PHIR_PGIF = const(0x0004)
# PHY Module LED Control register
ENC28J60_PHLCON_LACFG = const(0x0F00)
ENC28J60_PHLCON_LACFG_TX = const(0x0100)
ENC28J60_PHLCON_LACFG_RX = const(0x0200)
ENC28J60_PHLCON_LACFG_COL = const(0x0300)
ENC28J60_PHLCON_LACFG_LINK = const(0x0400)
ENC28J60_PHLCON_LACFG_DUPLEX = const(0x0500)
ENC28J60_PHLCON_LACFG_TX_RX = const(0x0700)
ENC28J60_PHLCON_LACFG_ON = const(0x0800)
ENC28J60_PHLCON_LACFG_OFF = const(0x0900)
ENC28J60_PHLCON_LACFG_BLINK_FAST = const(0x0A00)
ENC28J60_PHLCON_LACFG_BLINK_SLOW = const(0x0B00)
ENC28J60_PHLCON_LACFG_LINK_RX = const(0x0C00)
ENC28J60_PHLCON_LACFG_LINK_TX_RX = const(0x0D00)
ENC28J60_PHLCON_LACFG_DUPLEX_COL = const(0x0E00)
ENC28J60_PHLCON_LBCFG = const(0x00F0)
ENC28J60_PHLCON_LBCFG_TX = const(0x0010)
ENC28J60_PHLCON_LBCFG_RX = const(0x0020)
ENC28J60_PHLCON_LBCFG_COL = const(0x0030)
ENC28J60_PHLCON_LBCFG_LINK = const(0x0040)
ENC28J60_PHLCON_LBCFG_DUPLEX = const(0x0050)
ENC28J60_PHLCON_LBCFG_TX_RX = const(0x0070)
ENC28J60_PHLCON_LBCFG_ON = const(0x0080)
ENC28J60_PHLCON_LBCFG_OFF = const(0x0090)
ENC28J60_PHLCON_LBCFG_BLINK_FAST = const(0x00A0)
ENC28J60_PHLCON_LBCFG_BLINK_SLOW = const(0x00B0)
ENC28J60_PHLCON_LBCFG_LINK_RX = const(0x00C0)
ENC28J60_PHLCON_LBCFG_LINK_TX_RX = const(0x00D0)
ENC28J60_PHLCON_LBCFG_DUPLEX_COL = const(0x00E0)
ENC28J60_PHLCON_LFRQ = const(0x000C)
ENC28J60_PHLCON_LFRQ_40_MS = const(0x0000)
ENC28J60_PHLCON_LFRQ_73_MS = const(0x0004)
ENC28J60_PHLCON_LFRQ_139_MS = const(0x0008)
ENC28J60_PHLCON_STRCH = const(0x0002)
# Per-packet control byte
ENC28J60_TX_CTRL_PHUGEEN = const(0x08)
ENC28J60_TX_CTRL_PPADEN = const(0x04)
ENC28J60_TX_CTRL_PCRCEN = const(0x02)
ENC28J60_TX_CTRL_POVERRIDE = const(0x01)
# Receive status vector
ENC28J60_RSV_VLAN_TYPE = const(0x4000)
ENC28J60_RSV_UNKNOWN_OPCODE = const(0x2000)
ENC28J60_RSV_PAUSE_CONTROL_FRAME = const(0x1000)
ENC28J60_RSV_CONTROL_FRAME = const(0x0800)
ENC28J60_RSV_DRIBBLE_NIBBLE = const(0x0400)
ENC28J60_RSV_BROADCAST_PACKET = const(0x0200)
ENC28J60_RSV_MULTICAST_PACKET = const(0x0100)
ENC28J60_RSV_RECEIVED_OK = const(0x0080)
ENC28J60_RSV_LENGTH_OUT_OF_RANGE = const(0x0040)
ENC28J60_RSV_LENGTH_CHECK_ERROR = const(0x0020)
ENC28J60_RSV_CRC_ERROR = const(0x0010)
ENC28J60_RSV_CARRIER_EVENT = const(0x0004)
ENC28J60_RSV_DROP_EVENT = const(0x0001)
# Functions:
def LSB(val: int) -> int:
    """Return LSB of value"""
    return (val & 0xFF)
def MSB(val: int) -> int:
    """Return MSB of value"""
    return ((val >> 8) & 0xFF)
# Classes:
class ENC28J60:
    """This class provides control over ENC28J60 Ethernet chips"""
    # best baudrate for ENC28J60 is between 100_000 - 10_000_000!!!
    spi_detect: bool = False
    def __init__(self, spi: SPI, cs: Pin,
    baudrate: int=120_000,
    macAddr: bytearray=None,
    fullDuplex: bool=True,
    enableMulticastRx: bool=False,
    logger=None):
        self._logger = logger
        try:
            # CS pin
            self._cs = DigitalInOut(cs)
            self._cs.direction = Direction.OUTPUT
            # SPI
            self._spi = SPIDevice(spi, self._cs, baudrate=baudrate)
            ENC28J60.spi_detect = True
        except Exception:
            ENC28J60.spi_detect = False
        else:
            self.fullDuplex: bool = fullDuplex
            self.enableMulticastRx: bool = enableMulticastRx
            self._revId: int = 0
            self._tmpBytearray1B= bytearray(1)
            self._tmpBytearray2B = bytearray(2)
            self._tmpBytearray3B = bytearray(3)
            self._tmpBytearray6B = bytearray(6)
            # MAC Address
            if macAddr: self.macAddr = bytearray(macAddr)
            else: self.macAddr = bytearray(b'\x0e\x5f\x5f\x19\x98\x00')
            # self.macAddr = bytearray(b'\x0e\x5f\x5f' + unique_id()[-3:])
                
    @property
    def ENC28J60_GetMacAddr(self) -> bytearray:
        """Return MAC Address"""
        return self.macAddr
    @property
    def ENC28J60_GetRevId(self) -> int:
        """Return RevID"""
        if self._revId is None or self._revId == 0:
            self._revId = self.ENC28J60_ReadReg(ENC28J60_EREVID) & ENC28J60_EREVID_REV
        return self._revId
    def ENC28J60_Event(self, priority: str, msg: str) -> None:
        try: self._logger.event_registrar('ENC28J60', priority, msg)
        except AttributeError: pass
        finally: print(f"ENC28J60: {msg}")
    def ENC28J60_Init(self) -> None:
        """Initialize ENC28J60"""
        if ENC28J60.spi_detect: self.ENC28J60_Event('INFO', 'SPIDevice detected')
        else: self.ENC28J60_Event('ERROR', 'SPIDevice undetected'); return None
        self.ENC28J60_SoftReset() # Issue a system reset

        sleep(0.01) # After issuing the reset command, wait at least 1ms in firmware for the device to be ready

        # Initialize driver specific variables
        self._currentBank: int = 0xFFFF
        self._nextPacket: int = ENC28J60_RX_BUFFER_START

        # Read silicon revision ID
        self._revId = self.ENC28J60_ReadReg(ENC28J60_EREVID) & ENC28J60_EREVID_REV

        # Disable CLKOUT output
        self.ENC28J60_WriteReg(ENC28J60_ECOCON, ENC28J60_ECOCON_COCON_DISABLED)

        # Set the MAC address of the station
        self.ENC28J60_WriteReg(ENC28J60_MAADR5, self.macAddr[0])
        self.ENC28J60_WriteReg(ENC28J60_MAADR4, self.macAddr[1])
        self.ENC28J60_WriteReg(ENC28J60_MAADR3, self.macAddr[2])
        self.ENC28J60_WriteReg(ENC28J60_MAADR2, self.macAddr[3])
        self.ENC28J60_WriteReg(ENC28J60_MAADR1, self.macAddr[4])
        self.ENC28J60_WriteReg(ENC28J60_MAADR0, self.macAddr[5])

        # Set receive buffer location
        self.ENC28J60_WriteReg(ENC28J60_ERXSTL, LSB(ENC28J60_RX_BUFFER_START))
        self.ENC28J60_WriteReg(ENC28J60_ERXSTH, MSB(ENC28J60_RX_BUFFER_START))
        self.ENC28J60_WriteReg(ENC28J60_ERXNDL, LSB(ENC28J60_RX_BUFFER_STOP))
        self.ENC28J60_WriteReg(ENC28J60_ERXNDH, MSB(ENC28J60_RX_BUFFER_STOP))

        # The ERXRDPT register defines a location within the FIFO where the receive hardware is forbidden to write to
        self.ENC28J60_WriteReg(ENC28J60_ERXRDPTL, LSB(ENC28J60_RX_BUFFER_STOP))
        self.ENC28J60_WriteReg(ENC28J60_ERXRDPTH, MSB(ENC28J60_RX_BUFFER_STOP))

        # Configure the receive filters
        if self.enableMulticastRx:
            self.ENC28J60_WriteReg(ENC28J60_ERXFCON, ENC28J60_ERXFCON_UCEN | ENC28J60_ERXFCON_CRCEN | ENC28J60_ERXFCON_HTEN | ENC28J60_ERXFCON_BCEN | ENC28J60_ERXFCON_MCEN)
        else:
            self.ENC28J60_WriteReg(ENC28J60_ERXFCON, ENC28J60_ERXFCON_UCEN | ENC28J60_ERXFCON_CRCEN | ENC28J60_ERXFCON_HTEN | ENC28J60_ERXFCON_BCEN)

        # Initialize the hash table
        self.ENC28J60_WriteReg(ENC28J60_EHT0, 0x00)
        self.ENC28J60_WriteReg(ENC28J60_EHT1, 0x00)
        self.ENC28J60_WriteReg(ENC28J60_EHT2, 0x00)
        self.ENC28J60_WriteReg(ENC28J60_EHT3, 0x00)
        self.ENC28J60_WriteReg(ENC28J60_EHT4, 0x00)
        self.ENC28J60_WriteReg(ENC28J60_EHT5, 0x00)
        self.ENC28J60_WriteReg(ENC28J60_EHT6, 0x00)
        self.ENC28J60_WriteReg(ENC28J60_EHT7, 0x00)

        # Pull the MAC out of reset
        self.ENC28J60_WriteReg(ENC28J60_MACON2, 0x00)

        # Enable the MAC to receive frames
        self.ENC28J60_WriteReg(ENC28J60_MACON1, ENC28J60_MACON1_TXPAUS | ENC28J60_MACON1_RXPAUS | ENC28J60_MACON1_MARXEN)

        # Enable automatic padding, always append a valid CRC and check frame length. MAC can operate in half-duplex or full-duplex mode
        if self.fullDuplex:
            self.ENC28J60_WriteReg(ENC28J60_MACON3, ENC28J60_MACON3_PADCFG_AUTO | ENC28J60_MACON3_TXCRCEN | ENC28J60_MACON3_FRMLNEN | ENC28J60_MACON3_FULDPX)
        else:
            self.ENC28J60_WriteReg(ENC28J60_MACON3, ENC28J60_MACON3_PADCFG_AUTO | ENC28J60_MACON3_TXCRCEN | ENC28J60_MACON3_FRMLNEN)

        # When the medium is occupied, the MAC will wait indefinitely for it to become free when attempting to transmit
        self.ENC28J60_WriteReg(ENC28J60_MACON4, ENC28J60_MACON4_DEFER)

        # Maximum frame length that can be received or transmitted
        self.ENC28J60_WriteReg(ENC28J60_MAMXFLL, LSB(ENC28J60_ETH_RX_BUFFER_SIZE))
        self.ENC28J60_WriteReg(ENC28J60_MAMXFLH, MSB(ENC28J60_ETH_RX_BUFFER_SIZE))

        # Configure the back-to-back inter-packet gap register
        if self.fullDuplex:
            self.ENC28J60_WriteReg(ENC28J60_MABBIPG, ENC28J60_MABBIPG_DEFAULT_FD)
        else:
            self.ENC28J60_WriteReg(ENC28J60_MABBIPG, ENC28J60_MABBIPG_DEFAULT_HD)

        # Configure the non-back-to-back inter-packet gap register
        self.ENC28J60_WriteReg(ENC28J60_MAIPGL, ENC28J60_MAIPGL_DEFAULT)
        self.ENC28J60_WriteReg(ENC28J60_MAIPGH, ENC28J60_MAIPGH_DEFAULT)

        # Collision window register
        self.ENC28J60_WriteReg(ENC28J60_MACLCON2, ENC28J60_MACLCON2_COLWIN_DEFAULT)

        # Set the PHY to the proper duplex mode
        if self.fullDuplex:
            self.ENC28J60_WritePhyReg(ENC28J60_PHCON1, ENC28J60_PHCON1_PDPXMD)
        else:
            self.ENC28J60_WritePhyReg(ENC28J60_PHCON1, 0x0000)

        # Disable half-duplex loopback in PHY
        self.ENC28J60_WritePhyReg(ENC28J60_PHCON2, ENC28J60_PHCON2_HDLDIS)

        # LEDA displays link status and LEDB displays TX/RX activity
        # self.ENC28J60_WritePhyReg(ENC28J60_PHLCON, ENC28J60_PHLCON_LACFG_LINK | ENC28J60_PHLCON_LBCFG_TX_RX | ENC28J60_PHLCON_LFRQ_40_MS | ENC28J60_PHLCON_STRCH)

        # Clear interrupt flags
        self.ENC28J60_WriteReg(ENC28J60_EIR, 0x00)

        # Configure interrupts as desired
        self.ENC28J60_WriteReg(ENC28J60_EIE, ENC28J60_EIE_INTIE | ENC28J60_EIE_PKTIE | ENC28J60_EIE_LINKIE)
        # | ENC28J60_EIE_TXIE | ENC28J60_EIE_TXERIE)

        # Configure PHY interrupts as desired
        self.ENC28J60_WritePhyReg(ENC28J60_PHIE, ENC28J60_PHIE_PLNKIE | ENC28J60_PHIE_PGEIE)

        # Set RXEN to enable reception
        self.ENC28J60_WriteReg(ENC28J60_ECON1, ENC28J60_ECON1_RXEN)
        # Show event
        self.ENC28J60_Event('INFO', 'Ethernet initialized')
    def ENC28J60_WriteSpi(self, data: bytearray) -> None:
        self._cs.value = 0
        with self._spi as bus:
            bus.write(data)
        self._cs.value = 1
    def ENC28J60_SoftReset(self) -> None:
        self._tmpBytearray1B[0] = ENC28J60_CMD_SRC
        self.ENC28J60_WriteSpi(self._tmpBytearray1B)
        self.ENC28J60_Event('DEBUG', 'SPIDevice softreset')
    def ENC28J60_ClearBit(self, address: int, mask: int) -> None:
        self._tmpBytearray2B[0] = (ENC28J60_CMD_BFC | (address & REG_ADDR_MASK))
        self._tmpBytearray2B[1] = mask
        self.ENC28J60_WriteSpi(self._tmpBytearray2B)
    def ENC28J60_SetBit(self, address: int, mask: int) -> None:
        self._tmpBytearray2B[0] = (ENC28J60_CMD_BFS | (address & REG_ADDR_MASK))
        self._tmpBytearray2B[1] = mask
        self.ENC28J60_WriteSpi(self._tmpBytearray2B)
    def ENC28J60_SelectBank(self, address: int) -> None:
        # uint16_t address
        bank: int = address & REG_BANK_MASK

        # Rewrite the bank number only if a change is detected
        if (bank == self._currentBank):
            return None

        # Select the relevant bank
        if bank == BANK_0:
            self.ENC28J60_ClearBit(ENC28J60_ECON1, ENC28J60_ECON1_BSEL1 | ENC28J60_ECON1_BSEL0)
        elif bank == BANK_1:
            self.ENC28J60_SetBit(ENC28J60_ECON1, ENC28J60_ECON1_BSEL0)
            self.ENC28J60_ClearBit(ENC28J60_ECON1, ENC28J60_ECON1_BSEL1)
        elif bank == BANK_2:
            self.ENC28J60_ClearBit(ENC28J60_ECON1, ENC28J60_ECON1_BSEL0)
            self.ENC28J60_SetBit(ENC28J60_ECON1, ENC28J60_ECON1_BSEL1)
        else:
            self.ENC28J60_SetBit(ENC28J60_ECON1, ENC28J60_ECON1_BSEL1 | ENC28J60_ECON1_BSEL0)

        # Save bank number
        self._currentBank = bank
        return None
    def ENC28J60_WriteReg(self, address: int, data: int) -> None:
        # Make sure the corresponding bank is selected
        self.ENC28J60_SelectBank(address)

        # Write opcode and register address, Write register value
        self._tmpBytearray2B[0] = (ENC28J60_CMD_WCR | (address & REG_ADDR_MASK))
        self._tmpBytearray2B[1] = data
        self.ENC28J60_WriteSpi(self._tmpBytearray2B)
    def ENC28J60_ReadReg(self, address: int) -> int:
       # Make sure the corresponding bank is selected
        self.ENC28J60_SelectBank(address)

        self._cs.value = 0 # CS is acivate
        with self._spi as bus:
            data: int = 0
            if (address & REG_TYPE_MASK) != ETH_REG_TYPE:
                # Write opcode and register address
                self._tmpBytearray3B[0] = (ENC28J60_CMD_RCR | (address & REG_ADDR_MASK))
                # When reading MAC or MII registers, a dummy byte is first shifted out
                self._tmpBytearray3B[1] = 0
                # Read register contents
                self._tmpBytearray3B[2] = 0
                bus.write_readinto(self._tmpBytearray3B, self._tmpBytearray3B)
                data = self._tmpBytearray3B[2]
            else:
                # Write opcode and register address
                self._tmpBytearray2B[0] = (ENC28J60_CMD_RCR | (address & REG_ADDR_MASK))
                # Read register contents
                self._tmpBytearray2B[1] = 0
                bus.write_readinto(self._tmpBytearray2B, self._tmpBytearray2B)
                data = self._tmpBytearray2B[1]

        # Terminate the operation by raising the CS pin
        self._cs.value = 1 # CS is deacivate

        # Return register contents
        return data
    def ENC28J60_WritePhyReg(self, address: int, data: int) -> None:
        # Write register address
        self.ENC28J60_WriteReg(ENC28J60_MIREGADR, address & REG_ADDR_MASK)
        # Write the lower 8 bits
        self.ENC28J60_WriteReg(ENC28J60_MIWRL, LSB(data))
        # Write the upper 8 bits
        self.ENC28J60_WriteReg(ENC28J60_MIWRH, MSB(data))

        # Wait until the PHY register has been written
        while (self.ENC28J60_ReadReg(ENC28J60_MISTAT) & ENC28J60_MISTAT_BUSY) != 0:
            pass
    def ENC28J60_ReadPhyReg(self, address: int) -> int:
        # Write register address
        self.ENC28J60_WriteReg(ENC28J60_MIREGADR, address & REG_ADDR_MASK)

        # Start read operation
        self.ENC28J60_WriteReg(ENC28J60_MICMD, ENC28J60_MICMD_MIIRD)

        # Wait for the read operation to complete
        while 0 != (self.ENC28J60_ReadReg(ENC28J60_MISTAT) & ENC28J60_MISTAT_BUSY):
            pass

        # Clear command register
        self.ENC28J60_WriteReg(ENC28J60_MICMD, 0)

        data: int = 0
        # Read the lower 8 bits
        data = self.ENC28J60_ReadReg(ENC28J60_MIRDL)
        # Read the upper 8 bits
        data |= self.ENC28J60_ReadReg(ENC28J60_MIRDH) << 8

        # Return register contents
        return data
    def ENC28J60_WriteBuffer(self, chunks: list):
        self._cs.value = 0 # CS is activate

        with self._spi as bus:
            # Write opcode, Write per-packet control byte
            self._tmpBytearray2B[0] = ENC28J60_CMD_WBM
            self._tmpBytearray2B[1] = 0x00
            bus.write(self._tmpBytearray2B)

            # Loop through data chunks
            for data in chunks:
                bus.write(data)

        # Terminate the operation by raising the CS pin
        self._cs.value = 1 # CS is deactivate
    def ENC28J60_ReadBuffer(self, data: bytearray | memoryview) -> None:
        # Pull the CS pin low
        self._cs.value = 0

        with self._spi as bus:
            # Write opcode
            self._tmpBytearray1B[0] = ENC28J60_CMD_RBM
            bus.write(self._tmpBytearray1B)

            # Copy data from SRAM buffer
            bus.readinto(data)

        # Terminate the operation by raising the CS pin
        self._cs.value = 1
    def ENC28J60_IsLinkUp(self) -> bool:
        return (self.ENC28J60_ReadPhyReg(ENC28J60_PHSTAT2) & ENC28J60_PHSTAT2_LSTAT) != 0
    def ENC28J60_IsLinkStateChanged(self) -> bool:
        # Read interrupt status register
        status: int = self.ENC28J60_ReadReg(ENC28J60_EIR)

        # Check whether the link state has changed
        if (status & ENC28J60_EIR_LINKIF) == 0:
            self.ENC28J60_Event('WARNING', 'Ethernet link stat has changed')
            return False

        # Clear PHY interrupts flags
        self.ENC28J60_ReadPhyReg(ENC28J60_PHIR)

        # Clear interrupt flag
        self.ENC28J60_ClearBit(ENC28J60_EIR, ENC28J60_EIR_LINKIF)
        return True
    def ENC28J60_GetRxPacketCnt(self) -> int:
        return self.ENC28J60_ReadReg(ENC28J60_EPKTCNT)
    def ENC28J60_SendPacket(self, chunks: list) -> int:
        # Retrieve the length of the packet
        length: int = 0
        for data in chunks:
            length += len(data)

        # Check the frame length
        if length > ENC28J60_ETH_TX_BUFFER_SIZE:
            return ENC28J60_ETH_TX_ERR_MSGSIZE

        # Make sure the link is up before transmitting the frame
        if self.ENC28J60_IsLinkUp() == False:
            return ENC28J60_ETH_TX_ERR_LINKDOWN

        # It is recommended to reset the transmit logic before attempting to transmit a packet
        self.ENC28J60_SetBit(ENC28J60_ECON1, ENC28J60_ECON1_TXRST)
        self.ENC28J60_ClearBit(ENC28J60_ECON1, ENC28J60_ECON1_TXRST)

        # Interrupt flags should be cleared after the reset is completed
        self.ENC28J60_ClearBit(ENC28J60_EIR, ENC28J60_EIR_TXIF | ENC28J60_EIR_TXERIF)

        # Set transmit buffer location
        self.ENC28J60_WriteReg(ENC28J60_ETXSTL, LSB(ENC28J60_TX_BUFFER_START))
        self.ENC28J60_WriteReg(ENC28J60_ETXSTH, MSB(ENC28J60_TX_BUFFER_START))

        # Point to start of transmit buffer
        self.ENC28J60_WriteReg(ENC28J60_EWRPTL, LSB(ENC28J60_TX_BUFFER_START))
        self.ENC28J60_WriteReg(ENC28J60_EWRPTH, MSB(ENC28J60_TX_BUFFER_START))

        # Copy the data to the transmit buffer
        self.ENC28J60_WriteBuffer(chunks)

        # ETXND should point to the last byte in the data payload
        self.ENC28J60_WriteReg(ENC28J60_ETXNDL, LSB(ENC28J60_TX_BUFFER_START + length))
        self.ENC28J60_WriteReg(ENC28J60_ETXNDH, MSB(ENC28J60_TX_BUFFER_START + length))

        # Start transmission
        self.ENC28J60_SetBit(ENC28J60_ECON1, ENC28J60_ECON1_TXRTS)
        return length
    def ENC28J60_ReceivePacket(self, rxBuffer: bytearray) -> int:
        if self.ENC28J60_GetRxPacketCnt() == 0:
            return 0
    
        # Point to the start of the received packet
        self.ENC28J60_WriteReg(ENC28J60_ERDPTL, LSB(self._nextPacket))
        self.ENC28J60_WriteReg(ENC28J60_ERDPTH, MSB(self._nextPacket))

        # The packet is preceded by a 6-byte header
        self.ENC28J60_ReadBuffer(self._tmpBytearray6B)

        # Unpack header, little-endian
        headerStruct: tuple = struct.unpack("<HHH", self._tmpBytearray6B)

        # The first two bytes are the address of the next packet
        self._nextPacket = headerStruct[0]

        # Get the length of the received packet
        length: int = headerStruct[1]

        # Get the receive status vector (RSV)
        status: int = headerStruct[2]

        # Make sure no error occurred
        if (status & ENC28J60_RSV_RECEIVED_OK) != 0:
            # Limit the number of data to read
            length = min(length, ENC28J60_ETH_RX_BUFFER_SIZE)
            length = min(length, len(rxBuffer))

            # Read the Ethernet frame
            self.ENC28J60_ReadBuffer(memoryview(rxBuffer)[0:length])
        else:
            # The received packet contains an error
            length = ENC28J60_ETH_RX_ERR_UNSPECIFIED

        # Advance the ERXRDPT pointer, taking care to wrap back at the end of the received memory buffer
        if self._nextPacket == ENC28J60_RX_BUFFER_START:
            self.ENC28J60_WriteReg(ENC28J60_ERXRDPTL, LSB(ENC28J60_RX_BUFFER_STOP))
            self.ENC28J60_WriteReg(ENC28J60_ERXRDPTH, MSB(ENC28J60_RX_BUFFER_STOP))
        else:
            self.ENC28J60_WriteReg(ENC28J60_ERXRDPTL, LSB(self._nextPacket - 1))
            self.ENC28J60_WriteReg(ENC28J60_ERXRDPTH, MSB(self._nextPacket - 1))

        # Decrement the packet counter
        self.ENC28J60_SetBit(ENC28J60_ECON2, ENC28J60_ECON2_PKTDEC)
        return length
