"""
Live Interactive Magnetometer Calibration & Compass Debugging Tool
Run this script via Thonny on your ESP32-C3 SuperMini.
Rotate the board 360 degrees smoothly in the horizontal plane (and tilt slightly)
to see the min/max bounds adjust in real-time and compute the exact Hard-Iron offsets.
"""

import time
import math
import sys
from machine import Pin, I2C

# Reset cached modules if re-importing
sys.modules.pop("qmc5883", None)
from qmc5883 import QMC5883

def run_live_debug():
    print("\n============================================================")
    print(" 🧭 COMPASS LIVE REAL-TIME CALIBRATION & DEBUG TOOL")
    print("============================================================")

    # 1. Initialize I2C Bus
    try:
        i2c = I2C(0, sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)
    except Exception:
        from machine import SoftI2C
        i2c = SoftI2C(sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)

    devices = i2c.scan()
    print(f"📡 I2C Scan Devices: {[hex(d) for d in devices]}")

    if not devices:
        print("❌ ERROR: No I2C devices found! Check wiring (SDA=0, SCL=1, 3.3V, GND).")
        return

    # 2. Init QMC Magnetometer
    addr = 0x2C if 0x2C in devices else (0x0D if 0x0D in devices else devices[0])
    
    # Send Hardware Reset & Continuous Mode directly
    try:
        i2c.writeto(addr, bytearray([0x0A, 0x80]))
        time.sleep_ms(20)
    except Exception:
        pass

    try:
        i2c.writeto(addr, bytearray([0x0B, 0x01]))
        time.sleep_ms(10)
    except Exception:
        pass

    for mode_val in (0x0D, 0x05, 0x01, 0x25, 0x21):
        try:
            i2c.writeto(addr, bytearray([0x09, mode_val]))
            i2c.writeto(addr, bytearray([0x0A, mode_val]))
            time.sleep_ms(20)
            reg9 = i2c.readfrom_mem(addr, 0x09, 1)[0]
            reg10 = i2c.readfrom_mem(addr, 0x0A, 1)[0]
            if (reg10 & 0x01) == 1 or (reg9 & 0x01) == 1 or reg10 == mode_val or reg9 == mode_val:
                print(f"✅ QMC Magnetometer Continuous ±30G Mode Active at 0x{addr:02X}! (Reg 0x0A: 0x{reg10:02X}, Reg 0x09: 0x{reg9:02X})")
                break
        except Exception:
            pass

    print("\n------------------------------------------------------------")
    print("👉 ROTATE DEVICE 360° SLOWLY IN ALL DIRECTIONS NOW")
    print("   Press Ctrl+C at any time to finish and get final values.")
    print("------------------------------------------------------------\n")

    # Min/Max Tracking
    min_x, max_x = None, None
    min_y, max_y = None, None
    min_z, max_z = None, None

    sample_count = 0
    t_last_print = time.ticks_ms()
    import ustruct

    try:
        while True:
            try:
                data = i2c.readfrom_mem(addr, 0x01, 6)
                x, y, z = ustruct.unpack("<hhh", data)
                # Unlatch
                try:
                    i2c.readfrom_mem(addr, 0x09, 1)
                except Exception:
                    pass
            except Exception:
                x, y, z = None, None, None

            if x is not None:

                # Reject obvious glitch read (0,0,0)
                if x == 0 and y == 0 and z == 0:
                    time.sleep_ms(10)
                    continue

                if min_x is None:
                    min_x, max_x = x, x
                    min_y, max_y = y, y
                    min_z, max_z = z, z
                else:
                    if x < min_x: min_x = x
                    if x > max_x: max_x = x
                    if y < min_y: min_y = y
                    if y > max_y: max_y = y
                    if z < min_z: min_z = z
                    if z > max_z: max_z = z

                sample_count += 1

                now = time.ticks_ms()
                if time.ticks_diff(now, t_last_print) >= 150:
                    t_last_print = now

                    # Current calculated offsets
                    x_off = (max_x + min_x) / 2.0
                    y_off = (max_y + min_y) / 2.0
                    z_off = (max_z + min_z) / 2.0

                    # Calibrated X, Y
                    cal_x = x - x_off
                    cal_y = y - y_off

                    # Uncalibrated raw heading vs Calibrated heading
                    raw_heading = (math.degrees(math.atan2(y, x))) % 360.0
                    cal_heading = (math.degrees(math.atan2(cal_y, cal_x))) % 360.0

                    delta_x = max_x - min_x
                    delta_y = max_y - min_y

                    # Formatted live line
                    print(
                        f"Raw: ({x:6d}, {y:6d}) | "
                        f"Span: X:[{min_x:6d}..{max_x:6d}] Y:[{min_y:6d}..{max_y:6d}] | "
                        f"Offset: ({x_off:7.1f}, {y_off:7.1f}) | "
                        f"Heading: {cal_heading:5.1f}° (Raw: {raw_heading:5.1f}°)"
                    )

            time.sleep_ms(20)

    except KeyboardInterrupt:
        print("\n\n⏹️ Live calibration stopped by user.")

    # Final summary
    if min_x is not None and max_x is not None:
        x_off = (max_x + min_x) / 2.0
        y_off = (max_y + min_y) / 2.0
        z_off = (max_z + min_z) / 2.0

        delta_x = (max_x - min_x) / 2.0
        delta_y = (max_y - min_y) / 2.0
        delta_z = (max_z - min_z) / 2.0
        avg_delta = (delta_x + delta_y + delta_z) / 3.0 if (delta_x + delta_y + delta_z) > 0 else 1.0

        x_scale = (avg_delta / delta_x) if delta_x > 0 else 1.0
        y_scale = (avg_delta / delta_y) if delta_y > 0 else 1.0
        z_scale = (avg_delta / delta_z) if delta_z > 0 else 1.0

        print("\n============================================================")
        print("🎯 FINAL CALIBRATION PARAMETERS FOR CODES/main.py :")
        print("============================================================")
        print(f"Xoffset = {x_off:.1f}")
        print(f"Yoffset = {y_off:.1f}")
        print(f"Zoffset = {z_off:.1f}")
        print(f"Xscale  = {x_scale:.3f}")
        print(f"Yscale  = {y_scale:.3f}")
        print(f"Zscale  = {z_scale:.3f}")
        print("============================================================\n")

if __name__ == "__main__":
    run_live_debug()
