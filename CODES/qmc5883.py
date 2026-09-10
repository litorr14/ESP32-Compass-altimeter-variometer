"""
QMC5883L / QMC5883P / HMC5883L Magnetometer (GY-271) MicroPython Driver (I2C)
Provides flexible continuous mode setup, robust address detection, and sensor recovery.
"""

import time
import ustruct
from micropython import const

# Known I2C Addresses for GY-271 variants
ADDR_QMC5883L = const(0x0D)
ADDR_QMC5883P = const(0x2C)
ADDR_HMC5883L = const(0x1E)

class QMC5883:
    """MicroPython Driver for QMC5883 / HMC5883 3-Axis Magnetometers."""

    def __init__(self, i2c, address=None):
        self.i2c = i2c
        self.address = address
        self.chip_type = "QMC"  # "QMC" or "HMC"
        self.last_raw = (1000, 1000, 1000)

        if self.address is None:
            self.address = self._scan_address()

        if self.address is None:
            raise RuntimeError(
                "Magnetometer sensor not found on I2C bus! Check wiring (SDA/SCL), power (3.3V/GND), and pull-up resistors."
            )

        self.init_sensor()

    def _scan_address(self):
        """Auto-detect magnetometer address on I2C bus."""
        devices = self.i2c.scan()
        print(f"I2C Scan found devices: {[hex(d) for d in devices]}")

        for addr in (ADDR_QMC5883L, ADDR_QMC5883P, ADDR_HMC5883L):
            if addr in devices:
                if addr == ADDR_HMC5883L:
                    self.chip_type = "HMC"
                return addr

        # Check other common magnetometer addresses before failing
        for addr in (0x0C, 0x0E, 0x1C, 0x30):
            if addr in devices:
                return addr

        return None

    def _write_reg(self, reg, val):
        """Send register write using direct writeto with writeto_mem fallback."""
        try:
            self.i2c.writeto(self.address, bytearray([reg, val]))
        except Exception:
            try:
                self.i2c.writeto_mem(self.address, reg, bytearray([val]))
            except Exception:
                pass

    def init_sensor(self):
        """Configure sensor registers for continuous measurement mode."""
        try:
            if self.chip_type == "HMC":
                print(f"Configuring HMC5883L at address 0x{self.address:02X}...")
                self._write_reg(0x00, 0x70)  # 8-sample avg, 15Hz
                self._write_reg(0x01, 0x20)  # Gain 1.3 Ga
                self._write_reg(0x02, 0x00)  # Continuous mode
            else:
                print(f"Configuring QMC magnetometer at address 0x{self.address:02X}...")

                # 1. Reset / Set Period Register
                try:
                    self._write_reg(0x0A, 0x80)
                    time.sleep_ms(20)
                except Exception:
                    pass

                try:
                    self._write_reg(0x0B, 0x01)
                    time.sleep_ms(10)
                except Exception:
                    pass

                # 2. Write continuous measurement mode (0x0D = ±30G Range, 200Hz ODR, 512 OSR)
                mode_accepted = False
                for mode_val in (0x0D, 0x05, 0x01, 0x25, 0x21):
                    try:
                        self._write_reg(0x09, mode_val)
                        self._write_reg(0x0A, mode_val)
                        time.sleep_ms(20)

                        reg9 = self.i2c.readfrom_mem(self.address, 0x09, 1)[0]
                        reg10 = self.i2c.readfrom_mem(self.address, 0x0A, 1)[0]

                        if (reg10 & 0x01) == 1 or (reg9 & 0x01) == 1 or reg10 == mode_val or reg9 == mode_val:
                            print(f"  --> Continuous ±30G Mode Active! (Reg 0x0A: 0x{reg10:02X}, Reg 0x09: 0x{reg9:02X})")
                            mode_accepted = True
                            break
                    except Exception:
                        pass

                if not mode_accepted:
                    self._write_reg(0x09, 0x0D)
                    self._write_reg(0x0A, 0x0D)

                time.sleep_ms(30)

        except Exception as e:
            raise RuntimeError(f"Failed to initialize sensor at address 0x{self.address:02X}: {e}")

    def read_raw(self):
        """Read raw 16-bit X, Y, Z magnetic values from sensor (fallbacks to last_raw on glitch)."""
        try:
            if self.chip_type == "HMC":
                data = self.i2c.readfrom_mem(self.address, 0x03, 6)
                x, z, y = ustruct.unpack(">hhh", data)
            else:
                data = self.i2c.readfrom_mem(self.address, 0x01, 6)
                x, y, z = ustruct.unpack("<hhh", data)
                # Read register 0x09 to unlatch for next conversion cycle
                try:
                    self.i2c.readfrom_mem(self.address, 0x09, 1)
                except Exception:
                    pass

            if not (x == 0 and y == 0 and z == 0):
                self.last_raw = (x, y, z)
            return self.last_raw
        except Exception:
            return self.last_raw

