"""
GC9A01 Display Diagnostic Test Script for ESP32-C3 SuperMini (HW-466AB)
Pinout: SCL=GPIO10, SDA=GPIO6, DC=GPIO5, CS=GPIO7, RES=GPIO3
"""

import time
from machine import Pin, SoftSPI, SPI
from gc9a01 import GC9A01, RED, GREEN, BLUE, WHITE, BLACK

def test_display():
    print("==========================================")
    print(" GC9A01 7-Pin Display Test (HW-466AB)     ")
    print("==========================================")
    print("Pins: SCL=GPIO10, SDA=GPIO6, DC=GPIO5, CS=GPIO7, RES=GPIO3")

    try:
        spi = SoftSPI(sck=Pin(10), mosi=Pin(6), miso=Pin(8), baudrate=10000000)
    except Exception as e:
        spi = SPI(1, baudrate=10000000, sck=Pin(10), mosi=Pin(6))

    dc = Pin(5, Pin.OUT)
    cs = Pin(7, Pin.OUT)
    rst = Pin(3, Pin.OUT)

    display = GC9A01(spi, dc=dc, cs=cs, rst=rst, rotation=0)

    print("\n--> Filling Screen RED")
    display.fill(RED)
    time.sleep(2.0)

    print("--> Filling Screen GREEN")
    display.fill(GREEN)
    time.sleep(2.0)

    print("--> Filling Screen BLUE")
    display.fill(BLUE)
    time.sleep(2.0)

    print("--> Filling Screen WHITE")
    display.fill(WHITE)
    time.sleep(2.0)

    print("--> Filling Screen BLACK")
    display.fill(BLACK)

    print("\n==========================================")
    print(" Display Test Complete!                   ")
    print("==========================================")

if __name__ == "__main__":
    test_display()
