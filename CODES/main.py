"""
Micro-Compass-Vario Integrated Flight Instrument for ESP32-C3 SuperMini.
Sensors:
- GC9A01 1.28" Round SPI Display (240x240)
- GY-271 3-Axis Magnetometer (QMC5883L / QMC6310, I2C 0x0D)
- MPU-6050 6-DOF IMU (Accelerometer + Gyroscope, I2C 0x68)
- BMP280 Barometric Pressure & Altimeter (I2C 0x76)
- Passive Buzzer Vario Audio Synthesizer (PWM GPIO 4)
"""

import math
import time
import sys
from machine import Pin, SPI, I2C, SoftI2C

from gc9a01 import GC9A01
from qmc5883 import QMC5883
from mpu6050 import MPU6050
from bmp280 import BMP280
from vario_audio import VarioAudio
from vario_fusion import VarioFusion
from compass_ui import CompassUI

# -----------------------------------------------------------------------------
# Pin Configuration (ESP32-C3 SuperMini)
# -----------------------------------------------------------------------------
# SPI - GC9A01 Display
PIN_SCK      = 10  # GPIO 10 (SCL on display)
PIN_MOSI     = 6   # GPIO 6  (SDA on display)
PIN_DC       = 5   # GPIO 5  (DC on display)
PIN_CS       = 7   # GPIO 7  (CS on display)
PIN_RST      = 3   # GPIO 3  (RES on display)

# I2C - Sensors Bus (GY-271, MPU-6050, BMP280)
PIN_SDA      = 0   # GPIO 0
PIN_SCL      = 1   # GPIO 1

# PWM - Vario Audio Buzzer
PIN_BUZZER   = 4   # GPIO 4

# -----------------------------------------------------------------------------
# Magnetometer Calibration Parameters
# -----------------------------------------------------------------------------
Xoffset = 3384.0
Yoffset = -985.0
Zoffset = -132.0
Xscale  = 1.055
Yscale  = 1.000
Zscale  = 1.000
headingOffset = -4.0

def angle_difference(from_angle, to_angle):
    """Calculate shortest angular difference between two angles in degrees (-180 to +180)."""
    diff = to_angle - from_angle
    while diff > 180.0:
        diff -= 360.0
    while diff < -180.0:
        diff += 360.0
    return diff

def main():
    print("\n==========================================")
    print("🚀 Micro-Compass-Vario Starting Up...")
    print("==========================================")
    time.sleep_ms(300)

    # 1. Initialize GC9A01 Display via Hardware SPI
    try:
        spi = SPI(1, baudrate=20000000, sck=Pin(PIN_SCK), mosi=Pin(PIN_MOSI))
    except Exception:
        try:
            from machine import SoftSPI
            spi = SoftSPI(sck=Pin(PIN_SCK), mosi=Pin(PIN_MOSI), miso=Pin(8), baudrate=20000000)
        except Exception:
            spi = SPI(0, baudrate=20000000, sck=Pin(PIN_SCK), mosi=Pin(PIN_MOSI))

    dc = Pin(PIN_DC, Pin.OUT)
    cs = Pin(PIN_CS, Pin.OUT)
    rst = Pin(PIN_RST, Pin.OUT)

    display = GC9A01(spi, dc=dc, cs=cs, rst=rst, rotation=0)
    ui = CompassUI(display)
    ui.draw_static_dial()

    # 2. Initialize I2C Bus with Pull-Ups
    try:
        i2c = SoftI2C(sda=Pin(PIN_SDA, Pin.IN, Pin.PULL_UP), scl=Pin(PIN_SCL, Pin.IN, Pin.PULL_UP), freq=100000)
    except Exception:
        i2c = I2C(0, sda=Pin(PIN_SDA, Pin.IN, Pin.PULL_UP), scl=Pin(PIN_SCL, Pin.IN, Pin.PULL_UP), freq=100000)

    # I2C Discovery Scan
    scanned = i2c.scan()
    print(f"📡 I2C Scan Found Devices at: {[hex(a) for a in scanned]}")

    # 3. Initialize Magnetometer (QMC5883L / QMC6310)
    qmc = None
    try:
        qmc = QMC5883(i2c)
        print(f"✅ QMC5883L Magnetometer detected (0x{qmc.address:02X})")
    except Exception as e:
        print(f"⚠️ QMC5883L Magnetometer not found: {e}")

    # 4. Initialize MPU-6050 (IMU)
    mpu = None
    try:
        mpu = MPU6050(i2c)
        print(f"✅ MPU-6050 IMU detected (0x{mpu.address:02X})")
    except Exception as e:
        print(f"⚠️ MPU-6050 not detected: {e}")



    # 5. Initialize BMP280 (Barometer/Altimeter)
    bmp = None
    try:
        bmp = BMP280(i2c)
        print(f"✅ BMP280 Barometer detected (0x{bmp.address:02X})")
    except Exception as e:
        print(f"⚠️ BMP280 not detected: {e}")

    # 6. Initialize Vario Audio Synthesizer (Buzzer PWM on GPIO 4)
    audio = VarioAudio(pin_num=PIN_BUZZER, enabled=True)
    fusion = VarioFusion()

    # Show warning if no sensors connected
    if qmc is None and mpu is None and bmp is None:
        ui.draw_error_screen(
            "No Sensors Found!",
            [
                "Check I2C Wiring:",
                "SDA -> GPIO 0",
                "SCL -> GPIO 1",
                "3.3V & GND connected",
            ]
        )
        while True:
            time.sleep(1)

    # State variables
    pitch_deg, roll_deg = 0.0, 0.0
    current_alt = 0.0
    current_vspeed = 0.0
    last_heading = 0.0
    first_frame = True

    # Magnetometer Low-Pass Filter State
    sm_mx, sm_my, sm_mz = 0.0, 0.0, 0.0
    first_mag = True

    # Timers
    t_last_mag = time.ticks_ms()
    t_last_imu = time.ticks_ms()
    t_last_baro = time.ticks_ms()
    t_last_ui = time.ticks_ms()

    print("\n🟢 Flight Computer Operational. Running main loop...\n")

    while True:
        now = time.ticks_ms()

        # --- A. Read MPU-6050 (Pitch & Roll) at ~50 Hz (every 20ms) ---
        if mpu is not None and time.ticks_diff(now, t_last_imu) >= 20:
            t_last_imu = now
            try:
                p, r = mpu.read_pitch_roll()
                # Smooth pitch & roll to prevent sensor vibration jitter
                pitch_deg += 0.20 * (p - pitch_deg)
                roll_deg += 0.20 * (r - roll_deg)
            except Exception:
                pass

        # --- B. Read BMP280 (Altitude & Vario) at ~25 Hz (every 40ms) ---
        if bmp is not None and time.ticks_diff(now, t_last_baro) >= 40:
            t_last_baro = now
            try:
                raw_alt = bmp.read_altitude()
                current_alt, current_vspeed = fusion.update_vario(raw_alt)
            except Exception:
                pass

        # --- C. Update Acoustic Vario Audio Engine continuously ---
        audio.update(current_vspeed)

        # --- D. Read Magnetometer & Compute Heading at ~50 Hz (every 20ms) ---
        if qmc is not None and time.ticks_diff(now, t_last_mag) >= 20:
            t_last_mag = now
            raw_mag = qmc.read_raw()
            if raw_mag is not None:
                mx_raw, my_raw, mz_raw = raw_mag

                # Calibrate Hard-Iron and Soft-Iron offsets
                mx = (float(mx_raw) - Xoffset) * Xscale
                my = (float(my_raw) - Yoffset) * Yscale
                mz = (float(mz_raw) - Zoffset) * Zscale

                # Low-pass filter magnetic vector before trigonometry (eliminates spikes completely)
                if first_mag:
                    sm_mx, sm_my, sm_mz = mx, my, mz
                    first_mag = False
                else:
                    sm_mx += 0.25 * (mx - sm_mx)
                    sm_my += 0.25 * (my - sm_my)
                    sm_mz += 0.25 * (mz - sm_mz)

                # Calculate Clean Clockwise Magnetic Heading (Matching test_smooth_north.py)
                raw_heading = (-math.degrees(math.atan2(sm_my, sm_mx)) + headingOffset) % 360.0
                if raw_heading < 0:
                    raw_heading += 360.0

                last_heading = fusion.update_smooth_heading(raw_heading, alpha=0.30)

        # --- E. Render Display Frame at ~30-40 FPS (every 28ms) ---

        if time.ticks_diff(now, t_last_ui) >= 28:
            t_last_ui = now
            ui.update(
                heading_deg=last_heading,
                altitude_m=current_alt if bmp is not None else None,
                vspeed_mps=current_vspeed if bmp is not None else None,
                pitch_deg=pitch_deg,
                roll_deg=roll_deg
            )

        time.sleep_ms(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n❌ UNCAUGHT EXCEPTION IN MAIN:")
        sys.print_exception(e)
        while True:
            time.sleep(1)
