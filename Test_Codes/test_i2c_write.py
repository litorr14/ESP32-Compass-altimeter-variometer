"""
I2C Direct Register Write Test for QMC5883P (Address 0x2C)
Tests single-buffer writeto vs writeto_mem to verify register acceptance.
"""

import time
import ustruct
from machine import Pin, I2C

def test_write():
    print("==========================================")
    print(" QMC5883P Direct I2C Write Diagnostic     ")
    print("==========================================")

    try:
        i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100000)
    except Exception:
        from machine import SoftI2C
        i2c = SoftI2C(sda=Pin(0), scl=Pin(1), freq=100000)

    devices = i2c.scan()
    print("Devices on bus:", [hex(d) for d in devices])

    if 0x2C not in devices:
        print("ERROR: Address 0x2C not found on I2C bus!")
        return

    addr = 0x2C

    # Read Reg 0x09 before write
    reg9_before = i2c.readfrom_mem(addr, 0x09, 1)[0]
    print(f"Reg 0x09 before write: 0x{reg9_before:02X}")

    # Method 1: Single-buffer writeto b"\x09\x19"
    print("\n--> Testing Method 1: i2c.writeto(0x2C, b'\\x09\\x19')...")
    i2c.writeto(addr, b"\x0B\x01") # Set/Reset Period
    time.sleep_ms(10)

    i2c.writeto(addr, b"\x09\x19") # Mode 100Hz 8G Continuous
    time.sleep_ms(20)

    reg9_after1 = i2c.readfrom_mem(addr, 0x09, 1)[0]
    print(f"Reg 0x09 after Method 1 write: 0x{reg9_after1:02X}")

    if reg9_after1 == 0x19:
        print("🎉 SUCCESS! Register 0x09 accepted 0x19 continuous mode!")

    # Read raw readings
    time.sleep_ms(50)
    data = i2c.readfrom_mem(addr, 0x00, 6)
    x, y, z = ustruct.unpack("<hhh", data)
    print(f"Raw Reading -> X:{x}, Y:{y}, Z:{z}")

    print("==========================================")

if __name__ == "__main__":
    test_write()
