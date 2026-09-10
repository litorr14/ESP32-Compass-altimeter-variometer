"""
Live X-Axis Desaturation Monitor
Watch Reg 0x00 and 0x01 in real-time as you:
1. Lift the breadboard 30 cm up into the air (away from table/multimeter/tools).
2. Unplug the black buzzer.
"""

import time
import ustruct
from machine import Pin, I2C

def monitor_x():
    print("\n============================================================")
    print(" 📡 LIVE X-AXIS DESATURATION MONITOR")
    print("============================================================")

    try:
        i2c = I2C(0, sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)
    except Exception:
        from machine import SoftI2C
        i2c = SoftI2C(sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)

    devices = i2c.scan()
    addr = 0x2C if 0x2C in devices else 0x0D

    # Continuous Mode
    i2c.writeto(addr, bytearray([0x0A, 0x80]))
    time.sleep_ms(20)
    i2c.writeto(addr, bytearray([0x0B, 0x01]))
    time.sleep_ms(10)
    i2c.writeto(addr, bytearray([0x09, 0x1D]))
    i2c.writeto(addr, bytearray([0x0A, 0x1D]))
    time.sleep_ms(30)

    print("👉 LIFT THE BREADBOARD UP IN THE AIR (AWAY FROM TABLE / MULTIMETER)...")
    print("   Press Ctrl+C to stop.\n")

    try:
        while True:
            regs = i2c.readfrom_mem(addr, 0x00, 7)
            x_byte0 = regs[0]
            x_byte1 = regs[1]
            status  = regs[6]

            # Unpack full 16-bit
            x, y, z = ustruct.unpack("<hhh", regs[0:6])

            is_saturated = (x_byte0 == 0x80 and x_byte1 == 0xFF) or ((status & 0x10) != 0)
            sat_flag = "⚠️ SATURATED (0x80FF)" if is_saturated else "✅ ACTIVE / UNLOCKED!"

            print(f"X_Bytes: [{x_byte0:02X} {x_byte1:02X}] -> X: {x:6d} | Y: {y:6d} | Z: {z:6d} | Status: 0x{status:02X} | {sat_flag}")
            time.sleep_ms(200)

    except KeyboardInterrupt:
        print("\nMonitor stopped.")

if __name__ == "__main__":
    monitor_x()
