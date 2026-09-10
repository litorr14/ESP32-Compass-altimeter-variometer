"""
QMC Magnetometer Range & Demagnetize Test (±30 Gauss & Set/Reset Pulse)
Tests higher dynamic range (±30G / ±12G) to clear magnetic saturation on the X-axis.
"""

import time
import ustruct
from machine import Pin, I2C

def test_ranges():
    print("\n============================================================")
    print(" 🧲 QMC RANGE (±30G) & DEMAGNETIZATION TEST")
    print("============================================================")

    try:
        i2c = I2C(0, sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)
    except Exception:
        from machine import SoftI2C
        i2c = SoftI2C(sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)

    devices = i2c.scan()
    if 0x2C not in devices:
        print("❌ Magnetometer at 0x2C not found!")
        return

    addr = 0x2C

    # Test full dynamic range settings
    # Bits 5:4 in Reg 0x09 control full scale range:
    # 0x09 / 0x0D = ±2 Gauss
    # 0x19 / 0x1D = ±8 Gauss
    # 0x29 / 0x2D = ±12 Gauss
    # 0x39 / 0x3D = ±30 Gauss (Widest dynamic range)
    
    ranges = [
        ("±30 Gauss Range (Reg09=0x3D)", 0x3D),
        ("±30 Gauss Range (Reg09=0x39)", 0x39),
        ("±12 Gauss Range (Reg09=0x2D)", 0x2D),
        ("±12 Gauss Range (Reg09=0x29)", 0x29),
        ("±8 Gauss Range  (Reg09=0x1D)", 0x1D),
    ]

    for name, r9_val in ranges:
        print(f"\n---> Testing {name} <---")
        
        # 1. Soft Reset
        try:
            i2c.writeto(addr, bytearray([0x0A, 0x80]))
            time.sleep_ms(20)
        except Exception:
            pass

        # 2. Strong Set/Reset pulse (Reg 0x0B = 0x01)
        try:
            i2c.writeto(addr, bytearray([0x0B, 0x01]))
            time.sleep_ms(15)
        except Exception:
            pass

        # 3. Write Mode & Range
        try:
            i2c.writeto(addr, bytearray([0x09, r9_val]))
            i2c.writeto(addr, bytearray([0x0A, r9_val]))
            time.sleep_ms(30)

            r9 = i2c.readfrom_mem(addr, 0x09, 1)[0]
            rA = i2c.readfrom_mem(addr, 0x0A, 1)[0]
            status = i2c.readfrom_mem(addr, 0x06, 1)[0]
            print(f"  Status: Reg09=0x{r9:02X}, Reg0A=0x{rA:02X}, Status(0x06)=0x{status:02X}")

            # Read 6 samples while user moves board
            for s in range(6):
                raw = i2c.readfrom_mem(addr, 0x00, 6)
                x, y, z = ustruct.unpack("<hhh", raw)
                hex_str = " ".join([f"{b:02X}" for b in raw])
                print(f"    [{s+1}] Bytes=[{hex_str}] -> X:{x:6d} | Y:{y:6d} | Z:{z:6d}")
                time.sleep_ms(150)

        except Exception as e:
            print(f"  Error: {e}")

    print("\n============================================================")
    print(" 💡 NOTE: If X is still frozen, temporarily unplug or move")
    print("    the black buzzer away from the sensor board to test.")
    print("============================================================")

if __name__ == "__main__":
    test_ranges()
