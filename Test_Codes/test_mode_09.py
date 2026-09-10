"""
QMC5883P Mode 0x09 & 0x01 Test Script for MicroPython
Tests Continuous Mode (2G Range, 100Hz ODR) without 8G bit 0x10.
"""

import time
import math
import ustruct
from machine import Pin, I2C

def test_mode_09():
    print("==========================================")
    print(" QMC5883P Mode 0x09 (Continuous 2G) Test  ")
    print("==========================================")

    try:
        i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100000)
    except Exception:
        from machine import SoftI2C
        i2c = SoftI2C(sda=Pin(0), scl=Pin(1), freq=100000)

    addr = 0x2C

    # Reset sequence
    i2c.writeto(addr, b"\x0A\x80")
    time.sleep_ms(20)
    i2c.writeto(addr, b"\x0A\x00")
    time.sleep_ms(20)
    i2c.writeto(addr, b"\x0B\x01")
    time.sleep_ms(10)

    # Write 0x09 to Reg 0x09 (Continuous 100Hz 2G mode)
    print("Writing 0x09 to Reg 0x09 (Continuous Mode 100Hz)...")
    i2c.writeto(addr, b"\x09\x09")
    time.sleep_ms(30)

    reg9 = i2c.readfrom_mem(addr, 0x09, 1)[0]
    print(f"Reg 0x09 Readback: 0x{reg9:02X}")

    if reg9 == 0x09 or reg9 == 0x0D or reg9 == 0x01:
        print("🎉 SUCCESS! Mode accepted! Reading live vector data:\n")
    else:
        print("Writing 0x01 (Continuous 10Hz)...")
        i2c.writeto(addr, b"\x09\x01")
        time.sleep_ms(30)

    print("-" * 50)
    for i in range(25):
        data = i2c.readfrom_mem(addr, 0x00, 6)
        x, y, z = ustruct.unpack("<hhh", data)
        heading = (math.degrees(math.atan2(-y, x))) % 360
        print(f"[{i+1:02d}] Raw X: {x:6d} | Raw Y: {y:6d} | Raw Z: {z:6d} | Heading: {heading:5.1f}°")
        time.sleep(0.3)

    print("-" * 50)
    print("Test Complete!")

if __name__ == "__main__":
    test_mode_09()
