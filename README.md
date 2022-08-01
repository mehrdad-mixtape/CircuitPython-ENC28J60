# CircuitPython-ENC28J60:
ENC28J60 Ethernet chip driver for CircuitPython 7.2 (RP2)

## Rationale:
ENC28J60 is a popular and cheap module for DIY projects.
At the moment, however, there is no driver for the MicroPython environment.
The Python implementation seems easy for further improvements and self adaptation.

## Installation:
1. Go to `CircuitPython-ENC28J60/CircuitPython_version/`
	- Copy all .py files to CURCUITPY
	- Copy dir *adafruit_bus_device* to CURCUITPY/lib/
2. Go to `CircuitPython-ENC28J60/`
	- Run udp_server.py
3. Check your connections and wiring
4. Your system and pico must be in same network!
5. Default Addresses:
	- udp_server.py: IP=192.168.1.200 PORT=5000
		- You can change the Address in udp_server.py file
		```python
		if __name__ == '__main__':
			try:
				main('192.168.1.200', port=5000, ack=True)
		    except KeyboardInterrupt:
				if system() == 'Windows': run(['cls'])
		        elif system() == 'Linux': run(['clear'])
				kill(pid, SIGTERM)

		```
	- pico: IP=192.168.1.198 PORT=6000 GATEWAY=192.168.1.1
		- You can change the Address in conf.py file
		```python
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
		```

## Wiring:
Wiring requires pins for SPI: SCK, MISO, MOSI and ChipSelect and optionally Interrupt.
Example wiring that uses SPI1 bus (any SPI bus can be used):

| ENC28J60 Module | RP2040 Board | Notes |
| :-------------: |:-------------:| ---- |
| VCC | 3V3 | requires up to 180 mA |
| GND | GND | |
| SCK | GP10 | SPI1 SCK |
| MOSI | GP11 | SPI1 MOSI/TX |
| MISO | GP12 | SPI1 MISO/RX |
| CS | GP13 | SPI1 CSn |

## main.py:
### Trasmit and Receive UDP packets:

```python
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
            ethernet.tx_udp(f"id>>I'm Pico"); break
    ethernet.send_request(which='ntp') # request localtime
    ethernet.date_and_time()

    start: int = time()
    threshold: int = 0

    while True:
        if ethernet.kill_switch_stat:
            # Ready for ARP, ICMP, IP, UDP, ... ---------------------------------------------
            ethernet.rx_udp()
            # Threshold: ---------------------------------------------
            threshold = time() - start
            print(f"Threshold is {threshold}")
            print(f"Server is {'Alive' if ethernet.is_server_alive else 'Dead'}")
            print(f"UDP_Q={ethernet.udp_q_stat}")
            ethernet.date_and_time()
            if threshold % 10 == 0: # send random udp packet
                ethernet.tx_udp(choice(['msg>>Hello Pico', 'MixTape', 'ENC28J60 with CircuitPython']))
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
            ethernet.tx_udp('Critical DOS Attack!')
            ethernet.cool_down(timer=30, msg='UnderDOSAttack', op='CoolDown')
            collect() # free up memory space
            start = time()

if __name__ == '__main__':
    main()
```
# Test:

## First Interview:
![alt text](https://github.com/mehrdad-mixtape/CircuitPython-ENC28J60/blob/main/Images/img1.jpg)
- `Server is Alive`
- After successfully connecting with **udp_server.py**, pico sends `req>>time` to **udp_server.py** and updates the date and time itself.
- Pico tries to sends a random message to the server every 10 seconds and **udp_server.py** sends `ack>>pk` to pico

## Try Ping Pico:
![alt text](https://github.com/mehrdad-mixtape/CircuitPython-ENC28J60/blob/main/Images/img2.jpg)

## Try DoS Attack to Pico with hping3:
![alt text](https://github.com/mehrdad-mixtape/CircuitPython-ENC28J60/blob/main/Images/img3.jpg)
- *$ sudo hping3 -2 -c 10000 --flood 192.168.1.198*
- Dos config for UDP limit is **150** packet.

## Kill udp_server.py:
![alt text](https://github.com/mehrdad-mixtape/CircuitPython-ENC28J60/blob/main/Images/img4.jpg)
- When you killed **udp_server.py**, pico sends `req>>alive` to **udp_server.py** after few seconds. if **udp_server.py** can't sends `alive>>yes` to pico, pico changes the **udp_server.py** status to `Server is Dead`.
