"""
QMC6310 Unsigned `<HHH` Midpoint Subtraction Test
Unpacks as `<HHH` (unsigned 16-bit) and subtracts 32768 to eliminate the ±32k zero-crossing wrap.
"""

import time
import math
import ustruct
from machine import Pin, I2C

def test_unsigned():
    print("\n============================================================")
    print(" 🎯 QMC6310 UNSIGNED `<HHH` ZERO-CROSSING TEST")
    print("============================================================")

    try:
        i2c = I2C(0, sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)
    except Exception:
        from machine import SoftI2C
        i2c = SoftI2C(sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)

    devices = i2c.scan()
    addr = 0x2C if 0x2C in devices else 0x0D

    # Continuous Mode (0x0D = ±30G, 200Hz ODR, 512 OSR)
    i2c.writeto(addr, bytearray([0x0A, 0x80]))
    time.sleep_ms(20)
    i2c.writeto(addr, bytearray([0x0B, 0x01]))
    time.sleep_ms(10)
    i2c.writeto(addr, bytearray([0x09, 0x0D]))
    i2c.writeto(addr, bytearray([0x0A, 0x0D]))
    time.sleep_ms(30)

    print("👉 ROTATE DEVICE 360° SLOWLY IN THE AIR...\n")

    min_x, max_x = None, None
    min_y, max_y = None, None
    last_heading = None

    while True:
        try:
            data = i2c.readfrom_mem(addr, 0x00, 6)
            ux, uy, uz = ustruct.unpack("<HHH", data)
            i2c.readfrom_mem(addr, 0x06, 1)
        except Exception:
            time.sleep_ms(20)
            continue

        # Convert unsigned 16-bit (centered at 32768) to signed centered coordinate
        x = ux - 32768
        y = uy - 32768
        z = uz - 32768

        if min_x is None:
            min_x, max_x = x, x
            min_y, max_y = y, y
        else:
            if x < min_x: min_x = x
            if x > max_x: max_x = x
            if y < min_y: min_y = y
            if y > max_y: max_y = y

        x_center = (max_x + min_x) / 2.0
        y_center = (max_y + min_y) / 2.0

        cx = x - x_center
        cy = y - y_center

        heading = (math.degrees(math.atan2(cy, cx))) % 360.0

        jump_str = ""
        if last_heading is not None:
            diff = abs((heading - last_heading + 180.0) % 360.0 - 180.0)
            if diff > 40.0:
                jump_str = f"⚠️ JUMP! (Δ={diff:.1f}°)"

        last_heading = heading

        # Visual compass needle bar (16 sectors)
        sector = int((heading / 360.0) * 16) % 16
        bar = ["·"] * 16
        bar[sector] = "▶"
        needle_str = "".join(bar)

        print(f"X:{x:6d} Y:{y:6d} | cx:{cx:6.0f} cy:{cy:6.0f} | Angle:{heading:5.1f}° [{needle_str}] {jump_str}")
        time.sleep_ms(100)

if __name__ == "__main__":
    test_unsigned()
