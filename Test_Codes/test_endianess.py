"""
Endianness & Endian-Independent Angle Test
Tests Big-Endian (>hhh) vs Little-Endian (<hhh) simultaneously while rotating 360°.
"""

import time
import math
import ustruct
from machine import Pin, I2C

def test():
    print("\n============================================================")
    print(" 🧭 BIG-ENDIAN (>hhh) VS LITTLE-ENDIAN (<hhh) REAL-TIME TEST")
    print("============================================================")

    try:
        i2c = I2C(0, sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)
    except Exception:
        from machine import SoftI2C
        i2c = SoftI2C(sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)

    devices = i2c.scan()
    addr = 0x2C if 0x2C in devices else 0x0D

    # Init continuous mode
    i2c.writeto(addr, bytearray([0x0A, 0x80]))
    time.sleep_ms(20)
    i2c.writeto(addr, bytearray([0x0B, 0x01]))
    time.sleep_ms(10)
    i2c.writeto(addr, bytearray([0x09, 0x0D]))
    i2c.writeto(addr, bytearray([0x0A, 0x0D]))
    time.sleep_ms(30)

    print("👉 ROTATE DEVICE 360° SLOWLY IN THE AIR...\n")

    min_bx, max_bx = None, None
    min_by, max_by = None, None
    last_heading = None

    while True:
        try:
            data = i2c.readfrom_mem(addr, 0x00, 6)
            # Big-Endian unpack (>hhh)
            bx, by, bz = ustruct.unpack(">hhh", data)
            # Little-Endian unpack (<hhh)
            lx, ly, lz = ustruct.unpack("<hhh", data)
            # Unlatch
            i2c.readfrom_mem(addr, 0x06, 1)
        except Exception:
            time.sleep_ms(20)
            continue

        if min_bx is None:
            min_bx, max_bx = bx, bx
            min_by, max_by = by, by
        else:
            if bx < min_bx: min_bx = bx
            if bx > max_bx: max_bx = bx
            if by < min_by: min_by = by
            if by > max_by: max_by = by

        cx = bx - (max_bx + min_bx) / 2.0
        cy = by - (max_by + min_by) / 2.0

        heading = (math.degrees(math.atan2(cy, cx))) % 360.0

        jump_str = ""
        if last_heading is not None:
            diff = abs((heading - last_heading + 180.0) % 360.0 - 180.0)
            if diff > 40.0:
                jump_str = f"⚠️ JUMP! (Δ={diff:.1f}°)"

        last_heading = heading

        sector = int((heading / 360.0) * 16) % 16
        bar = ["·"] * 16
        bar[sector] = "▶"
        needle_str = "".join(bar)

        raw_hex = " ".join([f"{b:02X}" for b in data])
        print(f"Bytes:[{raw_hex}] | Big-E: X:{bx:6d} Y:{by:6d} | Angle:{heading:5.1f}° [{needle_str}] {jump_str}")
        time.sleep_ms(100)

if __name__ == "__main__":
    test()
