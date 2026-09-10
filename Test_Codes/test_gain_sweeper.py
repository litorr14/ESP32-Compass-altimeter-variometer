"""
QMC6310 Dynamic Range & Gain Scaler Test
Tests all 4 Range options (Reg09 bits 5:4 = 00, 01, 10, 11) to find the non-overflowing range
where vector magnitude is well within safe bounds (1,000 - 8,000 units instead of 32,000).
"""

import time
import math
import ustruct
from machine import Pin, I2C

def test_gain():
    print("\n============================================================")
    print(" 🎚️ QMC6310 DYNAMIC RANGE / GAIN SWEEPER")
    print("============================================================")

    try:
        i2c = I2C(0, sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)
    except Exception:
        from machine import SoftI2C
        i2c = SoftI2C(sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)

    devices = i2c.scan()
    addr = 0x2C if 0x2C in devices else 0x0D

    # 4 Range candidates for Reg 0x09 (bits 5:4):
    # RNG=00 (0x01 / 0x05 / 0x0D) -> ±30 Gauss (safest from overflow)
    # RNG=01 (0x11 / 0x15 / 0x1D) -> ±12 Gauss
    # RNG=10 (0x21 / 0x25 / 0x2D) -> ±8 Gauss
    # RNG=11 (0x31 / 0x35 / 0x3D) -> ±2 Gauss
    
    range_candidates = [
        ("Range 00 (±30G / 0x01)", 0x01),
        ("Range 00 (±30G / 0x05)", 0x05),
        ("Range 00 (±30G / 0x0D)", 0x0D),
        ("Range 01 (±12G / 0x11)", 0x11),
        ("Range 01 (±12G / 0x15)", 0x15),
        ("Range 10 (±8G  / 0x21)", 0x21),
        ("Range 10 (±8G  / 0x25)", 0x25),
    ]

    for label, val in range_candidates:
        print(f"\n---> Testing {label} <---")
        try:
            # Soft reset
            i2c.writeto(addr, bytearray([0x0A, 0x80]))
            time.sleep_ms(15)
            i2c.writeto(addr, bytearray([0x0B, 0x01]))
            time.sleep_ms(10)
            
            i2c.writeto(addr, bytearray([0x09, val]))
            i2c.writeto(addr, bytearray([0x0A, val]))
            time.sleep_ms(25)

            # Read 6 samples
            for s in range(6):
                data = i2c.readfrom_mem(addr, 0x00, 6)
                x, y, z = ustruct.unpack("<hhh", data)
                i2c.readfrom_mem(addr, 0x06, 1)
                
                mag = math.sqrt(x*x + y*y)
                is_overflow = abs(x) > 31000 or abs(y) > 31000
                flag = "❌ OVERFLOW (>31k)" if is_overflow else "✅ SAFE / SMOOTH"
                
                print(f"  Sample {s+1}: X={x:6d} | Y={y:6d} | Mag={mag:6.0f} | {flag}")
                time.sleep_ms(120)

        except Exception as e:
            print(f"  Error: {e}")

    print("\n============================================================")

if __name__ == "__main__":
    test_gain()
