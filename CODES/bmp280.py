"""
BMP280 Barometric Pressure & Temperature Sensor Driver for MicroPython.
Calculates calibrated pressure (hPa), temperature (°C), altitude (m/ft), and vertical climb rate.
Supports I2C addresses 0x76 (default SDO to GND) and 0x77 (SDO to 3.3V).
"""

import time
import struct
import math

class BMP280:
    """BMP280 Digital Pressure and Temperature Sensor."""

    # Registers
    REG_TEMP_XSB  = 0xFC
    REG_TEMP_LSB  = 0xFB
    REG_TEMP_MSB  = 0xFA
    REG_PRESS_XSB = 0xF9
    REG_PRESS_LSB = 0xF8
    REG_PRESS_MSB = 0xF7
    REG_CONFIG    = 0xF5
    REG_CTRL_MEAS = 0xF4
    REG_STATUS    = 0xF3
    REG_RESET     = 0xE0
    REG_ID        = 0xD0
    REG_CALIB     = 0x88

    # Standard Sea Level Pressure (QNH) in hPa
    STANDARD_SEA_LEVEL_HPA = 1013.25

    def __init__(self, i2c, address=None):
        self.i2c = i2c
        self.address = address or self._detect_address()
        self.t_fine = 0
        self.qnh = self.STANDARD_SEA_LEVEL_HPA
        
        # Verify chip ID
        chip_id = self._read_byte(self.REG_ID)
        # BMP280 chip IDs: 0x58 (BMP280), 0x56/0x57 (samples), 0x60 (BME280)
        if chip_id not in (0x58, 0x56, 0x57, 0x60):
            print(f"Warning: Unexpected BMP280 chip ID: 0x{chip_id:02X}")

        self._read_calibration()
        self._configure()

    def _detect_address(self):
        """Auto-detect sensor address on I2C bus (0x76 or 0x77)."""
        scanned = self.i2c.scan()
        if 0x76 in scanned:
            return 0x76
        elif 0x77 in scanned:
            return 0x77
        raise RuntimeError(f"BMP280 not found on I2C bus! Scanned addresses: {[hex(a) for a in scanned]}")

    def _read_byte(self, reg):
        return self.i2c.readfrom_mem(self.address, reg, 1)[0]

    def _write_byte(self, reg, val):
        self.i2c.writeto_mem(self.address, reg, bytes([val]))

    def _read_calibration(self):
        """Read 24 bytes of factory trimming parameters."""
        calib = self.i2c.readfrom_mem(self.address, self.REG_CALIB, 24)
        (
            self.dig_T1,
            self.dig_T2,
            self.dig_T3,
            self.dig_P1,
            self.dig_P2,
            self.dig_P3,
            self.dig_P4,
            self.dig_P5,
            self.dig_P6,
            self.dig_P7,
            self.dig_P8,
            self.dig_P9,
        ) = struct.unpack("<HhhHhhhhhhhh", calib)

    def _configure(self):
        """Configure sensor: Normal mode, osrs_t=x2, osrs_p=x16, filter=16, standby=0.5ms."""
        # CONFIG reg: standby 0.5ms (000), filter coeff 16 (100), spi3w_en 0 -> 0b00010000 = 0x10
        self._write_byte(self.REG_CONFIG, 0x10)
        # CTRL_MEAS reg: osrs_t x2 (010), osrs_p x16 (101), mode Normal (11) -> 0b01010111 = 0x57
        self._write_byte(self.REG_CTRL_MEAS, 0x57)
        time.sleep_ms(20)

    def set_qnh(self, qnh_hpa):
        """Set local sea level barometric pressure (QNH) in hPa for accurate altitude."""
        self.qnh = float(qnh_hpa)

    def read_raw(self):
        """Read raw uncompensated 20-bit temperature and pressure values."""
        data = self.i2c.readfrom_mem(self.address, self.REG_PRESS_MSB, 6)
        raw_p = ((data[0] << 16) | (data[1] << 8) | data[2]) >> 4
        raw_t = ((data[3] << 16) | (data[4] << 8) | data[5]) >> 4
        return raw_t, raw_p

    def read_temperature(self):
        """Read compensated temperature in degrees Celsius."""
        raw_t, _ = self.read_raw()
        var1 = (((raw_t >> 3) - (self.dig_T1 << 1)) * self.dig_T2) >> 11
        var2 = (((((raw_t >> 4) - self.dig_T1) * ((raw_t >> 4) - self.dig_T1)) >> 12) * self.dig_T3) >> 14
        self.t_fine = var1 + var2
        temp = (self.t_fine * 5 + 128) >> 8
        return temp / 100.0

    def read_pressure(self):
        """Read compensated atmospheric pressure in Pascals (Pa)."""
        raw_t, raw_p = self.read_raw()
        # Must compute temperature fine value first
        var1 = (((raw_t >> 3) - (self.dig_T1 << 1)) * self.dig_T2) >> 11
        var2 = (((((raw_t >> 4) - self.dig_T1) * ((raw_t >> 4) - self.dig_T1)) >> 12) * self.dig_T3) >> 14
        self.t_fine = var1 + var2

        # Pressure compensation 64-bit algorithm
        p_var1 = self.t_fine - 128000
        p_var2 = p_var1 * p_var1 * self.dig_P6
        p_var2 = p_var2 + ((p_var1 * self.dig_P5) << 17)
        p_var2 = p_var2 + (self.dig_P4 << 35)
        p_var1 = ((p_var1 * p_var1 * self.dig_P3) >> 8) + ((p_var1 * self.dig_P2) << 12)
        p_var1 = (((1 << 47) + p_var1) * self.dig_P1) >> 33

        if p_var1 == 0:
            return 0.0  # Avoid divide by zero

        p = 1048576 - raw_p
        p = int((((p << 31) - p_var2) * 3125) / p_var1)
        p_var1 = (self.dig_P9 * (p >> 13) * (p >> 13)) >> 25
        p_var2 = (self.dig_P8 * p) >> 19
        p = ((p + p_var1 + p_var2) >> 8) + (self.dig_P7 << 4)
        return p / 256.0

    def read_pressure_hpa(self):
        """Read pressure in hectopascals (hPa / mbar)."""
        return self.read_pressure() / 100.0

    def read_altitude(self):
        """
        Calculate barometric altitude in meters based on current pressure and QNH setting.
        Using the international barometric formula:
        h = 44330 * (1 - (P / QNH) ^ (1 / 5.255))
        """
        p_hpa = self.read_pressure_hpa()
        if p_hpa <= 0:
            return 0.0
        return 44330.0 * (1.0 - math.pow(p_hpa / self.qnh, 0.1902949))

    def read_all(self):
        """Convenience method returning (temp_c, press_hpa, altitude_m)."""
        press_pa = self.read_pressure()
        press_hpa = press_pa / 100.0
        temp_c = ((self.t_fine * 5 + 128) >> 8) / 100.0
        alt_m = 44330.0 * (1.0 - math.pow(press_hpa / self.qnh, 0.1902949)) if press_hpa > 0 else 0.0
        return temp_c, press_hpa, alt_m
