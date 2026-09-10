"""
QMC6310 RAW BYTES & ZERO-CROSSING PROOF
Run this in Thonny to verify that the 180-degree jumps are completely gone.
"""

import time
import math
import ustruct
from machine import Pin, I2C

def test():
    print("\n============================================================")
    print(" 🧭 QMC6310 CONTINUOUS SMOOTH 360° ROTATION CHECK")
    print("============================================================")

    try:
        i2c = I2C(0, sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)
    except Exception:
        from machine import SoftI2C
        i2c = SoftI2C(sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)

    devices = i2c.scan()
    addr = 0x2C if 0x2C in devices else 0x0D

    # 1. Reset
    i2c.writeto(addr, bytearray([0x0A, 0x80]))
    time.sleep_ms(20)
    i2c.writeto(addr, bytearray([0x0B, 0x01]))
    time.sleep_ms(10)
    # 2. Continuous Mode (0x0D = ±30G, 200Hz ODR, 512 OSR)
    i2c.writeto(addr, bytearray([0x09, 0x0D]))
    i2c.writeto(addr, bytearray([0x0A, 0x0D]))
    time.sleep_ms(30)

    print("👉 ROTATE DEVICE 360° SLOWLY IN THE AIR (AWAY FROM BUZZER/DESK)...\n")

    # Initial reasonable bounds
    min_x, max_x = -3000, 3000
    min_y, max_y = -3000, 3000
    last_heading = None

    while True:
        try:
            data = i2c.readfrom_mem(addr, 0x00, 6)
            ux, uy, uz = ustruct.unpack("<HHH", data)
            # Release latch
            i2c.readfrom_mem(addr, 0x06, 1)
        except Exception as e:
            time.sleep_ms(20)
            continue

        # Zero-centered coordinates (0x8000 = 32768 is magnetic 0)
        x = ux - 32768
        y = uy - 32768
        z = uz - 32768

        # Track min/max
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
            if diff > 45.0:
                jump_str = f"⚠️ JUMP! (Δ={diff:.1f}°)"

        last_heading = heading

        # Compass needle visualization
        sector = int((heading / 360.0) * 16) % 16
        bar = ["·"] * 16
        bar[sector] = "▶"
        needle_str = "".join(bar)

        print(f"X:{x:6d} Y:{y:6d} | cx:{cx:6.0f} cy:{cy:6.0f} | Angle:{heading:5.1f}° [{needle_str}] {jump_str}")
        time.sleep_ms(80)

if __name__ == "__main__":
    test()
