"""
Magnetometer Register Dump Diagnostic Tool for MicroPython
Reads and prints registers 0x00 through 0x0F to inspect sensor state.
"""

import time
from machine import Pin, I2C

def dump_sensor():
    print("==========================================")
    print(" Magnetometer Register Dump Diagnostic   ")
    print("==========================================")

    try:
        i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100000)
    except Exception:
        from machine import SoftI2C
        i2c = SoftI2C(sda=Pin(0), scl=Pin(1), freq=100000)

    devices = i2c.scan()
    print(f"Scanned I2C Bus: {[hex(d) for d in devices]}\n")

    if not devices:
        print("ERROR: No device on I2C bus! Check SDA/SCL wiring and 3.3V power.")
        return

    addr = devices[0]
    print(f"Dumping 16 Registers from Address 0x{addr:02X}:")
    print("-" * 45)

    try:
        regs = i2c.readfrom_mem(addr, 0x00, 16)
        for r_idx, val in enumerate(regs):
            print(f"  Reg 0x{r_idx:02X} : 0x{val:02X}  ({val:3d} decimal)")
    except Exception as e:
        print(f"Failed to read registers: {e}")

    print("-" * 45)

    # Test raw un-reset initialization sequence
    print("\nAttempting direct continuous mode write (0x09 <= 0x19)...")
    try:
        i2c.writeto_mem(addr, 0x0B, b"\x01")
        time.sleep_ms(10)
        i2c.writeto_mem(addr, 0x09, b"\x19")
        time.sleep_ms(30)

        data = i2c.readfrom_mem(addr, 0x00, 6)
        import ustruct
        x, y, z = ustruct.unpack("<hhh", data)
        print(f"Direct Reading after 0x19 write -> X:{x}, Y:{y}, Z:{z}")
    except Exception as e:
        print("Direct write error:", e)

    print("==========================================")

if __name__ == "__main__":
    dump_sensor()
