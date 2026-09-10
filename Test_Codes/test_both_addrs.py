"""
Dual-Address QMC5883L / QMC5883P Diagnostic Test Script
Tests address 0x0D and 0x2C to find which address outputs live magnetic data.
"""

import time
import math
import ustruct
from machine import Pin, I2C

def test_both():
    print("==========================================")
    print(" Dual-Address QMC5883 Scanner & Tester    ")
    print("==========================================")

    try:
        i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100000)
    except Exception:
        from machine import SoftI2C
        i2c = SoftI2C(sda=Pin(0), scl=Pin(1), freq=100000)

    devices = i2c.scan()
    print("Scanned I2C Bus Devices:", [hex(d) for d in devices])

    candidates = [addr for addr in (0x0D, 0x2C) if addr in devices]
    if not candidates:
        candidates = devices

    if not candidates:
        print("ERROR: No I2C devices found!")
        return

    for addr in candidates:
        print(f"\n---> Testing I2C Address 0x{addr:02X} <---")

        # Soft reset
        try:
            i2c.writeto(addr, bytearray([0x0A, 0x80]))
            time.sleep_ms(20)
            i2c.writeto(addr, bytearray([0x0A, 0x00]))
            time.sleep_ms(20)
        except Exception:
            pass

        # Set/Reset period
        try:
            i2c.writeto(addr, bytearray([0x0B, 0x01]))
            time.sleep_ms(10)
        except Exception:
            pass

        # Mode Continuous (0x1D for QMC5883L, 0x0D for QMC5883P)
        for mode_val in (0x1D, 0x0D, 0x09, 0x01):
            try:
                i2c.writeto(addr, bytearray([0x09, mode_val]))
                time.sleep_ms(20)
                read9 = i2c.readfrom_mem(addr, 0x09, 1)[0]
                if read9 != 0x00 and read9 != 0x18:
                    print(f"  Mode 0x{mode_val:02X} accepted -> Reg 0x09 readback: 0x{read9:02X}")
                    break
            except Exception:
                pass

        print("Reading 10 magnetic vectors...")
        live_found = False
        for i in range(10):
            try:
                data = i2c.readfrom_mem(addr, 0x00, 6)
                x, y, z = ustruct.unpack("<hhh", data)
                heading = (math.degrees(math.atan2(-y, x))) % 360
                print(f"  [{i+1:02d}] X:{x:6d} | Y:{y:6d} | Z:{z:6d} | Heading:{heading:5.1f}°")
                if not (x == 128 and y == 0 and z == 0) and not (x == 0 and y == 0 and z == 0):
                    live_found = True
            except Exception as e:
                print("  Read error:", e)
            time.sleep(0.3)

        if live_found:
            print(f"🎉 SUCCESS! Address 0x{addr:02X} is giving LIVE changing readings!")

    print("\n==========================================")

if __name__ == "__main__":
    test_both()
