"""
MPU-6050 6-DOF Gyroscope & Accelerometer Driver for MicroPython.
Calculates Pitch, Roll, 3-Axis Accel (g), and 3-Axis Gyro (°/s).
Supports I2C address 0x68 (AD0=GND) and 0x69 (AD0=3.3V).
"""

import time
import struct
import math

class MPU6050:
    """MPU-6050 IMU Driver."""

    # Registers
    REG_SMPLRT_DIV   = 0x19
    REG_CONFIG       = 0x1A
    REG_GYRO_CONFIG  = 0x1B
    REG_ACCEL_CONFIG = 0x1C
    REG_ACCEL_XOUT_H = 0x3B
    REG_TEMP_OUT_H   = 0x41
    REG_GYRO_XOUT_H  = 0x43
    REG_PWR_MGMT_1   = 0x6B
    REG_PWR_MGMT_2   = 0x6C
    REG_WHO_AM_I     = 0x75

    def __init__(self, i2c, address=None):
        self.i2c = i2c
        self.address = address or self._detect_address()

        # Calibration Offsets
        self.ax_offset = 0.0
        self.ay_offset = 0.0
        self.az_offset = 0.0
        self.gx_offset = 0.0
        self.gy_offset = 0.0
        self.gz_offset = 0.0

        # Sensitivity scale factors (Default: Accel ±2g -> 16384 LSB/g, Gyro ±250°/s -> 131 LSB/(°/s))
        self.accel_scale = 16384.0
        self.gyro_scale = 131.0

        self._init_sensor()

    def _detect_address(self):
        """Auto-detect MPU6050 address on I2C bus (0x68 or 0x69)."""
        scanned = self.i2c.scan()
        if 0x68 in scanned:
            return 0x68
        elif 0x69 in scanned:
            return 0x69
        raise RuntimeError(f"MPU-6050 not found on I2C bus! Scanned addresses: {[hex(a) for a in scanned]}")

    def _write_byte(self, reg, val):
        self.i2c.writeto_mem(self.address, reg, bytes([val]))

    def _read_byte(self, reg):
        return self.i2c.readfrom_mem(self.address, reg, 1)[0]

    def _init_sensor(self):
        """Wake up device and configure sample rate & low-pass filtering."""
        # 1. Wake up device (clear SLEEP bit in PWR_MGMT_1, set clock source to Gyro X PLL)
        self._write_byte(self.REG_PWR_MGMT_1, 0x01)
        time.sleep_ms(10)

        # 2. Set sample rate divider (1kHz / (1 + 4) = 200 Hz)
        self._write_byte(self.REG_SMPLRT_DIV, 0x04)

        # 3. Configure Digital Low Pass Filter (DLPF = 42Hz bandwidth)
        self._write_byte(self.REG_CONFIG, 0x03)

        # 4. Set Gyro full-scale range: ±250 deg/s (0x00)
        self._write_byte(self.REG_GYRO_CONFIG, 0x00)

        # 5. Set Accel full-scale range: ±2g (0x00)
        self._write_byte(self.REG_ACCEL_CONFIG, 0x00)
        time.sleep_ms(20)

    def read_raw_all(self):
        """Read 14 contiguous bytes: Accel (X,Y,Z), Temp, Gyro (X,Y,Z)."""
        data = self.i2c.readfrom_mem(self.address, self.REG_ACCEL_XOUT_H, 14)
        ax, ay, az, raw_temp, gx, gy, gz = struct.unpack(">hhhhhhh", data)
        return ax, ay, az, raw_temp, gx, gy, gz

    def read_accel(self):
        """Return calibrated acceleration in g (Earth gravity units: 1.0 = 1g)."""
        ax, ay, az, _, _, _, _ = self.read_raw_all()
        return (
            (ax / self.accel_scale) - self.ax_offset,
            (ay / self.accel_scale) - self.ay_offset,
            (az / self.accel_scale) - self.az_offset,
        )

    def read_gyro(self):
        """Return calibrated angular rate in degrees per second (°/s)."""
        _, _, _, _, gx, gy, gz = self.read_raw_all()
        return (
            (gx / self.gyro_scale) - self.gx_offset,
            (gy / self.gyro_scale) - self.gy_offset,
            (gz / self.gyro_scale) - self.gz_offset,
        )

    def read_pitch_roll(self):
        """
        Calculate static pitch and roll angles in degrees from accelerometer gravity vector.
        Pitch: Nose up/down (-90 to +90 deg)
        Roll:  Wing bank left/right (-180 to +180 deg)
        """
        ax, ay, az = self.read_accel()

        # Roll: rotation around X axis
        roll = math.degrees(math.atan2(ay, az))

        # Pitch: rotation around Y axis
        denom = math.sqrt(ay * ay + az * az)
        pitch = math.degrees(math.atan2(-ax, denom)) if denom > 0 else 0.0

        return pitch, roll

    def calibrate(self, samples=200):
        """Compute zero-bias calibration offsets (keep board stationary and level!)."""
        print(f"Calibrating MPU-6050 ({samples} samples, keep level and still)...")
        sum_ax, sum_ay, sum_az = 0.0, 0.0, 0.0
        sum_gx, sum_gy, sum_gz = 0.0, 0.0, 0.0

        for _ in range(samples):
            ax, ay, az, _, gx, gy, gz = self.read_raw_all()
            sum_ax += ax / self.accel_scale
            sum_ay += ay / self.accel_scale
            sum_az += az / self.accel_scale
            sum_gx += gx / self.gyro_scale
            sum_gy += gy / self.gyro_scale
            sum_gz += gz / self.gyro_scale
            time.sleep_ms(5)

        self.ax_offset = sum_ax / samples
        self.ay_offset = sum_ay / samples
        # For Z, expect 1.0g under normal gravity when level
        self.az_offset = (sum_az / samples) - 1.0

        self.gx_offset = sum_gx / samples
        self.gy_offset = sum_gy / samples
        self.gz_offset = sum_gz / samples

        print(f"MPU-6050 Calibration done: Accel offsets=({self.ax_offset:.3f}, {self.ay_offset:.3f}, {self.az_offset:.3f}), Gyro offsets=({self.gx_offset:.2f}, {self.gy_offset:.2f}, {self.gz_offset:.2f})")
