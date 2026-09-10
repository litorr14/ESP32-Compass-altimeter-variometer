"""
SMOOTH CLOCKWISE AVIATION COMPASS WITH 127° NORTH ALIGNMENT
Filters raw (mx, my) vector to eliminate all spikes and aligns North to 0°.
"""

import time
import math
import ustruct
from machine import Pin, I2C

def test():
    print("\n============================================================")
    print(" 🧭 SMOOTH NORTH-ALIGNED AVIATION COMPASS (0° = NORTH)")
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

    # Calibration parameters
    Xoffset = 3384.0
    Yoffset = -985.0
    Xscale  = 1.055
    Yscale  = 1.000
    NORTH_ALIGN_OFFSET = -4.0  # Offsets raw reading to true 0.0° North

    # Low-pass filter state
    sm_mx = 0.0
    sm_my = 0.0
    first = True

    print("👉 POINT BOARD NORTH TO VERIFY 0.0°, THEN ROTATE CLOCKWISE...\n")

    while True:
        try:
            data = i2c.readfrom_mem(addr, 0x01, 6)
            rx, ry, rz = ustruct.unpack("<hhh", data)
            i2c.readfrom_mem(addr, 0x09, 1)
        except Exception:
            time.sleep_ms(20)
            continue

        # 1. Hard-Iron & Soft-Iron correction
        mx = (float(rx) - Xoffset) * Xscale
        my = (float(ry) - Yoffset) * Yscale

        # 2. Vector Low-Pass Filter (eliminates noise spikes before atan2)
        if first:
            sm_mx = mx
            sm_my = my
            first = False
        else:
            sm_mx += 0.25 * (mx - sm_mx)
            sm_my += 0.25 * (my - sm_my)

        # 3. Clockwise Aviation Compass Heading
        raw_angle = math.degrees(math.atan2(sm_my, sm_mx))
        heading = (-raw_angle + NORTH_ALIGN_OFFSET) % 360.0

        # Cardinal Direction
        cardinals = ["N ", "NE", "E ", "SE", "S ", "SW", "W ", "NW"]
        cardinal = cardinals[int(((heading + 22.5) % 360.0) / 45.0)]

        # 16-segment visual needle bar
        sector = int((heading / 360.0) * 16) % 16
        bar = ["·"] * 16
        bar[sector] = "▶"
        needle_str = "".join(bar)

        print(f"Heading: {heading:5.1f}° [{cardinal}] [{needle_str}] (Raw: mx={sm_mx:5.0f}, my={sm_my:5.0f})")
        time.sleep_ms(80)

if __name__ == "__main__":
    test()
