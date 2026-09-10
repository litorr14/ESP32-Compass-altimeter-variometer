"""
QMC5883 / GY-271 Calibration Tool for MicroPython
Run this script on the ESP32-C3 SuperMini to capture Hard-Iron and Soft-Iron calibration values.
Rotate the assembled compass unit smoothly in all 3D orientations for 30 seconds.
"""

import time
import sys
from machine import Pin, I2C

sys.modules.pop("qmc5883", None)
from qmc5883 import QMC5883

def run_calibration():
    print("==========================================")
    print(" Micro-Compass Magnetometer Calibration   ")
    print("==========================================")

    try:
        i2c = I2C(0, sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)
    except Exception:
        from machine import SoftI2C
        i2c = SoftI2C(sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)

    try:
        qmc = QMC5883(i2c)
        print(f"Sensor detected at I2C address 0x{qmc.address:02X}")
    except Exception as e:
        print("ERROR: Could not find magnetometer sensor!", e)
        return

    print("\nStarting calibration in 3 seconds...")
    print("Get ready to rotate your device 360 degrees in all axes!")
    time.sleep(3)

    min_x, max_x = None, None
    min_y, max_y = None, None
    min_z, max_z = None, None

    duration_sec = 30
    start_time = time.time()

    print("\n--> ROTATE DEVICE NOW! (30 seconds remaining) <--\n")

    last_second = -1

    while True:
        elapsed = time.time() - start_time
        remaining = duration_sec - elapsed
        if remaining <= 0:
            break

        current_second = int(elapsed)
        if current_second != last_second:
            last_second = current_second
            print(f"Time remaining: {duration_sec - current_second}s ... keep rotating!")

        raw = qmc.read_raw()
        if raw is not None:
            x, y, z = raw

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

        time.sleep_ms(20)

    print("\nCalibration Complete!\n")
    print(f"Raw Ranges:")
    print(f"  X: [{min_x}, {max_x}]")
    print(f"  Y: [{min_y}, {max_y}]")
    print(f"  Z: [{min_z}, {max_z}]\n")

    # Hard-iron offset calculation
    x_offset = (max_x + min_x) / 2.0
    y_offset = (max_y + min_y) / 2.0
    z_offset = (max_z + min_z) / 2.0

    # Soft-iron scale calculation
    avg_delta_x = (max_x - min_x) / 2.0
    avg_delta_y = (max_y - min_y) / 2.0
    avg_delta_z = (max_z - min_z) / 2.0

    avg_delta = (avg_delta_x + avg_delta_y + avg_delta_z) / 3.0

    x_scale = avg_delta / avg_delta_x if avg_delta_x != 0 else 1.0
    y_scale = avg_delta / avg_delta_y if avg_delta_y != 0 else 1.0
    z_scale = avg_delta / avg_delta_z if avg_delta_z != 0 else 1.0

    print("==========================================")
    print("COPY AND PASTE THESE VALUES INTO main.py :")
    print("==========================================")
    print(f"Xoffset = {x_offset:.3f}")
    print(f"Yoffset = {y_offset:.3f}")
    print(f"Zoffset = {z_offset:.3f}\n")
    print(f"Xscale = {x_scale:.3f}")
    print(f"Yscale = {y_scale:.3f}")
    print(f"Zscale = {z_scale:.3f}")
    print("==========================================")

if __name__ == "__main__":
    run_calibration()
