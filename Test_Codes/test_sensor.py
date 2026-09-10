import time
import math
import sys
import ustruct
from machine import Pin, I2C

# Remove cached modules if re-imported
sys.modules.pop("qmc5883", None)
sys.modules.pop("test_sensor", None)

from qmc5883 import QMC5883

def test_sensor():
    print("==========================================")
    print(" Magnetometer Diagnostic Sensor Test      ")
    print("==========================================")

    try:
        i2c = I2C(0, sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)
    except Exception:
        from machine import SoftI2C
        i2c = SoftI2C(sda=Pin(0, Pin.IN, Pin.PULL_UP), scl=Pin(1, Pin.IN, Pin.PULL_UP), freq=100000)

    devices = i2c.scan()
    print("I2C Bus Scan Devices:", [hex(d) for d in devices])

    if not devices:
        print("ERROR: No I2C devices found! Check wiring (SDA=GPIO0, SCL=GPIO1) and 3.3V power.")
        return

    addr = 0x2C if 0x2C in devices else devices[0]
    print(f"Sensor detected at address 0x{addr:02X}")

    print("\nInitialising driver...")
    try:
        qmc = QMC5883(i2c)
        print(f"Sensor driver initialized successfully at address 0x{qmc.address:02X}!")
    except Exception as e:
        print("Driver init error:", e)
        qmc = None

    print("\nReading 20 magnetic vector samples (rotate board):")
    print("-" * 55)

    for i in range(20):
        if qmc:
            raw = qmc.read_raw()
        else:
            try:
                data = i2c.readfrom_mem(addr, 0x00, 6)
                raw = ustruct.unpack("<hhh", data)
            except Exception:
                raw = None

        if raw is not None:
            x, y, z = raw
            heading = (math.degrees(math.atan2(-y, x))) % 360
            print(f"[{i+1:02d}] Raw X: {x:6d} | Raw Y: {y:6d} | Raw Z: {z:6d} | Heading: {heading:5.1f}°")
        else:
            print(f"[{i+1:02d}] Read Failed (None)")
        time.sleep(0.3)

    print("-" * 55)
    print("Diagnostic Finished!")

if __name__ == "__main__":
    test_sensor()
