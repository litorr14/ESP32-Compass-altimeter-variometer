"""
Complete 32-Register Live Map Scanner for GY-271
Prints all registers from 0x00 to 0x1F to find exactly where the X, Y, Z data channels reside.
"""

import time
from machine import Pin, I2C

def scan_all_registers():
    print("\n============================================================")
    print(" 🔎 32-REGISTER LIVE MAP SCANNER")
    print("============================================================")

    try:
        i2c = I2C(0, sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)
    except Exception:
        from machine import SoftI2C
        i2c = SoftI2C(sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)

    devices = i2c.scan()
    addr = 0x2C if 0x2C in devices else 0x0D

    # Init
    i2c.writeto(addr, bytearray([0x0A, 0x80]))
    time.sleep_ms(20)
    i2c.writeto(addr, bytearray([0x0B, 0x01]))
    time.sleep_ms(10)
    i2c.writeto(addr, bytearray([0x09, 0x1D]))
    i2c.writeto(addr, bytearray([0x0A, 0x1D]))
    time.sleep_ms(30)

    print("👉 ROTATE DEVICE NOW WHILE READINGS ARE TAKEN...\n")

    for sweep in range(6):
        print(f"--- Sweep {sweep+1} ---")
        try:
            regs = i2c.readfrom_mem(addr, 0x00, 32)
            # Print in 2 rows of 16 bytes
            row1 = " ".join([f"{b:02X}" for b in regs[0:16]])
            row2 = " ".join([f"{b:02X}" for b in regs[16:32]])
            print(f"  Regs 0x00-0x0F: [{row1}]")
            print(f"  Regs 0x10-0x1F: [{row2}]\n")
        except Exception as e:
            print("  Read error:", e)
        time.sleep(1.0)

    print("============================================================")

if __name__ == "__main__":
    scan_all_registers()
