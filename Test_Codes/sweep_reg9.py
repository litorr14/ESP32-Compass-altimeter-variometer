"""
QMC5883P Register Writer & Unlock Sweeper for MicroPython
Tests all write methods and register byte patterns on address 0x2C to unlock continuous sampling.
"""

import time
import ustruct
from machine import Pin, I2C

def sweep_registers():
    print("==========================================")
    print(" QMC5883P Register Unlock & Byte Sweeper  ")
    print("==========================================")

    try:
        i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100000)
    except Exception:
        from machine import SoftI2C
        i2c = SoftI2C(sda=Pin(0), scl=Pin(1), freq=100000)

    addr = 0x2C

    print("\n1. Testing Soft Reset sequence combinations on 0x0A / 0x0B...")
    for reset_val in [0x80, 0x01, 0x00]:
        try:
            i2c.writeto(addr, bytearray([0x0A, reset_val]))
            time.sleep_ms(10)
        except Exception:
            pass

    # Try setting Set/Reset period (Reg 0x0B)
    for sr_val in [0x01, 0x00, 0x80]:
        try:
            i2c.writeto(addr, bytearray([0x0B, sr_val]))
            time.sleep_ms(10)
        except Exception:
            pass

    print("\n2. Sweeping candidate control bytes for Register 0x09...")
    accepted_values = []
    
    test_bytes = [
        0x01, 0x05, 0x09, 0x0D, 0x11, 0x15, 0x19, 0x1D,
        0x21, 0x25, 0x29, 0x2D, 0x41, 0x49, 0x51, 0x81,
        0x89, 0x9D, 0x00, 0x02, 0x04, 0x08, 0x10, 0x20
    ]

    for val in test_bytes:
        try:
            i2c.writeto(addr, bytearray([0x09, val]))
            time.sleep_ms(10)
            readback = i2c.readfrom_mem(addr, 0x09, 1)[0]
            if readback == val:
                print(f"  --> SUCCESS! Reg 0x09 accepted byte 0x{val:02X}")
                accepted_values.append(val)
        except Exception:
            pass

    if not accepted_values:
        print("  --> Reg 0x09 did not accept standard QMC byte values.")
        print("\n3. Testing HMC5883L style registers (Reg 0x00, 0x01, 0x02)...")
        try:
            i2c.writeto(addr, bytearray([0x00, 0x70]))
            i2c.writeto(addr, bytearray([0x01, 0x20]))
            i2c.writeto(addr, bytearray([0x02, 0x00]))
            time.sleep_ms(30)
            
            data = i2c.readfrom_mem(addr, 0x03, 6)
            x, z, y = ustruct.unpack(">hhh", data)
            print(f"  --> HMC Read result: X:{x}, Y:{y}, Z:{z}")
        except Exception as e:
            print("  --> HMC test error:", e)
    else:
        print(f"\nAccepted values for Reg 0x09: {[hex(v) for v in accepted_values]}")
        # Test reading data using first accepted value
        active_val = accepted_values[0]
        i2c.writeto(addr, bytearray([0x09, active_val]))
        time.sleep_ms(50)
        data = i2c.readfrom_mem(addr, 0x00, 6)
        x, y, z = ustruct.unpack("<hhh", data)
        print(f"  --> Live Data with 0x{active_val:02X} -> X:{x}, Y:{y}, Z:{z}")

    print("\n==========================================")

if __name__ == "__main__":
    sweep_registers()
