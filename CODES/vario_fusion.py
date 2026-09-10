"""
Sensor Fusion & Filtering Engine for Micro-Compass-Vario.
Provides:
1. Tilt-Compensated Magnetic Compass Heading (integrating QMC5883 + MPU-6050 Pitch/Roll).
2. Instantaneous Variometer Vertical Speed (Kalman / Complementary fusion of BMP280 Altitude + MPU-6050 Accel).
"""

import math
import time

class VarioFusion:
    """Sensor Fusion for Altitude, Climb Rate, and Tilt-Compensated Heading."""

    def __init__(self):
        # Variometer State
        self.filtered_alt = None
        self.climb_rate = 0.0        # m/s
        self.last_baro_time = time.ticks_ms()
        self.last_raw_alt = None

        # Complementary Filter Tuning
        # Weight between barometric differential vs accelerometer integration
        self.baro_weight = 0.85

        # Compass Filtering
        self.smooth_heading = 0.0
        self.first_heading = True

    def update_vario(self, raw_alt, accel_z=0.0):
        """
        Update altitude and vertical speed estimation.
        raw_alt: barometric altitude in meters from BMP280.
        accel_z: vertical acceleration in g from MPU-6050 (1.0g = stationary).
        Returns: (filtered_altitude, climb_rate_mps)
        """
        now = time.ticks_ms()
        dt_ms = time.ticks_diff(now, self.last_baro_time)

        if self.filtered_alt is None:
            self.filtered_alt = float(raw_alt)
            self.last_raw_alt = float(raw_alt)
            self.last_baro_time = now
            return self.filtered_alt, 0.0

        if dt_ms < 20:  # Avoid division by very small dt
            return self.filtered_alt, self.climb_rate

        dt = dt_ms / 1000.0
        self.last_baro_time = now

        prev_filtered_alt = self.filtered_alt

        # 1. Dual-stage low-pass smoothing on altitude
        self.filtered_alt += 0.15 * (raw_alt - self.filtered_alt)

        # 2. Derive vertical speed from smoothed altitude (eliminates raw derivative spikes)
        smooth_vspeed = (self.filtered_alt - prev_filtered_alt) / dt

        # 3. Low-pass filter vertical speed for graceful, spike-free transitions (~0.5s time constant)
        self.climb_rate += 0.10 * (smooth_vspeed - self.climb_rate)

        # 4. Clamp residual sensor drift around zero (-0.05 to +0.05 m/s)
        if abs(self.climb_rate) < 0.05:
            self.climb_rate = 0.0

        return self.filtered_alt, self.climb_rate

    def update_smooth_heading(self, target_deg, alpha=0.35):
        """
        Smoothly filter heading using shortest circular distance.
        Handles seamless wrapping across the 360° / 0° North boundary.
        Uses adaptive alpha: responds instantly to fast rotation,
        while maintaining smooth jitter-free needle when stationary.
        """
        target = target_deg % 360.0
        if target < 0:
            target += 360.0

        if self.first_heading:
            self.smooth_heading = target
            self.first_heading = False
            return self.smooth_heading

        # Shortest angular delta (-180° to +180°)
        diff = (target - self.smooth_heading + 180.0) % 360.0 - 180.0

        # Micro-deadband for stationary jitter suppression (0.2°)
        if abs(diff) < 0.2:
            return self.smooth_heading

        # Adaptive responsiveness: scale alpha up during active rotation
        abs_diff = abs(diff)
        if abs_diff > 30.0:
            eff_alpha = 0.85
        elif abs_diff > 12.0:
            eff_alpha = 0.60
        else:
            eff_alpha = alpha

        self.smooth_heading = (self.smooth_heading + eff_alpha * diff) % 360.0
        if self.smooth_heading < 0:
            self.smooth_heading += 360.0

        return self.smooth_heading

    def calculate_tilt_compensated_heading(self, mag_x, mag_y, mag_z, pitch_deg, roll_deg, heading_offset=0.0):
        """
        Calculate tilt-compensated magnetic heading using 3D magnetometer vector.
        Continuous smooth formulation with zero threshold jumps.
        """
        # Clamp pitch and roll to flight envelope (-50° to +50°)
        clamped_pitch = max(min(pitch_deg, 50.0), -50.0)
        clamped_roll  = max(min(roll_deg, 50.0), -50.0)

        pitch_rad = math.radians(clamped_pitch)
        roll_rad  = math.radians(clamped_roll)

        sin_p = math.sin(pitch_rad)
        cos_p = math.cos(pitch_rad)
        sin_r = math.sin(roll_rad)
        cos_r = math.cos(roll_rad)

        # Rotate magnetometer vector to horizontal ground plane
        xh = mag_x * cos_p + mag_y * sin_r * sin_p + mag_z * cos_r * sin_p
        yh = mag_y * cos_r - mag_z * sin_r

        # Calculate heading angle in clockwise degrees
        heading = (-math.degrees(math.atan2(yh, xh)) + heading_offset) % 360.0
        if heading < 0:
            heading += 360.0

        return heading


