"""
GC9A01 SPI Mode and Frequency Scanner for ESP32-C3 SuperMini.
Tests SPI Modes 0, 1, 2, 3 and clock speeds (1MHz, 5MHz, 10MHz) to find the exact hardware match.
"""

import time
from machine import Pin, SoftSPI
from gc9a01 import GC9A01, RED, GREEN, BLUE, WHITE, BLACK

SPI_MODES = [
    (0, 0, "SPI Mode 0 (Polarity=0, Phase=0)"),
    (0, 1, "SPI Mode 1 (Polarity=0, Phase=1)"),
    (1, 0, "SPI Mode 2 (Polarity=1, Phase=0)"),
    (1, 1, "SPI Mode 3 (Polarity=1, Phase=1)"),
]

SPEEDS = [1000000, 5000000, 10000000]

def test_spi_modes():
    print("==================================================")
    print("  GC9A01 SPI Mode & Frequency Diagnostic Test     ")
    print("==================================================")
    print("Pinout: SCL=GPIO10, SDA=GPIO6, DC=GPIO4, CS=GPIO7, RES=GPIO3\n")

    dc = Pin(4, Pin.OUT)
    cs = Pin(7, Pin.OUT)
    rst = Pin(3, Pin.OUT)

    for pol, pha, name in SPI_MODES:
        for speed in SPEEDS:
            speed_mhz = speed // 1000000
            print(f"Testing {name} @ {speed_mhz}MHz...")

            try:
                spi = SoftSPI(
                    sck=Pin(10),
                    mosi=Pin(6),
                    miso=Pin(5),
                    baudrate=speed,
                    polarity=pol,
                    phase=pha
                )

                display = GC9A01(spi, dc=dc, cs=cs, rst=rst, rotation=0)

                # Send bright RED fill
                display.fill(RED)
                time.sleep(1.2)

                # Send bright GREEN fill
                display.fill(GREEN)
                time.sleep(1.2)

                display.fill(BLACK)
                time.sleep(0.3)

            except Exception as e:
                print(f"    --> Error testing {name}: {e}")

    print("\n==================================================")
    print(" Diagnostic Test Complete!                       ")
    print("==================================================")

if __name__ == "__main__":
    test_spi_modes()
