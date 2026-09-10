"""
QMC6310 / QMC5883 Detailed Axis Diagnostic & Register Configurator
Run this script to unlock the X-axis and observe raw bytes of all 3 channels.
"""

import time
import math
import ustruct
from machine import Pin, I2C

def run_diagnostics():
    print("\n============================================================")
    print(" 🔬 QMC AXIS UNLOCK & REGISTER DIAGNOSTIC TOOL")
    print("============================================================")

    try:
        i2c = I2C(0, sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)
    except Exception:
        from machine import SoftI2C
        i2c = SoftI2C(sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)

    devices = i2c.scan()
    print(f"📡 I2C Scan Found Devices: {[hex(d) for d in devices]}")

    if 0x2C not in devices and 0x0D not in devices:
        print("❌ Magnetometer not detected on I2C bus!")
        return

    addr = 0x2C if 0x2C in devices else 0x0D
    print(f"🎯 Testing Magnetometer at address: 0x{addr:02X}\n")

    # Step 1: Dump initial register state
    print("--- 1. Initial Register State (0x00 to 0x0F) ---")
    try:
        initial_regs = i2c.readfrom_mem(addr, 0x00, 16)
        for idx, val in enumerate(initial_regs):
            print(f"  Reg 0x{idx:02X} : 0x{val:02X} ({val:3d})")
    except Exception as e:
        print(f"  Failed to read initial registers: {e}")

    # Step 2: Test different register configurations to find which unlocks X-axis
    configs = [
        {"name": "Config A: Reg09=0x19 (200Hz, 8G), Reg0A=0x00 (All axes ON)", "r9": 0x19, "rA": 0x00, "rB": 0x01},
        {"name": "Config B: Reg09=0x1D (200Hz, 8G, 512OSR), Reg0A=0x00 (All axes ON)", "r9": 0x1D, "rA": 0x00, "rB": 0x01},
        {"name": "Config C: Reg09=0x09 (100Hz, 2G), Reg0A=0x00 (All axes ON)", "r9": 0x09, "rA": 0x00, "rB": 0x01},
        {"name": "Config D: Reg09=0x19, Reg0A=0x19 (Dual Mode)", "r9": 0x19, "rA": 0x19, "rB": 0x01},
        {"name": "Config E: Reg09=0x1D, Reg0A=0x1D (Previous Mode)", "r9": 0x1D, "rA": 0x1D, "rB": 0x01},
    ]

    for cfg in configs:
        print(f"\n---> Testing {cfg['name']} <---")
        try:
            # Soft reset
            i2c.writeto(addr, bytearray([0x0A, 0x80]))
            time.sleep_ms(20)
            
            # Set Period
            i2c.writeto(addr, bytearray([0x0B, cfg['rB']]))
            time.sleep_ms(10)
            
            # Write Reg 0x09 and Reg 0x0A
            i2c.writeto(addr, bytearray([0x09, cfg['r9']]))
            time.sleep_ms(10)
            i2c.writeto(addr, bytearray([0x0A, cfg['rA']]))
            time.sleep_ms(30)

            # Read back
            r9 = i2c.readfrom_mem(addr, 0x09, 1)[0]
            rA = i2c.readfrom_mem(addr, 0x0A, 1)[0]
            print(f"  Readback: Reg 0x09 = 0x{r9:02X} | Reg 0x0A = 0x{rA:02X}")

            # Read 5 samples
            for s in range(5):
                raw_bytes = i2c.readfrom_mem(addr, 0x00, 6)
                x, y, z = ustruct.unpack("<hhh", raw_bytes)
                hex_str = " ".join([f"{b:02X}" for b in raw_bytes])
                print(f"    Sample {s+1}: RawBytes=[{hex_str}] -> X:{x:6d}, Y:{y:6d}, Z:{z:6d}")
                time.sleep_ms(100)

        except Exception as err:
            print(f"  Error testing config: {err}")

    print("\n============================================================")
    print(" Diagnostic Complete! Check which config gave non-frozen X.")
    print("============================================================")

if __name__ == "__main__":
    run_diagnostics()
