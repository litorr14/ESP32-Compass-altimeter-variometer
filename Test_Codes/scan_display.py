"""
GC9A01 Display Pin Combination Scanner for ESP32-C3 SuperMini.
Cycles through candidate SPI pin configurations to find the working wiring.
"""

import time
from machine import Pin, SoftSPI
from gc9a01 import GC9A01, RED, GREEN, BLUE, WHITE, BLACK

# Candidate Pin Configurations: (SCK, MOSI, DC, CS, RST, Name)
PIN_CONFIGS = [
    (10, 6, 4, 7, 3, "Config 1: SCK=10, MOSI=6, DC=4, CS=7, RST=3 (Original C++)"),
    (6, 10, 4, 7, 3, "Config 2: SCK=6, MOSI=10, DC=4, CS=7, RST=3 (Swapped SCK/MOSI)"),
    (4, 6, 10, 7, 3, "Config 3: SCK=4, MOSI=6, DC=10, CS=7, RST=3 (Hardware Default SPI)"),
    (10, 6, 3, 7, 4, "Config 4: SCK=10, MOSI=6, DC=3, CS=7, RST=4 (Swapped DC/RST)"),
    (10, 6, 4, 3, 7, "Config 5: SCK=10, MOSI=6, DC=4, CS=3, RST=7 (Swapped CS/RST)"),
    (8, 10, 4, 7, 3, "Config 6: SCK=8, MOSI=10, DC=4, CS=7, RST=3"),
]

def scan_pins():
    print("==================================================")
    print("  GC9A01 Display Pin Combination Scanner          ")
    print("==================================================")
    print("Watch your circular display! Each test fills screen RED.\n")

    for idx, (sck, mosi, dc_pin, cs_pin, rst_pin, name) in enumerate(PIN_CONFIGS, 1):
        print(f"[{idx}/{len(PIN_CONFIGS)}] Testing {name}...")
        try:
            spi = SoftSPI(sck=Pin(sck), mosi=Pin(mosi), miso=Pin(5), baudrate=10000000)
            dc = Pin(dc_pin, Pin.OUT)
            cs = Pin(cs_pin, Pin.OUT)
            rst = Pin(rst_pin, Pin.OUT)

            display = GC9A01(spi, dc=dc, cs=cs, rst=rst, rotation=0)

            # Fill screen RED to visually test if display lights up
            display.fill(RED)
            time.sleep(1.5)

            # Clear screen BLACK before next test
            display.fill(BLACK)
            time.sleep(0.5)

        except Exception as e:
            print(f"    --> Error with configuration: {e}")

    print("\n==================================================")
    print(" Scan Finished! If one of the tests turned RED,   ")
    print(" note its Config number and tell us below.       ")
    print("==================================================")

if __name__ == "__main__":
    scan_pins()
